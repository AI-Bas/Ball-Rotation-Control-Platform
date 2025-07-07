#!/usr/bin/env python3
"""
Ball Rotation Control Platform - Hardware Test Script
====================================================

Simple hardware identification and connectivity testing.
Focuses on identifying RoboClaws and mapping motors to wheels.

Author: System Demo
Date: 2025-07-06
"""

import sys
import time
import os
import json
import argparse
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# Add the utils directory to the path to import modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'utils'))

from roboclaw_3 import Roboclaw

# =============================================================================
# TEST CONFIGURATION
# =============================================================================

# USB Connection Settings
RC1_PORT = "/dev/ttyACM0"  # First RoboClaw
RC2_PORT = "/dev/ttyACM1"  # Second RoboClaw
ADDRESS = 128              # RoboClaw address (0x80)
BAUDRATE = 460800          # Communication baudrate

# Test Parameters
HIGH_VELOCITY_PULSES = 1000  # pulses/s for motor response test
TEST_DURATION = 5.0          # seconds for motor response test

class HardwareTester:
    """Hardware identification and connectivity tester."""
    
    def __init__(self):
        """Initialize the tester."""
        self.rc1 = None
        self.rc2 = None
        self.connected = False
        self.config_file = "demo_config.json"
        
        print("✓ HardwareTester initialized")
        
    def connect_controllers(self):
        """Connect to both RoboClaw controllers."""
        print("=" * 50)
        print("CONNECTING TO ROBOCLAW CONTROLLERS")
        print("=" * 50)
        
        # Connect to RC1
        print(f"Connecting to RC1 on {RC1_PORT}...")
        self.rc1 = Roboclaw(RC1_PORT, BAUDRATE)
        if not self.rc1.Open():
            print(f"✗ Failed to connect to RC1 on {RC1_PORT}")
            return False
        print(f"✓ Connected to RC1 on {RC1_PORT}")
        
        # Connect to RC2
        print(f"Connecting to RC2 on {RC2_PORT}...")
        self.rc2 = Roboclaw(RC2_PORT, BAUDRATE)
        if not self.rc2.Open():
            print(f"✗ Failed to connect to RC2 on {RC2_PORT}")
            return False
        print(f"✓ Connected to RC2 on {RC2_PORT}")
        
        # Test communication
        print("\nTesting communication...")
        version1 = self.rc1.ReadVersion(ADDRESS)
        version2 = self.rc2.ReadVersion(ADDRESS)
        
        if version1[0]:
            print(f"✓ RC1 Version: {version1[1]}")
        else:
            print("✗ RC1 communication failed")
            return False
            
        if version2[0]:
            print(f"✓ RC2 Version: {version2[1]}")
        else:
            print("✗ RC2 communication failed")
            return False
        
        self.connected = True
        print("✓ All controllers connected and communicating")
        return True
    
    def get_error_description(self, error_code: int) -> str:
        """Get error description from RoboClaw error code."""
        error_descriptions = {
            0x000000: "Normal",
            0x000001: "M1 Over Current Warning",
            0x000002: "M2 Over Current Warning", 
            0x000004: "Emergency Stop",
            0x000008: "Temperature1 Error",
            0x000010: "Temperature2 Error",
            0x000020: "Main Battery High Voltage Error",
            0x000040: "Logic Battery High Voltage Error",
            0x000080: "Logic Battery Low Voltage Error",
            0x000100: "M1 Driver Fault Error",
            0x000200: "M2 Driver Fault Error",
            0x000400: "Main Battery High Voltage Warning",
            0x000800: "Main Battery Low Voltage Warning",
            0x001000: "Temperature1 Warning",
            0x002000: "Temperature2 Warning",
            0x004000: "M1 Home Error",
            0x008000: "M2 Home Error",
            0x010000: "M1 Position Error",
            0x020000: "M2 Position Error",
            0x040000: "M1 Current Error",
            0x080000: "M2 Current Error"
        }
        return error_descriptions.get(error_code, f"Unknown Error ({error_code})")
    
    def read_motor_data(self, controller: Roboclaw, channel: str) -> Dict:
        """Read motor data for a specific channel."""
        data = {
            'channel': channel,
            'pulses_s': 0,
            'current': 0.0,
            'voltage': 0.0,
            'error_state': 0,
            'success': False
        }
        
        # Read speed in pulses/s
        if channel == 'M1':
            speed_data = controller.ReadSpeedM1(ADDRESS)
        else:  # M2
            speed_data = controller.ReadSpeedM2(ADDRESS)
        
        if speed_data[0]:
            data['pulses_s'] = speed_data[1]
            data['success'] = True
        
        # Read current
        current_data = controller.ReadCurrents(ADDRESS)
        if current_data[0]:
            if channel == 'M1':
                data['current'] = current_data[1] / 100.0  # Convert to amps
            else:  # M2
                data['current'] = current_data[2] / 100.0  # Convert to amps
        
        # Read voltage (same for both motors on a controller)
        voltage_data = controller.ReadMainBatteryVoltage(ADDRESS)
        if voltage_data[0]:
            data['voltage'] = voltage_data[1] / 10.0  # Convert to volts
        
        # Read error state
        error_data = controller.ReadError(ADDRESS)
        if error_data[0]:
            data['error_state'] = error_data[1]
        
        return data
    
    def test_connectivity(self):
        """Test connectivity by reading values from all motors."""
        print("\n" + "=" * 50)
        print("CONNECTIVITY TEST")
        print("=" * 50)
        
        if not self.connected:
            print("✗ Controllers not connected")
            return False
        
        print("Reading motor data from all channels...")
        print(f"{'Controller':<8} {'Channel':<8} {'Pulses/s':<10} {'Current':<10} {'Voltage':<8} {'Error':<20}")
        print("-" * 70)
        
        # Test RC1
        rc1_m1_data = self.read_motor_data(self.rc1, 'M1')
        rc1_m2_data = self.read_motor_data(self.rc1, 'M2')
        
        # Test RC2
        rc2_m1_data = self.read_motor_data(self.rc2, 'M1')
        rc2_m2_data = self.read_motor_data(self.rc2, 'M2')
        
        # Display results
        all_data = [
            ('RC1', rc1_m1_data),
            ('RC1', rc1_m2_data),
            ('RC2', rc2_m1_data),
            ('RC2', rc2_m2_data)
        ]
        
        for controller_name, data in all_data:
            if data['success']:
                error_desc = self.get_error_description(data['error_state'])
                print(f"{controller_name:<8} {data['channel']:<8} {data['pulses_s']:<10} {data['current']:<10.2f}A {data['voltage']:<8.1f}V {error_desc:<20}")
            else:
                print(f"{controller_name:<8} {data['channel']:<8} {'ERROR':<10} {'ERROR':<10} {'ERROR':<8} {'ERROR':<20}")
        
        print("=" * 70)
        print("✓ Connectivity test completed")
        return True
    
    def test_motor_response(self):
        """Test motor response by sending high velocity setpoints."""
        print("\n" + "=" * 50)
        print("MOTOR RESPONSE TEST")
        print("=" * 50)
        print(f"Testing each motor with {HIGH_VELOCITY_PULSES} pulses/s for {TEST_DURATION} seconds")
        print("=" * 50)
        
        if not self.connected:
            print("✗ Controllers not connected")
            return False
        
        # Test each motor channel individually
        test_channels = [
            ('RC1', 'M1', self.rc1),
            ('RC1', 'M2', self.rc1),
            ('RC2', 'M1', self.rc2),
            ('RC2', 'M2', self.rc2)
        ]
        
        for controller_name, channel, controller in test_channels:
            print(f"\nTesting {controller_name}_{channel}...")
            
            # Send high velocity command
            if channel == 'M1':
                result = controller.SpeedM1(ADDRESS, HIGH_VELOCITY_PULSES)
            else:  # M2
                result = controller.SpeedM2(ADDRESS, HIGH_VELOCITY_PULSES)
            
            if not result:
                print(f"✗ Failed to send command to {controller_name}_{channel}")
                continue
            
            print(f"✓ Command sent to {controller_name}_{channel}")
            print("Monitoring response for 2 seconds...")
            
            # Monitor response
            start_time = time.time()
            while time.time() - start_time < 2.0:
                data = self.read_motor_data(controller, channel)
                if data['success']:
                    print(f"  {controller_name}_{channel}: {data['pulses_s']} pulses/s, {data['current']:.2f}A, {data['voltage']:.1f}V")
                else:
                    print(f"  {controller_name}_{channel}: ERROR reading data")
                time.sleep(0.5)
            
            # Stop motor
            if channel == 'M1':
                controller.SpeedM1(ADDRESS, 0)
            else:  # M2
                controller.SpeedM2(ADDRESS, 0)
            
            print(f"✓ {controller_name}_{channel} test completed")
            time.sleep(1.0)  # Brief pause between tests
        
        print("\n✓ Motor response test completed")
        return True
    
    def identify_wheel_mapping(self):
        """Identify which wheel is connected to which motor channel."""
        print("\n" + "=" * 50)
        print("WHEEL MAPPING IDENTIFICATION")
        print("=" * 50)
        print("This test will spin each motor and ask you to identify which wheel is turning.")
        print("=" * 50)
        
        if not self.connected:
            print("✗ Controllers not connected")
            return False
        
        wheel_mapping = {}
        test_channels = [
            ('RC1', 'M1', self.rc1),
            ('RC1', 'M2', self.rc1),
            ('RC2', 'M1', self.rc2),
            ('RC2', 'M2', self.rc2)
        ]
        
        for controller_name, channel, controller in test_channels:
            print(f"\nSpinning {controller_name}_{channel}...")
            
            # Send moderate velocity command
            test_pulses = 500  # Moderate speed
            if channel == 'M1':
                result = controller.SpeedM1(ADDRESS, test_pulses)
            else:  # M2
                result = controller.SpeedM2(ADDRESS, test_pulses)
            
            if not result:
                print(f"✗ Failed to send command to {controller_name}_{channel}")
                continue
            
            print(f"✓ {controller_name}_{channel} is spinning")
            print("Which wheel is turning?")
            print("1. W1")
            print("2. W2") 
            print("3. W3")
            print("0. None (skip)")
            
            try:
                choice = input("Enter your choice (0-3): ").strip()
                if choice == '1':
                    wheel_mapping[f"{controller_name}_{channel}"] = 'W1'
                elif choice == '2':
                    wheel_mapping[f"{controller_name}_{channel}"] = 'W2'
                elif choice == '3':
                    wheel_mapping[f"{controller_name}_{channel}"] = 'W3'
                else:
                    print(f"Skipping {controller_name}_{channel}")
            except (ValueError, KeyboardInterrupt):
                print(f"Skipping {controller_name}_{channel}")
            
            # Stop motor
            if channel == 'M1':
                controller.SpeedM1(ADDRESS, 0)
            else:  # M2
                controller.SpeedM2(ADDRESS, 0)
            
            time.sleep(2.0)  # Wait between tests
        
        # Display identified mapping
        print("\n" + "=" * 50)
        print("IDENTIFIED WHEEL MAPPING")
        print("=" * 50)
        if wheel_mapping:
            for motor, wheel in wheel_mapping.items():
                print(f"{motor} → {wheel}")
        else:
            print("No wheel mapping identified")
        
        # Ask to save to config
        if wheel_mapping:
            self.save_wheel_mapping(wheel_mapping)
        
        print("✓ Wheel mapping identification completed")
        return True
    
    def save_wheel_mapping(self, wheel_mapping: Dict[str, str]):
        """Save wheel mapping to demo_config.json."""
        print(f"\nSaving wheel mapping to {self.config_file}...")
        
        # Load existing config
        config = {}
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
            except Exception as e:
                print(f"Warning: Could not load existing config: {e}")
        
        # Create wheel mapping in correct format
        wheel_config = {}
        for motor, wheel in wheel_mapping.items():
            controller_name, channel = motor.split('_')
            port = RC1_PORT if controller_name == 'RC1' else RC2_PORT
            
            wheel_config[wheel] = {
                "controller": controller_name,
                "channel": channel,
                "port": port,
                "working": True
            }
        
        # Update config
        config['wheel_mapping'] = wheel_config
        config['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Save config
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            print(f"✓ Wheel mapping saved to {self.config_file}")
        except Exception as e:
            print(f"✗ Failed to save config: {e}")
    
    def run_all_tests(self):
        """Run all hardware tests."""
        print("HARDWARE IDENTIFICATION AND TESTING")
        print("=" * 50)
        
        # Connect to controllers
        if not self.connect_controllers():
            print("ERROR: Failed to connect to controllers")
            return False
        
        # Run tests
        tests = [
            ("Connectivity Test", self.test_connectivity),
            ("Motor Response Test", self.test_motor_response),
            ("Wheel Mapping Identification", self.identify_wheel_mapping)
        ]
        
        for test_name, test_func in tests:
            print(f"\n{'='*20} {test_name} {'='*20}")
            try:
                success = test_func()
                if success:
                    print(f"✓ {test_name} completed successfully")
                else:
                    print(f"✗ {test_name} failed")
            except Exception as e:
                print(f"✗ {test_name} failed with error: {e}")
        
        print("\n" + "=" * 50)
        print("ALL TESTS COMPLETED")
        print("=" * 50)
        return True

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Hardware Identification and Testing')
    parser.add_argument('--connectivity', action='store_true', help='Run connectivity test only')
    parser.add_argument('--motor-response', action='store_true', help='Run motor response test only')
    parser.add_argument('--wheel-mapping', action='store_true', help='Run wheel mapping identification only')
    
    args = parser.parse_args()
    
    tester = HardwareTester()
    
    try:
        if not tester.connect_controllers():
            print("ERROR: Failed to connect to controllers")
            sys.exit(1)
        
        if args.connectivity:
            tester.test_connectivity()
        elif args.motor_response:
            tester.test_motor_response()
        elif args.wheel_mapping:
            tester.identify_wheel_mapping()
        else:
            # Run all tests
            success = tester.run_all_tests()
            if not success:
                sys.exit(1)
                
    except KeyboardInterrupt:
        print("\n\nTesting interrupted by user")
        print("Stopping all motors...")
        if tester.rc1:
            tester.rc1.SpeedM1(ADDRESS, 0)
            tester.rc1.SpeedM2(ADDRESS, 0)
        if tester.rc2:
            tester.rc2.SpeedM1(ADDRESS, 0)
            tester.rc2.SpeedM2(ADDRESS, 0)
        print("Motors stopped safely")
        
    except Exception as e:
        print(f"\nERROR: Unexpected error during testing: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 