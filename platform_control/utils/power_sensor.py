#!/usr/bin/env python3
"""
Power Sensor Interface using INA219
Simple INA219 implementation using smbus2 for Raspberry Pi compatibility
"""

import smbus2
from typing import List, Optional, Dict
import time

class INA219:
    """Simple INA219 implementation using smbus2"""
    
    # INA219 registers
    REG_CONFIG = 0x00
    REG_SHUNTVOLTAGE = 0x01
    REG_BUSVOLTAGE = 0x02
    REG_POWER = 0x03
    REG_CURRENT = 0x04
    REG_CALIBRATION = 0x05
    
    def __init__(self, address=0x40, bus=1):
        self.address = address
        self.bus = smbus2.SMBus(bus)
        self.current_lsb = 0.0001  # 100uA per bit
        self.power_lsb = 0.002     # 2mW per bit
        self.calibration_value = 0
        self._configure()
    
    def _configure(self):
        """Configure INA219 for 16V, 320mA range"""
        # Configuration: 16V range, 320mA range, 12-bit resolution
        config = 0x399F  # 16V, 320mA, 12-bit
        self.bus.write_word_data(self.address, self.REG_CONFIG, config)
        
        # Calibration for 320mA range
        self.calibration_value = 4096
        self.bus.write_word_data(self.address, self.REG_CALIBRATION, self.calibration_value)
    
    def voltage(self):
        """Get bus voltage in volts"""
        try:
            raw = self.bus.read_word_data(self.address, self.REG_BUSVOLTAGE)
            # Convert to voltage (4mV per bit)
            return (raw >> 3) * 0.004
        except:
            return 0.0
    
    def current(self):
        """Get current in amps"""
        try:
            raw = self.bus.read_word_data(self.address, self.REG_CURRENT)
            # Convert to current
            return raw * self.current_lsb
        except:
            return 0.0
    
    def power(self):
        """Get power in watts"""
        try:
            raw = self.bus.read_word_data(self.address, self.REG_POWER)
            # Convert to power
            return raw * self.power_lsb
        except:
            return 0.0
    
    def shunt_voltage(self):
        """Get shunt voltage in volts"""
        try:
            raw = self.bus.read_word_data(self.address, self.REG_SHUNTVOLTAGE)
            # Convert to voltage (10uV per bit)
            return raw * 0.00001
        except:
            return 0.0

class PowerSensor:
    """Class for interfacing with INA219 power monitoring IC using simple implementation"""
    
    def __init__(self, config: dict):
        """
        Initialize the power sensor using simple INA219 implementation
        Args:
            config: Dictionary containing sensor configuration
        """
        self.i2c_bus = config.get('i2c_bus', 1)
        self.address = int(config['address'], 16) if isinstance(config['address'], str) else config['address']
        self.channels = config.get('channels', [0, 1, 2, 3])
        
        # Initialize INA219 sensor using simple implementation
        try:
            self.sensor = INA219(address=self.address, bus=self.i2c_bus)
            print(f"✓ INA219 sensor initialized at address 0x{self.address:02x}")
        except Exception as e:
            print(f"✗ Failed to initialize INA219 sensor: {e}")
            self.sensor = None
        
    def get_shunt_voltage_mV(self) -> float:
        """Get shunt voltage in millivolts"""
        if self.sensor is None:
            return 0.0
        try:
            return self.sensor.shunt_voltage() * 1000  # Convert to mV
        except Exception as e:
            print(f"Error reading shunt voltage: {e}")
            return 0.0
        
    def get_bus_voltage_V(self) -> float:
        """Get bus voltage in volts"""
        if self.sensor is None:
            return 0.0
        try:
            return self.sensor.voltage()
        except Exception as e:
            print(f"Error reading bus voltage: {e}")
            return 0.0
        
    def get_current_mA(self) -> float:
        """Get current in milliamps"""
        if self.sensor is None:
            return 0.0
        try:
            return self.sensor.current() * 1000  # Convert to mA
        except Exception as e:
            print(f"Error reading current: {e}")
            return 0.0
        
    def get_power_W(self) -> float:
        """Get power in watts"""
        if self.sensor is None:
            return 0.0
        try:
            return self.sensor.power()
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
        if self.sensor:
            self.sensor.bus.close() 