#!/usr/bin/env python3
"""
RoboClaw Motor Demo Script
==========================

Simplified demo script focused on step response testing.
Run demo_test.py first to determine correct motor mapping.

Author: System Demo
Date: 2025-07-02
"""

import sys
import time
import os
import json

# Add the utils directory to the path to import roboclaw_3
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'utils'))

from roboclaw_3 import Roboclaw

class RoboClawDemo:
    """
    Simplified RoboClaw demo focused on step response testing.
    """
    
    def __init__(self):
        """Initialize the demo with motor controller connections."""
        # Controller configuration
        self.rc1_port = "/dev/ttyACM2"  # RC1
        self.rc2_port = "/dev/ttyACM1"  # RC2
        self.address = 0x80
        self.baudrate = 460800
        
        # Initialize controllers
        self.rc1 = None
        self.rc2 = None
        
        # MOTOR CONFIGURATION - Updated based on user's hardware setup
        # Motor 1: RC1, Motor 2 & 3: RC2
        self.motor_config = {
            'motor1': {'controller': 'RC1', 'channel': 'M1', 'speed': 400},
            'motor2': {'controller': 'RC2', 'channel': 'M1', 'speed': 400},
            'motor3': {'controller': 'RC2', 'channel': 'M2', 'speed': 400}
        }
        
        # Demo parameters
        self.motion_duration = 2   # seconds for each direction (changed from 5)
        self.pause_duration = 1    # seconds pause between directions (changed from 2)
        self.cycles = 3            # default number of cycles (changed from 2)
        self.monitor_interval = 1  # seconds
        self.command_delay = 0.2   # increased delay between commands to prevent overload
        self.stop_delay = 1.0      # increased delay after stop commands to ensure motors stop
        
        # Load configuration from file if available
        self.load_config()
        
    def load_config(self):
        """Load motor configuration from demo_config.json if available."""
        config_file = 'demo_config.json'
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    config_data = json.load(f)
                
                # Update motor mapping if available
                if 'motor_mapping' in config_data:
                    for motor, config in config_data['motor_mapping'].items():
                        if config['working']:
                            self.motor_config[motor] = {
                                'controller': config['controller'],
                                'channel': config['channel'],
                                'speed': 400  # Default speed
                            }
                        else:
                            # Remove non-working motors from config
                            if motor in self.motor_config:
                                del self.motor_config[motor]
                    print(f"✓ Loaded motor configuration from {config_file}")
            except Exception as e:
                print(f"⚠ Warning: Could not load config file: {e}")
        
    def connect_controllers(self):
        """Connect to both RoboClaw controllers."""
        print("Connecting to RoboClaw controllers...")
        
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
    
    def get_demo_parameters(self):
        """Get demo parameters from user input."""
        print("\n" + "=" * 50)
        print("MOTION DEMO CONFIGURATION")
        print("=" * 50)
        
        # Get number of cycles
        while True:
            try:
                user_input = input(f"Number of cycles (default {self.cycles}): ").strip()
                
                if user_input == "":
                    cycles = self.cycles
                    print(f"  Using default: {cycles}")
                    break
                else:
                    cycles = int(user_input)
                    if cycles > 0:
                        print(f"  Set to: {cycles}")
                        break
                    else:
                        print("  Please enter a positive number.")
                        
            except ValueError:
                print("  Please enter a valid integer.")
            except KeyboardInterrupt:
                return None, None
        
        # Get motor speeds
        speeds = {}
        for motor_name, config in self.motor_config.items():
            while True:
                try:
                    default_speed = config['speed']
                    user_input = input(f"{motor_name} velocity (default {default_speed}): ").strip()
                    
                    if user_input == "":
                        speeds[motor_name] = default_speed
                        print(f"  Using default: {default_speed}")
                        break
                    else:
                        speed = int(user_input)
                        speeds[motor_name] = speed
                        print(f"  Set to: {speed}")
                        break
                        
                except ValueError:
                    print("  Please enter a valid integer.")
                except KeyboardInterrupt:
                    return None, None
        
        return cycles, speeds
    
    def get_continuous_parameters(self):
        """Get continuous mode parameters from user input."""
        print("\n" + "=" * 50)
        print("CONTINUOUS MODE CONFIGURATION")
        print("=" * 50)
        
        # Get duration
        while True:
            try:
                user_input = input("Duration in seconds (default 30): ").strip()
                
                if user_input == "":
                    duration = 30
                    print(f"  Using default: {duration} seconds")
                    break
                else:
                    duration = int(user_input)
                    if duration > 0:
                        print(f"  Set to: {duration} seconds")
                        break
                    else:
                        print("  Please enter a positive number.")
                        
            except ValueError:
                print("  Please enter a valid integer.")
            except KeyboardInterrupt:
                return None, None
        
        # Get motor speeds
        speeds = {}
        for motor_name, config in self.motor_config.items():
            while True:
                try:
                    default_speed = config['speed']
                    user_input = input(f"{motor_name} velocity (default {default_speed}): ").strip()
                    
                    if user_input == "":
                        speeds[motor_name] = default_speed
                        print(f"  Using default: {default_speed}")
                        break
                    else:
                        speed = int(user_input)
                        speeds[motor_name] = speed
                        print(f"  Set to: {speed}")
                        break
                        
                except ValueError:
                    print("  Please enter a valid integer.")
                except KeyboardInterrupt:
                    return None, None
        
        return duration, speeds
    
    def start_motors_step(self, speeds):
        """Start all motors with step response velocities sequentially."""
        print(f"\nStarting motors with step response (sequential execution)...")
        
        for motor_name, speed in speeds.items():
            config = self.motor_config[motor_name]
            controller = self.rc1 if config['controller'] == 'RC1' else self.rc2
            
            print(f"  Starting {motor_name} ({config['controller']}_{config['channel']}) at speed {speed}...")
            
            if config['channel'] == 'M1':
                result = controller.SpeedM1(self.address, speed)
            else:  # M2
                result = controller.SpeedM2(self.address, speed)
                
            if result:
                print(f"    ✓ {motor_name}: Started successfully")
            else:
                print(f"    ✗ {motor_name}: Failed to start")
            
            # Delay between commands to prevent controller overload
            time.sleep(self.command_delay)
    
    def stop_motors(self):
        """Stop all motors sequentially with enhanced stopping."""
        print("\nStopping all motors (sequential execution)...")
        
        for motor_name, config in self.motor_config.items():
            controller = self.rc1 if config['controller'] == 'RC1' else self.rc2
            
            print(f"  Stopping {motor_name} ({config['controller']}_{config['channel']})...")
            
            if config['channel'] == 'M1':
                result = controller.SpeedM1(self.address, 0)
            else:  # M2
                result = controller.SpeedM2(self.address, 0)
                
            if result:
                print(f"    ✓ {motor_name}: Stop command sent")
            else:
                print(f"    ✗ {motor_name}: Failed to send stop command")
            
            # Delay between commands
            time.sleep(self.command_delay)
        
        # Additional delay to ensure all motors stop completely
        print("  Waiting for motors to stop completely...")
        time.sleep(self.stop_delay)
        
        # Verify all motors are stopped
        print("  Verifying motor stop status...")
        for motor_name, config in self.motor_config.items():
            controller = self.rc1 if config['controller'] == 'RC1' else self.rc2
            
            if config['channel'] == 'M1':
                speed_data = controller.ReadSpeedM1(self.address)
            else:  # M2
                speed_data = controller.ReadSpeedM2(self.address)
                
            if speed_data[0] and abs(speed_data[1]) < 10:
                print(f"    ✓ {motor_name}: Confirmed stopped")
            else:
                print(f"    ⚠ {motor_name}: May still be running (speed: {speed_data[1] if speed_data[0] else 'ERROR'})")
    
    def read_motor_data(self, motor_name, config):
        """
        Read comprehensive motor data for a specific motor.
        
        Args:
            motor_name: Name of the motor
            config: Motor configuration dictionary
            
        Returns:
            dict: Motor data including speed, voltage, current, and error status
        """
        data = {
            'motor_name': motor_name,
            'controller': config['controller'],
            'channel': config['channel'],
            'speed': 0,
            'voltage': 0,
            'current': 0,
            'error': None,
            'success': False
        }
        
        # Select the correct controller
        controller = self.rc1 if config['controller'] == 'RC1' else self.rc2
        
        # Read speed from the correct channel
        if config['channel'] == 'M1':
            speed_data = controller.ReadSpeedM1(self.address)
        else:  # M2
            speed_data = controller.ReadSpeedM2(self.address)
            
        if speed_data[0]:
            data['speed'] = speed_data[1]
            data['success'] = True
        
        # Read voltage (same for both motors on a controller)
        voltage_data = controller.ReadMainBatteryVoltage(self.address)
        if voltage_data[0]:
            data['voltage'] = voltage_data[1] / 10.0  # Convert to volts
        
        # Read current for the specific motor
        current_data = controller.ReadCurrents(self.address)
        if current_data[0]:
            if config['channel'] == 'M1':
                data['current'] = current_data[1] / 100.0  # Convert to amps
            else:  # M2
                data['current'] = current_data[2] / 100.0  # Convert to amps
        
        # Read error status
        error_data = controller.ReadError(self.address)
        if error_data[0]:
            data['error'] = error_data[1]
        
        return data
    
    def monitor_motors(self):
        """Monitor all motors and display comprehensive data."""
        print("\n" + "=" * 100)
        print("MOTOR MONITORING")
        print("=" * 100)
        print(f"{'Motor':<8} {'Controller':<10} {'Channel':<8} {'Speed':<8} {'Voltage':<8} {'Current':<8} {'Error':<8} {'Status':<10}")
        print("-" * 100)
        
        # Read data for each motor individually
        for motor_name, config in self.motor_config.items():
            data = self.read_motor_data(motor_name, config)
            
            # Format status
            if data['success']:
                status = "RUNNING" if abs(data['speed']) > 10 else "STOPPED"
            else:
                status = "ERROR"
            
            # Format error with description
            if data['error'] is not None:
                if data['error'] == 0:
                    error_str = "OK"
                elif data['error'] == 0xC0000000:
                    error_str = "NO_ACK"
                elif data['error'] == 0x80000000:
                    error_str = "TIMEOUT"
                else:
                    error_str = f"0x{data['error']:08X}"
            else:
                error_str = "OK"
            
            print(f"{data['motor_name']:<8} {data['controller']:<10} {data['channel']:<8} {data['speed']:<8} {data['voltage']:<8.1f} {data['current']:<8.2f} {error_str:<8} {status:<10}")
    
    def run_motion_demo(self):
        """Run motion demo with positive/negative direction cycling."""
        print("\n" + "=" * 60)
        print("MOTION DEMO")
        print("=" * 60)
        
        # Get parameters from user
        cycles, speeds = self.get_demo_parameters()
        if cycles is None or speeds is None:
            print("Demo cancelled by user.")
            return False
        
        print(f"\nRunning motion demo:")
        print(f"  Cycles: {cycles}")
        print(f"  Motion duration: {self.motion_duration} seconds")
        print(f"  Pause duration: {self.pause_duration} seconds")
        print(f"  Command delay: {self.command_delay} seconds")
        print("  Note: Motor direction depends on encoder wiring and may vary")
        print("  Press Ctrl+C to stop early")
        
        try:
            for cycle in range(cycles):
                print(f"\n=== CYCLE {cycle + 1}/{cycles} ===")
                
                # Phase 1: Positive direction
                print(f"  Phase 1: Positive direction ({self.motion_duration}s)")
                self.start_motors_step(speeds)
                time.sleep(self.motion_duration)
                
                # Phase 2: Stop
                print(f"  Phase 2: Stop ({self.pause_duration}s)")
                self.stop_motors()
                time.sleep(self.pause_duration)
                
                # Phase 3: Negative direction
                print(f"  Phase 3: Negative direction ({self.motion_duration}s)")
                negative_speeds = {motor: -speed for motor, speed in speeds.items()}
                self.start_motors_step(negative_speeds)
                time.sleep(self.motion_duration)
                
                # Phase 4: Stop
                print(f"  Phase 4: Stop ({self.pause_duration}s)")
                self.stop_motors()
                
                # Only pause between cycles, not after the last cycle
                if cycle < cycles - 1:
                    time.sleep(self.pause_duration)
            
            # Ensure motors are stopped at the end
            print("Ensuring motors are stopped...")
            self.stop_motors()
            
            print("Motion demo completed!")
            return True
            
        except KeyboardInterrupt:
            print("\n\nDemo interrupted by user")
            self.stop_motors()
            return False
    
    def run_continuous_demo(self):
        """Run continuous mode with constant speed."""
        print("\n" + "=" * 60)
        print("CONTINUOUS MODE")
        print("=" * 60)
        
        # Get parameters from user
        duration, speeds = self.get_continuous_parameters()
        if duration is None or speeds is None:
            print("Continuous mode cancelled by user.")
            return False
        
        print(f"\nRunning continuous mode:")
        print(f"  Duration: {duration} seconds")
        print(f"  Command delay: {self.command_delay} seconds")
        print("  Press Ctrl+C to stop early")
        
        try:
            # Start motors
            print("Starting motors at constant speed...")
            self.start_motors_step(speeds)
            
            # Run for specified duration
            print(f"Running for {duration} seconds...")
            start_time = time.time()
            
            while time.time() - start_time < duration:
                remaining = duration - (time.time() - start_time)
                print(f"  Time remaining: {remaining:.1f}s", end='\r')
                time.sleep(1)
            
            print(f"\nDuration completed ({duration}s)")
            
            # Stop motors
            print("Stopping motors...")
            self.stop_motors()
            
            print("Continuous mode completed!")
            return True
            
        except KeyboardInterrupt:
            print("\n\nContinuous mode interrupted by user")
            self.stop_motors()
            return False
    
    def show_menu(self):
        """Display the main menu."""
        print("\n" + "=" * 60)
        print("ROBOCLAW MOTOR DEMO MENU")
        print("=" * 60)
        print("1. Motion Demo (Positive/Negative Direction Cycling)")
        print("2. Continuous Mode (Constant Speed)")
        print("3. Monitor Motors Only")
        print("4. Run Connectivity Test")
        print("5. Exit")
        print("=" * 60)
    
    def run_demo(self):
        """Run the main demo loop with menu."""
        print("=" * 60)
        print("ROBOCLAW MOTOR DEMO")
        print("=" * 60)
        print("Motor Configuration:")
        for motor_name, config in self.motor_config.items():
            print(f"  {motor_name}: {config['controller']}_{config['channel']} (default speed: {config['speed']})")
        print(f"Command delay: {self.command_delay} seconds")
        print("=" * 60)
        
        # Step 1: Connect to controllers
        if not self.connect_controllers():
            print("ERROR: Failed to connect to motor controllers")
            return False
            
        # Step 2: Test communication
        if not self.test_controller_communication():
            print("ERROR: Controller communication test failed")
            return False
        
        # Main menu loop
        while True:
            self.show_menu()
            
            try:
                choice = input("Enter your choice (1-5): ").strip()
                
                if choice == '1':
                    self.run_motion_demo()
                    
                elif choice == '2':
                    self.run_continuous_demo()
                    
                elif choice == '3':
                    print("\nMonitoring motors for 10 seconds...")
                    start_time = time.time()
                    while time.time() - start_time < 10:
                        self.monitor_motors()
                        time.sleep(1)
                    
                elif choice == '4':
                    print("\nRunning connectivity test...")
                    # Get the full path to demo_test.py
                    demo_test_path = os.path.join(os.path.dirname(__file__), 'demo_test.py')
                    result = os.system(f'python3 "{demo_test_path}"')
                    if result == 0:
                        print("✓ Connectivity test completed successfully")
                    else:
                        print("✗ Connectivity test failed")
                    
                elif choice == '5':
                    print("\nExiting demo...")
                    break
                    
                else:
                    print("Invalid choice. Please enter 1-5.")
                    
            except KeyboardInterrupt:
                print("\n\nDemo interrupted by user")
                self.stop_motors()
                break
                
            except Exception as e:
                print(f"\nERROR: Unexpected error: {e}")
                self.stop_motors()
                break
        
        return True

def main():
    """Main function."""
    demo = RoboClawDemo()
    
    try:
        success = demo.run_demo()
        if success:
            print("\n✓ Demo completed successfully")
        else:
            print("\n✗ Demo failed")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
        demo.stop_motors()
        print("Motors stopped safely")
        
    except Exception as e:
        print(f"\nERROR: Unexpected error during demo: {e}")
        demo.stop_motors()
        sys.exit(1)

if __name__ == "__main__":
    main()
