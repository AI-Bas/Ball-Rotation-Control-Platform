#!/usr/bin/env python3
"""
DOT Graph Generator for Ball Rotation Control Platform
Generates comprehensive system architecture diagrams from YAML configuration
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
    """Sanitize names for DOT format"""
    return name.replace(' ', '_').replace('-', '_').replace('.', '_').replace('/', '_')

def generate_system_overview_dot(yaml_data: Dict[str, Any]) -> str:
    """Generate system overview diagram"""
    dot_content = []
    dot_content.append('digraph SystemOverview {')
    dot_content.append('  rankdir=TB;')
    dot_content.append('  node [shape=box, style=filled, fontname="Arial", fontsize=10];')
    dot_content.append('  edge [fontname="Arial", fontsize=8];')
    dot_content.append('')
    
    # System info
    system = yaml_data.get('system', {})
    dot_content.append(f'  // System: {system.get("name", "Unknown")}')
    dot_content.append(f'  // Version: {system.get("version", "Unknown")}')
    dot_content.append('')
    
    # Hardware components
    dot_content.append('  subgraph cluster_hardware {')
    dot_content.append('    label="Hardware Components";')
    dot_content.append('    style=filled;')
    dot_content.append('    color=lightblue;')
    
    hardware = yaml_data.get('hardware', {})
    
    # Motor controllers
    if 'motor_controllers' in hardware:
        dot_content.append('    subgraph cluster_motor_controllers {')
        dot_content.append('      label="Motor Controllers";')
        dot_content.append('      style=filled;')
        dot_content.append('      color=lightcyan;')
        
        controllers = hardware['motor_controllers'].get('controllers', {})
        for name, controller in controllers.items():
            sanitized_name = sanitize_name(name)
            dot_content.append(f'      {sanitized_name} [label="{name}\\n{controller.get("port", "")}", fillcolor=cyan];')
        
        dot_content.append('    }')
    
    # Sensors
    if 'sensors' in hardware:
        dot_content.append('    subgraph cluster_sensors {')
        dot_content.append('      label="Sensors";')
        dot_content.append('      style=filled;')
        dot_content.append('      color=lightgreen;')
        
        sensors = hardware['sensors']
        for sensor_type, sensor_info in sensors.items():
            if isinstance(sensor_info, dict):
                sanitized_name = sanitize_name(sensor_type)
                model = sensor_info.get('model', 'Unknown')
                dot_content.append(f'      {sanitized_name} [label="{sensor_type}\\n{model}", fillcolor=lightgreen];')
        
        dot_content.append('    }')
    
    # Experimental modules
    if 'experimental_modules' in hardware:
        exp_modules = hardware['experimental_modules']
        for module_name, module_info in exp_modules.items():
            if isinstance(module_info, dict):
                sanitized_name = sanitize_name(module_name)
                module_type = module_info.get('type', 'Unknown')
                dot_content.append(f'    {sanitized_name} [label="{module_name}\\n{module_type}", fillcolor=lightyellow];')
    
    dot_content.append('  }')
    dot_content.append('')
    
    # Software modules
    dot_content.append('  subgraph cluster_software {')
    dot_content.append('    label="Software Modules";')
    dot_content.append('    style=filled;')
    dot_content.append('    color=lightpink;')
    
    software = yaml_data.get('software', {})
    
    # Core modules
    if 'core_modules' in software:
        dot_content.append('    subgraph cluster_core_modules {')
        dot_content.append('      label="Core Modules";')
        dot_content.append('      style=filled;')
        dot_content.append('      color=lightcoral;')
        
        core_modules = software['core_modules']
        for module_name, module_info in core_modules.items():
            if isinstance(module_info, dict):
                sanitized_name = sanitize_name(module_name)
                description = module_info.get('description', '')[:30] + '...' if len(module_info.get('description', '')) > 30 else module_info.get('description', '')
                dot_content.append(f'      {sanitized_name} [label="{module_name}\\n{description}", fillcolor=coral];')
        
        dot_content.append('    }')
    
    # Sensor modules
    if 'sensor_modules' in software:
        dot_content.append('    subgraph cluster_sensor_modules {')
        dot_content.append('      label="Sensor Modules";')
        dot_content.append('      style=filled;')
        dot_content.append('      color=lightsteelblue;')
        
        sensor_modules = software['sensor_modules']
        for module_name, module_info in sensor_modules.items():
            if isinstance(module_info, dict):
                sanitized_name = sanitize_name(module_name)
                description = module_info.get('description', '')[:30] + '...' if len(module_info.get('description', '')) > 30 else module_info.get('description', '')
                dot_content.append(f'      {sanitized_name} [label="{module_name}\\n{description}", fillcolor=steelblue];')
        
        dot_content.append('    }')
    
    # Test modules
    if 'test_modules' in software:
        dot_content.append('    subgraph cluster_test_modules {')
        dot_content.append('      label="Test Modules";')
        dot_content.append('      style=filled;')
        dot_content.append('      color=lightgoldenrod;')
        
        test_modules = software['test_modules']
        for module_name, module_info in test_modules.items():
            if isinstance(module_info, dict):
                sanitized_name = sanitize_name(module_name)
                description = module_info.get('description', '')[:30] + '...' if len(module_info.get('description', '')) > 30 else module_info.get('description', '')
                dot_content.append(f'      {sanitized_name} [label="{module_name}\\n{description}", fillcolor=goldenrod];')
        
        dot_content.append('    }')
    
    dot_content.append('  }')
    dot_content.append('')
    
    # Add dependencies
    dot_content.append('  // Dependencies')
    
    # Hardware to software connections
    if 'hardware_responsibilities' in hardware:
        responsibilities = hardware['hardware_responsibilities']
        for hw_name, hw_info in responsibilities.items():
            if isinstance(hw_info, dict):
                hw_sanitized = sanitize_name(hw_name)
                responsibilities_list = hw_info.get('responsibilities', [])
                for resp in responsibilities_list:
                    if 'roboclaw' in resp.lower():
                        dot_content.append(f'  {hw_sanitized} -> roboclaw_interface [color=blue, label="controls"];')
                    elif 'optical' in resp.lower():
                        dot_content.append(f'  {hw_sanitized} -> optical_flow_sensor [color=green, label="senses"];')
                    elif 'power' in resp.lower():
                        dot_content.append(f'  {hw_sanitized} -> power_sensor [color=red, label="monitors"];')
    
    # Software module dependencies
    if 'core_modules' in software:
        core_modules = software['core_modules']
        for module_name, module_info in core_modules.items():
            if isinstance(module_info, dict):
                dependencies = module_info.get('dependencies', [])
                module_sanitized = sanitize_name(module_name)
                for dep in dependencies:
                    dep_sanitized = sanitize_name(dep)
                    dot_content.append(f'  {module_sanitized} -> {dep_sanitized} [color=purple, label="depends"];')
    
    dot_content.append('}')
    return '\n'.join(dot_content)

def generate_module_dependencies_dot(yaml_data: Dict[str, Any]) -> str:
    """Generate detailed module dependencies diagram"""
    dot_content = []
    dot_content.append('digraph ModuleDependencies {')
    dot_content.append('  rankdir=LR;')
    dot_content.append('  node [shape=box, style=filled, fontname="Arial", fontsize=9];')
    dot_content.append('  edge [fontname="Arial", fontsize=8];')
    dot_content.append('')
    
    software = yaml_data.get('software', {})
    all_modules = {}
    
    # Collect all modules
    for category in ['core_modules', 'sensor_modules', 'utility_modules', 'test_modules', 'experimental_modules']:
        if category in software:
            all_modules.update(software[category])
    
    # Create nodes
    for module_name, module_info in all_modules.items():
        if isinstance(module_info, dict):
            sanitized_name = sanitize_name(module_name)
            description = module_info.get('description', '')[:25] + '...' if len(module_info.get('description', '')) > 25 else module_info.get('description', '')
            tags = module_info.get('tags', [])
            
            # Color based on tags
            color = 'lightgray'
            if 'core' in tags:
                color = 'lightcoral'
            elif 'sensor' in tags:
                color = 'lightgreen'
            elif 'test' in tags:
                color = 'lightyellow'
            elif 'utility' in tags:
                color = 'lightblue'
            elif 'experimental' in tags:
                color = 'lightpink'
            
            dot_content.append(f'  {sanitized_name} [label="{module_name}\\n{description}", fillcolor={color}];')
    
    dot_content.append('')
    
    # Create dependencies
    for module_name, module_info in all_modules.items():
        if isinstance(module_info, dict):
            dependencies = module_info.get('dependencies', [])
            module_sanitized = sanitize_name(module_name)
            
            for dep in dependencies:
                dep_sanitized = sanitize_name(dep)
                # Only create edge if both nodes exist
                if dep_sanitized in [sanitize_name(name) for name in all_modules.keys()]:
                    dot_content.append(f'  {module_sanitized} -> {dep_sanitized} [color=blue, label="depends"];')
    
    dot_content.append('}')
    return '\n'.join(dot_content)

def generate_data_flow_dot(yaml_data: Dict[str, Any]) -> str:
    """Generate data flow diagram"""
    dot_content = []
    dot_content.append('digraph DataFlow {')
    dot_content.append('  rankdir=TB;')
    dot_content.append('  node [shape=box, style=filled, fontname="Arial", fontsize=9];')
    dot_content.append('  edge [fontname="Arial", fontsize=8];')
    dot_content.append('')
    
    # Data sources (sensors)
    dot_content.append('  subgraph cluster_sources {')
    dot_content.append('    label="Data Sources";')
    dot_content.append('    style=filled;')
    dot_content.append('    color=lightgreen;')
    dot_content.append('    optical_flow [label="Optical Flow\\nPAA5100JE-Q", fillcolor=green];')
    dot_content.append('    power_sensor [label="Power Sensor\\nINA219", fillcolor=green];')
    dot_content.append('    encoders [label="Motor Encoders\\nRoboClaw", fillcolor=green];')
    dot_content.append('  }')
    dot_content.append('')
    
    # Processing modules
    dot_content.append('  subgraph cluster_processing {')
    dot_content.append('    label="Data Processing";')
    dot_content.append('    style=filled;')
    dot_content.append('    color=lightblue;')
    dot_content.append('    kinematic_conversion [label="Kinematic\\nConversion", fillcolor=blue];')
    dot_content.append('    setpoint_generator [label="Setpoint\\nGenerator", fillcolor=blue];')
    dot_content.append('    data_logger [label="Data\\nLogger", fillcolor=blue];')
    dot_content.append('  }')
    dot_content.append('')
    
    # Control modules
    dot_content.append('  subgraph cluster_control {')
    dot_content.append('    label="Control System";')
    dot_content.append('    style=filled;')
    dot_content.append('    color=lightcoral;')
    dot_content.append('    roboclaw_interface [label="RoboClaw\\nInterface", fillcolor=coral];')
    dot_content.append('    roboclaw_control [label="RoboClaw\\nControl", fillcolor=coral];')
    dot_content.append('    platform_control [label="Platform\\nControl", fillcolor=coral];')
    dot_content.append('  }')
    dot_content.append('')
    
    # Outputs (motors)
    dot_content.append('  subgraph cluster_outputs {')
    dot_content.append('    label="Outputs";')
    dot_content.append('    style=filled;')
    dot_content.append('    color=lightyellow;')
    dot_content.append('    motor1 [label="Motor 1\\nX-axis", fillcolor=yellow];')
    dot_content.append('    motor2 [label="Motor 2\\n120°", fillcolor=yellow];')
    dot_content.append('    motor3 [label="Motor 3\\n240°", fillcolor=yellow];')
    dot_content.append('  }')
    dot_content.append('')
    
    # Data flow connections
    dot_content.append('  // Sensor to processing')
    dot_content.append('  optical_flow -> kinematic_conversion [label="ball motion"];')
    dot_content.append('  power_sensor -> data_logger [label="current/voltage"];')
    dot_content.append('  encoders -> roboclaw_interface [label="encoder data"];')
    dot_content.append('')
    
    # Processing to control
    dot_content.append('  // Processing to control')
    dot_content.append('  kinematic_conversion -> setpoint_generator [label="kinematics"];')
    dot_content.append('  setpoint_generator -> roboclaw_control [label="setpoints"];')
    dot_content.append('  roboclaw_control -> roboclaw_interface [label="commands"];')
    dot_content.append('')
    
    # Control to outputs
    dot_content.append('  // Control to outputs')
    dot_content.append('  roboclaw_interface -> motor1 [label="velocity"];')
    dot_content.append('  roboclaw_interface -> motor2 [label="velocity"];')
    dot_content.append('  roboclaw_interface -> motor3 [label="velocity"];')
    dot_content.append('')
    
    # Feedback loops
    dot_content.append('  // Feedback loops')
    dot_content.append('  motor1 -> encoders [label="feedback", style=dashed];')
    dot_content.append('  motor2 -> encoders [label="feedback", style=dashed];')
    dot_content.append('  motor3 -> encoders [label="feedback", style=dashed];')
    
    dot_content.append('}')
    return '\n'.join(dot_content)

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python3 generate_dot.py <yaml_file> [output_dir]")
        sys.exit(1)
    
    yaml_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else '.'
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Load YAML data
    data = load_yaml(yaml_path)
    
    # Generate different types of diagrams
    diagrams = {
        'system_overview': generate_system_overview_dot(data),
        'module_dependencies': generate_module_dependencies_dot(data),
        'data_flow': generate_data_flow_dot(data)
    }
    
    # Write DOT files
    for diagram_name, dot_content in diagrams.items():
        output_file = os.path.join(output_dir, f'{diagram_name}.dot')
        with open(output_file, 'w') as f:
            f.write(dot_content)
        print(f"Generated {output_file}")
    
    # Generate PNG files if dot command is available
    try:
        for diagram_name in diagrams.keys():
            dot_file = os.path.join(output_dir, f'{diagram_name}.dot')
            png_file = os.path.join(output_dir, f'{diagram_name}.png')
            os.system(f'dot -Tpng {dot_file} -o {png_file}')
            print(f"Generated {png_file}")
    except Exception as e:
        print(f"Note: Could not generate PNG files. Install Graphviz for PNG generation: {e}")

if __name__ == "__main__":
    main() 