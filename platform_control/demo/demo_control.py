#!/usr/bin/env python3
"""
Ball Rotation Control Platform - Demo Control Script
===================================================

This script provides a robust, menu-driven demo and test interface for the Ball Rotation Control Platform.

Features:
- Rolling motion demo: Runs a sequence of 8 setpoint vectors (scaled by user input Q) in a loop, each for 5 seconds with brief stops, until stopped.
- Rolling step response demo: Alternates between forward and reverse translation velocities for a set number of cycles, with brief stops between.
- Continuous rolling motion: Accepts user input velocity vectors (vX vY) and keeps the setpoint active until new input or stop command.
- Wheel calibration: Spins a selected wheel at a set angular velocity, measures RPM, and saves calibration data.
- Status display: Prints a consolidated table of wheel and ball status, including error codes and descriptions.
- Development mode: Toggle to enable/disable detailed troubleshooting messages (default ON).
- E-stop detection: Highlights emergency stop errors and prompts for reset.

All kinematic and transmission conversions are centralized in kinematic_conversion.py.
Wheel addressing is explicit and consistent (W1, W2, W3) to avoid mapping errors.

Menu Options:
1. Rolling Motion Demo
2. Rolling Step Response Demo
3. Continuous Rolling Motion
4. Wheel Calibration
5. Status Display
6. Stop All Wheels
7. Toggle Development Mode
8. Exit

Usage:
- Run interactively for menu, or use command-line arguments for direct demo execution.
- All parameters and calibration data are saved in demo_config.json.

For further details on system architecture, kinematics, and demo usage, see:
- docs/system_architecture_diagrams.md
- docs/system_design.md

Author: System Demo
Date: 2025-07-06
"""

import sys
import time
import os
import math
import json
import numpy as np
import argparse
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# Add the utils directory to the path to import modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'utils'))

from roboclaw_3 import Roboclaw
from kinematic_conversion import (
    jacobian, translation_to_rotation, rotation_to_wheel_velocities,
    wheel_velocities_to_rotation, wheel_velocity_to_encoder_pulses,
    encoder_pulses_to_wheel_velocity, calculate_velocity_error
)

# =============================================================================
# PLATFORM CONSTANTS (SI UNITS) - From streamlined_demo.py
# =============================================================================

# Physical dimensions
WHEEL_DIAMETER = 0.1  # meters
WHEEL_RADIUS = WHEEL_DIAMETER / 2.0  # meters
BALL_RADIUS = 0.111  # meters

# Transmission parameters
TRANSMISSION_RATIO = 13.0 / 3.0  # encoder_rev / wheel_rev
ENCODER_PULSES_PER_REV = 512  # pulses per encoder revolution

# Control loop parameters
CONTROL_LOOP_FREQUENCY = 5.0  # Hz
CONTROL_LOOP_PERIOD = 1.0 / CONTROL_LOOP_FREQUENCY  # seconds

# USB Connection Settings
RC1_PORT = "/dev/ttyACM0"  # First RoboClaw
RC2_PORT = "/dev/ttyACM1"  # Second RoboClaw
ADDRESS = 128              # RoboClaw address (0x80)
BAUDRATE = 460800          # Communication baudrate

# Wheel to Motor Channel Mapping - FROM STREAMLINED_DEMO.PY
WHEEL_CONFIG = {
    'W1': {'controller': 'RC1', 'channel': 'M1', 'port': RC1_PORT},
    'W2': {'controller': 'RC2', 'channel': 'M2', 'port': RC2_PORT},
    'W3': {'controller': 'RC2', 'channel': 'M1', 'port': RC2_PORT}
}

# Default Parameters
DEFAULT_SPEED_RAD_S = 2.0  # rad/s
DEFAULT_DURATION = 5.0     # seconds (reduced from 10.0)
DEFAULT_ROLLING_VELOCITY = [0.0, 5.0]  # [vx, vy] in m/s (increased to 5 m/s)
DEFAULT_CYCLES = 2         # number of cycles for step response

def calculate_optical_flow_feedback(optical_flow_velocity: List[float]) -> Dict:
    """
    Calculate ball rotation feedback from optical flow sensor data.
    
    Args:
        optical_flow_velocity: [vx, vy] surface velocity under the ball in m/s
        
    Returns:
        Dict: Ball rotation feedback data
    """
    # Placeholder function for optical flow sensor feedback
    # This will be implemented when the optical flow sensor is connected
    
    # The optical flow sensor reads the surface velocity under the ball
    # We multiply by -1 to get the opposite reference viewpoint (ball with respect to ground)
    # Then take cross product of XY tangential ball surface velocity and Z radius vector [0,0,0.111]
    # to get the translation of the rolling ball motion
    
    if optical_flow_velocity is None or len(optical_flow_velocity) != 2:
        return {
            'ball_rotation_feedback': [0.0, 0.0, 0.0],
            'translation_feedback': [0.0, 0.0],
            'error': 'No optical flow data available'
        }
    
    # Placeholder calculation (to be implemented with actual sensor)
    vx, vy = optical_flow_velocity
    
    # Cross product: [vx, vy, 0] × [0, 0, BALL_RADIUS] = [vy*BALL_RADIUS, -vx*BALL_RADIUS, 0]
    ball_rotation_feedback = [vy * BALL_RADIUS, -vx * BALL_RADIUS, 0.0]
    
    # Translation feedback (opposite of surface velocity)
    translation_feedback = [-vx, -vy]
    
    return {
        'ball_rotation_feedback': ball_rotation_feedback,
        'translation_feedback': translation_feedback,
        'optical_flow_velocity': optical_flow_velocity,
        'error': None
    }

class BallRotationControl:
    """Main ball rotation control system based on streamlined_demo.py."""
    
    def __init__(self):
        """Initialize the control system."""
        self.rc1 = None
        self.rc2 = None
        self.connected = False
        self.development_mode = True  # Start with development mode on
        
        # Initialize Jacobian matrices for kinematic conversions
        # Using 120-degree spacing between wheels (beta = 120°)
        # CORRECTED: Using the correct rZ and rX values from demo_config.json
        self.jacob_inv, self.jacob = jacobian(
            beta=120.0,           # Angle between wheels in degrees
            rBall=BALL_RADIUS,    # Ball radius in meters
            rOmni=WHEEL_RADIUS,   # Omniwheel radius in meters
            rZ=0.073,             # Z-offset of wheels in meters (CORRECTED)
            rX=0.085               # X-offset of wheels in meters (CORRECTED)
        )
        
        # Current setpoints and measurements
        self.current_setpoints = {
            'wheel_velocities': [0.0, 0.0, 0.0],  # [w1, w2, w3] in rad/s
            'ball_rotation': [0.0, 0.0, 0.0],     # [wx, wy, wz] in rad/s
            'translation': [0.0, 0.0]             # [vx, vy] in m/s
        }
        
        # Status printing control
        self.last_status_print = 0.0
        self.status_print_interval = 1.0  # 1 Hz status printing
        
        print("✓ BallRotationControl initialized")
        print(f"  Jacobian shape: {self.jacob.shape}")
        print(f"  Inverse Jacobian shape: {self.jacob_inv.shape}")
        print(f"  Using rZ={0.073} m, rX={0.085} m (corrected values)")
        
    def connect_controllers(self):
        """Connect to both RoboClaw controllers - from streamlined_demo.py."""
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
    
    def get_controller(self, controller_name: str):
        """Get the appropriate controller object."""
        if controller_name == 'RC1':
            return self.rc1
        elif controller_name == 'RC2':
            return self.rc2
        else:
            return None
    
    def get_error_description(self, error_code: int) -> str:
        """Get error description from RoboClaw error code."""
        error_descriptions = {
            0x000000: "Normal",
            0x000001: "M1 Over Current Warning",
            0x000002: "M2 Over Current Warning",
            0x000004: "EMERGENCY STOP (E-STOP)",
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
    
    def set_wheel_velocity(self, wheel_name: str, rad_s: float) -> bool:
        """
        Set wheel angular velocity in rad/s - from streamlined_demo.py.
        
        Args:
            wheel_name: Wheel name (W1, W2, W3)
            rad_s: Angular velocity in radians per second
        """
        if not self.connected:
            print("✗ Controllers not connected")
            return False
        
        if wheel_name not in WHEEL_CONFIG:
            print(f"✗ Unknown wheel: {wheel_name}")
            return False
        
        config = WHEEL_CONFIG[wheel_name]
        controller = self.get_controller(config['controller'])
        
        if controller is None:
            print(f"✗ Invalid controller: {config['controller']}")
            return False
        
        # Convert rad/s to encoder pulses using centralized utility
        pulses = wheel_velocity_to_encoder_pulses(rad_s, TRANSMISSION_RATIO, ENCODER_PULSES_PER_REV)
        
        if self.development_mode:
            print(f"TROUBLESHOOTING: Setting {wheel_name} ({config['controller']}_{config['channel']})")
            print(f"  Input: {rad_s:.3f} rad/s")
            print(f"  Conversion: {rad_s:.3f} rad/s → {pulses} pulses/s")
            print(f"  Controller: {config['controller']}, Channel: {config['channel']}, Address: {ADDRESS}")
        
        # Send speed command
        if config['channel'] == 'M1':
            result = controller.SpeedM1(ADDRESS, pulses)
        else:  # M2
            result = controller.SpeedM2(ADDRESS, pulses)
        
        if result:
            # Update current setpoints
            wheel_index = list(WHEEL_CONFIG.keys()).index(wheel_name)
            self.current_setpoints['wheel_velocities'][wheel_index] = rad_s
            if self.development_mode:
                print(f"✓ {wheel_name}: Velocity set successfully")
            return True
        else:
            print(f"✗ {wheel_name}: Failed to set velocity")
            return False
    
    def stop_wheel(self, wheel_name: str) -> bool:
        """Stop a specific wheel."""
        return self.set_wheel_velocity(wheel_name, 0.0)
    
    def stop_all_wheels(self):
        """Stop all wheels synchronously."""
        print("Stopping all wheels...")
        for wheel_name in WHEEL_CONFIG.keys():
            self.stop_wheel(wheel_name)
        print("✓ All wheels stopped")
    
    def read_wheel_data(self, wheel_name: str) -> Dict:
        """Read speed, current, and voltage for a specific wheel - from streamlined_demo.py."""
        if not self.connected:
            return {}
        
        if wheel_name not in WHEEL_CONFIG:
            return {}
        
        config = WHEEL_CONFIG[wheel_name]
        controller = self.get_controller(config['controller'])
        
        if controller is None:
            return {}
        
        data = {
            'wheel_name': wheel_name,
            'controller': config['controller'],
            'channel': config['channel'],
            'port': config['port'],
            'pulses_s': 0,
            'rad_s': 0.0,
            'current': 0.0,
            'voltage': 0.0,
            'error_state': 0,
            'success': False,
            'timestamp': time.time()
        }
        
        # Read speed in pulses/s
        if config['channel'] == 'M1':
            speed_data = controller.ReadSpeedM1(ADDRESS)
        else:  # M2
            speed_data = controller.ReadSpeedM2(ADDRESS)
        
        if speed_data[0]:
            data['pulses_s'] = speed_data[1]
            data['rad_s'] = encoder_pulses_to_wheel_velocity(speed_data[1], TRANSMISSION_RATIO, ENCODER_PULSES_PER_REV)
            data['success'] = True
        
        # Read current
        current_data = controller.ReadCurrents(ADDRESS)
        if current_data[0]:
            if config['channel'] == 'M1':
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
    
    def read_all_wheel_data(self) -> List[Dict]:
        """Read speed, current, and voltage for all wheels."""
        all_data = []
        for wheel_name in WHEEL_CONFIG.keys():
            data = self.read_wheel_data(wheel_name)
            if data:
                all_data.append(data)
        return all_data
    
    def print_status_table(self):
        """Print current status of all wheels in standardized format."""
        print("\n" + "=" * 140)
        print("WHEEL STATUS TABLE")
        print("=" * 140)
        print(f"{'[Wheel/Controller/Channel]':<25} {'[Rad/s]':<12} {'[Pulses/s]':<12} {'[Setpoint]':<12} {'[Error]':<12} {'[Ratio]':<10} {'[Current]':<10} {'[Voltage]':<10} {'[Error Code]':<15}")
        print("-" * 140)
        
        all_data = self.read_all_wheel_data()
        for data in all_data:
            if data['success']:
                # Calculate error and ratio
                setpoint = self.current_setpoints['wheel_velocities'][list(WHEEL_CONFIG.keys()).index(data['wheel_name'])]
                error = setpoint - data['rad_s']  # setpoint - feedback
                ratio = data['rad_s'] / setpoint if setpoint != 0 else 0.0
                
                direction = "REV" if data['rad_s'] < 0 else "FWD"
                wheel_label = f"[{data['wheel_name']}/{data['controller']}/{data['channel']}]"
                rad_s_display = f"{data['rad_s']:.2f}({direction})"
                pulses_display = f"{data['pulses_s']}"
                setpoint_display = f"{setpoint:.2f}"
                error_display = f"{error:.2f}"
                ratio_display = f"({ratio:.2f})"
                current_display = f"{data['current']:.2f}A"
                voltage_display = f"{data['voltage']:.1f}V"
                error_code = f"{data['error_state']} - {self.get_error_description(data['error_state'])}"
                
                print(f"{wheel_label:<25} {rad_s_display:<12} {pulses_display:<12} {setpoint_display:<12} {error_display:<12} {ratio_display:<10} {current_display:<10} {voltage_display:<10} {error_code:<15}")
            else:
                wheel_label = f"[{data['wheel_name']}/{data['controller']}/{data['channel']}]"
                print(f"{wheel_label:<25} {'ERROR':<12} {'ERROR':<12} {'ERROR':<12} {'ERROR':<12} {'ERROR':<10} {'ERROR':<10} {'ERROR':<10} {'ERROR':<15}")
        
        print("=" * 140)
        
        # Ball rotation status table
        print("\n" + "=" * 100)
        print("BALL ROTATION STATUS TABLE")
        print("=" * 100)
        print(f"{'Axis':<6} {'Setpoint':<12} {'Wheel_Feedback':<15} {'Optical_Feedback':<15} {'Wheel_Error':<12} {'Optical_Error':<12} {'Translation':<20}")
        print("-" * 100)
        
        # Calculate ball rotation from wheel velocities (kinematic feedback)
        wheel_velocities = [data['rad_s'] for data in all_data if data['success']]
        if len(wheel_velocities) == 3:
            wheel_rotation_feedback = wheel_velocities_to_rotation(np.array(wheel_velocities), self.jacob)
            
            # Placeholder for optical flow feedback (to be implemented)
            optical_flow_data = calculate_optical_flow_feedback([0.0, 0.0])  # No sensor data yet
            optical_rotation_feedback = optical_flow_data['ball_rotation_feedback']
            
            axes = ['wX', 'wY', 'wZ']
            for i, axis in enumerate(axes):
                setpoint = self.current_setpoints['ball_rotation'][i]
                wheel_feedback = wheel_rotation_feedback[i] if i < len(wheel_rotation_feedback) else 0.0
                optical_feedback = optical_rotation_feedback[i] if i < len(optical_rotation_feedback) else 0.0
                
                wheel_error = setpoint - wheel_feedback  # setpoint - wheel feedback
                optical_error = setpoint - optical_feedback  # setpoint - optical feedback
                
                setpoint_display = f"{setpoint:.2f}"
                wheel_feedback_display = f"{wheel_feedback:.2f}"
                optical_feedback_display = f"{optical_feedback:.2f}"
                wheel_error_display = f"{wheel_error:.2f}"
                optical_error_display = f"{optical_error:.2f}"
                
                # Translation setpoint
                translation_display = f"vX={self.current_setpoints['translation'][0]:.2f}, vY={self.current_setpoints['translation'][1]:.2f}"
                
                print(f"{axis:<6} {setpoint_display:<12} {wheel_feedback_display:<15} {optical_feedback_display:<15} {wheel_error_display:<12} {optical_error_display:<12} {translation_display:<20}")
        else:
            print("Insufficient wheel data for ball rotation calculation")
        
        print("=" * 100)
        
        # Optical flow status (placeholder)
        print("\n" + "=" * 80)
        print("OPTICAL FLOW SENSOR STATUS")
        print("=" * 80)
        print("Status: Not implemented (placeholder)")
        print("Function: Surface velocity measurement under the ball")
        print("Conversion: Cross product with Z-radius vector [0,0,0.111]")
        print("Reference: Ball motion relative to ground surface")
        print("=" * 80)
        
        # Check for e-stop
        e_stop_detected = any((data.get('error_state', 0) & 0x000004) for data in all_data)
        if e_stop_detected:
            print("\n!!! EMERGENCY STOP (E-STOP) DETECTED !!!")
            print("Please reset the E-STOP and press Enter to continue...")
            input()
            print("Rechecking status...")
            self.print_status_table()
            return
    
    def rolling_motion_demo(self, translation_velocity: Optional[List[float]] = None, duration: Optional[float] = None):
        """Execute rolling motion demo with setpoint sequences."""
        print(f"\n" + "=" * 50)
        print(f"ROLLING MOTION DEMO - SETPOINT SEQUENCES")
        print("=" * 50)
        print("This demo runs a sequence of 8 setpoint vectors in a loop:")
        print("[Q,0], [Q,Q], [0,Q], [-Q,Q], [-Q,0], [-Q,-Q], [0,-Q], [Q,-Q]")
        print("Each segment runs for 5 seconds with brief stops between segments")
        print("Type STOP at any prompt to return to menu.")
        print("Press Ctrl+C to stop and return to menu")
        print("=" * 50)
        try:
            # Get magnitude from user
            magnitude_input = input("Enter setpoint magnitude Q (m/s): ")
            if magnitude_input.strip().lower() == 'stop':
                print('Returning to menu...')
                self.stop_all_wheels()
                return True
            magnitude = float(magnitude_input)
            if magnitude <= 0:
                print("Magnitude must be positive")
                return False
            print(f"Starting sequence with magnitude Q = {magnitude} m/s")
            print("Press Ctrl+C to stop...")
            setpoint_sequence = [
                [magnitude, 0],
                [magnitude, magnitude],
                [0, magnitude],
                [-magnitude, magnitude],
                [-magnitude, 0],
                [-magnitude, -magnitude],
                [0, -magnitude],
                [magnitude, -magnitude]
            ]
            segment_duration = 5.0
            cycle = 1
            while True:
                print(f"\n--- CYCLE {cycle} ---")
                for i, setpoint in enumerate(setpoint_sequence):
                    print(f"\nSegment {i+1}/8: [{setpoint[0]:.2f}, {setpoint[1]:.2f}] m/s")
                    stop_input = input('Type STOP to return to menu or press Enter to continue: ').strip().lower()
                    if stop_input == 'stop':
                        print('Returning to menu...')
                        self.stop_all_wheels()
                        return True
                    self._execute_rolling_motion(setpoint, segment_duration, f"SEGMENT_{i+1}")
                    if i < len(setpoint_sequence) - 1:
                        if self.development_mode:
                            print("Brief stop before next segment...")
                        self.stop_all_wheels()
                        time.sleep(CONTROL_LOOP_PERIOD)
                cycle += 1
        except KeyboardInterrupt:
            print("\n\nSequence interrupted by user")
            self.stop_all_wheels()
            print("Sequence stopped safely")
            return True
        except ValueError:
            print("Invalid input")
            return False
        return True
    
    def rolling_step_response_demo(self, translation_velocity: Optional[List[float]] = None, duration: Optional[float] = None, cycles: Optional[int] = None):
        """Execute rolling step response demo with forward and reverse motion cycles."""
        if translation_velocity is None:
            translation_velocity = DEFAULT_ROLLING_VELOCITY.copy()
        else:
            translation_velocity = translation_velocity.copy()
        
        if duration is None:
            duration = DEFAULT_DURATION
            
        if cycles is None:
            cycles = DEFAULT_CYCLES
        
        print(f"\n" + "=" * 50)
        print(f"ROLLING STEP RESPONSE DEMO")
        print("=" * 50)
        print(f"Forward translation velocity: [{translation_velocity[0]:.2f}, {translation_velocity[1]:.2f}] m/s")
        print(f"Reverse translation velocity: [{-translation_velocity[0]:.2f}, {-translation_velocity[1]:.2f}] m/s")
        print(f"Duration per direction: {duration} seconds")
        print(f"Number of cycles: {cycles}")
        print(f"Control loop frequency: {CONTROL_LOOP_FREQUENCY} Hz")
        print("=" * 50)
        
        for cycle in range(cycles):
            print(f"\n--- CYCLE {cycle + 1}/{cycles} ---")
            
            # Forward motion
            print(f"Step 1: Forward motion for {duration} seconds...")
            self._execute_rolling_motion(translation_velocity, duration, "FORWARD")
            
            # Brief stop (one control cycle)
            print(f"Step 2: Brief stop...")
            self.stop_all_wheels()
            time.sleep(CONTROL_LOOP_PERIOD)
            
            # Reverse motion
            reverse_velocity = [-v for v in translation_velocity]
            print(f"Step 3: Reverse motion for {duration} seconds...")
            self._execute_rolling_motion(reverse_velocity, duration, "REVERSE")
            
            # Brief stop (one control cycle)
            print(f"Step 4: Brief stop...")
            self.stop_all_wheels()
            time.sleep(CONTROL_LOOP_PERIOD)
        
        print("\nRolling step response demo completed!")
        return True
    
    def continuous_rolling_motion(self):
        """Execute continuous rolling motion until stopped."""
        print(f"\n" + "=" * 50)
        print(f"CONTINUOUS ROLLING MOTION")
        print("=" * 50)
        print("Enter vX vY translation velocity in m/s (space separated)")
        print("Type STOP to return to menu.")
        print("=" * 50)
        current_velocity = [0.0, 0.0]
        running = True
        while running:
            try:
                input_str = input("Enter vX vY (m/s): ").strip()
                if input_str.lower() == 'stop':
                    print("Stopping continuous motion and returning to menu...")
                    self.stop_all_wheels()
                    break
                values = input_str.split()
                if len(values) != 2:
                    print("Invalid input. Please enter two numbers separated by space.")
                    continue
                vx = float(values[0])
                vy = float(values[1])
                if vx == 0.0 and vy == 0.0:
                    print("Stopping all wheels for one control cycle...")
                    self.stop_all_wheels()
                    time.sleep(CONTROL_LOOP_PERIOD)
                    continue
                # Stop for one control cycle before switching
                self.stop_all_wheels()
                time.sleep(CONTROL_LOOP_PERIOD)
                current_velocity = [vx, vy]
                print(f"Executing continuous motion: [{vx:.2f}, {vy:.2f}] m/s")
                self._execute_continuous_motion(current_velocity)
            except ValueError:
                print("Invalid input. Please enter numeric values.")
            except KeyboardInterrupt:
                print("\nContinuous motion interrupted by user")
                self.stop_all_wheels()
                break
        return True
    
    def _execute_continuous_motion(self, translation_velocity: List[float]):
        """Execute continuous rolling motion."""
        if self.development_mode:
            print(f"\nCONTINUOUS MOTION EXECUTION")
            print("=" * 50)
        
        # Convert translation velocity to ball rotation velocity
        ball_rotation = translation_to_rotation(
            translation_vel=np.array(translation_velocity),
            ball_radius=BALL_RADIUS
        )
        
        # Convert ball rotation to wheel angular velocities
        wheel_velocities = rotation_to_wheel_velocities(
            rotation_vel=ball_rotation,
            jacob_inv=self.jacob_inv
        )
        
        # Update current setpoints
        self.current_setpoints['ball_rotation'] = ball_rotation.copy()
        self.current_setpoints['translation'] = translation_velocity.copy()
        self.current_setpoints['wheel_velocities'] = wheel_velocities.copy()
        
        # Set wheel velocities synchronously using explicit wheel names
        wheel_names = ['W1', 'W2', 'W3']  # Explicit order to match kinematic calculations
        for i, wheel_name in enumerate(wheel_names):
            if self.development_mode:
                print(f"Setting {wheel_name} to {wheel_velocities[i]:.3f} rad/s")
            self.set_wheel_velocity(wheel_name, wheel_velocities[i])
        
        if self.development_mode:
            print(f"Continuous motion updated: [{translation_velocity[0]:.2f}, {translation_velocity[1]:.2f}] m/s")
            print("Motion continues until new input is provided")
            
            # Print status once after setting velocities
            time.sleep(0.5)  # Brief pause for motor response
            self.print_status_table()
    
    def calibration_demo(self):
        """Execute wheel calibration demo."""
        print(f"\n" + "=" * 50)
        print(f"WHEEL CALIBRATION DEMO")
        print("=" * 50)
        print("This calibration will set the wheel angular velocity directly using the same conversion as the main setpoint logic.")
        print("Available wheels:")
        for i, wheel_name in enumerate(WHEEL_CONFIG.keys()):
            print(f"  {i+1}: {wheel_name}")
        try:
            wheel_index = int(input(f"Select wheel (1-{len(WHEEL_CONFIG)}): ")) - 1
            if wheel_index < 0 or wheel_index >= len(WHEEL_CONFIG):
                print("Invalid wheel selection")
                return False
            wheel_name = list(WHEEL_CONFIG.keys())[wheel_index]
            angular_velocity = float(input(f"Enter angular velocity setpoint (default {DEFAULT_SPEED_RAD_S} rad/s): ") or DEFAULT_SPEED_RAD_S)
            duration = float(input(f"Enter duration (default 30 seconds): ") or 30.0)
            # Use the same conversion as main setpoint logic
            encoder_pulses = wheel_velocity_to_encoder_pulses(angular_velocity, TRANSMISSION_RATIO, ENCODER_PULSES_PER_REV)
            print(f"Calibration setpoint: {angular_velocity:.2f} rad/s = {encoder_pulses} pulses/s")
            print(f"Transmission ratio: {TRANSMISSION_RATIO} (13 encoder rev / 3 wheel rev)")
            print(f"Encoder pulses per rev: {ENCODER_PULSES_PER_REV}")
            print(f"\nCalibrating {wheel_name} at {angular_velocity:.2f} rad/s for {duration:.1f} seconds...")
            # Set wheel velocity directly
            if not self.set_wheel_velocity(wheel_name, angular_velocity):
                return False
            start_time = time.time()
            while time.time() - start_time < duration:
                elapsed = time.time() - start_time
                remaining = duration - elapsed
                current_time = time.time()
                if current_time - self.last_status_print >= 5.0:
                    print(f"Time: {elapsed:.1f}s (remaining: {remaining:.1f}s)")
                    self.print_status_table()
                    self.last_status_print = current_time
                time.sleep(CONTROL_LOOP_PERIOD)
            self.stop_wheel(wheel_name)
            measured_rpm = float(input("Enter measured RPM: "))
            if measured_rpm == 0:
                print("ERROR: Motor was not moving. Check connections and code.")
                return False
            measured_rad_s = measured_rpm * 2 * math.pi / 60.0
            calibration_factor = measured_rad_s / angular_velocity
            print(f"Calibration results:")
            print(f"  Setpoint: {angular_velocity:.2f} rad/s")
            print(f"  Measured: {measured_rpm:.1f} RPM = {measured_rad_s:.2f} rad/s")
            print(f"  Calibration factor: {calibration_factor:.3f}")
            self._save_calibration_data(wheel_name, angular_velocity, measured_rpm, measured_rad_s, calibration_factor)
            return True
        except ValueError:
            print("Invalid input")
            return False
        except KeyboardInterrupt:
            print("\nCalibration interrupted by user")
            self.stop_all_wheels()
            return False
    
    def _execute_calibration(self, wheel_name: str, angular_velocity: float, duration: float) -> bool:
        """Execute calibration for a specific wheel."""
        print(f"\nCALIBRATION EXECUTION")
        print("=" * 50)
        
        # Set wheel velocity
        if not self.set_wheel_velocity(wheel_name, angular_velocity):
            return False
        
        # Monitor for duration
        start_time = time.time()
        while time.time() - start_time < duration:
            elapsed = time.time() - start_time
            remaining = duration - elapsed
            
            # Print status periodically (less frequent for calibration)
            current_time = time.time()
            if current_time - self.last_status_print >= 5.0:  # Print every 5 seconds for calibration
                print(f"Time: {elapsed:.1f}s (remaining: {remaining:.1f}s)")
                self.print_status_table()
                self.last_status_print = current_time
            
            # Wait for next control loop iteration
            time.sleep(CONTROL_LOOP_PERIOD)
        
        # Stop wheel
        self.stop_wheel(wheel_name)
        return True
    
    def _save_calibration_data(self, wheel_name: str, setpoint: float, measured_rpm: float, measured_rad_s: float, calibration_factor: float):
        """Save calibration data to config file."""
        try:
            config_file = "demo_config.json"
            
            # Load existing config
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
            else:
                config = {}
            
            # Add calibration data
            if 'calibration_data' not in config:
                config['calibration_data'] = {}
            
            config['calibration_data'][wheel_name] = {
                'timestamp': datetime.now().isoformat(),
                'setpoint_rad_s': setpoint,
                'measured_rpm': measured_rpm,
                'measured_rad_s': measured_rad_s,
                'calibration_factor': calibration_factor
            }
            
            # Save config
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            print(f"Calibration data saved to {config_file}")
            
        except Exception as e:
            print(f"Error saving calibration data: {e}")
    
    def _execute_rolling_motion(self, translation_velocity: List[float], duration: float, direction_name: str):
        """Execute rolling motion with kinematic conversions."""
        print(f"\n{direction_name} MOTION EXECUTION")
        print("=" * 50)
        
        # Step 1: Convert translation velocity to ball rotation velocity
        if self.development_mode:
            print(f"\nStep 1: Converting translation to ball rotation...")
            print(f"TROUBLESHOOTING: Input translation_velocity={translation_velocity} m/s, ball_radius={BALL_RADIUS} m")
        ball_rotation = translation_to_rotation(
            translation_vel=np.array(translation_velocity),  # [vx, vy] in m/s
            ball_radius=BALL_RADIUS  # meters
        )
        if self.development_mode:
            print(f"TROUBLESHOOTING: Output ball_rotation={ball_rotation} rad/s")
            print(f"Ball rotation velocity: [{ball_rotation[0]:.3f}, {ball_rotation[1]:.3f}, {ball_rotation[2]:.3f}] rad/s")
        
        # Update current setpoints
        self.current_setpoints['ball_rotation'] = ball_rotation.copy()
        self.current_setpoints['translation'] = translation_velocity.copy()
        
        # Step 2: Convert ball rotation to wheel angular velocities using inverse Jacobian
        if self.development_mode:
            print(f"\nStep 2: Converting ball rotation to wheel velocities...")
            print(f"TROUBLESHOOTING: Input ball_rotation={ball_rotation} rad/s, jacob_inv shape={self.jacob_inv.shape}")
        wheel_velocities = rotation_to_wheel_velocities(
            rotation_vel=ball_rotation,  # [wx, wy, wz] in rad/s
            jacob_inv=self.jacob_inv     # Inverse Jacobian matrix
        )
        if self.development_mode:
            print(f"TROUBLESHOOTING: Output wheel_velocities={wheel_velocities} rad/s")
            print(f"Wheel angular velocities: [{wheel_velocities[0]:.3f}, {wheel_velocities[1]:.3f}, {wheel_velocities[2]:.3f}] rad/s")
        
        # Update current setpoints
        self.current_setpoints['wheel_velocities'] = wheel_velocities.copy()
        
        # Step 3: Convert wheel angular velocities to encoder pulses
        if self.development_mode:
            print(f"\nStep 3: Converting wheel velocities to encoder pulses...")
        wheel_pulses = []
        for i, wheel_vel in enumerate(wheel_velocities):
            pulses = wheel_velocity_to_encoder_pulses(wheel_vel, TRANSMISSION_RATIO, ENCODER_PULSES_PER_REV)
            wheel_pulses.append(pulses)
            if self.development_mode:
                print(f"TROUBLESHOOTING: W{i+1} ({list(WHEEL_CONFIG.keys())[i]}): {wheel_vel:.3f} rad/s → {pulses} pulses/s")
                print(f"W{i+1} ({list(WHEEL_CONFIG.keys())[i]}): {wheel_vel:.3f} rad/s → {pulses} pulses/s")
        
        # Step 4: Execute rolling motion with data logging
        if self.development_mode:
            print(f"\nStep 4: Executing {direction_name.lower()} motion for {duration} seconds...")
        start_time = time.time()
        
        # Set wheel velocities synchronously using explicit wheel names
        wheel_names = ['W1', 'W2', 'W3']  # Explicit order to match kinematic calculations
        for i, wheel_name in enumerate(wheel_names):
            if self.development_mode:
                print(f"Setting {wheel_name} to {wheel_velocities[i]:.3f} rad/s")
            self.set_wheel_velocity(wheel_name, wheel_velocities[i])
        
        # Monitor motion with fixed control loop frequency
        while time.time() - start_time < duration:
            elapsed = time.time() - start_time
            remaining = duration - elapsed
            
            # Print status periodically
            current_time = time.time()
            if current_time - self.last_status_print >= self.status_print_interval:
                print(f"\nTime: {elapsed:.1f}s (remaining: {remaining:.1f}s)")
                self.print_status_table()
                self.last_status_print = current_time
            
            # Wait for next control loop iteration
            time.sleep(CONTROL_LOOP_PERIOD)
        
        # Ensure clean stop
        print(f"\n{direction_name} motion completed. Stopping wheels...")
        self.stop_all_wheels()
        time.sleep(0.5)  # Brief pause for clean stop
        
        # Reset status print timer to prevent immediate printing after stop
        self.last_status_print = time.time()
    
    def show_menu(self):
        """Display the main menu."""
        print("\n" + "=" * 50)
        print("BALL ROTATION CONTROL MENU")
        print("=" * 50)
        print("1. Rolling Motion Demo")
        print("2. Rolling Step Response Demo")
        print("3. Continuous Rolling Motion")
        print("4. Wheel Calibration")
        print("5. Status Display")
        print("6. Stop All Wheels")
        print("7. Toggle Development Mode")
        print("8. Exit")
        print("=" * 50)
        print(f"Development Mode: {'ON' if self.development_mode else 'OFF'}")
        print("=" * 50)
    
    def run_demo(self):
        """Run the main demo loop."""
        print("BALL ROTATION CONTROL PLATFORM")
        print("=" * 50)
        print("Platform Constants:")
        print(f"  Wheel Diameter: {WHEEL_DIAMETER} m")
        print(f"  Wheel Radius: {WHEEL_RADIUS} m")
        print(f"  Ball Radius: {BALL_RADIUS} m")
        print(f"  Transmission Ratio: {TRANSMISSION_RATIO:.2f}")
        print(f"  Encoder Resolution: {ENCODER_PULSES_PER_REV} pulses/rev")
        print("=" * 50)
        print("Control Parameters:")
        print(f"  Control Loop Frequency: {CONTROL_LOOP_FREQUENCY} Hz")
        print(f"  Control Loop Period: {CONTROL_LOOP_PERIOD:.3f} s")
        print("=" * 50)
        print("Jacobian Parameters:")
        print(f"  rZ: 0.073 m (corrected)")
        print(f"  rX: 0.085 m (corrected)")
        print("=" * 50)
        
        # Connect to controllers
        if not self.connect_controllers():
            print("ERROR: Failed to connect to controllers")
            return False
        
        # Main menu loop
        while True:
            self.show_menu()
            
            try:
                choice = input("Enter your choice (1-8): ").strip()
                
                if choice == '1':
                    # Rolling motion demo with setpoint sequences
                    self.rolling_motion_demo()
                    
                elif choice == '2':
                    # Rolling step response demo
                    try:
                        vx = float(input("Enter X velocity (m/s): "))
                        vy = float(input("Enter Y velocity (m/s): "))
                        duration = float(input("Enter duration per direction (seconds): "))
                        cycles = int(input("Enter number of cycles (default 2): ") or DEFAULT_CYCLES)
                        self.rolling_step_response_demo([vx, vy], duration, cycles)
                    except ValueError:
                        print("Invalid input. Using default values.")
                        self.rolling_step_response_demo()
                    
                elif choice == '3':
                    # Continuous rolling motion
                    self.continuous_rolling_motion()
                    
                elif choice == '4':
                    # Wheel calibration
                    self.calibration_demo()
                    
                elif choice == '5':
                    # Status display
                    self.print_status_table()
                    
                elif choice == '6':
                    # Stop all wheels
                    self.stop_all_wheels()
                    
                elif choice == '7':
                    # Toggle development mode
                    self.development_mode = not self.development_mode
                    print(f"Development mode {'enabled' if self.development_mode else 'disabled'}")
                    
                elif choice == '8':
                    # Exit
                    print("\nExiting demo...")
                    self.stop_all_wheels()
                    break
                    
                else:
                    print("Invalid choice. Please enter 1-8.")
                    
            except KeyboardInterrupt:
                print("\n\nDemo interrupted by user")
                self.stop_all_wheels()
                break
                
            except Exception as e:
                print(f"\nERROR: Unexpected error: {e}")
                self.stop_all_wheels()
                break
        
        return True

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Ball Rotation Control Demo')
    parser.add_argument('--rolling-motion', action='store_true', help='Run rolling motion demo')
    parser.add_argument('--rolling-step', action='store_true', help='Run rolling step response demo')
    parser.add_argument('--vx', type=float, default=0.0, help='X velocity for rolling motion (m/s)')
    parser.add_argument('--vy', type=float, default=1.0, help='Y velocity for rolling motion (m/s)')
    parser.add_argument('--duration', type=float, default=5.0, help='Duration per direction (seconds)')
    parser.add_argument('--cycles', type=int, default=2, help='Number of cycles for step response')
    
    args = parser.parse_args()
    
    control = BallRotationControl()
    
    try:
        if not control.connect_controllers():
            print("ERROR: Failed to connect to controllers")
            sys.exit(1)
        
        if args.rolling_motion:
            # Run rolling motion demo with command line arguments
            control.rolling_motion_demo([args.vx, args.vy], args.duration)
        elif args.rolling_step:
            # Run rolling step response demo with command line arguments
            control.rolling_step_response_demo([args.vx, args.vy], args.duration, args.cycles)
        else:
            # Run interactive demo
            success = control.run_demo()
            if not success:
                sys.exit(1)
                
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
        control.stop_all_wheels()
        print("Wheels stopped safely")
        
    except Exception as e:
        print(f"\nERROR: Unexpected error during demo: {e}")
        control.stop_all_wheels()
        sys.exit(1)

if __name__ == "__main__":
    main() 