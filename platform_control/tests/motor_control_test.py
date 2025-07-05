#!/usr/bin/env python3
"""
Motor Control Test Module
Tests velocity setpoints and current monitoring with RoboClaw controllers
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

# Add the parent directory to sys.path to import from utils
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.roboclaw_interface import RoboClawInterface
from utils.autopilot_manager import create_autopilot_manager, set_autopilot_manager, get_autopilot_input

class MotorControlTest:
    """Motor control test module for velocity setpoints and current monitoring"""
    
    def __init__(self, development_mode: bool = False, autopilot_input: str = ""):
        """Initialize the motor control test module"""
        self.development_mode = development_mode
        self.autopilot_input = autopilot_input
        # Initialize autopilot manager for this script
        self.autopilot_manager = create_autopilot_manager("motor_control_test", autopilot_input)
        set_autopilot_manager(self.autopilot_manager)
        
        # Initialize RoboClaw interface
        self.interface = RoboClawInterface(use_dual_controllers=True)
        
        # Connect to controllers
        if not self.interface.connect():
            print("⚠️ Warning: Failed to connect to RoboClaw controllers")
        
        # Test results storage
        self.test_results = {}
        
        print("🔧 Motor Control Test Module Initialized")
        if self.development_mode:
            print("   Development mode enabled")
    
    def get_autopilot_input(self, prompt: str = "Enter choice: ") -> str:
        return get_autopilot_input(prompt)
    
    def test_velocity_setpoints(self, motor_num: int, velocity: int = 1000, duration: float = 2.0) -> Dict[str, Any]:
        """Test velocity setpoints for a specific motor"""
        print(f"\n🚀 Velocity Setpoint Test - Motor {motor_num}")
        print("-" * 40)
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "test_type": "velocity_setpoint",
            "motor_num": motor_num,
            "target_velocity": velocity,
            "duration": duration,
            "status": False,
            "current_readings": [],
            "voltage_readings": [],
            "encoder_readings": []
        }
        
        if motor_num not in self.interface.motor_data:
            result["error"] = f"Motor {motor_num} not found in mapping"
            print(f"   ❌ {result['error']}")
            return result
        
        motor_info = self.interface.motor_data[motor_num]
        controller = motor_info['controller']
        address = motor_info['address']
        channel = motor_info['channel']
        
        if not controller:
            result["error"] = f"Controller not available for motor {motor_num}"
            print(f"   ❌ {result['error']}")
            return result
        
        try:
            print(f"   📍 Motor {motor_num}: {motor_info['controller_name']} Channel {motor_info['channel_letter']}")
            print(f"   🎯 Target velocity: {velocity} counts/sec")
            print(f"   ⏱️ Duration: {duration} seconds")
            
            # Read baseline data
            print("   📊 Reading baseline data...")
            baseline_data = self.interface.get_motor_data(motor_num)
            if baseline_data:
                print(f"   📈 Baseline - Current: {baseline_data['current']:.2f}A, Voltage: {baseline_data['voltage']:.1f}V")
            
            # Set velocity setpoint
            print("   🚀 Setting velocity setpoint...")
            if channel == 1:
                success = controller.SpeedM1(address, velocity)
            else:
                success = controller.SpeedM2(address, velocity)
            
            if not success:
                result["error"] = f"Failed to set velocity for motor {motor_num}"
                print(f"   ❌ {result['error']}")
                return result
            
            print("   ✅ Velocity setpoint applied")
            
            # Monitor for specified duration
            start_time = time.time()
            sample_count = 0
            
            while time.time() - start_time < duration:
                # Read motor data
                motor_data = self.interface.get_motor_data(motor_num)
                if motor_data:
                    reading = {
                        "timestamp": time.time(),
                        "current": motor_data['current'],
                        "voltage": motor_data['voltage'],
                        "encoder_velocity": motor_data['encoder_velocity'],
                        "encoder_position": motor_data['encoder_position']
                    }
                    result["current_readings"].append(reading)
                    result["voltage_readings"].append(reading)
                    result["encoder_readings"].append(reading)
                    
                    if sample_count % 10 == 0:  # Print every 10th reading
                        print(f"   📊 Sample {sample_count}: Current={motor_data['current']:.2f}A, "
                              f"Voltage={motor_data['voltage']:.1f}V, "
                              f"Velocity={motor_data['encoder_velocity']:.0f} counts/sec")
                
                sample_count += 1
                time.sleep(0.1)  # 100ms sample rate
            
            # Stop motor
            print("   🛑 Stopping motor...")
            if channel == 1:
                controller.SpeedM1(address, 0)
            else:
                controller.SpeedM2(address, 0)
            
            # Calculate statistics
            if result["current_readings"]:
                currents = [r["current"] for r in result["current_readings"]]
                voltages = [r["voltage"] for r in result["voltage_readings"]]
                velocities = [r["encoder_velocity"] for r in result["encoder_readings"]]
                
                result["statistics"] = {
                    "avg_current": sum(currents) / len(currents),
                    "max_current": max(currents),
                    "min_current": min(currents),
                    "avg_voltage": sum(voltages) / len(voltages),
                    "avg_velocity": sum(velocities) / len(velocities),
                    "samples": len(result["current_readings"])
                }
                
                print(f"   📊 Statistics:")
                print(f"      Average Current: {result['statistics']['avg_current']:.2f}A")
                print(f"      Average Voltage: {result['statistics']['avg_voltage']:.1f}V")
                print(f"      Average Velocity: {result['statistics']['avg_velocity']:.0f} counts/sec")
                print(f"      Samples: {result['statistics']['samples']}")
            
            result["status"] = True
            print("   ✅ Velocity setpoint test completed successfully")
            
        except Exception as e:
            result["error"] = str(e)
            print(f"   ❌ Velocity setpoint test failed: {e}")
        
        return result
    
    def test_motor_mapping_verification(self) -> Dict[str, Any]:
        """Verify motor mapping by testing each motor"""
        print("\n🔍 Motor Mapping Verification Test")
        print("-" * 40)
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "test_type": "motor_mapping_verification",
            "motors": {},
            "status": False
        }
        
        # Test each mapped motor
        for motor_num in [1, 2, 3, 4]:
            if motor_num in self.interface.motor_data:
                print(f"\n   🔧 Testing Motor {motor_num}...")
                motor_result = self.test_velocity_setpoints(motor_num, velocity=500, duration=1.0)
                result["motors"][f"motor{motor_num}"] = motor_result
                
                if motor_result["status"]:
                    print(f"   ✅ Motor {motor_num} test passed")
                else:
                    print(f"   ❌ Motor {motor_num} test failed")
        
        # Determine overall status
        result["status"] = all(
            motor_result["status"] 
            for motor_result in result["motors"].values()
        )
        
        if result["status"]:
            print("\n   ✅ All motor mapping tests passed")
        else:
            print("\n   ❌ Some motor mapping tests failed")
        
        return result
    
    def test_current_monitoring(self) -> Dict[str, Any]:
        """Test current monitoring across all motors"""
        print("\n⚡ Current Monitoring Test")
        print("-" * 40)
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "test_type": "current_monitoring",
            "baseline_readings": {},
            "active_readings": {},
            "status": False
        }
        
        try:
            # Read baseline current for all motors
            print("   📊 Reading baseline current levels...")
            for motor_num in [1, 2, 3, 4]:
                if motor_num in self.interface.motor_data:
                    motor_data = self.interface.get_motor_data(motor_num)
                    if motor_data:
                        result["baseline_readings"][f"motor{motor_num}"] = {
                            "current": motor_data['current'],
                            "voltage": motor_data['voltage']
                        }
                        print(f"      Motor {motor_num}: {motor_data['current']:.2f}A @ {motor_data['voltage']:.1f}V")
            
            # Apply small velocity to each motor and monitor current
            print("   🚀 Applying small velocity to each motor...")
            for motor_num in [1, 2, 3, 4]:
                if motor_num in self.interface.motor_data:
                    print(f"      Testing Motor {motor_num}...")
                    
                    # Apply small velocity
                    motor_result = self.test_velocity_setpoints(motor_num, velocity=200, duration=0.5)
                    
                    if motor_result["status"] and motor_result["statistics"]:
                        result["active_readings"][f"motor{motor_num}"] = {
                            "avg_current": motor_result["statistics"]["avg_current"],
                            "avg_voltage": motor_result["statistics"]["avg_voltage"],
                            "current_change": motor_result["statistics"]["avg_current"] - 
                                            result["baseline_readings"].get(f"motor{motor_num}", {}).get("current", 0)
                        }
                        
                        current_change = result["active_readings"][f"motor{motor_num}"]["current_change"]
                        print(f"         Current change: {current_change:+.2f}A")
            
            result["status"] = len(result["active_readings"]) > 0
            print("   ✅ Current monitoring test completed")
            
        except Exception as e:
            result["error"] = str(e)
            print(f"   ❌ Current monitoring test failed: {e}")
        
        return result
    
    def run_test_menu(self) -> Dict[str, Any]:
        """Run the motor control test menu"""
        print("\n🔧 Motor Control Test Menu")
        print("=" * 50)
        
        while True:
            print("\nMain Menu:")
            print("1. Test Velocity Setpoints (Single Motor)")
            print("2. Motor Mapping Verification")
            print("3. Current Monitoring Test")
            print("4. Run All Tests")
            print("5. Save Results")
            print("6. Exit")
            print("-" * 30)
            
            choice = self.get_autopilot_input()
            
            if choice == "1":
                # Test single motor
                print("\nSelect motor to test:")
                print("1. Motor 1")
                print("2. Motor 2")
                print("3. Motor 3")
                print("4. Motor 4")
                
                motor_choice = self.get_autopilot_input("Enter motor number: ")
                try:
                    motor_num = int(motor_choice)
                    if 1 <= motor_num <= 4:
                        result = self.test_velocity_setpoints(motor_num, velocity=1000, duration=2.0)
                        self.test_results[f"velocity_test_motor{motor_num}"] = result
                    else:
                        print("   ❌ Invalid motor number")
                except ValueError:
                    print("   ❌ Invalid input")
            
            elif choice == "2":
                result = self.test_motor_mapping_verification()
                self.test_results["motor_mapping_verification"] = result
            
            elif choice == "3":
                result = self.test_current_monitoring()
                self.test_results["current_monitoring"] = result
            
            elif choice == "4":
                self.run_all_tests()
            
            elif choice == "5":
                if self.test_results:
                    self.save_test_results(self.test_results)
                else:
                    print("   ⚠️ No test results to save")
            
            elif choice == "6":
                print("   👋 Exiting motor control test menu")
                break
            
            else:
                print("   ❌ Invalid choice")
        
        return self.test_results
    
    def run_all_tests(self):
        """Run all motor control tests"""
        print("\n🚀 Running All Motor Control Tests")
        print("=" * 50)
        
        # Run motor mapping verification
        self.test_results["motor_mapping_verification"] = self.test_motor_mapping_verification()
        
        # Run current monitoring test
        self.test_results["current_monitoring"] = self.test_current_monitoring()
        
        print("\n   ✅ All motor control tests completed")
    
    def save_test_results(self, results: Dict[str, Any]):
        """Save test results to file"""
        try:
            # Ensure test_logs directory exists
            os.makedirs("test_logs/motor_control", exist_ok=True)
            
            # Save results to file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"motor_control_test_{timestamp}.json"
            filepath = os.path.join("test_logs/motor_control", filename)
            
            with open(filepath, 'w') as f:
                json.dump(results, f, indent=2)
            
            print(f"   💾 Test results saved: {filepath}")
            
        except Exception as e:
            print(f"   ⚠️ Failed to save test results: {e}")

def simple_velocity_test(interface=None):
    """Test velocity control with working motors (from simple_velocity_test.py)"""
    print("\n🔧 Simple Velocity Test (Merged)")
    print("=" * 40)
    if interface is None:
        from utils.roboclaw_interface import RoboClawInterface
        interface = RoboClawInterface(use_dual_controllers=True)
        if not interface.connect():
            print("❌ Failed to connect to RoboClaw controllers")
            return False
    test_motors = [1, 2, 3]
    test_velocities = [100, 200, 300]
    for motor_id in test_motors:
        print(f"\n🔍 Testing motor {motor_id}...")
        for velocity in test_velocities:
            print(f"   🔧 Setting velocity to {velocity}")
            success = interface.set_velocity(motor_id, velocity)
            if success:
                print(f"   ✅ Velocity {velocity} set successfully")
                import time
                time.sleep(0.5)
                motor_data = interface.get_motor_data(motor_id)
                if motor_data:
                    print(f"   📊 Motor data: {motor_data}")
                    # Check for encoder/velocity change
                    if not motor_data.get('velocity') or motor_data.get('velocity') == 0:
                        print(f"   ❌ No velocity detected! Test failed.")
                        return False
                else:
                    print(f"   ⚠️ No motor data available")
                    return False
                interface.set_velocity(motor_id, 0)
                print(f"   ✅ Motor stopped")
            else:
                print(f"   ❌ Failed to set velocity {velocity}")
                return False
    print("\n🎉 Simple velocity test completed!")
    return True

def main():
    """Main function for motor control testing"""
    parser = argparse.ArgumentParser(description="Motor Control Test Module")
    parser.add_argument("--dev", action="store_true", help="Enable development mode")
    parser.add_argument("--save", action="store_true", help="Save test results")
    parser.add_argument("--autopilot", type=str, default="", help="Autopilot input string")
    
    args = parser.parse_args()
    
    # Initialize test module
    test_module = MotorControlTest(development_mode=args.dev, autopilot_input=args.autopilot)
    
    # Run test menu
    results = test_module.run_test_menu()
    
    # Save results if requested
    if args.save and results:
        test_module.save_test_results(results)
    
    print("Motor control test completed.")

if __name__ == "__main__":
    main() 