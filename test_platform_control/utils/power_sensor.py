import smbus
from typing import List, Optional, Dict
from enum import IntEnum

class BusVoltageRange(IntEnum):
    """Constants for bus voltage range"""
    RANGE_16V = 0x00  # set bus voltage range to 16V
    RANGE_32V = 0x01  # set bus voltage range to 32V (default)

class Gain(IntEnum):
    """Constants for gain"""
    DIV_1_40MV = 0x00   # shunt prog. gain set to  1, 40 mV range
    DIV_2_80MV = 0x01   # shunt prog. gain set to /2, 80 mV range
    DIV_4_160MV = 0x02  # shunt prog. gain set to /4, 160 mV range
    DIV_8_320MV = 0x03  # shunt prog. gain set to /8, 320 mV range

class ADCResolution(IntEnum):
    """Constants for ADC resolution"""
    ADCRES_9BIT_1S = 0x00    #  9bit,   1 sample,     84us
    ADCRES_10BIT_1S = 0x01   # 10bit,   1 sample,    148us
    ADCRES_11BIT_1S = 0x02   # 11 bit,  1 sample,    276us
    ADCRES_12BIT_1S = 0x03   # 12 bit,  1 sample,    532us
    ADCRES_12BIT_2S = 0x09   # 12 bit,  2 samples,  1.06ms
    ADCRES_12BIT_4S = 0x0A   # 12 bit,  4 samples,  2.13ms
    ADCRES_12BIT_8S = 0x0B   # 12bit,   8 samples,  4.26ms
    ADCRES_12BIT_16S = 0x0C  # 12bit,  16 samples,  8.51ms
    ADCRES_12BIT_32S = 0x0D  # 12bit,  32 samples, 17.02ms
    ADCRES_12BIT_64S = 0x0E  # 12bit,  64 samples, 34.05ms
    ADCRES_12BIT_128S = 0x0F # 12bit, 128 samples, 68.10ms

class Mode(IntEnum):
    """Constants for operating mode"""
    POWERDOWN = 0x00              # power down
    SVOLT_TRIGGERED = 0x01        # shunt voltage triggered
    BVOLT_TRIGGERED = 0x02        # bus voltage triggered
    SANDBVOLT_TRIGGERED = 0x03    # shunt and bus voltage triggered
    ADCOFF = 0x04                 # ADC off
    SVOLT_CONTINUOUS = 0x05       # shunt voltage continuous
    BVOLT_CONTINUOUS = 0x06       # bus voltage continuous
    SANDBVOLT_CONTINUOUS = 0x07   # shunt and bus voltage continuous

class PowerSensor:
    """Class for interfacing with INA219 power monitoring IC"""
    
    # Register addresses
    REG_CONFIG = 0x00
    REG_SHUNTVOLTAGE = 0x01
    REG_BUSVOLTAGE = 0x02
    REG_POWER = 0x03
    REG_CURRENT = 0x04
    REG_CALIBRATION = 0x05
    
    def __init__(self, config: dict):
        """
        Initialize the power sensor
        Args:
            config: Dictionary containing sensor configuration
        """
        self.i2c_bus = config['i2c_bus']
        self.address = int(config['address'], 16)
        self.channels = config['channels']
        
        # Initialize I2C
        self.bus = smbus.SMBus(self.i2c_bus)
        
        # Initialize calibration values
        self._cal_value = 0
        self._current_lsb = 0
        self._power_lsb = 0
        
        # Set default configuration
        self.set_calibration_32V_2A()
        
    def set_calibration_32V_2A(self):
        """Configure sensor for 32V and 2A range"""
        # Current LSB = 100uA per bit
        self._current_lsb = 0.1
        
        # Calibration value
        self._cal_value = 4096
        
        # Power LSB = 2mW per bit
        self._power_lsb = 0.002
        
        # Set calibration register
        self.write(self.REG_CALIBRATION, self._cal_value)
        
        # Configure sensor
        config = (BusVoltageRange.RANGE_32V << 13 |
                 Gain.DIV_8_320MV << 11 |
                 ADCResolution.ADCRES_12BIT_32S << 7 |
                 ADCResolution.ADCRES_12BIT_32S << 3 |
                 Mode.SANDBVOLT_CONTINUOUS)
        
        self.write(self.REG_CONFIG, config)
        
    def read(self, address: int) -> int:
        """Read 16-bit value from register"""
        data = self.bus.read_i2c_block_data(self.address, address, 2)
        return ((data[0] * 256) + data[1])
        
    def write(self, address: int, data: int):
        """Write 16-bit value to register"""
        temp = [0, 0]
        temp[1] = data & 0xFF
        temp[0] = (data & 0xFF00) >> 8
        self.bus.write_i2c_block_data(self.address, address, temp)
        
    def get_shunt_voltage_mV(self) -> float:
        """Get shunt voltage in millivolts"""
        self.write(self.REG_CALIBRATION, self._cal_value)
        value = self.read(self.REG_SHUNTVOLTAGE)
        if value > 32767:
            value -= 65535
        return value * 0.01
        
    def get_bus_voltage_V(self) -> float:
        """Get bus voltage in volts"""
        self.write(self.REG_CALIBRATION, self._cal_value)
        value = self.read(self.REG_BUSVOLTAGE)
        return (value >> 3) * 0.004
        
    def get_current_mA(self) -> float:
        """Get current in milliamps"""
        value = self.read(self.REG_CURRENT)
        if value > 32767:
            value -= 65535
        return value * self._current_lsb
        
    def get_power_W(self) -> float:
        """Get power in watts"""
        value = self.read(self.REG_POWER)
        if value > 32767:
            value -= 65535
        return value * self._power_lsb
        
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
        try:
            self.bus.close()
        except Exception as e:
            print(f"Error closing I2C connection: {str(e)}") 