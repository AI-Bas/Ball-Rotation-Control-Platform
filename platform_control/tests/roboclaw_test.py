#!/usr/bin/env python3
"""
RoboClaw Test Module
Comprehensive RoboClaw testing with motor mapping, monitoring, and diagnostics
"""
import sys
import os
import json
import argparse
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.roboclaw_interface import RoboClawInterface
from utils.roboclaw_test_utils import fix_roboclaw_pins, check_error_state
from utils.autopilot_manager import create_autopilot_manager, set_autopilot_manager, get_autopilot_input

class RoboClawTestMenu:
    """Comprehensive RoboClaw test menu with all functionality"""
    
    def __init__(self, development_mode: bool = False, autopilot_input: str = ""):
        self.development_mode = development_mode
        self.autopilot_input = autopilot_input
        self.autopilot_manager = create_autopilot_manager("roboclaw_test", autopilot_input)
        set_autopilot_manager(self.autopilot_manager)
        
        # Initialize interface
        self.interface = RoboClawInterface(use_dual_controllers=True, autopilot_mode=bool(autopilot_input))
        
        # Connect to controllers
        if not self.interface.connect():
            print("⚠️ Warning: Failed to connect to RoboClaw controllers")
        
        self.test_results = {}
    
    def get_autopilot_input(self, prompt: str = "Enter choice: ") -> str:
        return get_autopilot_input(prompt)
    
    def display_main_menu(self):
        """Display the main RoboClaw test menu"""
        print("\n🔧 RoboClaw Test Menu")
        print("=" * 50)
        print("1. Motor Mapping Menu")
        print("2. E-Stop Functionality Test")
        print("3. Error State Diagnostics")
        print("4. Connectivity Test (moved to connectivity_test.py)")
        print("5. Motor Control Test")
        print("6. Pin Configuration Fix")
        print("7. RoboClaw Address Testing")
        print("8. Run All Tests")
        print("9. Save Results")
        print("10. Exit")
        print("=" * 50)
    
    def display_motor_mapping_menu(self):
        """Display the motor mapping submenu"""
        print("\n🔍 Motor Mapping Menu")
        print("=" * 40)
        print("1. Monitor Motor Channels")
        print("2. Identify Motor Mapping")
        print("3. Verify Motor Mapping")
        print("4. Back to Main Menu")
        print("=" * 40)
    
    def run_motor_mapping_menu(self):
        """Run the motor mapping submenu"""
        while True:
            self.display_motor_mapping_menu()
            choice = self.get_autopilot_input()
            
            if choice == "1":
                print("\n📊 Motor Channel Monitoring")
                self.interface.monitor_motor_channels()
                
            elif choice == "2":
                print("\n🔍 Motor Mapping Identification")
                result = self.interface.identify_motor_mapping()
                self.test_results["motor_mapping_identification"] = {
                    "timestamp": datetime.now().isoformat(),
                    "success": result
                }
                
            elif choice == "3":
                print("\n🔍 Motor Mapping Verification")
                result = self.interface.verify_motor_mapping()
                self.test_results["motor_mapping_verification"] = {
                    "timestamp": datetime.now().isoformat(),
                    "success": result
                }
                
            elif choice == "4":
                break
            else:
                print("❌ Invalid choice")
    
    def run_estop_test(self):
        """Run E-Stop functionality test"""
        print("\n🛑 E-Stop Functionality Test")
        print("=" * 40)
        
        results = {}
        for controller_name in ['rc1', 'rc2']:
            if controller_name in self.interface.controller_info and self.interface.controller_info[controller_name]['connected']:
                print(f"\nTesting E-Stop on {controller_name}...")
                result = self.interface.test_estop_functionality(controller_name)
                results[controller_name] = result
                if result:
                    print(f"✅ E-Stop test passed for {controller_name}")
                else:
                    print(f"❌ E-Stop test failed for {controller_name}")
            else:
                print(f"⚠️ {controller_name} not connected, skipping")
        
        self.test_results["estop_test"] = {
            "timestamp": datetime.now().isoformat(),
            "results": results
        }
    
    def run_error_diagnostics(self):
        """Run error state diagnostics"""
        print("\n🔍 Error State Diagnostics")
        print("=" * 40)
        
        results = {}
        for controller_name in ['rc1', 'rc2']:
            if controller_name in self.interface.controller_info and self.interface.controller_info[controller_name]['connected']:
                print(f"\nChecking error state for {controller_name}...")
                result = check_error_state(self.interface, controller_name)
                results[controller_name] = result
                print(f"Result: {result}")
            else:
                print(f"⚠️ {controller_name} not connected, skipping")
        
        self.test_results["error_diagnostics"] = {
            "timestamp": datetime.now().isoformat(),
            "results": results
        }
    
    # Connectivity test removed - handled by connectivity_test.py
    # This eliminates redundancy and follows system architecture
    
    def run_motor_control_test(self):
        """Run motor control test"""
        print("\n🚀 Motor Control Test")
        print("=" * 40)
        
        # Simple motor control test
        test_motors = [1, 2, 3, 4]
        test_velocities = [100, 200, 300]
        results = {}
        
        for motor_id in test_motors:
            motor_results = []
            print(f"\nTesting Motor {motor_id}...")
            
            for velocity in test_velocities:
                print(f"   Setting velocity to {velocity}")
                success = self.interface.set_velocity(motor_id, velocity)
                
                if success:
                    print(f"   ✅ Velocity {velocity} set successfully")
                    import time
                    time.sleep(0.5)
                    
                    motor_data = self.interface.get_motor_data(motor_id)
                    if motor_data:
                        print(f"   📊 Motor data: {motor_data}")
                        motor_results.append({
                            "velocity": velocity,
                            "success": True,
                            "motor_data": motor_data
                        })
                    else:
                        print(f"   ⚠️ No motor data available")
                        motor_results.append({
                            "velocity": velocity,
                            "success": False,
                            "error": "No motor data"
                        })
                else:
                    print(f"   ❌ Failed to set velocity {velocity}")
                    motor_results.append({
                        "velocity": velocity,
                        "success": False,
                        "error": "Failed to set velocity"
                    })
                
                # Stop motor
                self.interface.set_velocity(motor_id, 0)
                print(f"   ✅ Motor stopped")
            
            results[f"motor{motor_id}"] = motor_results
        
        self.test_results["motor_control_test"] = {
            "timestamp": datetime.now().isoformat(),
            "results": results
        }
        
        print("\n🎉 Motor control test completed!")
    
    def run_pin_config_fix(self):
        """Run pin configuration fix"""
        print("\n🔧 Pin Configuration Fix")
        print("=" * 40)
        
        results = {}
        for controller_name in ['rc1', 'rc2']:
            if controller_name in self.interface.controller_info and self.interface.controller_info[controller_name]['connected']:
                print(f"\nFixing pin settings for {controller_name}...")
                success, pin_result = fix_roboclaw_pins(self.interface, controller_name)
                results[controller_name] = {
                    "success": success,
                    "result": pin_result
                }
                
                if success:
                    print(f"✅ Pin settings fixed for {controller_name}: {pin_result}")
                else:
                    print(f"❌ Failed to fix pin settings for {controller_name}: {pin_result}")
            else:
                print(f"⚠️ {controller_name} not connected, skipping")
        
        self.test_results["pin_config_fix"] = {
            "timestamp": datetime.now().isoformat(),
            "results": results
        }
    
    def run_address_testing(self):
        """Run RoboClaw address testing"""
        print("\n🔍 RoboClaw Address Testing")
        print("=" * 40)
        
        result = self.interface.test_roboclaw_addresses()
        self.test_results["address_testing"] = {
            "timestamp": datetime.now().isoformat(),
            "results": result
        }
        
        if result:
            print("✅ Address testing completed")
        else:
            print("❌ Address testing failed")
    
    def run_all_tests(self):
        """Run all RoboClaw tests"""
        print("\n🚀 Running All RoboClaw Tests")
        print("=" * 50)
        
        # Run all tests in sequence
        # Connectivity test handled by connectivity_test.py
        self.run_error_diagnostics()
        self.run_estop_test()
        self.run_motor_control_test()
        self.run_pin_config_fix()
        self.run_address_testing()
        
        print("\n✅ All tests completed!")
    
    def save_results(self):
        """Save test results to file"""
        if not self.test_results:
            print("⚠️ No test results to save")
            return
        
        try:
            # Ensure test_logs directory exists
            os.makedirs("test_logs/roboclaw", exist_ok=True)
            
            # Save results to file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"roboclaw_test_{timestamp}.json"
            filepath = os.path.join("test_logs/roboclaw", filename)
            
            with open(filepath, 'w') as f:
                json.dump(self.test_results, f, indent=2)
            
            print(f"💾 Test results saved: {filepath}")
            
        except Exception as e:
            print(f"❌ Failed to save test results: {e}")
    
    def run_menu(self):
        """Run the main test menu"""
        while True:
            self.display_main_menu()
            
            try:
                choice = self.get_autopilot_input()
                
                if choice == "1":
                    self.run_motor_mapping_menu()
                elif choice == "2":
                    self.run_estop_test()
                elif choice == "3":
                    self.run_error_diagnostics()
                elif choice == "4":
                    print("🔌 Connectivity test moved to connectivity_test.py")
                    print("   Run: python3 tests/connectivity_test.py --dev --save")
                elif choice == "5":
                    self.run_motor_control_test()
                elif choice == "6":
                    self.run_pin_config_fix()
                elif choice == "7":
                    self.run_address_testing()
                elif choice == "8":
                    self.run_all_tests()
                elif choice == "9":
                    self.save_results()
                elif choice == "10":
                    print("👋 Exiting RoboClaw test menu")
                    break
                else:
                    print("❌ Invalid choice")
                    
            except KeyboardInterrupt:
                print("\n👋 Exiting...")
                break
            except Exception as e:
                print(f"❌ Error: {e}")

def main():
    parser = argparse.ArgumentParser(description="RoboClaw Test Menu - Comprehensive Testing")
    parser.add_argument("--dev", action="store_true", help="Enable development mode")
    parser.add_argument("--save", action="store_true", help="Save results to file")
    parser.add_argument("--autopilot", type=str, default="", help="Autopilot input string")
    args = parser.parse_args()

    # Initialize test menu
    test_menu = RoboClawTestMenu(development_mode=args.dev, autopilot_input=args.autopilot)
    
    # Run menu
    test_menu.run_menu()
    
    # Save results if requested
    if args.save:
        test_menu.save_results()
    
    return 0

if __name__ == "__main__":
    main() 