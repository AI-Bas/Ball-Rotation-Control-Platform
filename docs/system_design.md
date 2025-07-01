# Ball Rotation Control Platform - System Design

## 📋 PURPOSE
**Data formats, conventions, and development workflow** for AI agent reference.
**NOT the single source of truth** - see `system_design_architecture.yaml` for implementation details.

## 🏗️ DATA FORMATS AND CONVENTIONS

### File Extensions
- **.mdc**: Cursor-specific rule files for AI agent behavior
- **.md**: Standard Markdown documentation files
- **.py**: Python implementation files
- **.json**: Configuration and data files
- **.yaml**: Architecture and configuration files

### Documentation Structure
- **system_design_architecture.yaml**: Implementation details and dependencies (single source of truth)
- **platform_config.json**: Central configuration values
- **README.md**: User documentation and quick reference
- **to-do.md**: Development task tracking
- **to-verify.md**: Completed items awaiting validation
- **change-log.md**: Completed changes and updates

### Status Indicators
- **✅ COMPLETED**: Task finished successfully
- **🔄 IN PROGRESS**: Currently being worked on
- **⚠️ PENDING**: Waiting to be started
- **❌ FAILED**: Task failed and needs attention

### Priority Levels
- **🔴 CRITICAL**: Must be completed immediately
- **🟡 MEDIUM**: Important but not urgent
- **🟢 LOW**: Nice to have, can be deferred

## 🔧 DEVELOPMENT WORKFLOW

### Testing Phase
1. **Hardware Verification**: Check all connections and sensors
2. **Motor Identification**: Interactive motor assignment
3. **System Calibration**: Tune control parameters
4. **Performance Testing**: Validate system capabilities

### Development Phase
1. **Code Editing**: Direct access to Python files
2. **Pattern Matching**: AI cursor agent code analysis
3. **Platform Integration**: Maintain hardware separation
4. **Documentation**: Keep all files updated

### Deployment Phase
1. **Configuration**: Update platform_config.json
2. **Validation**: Run comprehensive test suite
3. **Documentation**: Update design and architecture files
4. **Maintenance**: Monitor system performance and logs

## 📁 FOLDER ORGANIZATION

```
Ball-Rotation-Control-Platform/
├── test_platform_control/
│   ├── tests/           # Hardware-specific test modules
│   ├── utils/           # Hardware and functional utilities
│   └── config/          # Configuration files
├── examples/            # Example code by component
├── roboclaw_python/     # Local RoboClaw library
└── docs/               # Documentation and architecture
```

## 🧪 TESTING CONVENTIONS

### Test Module Structure
- **connectivity_test.py**: System-wide connection scan
- **roboclaw_test_menu.py**: Motor controller testing
- **ina219_test_menu.py**: Power sensor testing
- **optical_flow_test_menu.py**: Motion sensor testing
- **maker_pi_tests.py**: Experimental module testing
- **calibration_tests.py**: System calibration
- **characterization_tests.py**: Performance analysis
- **system_test.py**: Test orchestration

### Test Execution Commands
```bash
# Individual test modules with autonomous execution
python test_platform_control/tests/[module_name].py --dev --save --autopilot "[input_string]"

# Central test orchestration
python test_platform_control/tests/system_test.py --dev --autopilot "123456"
```

### Development Mode Features
- Enhanced troubleshooting and error messages
- Detailed logging and result saving
- Autonomous execution with input strings
- Performance monitoring and bandwidth testing

## 🔧 HARDWARE RESPONSIBILITIES

### Raspberry Pi 5 (Core Motion Control)
- RoboClaw 2x30A motor controllers
- Optical flow sensor (PAA5100JE-Q)
- Power monitoring (INA219)
- Encoder feedback processing
- Motion control loop execution

### Maker Pi RP2040 (Experimental Modules)
- Experimental sensors (MicroPython)
- Display modules
- IO modules
- Future functionality expansion
- **Note**: Does NOT handle core motion control sensors

## 📚 LIBRARY MANAGEMENT

### Preferred Packages (PIP FIRST)
- **pmw3901>=1.0.0** - Optical flow sensor
- **ina219>=1.4.1** - Current sensor
- **gpiod>=2.0.0** - GPIO library
- **gpiodevice>=0.1.0** - GPIO device library
- **pyserial>=3.5** - Serial communication
- **smbus2>=0.5.0** - I2C communication
- **spidev>=3.7** - SPI communication
- **RPi.GPIO>=0.7.1** - Raspberry Pi GPIO control

### Local Libraries (Retained)
- **roboclaw_python/roboclaw_3.py** - RoboClaw motor controller interface

### Removed Libraries
- **Optical Flow Sensor/pmw3901-python-main/** - Replaced by pip package
- **Current-Power_Monitor_HAT_Code/RaspberryPi/ina219.py** - Replaced by pip package
- **roboclaw_python/roboclaw.py** - Replaced by roboclaw_3.py

## 🔄 COMMUNICATION PROTOCOLS

### USB Mode
- **Protocol**: USB virtual COM port
- **Addresses**: 0x80 for both controllers
- **Automatic Handling**: No baud rate configuration needed

### RS232 Mode
- **Protocol**: RS232 serial communication
- **Baud Rates**: [460800, 38400, 115200, 57600, 9600]
- **Addresses**: 0x80 for both controllers
- **Timeout**: 0.01 seconds
- **Retries**: 3

### I2C Communication
- **Power Sensors**: Addresses 0x40-0x43
- **Library**: smbus2 for I2C communication

### SPI Communication
- **Optical Flow Sensor**: Bus 0, device 0
- **Library**: spidev for SPI communication

### UART Communication
- **Maker Pi RP2040**: 115200 baud
- **Format**: JSON over UART

## ⚠️ ERROR HANDLING

### Connection Issues
- USB fallback to RS232 if needed
- Automatic baud rate testing
- Hardware context assignment
- Comprehensive error logging

### Test Execution
- Result capture and logging
- Error propagation and reporting
- Configuration validation
- Test result aggregation

## 📊 CONFIGURATION MANAGEMENT

### Platform Configuration
- **File**: `test_platform_control/config/platform_config.json`
- **Purpose**: Central configuration for all system parameters
- **Sections**: system_parameters, hardware, motor_defaults, testing

### Test Results
- **Directory**: `test_platform_control/tests/test_logs/`
- **Format**: JSON with timestamps
- **Files**: Various test result files with timestamps

### Settings Backup
- **Directory**: `test_platform_control/tests/roboclaw_settings_backup/`
- **Purpose**: RoboClaw settings backup and comparison
- **Files**: Timestamped settings snapshots

## 🎯 DEVELOPMENT PRINCIPLES

### Code Quality
- **Modular Design**: Maintain separate utilities for specific functions
- **Error Handling**: Comprehensive error catching and logging
- **Configuration**: Centralized configuration management
- **Testing**: Comprehensive testing with incremental validation

### Documentation Standards
- **Synchronization**: Keep all documentation synchronized
- **Change Tracking**: Document all changes and reasons
- **Version Control**: Maintain clear version tracking
- **Maintenance**: Regular documentation review and updates

### Best Practices
- **PIP FIRST**: Always check for pip packages before using local libraries
- **Testing**: Comprehensive testing before library changes
- **Documentation**: Update all relevant documentation
- **Configuration**: Keep platform_config.json synchronized
- **Validation**: Verify all hardware interfaces work correctly

## 🔍 TROUBLESHOOTING

### Common Issues
1. **PowerShell Command Errors**: Use VS Code tasks
2. **Connection Failures**: Check USB ports and try RS232 fallback
3. **Motor Identification**: Use interactive motor assignment
4. **Hardware Detection**: Verify all connections and drivers

### Support Resources
- Test logs: `test_platform_control/tests/test_logs/`
- Settings backup: `test_platform_control/tests/roboclaw_settings_backup/`
- Configuration: `test_platform_control/config/platform_config.json`
- Documentation: `docs/` directory

## 📋 REFERENCE INFORMATION

### For Implementation Details
- **Hardware Architecture**: See `system_design_architecture.yaml`
- **Software Modules**: See `system_design_architecture.yaml`
- **Dependencies**: See `system_design_architecture.yaml`
- **Configuration**: See `platform_config.json`

### For Development Context
- **Formats and Conventions**: This document
- **Workflow Procedures**: This document
- **Testing Protocols**: This document
- **Library Management**: This document

**This document provides non-technical context and conventions. For implementation details, always refer to system_design_architecture.yaml.** 