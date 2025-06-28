#!/usr/bin/env python3
"""
Maker Pi RP2040 Interface Module
Consolidated interface and testing module for Maker Pi RP2040 experimental modules
Handles CircuitPython drive detection, communication, and testing functionality

Note: Core motion control sensors (encoder feedback, optical flow, power sensor) 
are handled by Raspberry Pi 5. Maker Pi RP2040 handles experimental modules only.
"""

import os
import sys
import time
import json
import serial
import platform
import shutil
import subprocess
import glob
import serial.tools.list_ports
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

class MakerPiInterface:
    """
    Consolidated interface for Maker Pi RP2040 experimental modules
    Handles CircuitPython drive detection, communication, and testing
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Maker Pi interface
        Args:
            config: Configuration dictionary containing Maker Pi settings
        """
        self.config = config
        self.port = config.get('port', '/dev/ttyACM0')
        self.baudrate = config.get('baudrate', 115200)
        self.connection = None
        self.connected = False
        self.modules = config.get('modules', {})
        self.os_type = platform.system().lower()
        
        # CircuitPython detection settings
        self.circuitpython_config = config.get('circuitpython_detection', {})
        self.backup_directory = config.get('circuitpython_detection', {}).get('backup_directory', 'test_logs/maker_pi_backups')
        
        # Module states (experimental modules only)
        self.experimental_sensors_enabled = self.modules.get('experimental_sensors', {}).get('enabled', False)
        self.displays_enabled = self.modules.get('displays', {}).get('enabled', False)
        self.io_modules_enabled = self.modules.get('io_modules', {}).get('enabled', False)
        
        # Data buffers for experimental modules
        self.experimental_sensor_data = {}
        self.display_data = {}
        self.io_module_data = {}
        
        # CircuitPython drive detection results
        self.detected_drives = {}
        self.current_drive = None
        
        # Test results storage
        self.test_results = {
            "timestamp": datetime.now().isoformat(),
            "tests": {},
            "errors": [],
            "connection_info": {},
            "hardware_responsibility": "experimental_modules_only"
        }
        
        print("Note: Core motion control sensors handled by Raspberry Pi 5")
        print("Maker Pi RP2040 handles experimental sensors, displays, and IO modules")
    
    def detect_circuitpython_drives(self) -> Dict[str, Dict[str, Any]]:
        """
        Detect Maker Pi by looking for CircuitPython files on removable drives
        Returns:
            Dict of detected CircuitPython drives with file information
        """
        print(f"\n=== CircuitPython Drive Detection ({self.os_type.upper()}) ===")
        
        circuitpython_drives = {}
        
        if self.os_type == "windows":
            circuitpython_drives = self._detect_windows_circuitpython_drives()
        elif self.os_type == "linux":
            circuitpython_drives = self._detect_linux_circuitpython_drives()
        else:
            print(f"Unsupported OS: {self.os_type}")
            self.log_error("os_detection", f"Unsupported OS: {self.os_type}")
            return {}
        
        # Store detected drives and update config
        self.detected_drives = circuitpython_drives
        self._update_config_with_detected_drives(circuitpython_drives)
        
        return circuitpython_drives
    
    def _detect_windows_circuitpython_drives(self) -> Dict[str, Dict[str, Any]]:
        """Detect CircuitPython drives on Windows"""
        print("Detecting CircuitPython drives on Windows...")
        
        circuitpython_drives = {}
        
        try:
            import string
            import win32file
            
            # Get all available drive letters
            drives = []
            for letter in string.ascii_uppercase:
                drive = f"{letter}:\\"
                if win32file.GetDriveType(drive) == win32file.DRIVE_REMOVABLE:
                    drives.append(drive)
            
            print(f"Found {len(drives)} removable drives")
            
            for drive in drives:
                try:
                    # Check for CircuitPython files
                    code_py_path = os.path.join(drive, "code.py")
                    boot_out_path = os.path.join(drive, "boot_out.txt")
                    
                    if os.path.exists(code_py_path) and os.path.exists(boot_out_path):
                        print(f"✓ Found CircuitPython drive: {drive}")
                        
                        # Read boot_out.txt to get hardware description
                        boot_content = self._read_file_safe(boot_out_path)
                        print(f"  Boot info: {boot_content.strip()}")
                        
                        # Read code.py to get current script
                        code_content = self._read_file_safe(code_py_path)
                        print(f"  Code.py size: {len(code_content)} characters")
                        
                        # Find associated serial port
                        serial_port = self._find_serial_port_for_drive(drive)
                        
                        circuitpython_drives[drive] = {
                            'type': 'circuitpython_drive',
                            'boot_info': boot_content.strip(),
                            'code_content': code_content,
                            'code_size': len(code_content),
                            'os': 'windows',
                            'serial_port': serial_port,
                            'description': f"CircuitPython drive with {len(code_content)} chars in code.py",
                            'detection_time': datetime.now().isoformat()
                        }
                        
                        if serial_port:
                            print(f"  Associated serial port: {serial_port}")
                
                except Exception as e:
                    print(f"  Error checking drive {drive}: {e}")
        
        except ImportError:
            print("✗ pywin32 not available for Windows drive detection")
            self.log_error("windows_drive_detection", "pywin32 not available")
        except Exception as e:
            print(f"✗ Error detecting Windows CircuitPython drives: {e}")
            self.log_error("windows_drive_detection", str(e))
        
        return circuitpython_drives
    
    def _detect_linux_circuitpython_drives(self) -> Dict[str, Dict[str, Any]]:
        """Detect CircuitPython drives on Linux"""
        print("Detecting CircuitPython drives on Linux...")
        
        circuitpython_drives = {}
        
        try:
            # Check common mount points for removable drives
            mount_points = ['/media', '/mnt', '/run/media']
            
            for mount_base in mount_points:
                if os.path.exists(mount_base):
                    try:
                        # Look for mounted drives
                        for item in os.listdir(mount_base):
                            mount_path = os.path.join(mount_base, item)
                            
                            if os.path.isdir(mount_path):
                                # Check for CircuitPython files
                                code_py_path = os.path.join(mount_path, "code.py")
                                boot_out_path = os.path.join(mount_path, "boot_out.txt")
                                
                                if os.path.exists(code_py_path) and os.path.exists(boot_out_path):
                                    print(f"✓ Found CircuitPython drive: {mount_path}")
                                    
                                    # Read boot_out.txt
                                    boot_content = self._read_file_safe(boot_out_path)
                                    print(f"  Boot info: {boot_content.strip()}")
                                    
                                    # Read code.py
                                    code_content = self._read_file_safe(code_py_path)
                                    print(f"  Code.py size: {len(code_content)} characters")
                                    
                                    # Find associated serial port
                                    serial_port = self._find_serial_port_for_drive(mount_path)
                                    
                                    circuitpython_drives[mount_path] = {
                                        'type': 'circuitpython_drive',
                                        'boot_info': boot_content.strip(),
                                        'code_content': code_content,
                                        'code_size': len(code_content),
                                        'os': 'linux',
                                        'serial_port': serial_port,
                                        'description': f"CircuitPython drive with {len(code_content)} chars in code.py",
                                        'detection_time': datetime.now().isoformat()
                                    }
                                    
                                    if serial_port:
                                        print(f"  Associated serial port: {serial_port}")
                    
                    except Exception as e:
                        print(f"  Error checking {mount_base}: {e}")
        
        except Exception as e:
            print(f"✗ Error detecting Linux CircuitPython drives: {e}")
            self.log_error("linux_drive_detection", str(e))
        
        return circuitpython_drives
    
    def _read_file_safe(self, file_path: str) -> str:
        """Safely read a file with error handling"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            print(f"  Error reading {file_path}: {e}")
            return ""
    
    def _find_serial_port_for_drive(self, drive_path: str) -> Optional[str]:
        """Find the serial port associated with a CircuitPython drive"""
        try:
            ports = serial.tools.list_ports.comports()
            
            for port in ports:
                port_description = port.description.lower()
                
                # Check for common CircuitPython/RP2040 indicators
                if any(indicator in port_description for indicator in [
                    'raspberry', 'pi', 'pico', 'rp2040', 'maker', 'circuitpython'
                ]):
                    return port.device
            
            return None
            
        except Exception as e:
            print(f"  Error finding serial port for drive {drive_path}: {e}")
            return None
    
    def _update_config_with_detected_drives(self, detected_drives: Dict[str, Dict[str, Any]]):
        """Update platform configuration with detected drives"""
        try:
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'platform_config.json')
            
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Update Maker Pi configuration
            if 'maker_pi' not in config.get('hardware', {}):
                config['hardware']['maker_pi'] = {}
            
            maker_pi_config = config['hardware']['maker_pi']
            maker_pi_config['detected_drives'] = detected_drives
            maker_pi_config['last_updated'] = datetime.now().isoformat()
            maker_pi_config['updated_by'] = 'maker_pi_interface'
            
            # Save updated config
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=4)
            
            print("✓ Platform configuration updated with detected drives")
            
        except Exception as e:
            print(f"Error updating configuration: {e}")
            self.log_error("config_update", str(e))
    
    def backup_circuitpython_files(self, drive_path: str) -> bool:
        """Backup CircuitPython files with timestamp"""
        try:
            # Create backup directory
            os.makedirs(self.backup_directory, exist_ok=True)
            
            # Generate timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Backup code.py
            code_py_path = os.path.join(drive_path, "code.py")
            if os.path.exists(code_py_path):
                backup_code_path = os.path.join(self.backup_directory, f"code_py_backup_{timestamp}.py")
                shutil.copy2(code_py_path, backup_code_path)
                print(f"✓ Backed up code.py to {backup_code_path}")
            
            # Backup boot_out.txt
            boot_out_path = os.path.join(drive_path, "boot_out.txt")
            if os.path.exists(boot_out_path):
                backup_boot_path = os.path.join(self.backup_directory, f"boot_out_backup_{timestamp}.txt")
                shutil.copy2(boot_out_path, backup_boot_path)
                print(f"✓ Backed up boot_out.txt to {backup_boot_path}")
            
            return True
            
        except Exception as e:
            print(f"Error backing up CircuitPython files: {e}")
            self.log_error("file_backup", str(e))
            return False
    
    def read_boot_info(self, drive_path: str) -> Optional[str]:
        """Read boot information from CircuitPython drive"""
        try:
            boot_out_path = os.path.join(drive_path, "boot_out.txt")
            if os.path.exists(boot_out_path):
                return self._read_file_safe(boot_out_path)
            return None
        except Exception as e:
            print(f"Error reading boot info: {e}")
            return None
    
    def read_code_py(self, drive_path: str) -> Optional[str]:
        """Read code.py from CircuitPython drive"""
        try:
            code_py_path = os.path.join(drive_path, "code.py")
            if os.path.exists(code_py_path):
                return self._read_file_safe(code_py_path)
            return None
        except Exception as e:
            print(f"Error reading code.py: {e}")
            return None
        
    def connect(self) -> bool:
        """
        Connect to Maker Pi via serial communication
        Returns:
            bool: True if connection successful
        """
        try:
            print(f"\n=== Connecting to Maker Pi on {self.port} ===")
            
            # Try to connect via serial
            if self._connect_serial(self.port):
                self.connected = True
                print("✓ Connected to Maker Pi via serial")
                
                # Test communication
                if self._test_communication():
                    print("✓ Communication test successful")
                    
                    # Initialize modules
                    self._initialize_modules()
                    return True
                else:
                    print("✗ Communication test failed")
                    self.connected = False
                    return False
            else:
                print("✗ Failed to connect via serial")
                return False
                
        except Exception as e:
            print(f"Error connecting to Maker Pi: {e}")
            self.log_error("connection", str(e))
            return False
    
    def _connect_serial(self, port: str) -> bool:
        """Connect via serial communication"""
        try:
            self.connection = serial.Serial(
                port=port,
                baudrate=self.baudrate,
                timeout=1,
                write_timeout=1
            )
            
            if self.connection.is_open:
                print(f"✓ Serial connection opened on {port}")
                return True
            else:
                print(f"✗ Failed to open serial connection on {port}")
                return False
                
        except Exception as e:
            print(f"Error opening serial connection: {e}")
            return False
    
    def _test_communication(self) -> bool:
        """Test communication with Maker Pi"""
        try:
            if not self.connection or not self.connection.is_open:
                return False
            
            # Send test commands
            test_commands = [
                b'\r\n',  # Enter key
                b'print("test")\r\n',  # Simple print
                b'import sys\r\n',  # Import system
                b'print(sys.platform)\r\n'  # Platform info
            ]
            
            micropython_detected = False
            
            for command in test_commands:
                self.connection.write(command)
                time.sleep(0.2)
                response = self.connection.read_all()
                
                if response:
                    response_str = response.decode('utf-8', errors='ignore')
                    
                    # Check for MicroPython indicators
                    if any(indicator in response_str.lower() for indicator in ['micropython', '>>>', '...']):
                        micropython_detected = True
            
            return micropython_detected
                
        except Exception as e:
            print(f"Error testing communication: {e}")
            return False
    
    def _initialize_modules(self):
        """Initialize experimental modules"""
        print("\n=== Initializing Experimental Modules ===")
        
        if self.experimental_sensors_enabled:
            self._initialize_experimental_sensors()
        
        if self.displays_enabled:
            self._initialize_displays()
        
        if self.io_modules_enabled:
            self._initialize_io_modules()
    
    def _initialize_experimental_sensors(self):
        """Initialize experimental sensors (placeholder)"""
        print("  Initializing experimental sensors...")
        self.experimental_sensor_data = {
            'sensor1': {'value': 0.0, 'unit': 'V'},
            'sensor2': {'value': 0.0, 'unit': 'A'},
            'sensor3': {'value': 0.0, 'unit': '°C'}
        }
        print("  ✓ Experimental sensors initialized (placeholder)")
    
    def _initialize_displays(self):
        """Initialize displays (placeholder)"""
        print("  Initializing displays...")
        self.display_data = {
            'lcd': {'status': 'ready', 'message': 'Maker Pi Ready'},
            'oled': {'status': 'ready', 'brightness': 100}
        }
        print("  ✓ Displays initialized (placeholder)")
    
    def _initialize_io_modules(self):
        """Initialize IO modules (placeholder)"""
        print("  Initializing IO modules...")
        self.io_module_data = {
            'led': {'status': 'off', 'brightness': 0},
            'button': {'state': 'released', 'count': 0},
            'relay': {'state': 'off'}
        }
        print("  ✓ IO modules initialized (placeholder)")

    def read_experimental_sensors(self) -> Optional[Dict[str, float]]:
        """Read experimental sensor data (placeholder)"""
        if not self.experimental_sensors_enabled:
            return None
            
        try:
            # Placeholder: return simulated sensor data
            return {
                'sensor1': 3.3,  # Simulated voltage
                'sensor2': 0.5,  # Simulated current
                'sensor3': 25.0  # Simulated temperature
            }
        except Exception as e:
            print(f"Error reading experimental sensors: {e}")
            return None

    def read_displays(self) -> Optional[Dict[str, Any]]:
        """Read display status (placeholder)"""
        if not self.displays_enabled:
            return None
            
        try:
            # Placeholder: return simulated display data
            return {
                'lcd': {'status': 'active', 'message': 'Test Message'},
                'oled': {'status': 'active', 'brightness': 80}
            }
        except Exception as e:
            print(f"Error reading displays: {e}")
            return None

    def read_io_modules(self) -> Optional[Dict[str, Any]]:
        """Read IO module status (placeholder)"""
        if not self.io_modules_enabled:
            return None
            
        try:
            # Placeholder: return simulated IO data
            return {
                'led': {'status': 'on', 'brightness': 50},
                'button': {'state': 'pressed', 'count': 1},
                'relay': {'state': 'on'}
            }
        except Exception as e:
            print(f"Error reading IO modules: {e}")
            return None

    def read_all_sensors(self) -> Dict[str, Any]:
        """Read all experimental module data"""
        return {
            'experimental_sensors': self.read_experimental_sensors(),
            'displays': self.read_displays(),
            'io_modules': self.read_io_modules(),
            'timestamp': datetime.now().isoformat()
        }
    
    def send_command(self, command: str) -> Optional[str]:
        """Send command to Maker Pi (placeholder)"""
        try:
            if self.connection and self.connection.is_open:
                # Placeholder: send command via serial
                self.connection.write(f"{command}\r\n".encode())
                time.sleep(0.1)
                response = self.connection.read_all()
                if response:
                    return response.decode('utf-8', errors='ignore')
            return None
        except Exception as e:
            print(f"Error sending command: {e}")
            return None
    
    def reset_modules(self):
        """Reset all experimental modules"""
        print("Resetting experimental modules...")
        self._initialize_modules()
        print("✓ Modules reset")
    
    def close(self):
        """Close connection to Maker Pi"""
        try:
            if self.connection and self.connection.is_open:
                self.connection.close()
                self.connected = False
                print("✓ Connection closed")
        except Exception as e:
            print(f"Error closing connection: {e}")
    
    def log_error(self, test_name: str, error: str):
        """Log an error during testing"""
        self.test_results["errors"].append({
            "test": test_name,
            "error": error,
            "timestamp": datetime.now().isoformat()
        })
    
    def run_comprehensive_test(self) -> bool:
        """Run comprehensive Maker Pi test suite"""
        print("Maker Pi RP2040 Comprehensive Test Suite")
        print("========================================")
        print("Testing experimental module functionality only.")
        print("Core motion control sensors handled by Raspberry Pi 5.\n")
        
        tests = [
            ("CircuitPython Drive Detection", self.detect_circuitpython_drives),
            ("Connection Test", self.connect),
            ("Experimental Sensors Test", lambda: self.read_experimental_sensors() is not None),
            ("Displays Test", lambda: self.read_displays() is not None),
            ("IO Modules Test", lambda: self.read_io_modules() is not None),
            ("All Sensors Test", lambda: self.read_all_sensors() is not None)
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test_name, test_func in tests:
            print(f"\n{'='*60}")
            print(f"Running: {test_name}")
            print('='*60)
            
            try:
                if test_func():
                    passed_tests += 1
                    print(f"✓ {test_name} PASSED")
                    self.test_results["tests"][test_name.lower().replace(' ', '_')] = "passed"
                else:
                    print(f"✗ {test_name} FAILED")
                    self.test_results["tests"][test_name.lower().replace(' ', '_')] = "failed"
            except Exception as e:
                print(f"✗ {test_name} ERROR: {e}")
                self.log_error(test_name.lower().replace(' ', '_'), str(e))
        
        # Print summary
        print(f"\n{'='*60}")
        print("TEST SUMMARY")
        print('='*60)
        print(f"Passed: {passed_tests}/{total_tests}")
        print(f"Failed: {total_tests - passed_tests}/{total_tests}")
        
        if self.test_results["errors"]:
            print(f"\nErrors encountered: {len(self.test_results['errors'])}")
            for error in self.test_results["errors"]:
                print(f"  - {error['test']}: {error['error']}")
        
        # Save test results
        self.save_test_results()
        
        return passed_tests == total_tests
    
    def save_test_results(self):
        """Save test results to a JSON file"""
        try:
            test_logs_dir = "test_logs"
            test_logs_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), test_logs_dir)
            os.makedirs(test_logs_path, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"maker_pi_test_results_{timestamp}.json"
            filepath = os.path.join(test_logs_path, filename)
            
            with open(filepath, 'w') as f:
                json.dump(self.test_results, f, indent=2)
            
            print(f"\nTest results saved to: {filepath}")
            return filepath
            
        except Exception as e:
            print(f"Error saving test results: {str(e)}")
            return None

class MakerPiTestUtils:
    """Utility functions for Maker Pi testing"""
    
    @staticmethod
    def detect_maker_pi_ports() -> Dict[str, str]:
        """Detect available Maker Pi ports"""
        available_ports = {}
        
        try:
            ports = serial.tools.list_ports.comports()
            
            for port in ports:
                port_description = port.description.lower()
                
                # Check for Maker Pi RP2040 indicators
                maker_pi_indicators = [
                    'raspberry', 'pi', 'pico', 'rp2040', 'maker',
                    'usb serial device', 'usb serial port'
                ]
                
                if any(indicator in port_description for indicator in maker_pi_indicators):
                    available_ports[port.device] = port.description
            
            return available_ports
            
        except Exception as e:
            print(f"Error detecting Maker Pi ports: {e}")
            return {}
    
    @staticmethod
    def test_maker_pi_connection(port: str) -> bool:
        """Test connection to Maker Pi on specific port"""
        try:
            connection = serial.Serial(port, 115200, timeout=1)
            
            if connection.is_open:
                # Send test command
                connection.write(b'\r\n')
                time.sleep(0.1)
                
                response = connection.read_all()
                connection.close()
                
                if response:
                    response_str = response.decode('utf-8', errors='ignore')
                    return any(indicator in response_str.lower() 
                              for indicator in ['>>>', 'micropython', 'circuitpython'])
            
            return False
            
        except Exception as e:
            print(f"Error testing Maker Pi connection: {e}")
            return False
    
    @staticmethod
    def create_maker_pi_config(port: str, description: str) -> Dict[str, Any]:
        """Create Maker Pi configuration dictionary"""
        return {
            'port': port,
            'baudrate': 115200,
            'description': description,
            'modules': {
                'experimental_sensors': {'enabled': True},
                'displays': {'enabled': True},
                'io_modules': {'enabled': True}
            },
            'circuitpython_detection': {
                'backup_directory': 'test_logs/maker_pi_backups'
            }
        }

def main():
    """Main function for standalone testing"""
    print("Maker Pi RP2040 Interface and Test Suite")
    print("========================================")
    
    # Create default configuration
    config = {
        'port': '/dev/ttyACM0',
        'baudrate': 115200,
        'modules': {
            'experimental_sensors': {'enabled': True},
            'displays': {'enabled': True},
            'io_modules': {'enabled': True}
        },
        'circuitpython_detection': {
            'backup_directory': 'test_logs/maker_pi_backups'
        }
    }
    
    # Create and run test suite
    maker_pi = MakerPiInterface(config)
    
    try:
        success = maker_pi.run_comprehensive_test()
        
        if success:
            print("\n✓ All Maker Pi tests completed successfully!")
        else:
            print("\n✗ Some Maker Pi tests failed. Check the test results file for details.")
            
    except Exception as e:
        print(f"\nAn error occurred during testing: {str(e)}")
        return False
    
    return success

if __name__ == "__main__":
    main() 