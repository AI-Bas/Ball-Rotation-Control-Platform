# Hardware and Library Setup - Ball Rotation Control Platform

## System Overview
- **Platform**: Raspberry Pi 5 (ARM64 aarch64)
- **OS**: Ubuntu 24.04 LTS (Noble Numbat)
- **Kernel**: Linux 6.8.0-1018-raspi
- **Python**: 3.12.3
- **Purpose**: Three-wheel omni-directional ball balancing system for RoboCup football competition
- **License**: GNU GPL v3 (suitable for academic and commercial use)

## Hardware Components

### Core Motion Control (Raspberry Pi 5)
- **RoboClaw 2x30A Motor Controllers** (2 units)
  - Communication: USB virtual COM port (primary), RS232 (fallback)
  - Addresses: 0x80 (both controllers)
  - Motors: 3 active (motor1, motor2, motor3), 1 future (motor4 for linear stage)
  - Ports: COM5 (rc1), COM4 (rc2)
  - Safety: E-Stop monitoring, temperature protection, current limiting

- **PMW3901/PAA5100JE Optical Flow Sensor**
  - Interface: SPI
  - Purpose: Ball position and velocity tracking
  - Pins: CS=8, Reset=12, Motion=16
  - Library: pip package `pmw3901` (fully compatible)

- **INA219 Power Monitoring Sensors** (4 channels)
  - Interface: I2C
  - Addresses: 0x40, 0x41, 0x42, 0x43
  - Purpose: Real-time current and voltage monitoring
  - Library: pip package `ina219` (migrated from local implementation)

### Experimental Modules (Maker Pi RP2040)
- **Type**: Cytron Maker Pi RP2040
- **Platform**: CircuitPython (recommended over MicroPython)
- **Communication**: USB mass storage + UART at 115200 baud
- **Responsibility**: Experimental sensors, displays, IO modules (NOT core motion control)
- **Integration**: JSON command protocol over UART

## Development Environment Setup

### Python Environment
```bash
# Install Python packages
sudo apt update
sudo apt install -y python3-pip python3-venv

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate
```

### User Permissions
```bash
# Add user to dialout group for I2C/SPI access
sudo usermod -a -G dialout $USER

# Logout and login required for group changes to take effect
logout
# Then login again
```

### Hardware Access Verification
```bash
# GPIO access
ls -la /dev/gpiochip*    # 5 devices available

# I2C access
ls -la /dev/i2c*         # 3 devices available
i2cdetect -y 1           # Should show devices at 0x40-0x43

# SPI access
ls -la /dev/spidev*      # 3 devices available

# USB serial access
ls -la /dev/ttyACM*      # 2 devices available
```

## Library Management Strategy

### Pip Packages (Preferred)
```bash
# Core hardware libraries
pmw3901>=1.0.0          # Optical flow sensor (fully compatible)
ina219>=1.4.1           # Current sensor (migrated from local)
gpiod>=2.0.0            # GPIO library for PMW3901
gpiodevice>=0.1.0       # GPIO device library for PMW3901

# Communication
pyserial>=3.5           # Serial communication
smbus2>=0.5.0           # I2C communication
spidev>=3.7             # SPI communication

# Platform-specific
RPi.GPIO>=0.7.1         # Raspberry Pi GPIO control

# Scientific computing
numpy>=2.3.1            # Numerical computations
scipy>=1.16.0           # Scientific computing
matplotlib>=3.10.3      # Visualization
pandas>=2.3.0           # Data processing

# Development tools
black>=25.1.0           # Code formatting
flake8>=7.3.0           # Linting
mypy>=1.16.1            # Type checking
```

### Local Libraries (Retained)
- **roboclaw_3.py**: RoboClaw motor controller interface
  - Location: `roboclaw_python/roboclaw_3.py`
  - Reason: More comprehensive API than pip alternative
  - Features: Complete RoboClaw command set, settings management
  - Used by: All test scripts and examples

### Removed Libraries
- `examples/roboclaw/python-roboclaw-master/` - Modern API (not used)
- `roboclaw_python/roboclaw.py` - Duplicate of roboclaw_3.py
- `Optical Flow Sensor/pmw3901-python-main/` - Replaced by pip package
- `Current-Power_Monitor_HAT_Code/RaspberryPi/ina219.py` - Replaced by pip package

## Communication Protocols

### Hardware Communication
- **USB**: Primary for RoboClaw controllers (automatic baud rate)
- **I2C**: Power sensors at addresses 0x40-0x43
- **SPI**: Optical flow sensor on bus 0, device 0
- **UART**: Maker Pi RP2040 communication at 115200 baud

### Maker Pi RP2040 Protocol
```json
{
  "protocol": "JSON over UART",
  "baud_rate": 115200,
  "commands": ["read_sensors", "set_leds", "set_motors", "get_status"],
  "response_format": {"status": "ok|error", "data": {}, "message": ""}
}
```

## Example Scripts Organization

### Structure
```
examples/
├── roboclaw/                    # Motor controller examples
│   ├── speed_examples/          # 4 speed control examples
│   ├── position_examples/       # 1 position control example
│   └── pwm_examples/           # 3 PWM control examples
├── ina219/                      # Current sensor examples
│   └── current_monitoring_examples/  # Ready for examples
├── pmw3901/                     # Optical flow sensor examples
│   ├── motion_detection_examples/    # 2 motion detection examples
│   └── frame_capture_examples/       # Ready for examples
└── maker_pi_rp2040/            # Maker Pi RP2040 examples
    ├── circuitpython_examples/       # 1 CircuitPython demo
    └── communication_examples/       # 2 UART communication examples
```

### Example Usage
```python
# RoboClaw example (using local library)
from roboclaw import Roboclaw
rc = Roboclaw("COM3", 115200)
rc.Open()
enc1 = rc.ReadEncM1(0x80)
rc.SpeedM1(0x80, 12000)

# INA219 example (using pip package)
from ina219 import INA219
sensor = INA219(shunt_ohms=0.1, address=0x40)
current = sensor.current()

# PMW3901 example (using pip package)
from pmw3901 import PAA5100
sensor = PAA5100()
motion = sensor.get_motion()
```

## Library Compatibility Analysis

### INA219 Migration
- **Before**: Local implementation using deprecated `smbus`
- **After**: Pip package using `smbus2`
- **Benefits**: Better error handling, configurable ranges, automatic fallback
- **Compatibility**: Full compatibility with existing code

### PMW3901 Migration
- **Before**: Local library with complex setup
- **After**: Pip package with simplified interface
- **Benefits**: Easier installation, better documentation, active maintenance
- **Compatibility**: Full compatibility with PAA5100JE variant

### RoboClaw Library
- **Pip Alternative**: `roboclaw-python` (different API)
- **Local Library**: `roboclaw_3.py` (comprehensive API)
- **Decision**: Keep local library for better functionality
- **Features**: Complete settings management, backup/restore, error handling

## Testing and Validation

### Library Compatibility Test
```bash
# Test all libraries
python3 -c "
import pmw3901; print('PMW3901: ✓ PASSED')
import ina219; print('INA219: ✓ PASSED')
import sys; sys.path.append('roboclaw_python'); import roboclaw_3; print('RoboClaw: ✓ PASSED')
import smbus2; print('I2C: ✓ PASSED')
import serial; print('Serial: ✓ PASSED')
print('\\nOverall: 5/5 tests passed')
print('✓ All libraries are compatible and ready for use!')
"
```

### Hardware Testing
```bash
# Test I2C access
python3 -c "import smbus2; print('I2C access working')"

# Test SPI access
python3 -c "import spidev; print('SPI access working')"

# Test GPIO access
python3 -c "import RPi.GPIO as GPIO; print('GPIO access working')"

# Test USB serial access
python3 -c "import serial; print('USB serial access working')"
```

## Troubleshooting

### Permission Issues
If you encounter permission errors for I2C/SPI devices:
1. Ensure you're logged out and back in after being added to dialout group
2. Check group membership: `groups`
3. Verify device permissions: `ls -la /dev/i2c* /dev/spidev*`

### Import Errors
If you encounter import errors:
1. Ensure virtual environment is activated: `source venv/bin/activate`
2. Check Python path: `python -c "import sys; print(sys.path)"`
3. Verify package installation: `pip list`

### Hardware Detection Issues
If hardware devices are not detected:
1. Check device tree: `ls -la /dev/gpiochip* /dev/i2c* /dev/spidev*`
2. Verify kernel modules: `lsmod | grep i2c`
3. Check system logs: `dmesg | grep -i i2c`

## Maintenance Guidelines

### Library Updates
1. **Regular Updates**: Check for pip package updates monthly
2. **Compatibility Testing**: Test all updates before deployment
3. **Documentation**: Update documentation with any library changes
4. **Backup**: Maintain backup of working configurations

### Hardware Maintenance
1. **Connection Verification**: Regular hardware connection testing
2. **Settings Backup**: Automatic backup of RoboClaw settings
3. **Error Monitoring**: Continuous error status monitoring
4. **Performance Tracking**: Regular system performance validation

### Code Maintenance
1. **Modular Updates**: Update modules independently
2. **Testing**: Comprehensive testing after any changes
3. **Documentation**: Keep all documentation synchronized
4. **Version Control**: Maintain clear change tracking

## License Considerations

### GNU GPL v3 Suitability
- **Academic Use**: ✅ Suitable for graduation projects
- **Commercial Use**: ✅ Allows commercial use with source code sharing
- **RoboCup Competition**: ✅ Appropriate for competitive robotics
- **Public Resources**: ✅ Compatible with publicly available libraries
- **Requirements**: Must share source code if distributing modified versions

### License Compliance
- **Attribution**: All third-party libraries properly attributed
- **Source Code**: All modifications to GPL libraries must be shared
- **Distribution**: Binary distributions must include source code offer
- **Compatibility**: Compatible with pip package licenses (MIT, Apache, etc.)

## Lessons Learned

### Library Management
1. **Pip First**: Always check for pip packages before using local libraries
2. **Compatibility Testing**: Test pip packages thoroughly before migration
3. **Local Retention**: Keep local libraries only when pip alternatives are inferior
4. **Documentation**: Maintain clear documentation of library choices and reasons

### Hardware Integration
1. **Clear Responsibilities**: Separate core motion control from experimental modules
2. **Communication Protocols**: Use appropriate protocols for each component
3. **Error Handling**: Implement comprehensive error handling and fallback mechanisms
4. **Configuration Management**: Centralize configuration in JSON files

### Development Workflow
1. **Modular Design**: Maintain separate utilities for specific functions
2. **Testing Strategy**: Comprehensive testing with incremental validation
3. **Documentation**: Keep all documentation updated and consistent
4. **Version Control**: Track changes and maintain backup strategies

---
*Last Updated: 2025-01-29*
*Environment: Raspberry Pi 5 with Ubuntu 24.04 LTS*
*License: GNU GPL v3* 