#!/usr/bin/env python3
"""
Consolidated RoboClaw Interface Module
Integrates all RoboClaw functionality including interface, testing, troubleshooting, and motor identification
Uses roboclaw_3.py as the reference implementation and platform_config.json for configuration

Features:
- Dual controller support (USB and RS232 modes)
- Motor identification and assignment
- Settings backup and comparison
- PID parameter management (read/write only - no autotune via USB)
- Comprehensive troubleshooting and connectivity testing
- Integration with platform_config.json for all settings
"""

import sys
import os
import json
import time
import platform
import serial
import threading
import serial.tools.list_ports
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

# Add the parent directory to sys.path to import roboclaw_3
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
try:
    from roboclaw_3 import Roboclaw
except ImportError:
    # Try alternative path
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'RoboClaw Software & CODE', 'roboclaw_python'))
    from roboclaw_3 import Roboclaw

class TimeoutSafeRoboClaw:
    """Timeout-safe wrapper for RoboClaw to prevent hanging on non-RoboClaw devices"""
    
    def __init__(self, port_name: str, timeout: float = 1.0, retries: int = 1):
        """Initialize with timeout-safe settings"""
        # Create RoboClaw instance with reasonable timeout to prevent hanging
        self.rc = Roboclaw(port_name, 0, timeout=0.5, retries=retries)  # 500ms timeout
        self.port_name = port_name
        self.timeout = timeout
        
    def Open(self) -> bool:
        """Open the port with timeout protection"""
        try:
            return bool(self.rc.Open())
        except Exception:
            return False
    
    def ReadVersion(self, address: int) -> Tuple[int, Any]:
        """Read version with timeout protection"""
        try:
            # Set a very short timeout for the serial port to prevent hanging
            if hasattr(self.rc, '_port') and self.rc._port:
                self.rc._port.timeout = 0.1  # 100ms timeout
            
            result = self.rc.ReadVersion(address)
            return result
        except Exception:
            return (0, "")
    
    def _port_close(self):
        """Close the port safely"""
        try:
            if hasattr(self.rc, '_port') and self.rc._port:
                self.rc._port.close()
        except Exception:
            pass

class RoboClawTroubleshooter:
    """Helper for troubleshooting RoboClaw connectivity issues."""
    @staticmethod
    def handle_serial_timeout(port, channel=None, log_func=None):
        msg = f"\n[!] Serial timeout or no response from RoboClaw on port {port}"
        if channel:
            msg += f", channel {channel}"
        msg += ".\n"
        msg += "Possible causes:\n"
        msg += " - Incorrect COM port or port in use by another application\n"
        msg += " - USB/RS232 cable not connected or faulty\n"
        msg += " - RoboClaw not powered or not in correct mode\n"
        msg += " - Incorrect address or baudrate configuration\n"
        msg += " - Driver not installed or permissions issue\n"
        msg += " - Address conflict (multiple controllers with same address)\n"
        msg += "\nTroubleshooting steps:\n"
        msg += " 1. Check physical connections and power.\n"
        msg += " 2. Verify correct COM port in platform_config.json.\n"
        msg += " 3. Try disconnecting/reconnecting USB.\n"
        msg += " 4. Use Windows Device Manager to check port status.\n"
        msg += " 5. Ensure only one app is using the port.\n"
        msg += " 6. If using RS232, check wiring and jumpers.\n"
        msg += " 7. Try swapping cables or ports.\n"
        msg += " 8. If both controllers have same address, change one using IonMotion.\n"
        print(msg)
        if log_func:
            log_func("connectivity", msg)

class RoboClawInterface:
    def __init__(self, use_dual_controllers: bool = False, use_rs232_fallback: bool = False):
        """
        Initialize the RoboClaw interface
        Args:
            use_dual_controllers: If True, attempt to connect to both controllers. If False, only connect to RC1.
            use_rs232_fallback: If True, use RS232 communication instead of USB (for troubleshooting)
        """
        self.use_dual_controllers = use_dual_controllers
        self.use_rs232_fallback = use_rs232_fallback
        self.connected = False
        
        # Load configuration from platform_config.json
        self.config = self.load_platform_config()
        self.roboclaw_config = self.config.get('hardware', {}).get('roboclaw', {})
        
        # Initialize controllers based on configuration
        self.rc1 = None
        self.rc2 = None
        self.controller_info = {}
        self.motor_data = {}
        
        # Initialize settings manager
        self.settings_manager = RoboclawSettings()
        
        # Initialize troubleshooting components
        self.current_os = self.detect_os()
        self.backup_dir = self.config.get('testing', {}).get('roboclaw_settings_backup_dir', 
                                                           'tests/roboclaw_settings_backup')
        self.encoder_monitoring = False
        self.monitoring_thread = None
        self.errors = []
        
        # Setup controllers
        self.setup_controllers()
    
    def detect_os(self) -> str:
        """Detect the current operating system"""
        system = platform.system().lower()
        if system == "windows":
            return "windows"
        elif system == "linux":
            return "ubuntu"
        else:
            return "unknown"
    
    def load_platform_config(self) -> Dict[str, Any]:
        """Load platform configuration from JSON file"""
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'platform_config.json')
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load platform_config.json: {e}")
            return {}
    
    def _parse_address(self, address_value):
        """Parse address value from config (supports both hex strings and integers)"""
        if isinstance(address_value, str):
            if address_value.startswith('0x'):
                return int(address_value, 16)
            else:
                return int(address_value)
        else:
            return int(address_value)

    def setup_controllers(self):
        """Setup RoboClaw controllers based on configuration"""
        # Get controller configurations from platform_config.json
        controllers_config = self.roboclaw_config.get('controllers', {})
        communication_config = self.roboclaw_config.get('communication', {})
        rs232_config = communication_config.get('rs232_settings', {})
        motor_mapping = self.roboclaw_config.get('motor_mapping', {})

        # Get configuration values
        rc1_config = controllers_config.get('rc1', {})
        rc2_config = controllers_config.get('rc2', {})
        
        rc1_port = rc1_config.get('port')
        rc2_port = rc2_config.get('port')
        rc1_address = self._parse_address(rc1_config.get('address'))
        rc2_address = self._parse_address(rc2_config.get('address'))
        
        if self.use_rs232_fallback:
            # RS232 mode: requires baud rate and address
            baudrate_primary = rs232_config.get('baudrate_primary')
            baudrate_fallback = rs232_config.get('baudrate_fallback')
            rs232_rc1_address = self._parse_address(rs232_config.get('addresses', {}).get('rc1'))
            rs232_rc2_address = self._parse_address(rs232_config.get('addresses', {}).get('rc2'))

            # Use RS232 addresses if available, otherwise fall back to controller addresses
            rc1_address = rs232_rc1_address if rs232_rc1_address is not None else rc1_address
            rc2_address = rs232_rc2_address if rs232_rc2_address is not None else rc2_address

            # Initialize first controller with RS232 settings
            self.rc1 = Roboclaw(rc1_port, baudrate_primary)
            self.controller_info['rc1'] = {
                'connected': False, 
                'address': rc1_address,
                'port': rc1_port,
                'baudrate_primary': baudrate_primary,
                'baudrate_fallback': baudrate_fallback,
                'communication_mode': 'RS232'
            }

            # Initialize second controller if using dual controllers
            if self.use_dual_controllers:
                self.rc2 = Roboclaw(rc2_port, baudrate_primary)
                self.controller_info['rc2'] = {
                    'connected': False, 
                    'address': rc2_address,
                    'port': rc2_port,
                    'baudrate_primary': baudrate_primary,
                    'baudrate_fallback': baudrate_fallback,
                    'communication_mode': 'RS232'
                }
        else:
            # USB mode: still requires address for RoboClaw methods, but no baud rate
            # Initialize first controller with USB settings
            self.rc1 = Roboclaw(rc1_port, 0)  # USB mode, baud rate not used
            self.controller_info['rc1'] = {
                'connected': False, 
                'address': rc1_address,
                'port': rc1_port,
                'baudrate': None,  # No baud rate in USB mode
                'communication_mode': 'USB'
            }

            # Initialize second controller if using dual controllers
            if self.use_dual_controllers:
                self.rc2 = Roboclaw(rc2_port, 0)  # USB mode, baud rate not used
                self.controller_info['rc2'] = {
                    'connected': False, 
                    'address': rc2_address,
                    'port': rc2_port,
                    'baudrate': None,  # No baud rate in USB mode
                    'communication_mode': 'USB'
                }
        
        # Setup motor data based on motor mapping configuration
        self.motor_data = {}
        for motor_num in range(1, 4):  # Motors 1, 2, 3
            motor_key = f"motor{motor_num}"
            if motor_key in motor_mapping:
                motor_config = motor_mapping[motor_key]
                controller_name = motor_config['controller']
                address = self._parse_address(motor_config['address'])
                channel = motor_config['channel']
                
                # Get the appropriate controller instance
                if controller_name == 'rc1':
                    controller = self.rc1
                elif controller_name == 'rc2':
                    controller = self.rc2
                else:
                    print(f"Warning: Unknown controller {controller_name} for {motor_key}")
                    continue
                
                # Map channel A/B to 1/2 for RoboClaw methods
                channel_num = 1 if channel == 'A' else 2
                
                self.motor_data[motor_num] = {
                    'address': address,
                    'channel': channel_num,  # 1 for A, 2 for B
                    'controller': controller,
                    'controller_name': controller_name,
                    'channel_letter': channel
                }
    
    def connect(self) -> bool:
        """
        Connect to the RoboClaw controller(s)
        Returns:
            bool: True if at least one controller is connected successfully
        """
        try:
            print("\nAttempting to connect to Roboclaw controllers...")
            print(f"Communication mode: {'RS232' if self.use_rs232_fallback else 'USB'}")
            
            # Validate configuration before attempting connection
            if not self._validate_configuration():
                return False
            
            # Try to connect to first controller
            rc1_info = self.controller_info['rc1']
            print(f"\nTrying to connect to first controller on {rc1_info['port']}...")
            
            if self.use_rs232_fallback:
                print(f"  Address: 0x{rc1_info['address']:02X}")
                print(f"  Baudrate: {rc1_info['baudrate_primary']}")
                
                # Try primary baud rate first
                if self.rc1 and self.rc1.Open():
                    self.controller_info['rc1']['connected'] = True
                    print(f"✓ Successfully connected to first controller at {rc1_info['baudrate_primary']} baud")
                else:
                    # Try fallback baud rate
                    print(f"Primary baud rate failed, trying fallback {rc1_info['baudrate_fallback']}...")
                    self.rc1 = Roboclaw(rc1_info['port'], rc1_info['baudrate_fallback'])
                    if self.rc1 and self.rc1.Open():
                        self.controller_info['rc1']['connected'] = True
                        print(f"✓ Successfully connected to first controller at {rc1_info['baudrate_fallback']} baud")
                    else:
                        print(f"✗ Failed to connect to first controller on {rc1_info['port']}")
                        if self._handle_connection_failure('rc1', rc1_info):
                            return False
            else:
                # USB mode
                print(f"  Address: 0x{rc1_info['address']:02X}")
                
                if self.rc1 and self.rc1.Open():
                    self.controller_info['rc1']['connected'] = True
                    print("✓ Successfully connected to first controller via USB")
                else:
                    print(f"✗ Failed to connect to first controller on {rc1_info['port']}")
                    if self._handle_connection_failure('rc1', rc1_info):
                        return False
            
            # Try to connect to second controller if using dual controllers
            if self.use_dual_controllers and self.rc2:
                rc2_info = self.controller_info['rc2']
                print(f"\nTrying to connect to second controller on {rc2_info['port']}...")
                
                if self.use_rs232_fallback:
                    print(f"  Address: 0x{rc2_info['address']:02X}")
                    print(f"  Baudrate: {rc2_info['baudrate_primary']}")
                    
                    if self.rc2.Open():
                        self.controller_info['rc2']['connected'] = True
                        print(f"✓ Successfully connected to second controller at {rc2_info['baudrate_primary']} baud")
                    else:
                        # Try fallback baud rate
                        print(f"Primary baud rate failed, trying fallback {rc2_info['baudrate_fallback']}...")
                        self.rc2 = Roboclaw(rc2_info['port'], rc2_info['baudrate_fallback'])
                        if self.rc2.Open():
                            self.controller_info['rc2']['connected'] = True
                            print(f"✓ Successfully connected to second controller at {rc2_info['baudrate_fallback']} baud")
                        else:
                            print(f"✗ Failed to connect to second controller on {rc2_info['port']}")
                            if self._handle_connection_failure('rc2', rc2_info):
                                return False
                else:
                    # USB mode
                    print(f"  Address: 0x{rc2_info['address']:02X}")
                    
                    if self.rc2.Open():
                        self.controller_info['rc2']['connected'] = True
                        print("✓ Successfully connected to second controller via USB")
                    else:
                        print(f"✗ Failed to connect to second controller on {rc2_info['port']}")
                        if self._handle_connection_failure('rc2', rc2_info):
                            return False
            
            # Check if at least one controller is connected
            connected_controllers = [name for name, info in self.controller_info.items() if info['connected']]
            if connected_controllers:
                self.connected = True
                print(f"\n✓ Successfully connected to {len(connected_controllers)} controller(s): {', '.join(connected_controllers)}")
                self.update_config_timestamp()
                return True
            else:
                print("\n✗ No controllers connected successfully")
                return False
                
        except Exception as e:
            print(f"Error during connection: {e}")
            self.log_error("connection", str(e))
            return False
    
    def _validate_configuration(self) -> bool:
        """Validate the configuration has required fields"""
        required_fields = []
        
        # Check RC1 configuration
        rc1_config = self.roboclaw_config.get('controllers', {}).get('rc1', {})
        if not rc1_config.get('port'):
            required_fields.append("RC1 port")
        if not rc1_config.get('address'):
            required_fields.append("RC1 address")
        
        # Check RC2 configuration if using dual controllers
        if self.use_dual_controllers:
            rc2_config = self.roboclaw_config.get('controllers', {}).get('rc2', {})
            if not rc2_config.get('port'):
                required_fields.append("RC2 port")
            if not rc2_config.get('address'):
                required_fields.append("RC2 address")
        
        if required_fields:
            print(f"✗ Missing configuration: {', '.join(required_fields)}")
            return False
        
        print("✓ Configuration validation passed")
        return True
    
    def _handle_connection_failure(self, controller_name: str, current_settings: Dict[str, Any]) -> bool:
        """Handle connection failure with user interaction"""
        print(f"\nConnection failed for {controller_name}")
        print("Current settings:")
        for key, value in current_settings.items():
            print(f"  {key}: {value}")
        
        response = input("\nWould you like to update connection settings? (y/n): ").lower().strip()
        if response == 'y':
            new_settings = self.prompt_for_connection_settings(controller_name, current_settings)
            if new_settings:
                self.update_platform_config(controller_name, new_settings)
                return True
        
        return False
    
    def update_config_timestamp(self):
        """Update the last_updated timestamp in platform_config.json"""
        try:
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'platform_config.json')
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Update timestamp
            if 'hardware' not in config:
                config['hardware'] = {}
            if 'roboclaw' not in config['hardware']:
                config['hardware']['roboclaw'] = {}
            
            config['hardware']['roboclaw']['last_updated'] = datetime.now().isoformat()
            config['hardware']['roboclaw']['updated_by'] = 'roboclaw_interface'
            
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=4)
                
        except Exception as e:
            print(f"Warning: Could not update config timestamp: {e}")
    
    def read_and_save_settings(self) -> bool:
        """Read current settings from all connected controllers and save to backup"""
        try:
            print("\n=== Reading and Saving RoboClaw Settings ===")
            
            all_settings = {}
            for controller_name, controller_info in self.controller_info.items():
                if controller_info['connected']:
                    print(f"\nReading settings from {controller_name}...")
                    
                    # Get controller instance
                    if controller_name == 'rc1':
                        rc = self.rc1
                    elif controller_name == 'rc2':
                        rc = self.rc2
                    else:
                        continue
                    
                    # Read settings using RoboclawSettings class
                    settings = self.settings_manager.read_current_settings(rc, controller_info['address'])
                    if settings:
                        all_settings[controller_name] = settings
                        print(f"✓ Successfully read settings from {controller_name}")
                    else:
                        print(f"✗ Failed to read settings from {controller_name}")
            
            if all_settings:
                # Save settings to backup
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_filename = f"roboclaw_settings_{timestamp}.json"
                backup_path = os.path.join(self.backup_dir, backup_filename)
                
                # Ensure backup directory exists
                os.makedirs(self.backup_dir, exist_ok=True)
                
                with open(backup_path, 'w') as f:
                    json.dump(all_settings, f, indent=4)
                
                print(f"\n✓ Settings saved to {backup_path}")
                
                # Update platform_config.json with current settings
                for controller_name, settings in all_settings.items():
                    self.update_platform_config(controller_name, settings)
                
                return True
            else:
                print("✗ No settings read from any controller")
                return False
                
        except Exception as e:
            print(f"Error reading and saving settings: {e}")
            self.log_error("read_and_save_settings", str(e))
            return False
    
    def compare_with_previous_settings(self):
        """Compare current settings with previous backup"""
        try:
            print("\n=== Comparing with Previous Settings ===")
            
            # Get latest backup file
            backup_files = [f for f in os.listdir(self.backup_dir) if f.startswith('roboclaw_settings_') and f.endswith('.json')]
            if not backup_files:
                print("No previous settings found for comparison")
                return
            
            backup_files.sort(reverse=True)
            latest_backup = backup_files[0]
            latest_backup_path = os.path.join(self.backup_dir, latest_backup)
            
            print(f"Comparing with {latest_backup}...")
            
            with open(latest_backup_path, 'r') as f:
                previous_settings = json.load(f)
            
            # Read current settings
            current_settings = {}
            for controller_name, controller_info in self.controller_info.items():
                if controller_info['connected']:
                    if controller_name == 'rc1':
                        rc = self.rc1
                    elif controller_name == 'rc2':
                        rc = self.rc2
                    else:
                        continue
                    
                    settings = self.settings_manager.read_current_settings(rc, controller_info['address'])
                    if settings:
                        current_settings[controller_name] = settings
            
            # Compare settings
            differences = self.compare_with_reference_settings(current_settings)
            
            if differences:
                print("Differences found:")
                self.print_settings_comparison(differences, "previous")
            else:
                print("✓ No differences found")
                
        except Exception as e:
            print(f"Error comparing settings: {e}")
            self.log_error("compare_with_previous_settings", str(e))
    
    def get_motor_data(self, motor_num: int) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive motor data for a specific motor
        Args:
            motor_num: Motor number (1, 2, or 3)
        Returns:
            Dict containing motor data or None if error
        """
        try:
            if motor_num not in self.motor_data:
                print(f"Motor {motor_num} not configured")
                return None
            
            motor_info = self.motor_data[motor_num]
            controller = motor_info['controller']
            address = motor_info['address']
            channel = motor_info['channel']
            
            if not controller:
                print(f"Controller not available for motor {motor_num}")
                return None
            
            # Read encoder data
            if channel == 1:  # Motor A
                enc_result = controller.ReadEncM1(address)
                speed_result = controller.ReadSpeedM1(address)
                ispeed_result = controller.ReadISpeedM1(address)
            else:  # Motor B
                enc_result = controller.ReadEncM2(address)
                speed_result = controller.ReadSpeedM2(address)
                ispeed_result = controller.ReadISpeedM2(address)
            
            # Read voltage and current
            voltage_result = controller.ReadMainBatteryVoltage(address)
            current_result = controller.ReadCurrents(address)
            
            # Read error status
            error_result = controller.ReadError(address)
            
            # Read temperature
            temp_result = controller.ReadTemp(address)
            
            # Check if all reads were successful
            if (enc_result[0] and speed_result[0] and ispeed_result[0] and 
                voltage_result[0] and current_result[0] and error_result[0] and temp_result[0]):
                
                # Extract current for specific motor
                if channel == 1:
                    current = current_result[1]  # Motor 1 current
                else:
                    current = current_result[2]  # Motor 2 current
                
                # Get PID settings
                if channel == 1:
                    pid_result = controller.ReadM1VelocityPID(address)
                else:
                    pid_result = controller.ReadM2VelocityPID(address)
                
                pid_data = {}
                if pid_result[0]:
                    pid_data = {
                        'p': pid_result[1] / 65536.0,  # Convert from scaled value
                        'i': pid_result[2] / 65536.0,
                        'd': pid_result[3] / 65536.0,
                        'qpps': pid_result[4]
                    }
                
                return {
                    'motor_num': motor_num,
                    'controller': motor_info['controller_name'],
                    'channel': motor_info['channel_letter'],
                    'address': address,
                    'encoder_position': enc_result[1],
                    'encoder_velocity': speed_result[1],
                    'instantaneous_velocity': ispeed_result[1],
                    'voltage': voltage_result[1] / 10.0,  # Convert from 0.1V units
                    'current': current / 10.0,  # Convert from 0.1A units
                    'error': error_result[1],
                    'temperature': temp_result[1] / 10.0,  # Convert from 0.1°C units
                    'pid_settings': pid_data,
                    'timestamp': time.time()
                }
            else:
                print(f"Failed to read data from motor {motor_num}")
                return None
                
        except Exception as e:
            print(f"Error reading motor {motor_num} data: {e}")
            self.log_error("get_motor_data", f"Motor {motor_num}: {str(e)}")
            return None
    
    def set_velocity(self, motor_num: int, velocity: float) -> bool:
        """
        Set motor velocity in encoder counts per second
        Args:
            motor_num: Motor number (1, 2, or 3)
            velocity: Velocity in encoder counts per second
        Returns:
            bool: True if successful
        """
        try:
            if motor_num not in self.motor_data:
                print(f"Motor {motor_num} not configured")
                return False
            
            motor_info = self.motor_data[motor_num]
            controller = motor_info['controller']
            address = motor_info['address']
            channel = motor_info['channel']
            
            if not controller:
                print(f"Controller not available for motor {motor_num}")
                return False
            
            # Set velocity using RoboClaw 3.py methods
            if channel == 1:  # Motor A
                result = controller.SpeedM1(address, int(velocity))
            else:  # Motor B
                result = controller.SpeedM2(address, int(velocity))
            
            if result and result[0]:
                print(f"✓ Set motor {motor_num} velocity to {velocity:.0f} counts/s")
                return True
            else:
                print(f"✗ Failed to set motor {motor_num} velocity")
                return False
                
        except Exception as e:
            print(f"Error setting motor {motor_num} velocity: {e}")
            self.log_error("set_velocity", f"Motor {motor_num}: {str(e)}")
            return False
    
    def close(self):
        """Close all controller connections"""
        try:
            if self.rc1:
                self.rc1.Close()
            if self.rc2:
                self.rc2.Close()
            self.connected = False
            print("✓ RoboClaw connections closed")
        except Exception as e:
            print(f"Error closing connections: {e}")
    
    def compare_with_reference_settings(self, current_settings: Dict[str, Any]) -> Dict[str, Any]:
        """Compare current settings with reference settings from platform_config.json"""
        differences = {}
        
        def compare_nested_dicts(current: Dict[str, Any], reference: Dict[str, Any], path: str = "") -> None:
            for key, ref_value in reference.items():
                current_path = f"{path}.{key}" if path else key
                
                if key not in current:
                    differences[current_path] = {
                        'current': None,
                        'reference': ref_value,
                        'status': 'missing'
                    }
                elif isinstance(ref_value, dict) and isinstance(current[key], dict):
                    compare_nested_dicts(current[key], ref_value, current_path)
                elif current[key] != ref_value:
                    differences[current_path] = {
                        'current': current[key],
                        'reference': ref_value,
                        'status': 'different'
                    }
        
        # Get reference settings from platform_config.json
        reference_settings = self.config.get('roboclaw_settings_reference', {}).get('settings', {})
        
        if reference_settings:
            compare_nested_dicts(current_settings, reference_settings)
        
        return differences
    
    def print_settings_comparison(self, differences: Dict[str, Any], comparison_type: str = "reference"):
        """Print settings comparison in a readable format"""
        print(f"\nSettings Comparison ({comparison_type}):")
        print("-" * 80)
        
        for path, diff in differences.items():
            status = diff['status']
            current = diff['current']
            reference = diff['reference']
            
            if status == 'missing':
                print(f"✗ {path}: Missing (should be {reference})")
            elif status == 'different':
                print(f"⚠ {path}: {current} (should be {reference})")
        
        print("-" * 80)
    
    def restore_settings_from_backup(self, backup_file: str) -> bool:
        """Restore settings from a backup file"""
        try:
            print(f"\n=== Restoring Settings from {backup_file} ===")
            
            backup_path = os.path.join(self.backup_dir, backup_file)
            if not os.path.exists(backup_path):
                print(f"Backup file {backup_file} not found")
                return False
            
            with open(backup_path, 'r') as f:
                backup_settings = json.load(f)
            
            for controller_name, settings in backup_settings.items():
                if controller_name in self.controller_info and self.controller_info[controller_name]['connected']:
                    print(f"\nRestoring settings for {controller_name}...")
                    
                    # Get controller instance
                    if controller_name == 'rc1':
                        rc = self.rc1
                    elif controller_name == 'rc2':
                        rc = self.rc2
                    else:
                        continue
                    
                    address = self.controller_info[controller_name]['address']
                    
                    # Restore velocity PID settings
                    if 'velocity_pid' in settings:
                        pid_settings = settings['velocity_pid']
                        for motor_key, motor_pid in pid_settings.items():
                            if motor_key in ['motor1', 'motor2']:
                                channel = 1 if motor_key == 'motor1' else 2
                                p = int(motor_pid['p'] * 65536)  # Convert to scaled value
                                i = int(motor_pid['i'] * 65536)
                                d = int(motor_pid['d'] * 65536)
                                qpps = motor_pid['qpps']
                                
                                if channel == 1:
                                    result = rc.SetM1VelocityPID(address, p, i, d, qpps)
                                else:
                                    result = rc.SetM2VelocityPID(address, p, i, d, qpps)
                                
                                if result and result[0]:
                                    print(f"  ✓ Restored {motor_key} velocity PID")
                                else:
                                    print(f"  ✗ Failed to restore {motor_key} velocity PID")
                    
                    # Restore voltage limits
                    if 'voltage_limits' in settings:
                        voltage_settings = settings['voltage_limits']
                        if 'main_battery' in voltage_settings:
                            main_batt = voltage_settings['main_battery']
                            min_voltage = main_batt['min']
                            max_voltage = main_batt['max']
                            result = rc.SetMainVoltages(address, min_voltage, max_voltage)
                            if result and result[0]:
                                print(f"  ✓ Restored main battery voltage limits")
                            else:
                                print(f"  ✗ Failed to restore main battery voltage limits")
                    
                    # Restore current limits
                    if 'current_limits' in settings:
                        current_settings = settings['current_limits']
                        for motor_key, max_current in current_settings.items():
                            if motor_key in ['motor1', 'motor2']:
                                channel = 1 if motor_key == 'motor1' else 2
                                if channel == 1:
                                    result = rc.SetM1MaxCurrent(address, max_current)
                                else:
                                    result = rc.SetM2MaxCurrent(address, max_current)
                                
                                if result and result[0]:
                                    print(f"  ✓ Restored {motor_key} current limit")
                                else:
                                    print(f"  ✗ Failed to restore {motor_key} current limit")
            
            print("✓ Settings restoration completed")
            return True
            
        except Exception as e:
            print(f"Error restoring settings: {e}")
            self.log_error("restore_settings_from_backup", str(e))
            return False
    
    def update_platform_config(self, controller_name: str, new_settings: Dict[str, Any]) -> bool:
        """Update platform_config.json with new settings"""
        try:
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'platform_config.json')
            
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Update settings in config
            if 'roboclaw_settings_reference' not in config:
                config['roboclaw_settings_reference'] = {}
            
            if 'settings' not in config['roboclaw_settings_reference']:
                config['roboclaw_settings_reference']['settings'] = {}
            
            config['roboclaw_settings_reference']['settings'].update(new_settings)
            config['roboclaw_settings_reference']['last_updated'] = datetime.now().isoformat()
            config['roboclaw_settings_reference']['updated_by'] = 'roboclaw_interface'
            
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=4)
            
            return True
            
        except Exception as e:
            print(f"Error updating platform config: {e}")
            self.log_error("update_platform_config", str(e))
            return False
    
    def prompt_for_connection_settings(self, controller_name: str, current_settings: Dict[str, Any]) -> Dict[str, Any]:
        """Prompt user for new connection settings"""
        print(f"\nEnter new settings for {controller_name}:")
        
        new_settings = {}
        
        # Port
        current_port = current_settings.get('port', '')
        new_port = input(f"Port (current: {current_port}): ").strip()
        if new_port:
            new_settings['port'] = new_port
        
        # Address
        current_address = current_settings.get('address', 0x80)
        new_address = input(f"Address (current: 0x{current_address:02X}): ").strip()
        if new_address:
            if new_address.startswith('0x'):
                new_settings['address'] = int(new_address, 16)
            else:
                new_settings['address'] = int(new_address)
        
        # Baudrate (for RS232 mode)
        if self.use_rs232_fallback:
            current_baudrate = current_settings.get('baudrate_primary', 460800)
            new_baudrate = input(f"Baudrate (current: {current_baudrate}): ").strip()
            if new_baudrate:
                new_settings['baudrate_primary'] = int(new_baudrate)
        
        return new_settings
    
    def log_error(self, test_name: str, error: str):
        """Log an error for later reporting"""
        self.errors.append({
            'test': test_name,
            'error': error,
            'timestamp': datetime.now().isoformat()
        })

class RoboclawSettings:
    def __init__(self, settings_file: Optional[str] = None):
        # Use roboclaw_settings_backup directory for settings files
        if settings_file is None:
            backup_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tests', 'roboclaw_settings_backup')
            os.makedirs(backup_dir, exist_ok=True)
            settings_file = os.path.join(backup_dir, "roboclaw_settings.json")
        
        self.settings_file = settings_file
        self.current_settings: Dict[str, Any] = {}
        self.previous_settings: Dict[str, Any] = {}
        
    def read_current_settings(self, rc: Roboclaw, address: int) -> Dict[str, Any]:
        """Read all current settings from a Roboclaw controller"""
        settings = {
            "address": address,  # Store as integer
            "timestamp": datetime.now().isoformat(),
            "velocity_pid": {},
            "position_pid": {},
            "voltage_limits": {},
            "current_limits": {},
            "acceleration": {},
            "encoder_settings": {},
            "pwm_settings": {},
            "deadband": {},
            "pin_functions": {},
            "configuration": {},
            "encoder_counts": {},
            "status_monitoring": {}
        }
        
        try:
            print(f"Reading settings from controller at address 0x{address:02X}...")
            
            # Read Velocity PID settings for both motors
            for motor in [1, 2]:
                if motor == 1:
                    result = rc.ReadM1VelocityPID(address)
                else:
                    result = rc.ReadM2VelocityPID(address)
                
                if result[0]:  # Check if read was successful
                    settings["velocity_pid"][f"motor{motor}"] = {
                        "p": result[1],
                        "i": result[2],
                        "d": result[3],
                        "qpps": result[4]
                    }
                time.sleep(0.01)  # Small delay between commands
            
            # Read Position PID settings for both motors
            for motor in [1, 2]:
                if motor == 1:
                    result = rc.ReadM1PositionPID(address)
                else:
                    result = rc.ReadM2PositionPID(address)
                
                if result[0]:  # Check if read was successful
                    settings["position_pid"][f"motor{motor}"] = {
                        "kp": result[1] if len(result) > 1 else 0,
                        "ki": result[2] if len(result) > 2 else 0,
                        "kd": result[3] if len(result) > 3 else 0,
                        "kimax": result[4] if len(result) > 4 else 0,
                        "deadzone": result[5] if len(result) > 5 else 0,
                        "min": result[6] if len(result) > 6 else 0,
                        "max": result[7] if len(result) > 7 else 0
                    }
                time.sleep(0.01)  # Small delay between commands
            
            # Read voltage limits
            main_voltage_result = rc.ReadMinMaxMainVoltages(address)
            time.sleep(0.01)
            logic_voltage_result = rc.ReadMinMaxLogicVoltages(address)
            time.sleep(0.01)
            
            if main_voltage_result[0]:
                settings["voltage_limits"]["main_battery"] = {
                    "min": main_voltage_result[1],
                    "max": main_voltage_result[2]
                }
            
            if logic_voltage_result[0]:
                settings["voltage_limits"]["logic_battery"] = {
                    "min": logic_voltage_result[1],
                    "max": logic_voltage_result[2]
                }
            
            # Read current limits
            for motor in [1, 2]:
                if motor == 1:
                    result = rc.ReadM1MaxCurrent(address)
                else:
                    result = rc.ReadM2MaxCurrent(address)
                
                if result[0]:
                    settings["current_limits"][f"motor{motor}"] = result[1]
                time.sleep(0.01)  # Small delay between commands
            
            # Read acceleration settings (using default values since no direct read function)
            settings["acceleration"]["motor1"] = 100000  # Default value
            settings["acceleration"]["motor2"] = 100000  # Default value
            
            # Read encoder settings
            encoder_modes_result = rc.ReadEncoderModes(address)
            time.sleep(0.01)
            if encoder_modes_result[0]:
                settings["encoder_settings"]["motor1"] = encoder_modes_result[1] if len(encoder_modes_result) > 1 else 0
                settings["encoder_settings"]["motor2"] = encoder_modes_result[2] if len(encoder_modes_result) > 2 else 0
            
            # Read PWM mode
            pwm_mode_result = rc.ReadPWMMode(address)
            time.sleep(0.01)
            if pwm_mode_result[0]:
                settings["pwm_settings"]["pwm_mode"] = pwm_mode_result[1]
            
            # Read deadband settings
            deadband_result = rc.GetDeadBand(address)
            time.sleep(0.01)
            if deadband_result[0]:
                settings["deadband"]["min"] = deadband_result[1]
                settings["deadband"]["max"] = deadband_result[2]
            
            # Read pin functions
            pin_functions_result = rc.ReadPinFunctions(address)
            time.sleep(0.01)
            if pin_functions_result[0]:
                settings["pin_functions"]["s3_mode"] = pin_functions_result[1] if len(pin_functions_result) > 1 else 0
                settings["pin_functions"]["s4_mode"] = pin_functions_result[2] if len(pin_functions_result) > 2 else 0
                settings["pin_functions"]["s5_mode"] = pin_functions_result[3] if len(pin_functions_result) > 3 else 0
            
            # Read configuration
            config_result = rc.GetConfig(address)
            time.sleep(0.01)
            if config_result[0]:
                settings["configuration"]["config"] = config_result[1]
            
            # Read encoder counts
            for motor in [1, 2]:
                if motor == 1:
                    result = rc.ReadEncM1(address)
                else:
                    result = rc.ReadEncM2(address)
                
                if result[0]:
                    settings["encoder_counts"][f"motor{motor}"] = result[1]
                time.sleep(0.01)  # Small delay between commands
            
            # Read status monitoring values (real-time) - batch these together
            print("  Reading real-time status values...")
            main_voltage_result = rc.ReadMainBatteryVoltage(address)
            time.sleep(0.01)
            logic_voltage_result = rc.ReadLogicBatteryVoltage(address)
            time.sleep(0.01)
            temp_result = rc.ReadTemp(address)
            time.sleep(0.01)
            error_result = rc.ReadError(address)
            time.sleep(0.01)
            currents_result = rc.ReadCurrents(address)
            time.sleep(0.01)
            speed1_result = rc.ReadSpeedM1(address)
            time.sleep(0.01)
            speed2_result = rc.ReadSpeedM2(address)
            time.sleep(0.01)
            enc1_result = rc.ReadEncM1(address)
            time.sleep(0.01)
            enc2_result = rc.ReadEncM2(address)
            
            settings["status_monitoring"] = {
                "main_voltage": main_voltage_result[1] if main_voltage_result[0] else None,
                "logic_voltage": logic_voltage_result[1] if logic_voltage_result[0] else None,
                "temperature": temp_result[1] if temp_result[0] else None,
                "error_status": error_result[1] if error_result[0] else None,
                "motor1_current": list(currents_result)[1] if currents_result[0] and len(currents_result) > 1 else None,
                "motor2_current": list(currents_result)[2] if currents_result[0] and len(currents_result) > 2 else None,
                "motor3_current": None,  # Motor 3 is on a different controller
                "motor1_speed": speed1_result[1] if speed1_result[0] else None,
                "motor2_speed": speed2_result[1] if speed2_result[0] else None,
                "motor3_speed": None,  # Motor 3 is on a different controller
                "motor1_position": enc1_result[1] if enc1_result[0] else None,
                "motor2_position": enc2_result[1] if enc2_result[0] else None,
                "motor3_position": None  # Motor 3 is on a different controller
            }
            
            print(f"  Settings reading completed for controller 0x{address:02X}")
            
        except Exception as e:
            print(f"Error reading settings: {str(e)}")
            
        return settings
    
    def save_settings(self, settings: Dict[str, Any], filename: Optional[str] = None) -> None:
        """Save settings to a JSON file"""
        if filename is None:
            filename = self.settings_file
            
        with open(filename, 'w') as f:
            json.dump(settings, f, indent=4)
            
    def load_settings(self, filename: Optional[str] = None) -> Dict[str, Any]:
        """Load settings from a JSON file"""
        if filename is None:
            filename = self.settings_file
            
        try:
            with open(filename, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Settings file {filename} not found")
            return {}
            
    def compare_settings(self, current: Dict[str, Any], previous: Dict[str, Any]) -> Dict[str, Any]:
        """Compare current settings with previous settings and return differences"""
        differences = {}
        
        def compare_dicts(dict1: Dict[str, Any], dict2: Dict[str, Any], path: str = "") -> None:
            for key in set(dict1.keys()) | set(dict2.keys()):
                new_path = f"{path}.{key}" if path else key
                
                if key not in dict1:
                    differences[new_path] = {"previous": dict2[key], "current": None}
                elif key not in dict2:
                    differences[new_path] = {"previous": None, "current": dict1[key]}
                elif dict1[key] != dict2[key]:
                    if isinstance(dict1[key], dict) and isinstance(dict2[key], dict):
                        compare_dicts(dict1[key], dict2[key], new_path)
                    else:
                        differences[new_path] = {"previous": dict2[key], "current": dict1[key]}
        
        compare_dicts(current, previous)
        return differences
    
    def prepare_settings_file(self, differences: Dict[str, Any], output_file: str) -> None:
        """Prepare a new settings file with confirmed changes"""
        new_settings = self.current_settings.copy()
        
        for path, values in differences.items():
            if values["current"] is not None:  # Only include confirmed changes
                keys = path.split('.')
                current = new_settings
                for key in keys[:-1]:
                    current = current[key]
                current[keys[-1]] = values["current"]
        
        self.save_settings(new_settings, output_file)
        
    def backup_current_settings(self) -> None:
        """Create a backup of current settings with timestamp"""
        if not self.current_settings:
            return
            
        # Use roboclaw_settings_backup directory for backups
        backup_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tests', 'roboclaw_settings_backup')
        os.makedirs(backup_dir, exist_ok=True)
        
        # Create timestamp with hours, minutes, and seconds
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"roboclaw_settings_{timestamp}.json"
        backup_file_path = os.path.join(backup_dir, backup_filename)
        
        self.save_settings(self.current_settings, backup_file_path)
        print(f"Settings backed up to {backup_file_path}") 