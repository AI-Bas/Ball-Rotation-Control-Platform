#!/usr/bin/env python3
"""
Comprehensive Calibration and System Characterization Tests
Consolidated test module for motor calibration, system characterization, and performance analysis
This script will be called by system_test.py for calibration and characterization options

Features:
- Motor encoder calibration and validation
- PID parameter tuning and optimization
- Velocity and position calibration
- System response characterization
- Performance metrics and analysis
- Ball handling optimization
- Thermal and power analysis
"""

import sys
import os
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
import numpy as np
import argparse

# Add the parent directory to sys.path to import from utils
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.roboclaw_interface import RoboClawInterface

# --- Utility Classes ---

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

class SetpointGenerator:
    """Generate velocity setpoints for calibration and testing"""
    def __init__(self, velocity_converter: VelocityConverter):
        self.velocity_converter = velocity_converter
    
    def generate_tangential_velocity_setpoints(self, min_velocity: float = 0.0, max_velocity: float = 2.0, num_points: int = 10) -> List[float]:
        return np.linspace(min_velocity, max_velocity, num_points).tolist()
    
    def generate_rpm_setpoints_from_tangential_velocity(self, min_velocity: float = 0.0, max_velocity: float = 2.0, num_points: int = 10) -> List[float]:
        tangential_velocities = self.generate_tangential_velocity_setpoints(min_velocity, max_velocity, num_points)
        return [self.velocity_converter.tangential_velocity_to_rpm(v) for v in tangential_velocities]
    
    def generate_encoder_setpoints_from_rpm(self, rpm_setpoints: List[float]) -> List[float]:
        return [self.velocity_converter.rpm_to_encoder_counts(rpm) for rpm in rpm_setpoints]
    
    def generate_calibration_setpoints(self, min_velocity: float = 0.0, max_velocity: float = 2.0, num_points: int = 10) -> Dict[str, Any]:
        tangential_velocities = self.generate_tangential_velocity_setpoints(min_velocity, max_velocity, num_points)
        rpm_setpoints = self.generate_rpm_setpoints_from_tangential_velocity(min_velocity, max_velocity, num_points)
        encoder_setpoints = self.generate_encoder_setpoints_from_rpm(rpm_setpoints)
        return {
            'tangential_velocities': tangential_velocities,
            'rpm_setpoints': rpm_setpoints,
            'encoder_setpoints': encoder_setpoints,
            'num_points': num_points,
            'velocity_range': [min_velocity, max_velocity]
        }

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

class ComprehensiveCalibrationTests:
    """Comprehensive calibration and system characterization test suite"""
    
    def __init__(self):
        """Initialize comprehensive calibration test suite"""
        self.test_results = {
            "timestamp": datetime.now().isoformat(),
            "tests": {},
            "errors": [],
            "calibration_data": {},
            "performance_data": {},
            "characterization_data": {},
            "system_analysis": {}
        }
        self.platform_config = self.load_platform_config()
        self.motor_defaults = self.platform_config.get('motor_defaults', {})
        self.system_parameters = self.platform_config.get('system_parameters', {})
        
        # Initialize utility classes
        self.velocity_converter = VelocityConverter(
            encoder_cpr=self.motor_defaults.get('encoder_cpr', 512),
            gear_reduction=self.motor_defaults.get('gear_reduction', 4.333),
            wheel_radius=self.system_parameters.get('rOmni', 0.1)
        )
        self.setpoint_generator = SetpointGenerator(self.velocity_converter)
        self.data_buffer = CalibrationDataBuffer()
    
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
    
    def get_characterization_config(self) -> Dict[str, Any]:
        """Get characterization configuration with defaults"""
        default_config = {
            'step_response_duration': 10.0,
            'step_response_amplitude': 0.5,
            'frequency_response_range': [0.1, 10.0],
            'frequency_response_points': 20,
            'settling_time_threshold': 0.05,
            'overshoot_threshold': 0.1,
            'bandwidth_threshold': -3.0,
            'stability_margin_target': 45.0
        }
        characterization_config = self.platform_config.get('characterization', {})
        return {**default_config, **characterization_config}
    
    def analyze_system_parameters(self) -> Dict[str, Any]:
        """Analyze system parameters from configuration"""
        print("\n=== System Parameters Analysis ===")
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'system_parameters': {},
            'kinematic_parameters': {},
            'control_parameters': {},
            'hardware_parameters': {}
        }
        
        if self.system_parameters:
            analysis['system_parameters'] = {
                'ball_radius': self.system_parameters.get('rBall', 0.111),
                'omniwheel_radius': self.system_parameters.get('rOmni', 0.1),
                'wheel_positions': self.system_parameters.get('wheel_positions', []),
                'beta_angle': self.system_parameters.get('beta', 120.0)
            }
            print("✓ System parameters loaded")
        else:
            print("⚠ No system parameters found")
        
        initial_conditions = self.platform_config.get('initial_conditions', {})
        if initial_conditions:
            analysis['control_parameters'] = {
                'control_loop_dt': initial_conditions.get('control_loop', {}).get('dt', 0.01),
                'buffer_duration': initial_conditions.get('control_loop', {}).get('buffer_duration', 60.0),
                'pid_gains': initial_conditions.get('control_loop', {}).get('pid_gains', {})
            }
            print("✓ Control parameters loaded")
        else:
            print("⚠ No initial conditions found")
        
        if self.motor_defaults:
            analysis['hardware_parameters'] = {
                'encoder_cpr': self.motor_defaults.get('encoder_cpr', 512),
                'gear_reduction': self.motor_defaults.get('gear_reduction', 4.333),
                'motor_constant': self.motor_defaults.get('motor_constant', 699),
                'nominal_voltage': self.motor_defaults.get('nominal_voltage', 12),
                'nominal_current': self.motor_defaults.get('nominal_current', 6),
                'peak_current': self.motor_defaults.get('peak_current', 60)
            }
            print("✓ Hardware parameters loaded")
        else:
            print("⚠ No motor defaults found")
        
        self.test_results["system_analysis"] = analysis
        return analysis
    
    # --- Calibration Tests ---
    
    def test_motor_encoder_calibration(self):
        """Placeholder for motor encoder calibration"""
        print("\n=== Motor Encoder Calibration ===")
        print("(Placeholder - Future implementation)")
        print("This test will:")
        print("- Calibrate encoder counts per revolution")
        print("- Verify encoder direction and scaling")
        print("- Test encoder resolution and accuracy")
        print("- Validate encoder feedback loop")
        
        # Placeholder implementation
        self.test_results["tests"]["motor_encoder_calibration"] = "placeholder"
        return True
    
    def test_pid_parameter_tuning(self):
        """Placeholder for PID parameter tuning"""
        print("\n=== PID Parameter Tuning ===")
        print("(Placeholder - Future implementation)")
        print("This test will:")
        print("- Tune proportional, integral, and derivative gains")
        print("- Optimize for velocity control")
        print("- Optimize for position control")
        print("- Test system stability and response")
        
        # Placeholder implementation
        self.test_results["tests"]["pid_parameter_tuning"] = "placeholder"
        return True
    
    def test_velocity_calibration(self):
        """Placeholder for velocity calibration"""
        print("\n=== Velocity Calibration ===")
        print("(Placeholder - Future implementation)")
        print("This test will:")
        print("- Calibrate velocity scaling factors")
        print("- Test maximum and minimum velocities")
        print("- Verify velocity control accuracy")
        print("- Characterize velocity response time")
        
        # Placeholder implementation
        self.test_results["tests"]["velocity_calibration"] = "placeholder"
        return True
    
    def test_position_calibration(self):
        """Placeholder for position calibration"""
        print("\n=== Position Calibration ===")
        print("(Placeholder - Future implementation)")
        print("This test will:")
        print("- Calibrate position scaling factors")
        print("- Test position control accuracy")
        print("- Verify position repeatability")
        print("- Characterize position response time")
        
        # Placeholder implementation
        self.test_results["tests"]["position_calibration"] = "placeholder"
        return True
    
    def test_system_response_characterization(self):
        """Placeholder for system response characterization"""
        print("\n=== System Response Characterization ===")
        print("(Placeholder - Future implementation)")
        print("This test will:")
        print("- Characterize system step response")
        print("- Analyze frequency response")
        print("- Measure settling time and overshoot")
        print("- Determine system bandwidth")
        
        # Placeholder implementation
        self.test_results["tests"]["system_response_characterization"] = "placeholder"
        return True
    
    def test_ball_handling_optimization(self):
        """Placeholder for ball handling optimization"""
        print("\n=== Ball Handling Optimization ===")
        print("(Placeholder - Future implementation)")
        print("This test will:")
        print("- Optimize ball handling parameters")
        print("- Test ball tracking accuracy")
        print("- Characterize ball control performance")
        print("- Validate ball handling algorithms")
        
        # Placeholder implementation
        self.test_results["tests"]["ball_handling_optimization"] = "placeholder"
        return True
    
    # --- System Characterization Tests ---
    
    def test_system_response_time(self):
        """Placeholder for system response time measurement"""
        print("\n=== System Response Time Measurement ===")
        print("(Placeholder - Future implementation)")
        print("This test will:")
        print("- Measure command-to-response latency")
        print("- Test control loop response time")
        print("- Characterize communication delays")
        print("- Analyze system responsiveness")
        
        # Placeholder implementation
        self.test_results["tests"]["system_response_time"] = "placeholder"
        return True
    
    def test_maximum_velocity_acceleration(self):
        """Placeholder for maximum velocity and acceleration testing"""
        print("\n=== Maximum Velocity and Acceleration Testing ===")
        print("(Placeholder - Future implementation)")
        print("This test will:")
        print("- Test maximum achievable velocities")
        print("- Measure maximum acceleration rates")
        print("- Characterize velocity limits")
        print("- Analyze acceleration performance")
        
        # Placeholder implementation
        self.test_results["tests"]["maximum_velocity_acceleration"] = "placeholder"
        return True
    
    def test_power_consumption_analysis(self):
        """Placeholder for power consumption analysis"""
        print("\n=== Power Consumption Analysis ===")
        print("(Placeholder - Future implementation)")
        print("This test will:")
        print("- Measure power consumption under load")
        print("- Analyze efficiency at different speeds")
        print("- Characterize power requirements")
        print("- Test battery life estimation")
        
        # Placeholder implementation
        self.test_results["tests"]["power_consumption_analysis"] = "placeholder"
        return True
    
    def test_thermal_performance_monitoring(self):
        """Placeholder for thermal performance monitoring"""
        print("\n=== Thermal Performance Monitoring ===")
        print("(Placeholder - Future implementation)")
        print("This test will:")
        print("- Monitor motor temperatures")
        print("- Analyze thermal behavior under load")
        print("- Test thermal protection systems")
        print("- Characterize cooling requirements")
        
        # Placeholder implementation
        self.test_results["tests"]["thermal_performance_monitoring"] = "placeholder"
        return True
    
    def test_ball_handling_performance_metrics(self):
        """Placeholder for ball handling performance metrics"""
        print("\n=== Ball Handling Performance Metrics ===")
        print("(Placeholder - Future implementation)")
        print("This test will:")
        print("- Measure ball tracking accuracy")
        print("- Analyze ball control precision")
        print("- Test ball handling speed")
        print("- Characterize ball manipulation capabilities")
        
        # Placeholder implementation
        self.test_results["tests"]["ball_handling_performance_metrics"] = "placeholder"
        return True
    
    def test_system_stability_analysis(self):
        """Placeholder for system stability analysis"""
        print("\n=== System Stability Analysis ===")
        print("(Placeholder - Future implementation)")
        print("This test will:")
        print("- Analyze system stability margins")
        print("- Test robustness to disturbances")
        print("- Characterize stability under load")
        print("- Validate stability criteria")
        
        # Placeholder implementation
        self.test_results["tests"]["system_stability_analysis"] = "placeholder"
        return True
    
    def test_noise_vibration_characterization(self):
        """Placeholder for noise and vibration characterization"""
        print("\n=== Noise and Vibration Characterization ===")
        print("(Placeholder - Future implementation)")
        print("This test will:")
        print("- Measure system noise levels")
        print("- Analyze vibration characteristics")
        print("- Test noise reduction methods")
        print("- Characterize acoustic performance")
        
        # Placeholder implementation
        self.test_results["tests"]["noise_vibration_characterization"] = "placeholder"
        return True
    
    # --- Display and Utility Methods ---
    
    def display_motor_defaults(self):
        """Display motor default parameters"""
        print("\n=== Motor Default Parameters ===")
        if self.motor_defaults:
            for key, value in self.motor_defaults.items():
                print(f"{key}: {value}")
        else:
            print("No motor defaults found in configuration")
    
    def display_system_parameters(self):
        """Display system parameters"""
        print("\n=== System Parameters ===")
        if self.system_parameters:
            for key, value in self.system_parameters.items():
                print(f"{key}: {value}")
        else:
            print("No system parameters found in configuration")
    
    def run_calibration_tests(self) -> bool:
        """Run all calibration tests"""
        print("\n" + "="*60)
        print("🔧 COMPREHENSIVE CALIBRATION TESTS")
        print("="*60)
        print(f"⏰ Timestamp: {datetime.now().isoformat()}")
        print("="*60)
        
        # Analyze system parameters first
        self.analyze_system_parameters()
        
        # Run calibration tests
        calibration_tests = [
            ("Motor Encoder Calibration", self.test_motor_encoder_calibration),
            ("PID Parameter Tuning", self.test_pid_parameter_tuning),
            ("Velocity Calibration", self.test_velocity_calibration),
            ("Position Calibration", self.test_position_calibration),
            ("System Response Characterization", self.test_system_response_characterization),
            ("Ball Handling Optimization", self.test_ball_handling_optimization)
        ]
        
        for test_name, test_func in calibration_tests:
            try:
                test_func()
            except Exception as e:
                print(f"✗ Error in {test_name}: {e}")
                self.log_error(test_name, str(e))
        
        # Display motor defaults
        self.display_motor_defaults()
        
        # Save results
        self.save_test_results()
        
        return True
    
    def run_characterization_tests(self) -> bool:
        """Run all system characterization tests"""
        print("\n" + "="*60)
        print("🔧 SYSTEM CHARACTERIZATION TESTS")
        print("="*60)
        print(f"⏰ Timestamp: {datetime.now().isoformat()}")
        print("="*60)
        
        # Analyze system parameters first
        self.analyze_system_parameters()
        
        # Run characterization tests
        characterization_tests = [
            ("System Response Time", self.test_system_response_time),
            ("Maximum Velocity/Acceleration", self.test_maximum_velocity_acceleration),
            ("Power Consumption Analysis", self.test_power_consumption_analysis),
            ("Thermal Performance Monitoring", self.test_thermal_performance_monitoring),
            ("Ball Handling Performance Metrics", self.test_ball_handling_performance_metrics),
            ("System Stability Analysis", self.test_system_stability_analysis),
            ("Noise/Vibration Characterization", self.test_noise_vibration_characterization)
        ]
        
        for test_name, test_func in characterization_tests:
            try:
                test_func()
            except Exception as e:
                print(f"✗ Error in {test_name}: {e}")
                self.log_error(test_name, str(e))
        
        # Display system parameters
        self.display_system_parameters()
        
        # Save results
        self.save_test_results()
        
        return True
    
    def run_all_tests(self) -> bool:
        """Run both calibration and characterization tests"""
        print("\n" + "="*60)
        print("🔧 COMPREHENSIVE CALIBRATION AND CHARACTERIZATION")
        print("="*60)
        print(f"⏰ Timestamp: {datetime.now().isoformat()}")
        print("="*60)
        
        # Run calibration tests
        self.run_calibration_tests()
        
        # Run characterization tests
        self.run_characterization_tests()
        
        # Display summary
        print("\n" + "="*60)
        print("📊 TEST SUMMARY")
        print("="*60)
        print(f"Total Tests: {len(self.test_results['tests'])}")
        print(f"Errors: {len(self.test_results['errors'])}")
        print(f"System Analysis: {'✓' if self.test_results.get('system_analysis') else '✗'}")
        
        if self.test_results['errors']:
            print("\n⚠ ERRORS ENCOUNTERED:")
            for error in self.test_results['errors']:
                print(f"  {error['test']}: {error['error']}")
        
        return True
    
    def save_test_results(self) -> Optional[str]:
        """Save comprehensive test results"""
        try:
            # Ensure test_logs directory exists
            os.makedirs("test_logs/calibration", exist_ok=True)
            
            # Save results to file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"calibration_test_{timestamp}.json"
            filepath = os.path.join("test_logs/calibration", filename)
            
            # Save results
            with open(filepath, "w") as f:
                json.dump(self.test_results, f, indent=2)
            
            print(f"\n💾 Comprehensive results saved to {filepath}")
            return filepath
            
        except Exception as e:
            print(f"\n⚠ Could not save results: {e}")
            return None

def main():
    """Main function for standalone execution"""
    parser = argparse.ArgumentParser(description="Comprehensive Calibration Tests")
    parser.add_argument("--dev", action="store_true", help="Enable development mode")
    parser.add_argument("--save", action="store_true", help="Save test results")
    parser.add_argument("--autopilot", type=str, default="", help="Autopilot input string")
    
    args = parser.parse_args()
    
    tester = ComprehensiveCalibrationTests()
    
    print("Comprehensive Calibration and System Characterization Tests")
    print("="*60)
    print("1. Run Calibration Tests Only")
    print("2. Run Characterization Tests Only")
    print("3. Run All Tests")
    print("4. Display System Parameters")
    print("5. Exit")
    
    # Handle autopilot mode
    if args.autopilot:
        print("🤖 AUTOPILOT MODE - Running all tests")
        try:
            tester.run_all_tests()
            return 0
        except Exception as e:
            print(f"Error in autopilot mode: {e}")
            return 1
    
    # Interactive mode
    try:
        choice = input("\nEnter your choice (1-5): ").strip()
        
        if choice == "1":
            tester.run_calibration_tests()
        elif choice == "2":
            tester.run_characterization_tests()
        elif choice == "3":
            tester.run_all_tests()
        elif choice == "4":
            tester.display_system_parameters()
            tester.display_motor_defaults()
        elif choice == "5":
            print("Exiting...")
        else:
            print("Invalid choice. Exiting...")
            
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Error: {e}")
    
    return 0

if __name__ == "__main__":
    main() 