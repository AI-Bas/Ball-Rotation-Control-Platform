#!/usr/bin/env python3
"""
System Test Suite - Central Testing Controller
Streamlined modular testing system for Ball Handler Test Platform

This is the central controller that orchestrates all testing modules:
1. RoboClaw Motor Identification
2. RoboClaw Settings Manager  
3. Calibration Tests
4. System Characterization Tests
5. Maker Pi Experimental Module Testing

Each module is maintained through hardware abstraction layers and follows
the system architecture defined in system_design_architecture.yaml
"""

import sys
import os
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

# Add the parent directory to sys.path to import from utils
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.roboclaw_interface import RoboClawInterface

# Import consolidated test modules
from roboclaw_motor_identification import RoboClawMotorIdentification
from roboclaw_settings_manager import RoboClawSettingsManager
from calibration_tests import CalibrationTests
from system_characterization_tests import SystemCharacterizationTests
from maker_pi_tests import MakerPiTestSuite

class SystemTests:
    """Central system test controller"""
    
    def __init__(self, use_dual_controllers: bool = False, use_rs232_fallback: bool = False):
        """Initialize the system test suite"""
        self.test_results = {
            "timestamp": datetime.now().isoformat(),
            "tests": {},
            "errors": [],
            "module_results": {},
            "system_status": "initialized"
        }
        self.platform_config = self.load_platform_config()
        self.use_dual_controllers = use_dual_controllers
        self.use_rs232_fallback = use_rs232_fallback
        
        # Initialize module timestamps
        self._initialize_module_timestamps()

    def load_platform_config(self):
        """Load platform configuration"""
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'platform_config.json')
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load platform_config.json: {e}")
            return {}

    def _initialize_module_timestamps(self):
        """Initialize module timestamps for tracking"""
        if 'module_timestamps' not in self.platform_config:
            self.platform_config['module_timestamps'] = {}
        
        modules = [
            'roboclaw_motor_identification',
            'roboclaw_settings_manager', 
            'calibration_tests',
            'system_characterization_tests',
            'maker_pi_tests'
        ]
        
        for module in modules:
            if module not in self.platform_config['module_timestamps']:
                self.platform_config['module_timestamps'][module] = {
                    'last_updated': datetime.now().isoformat(),
                    'updated_by': 'system_initialization',
                    'status': 'initialized'
                }
    
    def log_error(self, test_name: str, error: str):
        """Log an error during testing"""
        self.test_results["errors"].append({
            "test": test_name,
            "error": error,
            "timestamp": datetime.now().isoformat()
        })

    def update_module_timestamp(self, module_name: str, updated_by: str = "test_execution"):
        """Update module timestamp"""
        if 'module_timestamps' not in self.platform_config:
            self.platform_config['module_timestamps'] = {}
        
        self.platform_config['module_timestamps'][module_name] = {
            'last_updated': datetime.now().isoformat(),
            'updated_by': updated_by,
            'status': 'completed'
        }
    
    def run_external_test_script(self, script_name: str, description: str) -> bool:
        """Run external test script and capture results"""
        print(f"\n=== Running {description} ===")
        print(f"Script: {script_name}")
        
        try:
            # Import and run the test module
            if script_name == "roboclaw_motor_identification":
                test_module = RoboClawMotorIdentification()
                success = test_module.run_motor_identification()
                if success:
                    self.test_results["module_results"]["roboclaw_motor_identification"] = test_module.test_results
                    self.update_module_timestamp("roboclaw_motor_identification")
                
            elif script_name == "roboclaw_settings_manager":
                test_module = RoboClawSettingsManager()
                success = test_module.run_settings_manager()
                if success:
                    self.test_results["module_results"]["roboclaw_settings_manager"] = test_module.test_results
                    self.update_module_timestamp("roboclaw_settings_manager")
                
            elif script_name == "calibration_tests":
                test_module = CalibrationTests()
                success = test_module.run_all_calibration_tests()
                if success:
                    self.test_results["module_results"]["calibration_tests"] = test_module.test_results
                    self.update_module_timestamp("calibration_tests")
                
            elif script_name == "system_characterization_tests":
                test_module = SystemCharacterizationTests()
                success = test_module.run_all_characterization_tests()
                if success:
                    self.test_results["module_results"]["system_characterization_tests"] = test_module.test_results
                    self.update_module_timestamp("system_characterization_tests")
                
            elif script_name == "maker_pi_tests":
                test_module = MakerPiTestSuite()
                success = test_module.run_maker_pi_identification()
                if success:
                    self.test_results["module_results"]["maker_pi_tests"] = test_module.test_results
                    self.update_module_timestamp("maker_pi_tests")
                
            else:
                print(f"✗ Unknown test script: {script_name}")
                return False
                
            if success:
                print(f"✓ {description} completed successfully")
                self.test_results["tests"][script_name] = "passed"
            else:
                print(f"✗ {description} failed")
                self.test_results["tests"][script_name] = "failed"
            
            return success
            
        except ImportError as e:
            print(f"✗ Error importing {script_name}: {e}")
            self.log_error(script_name, f"Import error: {e}")
            return False
        except Exception as e:
            print(f"✗ Error running {script_name}: {e}")
            self.log_error(script_name, str(e))
            return False

    def run_unified_connectivity_test(self):
        """Run unified connectivity test for all hardware"""
        print("\n=== Unified Connectivity Test ===")
        print("Testing connectivity for all hardware components...")
        
        connectivity_results = {
            "maker_pi": {},
            "roboclaw": {},
            "overall_status": "unknown"
        }
        
        try:
            # Check for Maker Pi devices
            try:
                maker_pi_suite = MakerPiTestSuite()
                detected_drives = maker_pi_suite.detect_circuitpython_drives()
                if detected_drives:
                    connectivity_results["maker_pi"] = {
                        "status": "detected",
                        "drives": detected_drives,
                        "count": len(detected_drives)
                    }
                    print(f"✓ Maker Pi: {len(detected_drives)} CircuitPython drive(s) detected")
                else:
                    connectivity_results["maker_pi"] = {
                        "status": "not_detected",
                        "drives": {},
                        "count": 0
                    }
                    print("✗ Maker Pi: No CircuitPython drives detected")
            except Exception as e:
                connectivity_results["maker_pi"] = {
                    "status": "error",
                    "error": str(e)
                }
                print(f"✗ Maker Pi: Error during detection - {e}")
            
            # Check for RoboClaw controllers
            try:
                roboclaw_test = RoboClawMotorIdentification()
                excluded_ports = roboclaw_test.check_maker_pi_identification()
                detected_controllers = roboclaw_test.detect_roboclaw_controllers(excluded_ports)
                if detected_controllers:
                    connectivity_results["roboclaw"] = {
                        "status": "detected",
                        "controllers": detected_controllers,
                        "count": len(detected_controllers)
                    }
                    print(f"✓ RoboClaw: {len(detected_controllers)} controller(s) detected")
                else:
                    connectivity_results["roboclaw"] = {
                        "status": "not_detected",
                        "controllers": {},
                        "count": 0
                    }
                    print("✗ RoboClaw: No controllers detected")
            except Exception as e:
                connectivity_results["roboclaw"] = {
                    "status": "error",
                    "error": str(e)
                }
                print(f"✗ RoboClaw: Error during detection - {e}")
            
            # Determine overall status
            maker_pi_status = connectivity_results["maker_pi"].get("status", "unknown")
            roboclaw_status = connectivity_results["roboclaw"].get("status", "unknown")
            
            if maker_pi_status == "detected" and roboclaw_status == "detected":
                connectivity_results["overall_status"] = "all_connected"
                print("✓ Overall Status: All hardware components detected and connected")
            elif maker_pi_status == "detected" or roboclaw_status == "detected":
                connectivity_results["overall_status"] = "partial_connection"
                print("⚠ Overall Status: Partial connection - some hardware detected")
            else:
                connectivity_results["overall_status"] = "no_connection"
                print("✗ Overall Status: No hardware components detected")
            
            self.test_results["connectivity_summary"] = connectivity_results
            return connectivity_results["overall_status"] != "no_connection"
            
        except Exception as e:
            print(f"✗ Error during unified connectivity test: {e}")
            self.log_error("unified_connectivity_test", str(e))
            return False
    
    def run_roboclaw_settings_management(self):
        """Run RoboClaw settings management module"""
        while True:
            try:
                print("\n=== Running RoboClaw Settings Management ===")
                
                # Import and run RoboClaw settings management
                from roboclaw_settings_manager import RoboClawSettingsManager
                
                settings_manager = RoboClawSettingsManager()
                success = settings_manager.run_settings_manager()
                
                if success:
                    print("\n✓ RoboClaw settings management completed successfully!")
                else:
                    print("\n✗ RoboClaw settings management failed!")
                    
            except Exception as e:
                print(f"\n✗ Error running RoboClaw settings management: {e}")
                self.log_error("roboclaw_settings_management", str(e))
            
            # Return to main menu option
            if self._offer_return_to_menu():
                break  # Return to main menu
            else:
                print("\n=== RoboClaw Settings Management Module Menu ===")
                print("1. 🔄 Re-run Settings Management")
                print("2. 📋 Show Current Settings")
                print("3. 🔙 Return to Main Menu")
                
                try:
                    choice = input("Enter choice (1-3): ").strip()
                    if choice == '1':
                        continue  # Re-run the settings management
                    elif choice == '2':
                        self.display_roboclaw_settings_status()
                    elif choice == '3':
                        break  # Return to main menu
                    else:
                        print("Invalid choice. Returning to main menu...")
                        break
                except KeyboardInterrupt:
                    print("\nReturning to main menu...")
                    break
    
    def run_calibration_tests(self):
        """Run calibration tests"""
        while True:
            try:
                print("\n=== Running Calibration Tests ===")
                
                # Import and run calibration tests
                from calibration_tests import CalibrationTests
                
                calibration_test = CalibrationTests()
                success = calibration_test.run_all_calibration_tests()
                
                if success:
                    print("\n✓ Calibration tests completed successfully!")
                else:
                    print("\n✗ Calibration tests failed!")
                    
            except Exception as e:
                print(f"\n✗ Error running calibration tests: {e}")
                self.log_error("calibration_tests", str(e))
            
            # Return to main menu option
            if self._offer_return_to_menu():
                break  # Return to main menu
            else:
                print("\n=== Calibration Tests Module Menu ===")
                print("1. 🔄 Re-run Calibration Tests")
                print("2. 📋 Show Calibration Status")
                print("3. 🔙 Return to Main Menu")
                
                try:
                    choice = input("Enter choice (1-3): ").strip()
                    if choice == '1':
                        continue  # Re-run the calibration tests
                    elif choice == '2':
                        self.display_calibration_status()
                    elif choice == '3':
                        break  # Return to main menu
                    else:
                        print("Invalid choice. Returning to main menu...")
                        break
                except KeyboardInterrupt:
                    print("\nReturning to main menu...")
                    break
    
    def run_system_characterization_tests(self):
        """Run system characterization tests"""
        while True:
            try:
                print("\n=== Running System Characterization Tests ===")
                
                # Import and run system characterization tests
                from system_characterization_tests import SystemCharacterizationTests
                
                characterization_test = SystemCharacterizationTests()
                success = characterization_test.run_all_characterization_tests()
                
                if success:
                    print("\n✓ System characterization tests completed successfully!")
                else:
                    print("\n✗ System characterization tests failed!")
                    
            except Exception as e:
                print(f"\n✗ Error running system characterization tests: {e}")
                self.log_error("system_characterization_tests", str(e))
            
            # Return to main menu option
            if self._offer_return_to_menu():
                break  # Return to main menu
            else:
                print("\n=== System Characterization Tests Module Menu ===")
                print("1. 🔄 Re-run Characterization Tests")
                print("2. 📋 Show System Performance Status")
                print("3. 🔙 Return to Main Menu")
                
                try:
                    choice = input("Enter choice (1-3): ").strip()
                    if choice == '1':
                        continue  # Re-run the characterization tests
                    elif choice == '2':
                        self.display_system_performance_status()
                    elif choice == '3':
                        break  # Return to main menu
                    else:
                        print("Invalid choice. Returning to main menu...")
                        break
                except KeyboardInterrupt:
                    print("\nReturning to main menu...")
                    break

    def display_test_menu(self):
        """Display the main test menu"""
        while True:
            print("\n" + "="*60)
            print("BALL HANDLER TEST PLATFORM - SYSTEM TEST MENU")
            print("="*60)
            print("1. 🔍 Run Maker Pi Identification")
            print("2. ⚙️  Run RoboClaw Motor Identification") 
            print("3. 🔧 Run RoboClaw Settings Management")
            print("4. 📊 Run Calibration Tests")
            print("5. 📈 Run System Characterization Tests")
            print("6. 🔄 Run All Tests Sequential")
            print("7. 📋 Display System Status")
            print("8. ❌ Exit")
            print("="*60)
            
            try:
                choice = input("Enter your choice (1-8): ").strip()
                
                if choice == '1':
                    self.run_maker_pi_identification()
                elif choice == '2':
                    self.run_roboclaw_motor_identification()
                elif choice == '3':
                    self.run_roboclaw_settings_management()
                elif choice == '4':
                    self.run_calibration_tests()
                elif choice == '5':
                    self.run_system_characterization_tests()
                elif choice == '6':
                    self.run_all_tests_sequential()
                elif choice == '7':
                    self.display_system_status()
                elif choice == '8':
                    print("Exiting...")
                    break
                else:
                    print("Invalid choice. Please enter a number between 1-8.")
                    
            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                print(f"An error occurred: {e}")
    
    def run_maker_pi_identification(self):
        """Run Maker Pi identification module"""
        while True:
            try:
                print("\n=== Running Maker Pi Identification ===")
                
                # Import and run Maker Pi identification
                from maker_pi_tests import MakerPiTestSuite
                
                maker_pi_suite = MakerPiTestSuite()
                success = maker_pi_suite.run_maker_pi_identification()
                
                if success:
                    print("\n✓ Maker Pi identification completed successfully!")
                else:
                    print("\n✗ Maker Pi identification failed!")
                    
            except Exception as e:
                print(f"\n✗ Error running Maker Pi identification: {e}")
                self.log_error("maker_pi_identification", str(e))
            
            # Return to main menu option
            if self._offer_return_to_menu():
                break  # Return to main menu
            else:
                print("\n=== Maker Pi Identification Module Menu ===")
                print("1. 🔄 Re-run Maker Pi Identification")
                print("2. 📋 Show Maker Pi Status")
                print("3. 🔙 Return to Main Menu")
                
                try:
                    choice = input("Enter choice (1-3): ").strip()
                    if choice == '1':
                        continue  # Re-run the identification
                    elif choice == '2':
                        self.display_maker_pi_status()
                    elif choice == '3':
                        break  # Return to main menu
                    else:
                        print("Invalid choice. Returning to main menu...")
                        break
                except KeyboardInterrupt:
                    print("\nReturning to main menu...")
                    break
    
    def run_roboclaw_motor_identification(self):
        """Run RoboClaw motor identification module"""
        while True:
            try:
                print("\n=== Running RoboClaw Motor Identification ===")
                
                # Import and run RoboClaw motor identification
                from roboclaw_motor_identification import RoboClawMotorIdentification
                
                roboclaw_identification = RoboClawMotorIdentification()
                
                # Check for previously identified Maker Pi devices to exclude their ports
                excluded_ports = roboclaw_identification.check_maker_pi_identification()
                
                success = roboclaw_identification.run_motor_identification()
                
                if success:
                    print("\n✓ RoboClaw motor identification completed successfully!")
                else:
                    print("\n✗ RoboClaw motor identification failed!")
                    
            except Exception as e:
                print(f"\n✗ Error running RoboClaw motor identification: {e}")
                self.log_error("roboclaw_motor_identification", str(e))
            
            # Return to main menu option
            if self._offer_return_to_menu():
                break  # Return to main menu
            else:
                print("\n=== RoboClaw Motor Identification Module Menu ===")
                print("1. 🔄 Re-run Motor Identification")
                print("2. 📋 Show Motor Mapping Status")
                print("3. 🔙 Return to Main Menu")
                
                try:
                    choice = input("Enter choice (1-3): ").strip()
                    if choice == '1':
                        continue  # Re-run the identification
                    elif choice == '2':
                        self.display_motor_mapping_status()
                    elif choice == '3':
                        break  # Return to main menu
                    else:
                        print("Invalid choice. Returning to main menu...")
                        break
                except KeyboardInterrupt:
                    print("\nReturning to main menu...")
                    break

    def _offer_return_to_menu(self):
        """Offer to return to main menu"""
        print("\n" + "-"*40)
        print("Return to main menu? (y/n):")
        try:
            choice = input().strip().lower()
            if choice == 'y':
                print("Returning to main menu...")
                return True  # Return to main menu
            else:
                print("Continuing with current module...")
                return False  # Stay in current module
        except KeyboardInterrupt:
            print("\nReturning to main menu...")
            return True  # Return to main menu on interrupt
        except Exception:
            print("Returning to main menu...")
            return True  # Return to main menu on error

    def display_system_status(self):
        """Display current system status"""
        print("\n=== System Status ===")
        
        # Display module timestamps
        module_timestamps = self.platform_config.get('module_timestamps', {})
        if module_timestamps:
            print("Module Status:")
            for module_name, module_info in module_timestamps.items():
                last_updated = module_info.get('last_updated', 'Unknown')
                status = module_info.get('status', 'Unknown')
                updated_by = module_info.get('updated_by', 'Unknown')
                print(f"  {module_name}:")
                print(f"    Status: {status}")
                print(f"    Last updated: {last_updated}")
                print(f"    Updated by: {updated_by}")
        else:
            print("No module timestamps found")
        
        # Display hardware configuration
        hardware_config = self.platform_config.get('hardware', {})
        if hardware_config:
            print("\nHardware Configuration:")
            
            # RoboClaw info
            roboclaw_config = hardware_config.get('roboclaw', {})
            if roboclaw_config:
                controllers = roboclaw_config.get('controllers', {})
                print(f"  RoboClaw controllers: {len(controllers)}")
                for controller_name, controller_info in controllers.items():
                    print(f"    {controller_name}: {controller_info.get('port', 'Unknown')}")
            
            # Maker Pi info
            maker_pi_config = hardware_config.get('maker_pi', {})
            if maker_pi_config:
                print(f"  Maker Pi: {maker_pi_config.get('type', 'Unknown')}")
                print(f"    Responsibility: {maker_pi_config.get('responsibility', 'Unknown')}")
        
        # Display system parameters
        system_params = self.platform_config.get('system_parameters', {})
        if system_params:
            print("\nSystem Parameters:")
            print(f"  Ball radius: {system_params.get('rBall', 'Unknown')} m")
            print(f"  Omniwheel radius: {system_params.get('rOmni', 'Unknown')} m")
            print(f"  Beta angle: {system_params.get('beta', 'Unknown')}°")
    
    def run_all_tests_sequential(self):
        """Run all test modules in sequence"""
        print("\n=== Running All Tests Sequentially ===")
        print("This will execute all test modules in the recommended order:")
        print("1. Unified Connectivity Test")
        print("2. RoboClaw Settings Management")
        print("3. Calibration Tests")
        print("4. System Characterization Tests")
        print()
        
        # Confirm with user
        try:
            user_input = input("Proceed with all tests? (y/n): ").strip().lower()
            if user_input != 'y':
                print("Sequential test execution cancelled")
                return False
        except KeyboardInterrupt:
            print("\nSequential test execution cancelled")
            return False
        
        # Run tests in sequence
        test_results = []
        
        # Test 1: Unified Connectivity
        print("\n" + "="*60)
        print("TEST 1: Unified Connectivity Test")
        print("="*60)
        result1 = self.run_unified_connectivity_test()
        test_results.append(("Unified Connectivity", result1))
        
        if not result1:
            print("⚠ Connectivity test failed. Some subsequent tests may fail.")
            print("Continue with remaining tests? (y/n): ", end='')
            try:
                if input().strip().lower() != 'y':
                    print("Sequential test execution stopped")
                    return False
            except KeyboardInterrupt:
                print("\nSequential test execution stopped")
                return False
        
        # Test 2: Settings Management
        print("\n" + "="*60)
        print("TEST 2: RoboClaw Settings Management")
        print("="*60)
        result2 = self.run_roboclaw_settings_management()
        test_results.append(("Settings Management", result2))
        
        # Test 3: Calibration
        print("\n" + "="*60)
        print("TEST 3: Calibration Tests")
        print("="*60)
        result3 = self.run_calibration_tests()
        test_results.append(("Calibration", result3))
        
        # Test 4: System Characterization
        print("\n" + "="*60)
        print("TEST 4: System Characterization Tests")
        print("="*60)
        result4 = self.run_system_characterization_tests()
        test_results.append(("System Characterization", result4))
        
        # Display summary
        print("\n" + "="*60)
        print("SEQUENTIAL TEST SUMMARY")
        print("="*60)
        
        passed_tests = sum(1 for _, result in test_results if result)
        total_tests = len(test_results)
        
        for test_name, result in test_results:
            status = "✓ PASSED" if result else "✗ FAILED"
            print(f"{test_name}: {status}")
        
        print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("✓ All tests completed successfully!")
            self.test_results["system_status"] = "all_tests_passed"
        else:
            print("⚠ Some tests failed. Check individual test results for details.")
            self.test_results["system_status"] = "some_tests_failed"
        
        return passed_tests == total_tests

    def save_test_results(self):
        """Save test results to a JSON file"""
        try:
            # Use the test_logs directory
            test_logs_dir = "test_logs"
            test_logs_path = os.path.join(os.path.dirname(__file__), test_logs_dir)
            os.makedirs(test_logs_path, exist_ok=True)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"system_test_results_{timestamp}.json"
            filepath = os.path.join(test_logs_path, filename)
            
            # Save results
            with open(filepath, 'w') as f:
                json.dump(self.test_results, f, indent=2)
            
            print(f"\nTest results saved to: {filepath}")
            return filepath
            
        except Exception as e:
            print(f"Error saving test results: {str(e)}")
            return None

    def display_maker_pi_status(self):
        """Display Maker Pi status from platform configuration"""
        print("\n=== Maker Pi Status ===")
        
        maker_pi_config = self.platform_config.get('hardware', {}).get('maker_pi', {})
        if maker_pi_config:
            print(f"Type: {maker_pi_config.get('type', 'Unknown')}")
            print(f"Responsibility: {maker_pi_config.get('responsibility', 'Unknown')}")
            
            detected_drives = maker_pi_config.get('detected_drives', {})
            if detected_drives:
                print(f"\nDetected Drives: {len(detected_drives)}")
                for drive_path, drive_info in detected_drives.items():
                    print(f"  {drive_path}:")
                    print(f"    Type: {drive_info.get('type', 'Unknown')}")
                    print(f"    Code Size: {drive_info.get('code_size', 0)} characters")
                    print(f"    Serial Port: {drive_info.get('serial_port', 'Not detected')}")
            else:
                print("\nNo drives detected")
        else:
            print("No Maker Pi configuration found")
    
    def display_motor_mapping_status(self):
        """Display motor mapping status from platform configuration"""
        print("\n=== Motor Mapping Status ===")
        
        roboclaw_config = self.platform_config.get('hardware', {}).get('roboclaw', {})
        if roboclaw_config:
            motor_mapping = roboclaw_config.get('motor_mapping', {})
            if motor_mapping:
                print(f"Configured Motors: {len(motor_mapping)}")
                for motor_name, motor_info in motor_mapping.items():
                    print(f"  {motor_name}:")
                    print(f"    Controller: {motor_info.get('controller', 'Unknown')}")
                    print(f"    Port: {motor_info.get('port', 'Unknown')}")
                    print(f"    Position: {motor_info.get('position', 'Unknown')}")
                    print(f"    Description: {motor_info.get('description', 'Unknown')}")
            else:
                print("No motor mapping configured")
        else:
            print("No RoboClaw configuration found")

    def display_roboclaw_settings_status(self):
        """Display RoboClaw settings status from platform configuration"""
        print("\n=== RoboClaw Settings Status ===")
        
        roboclaw_config = self.platform_config.get('hardware', {}).get('roboclaw', {})
        if roboclaw_config:
            controllers = roboclaw_config.get('controllers', {})
            if controllers:
                print(f"Configured Controllers: {len(controllers)}")
                for controller_name, controller_info in controllers.items():
                    print(f"  {controller_name}:")
                    print(f"    Port: {controller_info.get('port', 'Unknown')}")
                    print(f"    Address: {controller_info.get('address', 'Unknown')}")
                    print(f"    Channels: {controller_info.get('channels', [])}")
            else:
                print("No controllers configured")
        else:
            print("No RoboClaw configuration found")
    
    def display_calibration_status(self):
        """Display calibration status from platform configuration"""
        print("\n=== Calibration Status ===")
        
        motor_defaults = self.platform_config.get('motor_defaults', {})
        if motor_defaults:
            print("Motor Default Values:")
            for key, value in motor_defaults.items():
                print(f"  {key}: {value}")
        else:
            print("No motor defaults configured")
        
        # Check for calibration data in test results
        if hasattr(self, 'test_results') and 'calibration_data' in self.test_results:
            print("\nCalibration Test Results:")
            for test_name, result in self.test_results['calibration_data'].items():
                print(f"  {test_name}: {result}")
    
    def display_system_performance_status(self):
        """Display system performance status from platform configuration"""
        print("\n=== System Performance Status ===")
        
        system_params = self.platform_config.get('system_parameters', {})
        if system_params:
            print("System Parameters:")
            print(f"  Ball radius: {system_params.get('rBall', 'Unknown')} m")
            print(f"  Omniwheel radius: {system_params.get('rOmni', 'Unknown')} m")
            print(f"  Beta angle: {system_params.get('beta', 'Unknown')}°")
        
        initial_conditions = self.platform_config.get('initial_conditions', {})
        if initial_conditions:
            control_loop = initial_conditions.get('control_loop', {})
            if control_loop:
                print("\nControl Loop Parameters:")
                print(f"  dt: {control_loop.get('dt', 'Unknown')} s")
                print(f"  Buffer duration: {control_loop.get('buffer_duration', 'Unknown')} s")
                
                pid_gains = control_loop.get('pid_gains', {})
                if pid_gains:
                    print(f"  PID gains - Kp: {pid_gains.get('kp', 'Unknown')}, Ki: {pid_gains.get('ki', 'Unknown')}, Kd: {pid_gains.get('kd', 'Unknown')}")
        else:
            print("No system performance data found")

def main():
    """Main function for the system test suite"""
    print("Ball Handler Test Platform - System Test Suite")
    print("==============================================")
    print("Central testing controller for streamlined modular testing")
    print("Each module is maintained through hardware abstraction layers")
    print("and follows the system architecture defined in system_design_architecture.yaml")
    print()
    
    # Initialize system tests
    system_tests = SystemTests()
    
    # Display menu and handle user input
    system_tests.display_test_menu()
    
    # Save test results
    system_tests.save_test_results()
    print("\nSystem test suite completed.")
    print("Test results have been saved to the test_logs directory.")

if __name__ == "__main__":
    main() 