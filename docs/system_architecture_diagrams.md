# System Architecture Diagrams

This document provides an overview of the system architecture diagrams generated for the Ball Rotation Control Platform. These diagrams are automatically generated from the `system_design_architecture.yaml` configuration file.

## Generated Diagrams

### DOT Format Diagrams (Graphviz)

The following diagrams are generated in DOT format and can be rendered using Graphviz:

#### 1. System Overview (`system_overview.dot` / `system_overview.png`)
- **Purpose**: High-level system architecture showing hardware and software components
- **Structure**: 
  - Hardware Components (Motor Controllers, Sensors, Experimental Modules)
  - Software Modules (Core, Sensor, Test modules)
  - Dependencies between components
- **Use Case**: System understanding, component overview, architecture review

#### 2. Module Dependencies (`module_dependencies.dot` / `module_dependencies.png`)
- **Purpose**: Detailed view of software module dependencies and relationships
- **Structure**:
  - All software modules organized by category
  - Dependency relationships between modules
  - Color-coded by module type (core, sensor, test, utility, experimental)
- **Use Case**: Code organization, dependency analysis, refactoring planning

#### 3. Data Flow (`data_flow.dot` / `data_flow.png`)
- **Purpose**: Shows how data flows through the system from sensors to actuators
- **Structure**:
  - Data Sources (sensors)
  - Processing Modules (kinematics, setpoints, logging)
  - Control System (motor interfaces)
  - Outputs (motors)
  - Feedback loops
- **Use Case**: Understanding system operation, debugging data flow issues

### UML Format Diagrams (Mermaid)

The following diagrams are generated in Mermaid format and can be viewed in HTML browsers:

#### 1. Class Diagram (`class_diagram.mmd` / `class_diagram.html`)
- **Purpose**: UML class diagram showing software module relationships
- **Structure**:
  - Core modules as classes with methods and attributes
  - Sensor modules with their features
  - Test modules with their capabilities
  - Hardware components as classes
  - Relationships and dependencies
- **Use Case**: Software design, object-oriented analysis, module interface design

#### 2. Sequence Diagram (`sequence_diagram.mmd` / `sequence_diagram.html`)
- **Purpose**: Shows the sequence of interactions during system operation
- **Structure**:
  - System initialization sequence
  - Control loop interactions
  - Communication between components
  - System shutdown sequence
- **Use Case**: Understanding system behavior, debugging timing issues, integration testing

#### 3. Component Diagram (`component_diagram.mmd` / `component_diagram.html`)
- **Purpose**: Shows system components and their interfaces
- **Structure**:
  - Hardware Layer (controllers, sensors, motors)
  - Software Layer (core, sensor, utility modules)
  - Testing Layer (test modules)
  - External Interfaces (configuration, logs, backup)
- **Use Case**: System integration, interface design, component deployment

#### 4. Deployment Diagram (`deployment_diagram.mmd` / `deployment_diagram.html`)
- **Purpose**: Shows how components are deployed across hardware nodes
- **Structure**:
  - Raspberry Pi 5 node with software components
  - Maker Pi RP2040 node with experimental modules
  - Hardware components (controllers, sensors, motors)
  - Storage components (configuration, logs, backup)
- **Use Case**: Hardware deployment planning, system architecture, network design

## How to Generate Diagrams

### Prerequisites
- Python 3.x
- PyYAML package (`pip install pyyaml`)
- Graphviz (for PNG generation): `sudo apt install graphviz`

### Generation Commands

```bash
# Generate DOT diagrams
cd docs/scripts
python3 generate_dot.py ../system_design_architecture.yaml [output_dir]

# Generate UML diagrams
python3 generate_uml.py ../system_design_architecture.yaml [output_dir]
```

### Output Files

#### DOT Generation Output:
- `system_overview.dot` - System overview in DOT format
- `module_dependencies.dot` - Module dependencies in DOT format
- `data_flow.dot` - Data flow diagram in DOT format
- `*.png` - Rendered PNG images (if Graphviz is installed)

#### UML Generation Output:
- `class_diagram.mmd` - Class diagram in Mermaid format
- `sequence_diagram.mmd` - Sequence diagram in Mermaid format
- `component_diagram.mmd` - Component diagram in Mermaid format
- `deployment_diagram.mmd` - Deployment diagram in Mermaid format
- `*.html` - HTML files with embedded Mermaid diagrams

## Viewing the Diagrams

### DOT Diagrams
- **DOT files**: Use any Graphviz-compatible viewer
- **PNG files**: View with any image viewer
- **Online**: Use [Graphviz Online](https://dreampuf.github.io/GraphvizOnline/)

### UML Diagrams
- **Mermaid files**: Use [Mermaid Live Editor](https://mermaid.live/)
- **HTML files**: Open in any web browser
- **GitHub**: Mermaid diagrams render automatically in GitHub markdown

## Diagram Customization

### Modifying the YAML Structure
The diagrams are generated from the `system_design_architecture.yaml` file. To modify the diagrams:

1. **Add new modules**: Add entries to the appropriate section in the YAML file
2. **Modify dependencies**: Update the `dependencies` lists in module definitions
3. **Add hardware components**: Update the `hardware` section
4. **Change descriptions**: Modify the `description` fields

### Customizing Diagram Styles
- **DOT diagrams**: Modify the `generate_*.dot()` functions in `generate_dot.py`
- **UML diagrams**: Modify the `generate_*.diagram()` functions in `generate_uml.py`

## System Architecture Overview

The Ball Rotation Control Platform consists of:

### Hardware Components
- **RoboClaw Controllers**: Motor control (2x30A controllers)
- **Motors**: Maxon DCX35L motors with encoders
- **Sensors**: 
  - Optical Flow Sensor (PAA5100JE-Q) for ball tracking
  - Power Sensor (INA219) for current monitoring
- **Experimental Modules**: Maker Pi RP2040 for experimental features

### Software Components
- **Core Modules**: Platform control, kinematics, setpoint generation
- **Sensor Modules**: Optical flow and power sensor interfaces
- **Utility Modules**: Data logging, autopilot management, test utilities
- **Test Modules**: Comprehensive testing suite for all components

### Key Features
- **Modular Design**: Clear separation of concerns
- **Hardware Abstraction**: Platform-independent interfaces
- **Comprehensive Testing**: Automated test suite for all components
- **Real-time Control**: Low-latency motor control and sensor feedback
- **Data Logging**: Comprehensive logging and analysis capabilities

## Maintenance

### Updating Diagrams
1. Modify the `system_design_architecture.yaml` file
2. Run the generation scripts
3. Commit the updated diagrams to version control
4. Update this documentation if needed

### Version Control
- All generated diagrams should be committed to version control
- Diagrams are automatically generated, so the YAML file is the source of truth
- Include both source files (`.dot`, `.mmd`) and rendered images (`.png`, `.html`)

## Troubleshooting

### Common Issues
1. **Missing PyYAML**: `pip install pyyaml`
2. **Missing Graphviz**: `sudo apt install graphviz`
3. **YAML parsing errors**: Check YAML syntax in the architecture file
4. **Missing dependencies**: Ensure all required Python packages are installed

### Debugging
- Check the script output for error messages
- Verify the YAML file structure matches the expected format
- Test with a minimal YAML file to isolate issues

## Future Enhancements

### Planned Improvements
1. **Interactive Diagrams**: Add clickable elements to HTML diagrams
2. **Real-time Updates**: Auto-regenerate diagrams when YAML changes
3. **Additional Diagram Types**: Add state diagrams, activity diagrams
4. **Export Formats**: Support for SVG, PDF, and other formats
5. **Web Interface**: Web-based diagram generation and viewing

### Integration Ideas
1. **CI/CD Integration**: Auto-generate diagrams in build pipeline
2. **Documentation Integration**: Embed diagrams in documentation
3. **Code Analysis**: Generate diagrams from actual code structure
4. **Live Monitoring**: Real-time system state visualization

---

*Generated on: 2025-07-02 19:22:55*
*Source: system_design_architecture.yaml*
*Scripts: generate_dot.py, generate_uml.py* 