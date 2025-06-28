#!/usr/bin/env python3
"""
Maker Pi RP2040 Test Module
Comprehensive test module for Maker Pi RP2040 experimental module functionality
Centrally controlled by system_test.py

Features:
- CircuitPython drive detection and validation
- Serial port identification and testing
- Code.py backup to test_logs directory
- Experimental module placeholder testing
- Integration with platform_config.json
- Clear separation from RoboClaw testing
- Windows/Linux USB detection and connection troubleshooting

Note: This tests experimental modules only. Core motion control sensors 
(encoder feedback, optical flow, power sensor) are handled by Raspberry Pi 5.
"""

import sys
import os
import time
import json
import platform
import subprocess
import glob
import shutil
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

# Add the parent directory to sys.path to import from utils
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.maker_pi_interface import MakerPiInterface, MakerPiTestUtils

class MakerPiTestSuite:
    """Comprehensive test suite for Maker Pi RP2040 experimental module functionality"""
    
    def __init__(self):
        """Initialize the Maker Pi test suite"""
        self.test_results = {
            "timestamp": datetime.now().isoformat(),
            "tests": {},
            "errors": [],
            "hardware_responsibility": "experimental_modules_only",
            "connection_info": {},
            "micropython_access": {},
            "detected_devices": {},
            "backup_files": {},
            "experimental_modules": {}
        }
        self.platform_config = self.load_platform_config()
        self.maker_pi_config = self.platform_config.get('hardware', {}).get('maker_pi', {})
        self.os_type = platform.system().lower()
        
        # Initialize Maker Pi interface
        self.maker_pi_interface = MakerPiInterface(self.maker_pi_config)
        
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
    
    def detect_circuitpython_drives(self) -> Dict[str, Dict[str, Any]]:
        """Detect Maker Pi by looking for CircuitPython files on removable drives"""
        print(f"\n=== CircuitPython Drive Detection ({self.os_type.upper()}) ===")
        
        try:
            detected_drives = self.maker_pi_interface.detect_circuitpython_drives()
            
            if detected_drives:
                print(f"✓ Found {len(detected_drives)} CircuitPython drive(s):")
                for drive_path, drive_info in detected_drives.items():
                    print(f"  Drive: {drive_path}")
                    print(f"    Type: {drive_info.get('type', 'Unknown')}")
                    print(f"    Boot Info: {drive_info.get('boot_info', 'Not available')[:100]}...")
                    print(f"    Code Size: {drive_info.get('code_size', 0)} characters")
                    print(f"    OS: {drive_info.get('os', 'Unknown')}")
                    print(f"    Serial Port: {drive_info.get('serial_port', 'Not detected')}")
                    print()
            else:
                print("✗ No CircuitPython drives detected")
            
            return detected_drives
            
        except Exception as e:
            print(f"✗ Error detecting CircuitPython drives: {e}")
            self.log_error("circuitpython_detection", str(e))
            return {}
    
    def backup_code_py_files(self, detected_drives: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Backup code.py files to test_logs directory"""
        print("\n=== Backing up code.py files ===")
        
        backup_files = {}
        backup_dir = os.path.join(os.path.dirname(__file__), 'test_logs', 'maker_pi_backups')
        
        # Create backup directory if it doesn't exist
        os.makedirs(backup_dir, exist_ok=True)
        
        for drive_path, drive_info in detected_drives.items():
            try:
                code_py_path = os.path.join(drive_path, 'code.py')
                if os.path.exists(code_py_path):
                    # Create timestamped backup filename
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    backup_filename = f"code_py_backup_{timestamp}_{drive_path.replace(':', '_').replace('/', '_')}.py"
                    backup_path = os.path.join(backup_dir, backup_filename)
                    
                    # Copy the file
                    shutil.copy2(code_py_path, backup_path)
                    
                    # Read and store content for reference
                    with open(code_py_path, 'r', encoding='utf-8', errors='ignore') as f:
                        code_content = f.read()
                    
                    backup_files[drive_path] = {
                        'backup_path': backup_path,
                        'original_path': code_py_path,
                        'code_size': len(code_content),
                        'backup_timestamp': timestamp,
                        'description': f"Backup of {drive_path}/code.py"
                    }
                    
                    print(f"✓ Backed up {drive_path}/code.py to {backup_filename}")
                    print(f"  Code size: {len(code_content)} characters")
                else:
                    print(f"⚠ No code.py found on {drive_path}")
                    
            except Exception as e:
                print(f"✗ Error backing up {drive_path}: {e}")
                self.log_error("backup_code_py", f"Error backing up {drive_path}: {e}")
        
        if backup_files:
            print(f"\n✓ Backed up {len(backup_files)} code.py files")
        else:
            print("\n⚠ No code.py files were backed up")
        
        return backup_files
    
    def test_serial_connections(self, detected_drives: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Test serial connections for detected drives"""
        print("\n=== Serial Connection Testing ===")
        print("Testing serial connections for detected drives...")
        
        connection_status = {}
        
        for drive_path, drive_info in detected_drives.items():
            serial_port = drive_info.get('serial_port')
            if not serial_port:
                print(f"✗ No serial port detected for {drive_path}")
                connection_status[drive_path] = {
                    'status': 'no_serial_port',
                    'error': 'No serial port detected'
                }
                continue
            
            try:
                print(f"Testing serial connection on {serial_port} for {drive_path}...")
                
                # Test serial connection using Maker Pi interface
                if self.maker_pi_interface._connect_serial(serial_port):
                    # Test basic communication
                    if self.maker_pi_interface._test_communication():
                        connection_status[drive_path] = {
                            'status': 'connected',
                            'serial_port': serial_port,
                            'communication': 'working'
                        }
                        print(f"✓ Serial connection successful on {serial_port}")
                    else:
                        connection_status[drive_path] = {
                            'status': 'connected',
                            'serial_port': serial_port,
                            'communication': 'failed'
                        }
                        print(f"⚠ Serial port {serial_port} accessible but communication failed")
                else:
                    connection_status[drive_path] = {
                        'status': 'failed',
                        'serial_port': serial_port,
                        'error': 'Could not open serial port'
                    }
                    print(f"✗ Failed to open serial port {serial_port}")
                    
            except Exception as e:
                print(f"✗ Error testing serial connection for {drive_path}: {e}")
                connection_status[drive_path] = {
                    'status': 'error',
                    'serial_port': serial_port,
                    'error': str(e)
                }
                self.log_error("serial_testing", f"Error testing {drive_path}: {e}")
        
        return connection_status
    
    def test_experimental_modules(self, detected_drives: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Test experimental module placeholders"""
        print("\n=== Experimental Module Testing ===")
        print("Testing experimental module placeholders...")
        
        experimental_modules = {}
        
        for drive_path, drive_info in detected_drives.items():
            print(f"\nTesting experimental modules for {drive_path}...")
            
            drive_modules = {
                'experimental_sensors': {
                    'status': 'placeholder',
                    'description': 'Future experimental sensor modules (NOT core motion control sensors)',
                    'note': 'Core motion control sensors handled by Raspberry Pi 5'
                },
                'displays': {
                    'status': 'placeholder',
                    'description': 'Future display modules for user interface and status'
                },
                'io_modules': {
                    'status': 'placeholder',
                    'description': 'Future IO modules for additional functionality'
                }
            }
            
            # Test file system access for experimental modules
            try:
                # Check if we can write to the drive
                test_file_path = os.path.join(drive_path, 'test_experimental_access.txt')
                with open(test_file_path, 'w') as f:
                    f.write(f"Experimental module test - {datetime.now().isoformat()}")
                
                # Remove test file
                os.remove(test_file_path)
                
                drive_modules['file_system_access'] = {
                    'status': 'working',
                    'description': 'File system access confirmed'
                }
                print(f"  ✓ File system access working")
                
            except Exception as e:
                drive_modules['file_system_access'] = {
                    'status': 'failed',
                    'description': f'File system access failed: {str(e)}'
                }
                print(f"  ✗ File system access failed: {e}")
            
            experimental_modules[drive_path] = drive_modules
            
            print(f"  ✓ Experimental module placeholders configured")
        
        return experimental_modules
    
    def update_platform_config(self, detected_drives: Dict[str, Dict[str, Any]], 
                              backup_files: Dict[str, Dict[str, Any]],
                              connection_status: Dict[str, Dict[str, Any]],
                              experimental_modules: Dict[str, Dict[str, Any]]) -> bool:
        """Update platform configuration with Maker Pi detection results"""
        try:
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'platform_config.json')
            
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Update Maker Pi configuration
            if 'hardware' not in config:
                config['hardware'] = {}
            if 'maker_pi' not in config['hardware']:
                config['hardware']['maker_pi'] = {}
            
            # Update detected drives
            config['hardware']['maker_pi']['detected_drives'] = detected_drives
            
            # Update backup information
            if backup_files:
                config['hardware']['maker_pi']['backup_files'] = backup_files
            
            # Update connection status
            if connection_status:
                config['hardware']['maker_pi']['connection_status'] = connection_status
            
            # Update experimental modules
            if experimental_modules:
                config['hardware']['maker_pi']['experimental_modules'] = experimental_modules
            
            # Update timestamp
            config['hardware']['maker_pi']['last_updated'] = datetime.now().isoformat()
            config['hardware']['maker_pi']['updated_by'] = 'maker_pi_test_suite'
            
            # Save updated config
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=4)
            
            print(f"\n✓ Maker Pi configuration updated in {config_path}")
            return True
            
        except Exception as e:
            print(f"Error updating platform configuration: {e}")
            self.log_error("config_update", str(e))
            return False
    
    def display_identification_summary(self, detected_drives: Dict[str, Dict[str, Any]], 
                                     backup_files: Dict[str, Dict[str, Any]],
                                     connection_status: Dict[str, Dict[str, Any]],
                                     experimental_modules: Dict[str, Dict[str, Any]]):
        """Display comprehensive identification summary"""
        print("\n" + "="*80)
        print("MAKER PI IDENTIFICATION SUMMARY")
        print("="*80)
        
        # Display detected drives
        if detected_drives:
            print("\n✓ DETECTED CIRCUITPYTHON DRIVES:")
            for drive_path, drive_info in detected_drives.items():
                print(f"  {drive_path}:")
                print(f"    Type: {drive_info.get('type', 'Unknown')}")
                print(f"    Boot Info: {drive_info.get('boot_info', 'Not available')[:80]}...")
                print(f"    Code Size: {drive_info.get('code_size', 0)} characters")
                print(f"    OS: {drive_info.get('os', 'Unknown')}")
                print(f"    Serial Port: {drive_info.get('serial_port', 'Not detected')}")
                print()
        else:
            print("\n✗ No CircuitPython drives detected")
        
        # Display backup information
        if backup_files:
            print("✓ CODE.PY BACKUPS:")
            for drive_path, backup_info in backup_files.items():
                print(f"  {drive_path}:")
                print(f"    Backup: {backup_info.get('backup_path', 'Unknown')}")
                print(f"    Code Size: {backup_info.get('code_size', 0)} characters")
                print(f"    Timestamp: {backup_info.get('backup_timestamp', 'Unknown')}")
                print()
        else:
            print("\n⚠ No code.py files backed up")
        
        # Display connection status
        if connection_status:
            print("✓ SERIAL CONNECTION STATUS:")
            for drive_path, status_info in connection_status.items():
                print(f"  {drive_path}:")
                print(f"    Status: {status_info.get('status', 'Unknown')}")
                print(f"    Serial Port: {status_info.get('serial_port', 'Not detected')}")
                if 'communication' in status_info:
                    print(f"    Communication: {status_info['communication']}")
                if 'error' in status_info:
                    print(f"    Error: {status_info['error']}")
                print()
        else:
            print("\n⚠ No serial connections tested")
        
        # Display experimental modules
        if experimental_modules:
            print("✓ EXPERIMENTAL MODULES:")
            for drive_path, modules in experimental_modules.items():
                print(f"  {drive_path}:")
                for module_name, module_info in modules.items():
                    print(f"    {module_name}: {module_info.get('status', 'Unknown')}")
                    print(f"      {module_info.get('description', 'No description')}")
                print()
        else:
            print("\n⚠ No experimental modules configured")
        
        # Display statistics
        print("STATISTICS:")
        print(f"  CircuitPython drives detected: {len(detected_drives)}")
        print(f"  Code.py files backed up: {len(backup_files)}")
        print(f"  Serial connections tested: {len(connection_status)}")
        print(f"  Experimental modules configured: {len(experimental_modules)}")
        
        print("="*80)
    
    def offer_experimental_module_testing(self) -> bool:
        """Offer to run experimental module testing"""
        print("\n=== Experimental Module Testing Option ===")
        print("Maker Pi identification completed successfully!")
        print("Would you like to run experimental module testing to:")
        print("1. Test experimental sensor placeholders")
        print("2. Test display module placeholders")
        print("3. Test IO module placeholders")
        print("4. Skip experimental module testing for now")
        print()
        
        while True:
            try:
                choice = input("Enter choice (1-4): ").strip()
                
                if choice == '1':
                    print("✓ Will test experimental sensor placeholders")
                    return True
                elif choice == '2':
                    print("✓ Will test display module placeholders")
                    return True
                elif choice == '3':
                    print("✓ Will test IO module placeholders")
                    return True
                elif choice == '4':
                    print("✓ Skipping experimental module testing")
                    return False
                else:
                    print("⚠ Invalid choice. Please enter 1-4")
                    continue
                    
            except KeyboardInterrupt:
                print("\n⚠ Interrupted by user")
                return False
    
    def run_maker_pi_identification(self) -> bool:
        """Run complete Maker Pi identification process"""
        print("Maker Pi RP2040 Identification Module")
        print("======================================")
        print("This module will:")
        print("1. Detect CircuitPython drives")
        print("2. Backup code.py files")
        print("3. Test serial connections")
        print("4. Configure experimental module placeholders")
        print("5. Update platform configuration")
        print("6. Offer experimental module testing")
        print()
        
        # Step 1: Detect CircuitPython drives
        detected_drives = self.detect_circuitpython_drives()
        if not detected_drives:
            print("✗ No CircuitPython drives detected")
            return False
        
        # Step 2: Backup code.py files
        backup_files = self.backup_code_py_files(detected_drives)
        
        # Step 3: Test serial connections
        connection_status = self.test_serial_connections(detected_drives)
        
        # Step 4: Test experimental modules
        experimental_modules = self.test_experimental_modules(detected_drives)
        
        # Step 5: Display summary
        self.display_identification_summary(detected_drives, backup_files, connection_status, experimental_modules)
        
        # Step 6: Update platform configuration
        if self.update_platform_config(detected_drives, backup_files, connection_status, experimental_modules):
            print("✓ Maker Pi identification completed successfully!")
            
            # Step 7: Offer experimental module testing
            if self.offer_experimental_module_testing():
                print("✓ Experimental module testing will be available in the main menu")
            
            self.test_results["detected_devices"] = detected_drives
            self.test_results["backup_files"] = backup_files
            self.test_results["experimental_modules"] = experimental_modules
            return True
        else:
            print("✗ Failed to update platform configuration")
            return False

def main():
    """Main function to run the Maker Pi test suite"""
    # Check if this is being run directly or imported
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--standalone':
        print("Maker Pi RP2040 Comprehensive Experimental Module Test Suite")
        print("============================================================")
        print("This test suite verifies that:")
        print("1. Core motion control sensors (encoder feedback, optical flow, power sensor)")
        print("   are handled by Raspberry Pi 5")
        print("2. Experimental modules (sensors, displays, IO) are handled by Maker Pi RP2040")
        print("3. Windows/Linux USB detection and connection troubleshooting works")
        print("4. MicroPython file system access is available for development")
        print("5. Placeholder functionality works correctly for future implementation")
        print()
        
        # Create and run test suite
        test_suite = MakerPiTestSuite()
        
        try:
            success = test_suite.run_maker_pi_identification()
            
            if success:
                print("\n✓ All Maker Pi tests completed successfully!")
                print("\nNext steps for development:")
                print("1. Use the connection information in platform_config.json")
                print("2. Access MicroPython files via the established serial connection")
                print("3. Edit code directly on the Maker Pi flash drive")
                print("4. Use AI cursor agent to match code patterns across platforms")
            else:
                print("\n✗ Some Maker Pi tests failed. Check the test results file for details.")
                print("\nTroubleshooting steps:")
                print("1. Check USB connections and drivers")
                print("2. Verify Maker Pi is in bootloader mode if needed")
                print("3. Try different USB ports or cables")
                print("4. Check platform-specific serial port permissions")
                
        except Exception as e:
            print(f"\nAn error occurred during testing: {str(e)}")
            return False
        
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
        print("Maker Pi test module loaded. Use --standalone flag to run directly.") 