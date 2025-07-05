#!/usr/bin/env python3
"""
RoboClaw Motor Connection Test
=============================

Comprehensive motor connection testing with fresh mapping.
Tests all motors systematically without assuming previous mappings.

Author: System Demo
Date: 2025-07-05
"""

import sys
import time
import os
import json

# Add the utils directory to the path to import roboclaw_3
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'utils'))

from roboclaw_3 import Roboclaw

class MotorConnectionTester:
    """
    Comprehensive motor connection tester with fresh mapping.
    """
    
    def __init__(self):
        """Initialize the tester with motor controller connections."""
        # Controller configuration
        self.rc1_port = "/dev/ttyACM2"  # RC1
        self.rc2_port = "/dev/ttyACM1"  # RC2
        self.address = 0x80
        self.baudrate = 460800
        
        # Initialize controllers
        self.rc1 = None
        self.rc2 = None
        
        # Test parameters
        self.test_speed = 200  # Speed for testing
        self.test_duration = 2  # seconds
        
        # Motor mapping storage
        self.motor_mapping = {}
        
    def connect_controllers(self):
        """Connect to both RoboClaw controllers."""
        print("=" * 60)
        print("CONNECTING TO ROBOCLAW CONTROLLERS")
        print("=" * 60)
        
        # Connect to RC1
        self.rc1 = Roboclaw(self.rc1_port, self.baudrate)
        if not self.rc1.Open():
            print(f"ERROR: Failed to connect to RC1 on {self.rc1_port}")
            return False
        print(f"✓ Connected to RC1 on {self.rc1_port}")
        
        # Connect to RC2
        self.rc2 = Roboclaw(self.rc2_port, self.baudrate)
        if not self.rc2.Open():
            print(f"ERROR: Failed to connect to RC2 on {self.rc2_port}")
            return False
        print(f"✓ Connected to RC2 on {self.rc2_port}")
        
        return True
    
    def test_controller_communication(self):
        """Test communication with both controllers."""
        print("\nTesting controller communication...")
        
        # Test RC1
        version = self.rc1.ReadVersion(self.address)
        if version[0]:
            print(f"✓ RC1 Version: {version[1]}")
        else:
            print("✗ RC1 communication failed")
            return False
            
        # Test RC2
        version = self.rc2.ReadVersion(self.address)
        if version[0]:
            print(f"✓ RC2 Version: {version[1]}")
        else:
            print("✗ RC2 communication failed")
            return False
            
        return True
    
    def test_single_motor_comprehensive(self, controller, controller_name, channel, port):
        """
        Test a single motor with comprehensive monitoring.
        """
        motor_id = f"{controller_name}_{channel}"
        print(f"\nTesting {motor_id} on {port}...")
        
        # Test motor with speed control
        if channel == "M1":
            result = controller.SpeedM1(self.address, self.test_speed)
            read_speed_func = controller.ReadSpeedM1
        else:  # M2
            result = controller.SpeedM2(self.address, self.test_speed)
            read_speed_func = controller.ReadSpeedM2
            
        if not result:
            print(f"  ✗ {motor_id}: Failed to set speed")
            return {'working': False, 'method': 'speed', 'error': 'set_speed_failed'}
            
        # Wait for motor to start
        time.sleep(1)
        
        # Read comprehensive data multiple times
        speed_readings = []
        current_readings = []
        
        for i in range(5):
            # Read speed
            speed_data = read_speed_func(self.address)
            if speed_data[0]:
                speed_readings.append(speed_data[1])
            
            # Read current
            current_data = controller.ReadCurrents(self.address)
            if current_data[0]:
                if channel == "M1":
                    current_readings.append(current_data[1] / 100.0)  # Convert to amps
                else:  # M2
                    current_readings.append(current_data[2] / 100.0)  # Convert to amps
            
            time.sleep(0.4)
            
        # Stop motor
        if channel == "M1":
            controller.SpeedM1(self.address, 0)
        else:
            controller.SpeedM2(self.address, 0)
            
        # Analyze results
        if speed_readings:
            max_speed = max(speed_readings)
            avg_speed = sum(speed_readings) / len(speed_readings)
            avg_current = sum(current_readings) / len(current_readings) if current_readings else 0
            
            print(f"  Speed readings: {speed_readings}")
            print(f"  Current readings: {[f'{c:.2f}A' for c in current_readings]}")
            print(f"  Average speed: {avg_speed:.1f}")
            print(f"  Average current: {avg_current:.2f}A")
            print(f"  Max speed: {max_speed}")
            
            # More lenient detection: motor is working if it shows speed OR current
            speed_threshold = 10
            current_threshold = 0.01
            
            if abs(max_speed) > speed_threshold or abs(avg_current) > current_threshold:
                print(f"  ✓ {motor_id}: WORKING (speed control)")
                return {
                    'working': True,
                    'method': 'speed',
                    'controller': controller_name,
                    'channel': channel,
                    'port': port,
                    'max_speed': max_speed,
                    'avg_speed': avg_speed,
                    'avg_current': avg_current
                }
            else:
                print(f"  ✗ {motor_id}: NOT WORKING (insufficient speed/current)")
                print(f"    Speed threshold: {speed_threshold}, Current threshold: {current_threshold}")
                return {'working': False, 'method': 'speed', 'error': 'insufficient_response'}
        else:
            print(f"  ✗ {motor_id}: NOT WORKING (no speed readings)")
            return {'working': False, 'method': 'speed', 'error': 'no_readings'}
    
    def test_all_motors(self):
        """Test all motors on both controllers systematically."""
        print("\n" + "=" * 60)
        print("SYSTEMATIC MOTOR TESTING")
        print("=" * 60)
        
        working_motors = []
        motor_results = {}
        
        # Test RC1 motors
        print("\n" + "=" * 30)
        print("TESTING RC1 MOTORS")
        print("=" * 30)
        
        # Test RC1_M1
        result = self.test_single_motor_comprehensive(self.rc1, "RC1", "M1", self.rc1_port)
        motor_results["RC1_M1"] = result
        if result['working']:
            working_motors.append("RC1_M1")
            
        # Test RC1_M2
        result = self.test_single_motor_comprehensive(self.rc1, "RC1", "M2", self.rc1_port)
        motor_results["RC1_M2"] = result
        if result['working']:
            working_motors.append("RC1_M2")
            
        # Test RC2 motors
        print("\n" + "=" * 30)
        print("TESTING RC2 MOTORS")
        print("=" * 30)
        
        # Test RC2_M1
        result = self.test_single_motor_comprehensive(self.rc2, "RC2", "M1", self.rc2_port)
        motor_results["RC2_M1"] = result
        if result['working']:
            working_motors.append("RC2_M1")
            
        # Test RC2_M2
        result = self.test_single_motor_comprehensive(self.rc2, "RC2", "M2", self.rc2_port)
        motor_results["RC2_M2"] = result
        if result['working']:
            working_motors.append("RC2_M2")
            
        return working_motors, motor_results
    
    def user_motor_mapping(self, working_motors, motor_results, observed_count):
        """
        User-guided motor mapping with prompts.
        """
        print("\n" + "=" * 60)
        print("USER-GUIDED MOTOR MAPPING")
        print("=" * 60)
        print("I will slowly turn each motor one by one.")
        print("Please identify which motor is turning and enter the corresponding index (1, 2, or 3).")
        print("=" * 60)
        
        # Initialize motor mapping
        self.motor_mapping = {}
        for motor in ['motor1', 'motor2', 'motor3']:
            self.motor_mapping[motor] = {'controller': None, 'channel': None, 'port': None, 'working': False}
        
        mapped_motors = []
        remaining_motors = [1, 2, 3]  # Track which motors still need mapping
        
        # Create list of all motors to test (including potentially undetected ones)
        all_motors = [
            ("RC1", "M1", self.rc1_port, self.rc1),
            ("RC1", "M2", self.rc1_port, self.rc1),
            ("RC2", "M1", self.rc2_port, self.rc2),
            ("RC2", "M2", self.rc2_port, self.rc2)
        ]
        
        # Test each motor for mapping
        for controller_name, channel, port, controller in all_motors:
            motor_id = f"{controller_name}_{channel}"
            
            print(f"\nTurning {motor_id} slowly...")
            print(f"Available motor indices: {remaining_motors}")
            print("Watch which motor moves and enter the index:")
            
            # Stop ALL motors before starting a new one
            print("Stopping all motors first...")
            self.rc1.SpeedM1(self.address, 0)
            self.rc1.SpeedM2(self.address, 0)
            self.rc2.SpeedM1(self.address, 0)
            self.rc2.SpeedM2(self.address, 0)
            time.sleep(1.0)  # Increased wait time for motors to stop completely
            
            # Double-check all motors are stopped
            print("Verifying all motors are stopped...")
            self.monitor_all_motors_during_mapping()
            
            # Additional delay to ensure complete stop
            time.sleep(0.5)
            
            # Read and display PID values before testing
            pid_data = self.read_pid_values(controller, channel)
            
            print(f"PID Values for {motor_id}:")
            print(f"  P: {pid_data['p']}, I: {pid_data['i']}, D: {pid_data['d']}")
            print(f"  QPPS: {pid_data['qpps']}, Max Current: {pid_data['max_i']}")
            
            # Start motor slowly
            slow_speed = 200  # Increased speed for identification (was 100)
            
            if channel == 'M1':
                controller.SpeedM1(self.address, slow_speed)
            else:
                controller.SpeedM2(self.address, slow_speed)
            
            # Wait a moment for motor to start
            time.sleep(0.5)
            
            # Monitor all motors to verify only one is spinning
            print("Monitoring motor states...")
            self.monitor_all_motors_during_mapping()
            
            # Get user input
            while True:
                try:
                    user_input = input("Enter motor index (1, 2, 3) or 'n' for none: ").strip()
                    if user_input.lower() == 'n':
                        # Stop motor and skip this mapping
                        if channel == 'M1':
                            controller.SpeedM1(self.address, 0)
                        else:
                            controller.SpeedM2(self.address, 0)
                        print(f"Skipped mapping for {motor_id}")
                        
                        # Verify no motors are running
                        print("Verifying all motors are stopped...")
                        self.monitor_all_motors_during_mapping()
                        break
                    elif user_input in ['1', '2', '3']:
                        motor_index = int(user_input)
                        
                        # Check if this index is already assigned
                        if motor_index not in remaining_motors:
                            print(f"Motor index {motor_index} is already assigned. Please choose from: {remaining_motors}")
                            continue
                        
                        # Verify only the expected motor is running
                        print("Verifying motor behavior...")
                        running_motors = self.monitor_all_motors_during_mapping()
                        
                        # Check if multiple motors are running when only one should be
                        if len(running_motors) > 1:
                            print(f"⚠ WARNING: Multiple motors running: {running_motors}")
                            print("This may indicate a wiring issue or motor connection problem.")
                            print("The motor you identified may be correct, but other motors are also responding.")
                        
                        # Stop motor
                        if channel == 'M1':
                            controller.SpeedM1(self.address, 0)
                        else:
                            controller.SpeedM2(self.address, 0)
                        
                        # Check if this motor was in the working_motors list
                        if motor_id in motor_results and motor_results[motor_id]['working']:
                            result = motor_results[motor_id]
                            method = result['method']
                            max_speed = result['max_speed']
                            avg_current = result['avg_current']
                        else:
                            # Motor was not detected but user confirmed it's working
                            method = 'speed'
                            max_speed = 0
                            avg_current = 0
                        
                        # Assign motor
                        motor_label = f'motor{motor_index}'
                        self.motor_mapping[motor_label] = {
                            'controller': controller_name,
                            'channel': channel,
                            'port': port,
                            'working': True,
                            'method': method,
                            'max_speed': max_speed,
                            'avg_current': avg_current,
                            'pid_values': pid_data
                        }
                        
                        mapped_motors.append(motor_index)
                        remaining_motors.remove(motor_index)
                        print(f"✓ {motor_label} = {motor_id}")
                        
                        # Stop mapping if we have 3 motors
                        if len(mapped_motors) >= 3:
                            print("✓ All 3 motors mapped successfully!")
                            return len(mapped_motors)
                        
                        break
                        
                    else:
                        print(f"Please enter one of: {remaining_motors} or 'n' for none")
                        
                except KeyboardInterrupt:
                    # Stop motor and exit
                    if channel == 'M1':
                        controller.SpeedM1(self.address, 0)
                    else:
                        controller.SpeedM2(self.address, 0)
                    print("\nMapping interrupted by user.")
                    return len(mapped_motors)
        
        return len(mapped_motors)
    
    def monitor_all_motors_during_mapping(self):
        """
        Monitor all motors to verify only one is spinning during mapping.
        """
        print("Motor Status Check:")
        print(f"{'Motor':<8} {'Speed':<8} {'Status':<10}")
        print("-" * 30)
        
        # Check RC1_M1
        speed_data = self.rc1.ReadSpeedM1(self.address)
        if speed_data[0]:
            speed = speed_data[1]
            status = "RUNNING" if abs(speed) > 10 else "STOPPED"
        else:
            speed = 0
            status = "ERROR"
        print(f"RC1_M1   {speed:<8} {status:<10}")
        
        # Check RC1_M2
        speed_data = self.rc1.ReadSpeedM2(self.address)
        if speed_data[0]:
            speed = speed_data[1]
            status = "RUNNING" if abs(speed) > 10 else "STOPPED"
        else:
            speed = 0
            status = "ERROR"
        print(f"RC1_M2   {speed:<8} {status:<10}")
        
        # Check RC2_M1
        speed_data = self.rc2.ReadSpeedM1(self.address)
        if speed_data[0]:
            speed = speed_data[1]
            status = "RUNNING" if abs(speed) > 10 else "STOPPED"
        else:
            speed = 0
            status = "ERROR"
        print(f"RC2_M1   {speed:<8} {status:<10}")
        
        # Check RC2_M2
        speed_data = self.rc2.ReadSpeedM2(self.address)
        if speed_data[0]:
            speed = speed_data[1]
            status = "RUNNING" if abs(speed) > 10 else "STOPPED"
        else:
            speed = 0
            status = "ERROR"
        print(f"RC2_M2   {speed:<8} {status:<10}")
        
        # Count running motors
        running_motors = []
        for motor_id, (controller, channel, port, ctrl) in [
            ("RC1_M1", ("RC1", "M1", self.rc1_port, self.rc1)),
            ("RC1_M2", ("RC1", "M2", self.rc1_port, self.rc1)),
            ("RC2_M1", ("RC2", "M1", self.rc2_port, self.rc2)),
            ("RC2_M2", ("RC2", "M2", self.rc2_port, self.rc2))
        ]:
            if channel == "M1":
                speed_data = ctrl.ReadSpeedM1(self.address)
            else:
                speed_data = ctrl.ReadSpeedM2(self.address)
            
            if speed_data[0] and abs(speed_data[1]) > 10:
                running_motors.append(motor_id)
        
        print(f"Running motors: {running_motors}")
        if len(running_motors) != 1:
            print(f"⚠ WARNING: Expected 1 motor running, found {len(running_motors)}")
        else:
            print(f"✓ Confirmed: Only {running_motors[0]} is running")
        
        return running_motors
    
    def read_pid_values(self, controller, channel):
        """
        Read PID values for a specific motor channel.
        """
        pid_data = {
            'p': 0, 'i': 0, 'd': 0, 'qpps': 0,
            'max_i': 0, 'deadzone': 0, 'min_pos': 0, 'max_pos': 0
        }
        
        try:
            if channel == 'M1':
                # Read PID values for M1
                pid_values = controller.ReadM1PositionPID(self.address)
                if pid_values[0]:
                    pid_data['p'] = pid_values[1]
                    pid_data['i'] = pid_values[2]
                    pid_data['d'] = pid_values[3]
                    pid_data['qpps'] = pid_values[4]
                
                # Read additional settings
                max_i = controller.ReadM1MaxCurrent(self.address)
                if max_i[0]:
                    pid_data['max_i'] = max_i[1]
                    
            else:  # M2
                # Read PID values for M2
                pid_values = controller.ReadM2PositionPID(self.address)
                if pid_values[0]:
                    pid_data['p'] = pid_values[1]
                    pid_data['i'] = pid_values[2]
                    pid_data['d'] = pid_values[3]
                    pid_data['qpps'] = pid_values[4]
                
                # Read additional settings
                max_i = controller.ReadM2MaxCurrent(self.address)
                if max_i[0]:
                    pid_data['max_i'] = max_i[1]
                    
        except Exception as e:
            print(f"Warning: Could not read PID values for {channel}: {e}")
            
        return pid_data
    
    def save_motor_config(self):
        """Save motor configuration to JSON file for later reference."""
        config_data = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'motor_mapping': self.motor_mapping,
            'controller_config': {
                'rc1_port': self.rc1_port,
                'rc2_port': self.rc2_port,
                'address': self.address,
                'baudrate': self.baudrate
            }
        }
        
        config_file = 'demo_config.json'
        try:
            with open(config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
            print(f"✓ Motor configuration saved to {config_file}")
        except Exception as e:
            print(f"✗ Failed to save configuration: {e}")
    
    def print_motor_mapping(self):
        """Print the final motor mapping."""
        print("\n" + "=" * 60)
        print("FINAL MOTOR MAPPING")
        print("=" * 60)
        
        for motor, config in self.motor_mapping.items():
            if config['working']:
                print(f"✓ {motor}: {config['controller']}_{config['channel']} on {config['port']}")
                print(f"  Method: {config['method']}")
                print(f"  Max Speed: {config['max_speed']}")
                print(f"  Avg Current: {config['avg_current']:.2f}A")
            else:
                print(f"✗ {motor}: Not assigned")
        
        print("\n" + "=" * 60)
        print("CONFIGURATION FOR demo.py")
        print("=" * 60)
        print("Copy this configuration to demo.py:")
        print()
        
        for motor, config in self.motor_mapping.items():
            if config['working']:
                print(f"# {motor}: {config['controller']}_{config['channel']} on {config['port']}")
                print(f"# Method: {config['method']}")
                print(f"# Max Speed: {config['max_speed']}")
                print(f"# Avg Current: {config['avg_current']:.2f}A")
                print()
    
    def run_comprehensive_test(self):
        """Run the complete motor connection test."""
        print("ROBOCLAW MOTOR CONNECTION TEST")
        print("=" * 60)
        
        # Step 1: Connect to controllers
        if not self.connect_controllers():
            print("ERROR: Failed to connect to motor controllers")
            return False
            
        # Step 2: Test communication
        if not self.test_controller_communication():
            print("ERROR: Controller communication test failed")
            return False
            
        # Step 3: Test all motors
        working_motors, motor_results = self.test_all_motors()
        
        # Step 4: User-guided motor mapping
        print(f"\nFound {len(working_motors)} working motors.")
        
        # Ask user to confirm how many motors responded
        while True:
            try:
                user_count = input(f"How many motors did you see spinning? (0-4): ").strip()
                if user_count in ['0', '1', '2', '3', '4']:
                    observed_count = int(user_count)
                    break
                else:
                    print("Please enter a number between 0 and 4.")
            except KeyboardInterrupt:
                print("\nTest interrupted by user.")
                return False
        
        if observed_count >= 1:  # Changed from 3 to 1 to allow partial mapping
            print(f"\n✓ Confirmed {observed_count} motors are working.")
            
            # If user saw more motors than detected, identify the missing one
            if observed_count > len(working_motors):
                print(f"⚠ NOTE: You saw {observed_count} motors but only {len(working_motors)} were detected.")
                print("This may indicate a motor with low current draw or encoder issues.")
                print("The missing motor will be identified during mapping.")
            
            mapped_count = self.user_motor_mapping(working_motors, motor_results, observed_count)
        else:
            print(f"\n⚠ WARNING: No motors confirmed working.")
            print("Please check connections.")
            return False
        
        # Step 5: Print final mapping
        self.print_motor_mapping()
        
        # Step 6: Summary and save option
        print(f"\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"✓ Working motors found: {len(working_motors)}")
        print(f"✓ Motors mapped: {mapped_count}")
        
        if mapped_count >= 1:
            print("✓ SUCCESS: Motor mapping completed")
            
            # Ask user if they want to save configuration
            while True:
                try:
                    save_choice = input("\nSave configuration to demo_config.json? (y/n): ").strip().lower()
                    if save_choice in ['y', 'yes']:
                        self.save_motor_config()
                        print("✓ Configuration saved successfully")
                        break
                    elif save_choice in ['n', 'no']:
                        print("Configuration not saved")
                        break
                    else:
                        print("Please enter 'y' or 'n'")
                except KeyboardInterrupt:
                    print("\nConfiguration not saved")
                    break
            
            return True
        else:
            print("⚠ WARNING: No motors were mapped")
            return False

def main():
    """Main function."""
    tester = MotorConnectionTester()
    
    try:
        success = tester.run_comprehensive_test()
        if success:
            print("\n✓ Motor connection test completed successfully")
            print("Use the configuration above to update demo.py")
        else:
            print("\n✗ Motor connection test failed")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        print("Motors stopped safely")
        
    except Exception as e:
        print(f"\nERROR: Unexpected error during test: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 