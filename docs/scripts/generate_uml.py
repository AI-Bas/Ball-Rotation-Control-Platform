#!/usr/bin/env python3
"""
UML Diagram Generator for Ball Rotation Control Platform
Generates comprehensive UML diagrams from YAML configuration
"""

import yaml
import sys
import os
from typing import Dict, Any, List, Set

def load_yaml(path: str) -> Dict[str, Any]:
    """Load YAML system architecture file"""
    try:
        with open(path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading YAML file: {e}")
        sys.exit(1)

def sanitize_name(name: str) -> str:
    """Sanitize names for UML format"""
    return name.replace(' ', '_').replace('-', '_').replace('.', '_').replace('/', '_')

def generate_class_diagram(yaml_data: Dict[str, Any]) -> str:
    """Generate UML class diagram"""
    mermaid_content = []
    mermaid_content.append('classDiagram')
    mermaid_content.append('')
    
    software = yaml_data.get('software', {})
    
    # Core modules as classes
    if 'core_modules' in software:
        mermaid_content.append('    %% Core Modules')
        core_modules = software['core_modules']
        for module_name, module_info in core_modules.items():
            if isinstance(module_info, dict):
                sanitized_name = sanitize_name(module_name)
                description = module_info.get('description', '')
                features = module_info.get('features', [])
                key_methods = module_info.get('key_methods', [])
                
                mermaid_content.append(f'    class {sanitized_name} {{')
                mermaid_content.append(f'        <<Core Module>>')
                mermaid_content.append(f'        +description: {description}')
                if features:
                    mermaid_content.append(f'        +features: {", ".join(features[:3])}')
                if key_methods:
                    for method in key_methods[:3]:
                        mermaid_content.append(f'        +{method}()')
                mermaid_content.append('    }')
                mermaid_content.append('')
    
    # Sensor modules as classes
    if 'sensor_modules' in software:
        mermaid_content.append('    %% Sensor Modules')
        sensor_modules = software['sensor_modules']
        for module_name, module_info in sensor_modules.items():
            if isinstance(module_info, dict):
                sanitized_name = sanitize_name(module_name)
                description = module_info.get('description', '')
                features = module_info.get('features', [])
                
                mermaid_content.append(f'    class {sanitized_name} {{')
                mermaid_content.append(f'        <<Sensor Module>>')
                mermaid_content.append(f'        +description: {description}')
                if features:
                    mermaid_content.append(f'        +features: {", ".join(features[:3])}')
                mermaid_content.append('    }')
                mermaid_content.append('')
    
    # Test modules as classes
    if 'test_modules' in software:
        mermaid_content.append('    %% Test Modules')
        test_modules = software['test_modules']
        for module_name, module_info in test_modules.items():
            if isinstance(module_info, dict):
                sanitized_name = sanitize_name(module_name)
                description = module_info.get('description', '')
                features = module_info.get('features', [])
                
                mermaid_content.append(f'    class {sanitized_name} {{')
                mermaid_content.append(f'        <<Test Module>>')
                mermaid_content.append(f'        +description: {description}')
                if features:
                    mermaid_content.append(f'        +features: {", ".join(features[:3])}')
                mermaid_content.append('    }')
                mermaid_content.append('')
    
    # Hardware components as classes
    hardware = yaml_data.get('hardware', {})
    if 'motor_controllers' in hardware:
        mermaid_content.append('    %% Hardware Components')
        controllers = hardware['motor_controllers'].get('controllers', {})
        for name, controller in controllers.items():
            sanitized_name = sanitize_name(name)
            mermaid_content.append(f'    class {sanitized_name} {{')
            mermaid_content.append(f'        <<Hardware>>')
            mermaid_content.append(f'        +port: {controller.get("port", "")}')
            mermaid_content.append(f'        +address: {controller.get("address", "")}')
            mermaid_content.append('    }')
            mermaid_content.append('')
    
    # Relationships
    mermaid_content.append('    %% Relationships')
    
    # Dependencies
    if 'core_modules' in software:
        core_modules = software['core_modules']
        for module_name, module_info in core_modules.items():
            if isinstance(module_info, dict):
                dependencies = module_info.get('dependencies', [])
                module_sanitized = sanitize_name(module_name)
                
                for dep in dependencies:
                    dep_sanitized = sanitize_name(dep)
                    # Check if dependency exists as a module
                    if any(dep_sanitized == sanitize_name(name) for name in 
                           list(software.get('core_modules', {}).keys()) +
                           list(software.get('sensor_modules', {}).keys()) +
                           list(software.get('test_modules', {}).keys())):
                        mermaid_content.append(f'    {module_sanitized} --> {dep_sanitized} : depends on')
    
    # Hardware to software relationships
    if 'hardware_responsibilities' in hardware:
        responsibilities = hardware['hardware_responsibilities']
        for hw_name, hw_info in responsibilities.items():
            if isinstance(hw_info, dict):
                hw_sanitized = sanitize_name(hw_name)
                responsibilities_list = hw_info.get('responsibilities', [])
                
                for resp in responsibilities_list:
                    if 'roboclaw' in resp.lower():
                        mermaid_content.append(f'    {hw_sanitized} --> roboclaw_interface : controls')
                    elif 'optical' in resp.lower():
                        mermaid_content.append(f'    {hw_sanitized} --> optical_flow_sensor : senses')
                    elif 'power' in resp.lower():
                        mermaid_content.append(f'    {hw_sanitized} --> power_sensor : monitors')
    
    return '\n'.join(mermaid_content)

def generate_sequence_diagram(yaml_data: Dict[str, Any]) -> str:
    """Generate UML sequence diagram for system operation"""
    mermaid_content = []
    mermaid_content.append('sequenceDiagram')
    mermaid_content.append('    participant User as User')
    mermaid_content.append('    participant PC as Platform Control')
    mermaid_content.append('    participant KI as Kinematic Conversion')
    mermaid_content.append('    participant SG as Setpoint Generator')
    mermaid_content.append('    participant RC as RoboClaw Interface')
    mermaid_content.append('    participant OF as Optical Flow Sensor')
    mermaid_content.append('    participant PS as Power Sensor')
    mermaid_content.append('    participant M1 as Motor 1')
    mermaid_content.append('    participant M2 as Motor 2')
    mermaid_content.append('    participant M3 as Motor 3')
    mermaid_content.append('')
    
    mermaid_content.append('    %% System Initialization')
    mermaid_content.append('    User->>PC: Start System')
    mermaid_content.append('    PC->>RC: Initialize RoboClaw')
    mermaid_content.append('    PC->>OF: Initialize Optical Flow')
    mermaid_content.append('    PC->>PS: Initialize Power Sensor')
    mermaid_content.append('    RC-->>PC: Connection Status')
    mermaid_content.append('    OF-->>PC: Sensor Ready')
    mermaid_content.append('    PS-->>PC: Sensor Ready')
    mermaid_content.append('')
    
    mermaid_content.append('    %% Control Loop')
    mermaid_content.append('    loop Control Loop')
    mermaid_content.append('        OF->>PC: Ball Position/Velocity')
    mermaid_content.append('        PS->>PC: Current/Voltage Data')
    mermaid_content.append('        RC->>PC: Encoder Feedback')
    mermaid_content.append('        PC->>KI: Calculate Kinematics')
    mermaid_content.append('        KI-->>PC: Wheel Velocities')
    mermaid_content.append('        PC->>SG: Generate Setpoints')
    mermaid_content.append('        SG-->>PC: Motor Commands')
    mermaid_content.append('        PC->>RC: Set Motor Velocities')
    mermaid_content.append('        RC->>M1: Set Velocity')
    mermaid_content.append('        RC->>M2: Set Velocity')
    mermaid_content.append('        RC->>M3: Set Velocity')
    mermaid_content.append('        M1-->>RC: Encoder Feedback')
    mermaid_content.append('        M2-->>RC: Encoder Feedback')
    mermaid_content.append('        M3-->>RC: Encoder Feedback')
    mermaid_content.append('    end')
    mermaid_content.append('')
    
    mermaid_content.append('    %% System Shutdown')
    mermaid_content.append('    User->>PC: Stop System')
    mermaid_content.append('    PC->>RC: Stop All Motors')
    mermaid_content.append('    RC->>M1: Stop')
    mermaid_content.append('    RC->>M2: Stop')
    mermaid_content.append('    RC->>M3: Stop')
    mermaid_content.append('    PC-->>User: System Stopped')
    
    return '\n'.join(mermaid_content)

def generate_component_diagram(yaml_data: Dict[str, Any]) -> str:
    """Generate UML component diagram"""
    mermaid_content = []
    mermaid_content.append('graph TB')
    mermaid_content.append('')
    
    # System boundary
    mermaid_content.append('    subgraph System["Ball Rotation Control Platform"]')
    mermaid_content.append('')
    
    # Hardware components
    mermaid_content.append('        subgraph Hardware["Hardware Layer"]')
    mermaid_content.append('            RC1[RoboClaw Controller 1]')
    mermaid_content.append('            RC2[RoboClaw Controller 2]')
    mermaid_content.append('            OF[Optical Flow Sensor]')
    mermaid_content.append('            PS[Power Sensor]')
    mermaid_content.append('            M1[Motor 1]')
    mermaid_content.append('            M2[Motor 2]')
    mermaid_content.append('            M3[Motor 3]')
    mermaid_content.append('            MP[Maker Pi RP2040]')
    mermaid_content.append('        end')
    mermaid_content.append('')
    
    # Software components
    mermaid_content.append('        subgraph Software["Software Layer"]')
    mermaid_content.append('            PC[Platform Control]')
    mermaid_content.append('            KI[Kinematic Conversion]')
    mermaid_content.append('            SG[Setpoint Generator]')
    mermaid_content.append('            RI[RoboClaw Interface]')
    mermaid_content.append('            OFI[Optical Flow Interface]')
    mermaid_content.append('            PSI[Power Sensor Interface]')
    mermaid_content.append('            DL[Data Logger]')
    mermaid_content.append('            AM[Autopilot Manager]')
    mermaid_content.append('        end')
    mermaid_content.append('')
    
    # Test components
    mermaid_content.append('        subgraph Testing["Testing Layer"]')
    mermaid_content.append('            ST[System Test]')
    mermaid_content.append('            CT[Connectivity Test]')
    mermaid_content.append('            RT[RoboClaw Test]')
    mermaid_content.append('            CLT[Calibration Test]')
    mermaid_content.append('            PT[Performance Test]')
    mermaid_content.append('        end')
    mermaid_content.append('')
    
    # External interfaces
    mermaid_content.append('        subgraph External["External Interfaces"]')
    mermaid_content.append('            Config[Configuration Files]')
    mermaid_content.append('            Logs[Test Logs]')
    mermaid_content.append('            Backup[Settings Backup]')
    mermaid_content.append('        end')
    mermaid_content.append('    end')
    mermaid_content.append('')
    
    # Connections
    mermaid_content.append('    %% Hardware connections')
    mermaid_content.append('    RC1 --> M1')
    mermaid_content.append('    RC1 --> M2')
    mermaid_content.append('    RC2 --> M3')
    mermaid_content.append('')
    
    mermaid_content.append('    %% Software to hardware')
    mermaid_content.append('    RI --> RC1')
    mermaid_content.append('    RI --> RC2')
    mermaid_content.append('    OFI --> OF')
    mermaid_content.append('    PSI --> PS')
    mermaid_content.append('')
    
    mermaid_content.append('    %% Software internal')
    mermaid_content.append('    PC --> RI')
    mermaid_content.append('    PC --> KI')
    mermaid_content.append('    PC --> SG')
    mermaid_content.append('    PC --> OFI')
    mermaid_content.append('    PC --> PSI')
    mermaid_content.append('    PC --> DL')
    mermaid_content.append('    PC --> AM')
    mermaid_content.append('')
    
    mermaid_content.append('    %% Testing connections')
    mermaid_content.append('    ST --> CT')
    mermaid_content.append('    ST --> RT')
    mermaid_content.append('    ST --> CLT')
    mermaid_content.append('    ST --> PT')
    mermaid_content.append('')
    
    mermaid_content.append('    %% External connections')
    mermaid_content.append('    PC --> Config')
    mermaid_content.append('    DL --> Logs')
    mermaid_content.append('    RT --> Backup')
    
    return '\n'.join(mermaid_content)

def generate_deployment_diagram(yaml_data: Dict[str, Any]) -> str:
    """Generate UML deployment diagram"""
    mermaid_content = []
    mermaid_content.append('graph TB')
    mermaid_content.append('')
    
    # Raspberry Pi 5 node
    mermaid_content.append('    subgraph RPi5["Raspberry Pi 5"]')
    mermaid_content.append('        subgraph RPi5_Software["Software Components"]')
    mermaid_content.append('            PC[Platform Control]')
    mermaid_content.append('            KI[Kinematic Conversion]')
    mermaid_content.append('            SG[Setpoint Generator]')
    mermaid_content.append('            RI[RoboClaw Interface]')
    mermaid_content.append('            OFI[Optical Flow Interface]')
    mermaid_content.append('            PSI[Power Sensor Interface]')
    mermaid_content.append('            DL[Data Logger]')
    mermaid_content.append('            AM[Autopilot Manager]')
    mermaid_content.append('        end')
    mermaid_content.append('')
    mermaid_content.append('        subgraph RPi5_Testing["Testing Components"]')
    mermaid_content.append('            ST[System Test]')
    mermaid_content.append('            CT[Connectivity Test]')
    mermaid_content.append('            RT[RoboClaw Test]')
    mermaid_content.append('            CLT[Calibration Test]')
    mermaid_content.append('            PT[Performance Test]')
    mermaid_content.append('        end')
    mermaid_content.append('    end')
    mermaid_content.append('')
    
    # Maker Pi RP2040 node
    mermaid_content.append('    subgraph MP2040["Maker Pi RP2040"]')
    mermaid_content.append('        subgraph MP2040_Software["Experimental Software"]')
    mermaid_content.append('            MPI[Maker Pi Interface]')
    mermaid_content.append('            ES[Experimental Sensors]')
    mermaid_content.append('            DM[Display Modules]')
    mermaid_content.append('            IOM[IO Modules]')
    mermaid_content.append('        end')
    mermaid_content.append('    end')
    mermaid_content.append('')
    
    # Hardware nodes
    mermaid_content.append('    subgraph Hardware["Hardware Components"]')
    mermaid_content.append('        RC1[RoboClaw Controller 1]')
    mermaid_content.append('        RC2[RoboClaw Controller 2]')
    mermaid_content.append('        OF[Optical Flow Sensor]')
    mermaid_content.append('        PS[Power Sensor]')
    mermaid_content.append('        M1[Motor 1]')
    mermaid_content.append('        M2[Motor 2]')
    mermaid_content.append('        M3[Motor 3]')
    mermaid_content.append('    end')
    mermaid_content.append('')
    
    # Storage node
    mermaid_content.append('    subgraph Storage["Storage"]')
    mermaid_content.append('        Config[Configuration Files]')
    mermaid_content.append('        Logs[Test Logs]')
    mermaid_content.append('        Backup[Settings Backup]')
    mermaid_content.append('    end')
    mermaid_content.append('')
    
    # Connections
    mermaid_content.append('    %% Raspberry Pi to Hardware')
    mermaid_content.append('    RI -.-> RC1 : USB/RS232')
    mermaid_content.append('    RI -.-> RC2 : USB/RS232')
    mermaid_content.append('    OFI -.-> OF : SPI')
    mermaid_content.append('    PSI -.-> PS : I2C')
    mermaid_content.append('')
    
    mermaid_content.append('    %% Hardware to Motors')
    mermaid_content.append('    RC1 -.-> M1 : Motor Control')
    mermaid_content.append('    RC1 -.-> M2 : Motor Control')
    mermaid_content.append('    RC2 -.-> M3 : Motor Control')
    mermaid_content.append('')
    
    mermaid_content.append('    %% Raspberry Pi to Maker Pi')
    mermaid_content.append('    PC -.-> MPI : USB/UART')
    mermaid_content.append('')
    
    mermaid_content.append('    %% Storage connections')
    mermaid_content.append('    PC -.-> Config : File I/O')
    mermaid_content.append('    DL -.-> Logs : File I/O')
    mermaid_content.append('    RT -.-> Backup : File I/O')
    
    return '\n'.join(mermaid_content)

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python3 generate_uml.py <yaml_file> [output_dir]")
        sys.exit(1)
    
    yaml_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else '.'
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Load YAML data
    data = load_yaml(yaml_path)
    
    # Generate different types of UML diagrams
    diagrams = {
        'class_diagram': generate_class_diagram(data),
        'sequence_diagram': generate_sequence_diagram(data),
        'component_diagram': generate_component_diagram(data),
        'deployment_diagram': generate_deployment_diagram(data)
    }
    
    # Write Mermaid files
    for diagram_name, mermaid_content in diagrams.items():
        output_file = os.path.join(output_dir, f'{diagram_name}.mmd')
        with open(output_file, 'w') as f:
            f.write(mermaid_content)
        print(f"Generated {output_file}")
    
    # Generate HTML files with embedded Mermaid
    for diagram_name in diagrams.keys():
        mmd_file = os.path.join(output_dir, f'{diagram_name}.mmd')
        html_file = os.path.join(output_dir, f'{diagram_name}.html')
        
        with open(mmd_file, 'r') as f:
            mermaid_content = f.read()
        
        html_content = f'''<!DOCTYPE html>
<html>
<head>
    <title>{diagram_name.replace('_', ' ').title()}</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <script>
        mermaid.initialize({{ startOnLoad: true }});
    </script>
</head>
<body>
    <h1>{diagram_name.replace('_', ' ').title()}</h1>
    <div class="mermaid">
{mermaid_content}
    </div>
</body>
</html>'''
        
        with open(html_file, 'w') as f:
            f.write(html_content)
        print(f"Generated {html_file}")

if __name__ == "__main__":
    main() 