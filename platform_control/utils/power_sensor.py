import board
import busio
from adafruit_ina219 import INA219
from typing import List, Optional, Dict
import time

class PowerSensor:
    """Class for interfacing with INA219 power monitoring IC using Adafruit CircuitPython library"""
    
    def __init__(self, config: dict):
        """
        Initialize the power sensor using Adafruit CircuitPython INA219 library
        Args:
            config: Dictionary containing sensor configuration
        """
        self.i2c_bus = config.get('i2c_bus', 1)
        self.address = int(config['address'], 16) if isinstance(config['address'], str) else config['address']
        self.channels = config.get('channels', [0, 1, 2, 3])
        
        # Initialize INA219 sensor using Adafruit CircuitPython library
        try:
            # Initialize I2C bus
            i2c = busio.I2C(board.SCL, board.SDA)
            # Use shunt resistance of 0.1 ohm (typical for INA219)
            self.sensor = INA219(i2c)
            print(f"✓ INA219 sensor initialized at address 0x{self.address:02x}")
        except Exception as e:
            print(f"✗ Failed to initialize INA219 sensor: {e}")
            self.sensor = None
        
    def get_shunt_voltage_mV(self) -> float:
        """Get shunt voltage in millivolts"""
        if self.sensor is None:
            return 0.0
        try:
            return self.sensor.shunt_voltage * 1000  # Convert to mV
        except Exception as e:
            print(f"Error reading shunt voltage: {e}")
            return 0.0
        
    def get_bus_voltage_V(self) -> float:
        """Get bus voltage in volts"""
        if self.sensor is None:
            return 0.0
        try:
            return self.sensor.bus_voltage
        except Exception as e:
            print(f"Error reading bus voltage: {e}")
            return 0.0
        
    def get_current_mA(self) -> float:
        """Get current in milliamps"""
        if self.sensor is None:
            return 0.0
        try:
            return self.sensor.current * 1000  # Convert to mA
        except Exception as e:
            print(f"Error reading current: {e}")
            return 0.0
        
    def get_power_W(self) -> float:
        """Get power in watts"""
        if self.sensor is None:
            return 0.0
        try:
            return self.sensor.power
        except Exception as e:
            print(f"Error reading power: {e}")
            return 0.0
        
    def read_channel(self, channel: int) -> Optional[Dict[str, float]]:
        """
        Read power measurements for a specific channel
        Args:
            channel: Channel number (0-3)
        Returns:
            Dictionary containing voltage, current and power readings
        """
        if channel not in self.channels:
            print(f"Invalid channel: {channel}")
            return None
            
        if self.sensor is None:
            return None
            
        try:
            # Read measurements
            voltage = self.get_bus_voltage_V()
            current = self.get_current_mA() / 1000.0  # Convert to amps
            power = self.get_power_W()
            
            return {
                'voltage': voltage,
                'current': current,
                'power': power
            }
            
        except Exception as e:
            print(f"Error reading channel {channel}: {str(e)}")
            return None
            
    def read_all_channels(self) -> List[Optional[Dict[str, float]]]:
        """Read power measurements from all channels"""
        return [self.read_channel(channel) for channel in self.channels]
        
    def close(self):
        """Close I2C connection"""
        # The Adafruit library handles connection cleanup automatically
        pass 