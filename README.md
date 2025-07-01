# Ball Rotation Control Platform

A comprehensive hardware control system for autonomous ball rotation control using Raspberry Pi 5, RoboClaw motor controllers, optical flow sensors, and power monitoring.

## 🎉 Major Milestone Achieved

**First Autonomous Motor Control**: RoboClaw controllers successfully spun motors for the first time through autonomous testing, demonstrating the power of systematic troubleshooting and modular architecture.

## 🏗️ System Architecture

### Hardware Components
- **Raspberry Pi 5** - Core control system running Ubuntu 24.04 LTS
- **RoboClaw 2x30A Motor Controllers** - Dual motor control with encoder feedback
- **PAA5100JE-Q Optical Flow Sensor** - Ball position and velocity tracking
- **INA219 Power Sensors** - Real-time current and voltage monitoring (4 channels)
- **Maker Pi RP2040** - Experimental modules and additional sensors

### Software Architecture
- **Modular Test Suite** - 6 dedicated test modules for each hardware component
- **Autonomous Execution** - Intelligent autopilot system for hands-free testing
- **Hardware Abstraction** - Clean separation between hardware interfaces and operational code
- **Comprehensive Logging** - Detailed test results and system performance tracking

## 🚀 Quick Start

### Prerequisites
- Raspberry Pi 5 with Ubuntu 24.04 LTS
- Python 3.12.3 or higher
- Hardware components listed above

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/Ball-Rotation-Control-Platform.git
   cd Ball-Rotation-Control-Platform
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure hardware**
   - Connect RoboClaw controllers to USB ports
   - Connect INA219 sensors to I2C bus
   - Connect PAA5100JE-Q sensor to SPI bus
   - Connect Maker Pi RP2040 to USB

### Basic Usage

1. **Run connectivity test**
   ```bash
   python platform_control/tests/connectivity_test.py --dev --save --autopilot "1"
   ```

2. **Test motor controllers**
   ```bash
   python platform_control/tests/roboclaw_test.py --dev --save --autopilot "123"
   ```

3. **Test power sensors**
   ```bash
   python platform_control/tests/ina219_test_menu.py --dev --save --autopilot "1234"
   ```

4. **Run complete system test**
   ```bash
   python platform_control/tests/system_test.py --dev --save --autopilot "123456"
   ```

## 📁 Project Structure

```
Ball-Rotation-Control-Platform/
├── platform_control/           # Main control system
│   ├── tests/                 # Hardware-specific test modules
│   │   ├── connectivity_test.py
│   │   ├── roboclaw_test.py
│   │   ├── ina219_test_menu.py
│   │   ├── optical_flow_test_menu.py
│   │   ├── maker_pi_tests.py
│   │   ├── calibration_tests.py
│   │   ├── performance_test.py
│   │   ├── code_integration_test.py
│   │   └── system_test.py
│   ├── utils/                 # Hardware and functional utilities
│   │   ├── roboclaw_interface.py
│   │   ├── power_sensor.py
│   │   ├── optical_flow_sensor.py
│   │   ├── maker_pi_interface.py
│   │   ├── kinematic_conversion.py
│   │   ├── data_logger.py
│   │   └── autopilot_manager.py
│   ├── config/               # Configuration files
│   │   └── platform_config.json
│   └── platform_control.py   # Main operational system
├── examples/                 # Example code by component
├── roboclaw_python/         # Local RoboClaw library
├── docs/                    # Documentation and architecture
└── test_logs/              # Test results and performance data
```

## 🔧 Hardware Setup

### RoboClaw Motor Controllers
- **Ports**: `/dev/ttyACM0`, `/dev/ttyACM1`
- **Features**: Motor identification, e-stop cycling, LED monitoring
- **Status**: ✅ Autonomous motor spinning achieved

### INA219 Power Sensors
- **Bus**: I2C (busnum=1)
- **Features**: Voltage measurement (10-26V), current mapping
- **Status**: ✅ Power monitoring confirmed working

### PAA5100JE-Q Optical Flow Sensor
- **Interface**: SPI
- **Features**: LED control, motion detection
- **Status**: ✅ Sensor naming and communication validated

### Maker Pi RP2040
- **Interface**: USB (CIRCUITPY drive)
- **Features**: Experimental modules, UART communication
- **Status**: ✅ USB detection and UART integration working

## 🧪 Testing Framework

### Autonomous Testing
All test modules support autonomous execution with intelligent autopilot:
- **--dev**: Development mode with enhanced troubleshooting
- **--save**: Save results to test_logs directory
- **--autopilot**: Automated menu navigation

### Test Modules
1. **Connectivity Test** - System-wide hardware detection
2. **RoboClaw Test** - Motor control and identification
3. **INA219 Test** - Power monitoring and current mapping
4. **Optical Flow Test** - Motion detection and LED control
5. **Maker Pi Test** - Experimental module testing
6. **Calibration Test** - System calibration and characterization
7. **Performance Test** - System performance analysis
8. **Code Integration Test** - Code integrity validation

## 📊 Performance Metrics

### System Statistics
- **Total Test Files**: 6 modules (58% reduction from original 12 files)
- **Total Lines**: ~3,630 lines (58% reduction from 8,623 lines)
- **System Test**: 375 lines (90% reduction from 3,739 lines)
- **Modularization**: 100% complete

### Hardware Performance
- **RoboClaw Response**: Autonomous motor control achieved
- **INA219 Accuracy**: Voltage and current monitoring confirmed
- **Optical Flow**: Motion detection and LED control functional
- **Maker Pi**: USB detection and UART communication working

## 🔍 Troubleshooting

### Common Issues

1. **RoboClaw Connection Issues**
   - Check USB ports: `/dev/ttyACM0`, `/dev/ttyACM1`
   - Verify power supply and connections
   - Check error lights for fault conditions

2. **INA219 I2C Issues**
   - Verify I2C bus detection: `i2cdetect -y 1`
   - Check sensor addresses and connections
   - Ensure proper power supply

3. **Optical Flow Sensor Issues**
   - Verify SPI interface configuration
   - Check LED control functionality
   - Test motion detection with manual movement

4. **Maker Pi Detection Issues**
   - Check USB connection and CIRCUITPY drive
   - Verify CircuitPython installation
   - Test UART communication

### Error Recovery
- **Automatic Retry**: Tests automatically retry failed operations
- **Error Logging**: Comprehensive error logging with context
- **Fallback Mechanisms**: Multiple communication methods for reliability

## 📚 Documentation

### Key Documents
- **System Architecture**: `docs/system_design_architecture.yaml`
- **Hardware Setup**: `hardware-and-library-setup.md`
- **Development Rules**: `.cursor/rules/`
- **Configuration**: `platform_control/config/platform_config.json`

### Development Workflow
- **To-Do List**: `to-do.md` - Current development tasks
- **To-Verify List**: `to-verify.md` - Items requiring validation
- **Change Log**: `change-log.md` - Completed changes and milestones

## 🤝 Contributing

### Development Guidelines
1. Follow the modular architecture principles
2. Use autonomous testing for validation
3. Update documentation for all changes
4. Maintain hardware abstraction layers
5. Follow the established coding standards

### Testing Protocol
1. Run connectivity tests first
2. Test individual hardware modules
3. Validate system integration
4. Document any issues or improvements

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **RoboClaw**: Basic Micro for motor controller technology
- **Adafruit**: CircuitPython libraries and hardware support
- **Raspberry Pi Foundation**: Platform and community support
- **Open Source Community**: Libraries and tools that made this possible

## 📞 Support

For issues, questions, or contributions:
- Check the troubleshooting section above
- Review the test logs in `test_logs/` directory
- Examine the configuration in `platform_control/config/`
- Consult the system architecture documentation

---

**Status**: Ready for comprehensive testing and validation with working RoboClaw connectivity and autonomous motor control achieved.
