import numpy as np
import time
import matplotlib.pyplot as plt
from collections import deque
from datetime import datetime, timedelta
import serial  # For serial communication
import sys
import os
import traceback  # For exception handling
import json
from typing import Dict, Any, Optional, Tuple

# Add the local roboclaw_python directory to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'roboclaw_python'))
from roboclaw_3 import Roboclaw

# Initialize system parameters
rBall = 0.1  # meters, ball radius
rOmni = 0.025  # meters, omniwheel radius
beta = 120  # degrees between omniwheels
rZ = 0.05  # meters, height above equator
rX = 0.08  # meters, distance from center

# PID controller gains
kP = 1.0
kI = 0.1
kD = 0.05

# Data storage and timing parameters
BUFFER_DURATION = 60.0  # seconds to store in buffer
SAMPLE_TIME = 0.001  # seconds (control loop period)
PLOT_UPDATE_INTERVAL = 0.5  # seconds between plot updates
DATA_FIELDS = [
    'timestamp', 'setpoint_omni', 'feedback_omni', 'omni_error', 
    'setpoint_ball', 'feedback_ball', 'ball_error',
    # Additional fields for Roboclaw data
    'encoder_pos', 'encoder_velocity', 'encoder_accel',
    'motor_current', 'motor_voltage', 'motor_temp', 'estop_status',
    'sample_interval'  # To track the time between samples
]

# Roboclaw configuration
RC_BAUDRATE = 38400
RC1_ADDRESS = 0x80  # Address for first Roboclaw (motors 1 & 2)
RC2_ADDRESS = 0x81  # Address for second Roboclaw (motor 3)
RC1_PORT = 'COM3'  # Default USB port for first Roboclaw on Windows (adjust if needed)
RC2_PORT = 'COM4'  # Default USB port for second Roboclaw on Windows (adjust if needed)

# Test parameters
TEST_LAG_MULTIPLIER = 5  # Number of sample times to lag behind
ERROR_PERCENTAGE = 0.01  # 1% maximum error
TEST_FREQUENCY = 0.1  # Hz, frequency of sinusoidal test signal

# Global Roboclaw interface
rc_interface = None

class DataBuffer:
    def __init__(self, buffer_duration, sample_time):
        self.max_points = int(buffer_duration / sample_time)
        self.data = {field: deque(maxlen=self.max_points) for field in DATA_FIELDS}
        self.buffer_duration = buffer_duration
        
        # Initialize motor-specific data structures
        for i in range(1, 4):  # Motors 1, 2, 3
            self.data[f'motor{i}_encoder_pos'] = deque(maxlen=self.max_points)
            self.data[f'motor{i}_velocity'] = deque(maxlen=self.max_points)
            self.data[f'motor{i}_accel'] = deque(maxlen=self.max_points)
            self.data[f'motor{i}_current'] = deque(maxlen=self.max_points)
            self.data[f'motor{i}_voltage'] = deque(maxlen=self.max_points)
            self.data[f'motor{i}_temp'] = deque(maxlen=self.max_points)
            self.data[f'motor{i}_estop'] = deque(maxlen=self.max_points)
        
        # Sample interval tracking for performance monitoring
        self.data['sample_intervals'] = deque(maxlen=self.max_points)
        self.last_sample_time = None

    def add_data(self, **kwargs):
        current_time = time.time()
        
        # Calculate sample interval if we have a previous sample
        if self.last_sample_time is not None:
            interval = current_time - self.last_sample_time
            self.data['sample_intervals'].append(interval)
        
        self.last_sample_time = current_time
        
        # Add the rest of the data
        for field, value in kwargs.items():
            if field in self.data:
                self.data[field].append(value)

    def get_time_vector(self):
        """Returns time vector relative to newest sample"""
        if len(self.data['timestamp']) == 0:
            return np.array([])
        newest_time = self.data['timestamp'][-1]
        return np.array([t - newest_time for t in self.data['timestamp']])
    
    def get_rolling_average_sample_interval(self, window=20):
        """Calculate a rolling average of sample intervals"""
        if len(self.data['sample_intervals']) < window:
            if len(self.data['sample_intervals']) == 0:
                return 0
            return sum(self.data['sample_intervals']) / len(self.data['sample_intervals'])
        
        recent_intervals = list(self.data['sample_intervals'])[-window:]
        return sum(recent_intervals) / len(recent_intervals)

class TestSignalGenerator:
    def __init__(self, sample_time, lag_multiplier, error_percentage):
        self.sample_time = sample_time
        self.lag_samples = lag_multiplier
        self.error_percentage = error_percentage
        self.setpoint_history = deque(maxlen=lag_multiplier + 1)
        self.time = 0
        
    def generate_setpoint(self):
        """Generate a test setpoint signal"""
        # Generate three sinusoidal components with different phases
        wx = np.sin(2 * np.pi * TEST_FREQUENCY * self.time)
        wy = np.sin(2 * np.pi * TEST_FREQUENCY * self.time + 2*np.pi/3)
        wz = np.sin(2 * np.pi * TEST_FREQUENCY * self.time + 4*np.pi/3)
        
        setpoint = np.array([wx, wy, wz])
        self.setpoint_history.append(setpoint)
        self.time += self.sample_time
        return setpoint
    
    def generate_feedback(self):
        """Generate feedback with lag and small error"""
        if len(self.setpoint_history) <= self.lag_samples:
            return np.zeros(3)
        
        # Get historical setpoint (implementing lag)
        lagged_setpoint = self.setpoint_history[0]
        
        # Add small random error (within error_percentage)
        error = np.random.uniform(-self.error_percentage, self.error_percentage, 3)
        feedback = lagged_setpoint * (1 + error)
        
        return feedback
    
    def generate_encoder_data(self, motor_index):
        """Generate simulated encoder data for testing"""
        data = {
            'encoder_pos': int(np.random.normal(1000, 100)),
            'velocity': np.random.normal(100, 10),
            'accel': np.random.normal(20, 5),
            'current': np.random.normal(0.5, 0.1),  # Amps
            'voltage': np.random.normal(12, 0.5),   # Volts
            'temp': np.random.normal(35, 2),        # Celsius
            'estop': 0 if np.random.random() < 0.99 else 1  # 1% chance of estop
        }
        return data

def jacobian(beta, rBall, rOmni, rZ, rX):
    """
    Calculates the Jacobian and inverse Jacobian matrices for a ball driven by 3 omniwheels
    """
    # Define angles for each omniwheel
    beta1 = np.radians(0)
    beta2 = np.radians(beta)
    beta3 = np.radians(2 * beta)
    
    # Initialize Jacobian matrix
    jacob = np.zeros((3,3))

    jacob[0,0] = rZ;    jacob[0,1] = rZ * np.cos(beta2);    jacob[0,2] = rZ * np.cos(beta3)
    jacob[1,0] = 0;     jacob[1,1] = -rZ * np.sin(beta2);   jacob[1,2] = -rZ * np.sin(beta3)
    jacob[2,0] = -rX;   jacob[2,1] = -rX;                   jacob[2,2] = -rX

    jacob = (rOmni/rBall**2) * jacob
    
    # Calculate inverse of Jacobian matrix
    jacobInv = np.linalg.inv(jacob)
    
    return jacobInv, jacob

def omniAngVel(setpointBallAngVel, jacobInv):
    """
    Calculates the angular velocities of the three omniwheels
    """
    setpointBallAngVel = np.array(setpointBallAngVel)
    omniAngVel = np.dot(jacobInv, setpointBallAngVel)
    return omniAngVel

def calculateBallAngVelFeedback(encoderOmniAngVel, jacob):
    """
    Calculates actual ball rotation from encoder feedback
    """
    feedbackBallAngVel = np.dot(jacob, encoderOmniAngVel)
    return feedbackBallAngVel

def generateSetpointBallAngVel():
    """
    Placeholder function to generate desired ball rotation vector
    """
    setpointBallAngVel = np.array([0.0, 0.0, 1.0])  # rad/s [wx, wy, wz]
    return setpointBallAngVel

class RoboClawInterface:
    def __init__(self):
        self.rc1 = Roboclaw(RC1_PORT, RC_BAUDRATE)
        self.rc2 = Roboclaw(RC2_PORT, RC_BAUDRATE)
        self.connected = False
        self.motor_data = {
            1: {'address': RC1_ADDRESS, 'channel': 1, 'controller': self.rc1},
            2: {'address': RC1_ADDRESS, 'channel': 2, 'controller': self.rc1},
            3: {'address': RC2_ADDRESS, 'channel': 1, 'controller': self.rc2}
        }
        self.settings_manager = RoboclawSettings()
    
    def connect(self):
        """Connect to the Roboclaw controllers"""
        try:
            # Try to open the ports
            self.rc1.port.open()
            self.rc2.port.open()
            self.connected = True
            
            if self.connected:
                print("Connected to Roboclaw controllers successfully")
                
                # Read firmware versions to verify communication
                version1 = self.rc1.ReadVersion(RC1_ADDRESS)
                version2 = self.rc2.ReadVersion(RC2_ADDRESS)
                
                if version1[0] and version2[0]:
                    print(f"Roboclaw 1 version: {version1[1]}")
                    print(f"Roboclaw 2 version: {version2[1]}")
                else:
                    print("Warning: Could not read version from one or both controllers")
            else:
                print("Failed to connect to Roboclaw controllers")
                
            return self.connected
        except Exception as e:
            print(f"Error connecting to Roboclaw controllers: {str(e)}")
            self.connected = False
            return False
    
    def read_and_save_settings(self):
        """Read current settings from all controllers and save them"""
        if not self.connected:
            print("Not connected to Roboclaw controllers")
            return False
            
        try:
            # Read settings from both controllers
            settings1 = self.settings_manager.read_current_settings(self.rc1, RC1_ADDRESS)
            settings2 = self.settings_manager.read_current_settings(self.rc2, RC2_ADDRESS)
            
            # Combine settings
            combined_settings = {
                "controller1": settings1,
                "controller2": settings2,
                "timestamp": datetime.now().isoformat()
            }
            
            # Save current settings
            self.settings_manager.current_settings = combined_settings
            self.settings_manager.save_settings(combined_settings)
            
            # Create backup
            self.settings_manager.backup_current_settings()
            
            print("Settings read and saved successfully")
            return True
            
        except Exception as e:
            print(f"Error reading settings: {str(e)}")
            return False
    
    def compare_with_previous_settings(self):
        """Compare current settings with previous settings"""
        if not self.settings_manager.current_settings:
            print("No current settings available")
            return None
            
        # Load previous settings
        self.settings_manager.previous_settings = self.settings_manager.load_settings()
        
        if not self.settings_manager.previous_settings:
            print("No previous settings found for comparison")
            return None
            
        # Compare settings
        differences = self.settings_manager.compare_settings(
            self.settings_manager.current_settings,
            self.settings_manager.previous_settings
        )
        
        if differences:
            print("\nDifferences found:")
            for path, values in differences.items():
                print(f"{path}:")
                print(f"  Previous: {values['previous']}")
                print(f"  Current:  {values['current']}")
        else:
            print("No differences found between current and previous settings")
            
        return differences
    
    def set_pid_params(self, motor_num, p, i, d, qpps):
        """Set PID parameters for a motor"""
        if not self.connected:
            print("Not connected to Roboclaw controllers")
            return False
        
        motor = self.motor_data.get(motor_num)
        if not motor:
            print(f"Invalid motor number: {motor_num}")
            return False
        
        rc = motor['controller']
        address = motor['address']
        
        try:
            if motor['channel'] == 1:
                result = rc.SetM1VelocityPID(address, p, i, d, qpps)
            else:
                result = rc.SetM2VelocityPID(address, p, i, d, qpps)
            
            return result
        except Exception as e:
            print(f"Error setting PID parameters for motor {motor_num}: {str(e)}")
            return False
    
    def read_pid_params(self, motor_num):
        """Read PID parameters from a motor"""
        if not self.connected:
            print("Not connected to Roboclaw controllers")
            return None
        
        motor = self.motor_data.get(motor_num)
        if not motor:
            print(f"Invalid motor number: {motor_num}")
            return None
        
        rc = motor['controller']
        address = motor['address']
        
        try:
            if motor['channel'] == 1:
                result = rc.ReadM1VelocityPID(address)
            else:
                result = rc.ReadM2VelocityPID(address)
            
            if result[0]:
                return {
                    'p': result[1],
                    'i': result[2],
                    'd': result[3],
                    'qpps': result[4]
                }
            else:
                print(f"Failed to read PID parameters for motor {motor_num}")
                return None
        except Exception as e:
            print(f"Error reading PID parameters for motor {motor_num}: {str(e)}")
            return None
    
    def set_encoder_count(self, motor_num, count):
        """Set the encoder count for a motor"""
        if not self.connected:
            print("Not connected to Roboclaw controllers")
            return False
        
        motor = self.motor_data.get(motor_num)
        if not motor:
            print(f"Invalid motor number: {motor_num}")
            return False
        
        rc = motor['controller']
        address = motor['address']
        
        try:
            if motor['channel'] == 1:
                result = rc.SetEncM1(address, count)
            else:
                result = rc.SetEncM2(address, count)
            
            return result
        except Exception as e:
            print(f"Error setting encoder count for motor {motor_num}: {str(e)}")
            return False
    
    def get_motor_data(self, motor_num):
        """Get all data for a specific motor"""
        if not self.connected:
            print("Not connected to Roboclaw controllers")
            return None
        
        motor = self.motor_data.get(motor_num)
        if not motor:
            print(f"Invalid motor number: {motor_num}")
            return None
        
        rc = motor['controller']
        address = motor['address']
        channel = motor['channel']
        
        try:
            data = {}
            data['timestamp'] = time.time()
            
            # Read encoder position and velocity
            if channel == 1:
                enc_result = rc.ReadEncM1(address)
                speed_result = rc.ReadSpeedM1(address)
            else:
                enc_result = rc.ReadEncM2(address)
                speed_result = rc.ReadSpeedM2(address)
            
            if enc_result[0]:
                data['encoder_pos'] = enc_result[1]
                data['encoder_status'] = enc_result[2]  # Status byte
            
            if speed_result[0]:
                data['encoder_velocity'] = speed_result[1]
                data['encoder_status'] = speed_result[2]  # Status byte
            
            # Read current (returned in 10mA increments)
            current_result = rc.ReadCurrents(address)
            if current_result[0]:
                if channel == 1:
                    data['current'] = current_result[1] / 100.0  # Convert to Amps
                else:
                    data['current'] = current_result[2] / 100.0  # Convert to Amps
            
            # Read main battery voltage (returned in 10mV increments)
            voltage_result = rc.ReadMainBatteryVoltage(address)
            if voltage_result[0]:
                data['voltage'] = voltage_result[1] / 10.0  # Convert to Volts
            
            # Read temperature
            temp_result = rc.ReadTemp(address)
            if temp_result[0]:
                data['temp'] = temp_result[1] / 10.0  # Convert to Celsius
            
            # Read error status
            error_result = rc.ReadError(address)
            if error_result[0]:
                data['error'] = error_result[1]
                # Check if E-Stop bit is set (bit 0)
                data['estop_status'] = 1 if (error_result[1] & 0x01) else 0
            
            return data
            
        except Exception as e:
            print(f"Error getting data for motor {motor_num}: {str(e)}")
            return None

def getOmniEncoder():
    """
    Get encoder feedback from the Roboclaw controllers for all three omniwheels
    Returns encoder positions, velocities, and other status information
    """
    # When in test mode, this function will be replaced with simulated data
    if 'rc_interface' not in globals() or not rc_interface.connected:
        # Return zeros if not connected to Roboclaw
        return np.array([0.0, 0.0, 0.0]), [{}, {}, {}]
    
    # Get data for all three motors
    motor_data = []
    encoder_velocities = []
    
    for motor_num in range(1, 4):
        data = rc_interface.get_motor_data(motor_num)
        if data is None:
            data = {}
            encoder_velocities.append(0.0)
        else:
            # Convert to rad/s if needed (depends on your encoder setup)
            # Assuming the Roboclaw returns counts per second
            counts_per_rev = 4096  # Example value, adjust to your encoder
            if 'encoder_velocity' in data:
                rad_per_sec = (data['encoder_velocity'] / counts_per_rev) * 2 * np.pi
                encoder_velocities.append(rad_per_sec)
            else:
                encoder_velocities.append(0.0)
        
        motor_data.append(data)
    
    return np.array(encoder_velocities), motor_data

def sendSetpointAngVel(setpointOmniAngVel):
    """
    Send angular velocity setpoints to the Roboclaw controllers
    Input: setpointOmniAngVel - array of 3 angular velocities in rad/s
    """
    # When in test mode, this function will not actually send commands
    if 'rc_interface' not in globals() or not rc_interface.connected:
        return False
    
    # Convert from rad/s to counts per second (depends on your encoder setup)
    counts_per_rev = 4096  # Example value, adjust to your encoder
    
    success = True
    for i, vel_rad_sec in enumerate(setpointOmniAngVel):
        motor_num = i + 1
        motor = rc_interface.motor_data.get(motor_num)
        
        if not motor:
            print(f"Invalid motor number: {motor_num}")
            success = False
            continue
        
        rc = motor['controller']
        address = motor['address']
        channel = motor['channel']
        
        # Convert to counts per second
        vel_counts = int((vel_rad_sec * counts_per_rev) / (2 * np.pi))
        
        try:
            # Set velocity with acceleration limit
            accel = 10000  # Acceleration limit in counts per second per second
            
            if channel == 1:
                result = rc.SpeedAccelM1(address, accel, vel_counts)
            else:
                result = rc.SpeedAccelM2(address, accel, vel_counts)
            
            if not result:
                print(f"Failed to set velocity for motor {motor_num}")
                success = False
        except Exception as e:
            print(f"Error setting velocity for motor {motor_num}: {str(e)}")
            success = False
    
    return success

def initializePlots():
    """
    Initialize the plotting environment with four subplots
    """
    plt.ion()  # Enable interactive plotting
    fig = plt.figure(figsize=(12, 10))
    
    # Create 2x2 grid of subplots
    ax1 = plt.subplot(221)  # Omniwheel velocities
    ax2 = plt.subplot(222)  # Ball rotation
    ax3 = plt.subplot(223)  # Omniwheel errors
    ax4 = plt.subplot(224)  # Ball rotation errors
    
    # Set titles and labels
    ax1.set_title('Omniwheel Angular Velocities')
    ax1.set_xlabel('Time (s)')
    ax1.set_ylabel('Angular Velocity (rad/s)')
    
    ax2.set_title('Ball Angular Velocities')
    ax2.set_xlabel('Time (s)')
    ax2.set_ylabel('Angular Velocity (rad/s)')
    
    ax3.set_title('Omniwheel Error')
    ax3.set_xlabel('Time (s)')
    ax3.set_ylabel('Error (rad/s)')
    
    ax4.set_title('Ball Rotation Error')
    ax4.set_xlabel('Time (s)')
    ax4.set_ylabel('Error (rad/s)')
    
    plt.tight_layout()
    return fig, (ax1, ax2, ax3, ax4)

def updatePlots(data_buffer, fig, axes):
    """
    Update all plots with dynamic scaling
    """
    # Handle both 4-axes and 6-axes cases
    if len(axes) == 4:
        ax1, ax2, ax3, ax4 = axes
    else:  # len(axes) == 6
        ax1, ax2, ax3, ax4, ax5, ax6 = axes
    
    time_vector = data_buffer.get_time_vector()
    
    if len(time_vector) < 2:
        return

    # Clear all plots
    for ax in axes:
        ax.clear()

    # Colors for the three components
    colors = ['red', 'green', 'blue']
    
    try:
        # Plot omniwheel velocities (ax1)
        y_max_ax1 = 0
        for i in range(3):
            setpoints = np.array([x[i] for x in data_buffer.data['setpoint_omni']])
            feedback = np.array([x[i] for x in data_buffer.data['feedback_omni']])
            ax1.plot(time_vector, setpoints, '--', color=colors[i], label=f'Setpoint {i+1}')
            ax1.plot(time_vector, feedback, '-', color=colors[i], label=f'Feedback {i+1}')
            y_max_ax1 = max(y_max_ax1, np.max(np.abs(setpoints)), np.max(np.abs(feedback)))

        # Plot ball velocities (ax2)
        y_max_ax2 = 0
        for i in range(3):
            setpoints = np.array([x[i] for x in data_buffer.data['setpoint_ball']])
            feedback = np.array([x[i] for x in data_buffer.data['feedback_ball']])
            ax2.plot(time_vector, setpoints, '--', color=colors[i], label=f'Setpoint axis {i+1}')
            ax2.plot(time_vector, feedback, '-', color=colors[i], label=f'Feedback axis {i+1}')
            y_max_ax2 = max(y_max_ax2, np.max(np.abs(setpoints)), np.max(np.abs(feedback)))

        # Plot omniwheel errors (ax3)
        y_max_ax3 = 0
        for i in range(3):
            errors = np.array([x[i] for x in data_buffer.data['omni_error']])
            ax3.plot(time_vector, errors, '-', color=colors[i], label=f'Wheel {i+1} Error')
            y_max_ax3 = max(y_max_ax3, np.max(np.abs(errors)))

        # Plot ball rotation errors (ax4)
        y_max_ax4 = 0
        for i in range(3):
            errors = np.array([x[i] for x in data_buffer.data['ball_error']])
            ax4.plot(time_vector, errors, '-', color=colors[i], label=f'Axis {i+1} Error')
            y_max_ax4 = max(y_max_ax4, np.max(np.abs(errors)))

        # Plot additional motor data if present (motor currents, temperatures)
        if 'motor1_current' in data_buffer.data and len(data_buffer.data['motor1_current']) > 0:
            # Create two more plots if needed
            if len(axes) < 6:
                fig.clear()
                gs = fig.add_gridspec(3, 2)
                ax1 = fig.add_subplot(gs[0, 0])
                ax2 = fig.add_subplot(gs[0, 1])
                ax3 = fig.add_subplot(gs[1, 0])
                ax4 = fig.add_subplot(gs[1, 1])
                ax5 = fig.add_subplot(gs[2, 0])
                ax6 = fig.add_subplot(gs[2, 1])
                axes = (ax1, ax2, ax3, ax4, ax5, ax6)
            else:
                ax5, ax6 = axes[4], axes[5]
                ax5.clear()
                ax6.clear()
            
            # Plot motor currents
            for i in range(1, 4):
                currents = list(data_buffer.data[f'motor{i}_current'])
                if currents:
                    ax5.plot(time_vector[-len(currents):], currents, color=colors[i-1], label=f'Motor {i} Current')
            
            ax5.set_title('Motor Currents')
            ax5.set_xlabel('Time (s)')
            ax5.set_ylabel('Current (A)')
            ax5.grid(True)
            ax5.legend()
            
            # Plot motor temperatures
            for i in range(1, 4):
                temps = list(data_buffer.data[f'motor{i}_temp'])
                if temps:
                    ax6.plot(time_vector[-len(temps):], temps, color=colors[i-1], label=f'Motor {i} Temp')
            
            # Plot sample interval
            if 'sample_intervals' in data_buffer.data and len(data_buffer.data['sample_intervals']) > 0:
                intervals = list(data_buffer.data['sample_intervals'])
                # Make sure interval_times and intervals have the same length
                interval_times = time_vector[-len(intervals):]
                if len(interval_times) == len(intervals):
                    ax6.plot(interval_times, intervals, 'k--', label='Sample Interval (s)')
            
            ax6.set_title('Motor Temperatures & Sample Interval')
            ax6.set_xlabel('Time (s)')
            ax6.set_ylabel('Temperature (°C) / Time (s)')
            ax6.grid(True)
            ax6.legend()

        # Set axis limits with padding
        padding = 1.1  # 10% padding
        for ax, y_max in zip(axes[:4], [y_max_ax1, y_max_ax2, y_max_ax3, y_max_ax4]):
            if y_max > 0:
                ax.set_ylim(-y_max * padding, y_max * padding)
            ax.set_xlim(-data_buffer.buffer_duration, 0)  # Time axis from -buffer_duration to 0
            ax.grid(True)
            ax.legend()

        # Update titles and labels
        ax1.set_title('Omniwheel Angular Velocities')
        ax1.set_xlabel('Time (s)')
        ax1.set_ylabel('Angular Velocity (rad/s)')

        ax2.set_title('Ball Angular Velocities')
        ax2.set_xlabel('Time (s)')
        ax2.set_ylabel('Angular Velocity (rad/s)')

        ax3.set_title('Omniwheel Error')
        ax3.set_xlabel('Time (s)')
        ax3.set_ylabel('Error (rad/s)')

        ax4.set_title('Ball Rotation Error')
        ax4.set_xlabel('Time (s)')
        ax4.set_ylabel('Error (rad/s)')

        plt.tight_layout()
        
        # Use non-blocking draw and flush
        fig.canvas.draw_idle()
        fig.canvas.flush_events()
        
    except Exception as e:
        print(f"Error in plotting: {str(e)}")
        raise

def pidController(error, integral, lastError, dt):
    """
    PID controller implementation
    """
    integral = integral + error * dt
    derivative = (error - lastError) / dt
    
    output = kP * error + kI * integral + kD * derivative
    
    return output, integral

def mainControlLoop():
    """Run the main control loop with real Roboclaw hardware"""
    global rc_interface
    
    # Initialize Roboclaw interface
    rc_interface = RoboClawInterface()
    connected = rc_interface.connect()
    
    if not connected:
        print("WARNING: Failed to connect to Roboclaw controllers. Running in simulation mode.")
    
    # Calculate Jacobian matrices (constant for fixed geometry)
    jacobInv, jacob = jacobian(
        beta=beta,
        rBall=rBall,
        rOmni=rOmni,
        rZ=rZ,
        rX=rX
    )

    # Initialize PID variables
    integral = np.zeros(3)
    lastError = np.zeros(3)

    # Initialize plotting 
    fig = plt.figure(figsize=(14, 12))
    gs = fig.add_gridspec(3, 2)
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    ax3 = fig.add_subplot(gs[1, 0])
    ax4 = fig.add_subplot(gs[1, 1])
    ax5 = fig.add_subplot(gs[2, 0])
    ax6 = fig.add_subplot(gs[2, 1])
    axes = (ax1, ax2, ax3, ax4, ax5, ax6)
    
    data_buffer = DataBuffer(BUFFER_DURATION, SAMPLE_TIME)
    last_plot_update = time.time()
    last_sample_time = time.time()
    last_sample_intervals = []  # For calculating rolling average

    try:
        while True:
            current_time = time.time()
            
            # Calculate sample interval
            sample_interval = current_time - last_sample_time
            last_sample_time = current_time
            last_sample_intervals.append(sample_interval)
            
            # Keep only the last 100 intervals for rolling average
            if len(last_sample_intervals) > 100:
                last_sample_intervals.pop(0)
            rolling_avg_interval = sum(last_sample_intervals) / len(last_sample_intervals)
            
            # Get desired ball rotation
            setpointBallAngVel = generateSetpointBallAngVel()

            # Calculate desired omniwheel velocities
            setpointOmniAngVel = omniAngVel(
                setpointBallAngVel=setpointBallAngVel,
                jacobInv=jacobInv
            )

            # Get encoder feedback and motor data
            encoderOmniAngVel, motor_data_list = getOmniEncoder()

            # Calculate actual ball rotation from feedback
            feedbackBallAngVel = calculateBallAngVelFeedback(encoderOmniAngVel, jacob)

            # Calculate errors
            ballAngVelError = setpointBallAngVel - feedbackBallAngVel
            omniAngVelError = setpointOmniAngVel - encoderOmniAngVel

            # Apply PID control
            pidOutput = np.zeros(3)
            for i in range(3):
                pidOutput[i], integral[i] = pidController(
                    ballAngVelError[i],
                    integral[i],
                    lastError[i],
                    SAMPLE_TIME
                )
            lastError = ballAngVelError

            # Add PID output to desired rotation
            correctedBallAngVel = setpointBallAngVel + pidOutput

            # Recalculate omniwheel velocities with correction
            correctedOmniAngVel = omniAngVel(
                setpointBallAngVel=correctedBallAngVel,
                jacobInv=jacobInv
            )

            # Send setpoints to motor controller
            sendSetpointAngVel(correctedOmniAngVel)

            # Store data
            data_buffer.add_data(
                timestamp=current_time,
                setpoint_omni=setpointOmniAngVel,
                feedback_omni=encoderOmniAngVel,
                omni_error=omniAngVelError,
                setpoint_ball=setpointBallAngVel,
                feedback_ball=feedbackBallAngVel,
                ball_error=ballAngVelError,
                sample_interval=rolling_avg_interval
            )
            
            # Store motor-specific data
            for i, motor_data in enumerate(motor_data_list, 1):
                if motor_data:
                    data_buffer.add_data(**{
                        f'motor{i}_encoder_pos': motor_data.get('encoder_pos', 0),
                        f'motor{i}_velocity': motor_data.get('encoder_velocity', 0),
                        f'motor{i}_accel': motor_data.get('encoder_accel', 0),
                        f'motor{i}_current': motor_data.get('current', 0),
                        f'motor{i}_voltage': motor_data.get('voltage', 0),
                        f'motor{i}_temp': motor_data.get('temp', 0),
                        f'motor{i}_estop': motor_data.get('estop_status', 0)
                    })

            # Update plots every 0.5 seconds
            if current_time - last_plot_update >= PLOT_UPDATE_INTERVAL:
                updatePlots(data_buffer, fig, axes)
                last_plot_update = current_time

            # Sleep to maintain sample time, but account for processing time
            elapsed = time.time() - current_time
            sleep_time = max(0, SAMPLE_TIME - elapsed)
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("Control loop terminated by user")
        plt.ioff()
        plt.close('all')

def testRun():
    """
    Test run with simulated values and feedback
    """
    # Calculate Jacobian matrices (constant for fixed geometry)
    jacobInv, jacob = jacobian(
        beta=beta,
        rBall=rBall,
        rOmni=rOmni,
        rZ=rZ,
        rX=rX
    )

    # Initialize PID variables
    integral = np.zeros(3)
    lastError = np.zeros(3)

    # Initialize plotting with more plots
    plt.ion()  # Enable interactive mode
    fig = plt.figure(figsize=(14, 12))
    gs = fig.add_gridspec(3, 2)
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    ax3 = fig.add_subplot(gs[1, 0])
    ax4 = fig.add_subplot(gs[1, 1])
    ax5 = fig.add_subplot(gs[2, 0])
    ax6 = fig.add_subplot(gs[2, 1])
    axes = (ax1, ax2, ax3, ax4, ax5, ax6)
    
    data_buffer = DataBuffer(BUFFER_DURATION, SAMPLE_TIME)
    last_plot_update = time.time()

    # Initialize test signal generator
    test_gen = TestSignalGenerator(SAMPLE_TIME, TEST_LAG_MULTIPLIER, ERROR_PERCENTAGE)

    running = True
    print("Press Ctrl+C to stop the test...")
    
    try:
        while running:
            try:
                current_time = time.time()
                
                # Generate test setpoint for ball rotation
                setpointBallAngVel = test_gen.generate_setpoint()

                # Calculate desired omniwheel velocities
                setpointOmniAngVel = omniAngVel(
                    setpointBallAngVel=setpointBallAngVel,
                    jacobInv=jacobInv
                )

                # Generate simulated encoder feedback with lag and error
                encoderOmniAngVel = test_gen.generate_feedback()
                
                # Calculate actual ball rotation from feedback
                feedbackBallAngVel = calculateBallAngVelFeedback(encoderOmniAngVel, jacob)

                # Calculate errors
                ballAngVelError = setpointBallAngVel - feedbackBallAngVel
                omniAngVelError = setpointOmniAngVel - encoderOmniAngVel
                
                # Generate simulated motor data
                motor_data = []
                for i in range(1, 4):
                    motor_data.append(test_gen.generate_encoder_data(i))

                # Store data
                data_buffer.add_data(
                    timestamp=current_time,
                    setpoint_omni=setpointOmniAngVel,
                    feedback_omni=encoderOmniAngVel,
                    omni_error=omniAngVelError,
                    setpoint_ball=setpointBallAngVel,
                    feedback_ball=feedbackBallAngVel,
                    ball_error=ballAngVelError,
                    sample_interval=SAMPLE_TIME
                )
                
                # Store simulated motor-specific data
                for i, data in enumerate(motor_data, 1):
                    data_buffer.add_data(**{
                        f'motor{i}_encoder_pos': data['encoder_pos'],
                        f'motor{i}_velocity': data['velocity'],
                        f'motor{i}_accel': data['accel'],
                        f'motor{i}_current': data['current'],
                        f'motor{i}_voltage': data['voltage'],
                        f'motor{i}_temp': data['temp'],
                        f'motor{i}_estop': data['estop']
                    })

                # Update plots every 0.5 seconds
                if current_time - last_plot_update >= PLOT_UPDATE_INTERVAL:
                    updatePlots(data_buffer, fig, axes)
                    last_plot_update = current_time

                time.sleep(SAMPLE_TIME)

            except KeyboardInterrupt:
                print("\nStopping test run...")
                running = False
                break

    finally:
        print("Cleaning up...")
        plt.ioff()
        plt.close('all')

class RoboclawSettings:
    def __init__(self, settings_file: Optional[str] = None):
        # Use roboclaw_settings_backup directory for settings files
        if settings_file is None:
            backup_dir = os.path.join(os.path.dirname(__file__), 'tests', 'roboclaw_settings_backup')
            os.makedirs(backup_dir, exist_ok=True)
            settings_file = os.path.join(backup_dir, "roboclaw_settings.json")
        
        self.settings_file = settings_file
        self.current_settings: Dict[str, Any] = {}
        self.previous_settings: Dict[str, Any] = {}
        
    def read_current_settings(self, rc: Roboclaw, address: int) -> Dict[str, Any]:
        """Read all current settings from a Roboclaw controller"""
        settings = {
            "address": address,
            "timestamp": datetime.now().isoformat(),
            "pid_settings": {},
            "motor_settings": {},
            "status": {}
        }
        
        try:
            # Read PID settings for both motors
            for motor in [1, 2]:
                if motor == 1:
                    result = rc.ReadM1VelocityPID(address)
                else:
                    result = rc.ReadM2VelocityPID(address)
                
                if result[0]:  # Check if read was successful
                    settings["pid_settings"][f"motor{motor}"] = {
                        "p": result[1],
                        "i": result[2],
                        "d": result[3],
                        "qpps": result[4]
                    }
            
            # Read motor settings
            settings["motor_settings"] = {
                "max_current": rc.ReadMaxCurrent(address)[1] if rc.ReadMaxCurrent(address)[0] else None,
                "main_voltage": rc.ReadMainBatteryVoltage(address)[1] / 10.0 if rc.ReadMainBatteryVoltage(address)[0] else None,
                "logic_voltage": rc.ReadLogicBatteryVoltage(address)[1] / 10.0 if rc.ReadLogicBatteryVoltage(address)[0] else None
            }
            
            # Read status
            settings["status"] = {
                "error": rc.ReadError(address)[1] if rc.ReadError(address)[0] else None,
                "temperature": rc.ReadTemp(address)[1] / 10.0 if rc.ReadTemp(address)[0] else None,
                "firmware_version": rc.ReadVersion(address)[1] if rc.ReadVersion(address)[0] else None
            }
            
        except Exception as e:
            print(f"Error reading settings: {str(e)}")
            
        return settings
    
    def save_settings(self, settings: Dict[str, Any], filename: Optional[str] = None) -> None:
        """Save settings to a JSON file"""
        if filename is None:
            filename = self.settings_file
            
        with open(filename, 'w') as f:
            json.dump(settings, f, indent=4)
            
    def load_settings(self, filename: Optional[str] = None) -> Dict[str, Any]:
        """Load settings from a JSON file"""
        if filename is None:
            filename = self.settings_file
            
        try:
            with open(filename, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Settings file {filename} not found")
            return {}
            
    def compare_settings(self, current: Dict[str, Any], previous: Dict[str, Any]) -> Dict[str, Any]:
        """Compare current settings with previous settings and return differences"""
        differences = {}
        
        def compare_dicts(dict1: Dict[str, Any], dict2: Dict[str, Any], path: str = "") -> None:
            for key in set(dict1.keys()) | set(dict2.keys()):
                new_path = f"{path}.{key}" if path else key
                
                if key not in dict1:
                    differences[new_path] = {"previous": dict2[key], "current": None}
                elif key not in dict2:
                    differences[new_path] = {"previous": None, "current": dict1[key]}
                elif dict1[key] != dict2[key]:
                    if isinstance(dict1[key], dict) and isinstance(dict2[key], dict):
                        compare_dicts(dict1[key], dict2[key], new_path)
                    else:
                        differences[new_path] = {"previous": dict2[key], "current": dict1[key]}
        
        compare_dicts(current, previous)
        return differences
    
    def prepare_settings_file(self, differences: Dict[str, Any], output_file: str) -> None:
        """Prepare a new settings file with confirmed changes"""
        new_settings = self.current_settings.copy()
        
        for path, values in differences.items():
            if values["current"] is not None:  # Only include confirmed changes
                keys = path.split('.')
                current = new_settings
                for key in keys[:-1]:
                    current = current[key]
                current[keys[-1]] = values["current"]
        
        self.save_settings(new_settings, output_file)
        
    def backup_current_settings(self) -> None:
        """Create a backup of current settings with timestamp"""
        if not self.current_settings:
            return
            
        # Use roboclaw_settings_backup directory for backups
        backup_dir = os.path.join(os.path.dirname(__file__), 'tests', 'roboclaw_settings_backup')
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(backup_dir, f"roboclaw_settings_backup_{timestamp}.json")
        self.save_settings(self.current_settings, backup_file)
        print(f"Settings backed up to {backup_file}")

if __name__ == "__main__":
    # Set TEST_MODE to True for test run, False for regular operation
    TEST_MODE = True
    
    try:
        if TEST_MODE:
            print("Starting test run with simulated values...")
            testRun()
        else:
            print("Starting regular operation with Roboclaw controllers...")
            interface = RoboClawInterface()
            
            print("\n=== Step 1: Connecting to Roboclaw ===")
            if interface.connect():
                print("\n=== Step 2: Reading Current Settings ===")
                if interface.read_and_save_settings():
                    print("\n=== Step 3: Comparing with Previous Settings ===")
                    differences = interface.compare_with_previous_settings()
                    
                    if differences:
                        print("\n=== Step 4: Reviewing Changes ===")
                        print("The following changes were detected:")
                        for path, values in differences.items():
                            print(f"\n{path}:")
                            print(f"  Previous: {values['previous']}")
                            print(f"  Current:  {values['current']}")
                        
                        print("\nTo apply these changes, you would need to:")
                        print("1. Review the changes above")
                        print("2. Confirm which changes you want to keep")
                        print("3. Use the prepare_settings_file() method to create a new settings file")
                        print("4. Apply the new settings file to the Roboclaw")
                    else:
                        print("No differences found between current and previous settings")
                
                print("\n=== Step 5: Starting Main Control Loop ===")
                mainControlLoop()
            else:
                print("Failed to connect to Roboclaw controllers")
                
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        traceback.print_exc()
    finally:
        plt.ioff()
        plt.close('all')
        print("Program terminated.")






