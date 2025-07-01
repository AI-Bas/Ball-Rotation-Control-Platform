# Hardware Examples Directory

This directory contains example scripts and reference implementations for all hardware components used in the Ball Handler Test Platform.

## Directory Structure

```
examples/
├── roboclaw/
│   ├── speed_examples/          # Motor speed control examples
│   ├── position_examples/       # Motor position control examples
│   └── pwm_examples/           # PWM control examples
├── ina219/
│   └── current_monitoring_examples/  # Current monitoring examples
├── pmw3901/
│   ├── motion_detection_examples/    # Optical flow sensor examples
│   └── frame_capture_examples/       # Frame capture examples
└── maker_pi_rp2040/
    ├── circuitpython_examples/       # CircuitPython examples
    └── communication_examples/       # Communication protocol examples
```

## Hardware Components

### 1. RoboClaw Motor Controllers

#### Speed Examples
- `roboclaw_speed.py` - Basic speed control
- `roboclaw_speedaccel.py` - Speed control with acceleration
- `roboclaw_speeddistance.py` - Speed control with distance limits
- `roboclaw_speedacceldistance.py` - Speed control with acceleration and distance

#### Position Examples
- `roboclaw_position.py` - Basic position control

#### PWM Examples
- `roboclaw_simplepwm.py` - Simple PWM control
- `roboclaw_mixedpwm.py` - Mixed PWM control
- `roboclaw_duty.py` - Duty cycle control

### 2. INA219 Current Sensors

#### Current Monitoring Examples
- Basic current and voltage monitoring
- Multi-channel sensor reading
- Power calculation examples

### 3. PMW3901 Optical Flow Sensor

#### Motion Detection Examples
- `motion.py` - Basic motion detection
- `frame_capture.py` - Frame capture and analysis

### 4. Maker Pi RP2040

#### CircuitPython Examples
- `code.py` - Complete CircuitPython demo with LEDs, motors, and sensors

#### Communication Examples
- UART communication protocols
- JSON command/response examples
- File transfer examples

## Usage

### Running Examples

1. **RoboClaw Examples**:
   ```bash
   cd examples/roboclaw/speed_examples
   python roboclaw_speed.py
   ```

2. **PMW3901 Examples**:
   ```bash
   cd examples/pmw3901/motion_detection_examples
   python motion.py
   ```

3. **Maker Pi RP2040 Examples**:
   - Copy `code.py` to CircuitPython drive
   - Monitor serial output for results

### Hardware Requirements

- **RoboClaw**: 2x30A motor controllers connected via USB/RS232
- **INA219**: Current sensors connected via I2C (addresses 0x40-0x43)
- **PMW3901**: Optical flow sensor connected via SPI
- **Maker Pi RP2040**: Connected via USB for file transfer and serial communication

### Communication Protocols

#### RoboClaw
- **Interface**: USB virtual COM port or RS232
- **Baud Rate**: 460800 (primary), 38400 (fallback)
- **Address**: 0x80 (hex)

#### INA219
- **Interface**: I2C
- **Bus**: 1 (Raspberry Pi 5)
- **Addresses**: 0x40, 0x41, 0x42, 0x43

#### PMW3901
- **Interface**: SPI
- **CS Pin**: GPIO 8
- **Reset Pin**: GPIO 12
- **Motion Pin**: GPIO 16

#### Maker Pi RP2040
- **File Transfer**: USB mass storage
- **Serial Communication**: UART at 115200 baud
- **Protocol**: JSON over serial

## Integration with Main System

These examples serve as reference implementations for the main system components:

- **test_platform_control/utils/roboclaw_interface.py** - Uses local `roboclaw_3.py`
- **test_platform_control/utils/power_sensor.py** - Uses pip `ina219` library
- **test_platform_control/utils/optical_flow_sensor.py** - Uses pip `pmw3901` library
- **test_platform_control/utils/maker_pi_interface.py** - Handles RP2040 communication

## Development Notes

### Library Versions
- **RoboClaw**: Local `roboclaw_3.py` (more comprehensive API)
- **INA219**: Pip package `ina219` (better maintained)
- **PMW3901**: Pip package `pmw3901` (identical functionality)

### Error Handling
All examples include basic error handling for:
- Hardware connection failures
- Communication timeouts
- Invalid parameters

### Testing
Examples can be used for:
- Hardware validation
- Protocol testing
- Performance benchmarking
- Integration testing

## Contributing

When adding new examples:
1. Follow the existing directory structure
2. Include proper error handling
3. Add documentation comments
4. Test with actual hardware
5. Update this README

## References

- [RoboClaw Documentation](https://www.basicmicro.com/roboclaw-2x30a-motor-controller)
- [INA219 Datasheet](https://www.ti.com/lit/ds/symlink/ina219.pdf)
- [PMW3901 Datasheet](https://www.pixart.com/products-detail/PMW3901)
- [Maker Pi RP2040 Documentation](https://www.cytron.io/p-maker-pi-rp2040)
- [CircuitPython Documentation](https://circuitpython.readthedocs.io/) 