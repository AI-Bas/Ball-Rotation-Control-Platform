#!/usr/bin/env python3
"""
Unified RoboClaw Test Module
Consolidates all RoboClaw testing functionality from:
- roboclaw_test_menu.py
- roboclaw_settings_manager.py  
- roboclaw_motor_identification.py

Provides comprehensive testing with sub-menus for different test categories.
"""

import os
import sys
import json
import time
import argparse
import serial.tools.list_ports
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

# Add the parent directory to sys.path to import from utils
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.roboclaw_interface import RoboClawInterface
from utils.roboclaw_test_utils import RoboClawTestUtils, RoboClawTroubleshooter
from utils.roboclaw_interface import RoboclawSettings
from utils.autopilot_manager import create_autopilot_manager, set_autopilot_manager, get_autopilot_input

class RoboClawTest:
    """Unified RoboClaw test module with comprehensive testing capabilities"""
    
    def __init__(self, development_mode: bool = False, autopilot_input: str = ""):
        """Initialize the RoboClaw test module"""
        self.development_mode = development_mode
        self.autopilot_input = autopilot_input
        # Initialize autopilot manager for this script
        self.autopilot_manager = create_autopilot_manager("roboclaw_test", autopilot_input)
        set_autopilot_manager(self.autopilot_manager)
        
        # Initialize RoboClaw interface
        self.interface = RoboClawInterface(use_dual_controllers=True)
        
        # Connect to controllers
        if not self.interface.connect():
            print("⚠️ Warning: Failed to connect to RoboClaw controllers")
        
        self.test_utils = RoboClawTestUtils(self.interface)
        
        # Test results storage
        self.test_results = {}
        
        # Load configuration
        self.config = self.interface.config
        self.roboclaw_config = self.config.get('hardware', {}).get('roboclaw', {})
        
        print("🔧 RoboClaw Test Module Initialized")
        if self.development_mode:
            print("   Development mode enabled")
    
    def get_autopilot_input(self, prompt: str = "Enter choice: ") -> str:
        return get_autopilot_input(prompt)
    
    def test_connectivity_detailed(self) -> Dict[str, Any]:
        """Test detailed connectivity for all controllers"""
        print("\n🔌 RoboClaw Connectivity Test")
        print("-" * 40)
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "test_type": "connectivity_detailed",
            "controllers": {},
            "overall_status": False
        }
        
        # Test each controller
        for controller_name in ['rc1', 'rc2']:
            if controller_name in self.interface.controller_info:
                controller_info = self.interface.controller_info[controller_name]
                controller_result = {
                    "connected": controller_info['connected'],
                    "port": controller_info.get('port', 'unknown'),
                    "address": controller_info.get('address', 'unknown'),
                    "version": "unknown"
                }
                
                if controller_info['connected']:
                    controller = getattr(self.interface, controller_name)
                    if controller:
                        # Read version
                        version_result = controller.ReadVersion(controller_info['address'])
                        if version_result[0]:
                            controller_result["version"] = version_result[1]
                            print(f"   ✅ {controller_name}: Connected (v{version_result[1]})")
                        else:
                            print(f"   ⚠️ {controller_name}: Connected but version read failed")
                    else:
                        print(f"   ❌ {controller_name}: Not available")
                else:
                    print(f"   ❌ {controller_name}: Not connected")
                
                result["controllers"][controller_name] = controller_result
        
        # Determine overall status
        result["overall_status"] = any(
            controller_result["connected"] 
            for controller_result in result["controllers"].values()
        )
        
        if result["overall_status"]:
            print("   ✅ Connectivity test completed successfully")
        else:
            print("   ❌ No controllers connected")
        
        return result
    
    def test_bandwidth_incremental(self, controller: str) -> Dict[str, Any]:
        """Test bandwidth with incremental speed increases"""
        print(f"\n📊 Bandwidth Test - {controller}")
        print("-" * 40)
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "test_type": "bandwidth_incremental",
            "controller": controller,
            "max_safe_speed": 0,
            "status": False
        }
        
        if controller not in self.interface.controller_info:
            result["error"] = f"Controller {controller} not found"
            print(f"   ❌ {result['error']}")
            return result
        
        if not self.interface.controller_info[controller]['connected']:
            result["error"] = f"Controller {controller} not connected"
            print(f"   ❌ {result['error']}")
            return result
        
        controller_obj = getattr(self.interface, controller)
        address = self.interface.controller_info[controller]['address']
        
        # Test incremental speeds
        test_speeds = [1000, 5000, 10000, 20000, 50000, 100000, 200000, 500000]
        
        for speed in test_speeds:
            print(f"   Testing speed: {speed}")
            
            try:
                # Test both motors
                for motor in [1, 2]:
                    if motor == 1:
                        controller_obj.SpeedM1(address, speed)
                    else:
                        controller_obj.SpeedM2(address, speed)
                
                time.sleep(0.1)  # Brief test
                
                # Stop motors
                controller_obj.SpeedM1(address, 0)
                controller_obj.SpeedM2(address, 0)
                
                result["max_safe_speed"] = speed
                print(f"   ✅ Speed {speed} OK")
                
            except Exception as e:
                print(f"   ❌ Speed {speed} failed: {e}")
                break
        
        result["status"] = result["max_safe_speed"] > 0
        print(f"   📊 Max safe speed: {result['max_safe_speed']}")
        
        return result
    
    def test_e_stop_cycling(self, controller: str, rate: int = 1) -> Dict[str, Any]:
        """Test E-Stop cycling with S3 pin toggling"""
        print(f"\n🛑 E-Stop Cycling Test - {controller}")
        print("-" * 40)
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "test_type": "e_stop_cycling",
            "controller": controller,
            "cycles": 0,
            "status": False
        }
        
        if controller not in self.interface.controller_info:
            result["error"] = f"Controller {controller} not found"
            print(f"   ❌ {result['error']}")
            return result
        
        if not self.interface.controller_info[controller]['connected']:
            result["error"] = f"Controller {controller} not connected"
            print(f"   ❌ {result['error']}")
            return result
        
        controller_obj = getattr(self.interface, controller)
        address = self.interface.controller_info[controller]['address']
        
        print(f"   Cycling E-Stop (S3) at {rate}Hz for 5 seconds...")
        
        try:
            cycles = 0
            start_time = time.time()
            
            while time.time() - start_time < 5.0:
                # Toggle S3 pin (E-Stop)
                controller_obj.SetPinFunctions(address, 1, 1, 1)  # Set S3 to mode 1 (E-Stop)
                time.sleep(1.0 / (2 * rate))  # Half period
                
                controller_obj.SetPinFunctions(address, 0, 1, 1)  # Clear S3
                time.sleep(1.0 / (2 * rate))  # Half period
                
                cycles += 1
            
            result["cycles"] = cycles
            result["status"] = True
            print(f"   ✅ E-Stop cycling completed: {cycles} cycles")
            
        except Exception as e:
            result["error"] = str(e)
            print(f"   ❌ E-Stop cycling failed: {e}")
        
        return result
    
    def test_motor_mapping(self) -> Dict[str, Any]:
        """Test motor identification and mapping"""
        print("\n🔍 Motor Mapping Test")
        print("-" * 40)
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "test_type": "motor_mapping",
            "motors": {},
            "status": False
        }
        
        motor_mapping = self.roboclaw_config.get('motor_mapping', {})
        
        for motor_name, motor_config in motor_mapping.items():
            motor_result = {
                "controller": motor_config.get('controller', 'unknown'),
                "channel": motor_config.get('channel', 'unknown'),
                "position": motor_config.get('position', 'unknown'),
                "description": motor_config.get('description', 'unknown'),
                "encoder_change": motor_config.get('encoder_change', 0),
                "detection_time": motor_config.get('detection_time', 0)
            }
            
            result["motors"][motor_name] = motor_result
            print(f"   📍 {motor_name}: {motor_result['position']} ({motor_result['controller']})")
        
        result["status"] = len(result["motors"]) > 0
        print(f"   ✅ Motor mapping completed: {len(result['motors'])} motors")
        
        return result
    
    def test_settings_manager(self) -> Dict[str, Any]:
        """Test settings management functionality"""
        print("\n⚙️ Settings Manager Test")
        print("-" * 40)
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "test_type": "settings_manager",
            "settings_read": False,
            "settings_saved": False,
            "comparison": False,
            "status": False
        }
        
        try:
            # Read and save current settings
            if self.test_utils.read_and_save_settings():
                result["settings_read"] = True
                result["settings_saved"] = True
                print("   ✅ Settings read and saved successfully")
            
            # Compare with previous settings
            self.test_utils.compare_with_previous_settings()
            result["comparison"] = True
            print("   ✅ Settings comparison completed")
            
            result["status"] = result["settings_read"] and result["settings_saved"]
            
        except Exception as e:
            result["error"] = str(e)
            print(f"   ❌ Settings manager test failed: {e}")
        
        return result
    
    def run_connectivity_menu(self):
        """Run connectivity test sub-menu"""
        while True:
            print("\n🔌 Connectivity Test Menu")
            print("1. Detailed Connectivity Test")
            print("2. Bandwidth Test (RC1)")
            print("3. Bandwidth Test (RC2)")
            print("4. E-Stop Cycling Test (RC1)")
            print("5. E-Stop Cycling Test (RC2)")
            print("6. Back to Main Menu")
            
            choice = self.get_autopilot_input()
            
            if choice == "1":
                result = self.test_connectivity_detailed()
                self.test_results["connectivity_detailed"] = result
            elif choice == "2":
                result = self.test_bandwidth_incremental("rc1")
                self.test_results["bandwidth_rc1"] = result
            elif choice == "3":
                result = self.test_bandwidth_incremental("rc2")
                self.test_results["bandwidth_rc2"] = result
            elif choice == "4":
                result = self.test_e_stop_cycling("rc1")
                self.test_results["e_stop_rc1"] = result
            elif choice == "5":
                result = self.test_e_stop_cycling("rc2")
                self.test_results["e_stop_rc2"] = result
            elif choice == "6":
                break
            else:
                print("   ❌ Invalid choice")
    
    def run_motor_mapping_menu(self):
        """Run motor mapping test sub-menu"""
        while True:
            print("\n🔍 Motor Mapping Menu")
            print("1. Test Motor Mapping")
            print("2. View Current Mapping")
            print("3. Back to Main Menu")
            
            choice = self.get_autopilot_input()
            
            if choice == "1":
                result = self.test_motor_mapping()
                self.test_results["motor_mapping"] = result
            elif choice == "2":
                self.display_motor_mapping()
            elif choice == "3":
                break
            else:
                print("   ❌ Invalid choice")
    
    def run_settings_menu(self):
        """Run settings management sub-menu"""
        while True:
            print("\n⚙️ Settings Management Menu")
            print("1. Test Settings Manager")
            print("2. Read and Save Settings")
            print("3. Compare with Previous")
            print("4. Back to Main Menu")
            
            choice = self.get_autopilot_input()
            
            if choice == "1":
                result = self.test_settings_manager()
                self.test_results["settings_manager"] = result
            elif choice == "2":
                self.test_utils.read_and_save_settings()
            elif choice == "3":
                self.test_utils.compare_with_previous_settings()
            elif choice == "4":
                break
            else:
                print("   ❌ Invalid choice")
    
    def display_motor_mapping(self):
        """Display current motor mapping"""
        print("\n📋 Current Motor Mapping")
        print("-" * 40)
        
        motor_mapping = self.roboclaw_config.get('motor_mapping', {})
        
        for motor_name, motor_config in motor_mapping.items():
            print(f"   {motor_name}:")
            print(f"     Controller: {motor_config.get('controller', 'unknown')}")
            print(f"     Channel: {motor_config.get('channel', 'unknown')}")
            print(f"     Position: {motor_config.get('position', 'unknown')}")
            print(f"     Description: {motor_config.get('description', 'unknown')}")
            print()
    
    def save_test_results(self, results: Dict[str, Any]):
        """Save test results to file"""
        try:
            # Ensure test_logs directory exists
            os.makedirs("test_logs/roboclaw", exist_ok=True)
            
            # Save results to file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"roboclaw_test_{timestamp}.json"
            filepath = os.path.join("test_logs/roboclaw", filename)
            
            with open(filepath, 'w') as f:
                json.dump(results, f, indent=2)
            
            print(f"   💾 Test results saved: {filepath}")
            
        except Exception as e:
            print(f"   ⚠️ Failed to save test results: {e}")
    
    def run_test_menu(self) -> Dict[str, Any]:
        """Run the main test menu"""
        print("\n🔧 RoboClaw Test Menu")
        print("=" * 50)
        
        while True:
            print("\nMain Menu:")
            print("1. Connectivity Tests")
            print("2. Motor Mapping Tests")
            print("3. Settings Management Tests")
            print("4. Run All Tests")
            print("5. Save Results")
            print("6. Exit")
            print("-" * 30)
            
            choice = self.get_autopilot_input()
            
            if choice == "1":
                self.run_connectivity_menu()
            elif choice == "2":
                self.run_motor_mapping_menu()
            elif choice == "3":
                self.run_settings_menu()
            elif choice == "4":
                self.run_all_tests()
            elif choice == "5":
                if self.test_results:
                    self.save_test_results(self.test_results)
                else:
                    print("   ⚠️ No test results to save")
            elif choice == "6":
                print("   👋 Exiting RoboClaw test menu")
                break
            else:
                print("   ❌ Invalid choice")
        
        return self.test_results
    
    def run_all_tests(self):
        """Run all RoboClaw tests"""
        print("\n🚀 Running All RoboClaw Tests")
        print("=" * 50)
        
        # Run connectivity tests
        self.test_results["connectivity_detailed"] = self.test_connectivity_detailed()
        
        # Run bandwidth tests
        self.test_results["bandwidth_rc1"] = self.test_bandwidth_incremental("rc1")
        self.test_results["bandwidth_rc2"] = self.test_bandwidth_incremental("rc2")
        
        # Run E-Stop tests
        self.test_results["e_stop_rc1"] = self.test_e_stop_cycling("rc1")
        self.test_results["e_stop_rc2"] = self.test_e_stop_cycling("rc2")
        
        # Run motor mapping test
        self.test_results["motor_mapping"] = self.test_motor_mapping()
        
        # Run settings manager test
        self.test_results["settings_manager"] = self.test_settings_manager()
        
        print("   ✅ All tests completed")

def main():
    """Main function for RoboClaw test menu"""
    parser = argparse.ArgumentParser(description="Unified RoboClaw Test Menu")
    parser.add_argument("--dev", "--development", action="store_true", 
                       help="Enable development mode with enhanced troubleshooting")
    parser.add_argument("--save", action="store_true", 
                       help="Automatically save test results")
    parser.add_argument("--autopilot", type=str, default="", 
                       help="Autonomous execution input string")
    
    args = parser.parse_args()
    
    print("🔧 Unified RoboClaw Test Menu")
    print("=" * 50)
    
    if args.dev:
        print("🔧 Development mode enabled")
    else:
        print("💡 Run with --dev flag for development mode")
    
    # Initialize test module
    test_module = RoboClawTest(
        development_mode=args.dev,
        autopilot_input=args.autopilot
    )
    
    # Run test menu
    results = test_module.run_test_menu()
    
    # Auto-save if requested
    if args.save and results:
        test_module.save_test_results(results)
    
    print("\nRoboClaw test menu completed.")

if __name__ == "__main__":
    main() 