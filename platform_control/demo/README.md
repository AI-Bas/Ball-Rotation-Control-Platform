# RoboClaw Motor Demo Scripts

This directory contains the main demo scripts for controlling RoboClaw motor drivers.

## Scripts Overview

### 1. `demo_test.py` - Motor Connection Testing & Mapping
**Purpose**: Comprehensive motor connectivity testing and user-guided motor mapping.

**Features**:
- Tests all motors on both controllers systematically
- Monitors encoder speed and current for verification
- User-guided motor mapping with prompts
- Identifies working motors and their control methods
- Provides configuration output for `demo.py`

**Usage**:
```bash
python3 demo_test.py
```

**Process**:
1. Connects to both RoboClaw controllers
2. Tests communication with each controller
3. Tests each motor channel with speed control
4. Monitors encoder feedback and current draw
5. Prompts user to identify which motor is turning
6. Maps motors to motor1, motor2, motor3 labels
7. Outputs configuration for `demo.py`

### 2. `demo.py` - Main Demo Control Script
**Purpose**: Menu-driven demo with static velocity and motion profile options.

**Features**:
- Menu system for different demo modes
- Static velocity demo with step response
- Motion profile demo with sinusoidal/ramp profiles
- Real-time motor monitoring
- User-configurable speeds and profiles

**Usage**:
```bash
python3 demo.py
```

**Menu Options**:
1. **Static Velocity Demo**: Run motors at constant speeds for 15 seconds, then pause for 5 seconds
2. **Motion Profile Demo**: Run motors with sinusoidal or ramp velocity profiles
3. **Monitor Motors Only**: Real-time monitoring for 10 seconds
4. **Exit**: Close the demo

### 3. `demo_motion.py` - Motion Profile Generator
**Purpose**: Generates velocity profiles for motor control.

**Features**:
- Sinusoidal velocity profiles
- Ramp up/down velocity profiles
- Configurable amplitude, frequency, and duration
- Profile preview functionality
- User input for parameter configuration

**Usage**:
```bash
python3 demo_motion.py
```

**Profile Types**:
- **Sinusoidal**: Smooth oscillation with configurable amplitude and frequency
- **Ramp**: Gradual ramp up, constant speed, then ramp down

## Hardware Configuration

### Controller Setup
- **RC1**: Connected to `/dev/ttyACM2`
- **RC2**: Connected to `/dev/ttyACM1`
- **Address**: 0x80 (default RoboClaw address)
- **Baudrate**: 460800

### Motor Configuration
Update the `motor_config` in `demo.py` based on `demo_test.py` results:

```python
self.motor_config = {
    'motor1': {'controller': 'RC1', 'channel': 'M1', 'speed': 400},
    'motor2': {'controller': 'RC1', 'channel': 'M2', 'speed': 400},
    'motor3': {'controller': 'RC2', 'channel': 'M1', 'speed': 400}
}
```

## Workflow

### First Time Setup
1. **Run connectivity test**: `python3 demo_test.py`
2. **Follow motor mapping prompts**: Identify which motor is which
3. **Update demo.py configuration**: Copy the output configuration
4. **Test the demo**: `python3 demo.py`

### Regular Usage
1. **For testing**: Use `demo_test.py` to verify connections
2. **For demos**: Use `demo.py` with menu options
3. **For motion profiles**: Use `demo_motion.py` to generate profiles

## Safety Features

- **Emergency Stop**: Ctrl+C stops all motors immediately
- **Error Monitoring**: Continuous monitoring of voltage, current, and error states
- **Safe Shutdown**: Motors are stopped before script exit
- **Connection Verification**: Controllers are tested before motor operation

## Monitoring Data

The scripts monitor:
- **Encoder Speed**: Real-time motor speed in encoder counts per second
- **Voltage**: Main battery voltage
- **Current**: Motor current draw in amps
- **Error Status**: RoboClaw error codes
- **Motor Status**: Running/Stopped/Error states

## Troubleshooting

### Common Issues
1. **Connection Failed**: Check USB ports and permissions
2. **Motor Not Responding**: Check wiring and power supply
3. **Communication Errors**: Verify baudrate and address settings
4. **Import Errors**: Ensure `roboclaw_3.py` is in the utils directory

### Debug Steps
1. Run `demo_test.py` to verify all connections
2. Check motor mapping is correct
3. Verify power supply and wiring
4. Test individual motors if needed

## File Organization

```
demo/
├── README.md           # This file
├── demo_test.py        # Motor testing and mapping
├── demo.py            # Main demo control script
└── demo_motion.py     # Motion profile generator
```

## Dependencies

- `roboclaw_3.py` (in `../utils/`)
- Python 3.x
- Serial communication libraries
- Math library for motion profiles

## Notes

- Always run `demo_test.py` first to ensure proper motor mapping
- Update motor configuration in `demo.py` after running tests
- Monitor motor behavior during operation
- Use appropriate speeds for your hardware setup
- Keep emergency stop accessible during testing 