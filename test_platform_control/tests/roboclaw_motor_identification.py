#!/usr/bin/env python3
"""
RoboClaw Motor Identification Module
Comprehensive module for RoboClaw motor controller identification and motor mapping
Centrally controlled by system_test.py

Features:
- Check for previously identified Maker Pi devices and exclude their ports
- Detect and connect to RoboClaw controllers with timeout handling
- Interactive motor assignment with manual wheel turning and exit options
- Maker Pi detection and integration
- Automatic platform_config.json updates
- Cross-platform USB device detection
- Comprehensive error handling and logging
"""

import sys
import os
import json
import time
import serial
import serial.tools.list_ports
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

# Add the parent directory to sys.path to import from utils
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.roboclaw_interface import RoboClawInterface, TimeoutSafeRoboClaw
from utils.maker_pi_interface import MakerPiInterface

class RoboClawMotorIdentification:
    """RoboClaw motor identification and mapping module"""
    
    def __init__(self):
        """Initialize the motor identification module"""
        self.test_results = {
            "timestamp": datetime.now().isoformat(),
            "tests": {},
            "errors": [],
            "connection_timeouts": {
                "connection_test_timeout": 3.0,  # 3 seconds for connection test
                "version_read_timeout": 2.0,     # 2 seconds for version read
                "motor_data_timeout": 1.0        # 1 second for motor data read
            },
            "detected_controllers": {},
            "detected_maker_pi_devices": {},
            "motor_assignments": {},
            "motor_mapping": {}
        }
        self.platform_config = self.load_platform_config()
        self.roboclaw_config = self.platform_config.get('hardware', {}).get('roboclaw', {})
        self.maker_pi_config = self.platform_config.get('hardware', {}).get('maker_pi', {})
        
        # Initialize RoboClaw interface
        self.roboclaw_interface = RoboClawInterface(use_dual_controllers=True)
        
    def load_platform_config(self) -> Dict[str, Any]:
        """Load platform configuration"""
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'platform_config.json')
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load platform_config.json: {e}")
            return {}
    
    def log_error(self, test_name: str, error: str):
        """Log an error during testing"""
        self.test_results["errors"].append({
            "test": test_name,
            "error": error,
            "timestamp": datetime.now().isoformat()
        })
    
    def check_maker_pi_identification(self) -> List[str]:
        """Check for previously identified Maker Pi devices and return their ports"""
        print("\n=== Checking for Previously Identified Maker Pi Devices ===")
        
        maker_pi_config = self.platform_config.get('hardware', {}).get('maker_pi', {})
        detected_drives = maker_pi_config.get('detected_drives', {})
        
        excluded_ports = []
        
        if detected_drives:
            print(f"Found {len(detected_drives)} previously identified Maker Pi device(s):")
            for drive_path, drive_info in detected_drives.items():
                serial_port = drive_info.get('serial_port')
                if serial_port:
                    excluded_ports.append(serial_port)
                    print(f"  ✓ {drive_path}: {serial_port} (will be excluded from RoboClaw detection)")
                else:
                    print(f"  ⚠ {drive_path}: No serial port detected")
        else:
            print("No previously identified Maker Pi devices found")
            print("All USB ports will be scanned for RoboClaw controllers")
        
        return excluded_ports
    
    def detect_roboclaw_controllers(self, excluded_ports: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
        """Detect and connect to RoboClaw controllers with timeout handling and address prompting"""
        print("\n=== RoboClaw Controller Detection ===")
        print("Scanning for RoboClaw controllers with timeout protection...")
        
        if excluded_ports is None:
            excluded_ports = []
        
        if excluded_ports:
            print(f"⚠ Excluding ports used by Maker Pi devices: {excluded_ports}")
        
        controllers = self.roboclaw_config.get('controllers', {})
        if not controllers:
            print("✗ No RoboClaw controllers found in configuration")
            return {}
        
        detected_controllers = {}
        timeout = self.test_results["connection_timeouts"]["connection_test_timeout"]
        
        for controller_name, controller_info in controllers.items():
            try:
                port = controller_info['port']
                address = int(controller_info['address'], 16) if isinstance(controller_info['address'], str) else controller_info['address']
                
                # Skip if port is excluded (used by Maker Pi)
                if port in excluded_ports:
                    print(f"⚠ Skipping {controller_name} on {port} (excluded - used by Maker Pi)")
                    continue
                
                print(f"\nTesting {controller_name} on {port} (Address: 0x{address:02X})...")
                
                # Test port availability first
                if not self._test_port_availability(port):
                    print(f"✗ Port {port} is not available")
                    # Run troubleshooting for port availability issues
                    troubleshooting = self._troubleshoot_connection_issues(port, address)
                    continue
                
                # Test connection with timeout - this includes version reading
                connection_status, version_result = self._test_roboclaw_connection_with_timeout(port, address, timeout)
                if connection_status and version_result:
                    # Create controller object for successful connection with proper timeout
                    rc = TimeoutSafeRoboClaw(port, timeout=1.0, retries=2)
                    if rc.Open():
                        detected_controllers[controller_name] = {
                            'controller': rc.rc,  # Use the underlying Roboclaw object
                            'address': address,
                            'port': port,
                            'version': version_result,
                            'channels': controller_info.get('channels', [1, 2]),
                            'info': controller_info
                        }
                        print(f"✓ Connected to {controller_name} on {port}")
                        print(f"  Version: {version_result}")
                    else:
                        print(f"✗ Could not open port {port} for {controller_name}")
                        # Run troubleshooting for connection issues
                        troubleshooting = self._troubleshoot_connection_issues(port, address)
                else:
                    # Connection failed - prompt for different address or skip
                    print(f"✗ {controller_name} not responding to address 0x{address:02X}")
                    
                    # Run troubleshooting first
                    troubleshooting = self._troubleshoot_connection_issues(port, address)
                    
                    # Try alternative addresses
                    alternative_addresses = [0x81, 0x82, 0x83]
                    for alt_addr in alternative_addresses:
                        if alt_addr == address:
                            continue
                        
                        print(f"  Trying alternative address 0x{alt_addr:02X}...")
                        alt_connection_status, alt_version_result = self._test_roboclaw_connection_with_timeout(port, alt_addr, timeout)
                        
                        if alt_connection_status and alt_version_result:
                            print(f"✓ Found {controller_name} on {port} with address 0x{alt_addr:02X}")
                            print(f"  Version: {alt_version_result}")
                            
                            # Create controller object
                            rc = TimeoutSafeRoboClaw(port, timeout=1.0, retries=2)
                            if rc.Open():
                                detected_controllers[controller_name] = {
                                    'controller': rc.rc,
                                    'address': alt_addr,
                                    'port': port,
                                    'version': alt_version_result,
                                    'channels': controller_info.get('channels', [1, 2]),
                                    'info': controller_info
                                }
                                break
                    
                    if controller_name not in detected_controllers:
                        print(f"  ✗ {controller_name} not found on {port} with any address")
                        print("  Skipping this controller and continuing with others...")
                        
            except Exception as e:
                print(f"✗ Error testing {controller_name}: {e}")
                self.log_error("controller_detection", f"Error testing {controller_name}: {e}")
                continue
        
        if not detected_controllers:
            print("✗ No controllers connected!")
            print("\n🔧 Troubleshooting suggestions:")
            print("1. Check USB connections and cables")
            print("2. Verify RoboClaw power is on")
            print("3. Check Device Manager (Windows) or /dev/tty* (Linux)")
            print("4. Try different USB ports")
            print("5. Ensure RoboClaw drivers are installed")
        else:
            print(f"\n✓ Connected to {len(detected_controllers)} controller(s)")
        
        return detected_controllers
    
    def _test_port_availability(self, port_name: str) -> bool:
        """Test if a port is available for connection"""
        try:
            import serial
            with serial.Serial(port_name, 460800, timeout=0.1) as ser:
                return True
        except:
            return False
    
    def _troubleshoot_connection_issues(self, port_name: str, address: int) -> Dict[str, Any]:
        """Troubleshoot connection issues with detailed diagnostics"""
        troubleshooting_result = {
            'port': port_name,
            'address': address,
            'issues': [],
            'suggestions': [],
            'timestamp': datetime.now().isoformat()
        }
        
        print(f"\n🔧 Troubleshooting connection to {port_name} (Address: 0x{address:02X})...")
        
        # Check 1: Port availability
        if not self._test_port_availability(port_name):
            troubleshooting_result['issues'].append('Port not available')
            troubleshooting_result['suggestions'].append('Check if device is connected and drivers are installed')
            print("  ✗ Port not available - check device connection and drivers")
        else:
            print("  ✓ Port is available")
        
        # Check 2: Try different baud rates
        baud_rates = [460800, 38400, 115200, 57600, 9600]
        working_baud = None
        
        for baud in baud_rates:
            try:
                with serial.Serial(port_name, baud, timeout=0.5) as ser:
                    working_baud = baud
                    print(f"  ✓ Port accessible at {baud} baud")
                    break
            except:
                continue
        
        if working_baud is None:
            troubleshooting_result['issues'].append('Port not accessible at any baud rate')
            troubleshooting_result['suggestions'].append('Check device drivers and permissions')
            print("  ✗ Port not accessible at any baud rate")
        else:
            troubleshooting_result['suggestions'].append(f'Try using {working_baud} baud rate')
        
        # Check 3: OS-specific warnings
        import platform
        os_type = platform.system().lower()
        
        if os_type == "windows":
            troubleshooting_result['suggestions'].extend([
                'Check Device Manager for COM port assignment',
                'Ensure RoboClaw drivers are installed',
                'Try different USB cable or port'
            ])
            print("  ℹ Windows detected - check Device Manager and drivers")
        elif os_type == "linux":
            troubleshooting_result['suggestions'].extend([
                'Check user permissions for serial port access',
                'Run: sudo usermod -a -G dialout $USER',
                'Check if device appears in /dev/tty*'
            ])
            print("  ℹ Linux detected - check permissions and device files")
        
        return troubleshooting_result
    
    def _test_roboclaw_connection_with_timeout(self, port_name: str, address: int, timeout: float) -> Tuple[bool, Optional[str]]:
        """Test RoboClaw connection with timeout protection"""
        import threading
        import queue
        
        result_queue = queue.Queue()
        
        def connection_test():
            try:
                # Import Roboclaw class from the correct location
                sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'RoboClaw Software & CODE', 'roboclaw_python'))
                from roboclaw_3 import Roboclaw
                
                rc = Roboclaw(port_name, 0)  # USB mode
                if rc.Open():
                    version_result = self._read_roboclaw_version_with_timeout(rc, address, timeout)
                    if version_result:
                        result_queue.put((True, version_result))
                    else:
                        result_queue.put((False, None))
                else:
                    result_queue.put((False, None))
            except Exception as e:
                result_queue.put((False, None))
        
        # Start connection test in separate thread
        test_thread = threading.Thread(target=connection_test)
        test_thread.daemon = True
        test_thread.start()
        
        # Wait for result with timeout
        try:
            result = result_queue.get(timeout=timeout)
            return result
        except queue.Empty:
            print(f"  ⏰ Connection test timed out after {timeout} seconds")
            return (False, None)
    
    def _read_roboclaw_version_with_timeout(self, rc, address: int, timeout: float) -> Optional[str]:
        """Read RoboClaw version with timeout protection"""
        import threading
        import queue
        
        result_queue = queue.Queue()
        
        def version_read():
            try:
                version_result = rc.ReadVersion(address)
                if version_result[0]:
                    result_queue.put(version_result[1])
                else:
                    result_queue.put(None)
            except Exception as e:
                result_queue.put(None)
        
        # Start version read in separate thread
        read_thread = threading.Thread(target=version_read)
        read_thread.daemon = True
        read_thread.start()
        
        # Wait for result with timeout
        try:
            result = result_queue.get(timeout=timeout)
            return result
        except queue.Empty:
            print(f"  ⏰ Version read timed out after {timeout} seconds")
            return None
    
    def detect_maker_pi_devices(self) -> Dict[str, Dict[str, Any]]:
        """Detect Maker Pi devices with timeout protection"""
        print("\n=== Maker Pi Device Detection ===")
        
        import threading
        import queue
        
        result_queue = queue.Queue()
        
        def detection_with_timeout():
            try:
                # Use MakerPiInterface for detection
                maker_pi_interface = MakerPiInterface(self.maker_pi_config)
                detected_drives = maker_pi_interface.detect_circuitpython_drives()
                result_queue.put(detected_drives)
            except Exception as e:
                print(f"Error detecting Maker Pi devices: {e}")
                result_queue.put({})
        
        def run_detection():
            detection_thread = threading.Thread(target=detection_with_timeout)
            detection_thread.daemon = True
            detection_thread.start()
            
            try:
                result = result_queue.get(timeout=10.0)  # 10 second timeout
                return result
            except queue.Empty:
                print("⏰ Maker Pi detection timed out")
                return {}
        
        detected_drives = run_detection()
        
        if detected_drives:
            print(f"✓ Detected {len(detected_drives)} Maker Pi device(s):")
            for drive_path, drive_info in detected_drives.items():
                print(f"  {drive_path}: {drive_info.get('description', 'Unknown')}")
                if 'serial_port' in drive_info:
                    print(f"    Serial port: {drive_info['serial_port']}")
        else:
            print("No Maker Pi devices detected")
        
        return detected_drives
    
    def get_motor_data_from_controller(self, rc, address: int, channel: str) -> Optional[Dict[str, Any]]:
        """Get motor data from controller with timeout protection"""
        import threading
        import queue
        
        result_queue = queue.Queue()
        timeout = self.test_results["connection_timeouts"]["motor_data_timeout"]
        
        def read_motor_data():
            try:
                if channel == 'A':
                    enc_result = rc.ReadEncM1(address)
                    speed_result = rc.ReadSpeedM1(address)
                else:  # channel == 'B'
                    enc_result = rc.ReadEncM2(address)
                    speed_result = rc.ReadSpeedM2(address)
                
                if enc_result[0] and speed_result[0]:
                    result_queue.put({
                        'position': enc_result[1],
                        'velocity': speed_result[1],
                        'channel': channel
                    })
                else:
                    result_queue.put(None)
            except Exception as e:
                result_queue.put(None)
        
        # Start motor data read in separate thread
        read_thread = threading.Thread(target=read_motor_data)
        read_thread.daemon = True
        read_thread.start()
        
        # Wait for result with timeout
        try:
            result = result_queue.get(timeout=timeout)
            return result
        except queue.Empty:
            print(f"  ⏰ Motor data read timed out for channel {channel}")
            return None
    
    def interactive_motor_assignment(self, roboclaw_controllers: Dict[str, Dict[str, Any]]) -> Tuple[Dict[str, str], Dict[str, Dict[str, Any]]]:
        """Interactive motor assignment with user input and exit options"""
        print("\n=== Interactive Motor Assignment ===")
        print("Assign motors to their physical positions:")
        print("1. X-axis wheel (0°)")
        print("2. 120° from X-axis")
        print("3. 240° from X-axis")
        print("4. Linear stage (future)")
        print()
        print("Commands:")
        print("- Enter motor number (1-4) to assign")
        print("- Enter 's' to save current assignments")
        print("- Enter 'x' to exit without saving")
        print("- Enter 'r' to reset all assignments")
        print("- Enter 'h' to display current assignments")
        print()
        
        # Create list of available motors
        available_motors = []
        motor_info = {}
        
        for controller_name, controller_data in roboclaw_controllers.items():
            for channel in ['A', 'B']:
                motor_data = self.get_motor_data_from_controller(
                    controller_data['controller'], 
                    controller_data['address'], 
                    channel
                )
                if motor_data:
                    motor_num = len(available_motors) + 1
                    motor_name = f"motor{motor_num}"
                    available_motors.append(motor_name)
                    motor_info[motor_name] = {
                        'controller': controller_name,
                        'channel': channel,
                        'address': controller_data['address'],
                        'port': controller_data['port'],
                        'data': motor_data
                    }
                    print(f"✓ {motor_name}: {controller_name} Channel {channel} on {controller_data['port']}")
        
        if not available_motors:
            print("✗ No motors found!")
            return {}, {}
        
        print(f"\nFound {len(available_motors)} motor(s) to assign")
        
        # Initialize assignments
        assignments = {}  # position -> motor_name
        assigned_motors = set()  # motor_name
        
        while True:
            try:
                print("\nCurrent assignments:")
                if assignments:
                    for position, motor in assignments.items():
                        print(f"  Position {position} ({self._get_motor_position_description(int(position))}): {motor}")
                else:
                    print("  No motors assigned yet")
                
                print(f"\nAvailable motors: {', '.join([m for m in available_motors if m not in assigned_motors])}")
                
                choice = input("\nEnter choice (1-4, s, x, r, h): ").strip().lower()
                
                if choice == 's':
                    if assignments:
                        print("✓ Saving assignments...")
                        break
                    else:
                        print("⚠ No assignments to save")
                        continue
                
                elif choice == 'x':
                    print("⚠ Exiting without saving assignments")
                    return {}, {}
                
                elif choice == 'r':
                    assignments.clear()
                    assigned_motors.clear()
                    print("✓ All assignments reset")
                    continue
                
                elif choice == 'h':
                    self._display_current_assignments(assignments, motor_info)
                    continue
                
                elif choice in ['1', '2', '3', '4']:
                    position = int(choice)
                    
                    if position in assignments:
                        print(f"⚠ Position {position} is already assigned to {assignments[position]}")
                        unassign = input("Unassign it? (y/n): ").strip().lower()
                        if unassign == 'y':
                            assigned_motors.remove(assignments[position])
                            del assignments[position]
                            print(f"✓ Position {position} unassigned")
                        continue
                    
                    print(f"\nAssigning position {position} ({self._get_motor_position_description(position)})")
                    print("Available motors:")
                    available = [m for m in available_motors if m not in assigned_motors]
                    for i, motor in enumerate(available, 1):
                        print(f"  {i}. {motor}")
                    
                    motor_choice = input("Enter motor number: ").strip()
                    try:
                        motor_index = int(motor_choice) - 1
                        if 0 <= motor_index < len(available):
                            selected_motor = available[motor_index]
                            assignments[position] = selected_motor
                            assigned_motors.add(selected_motor)
                            print(f"✓ Position {position} assigned to {selected_motor}")
                        else:
                            print("⚠ Invalid motor number")
                    except ValueError:
                        print("⚠ Invalid input")
                    continue
                
                else:
                    print("⚠ Invalid choice. Please enter 1-4, s, x, r, or h")
                    continue
                    
            except KeyboardInterrupt:
                print("\n⚠ Interrupted by user")
                save_choice = input("Save current assignments? (y/n): ").strip().lower()
                if save_choice == 'y' and assignments:
                    print("✓ Saving assignments...")
                    break
                else:
                    print("⚠ Exiting without saving")
                    return {}, {}
        
        return assignments, motor_info
    
    def _get_motor_position_description(self, position: int) -> str:
        """Get description for motor position"""
        descriptions = {
            1: "X-axis (0°)",
            2: "120° from X-axis", 
            3: "240° from X-axis",
            4: "Linear stage (future)"
        }
        return descriptions.get(position, f"Position {position}")
    
    def _display_current_assignments(self, assignments: Dict[str, str], motor_info: Dict[str, Dict[str, Any]]):
        """Display current motor assignments"""
        print("\n=== Current Motor Assignments ===")
        if assignments:
            for position, motor in assignments.items():
                info = motor_info.get(motor, {})
                print(f"Position {position} ({self._get_motor_position_description(int(position))}):")
                print(f"  Motor: {motor}")
                print(f"  Controller: {info.get('controller', 'Unknown')}")
                print(f"  Channel: {info.get('channel', 'Unknown')}")
                print(f"  Port: {info.get('port', 'Unknown')}")
                print()
        else:
            print("No motors assigned")
    
    def create_motor_mapping(self, assignments: Dict[str, str], motor_info: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Create motor mapping for platform configuration"""
        motor_mapping = {}
        
        for position, motor_name in assignments.items():
            info = motor_info.get(motor_name, {})
            position_desc = self._get_motor_position_description(int(position))
            
            motor_mapping[motor_name] = {
                'controller': info.get('controller', 'unknown'),
                'address': f"0x{info.get('address', 0):02X}",
                'channel': info.get('channel', 'unknown'),
                'port': info.get('port', 'unknown'),
                'position': position_desc,
                'description': f"Motor at {position_desc}",
                'last_updated': datetime.now().isoformat(),
                'updated_by': 'roboclaw_motor_identification'
            }
        
        return motor_mapping
    
    def update_platform_config(self, motor_mapping: Dict[str, Dict[str, Any]], roboclaw_controllers: Dict[str, Dict[str, Any]]) -> bool:
        """Update platform configuration with motor mapping and controller info"""
        try:
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'platform_config.json')
            
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Update motor mapping
            if 'hardware' not in config:
                config['hardware'] = {}
            if 'roboclaw' not in config['hardware']:
                config['hardware']['roboclaw'] = {}
            
            config['hardware']['roboclaw']['motor_mapping'] = motor_mapping
            
            # Update controller information
            controllers_info = {}
            for controller_name, controller_data in roboclaw_controllers.items():
                controllers_info[controller_name] = {
                    'port': controller_data['port'],
                    'address': f"0x{controller_data['address']:02X}",
                    'channels': controller_data['channels'],
                    'motors': [motor for motor, info in motor_mapping.items() 
                              if info['controller'] == controller_name],
                    'description': f"Controller for {controller_name}",
                    'last_updated': datetime.now().isoformat(),
                    'updated_by': 'roboclaw_motor_identification'
                }
            
            config['hardware']['roboclaw']['controllers'] = controllers_info
            
            # Update timestamp
            config['hardware']['roboclaw']['last_updated'] = datetime.now().isoformat()
            config['hardware']['roboclaw']['updated_by'] = 'roboclaw_motor_identification'
            
            # Save updated config
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=4)
            
            print(f"\n✓ Motor mapping saved to {config_path}")
            return True
            
        except Exception as e:
            print(f"Error updating platform configuration: {e}")
            self.log_error("config_update", str(e))
            return False
    
    def display_identification_summary(self, assignments: Dict[str, str], motor_info: Dict[str, Dict[str, Any]], roboclaw_controllers: Dict[str, Dict[str, Any]]):
        """Display comprehensive identification summary"""
        print("\n" + "="*80)
        print("ROBOCLAW MOTOR IDENTIFICATION SUMMARY")
        print("="*80)
        
        # Display controller information
        if roboclaw_controllers:
            print("\n✓ CONNECTED CONTROLLERS:")
            for controller_name, controller_data in roboclaw_controllers.items():
                print(f"  {controller_name}:")
                print(f"    Port: {controller_data['port']}")
                print(f"    Address: 0x{controller_data['address']:02X}")
                print(f"    Version: {controller_data['version']}")
                print(f"    Channels: {controller_data['channels']}")
                print()
        else:
            print("\n✗ No controllers connected")
        
        # Display motor assignments
        if assignments:
            print("✓ MOTOR ASSIGNMENTS:")
            for position, motor in assignments.items():
                info = motor_info.get(motor, {})
                print(f"  Position {position} ({self._get_motor_position_description(int(position))}):")
                print(f"    Motor: {motor}")
                print(f"    Controller: {info.get('controller', 'Unknown')}")
                print(f"    Channel: {info.get('channel', 'Unknown')}")
                print(f"    Port: {info.get('port', 'Unknown')}")
                print()
        else:
            print("\n✗ No motors assigned")
        
        # Display statistics
        print("STATISTICS:")
        print(f"  Controllers detected: {len(roboclaw_controllers)}")
        print(f"  Motors available: {len(motor_info)}")
        print(f"  Motors assigned: {len(assignments)}")
        print(f"  Assignment completion: {(len(assignments) / len(motor_info) * 100):.1f}%" if motor_info else "0%")
        
        print("="*80)
    
    def offer_calibration_testing(self) -> bool:
        """Offer to run calibration tests after motor identification"""
        print("\n=== Calibration Testing Option ===")
        print("Motor identification completed successfully!")
        print("Would you like to run calibration tests to:")
        print("1. Calibrate motor constants")
        print("2. Validate speeds with tachometer")
        print("3. Update PID parameters")
        print("4. Skip calibration for now")
        print()
        
        while True:
            try:
                choice = input("Enter choice (1-4): ").strip()
                
                if choice == '1':
                    print("✓ Will run motor constant calibration")
                    return True
                elif choice == '2':
                    print("✓ Will run tachometer validation")
                    return True
                elif choice == '3':
                    print("✓ Will run PID parameter tuning")
                    return True
                elif choice == '4':
                    print("✓ Skipping calibration")
                    return False
                else:
                    print("⚠ Invalid choice. Please enter 1-4")
                    continue
                    
            except KeyboardInterrupt:
                print("\n⚠ Interrupted by user")
                return False
    
    def run_motor_identification(self) -> bool:
        """Run complete motor identification process"""
        print("RoboClaw Motor Identification Module")
        print("====================================")
        print("This module will:")
        print("1. Check for previously identified Maker Pi devices")
        print("2. Detect and connect to RoboClaw controllers")
        print("3. Perform interactive motor assignment")
        print("4. Create motor mapping for platform configuration")
        print("5. Offer calibration testing")
        print()
        
        # Step 1: Check for Maker Pi devices
        excluded_ports = self.check_maker_pi_identification()
        
        # Step 2: Detect RoboClaw controllers
        roboclaw_controllers = self.detect_roboclaw_controllers(excluded_ports)
        if not roboclaw_controllers:
            print("✗ No RoboClaw controllers detected")
            return False
        
        # Step 3: Interactive motor assignment
        assignments, motor_info = self.interactive_motor_assignment(roboclaw_controllers)
        if not assignments:
            print("⚠ No motors assigned")
            return False
        
        # Step 4: Create motor mapping
        motor_mapping = self.create_motor_mapping(assignments, motor_info)
        
        # Step 5: Display summary
        self.display_identification_summary(assignments, motor_info, roboclaw_controllers)
        
        # Step 6: Update platform configuration
        if self.update_platform_config(motor_mapping, roboclaw_controllers):
            print("✓ Motor identification completed successfully!")
            
            # Step 7: Offer calibration testing
            if self.offer_calibration_testing():
                print("✓ Calibration testing will be available in the main menu")
            
            self.test_results["detected_controllers"] = roboclaw_controllers
            self.test_results["motor_assignments"] = assignments
            self.test_results["motor_mapping"] = motor_mapping
            return True
        else:
            print("✗ Failed to update platform configuration")
            return False

def main():
    """Main function for standalone execution"""
    # Check if this is being run directly or imported
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--standalone':
        motor_identification = RoboClawMotorIdentification()
        success = motor_identification.run_motor_identification()
        
        if success:
            print("\n✓ Motor identification completed successfully!")
        else:
            print("\n✗ Motor identification failed!")
        
        return success
    else:
        # This is being imported by system_test.py, don't run automatically
        return True

if __name__ == "__main__":
    # Only run if called directly with --standalone flag
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--standalone':
        main()
    else:
        print("RoboClaw motor identification module loaded. Use --standalone flag to run directly.") 