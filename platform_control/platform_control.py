import json
import time
import csv
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import serial
import threading

from utils.roboclaw_interface import RoboClawInterface
from pmw3901 import PAA5100
from utils.power_sensor import PowerSensor
from utils.kinematic_conversion import (
    jacobian, translation_to_rotation, rotation_to_wheel_velocities,
    wheel_velocities_to_rotation
)
from utils.pidController import PIDController

class PlatformController:
    def __init__(self, config_file: str):
        """
        Initialize the platform controller
        Args:
            config_file: Path to configuration file
        """
        # Load configuration
        with open(config_file, 'r') as f:
            self.config = json.load(f)
            
        # Initialize system parameters
        params = self.config['system_parameters']
        self.rBall = params['rBall']  # meters
        self.rOmni = params['rOmni']  # meters
        self.rZ = params['rZ']  # meters
        self.rX = params['rX']  # meters
        self.beta = params['beta']  # degrees
        
        # Optical flow sensor parameters
        self.flow_resolution = 0.0001  # meters per pixel
        self.flow_frame_rate = 100  # Hz
        
        # Calculate Jacobian matrices
        self.jacobInv, self.jacob = jacobian(
            beta=np.radians(self.beta),  # Convert to radians
            rBall=self.rBall,
            rOmni=self.rOmni,
            rZ=self.rZ,
            rX=self.rX
        )
        
        # Initialize hardware interfaces
        self.roboclaw = RoboClawInterface(use_dual_controllers=True)
        
        # Initialize optical flow sensor
        flow_config = self.config['hardware']['optical_flow']
        self.optical_flow = PAA5100(
            spi_port=flow_config['spi_bus'],
            spi_cs=flow_config['spi_device'],
            spi_cs_gpio=flow_config['cs_pin']
        )
        self.optical_flow.set_rotation(0)  # Set sensor rotation
        self.optical_flow.set_orientation(invert_x=True, invert_y=True, swap_xy=False)
        
        # Initialize power sensor
        power_config = self.config['hardware']['power_sensor']
        self.power_sensor = PowerSensor(
            i2c_bus=power_config['i2c_bus'],
            address=int(power_config['address'], 16)
        )
        self.power_sensor.set_calibration_32V_2A()  # Set calibration for 32V/2A range
        
        # Initialize data logging
        self.data_buffer = []
        self.error_log = []
        self.start_time = time.time()
        self.last_plot_update = 0
        self.plot_update_interval = self.config['logging']['plot_update_interval']
        
        # Initialize control variables
        self.dt = self.config['initial_conditions']['control_loop']['dt']
        self.translation_setpoint = self.config['initial_conditions']['translation_velocity']
        self.running = False
        
        # Initialize serial communication
        self.serial = serial.Serial('/dev/ttyAMA0', 115200, timeout=1)
        
        # Initialize PID controllers
        pid_gains = self.config['initial_conditions']['control_loop']['pid_gains']
        self.pid_x = PIDController(pid_gains['kp'], pid_gains['ki'], pid_gains['kd'])
        self.pid_y = PIDController(pid_gains['kp'], pid_gains['ki'], pid_gains['kd'])
        
        # Initialize plots
        self.fig, self.axes = plt.subplots(2, 2, figsize=(12, 8))
        plt.ion()
        
    def check_connections(self) -> bool:
        """Check all hardware connections"""
        try:
            # Check RoboClaw connection
            if not self.roboclaw.connect():
                self.error_log.append("Failed to connect to RoboClaw controllers")
                return False
                
            # Check optical flow sensor
            dx, dy = self.optical_flow.get_motion()
            if dx is None or dy is None:
                self.error_log.append("Failed to read from optical flow sensor")
                return False
                
            # Check power sensor
            readings = self.power_sensor.get_all_readings()
            if any(r is None for r in readings):
                self.error_log.append("Failed to read from power sensor")
                return False
                
            return True
            
        except Exception as e:
            self.error_log.append(f"Connection check error: {str(e)}")
            return False
            
    def log_data(self, data: Dict):
        """Log data to buffer"""
        data['timestamp'] = time.time()
        self.data_buffer.append(data)
        
        # Remove old data
        buffer_duration = self.config['initial_conditions']['control_loop']['buffer_duration']
        current_time = time.time()
        self.data_buffer = [d for d in self.data_buffer 
                           if current_time - d['timestamp'] <= buffer_duration]
                           
    def save_data(self):
        """Save logged data to CSV file"""
        filename = self.config['logging']['data_file']
        with open(filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=self.data_buffer[0].keys())
            writer.writeheader()
            writer.writerows(self.data_buffer)
            
    def save_error_log(self):
        """Save error log to file"""
        filename = self.config['logging']['error_file']
        with open(filename, 'w') as f:
            for error in self.error_log:
                f.write(f"{datetime.now()}: {error}\n")
                
    def update_plots(self):
        """Update all plots with latest data"""
        if not self.data_buffer:
            return
            
        timestamps = [d['timestamp'] for d in self.data_buffer]
        
        # Plot 1: Translation velocities
        self.axes[0, 0].clear()
        self.axes[0, 0].plot(timestamps, [d['setpoint_vx'] for d in self.data_buffer], 'b--', label='Setpoint Vx')
        self.axes[0, 0].plot(timestamps, [d['setpoint_vy'] for d in self.data_buffer], 'r--', label='Setpoint Vy')
        self.axes[0, 0].plot(timestamps, [d['measured_vx'] for d in self.data_buffer], 'b-', label='Measured Vx')
        self.axes[0, 0].plot(timestamps, [d['measured_vy'] for d in self.data_buffer], 'r-', label='Measured Vy')
        self.axes[0, 0].plot(timestamps, [d['expected_vx'] for d in self.data_buffer], 'b:', label='Expected Vx')
        self.axes[0, 0].plot(timestamps, [d['expected_vy'] for d in self.data_buffer], 'r:', label='Expected Vy')
        self.axes[0, 0].set_title('Translation Velocities')
        self.axes[0, 0].legend()
        self.axes[0, 0].grid(True)
        
        # Plot 2: Wheel velocities
        self.axes[0, 1].clear()
        for i in range(3):
            self.axes[0, 1].plot(timestamps, [d['wheel_velocities'][i] for d in self.data_buffer], 
                                f'C{i}--', label=f'Commanded ω{i+1}')
            self.axes[0, 1].plot(timestamps, [d['wheel_velocities_measured'][i] for d in self.data_buffer], 
                                f'C{i}-', label=f'Measured ω{i+1}')
        self.axes[0, 1].set_title('Wheel Angular Velocities')
        self.axes[0, 1].legend()
        self.axes[0, 1].grid(True)
        
        # Plot 3: Error metrics
        self.axes[1, 0].clear()
        self.axes[1, 0].plot(timestamps, [d['slip_error'] * 100 for d in self.data_buffer], 
                            'b-', label='Slip Error (%)')
        self.axes[1, 0].plot(timestamps, [d['translation_error'] * 100 for d in self.data_buffer], 
                            'r-', label='Translation Error (%)')
        for i in range(3):
            self.axes[1, 0].plot(timestamps, [d['wheel_errors'][i] * 100 for d in self.data_buffer], 
                                f'C{i}:', label=f'Wheel {i+1} Error (%)')
        self.axes[1, 0].set_title('Error Metrics')
        self.axes[1, 0].set_ylabel('Error (%)')
        self.axes[1, 0].legend()
        self.axes[1, 0].grid(True)
        
        # Plot 4: Power measurements
        self.axes[1, 1].clear()
        
        # Plot INA219 measurements
        self.axes[1, 1].plot(timestamps, [d['power_data']['current'] for d in self.data_buffer], 
                            'b-', label='INA219 Current')
        self.axes[1, 1].plot(timestamps, [d['power_data']['power'] for d in self.data_buffer], 
                            'g-', label='INA219 Power')
        
        # Plot RoboClaw measurements for each motor
        for i in range(3):
            self.axes[1, 1].plot(timestamps, [d['roboclaw_power_data'][i]['current'] for d in self.data_buffer], 
                                f'C{i}--', label=f'Motor {i+1} Current')
            self.axes[1, 1].plot(timestamps, [d['roboclaw_power_data'][i]['power'] for d in self.data_buffer], 
                                f'C{i}:', label=f'Motor {i+1} Power')
        
        self.axes[1, 1].set_title('Power Measurements')
        self.axes[1, 1].legend()
        self.axes[1, 1].grid(True)
        
        plt.tight_layout()
        plt.draw()
        plt.pause(0.001)
        
    def control_loop(self):
        """Main control loop"""
        try:
            # Read optical flow sensor data
            dx, dy = self.optical_flow.get_motion()  # Returns (dx, dy) in pixels
            if dx is None or dy is None:
                self.error_log.append(f"Error reading optical flow sensor at {time.time()}")
                return
            
            # Convert optical flow measurements to SI units (m/s)
            measured_translation = np.array([
                -dx * self.flow_resolution * self.flow_frame_rate,  # Convert to m/s
                -dy * self.flow_resolution * self.flow_frame_rate   # Convert to m/s
            ])
            
            # Calculate actual ball rotation from optical flow measurements
            actual_rotation = translation_to_rotation(measured_translation, self.rBall)
            
            # Read RoboClaw error status for all motors
            roboclaw_errors = {}
            for i in range(1, 4):
                data = self.roboclaw.get_motor_data(i)
                if data is not None and 'error' in data:
                    error_code = data['error']
                    roboclaw_errors[f'motor_{i}'] = {
                        'error_code': error_code,
                        'timestamp': time.time() - self.start_time,
                        'description': self._decode_error(error_code)
                    }
                    if error_code != 0:
                        self.error_log.append(
                            f"Motor {i} error: 0x{error_code:02X} - {self._decode_error(error_code)} at {time.time()}"
                        )
            
            # Get current setpoint (already in m/s)
            setpoint = np.array([
                self.config['initial_conditions']['translation_velocity']['vx'],
                self.config['initial_conditions']['translation_velocity']['vy']
            ])
            
            # Calculate errors
            error_x = setpoint[0] - measured_translation[0]
            error_y = setpoint[1] - measured_translation[1]
            
            # Compute PID outputs
            dt = self.config['initial_conditions']['control_loop']['dt']
            pid_x_output = self.pid_x.compute(error_x, dt)
            pid_y_output = self.pid_y.compute(error_y, dt)
            
            # Convert PID outputs to desired ball rotation
            control_vel = np.array([pid_x_output, pid_y_output])
            desired_rotation = translation_to_rotation(control_vel, self.rBall)
            
            # Convert desired rotation to wheel velocities
            wheel_velocities = rotation_to_wheel_velocities(desired_rotation, self.jacobInv)
            
            # Send commands to motors
            for i, vel in enumerate(wheel_velocities):
                self.roboclaw.set_velocity(i + 1, vel)
            
            # Read current wheel velocities and power data from RoboClaw
            wheel_velocities_measured = []
            roboclaw_power_data = []
            for i in range(3):
                data = self.roboclaw.get_motor_data(i + 1)
                if data is not None:
                    # Convert encoder velocity to rad/s
                    encoder_resolution = 3600  # pulses per revolution
                    wheel_velocities_measured.append(data.get('encoder_velocity', 0) * 2 * np.pi / encoder_resolution)
                    
                    # Get power data from RoboClaw
                    motor_power = {
                        'current': data.get('current', 0) / 100.0,  # Convert to Amps
                        'voltage': data.get('voltage', 0) / 10.0,   # Convert to Volts
                        'power': (data.get('current', 0) / 100.0) * (data.get('voltage', 0) / 10.0)  # Compute power in Watts
                    }
                    roboclaw_power_data.append(motor_power)
                else:
                    wheel_velocities_measured.append(0.0)
                    roboclaw_power_data.append({'current': 0, 'voltage': 0, 'power': 0})
            
            # Calculate expected ball rotation from measured wheel velocities (assuming no slip)
            expected_rotation = wheel_velocities_to_rotation(
                np.array(wheel_velocities_measured),
                self.jacob
            )
            
            # Calculate expected translation from rotation
            expected_translation = np.array([
                expected_rotation[1] * self.rBall,  # vx = wy * r
                -expected_rotation[0] * self.rBall  # vy = -wx * r
            ])
            
            # Calculate error metrics
            # 1. Slip error: difference between wheel-based rotation (no slip) and actual rotation from optical flow
            slip_error = np.linalg.norm(expected_rotation - actual_rotation) / np.linalg.norm(expected_rotation) if np.linalg.norm(expected_rotation) > 0 else 0
            
            # 2. Translation error as percentage of desired translation
            translation_error = np.linalg.norm(control_vel - expected_translation) / np.linalg.norm(control_vel) if np.linalg.norm(control_vel) > 0 else 0
            
            # 3. Individual wheel velocity errors as percentages
            wheel_errors = []
            for i in range(3):
                if abs(wheel_velocities[i]) > 0:
                    error = abs(wheel_velocities[i] - wheel_velocities_measured[i]) / abs(wheel_velocities[i])
                else:
                    error = 0
                wheel_errors.append(error)
            
            # Read power sensor data
            power_data = {
                'shunt_voltage': self.power_sensor.getShuntVoltage_mV() / 1000.0,  # Convert to Volts
                'bus_voltage': self.power_sensor.getBusVoltage_V(),  # Already in Volts
                'current': self.power_sensor.getCurrent_mA() / 1000.0,  # Convert to Amps
                'power': self.power_sensor.getPower_W()  # Already in Watts
            }
            
            # Log data
            self.log_data({
                'timestamp': time.time() - self.start_time,
                'setpoint_vx': setpoint[0],
                'setpoint_vy': setpoint[1],
                'measured_vx': measured_translation[0],
                'measured_vy': measured_translation[1],
                'expected_vx': expected_translation[0],
                'expected_vy': expected_translation[1],
                'wheel_velocities': wheel_velocities.tolist(),
                'wheel_velocities_measured': wheel_velocities_measured,
                'slip_error': slip_error,
                'translation_error': translation_error,
                'wheel_errors': wheel_errors,
                'power_data': power_data,
                'roboclaw_power_data': roboclaw_power_data,
                'roboclaw_errors': roboclaw_errors
            })
            
            # Update plots
            self.update_plots()
            
        except Exception as e:
            self.error_log.append(f"Error in control loop: {str(e)}")
            
    def _decode_error(self, error_code: int) -> str:
        """Decode RoboClaw error codes"""
        error_messages = {
            0x00: "No Error",
            0x01: "E-Stop",
            0x02: "Temperature Error",
            0x04: "Main Battery High Error",
            0x08: "Logic Battery High Error",
            0x10: "Logic Battery Low Error",
            0x20: "M1 Driver Fault",
            0x40: "M2 Driver Fault",
            0x80: "Main Battery Low Error"
        }
        
        messages = []
        for code, message in error_messages.items():
            if error_code & code:
                messages.append(message)
        
        return " | ".join(messages) if messages else "Unknown Error"
            
    def run(self):
        """Run the platform controller"""
        print("Initializing platform controller...")
        
        # Check connections
        if not self.check_connections():
            print("Failed to initialize hardware connections")
            self.save_error_log()
            return
            
        print("Hardware connections established")
        print("Waiting for command (S: Stop, U: Update)...")
        
        self.running = True
        control_thread = threading.Thread(target=self.control_loop)
        control_thread.start()
        
        while self.running:
            if self.serial.in_waiting:
                command = self.serial.read().decode().upper()
                
                if command == 'S':
                    print("Stop command received")
                    self.running = False
                    break
                    
                elif command == 'U':
                    print("Update command received")
                    print("Enter new X velocity (m/s):")
                    x = float(input())
                    print("Enter new Y velocity (m/s):")
                    y = float(input())
                    
                    self.translation_setpoint = {'vx': x, 'vy': y}
                    print(f"New setpoint: X={x}, Y={y}")
                    
        # Clean up
        control_thread.join()
        self.save_data()
        self.save_error_log()
        self.cleanup()
        
    def cleanup(self):
        """Clean up resources"""
        self.roboclaw.close()
        self.optical_flow.close()
        self.power_sensor.close()
        self.serial.close()
        
if __name__ == "__main__":
    controller = PlatformController("config/platform_config.json")
    controller.run() 