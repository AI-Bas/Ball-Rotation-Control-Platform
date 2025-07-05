#!/usr/bin/env python3
"""
Comprehensive Calibration Test Module
Consolidated from calibration_tests.py - Motor calibration, system characterization, and performance analysis
"""

import os
import sys
import json
import time
import numpy as np
import argparse
from datetime import datetime
from typing import Dict, Any, Optional, List

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.roboclaw_interface import RoboClawInterface
from utils.roboclaw_control import RoboClawMotorInterface
from utils.setpoint_generator import RoboClawSetpointGenerator
from utils.autopilot_manager import create_autopilot_manager, set_autopilot_manager, get_autopilot_input

# --- Utility Classes (Consolidated from calibration_tests.py) ---

class VelocityConverter:
    """Utility class for velocity conversions between different units"""
    def __init__(self, encoder_cpr: float = 512, gear_reduction: float = 4.333, wheel_radius: float = 0.1):
        self.encoder_cpr = encoder_cpr
        self.gear_reduction = gear_reduction
        self.wheel_radius = wheel_radius
    
    def encoder_counts_to_rad_per_sec(self, encoder_counts_per_sec: float) -> float:
        return (encoder_counts_per_sec / self.encoder_cpr) * 2 * np.pi / self.gear_reduction
    
    def rad_per_sec_to_encoder_counts(self, rad_per_sec: float) -> float:
        return (rad_per_sec * self.gear_reduction) / (2 * np.pi) * self.encoder_cpr
    
    def rad_per_sec_to_rpm(self, rad_per_sec: float) -> float:
        return rad_per_sec * 60 / (2 * np.pi)
    
    def rpm_to_rad_per_sec(self, rpm: float) -> float:
        return rpm * 2 * np.pi / 60
    
    def rad_per_sec_to_tangential_velocity(self, rad_per_sec: float) -> float:
        return rad_per_sec * self.wheel_radius
    
    def tangential_velocity_to_rad_per_sec(self, tangential_velocity: float) -> float:
        return tangential_velocity / self.wheel_radius
    
    def tangential_velocity_to_rpm(self, tangential_velocity: float) -> float:
        rad_per_sec = self.tangential_velocity_to_rad_per_sec(tangential_velocity)
        return self.rad_per_sec_to_rpm(rad_per_sec)
    
    def rpm_to_encoder_counts(self, rpm: float) -> float:
        rad_per_sec = self.rpm_to_rad_per_sec(rpm)
        return self.rad_per_sec_to_encoder_counts(rad_per_sec)
    
    def encoder_counts_to_rpm(self, encoder_counts_per_sec: float) -> float:
        rad_per_sec = self.encoder_counts_to_rad_per_sec(encoder_counts_per_sec)
        return self.rad_per_sec_to_rpm(rad_per_sec)



class CalibrationDataBuffer:
    """Data buffer for calibration measurements"""
    def __init__(self, buffer_duration: float = 60.0, sample_frequency: float = 100.0):
        self.buffer_duration = buffer_duration
        self.sample_frequency = sample_frequency
        self.sample_time = 1.0 / sample_frequency
        self.max_samples = int(buffer_duration * sample_frequency)
        self.timestamps = []
        self.motor_data = {
            'motor1': {'position': [], 'velocity': [], 'voltage': [], 'current': []},
            'motor2': {'position': [], 'velocity': [], 'voltage': [], 'current': []},
            'motor3': {'position': [], 'velocity': [], 'voltage': [], 'current': []}
        }
        self.power_sensor_data = {
            'channel0': {'voltage': [], 'current': [], 'power': []},
            'channel1': {'voltage': [], 'current': [], 'power': []},
            'channel2': {'voltage': [], 'current': [], 'power': []},
            'channel3': {'voltage': [], 'current': [], 'power': []}
        }
        self.computed_data = {
            'wheel_angular_velocity': [],
            'wheel_rpm': [],
            'tangential_velocity': [],
            'motor_constant': []
        }
    
    def add_motor_data(self, motor_id: str, position: float, velocity: float, voltage: float, current: float):
        """Add motor data to buffer"""
        if motor_id in self.motor_data:
            self.motor_data[motor_id]['position'].append(position)
            self.motor_data[motor_id]['velocity'].append(velocity)
            self.motor_data[motor_id]['voltage'].append(voltage)
            self.motor_data[motor_id]['current'].append(current)
    
    def add_power_data(self, channel: str, voltage: float, current: float, power: float):
        """Add power sensor data to buffer"""
        if channel in self.power_sensor_data:
            self.power_sensor_data[channel]['voltage'].append(voltage)
            self.power_sensor_data[channel]['current'].append(current)
            self.power_sensor_data[channel]['power'].append(power)
    
    def get_motor_statistics(self, motor_id: str) -> Dict[str, float]:
        """Get statistical analysis of motor data"""
        if motor_id not in self.motor_data:
            return {}
        
        data = self.motor_data[motor_id]
        stats = {}
        
        for key, values in data.items():
            if values:
                stats[f'{key}_mean'] = np.mean(values)
                stats[f'{key}_std'] = np.std(values)
                stats[f'{key}_min'] = np.min(values)
                stats[f'{key}_max'] = np.max(values)
        
        return stats

# --- Main Calibration Test Class ---

class CalibrationTest:
    """Comprehensive calibration test module (consolidated from calibration_tests.py)"""
    
    def __init__(self, development_mode: bool = False, autopilot_input: str = ""):
        """Initialize the calibration test module"""
        self.development_mode = development_mode
        self.autopilot_input = autopilot_input
        # Initialize autopilot manager for this script
        self.autopilot_manager = create_autopilot_manager("calibration_test", autopilot_input)
        set_autopilot_manager(self.autopilot_manager)
        
        # Initialize RoboClaw interface
        self.roboclaw_interface = RoboClawInterface(use_dual_controllers=True)
        
        # Connect to controllers
        if not self.roboclaw_interface.connect():
            print("⚠️ Warning: Failed to connect to RoboClaw controllers")
        
        # Initialize RoboClaw motor interface
        self.motor_interface = RoboClawMotorInterface(self.roboclaw_interface)
        
        # Load configuration
        self.platform_config = self.load_platform_config()
        self.motor_defaults = self.platform_config.get('motor_defaults', {})
        self.system_parameters = self.platform_config.get('system_parameters', {})
        
        # Initialize utility classes
        self.velocity_converter = VelocityConverter(
            encoder_cpr=self.motor_defaults.get('encoder_cpr', 512),
            gear_reduction=self.motor_defaults.get('gear_reduction', 4.333),
            wheel_radius=self.system_parameters.get('rOmni', 0.1)
        )
        self.setpoint_generator = RoboClawSetpointGenerator()
        self.data_buffer = CalibrationDataBuffer()
        
        # Test results storage
        self.test_results = {
            "timestamp": datetime.now().isoformat(),
            "tests": {},
            "errors": [],
            "calibration_data": {},
            "performance_data": {},
            "characterization_data": {},
            "system_analysis": {}
        }
        
        print("🔧 Calibration Test Module Initialized")
        if self.development_mode:
            print("   Development mode enabled")
        print("   Note: Currently using RoboClaw-specific implementation")
        print("   TODO: Prepare for broader motor-agnostic implementation")
    
    def get_autopilot_input(self, prompt: str = "Enter choice: ") -> str:
        return get_autopilot_input(prompt)
    
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
    
    def run_motor_mapping_test(self) -> Dict[str, Any]:
        """Run motor mapping test with actual motion validation"""
        print("\n🔧 Motor Mapping Test")
        print("-" * 40)
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "test_type": "motor_mapping",
            "motors": {},
            "status": False,
            "motion_validation": False
        }
        
        # Check for motor mapping file
        motor_mapping_file = os.path.join(os.path.dirname(__file__), "motor_mapping.json")
        if not os.path.exists(motor_mapping_file):
            print("   ⚠️ No motor mapping file found")
            print("   ⚠️ Motor mapping may be stale - consider re-mapping")
            print("   💡 You may want to run manual motor mapping first")
        
        print("   🔧 Testing motor mapping...")
        
        # Test each motor with actual motion validation
        for logical_id in range(1, 5):  # Test motors 1-4
            print(f"   📋 Testing logical motor {logical_id} → physical motor {logical_id}")
            
            # Get baseline data
            baseline_data = self.motor_interface.get_motor_status(logical_id)
            if not baseline_data:
                print(f"   ❌ Failed to read baseline data from motor {logical_id}")
                result["motors"][f"motor{logical_id}"] = {"status": "failed", "error": "baseline_read_failed"}
                continue
            
            baseline_encoder = baseline_data.get("encoder", 0) or 0
            baseline_velocity = baseline_data.get("velocity", 0) or 0
            baseline_current = baseline_data.get("current", 0) or 0
            
            # Set velocity command
            success = self.motor_interface.set_velocity(logical_id, 50)
            if not success:
                print(f"   ❌ Failed to set velocity for motor {logical_id}")
                result["motors"][f"motor{logical_id}"] = {"status": "failed", "error": "velocity_set_failed"}
                continue
            
            print(f"   ✅ Set motor {logical_id} velocity to 50 counts/s")
            
            # Wait for motion to occur
            time.sleep(1.0)  # Wait 1 second for motion
            
            # Read data after motion command
            motion_data = self.motor_interface.get_motor_status(logical_id)
            if not motion_data:
                print(f"   ❌ Failed to read motion data from motor {logical_id}")
                result["motors"][f"motor{logical_id}"] = {"status": "failed", "error": "motion_read_failed"}
                continue
            
            # Validate actual motion occurred
            motion_encoder = motion_data.get("encoder", 0) or 0
            motion_velocity = motion_data.get("velocity", 0) or 0
            motion_current = motion_data.get("current", 0) or 0
            encoder_change = abs(motion_encoder - baseline_encoder)
            velocity_change = abs(motion_velocity - baseline_velocity)
            current_change = abs(motion_current - baseline_current)
            
            print(f"   📊 Encoder change: {encoder_change}")
            print(f"   📊 Velocity change: {velocity_change}")
            print(f"   📊 Current change: {current_change}")
            
            # Check if motion actually occurred
            motion_detected = (encoder_change > 0 or velocity_change > 0 or current_change > 0.01)
            
            if not motion_detected:
                print(f"   ❌ NO MOTION DETECTED for motor {logical_id}!")
                print(f"   ❌ Test FAILED - motor not actually spinning")
                result["motors"][f"motor{logical_id}"] = {
                    "status": "failed", 
                    "error": "no_motion_detected",
                    "encoder_change": encoder_change,
                    "velocity_change": velocity_change,
                    "current_change": current_change
                }
                # Stop motor
                self.motor_interface.stop_motor(logical_id)
                continue
            
            print(f"   ✅ Motion detected for motor {logical_id}")
            
            # Stop motor
            self.motor_interface.stop_motor(logical_id)
            print(f"   ✅ Set motor {logical_id} velocity to 0 counts/s")
            
            result["motors"][f"motor{logical_id}"] = {
                "status": "success",
                "encoder_change": encoder_change,
                "velocity_change": velocity_change,
                "current_change": current_change,
                "motion_detected": True
            }
            
            print(f"   ✅ Motor {logical_id} mapping test completed")
        
        # Determine overall status
        successful_motors = sum(1 for motor_data in result["motors"].values() if motor_data.get("status") == "success")
        total_motors = len(result["motors"])
        
        if successful_motors == 0:
            print("   ❌ NO MOTORS SHOWED ACTUAL MOTION - Test FAILED")
            result["status"] = False
            result["motion_validation"] = False
        elif successful_motors < total_motors:
            print(f"   ⚠️ Only {successful_motors}/{total_motors} motors showed motion")
            result["status"] = False
            result["motion_validation"] = False
        else:
            print(f"   ✅ All {successful_motors} motors showed actual motion")
            result["status"] = True
            result["motion_validation"] = True
        
        return result
    
    def run_velocity_calibration_test(self) -> Dict[str, Any]:
        """Run velocity calibration test with setpoint generation"""
        print("\n⚙️ Velocity Calibration Test")
        print("-" * 40)
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "test_type": "velocity_calibration",
            "setpoints": {},
            "status": False
        }
        
        # Generate calibration setpoints
        setpoints = self.setpoint_generator.generate_calibration_setpoints(
            min_velocity=0.0, max_velocity=100.0, num_points=5
        )
        
        print(f"   📋 Generated {setpoints['num_points']} velocity setpoints")
        print(f"   📊 Velocity range: {setpoints['velocity_range']}")
        
        # Test each setpoint
        for i, velocity in enumerate(setpoints['velocities']):
            print(f"   🔧 Testing setpoint {i+1}: {velocity:.0f} counts/s")
            
            # Test with motor 1 (assuming it's working)
            motor_id = 1
            
            # Set velocity
            success = self.motor_interface.set_velocity(motor_id, velocity)
            if not success:
                print(f"   ❌ Failed to set velocity for motor {motor_id}")
                result["setpoints"][f"setpoint_{i+1}"] = {"status": "failed", "error": "velocity_set_failed"}
                continue
            
            # Wait for motor to reach speed
            time.sleep(0.5)
            
            # Get motor status
            motor_status = self.motor_interface.get_motor_status(motor_id)
            if not motor_status:
                print(f"   ❌ Failed to read motor status")
                result["setpoints"][f"setpoint_{i+1}"] = {"status": "failed", "error": "status_read_failed"}
                continue
            
            # Store results
            result["setpoints"][f"setpoint_{i+1}"] = {
                "status": "success",
                "target_velocity": velocity,
                "actual_velocity": motor_status.get("velocity", 0),
                "actual_current": motor_status.get("current", 0),
                "actual_voltage": motor_status.get("voltage", 0)
            }
            
            print(f"   ✅ Setpoint {i+1} completed")
            
            # Stop motor
            self.motor_interface.stop_motor(motor_id)
            time.sleep(0.2)
        
        # Determine overall status
        successful_setpoints = sum(1 for sp in result["setpoints"].values() if sp.get("status") == "success")
        result["status"] = successful_setpoints > 0
        
        if result["status"]:
            print(f"   ✅ Velocity calibration completed: {successful_setpoints} setpoints successful")
        else:
            print("   ❌ Velocity calibration failed")
        
        return result
    
    def run_comprehensive_calibration(self) -> Dict[str, Any]:
        """Run comprehensive calibration test suite"""
        print("\n🔧 Comprehensive Calibration Test Suite")
        print("=" * 50)
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "test_suite": "comprehensive_calibration",
            "tests": {},
            "overall_status": False
        }
        
        # Run motor mapping test
        print("\n1️⃣ Running motor mapping test...")
        mapping_result = self.run_motor_mapping_test()
        result["tests"]["motor_mapping"] = mapping_result
        
        if not mapping_result["status"]:
            print("   ❌ Motor mapping test failed. Stopping calibration suite.")
            return result
        
        # Run velocity calibration test
        print("\n2️⃣ Running velocity calibration test...")
        velocity_result = self.run_velocity_calibration_test()
        result["tests"]["velocity_calibration"] = velocity_result
        
        # Determine overall status
        result["overall_status"] = mapping_result["status"] and velocity_result["status"]
        
        if result["overall_status"]:
            print("   ✅ Comprehensive calibration completed successfully")
        else:
            print("   ⚠️ Some calibration tests failed")
        
        return result
    
    def save_test_results(self, results: Dict[str, Any]) -> Optional[str]:
        """Save test results to file"""
        try:
            # Ensure test_logs directory exists
            os.makedirs("test_logs/calibration", exist_ok=True)
            
            # Save results to file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"calibration_test_{timestamp}.json"
            filepath = os.path.join("test_logs/calibration", filename)
            
            with open(filepath, 'w') as f:
                json.dump(results, f, indent=2)
            
            print(f"   💾 Test results saved: {filepath}")
            return filepath
            
        except Exception as e:
            print(f"   ⚠️ Failed to save test results: {e}")
            return None
    
    def display_menu(self):
        """Display the calibration test menu"""
        print("\n🔧 Calibration Test Menu")
        print("=" * 50)
        print("1. Motor Mapping Test")
        print("2. Velocity Calibration Test")
        print("3. Run Comprehensive Calibration")
        print("4. Save Results")
        print("5. Exit")
        print("-" * 30)

def main():
    """Main function for calibration testing"""
    parser = argparse.ArgumentParser(description="Comprehensive Calibration Test Module")
    parser.add_argument("--dev", "--development", action="store_true", 
                       help="Enable development mode with enhanced troubleshooting")
    parser.add_argument("--save", action="store_true", 
                       help="Automatically save test results")
    parser.add_argument("--autopilot", type=str, default="", 
                       help="Autonomous execution input string")
    
    args = parser.parse_args()
    
    print("🔧 Comprehensive Calibration Test Module")
    print("=" * 50)
    
    if args.dev:
        print("🔧 Development mode enabled")
    else:
        print("💡 Run with --dev flag for development mode")
    
    # Initialize test module
    test_module = CalibrationTest(
        development_mode=args.dev,
        autopilot_input=args.autopilot
    )
    
    # Handle autopilot mode
    if args.autopilot:
        print("🤖 AUTOPILOT MODE - Running comprehensive calibration")
        results = test_module.run_comprehensive_calibration()
        
        # Auto-save if requested
        if args.save and results:
            test_module.save_test_results(results)
        
        return results
    
    # Interactive mode
    while True:
        test_module.display_menu()
        choice = test_module.get_autopilot_input()
        
        if choice == "1":
            result = test_module.run_motor_mapping_test()
            test_module.test_results["motor_mapping"] = result
        elif choice == "2":
            result = test_module.run_velocity_calibration_test()
            test_module.test_results["velocity_calibration"] = result
        elif choice == "3":
            result = test_module.run_comprehensive_calibration()
            test_module.test_results["comprehensive_calibration"] = result
        elif choice == "4":
            if test_module.test_results:
                test_module.save_test_results(test_module.test_results)
            else:
                print("   ⚠️ No test results to save")
        elif choice == "5":
            print("   👋 Exiting calibration test menu")
            break
        else:
            print("   ❌ Invalid choice")
    
    # Auto-save if requested
    if args.save and test_module.test_results:
        test_module.save_test_results(test_module.test_results)
    
    print("\nCalibration test module completed.")

if __name__ == "__main__":
    main() 