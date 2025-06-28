# Football Rotation Motion Control Test Platform

A comprehensive three-wheel omni-directional ball balancing system designed for robot soccer applications. This platform provides real-time ball balancing with optical flow sensing, precise motor control with position feedback, and comprehensive testing and calibration capabilities.

## 🎯 Project Overview

The Football Rotation Motion Control Test Platform is a sophisticated motion control system that enables precise ball manipulation through three omni-directional wheels. The system is designed for research and development in robot soccer applications, providing a modular architecture that supports AI agent development and comprehensive testing capabilities.

### Key Features

- **Real-time ball balancing** with optical flow sensing
- **Precise motor control** with position feedback
- **Comprehensive testing and calibration** capabilities
- **Modular architecture** for AI agent development
- **Safety-first design** with comprehensive error handling
- **Cross-platform compatibility** (Windows, Linux, Raspberry Pi)

## 🏗️ System Architecture

### Hardware Components

#### Core Motion Control (Raspberry Pi 5)
- **RoboClaw 2x30A motor controllers** (2x) - Primary motor control
- **Optical flow sensor (PAA5100JE)** - Ball position and velocity tracking
- **Power monitoring (INA219)** - Real-time current and voltage monitoring
- **Encoder feedback processing** - Position and velocity feedback

#### Experimental Modules (Maker Pi RP2040)
- **Experimental sensors** - Future sensor modules
- **Display modules** - User interface and status displays
- **IO modules** - Additional functionality expansion

### Software Architecture

The system follows a modular design with clear separation of concerns:

```
test_platform_control/
├── platform_control.py          # Main control interface
├── config/
│   └── platform_config.json     # Central configuration
├── utils/                       # Core utility modules
│   ├── roboclaw_interface.py    # Motor controller communication
│   ├── kinematic_conversion.py  # Kinematic transformations
│   ├── pid_controller.py        # PID control implementation
│   ├── optical_flow_sensor.py   # Optical flow sensor interface
│   ├── power_sensor.py          # Power monitoring interface
│   └── maker_pi_interface.py    # Experimental module interface
└── tests/                       # Testing and calibration modules
    ├── system_test.py           # Central testing controller
    ├── roboclaw_motor_identification.py
    ├── roboclaw_settings_manager.py
    ├── calibration_tests.py
    ├── system_characterization_tests.py
    └── maker_pi_tests.py
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- Raspberry Pi 5 (for deployment)
- RoboClaw 2x30A motor controllers
- Optical flow sensor (PAA5100JE)
- Power monitoring sensors (INA219)
- Maker Pi RP2040 (optional, for experimental modules)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/football-rotation-motion-control-test-platform.git
   cd football-rotation-motion-control-test-platform
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure hardware connections:**
   - Connect RoboClaw controllers via USB
   - Connect optical flow sensor via SPI
   - Connect power monitoring sensors via I2C
   - Connect Maker Pi RP2040 via USB (optional)

4. **Run initial setup:**
   ```bash
   cd test_platform_control
   python tests/system_test.py
   ```

### Configuration

The system uses a centralized configuration approach:

- **`platform_config.json`** - Main configuration file
- **`system_design_architecture.yaml`** - System architecture documentation
- **Test logs** - Automatic logging in `tests/test_logs/`
- **Settings backup** - Automatic backup in `tests/roboclaw_settings_backup/`

## 🧪 Testing and Calibration

The platform includes comprehensive testing and calibration capabilities:

### System Test Suite

Run the central testing controller:
```bash
python tests/system_test.py
```

This provides access to:
1. **Maker Pi Identification** - Detect and configure experimental modules
2. **RoboClaw Motor Identification** - Interactive motor mapping
3. **RoboClaw Settings Management** - Settings backup and comparison
4. **Calibration Tests** - Motor and system calibration
5. **System Characterization Tests** - Performance analysis

### Individual Test Modules

Each test module can be run independently:

```bash
# Motor identification
python tests/roboclaw_motor_identification.py

# Settings management
python tests/roboclaw_settings_manager.py

# Calibration tests
python tests/calibration_tests.py

# System characterization
python tests/system_characterization_tests.py

# Maker Pi testing
python tests/maker_pi_tests.py
```

## 🔧 Development

### Code Organization

The codebase follows consistent naming conventions:
- **Functions and variables**: `snake_case`
- **Classes**: `CamelCase`
- **Constants**: `ALL_CAPS_WITH_UNDERSCORES`
- **Files and modules**: `snake_case`

### Adding New Modules

1. **Create the module** in the appropriate directory (`utils/` or `tests/`)
2. **Update dependencies** in `system_design_architecture.yaml`
3. **Add configuration** to `platform_config.json` if needed
4. **Update imports** in dependent modules
5. **Add tests** to the appropriate test module

### AI Agent Integration

The system is designed for AI agent development:
- **Tagged and labeled** modules for automated analysis
- **Graph generation support** (DOT and UML formats)
- **Comprehensive documentation** in YAML format
- **Modular architecture** for easy navigation and modification

## 📊 System Parameters

### Physical Parameters
- **Ball radius**: 0.111 meters
- **Omniwheel radius**: 0.100 meters
- **Wheel separation**: 120° between wheels
- **Vertical offset**: -0.0555 meters
- **Horizontal offset**: 0.0555 meters

### Control Parameters
- **Sample time**: 0.01 seconds (100 Hz control loop)
- **Buffer duration**: 60.0 seconds
- **PID gains**: Kp=1.0, Ki=0.01, Kd=0.001

## 🔒 Safety Features

### Hardware Safety
- **E-Stop monitoring** - Real-time emergency stop status
- **Temperature monitoring** - Over-temperature protection
- **Current limiting** - Motor overload protection
- **Voltage monitoring** - Over/under voltage protection

### Software Safety
- **Error status checking** - Comprehensive error bit monitoring
- **Connection verification** - Robust connection testing
- **Settings validation** - Configuration validation before use
- **Backup protection** - Automatic settings backup

## 📁 Project Structure

```
CODE & Software/
├── test_platform_control/          # Main platform code
│   ├── platform_control.py         # Primary control interface
│   ├── config/                     # Configuration files
│   ├── utils/                      # Core utility modules
│   ├── tests/                      # Testing and calibration
│   └── test_logs/                  # Test results and logs
├── docs/                           # Documentation
│   ├── system_design_architecture.yaml
│   └── scripts/                    # Graph generation scripts
├── RoboClaw Software & CODE/       # RoboClaw library and examples
├── Current-Power_Monitor_HAT_Code/ # Power monitoring examples
├── Optical Flow Sensor/            # Optical flow sensor examples
└── CircuitPython/                  # Maker Pi experimental code
```

## 🤝 Contributing

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/amazing-feature`)
3. **Commit your changes** (`git commit -m 'Add amazing feature'`)
4. **Push to the branch** (`git push origin feature/amazing-feature`)
5. **Open a Pull Request**

### Development Guidelines

- Follow the established naming conventions
- Update documentation for any architectural changes
- Add tests for new functionality
- Ensure cross-platform compatibility
- Maintain safety-first design principles

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **VDL Robot Sports** - Project sponsor and technical guidance
- **Fontys University of Applied Sciences** - Academic support
- **RoboClaw** - Motor controller hardware and software
- **Pimoroni** - Optical flow sensor and Maker Pi hardware

## 📞 Support

For technical support or questions:
- **Issues**: Use the GitHub Issues page
- **Documentation**: Check the `docs/` directory
- **Configuration**: Review `platform_config.json` and `system_design_architecture.yaml`

## 🔄 Version History

- **v1.0** (2025-01-27) - Initial release with comprehensive testing suite
  - Complete motor control system
  - Optical flow sensor integration
  - Power monitoring capabilities
  - Modular testing architecture
  - AI agent development support

---

**Note**: This platform is designed for research and development purposes. Always follow safety protocols when working with motorized systems. 