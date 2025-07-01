import time
import platform
from typing import Tuple, Optional

class OpticalFlowSensor:
    def __init__(self, config: dict):
        """
        Initialize the optical flow sensor
        Args:
            config: Dictionary containing sensor configuration
        """
        self.spi_bus = config['spi_bus']
        self.spi_device = config['spi_device']
        self.cs_pin = config['cs_pin']
        self.reset_pin = config['reset_pin']
        self.motion_pin = config['motion_pin']
        
        # Check if running on Linux (Raspberry Pi)
        if platform.system() == 'Linux':
            try:
                import spidev
                from pmw3901 import PAA5100
                import RPi.GPIO as GPIO
                
                # Initialize GPIO
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(self.cs_pin, GPIO.OUT)
                GPIO.setup(self.reset_pin, GPIO.OUT)
                GPIO.setup(self.motion_pin, GPIO.IN)
                
                # Initialize PAA5100 sensor
                self.sensor = PAA5100(spi_port=self.spi_bus, spi_cs=self.cs_pin)
                
                # Reset sensor
                self.reset()
                
                # Set rotation (0 degrees by default)
                self.sensor.set_rotation(0)
                
                self.is_linux = True
                self.GPIO = GPIO
            except ImportError as e:
                print(f"Warning: Required packages not found ({e}). Running in simulation mode.")
                self.is_linux = False
                self.GPIO = None
        else:
            print("Warning: Not running on Linux. Running in simulation mode.")
            self.is_linux = False
            self.GPIO = None
        
    def reset(self):
        """Reset the optical flow sensor"""
        if self.is_linux and self.GPIO:
            self.GPIO.output(self.reset_pin, self.GPIO.LOW)
            time.sleep(0.1)
            self.GPIO.output(self.reset_pin, self.GPIO.HIGH)
            time.sleep(0.1)
        
    def read_motion(self) -> Tuple[Optional[float], Optional[float]]:
        """
        Read motion data from the sensor
        Returns:
            Tuple of (x_velocity, y_velocity) in mm/s
        """
        if not self.is_linux:
            # Return simulated values for development
            return 0.0, 0.0
            
        try:
            # Get motion data using the more reliable burst read method
            x, y = self.sensor.get_motion()
            
            # Convert to mm/s (sensor specific conversion)
            x_vel = x * 0.1  # Adjust based on sensor specifications
            y_vel = y * 0.1
            
            return x_vel, y_vel
            
        except Exception as e:
            print(f"Error reading optical flow sensor: {str(e)}")
            return None, None
            
    def close(self):
        """Clean up resources"""
        if self.is_linux and self.GPIO:
            self.GPIO.cleanup() 