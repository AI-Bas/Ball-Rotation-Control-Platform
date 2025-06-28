#!/usr/bin/env python3
"""
RoboClaw Settings Manager Module
Streamlined module for managing and comparing RoboClaw settings
Centrally controlled by system_test.py

Features:
- Compare platform_config.json with actual RoboClaw settings
- Prioritize safety settings (S3, S4, S5 pins, voltage/current limits)
- Interactive settings update with numbered options
- Comprehensive settings backup and restoration
- Integration with platform_config.json and system_design_architecture.yaml
"""

import sys
import os
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

# Add the parent directory to sys.path to import from utils
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.roboclaw_interface import RoboClawInterface

class RoboClawSettingsManager:
    """RoboClaw settings management and comparison module"""
    
    def __init__(self):
        """Initialize the settings manager"""
        self.test_results = {
            "timestamp": datetime.now().isoformat(),
            "tests": {},
            "errors": [],
            "settings_comparison": {},
            "settings_updated": {},
            "backup_created": False
        }
        self.platform_config = self.load_platform_config()
        self.roboclaw_config = self.platform_config.get('hardware', {}).get('roboclaw', {})
        self.settings_reference = self.platform_config.get('roboclaw_settings_reference', {})
        
    def load_platform_config(self) -> Dict[str, Any]:
        """Load platform configuration"""
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'platform_config.json')
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load platform_config.json: {e}")
            return {}
    
    def log_error(self, test_name: str, error: str):
        """Log an error during testing"""
        self.test_results["errors"].append({
            "test": test_name,
            "error": error,
            "timestamp": datetime.now().isoformat()
        })
    
    def get_roboclaw_controllers(self) -> Dict[str, Dict[str, Any]]:
        """Get RoboClaw controllers from platform configuration"""
        controllers = self.roboclaw_config.get('controllers', {})
        if not controllers:
            print("⚠ No RoboClaw controllers found in platform configuration")
            print("Please run motor identification first to detect controllers")
            return {}
        
        return controllers
    
    def connect_to_controllers(self, controllers: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Connect to all RoboClaw controllers"""
        print("\n=== Connecting to RoboClaw Controllers ===")
        
        connected_controllers = {}
        
        for controller_name, controller_info in controllers.items():
            try:
                port = controller_info['port']
                address = int(controller_info['address'], 16) if isinstance(controller_info['address'], str) else controller_info['address']
                
                # Import Roboclaw class
                sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
                from roboclaw_3 import Roboclaw
                
                rc = Roboclaw(port, 0)  # USB mode
                if rc.Open():
                    # Test connection by reading version
                    version_result = rc.ReadVersion(address)
                    if version_result[0]:
                        connected_controllers[controller_name] = {
                            'controller': rc,
                            'address': address,
                            'port': port,
                            'version': version_result[1],
                            'info': controller_info
                        }
                        print(f"✓ Connected to {controller_name} on {port} (Address: 0x{address:02X})")
                        print(f"  Version: {version_result[1]}")
                    else:
                        print(f"✗ {controller_name} not responding on {port}")
                else:
                    print(f"✗ Could not open port {port} for {controller_name}")
                    
            except Exception as e:
                print(f"✗ Error connecting to {controller_name}: {e}")
                self.log_error("controller_connection", f"Error connecting to {controller_name}: {e}")
        
        if not connected_controllers:
            print("✗ No controllers connected!")
        else:
            print(f"\n✓ Connected to {len(connected_controllers)} controller(s)")
        
        return connected_controllers
    
    def read_current_settings(self, controller_name: str, controller_data: Dict[str, Any]) -> Dict[str, Any]:
        """Read current settings from a RoboClaw controller"""
        rc = controller_data['controller']
        address = controller_data['address']
        
        current_settings = {
            'controller_name': controller_name,
            'address': address,
            'timestamp': datetime.now().isoformat(),
            'settings': {}
        }
        
        try:
            # Safety Settings (Priority 1)
            print(f"Reading safety settings from {controller_name}...")
            
            # Pin functions (S3, S4, S5)
            pin_result = rc.ReadPinFunctions(address)
            if pin_result[0]:
                current_settings['settings']['pin_functions'] = {
                    's3_mode': pin_result[1],
                    's4_mode': pin_result[2],
                    's5_mode': pin_result[3],
                    'description': 'Pin function modes (0=Disabled, 1=E-Stop, 2=Voltage clamp, 3=User switch)'
                }
            
            # Voltage limits
            main_voltage_result = rc.ReadMinMaxMainVoltages(address)
            if main_voltage_result[0]:
                current_settings['settings']['voltage_limits'] = {
                    'main_battery_min': main_voltage_result[1],
                    'main_battery_max': main_voltage_result[2],
                    'description': 'Main battery voltage limits (0.1V units)'
                }
            
            logic_voltage_result = rc.ReadMinMaxLogicVoltages(address)
            if logic_voltage_result[0]:
                current_settings['settings']['logic_voltage_limits'] = {
                    'logic_battery_min': logic_voltage_result[1],
                    'logic_battery_max': logic_voltage_result[2],
                    'description': 'Logic battery voltage limits (0.1V units)'
                }
            
            # Current limits
            m1_current_result = rc.ReadM1MaxCurrent(address)
            if m1_current_result[0]:
                current_settings['settings']['current_limits'] = {
                    'motor1_max_current': m1_current_result[1],
                    'description': 'Motor current limits (0.1A units)'
                }
            
            m2_current_result = rc.ReadM2MaxCurrent(address)
            if m2_current_result[0]:
                current_settings['settings']['current_limits']['motor2_max_current'] = m2_current_result[1]
            
            # Motion Control Settings (Priority 2)
            print(f"Reading motion control settings from {controller_name}...")
            
            # Velocity PID for both motors
            for motor_num in [1, 2]:
                if motor_num == 1:
                    pid_result = rc.ReadM1VelocityPID(address)
                else:
                    pid_result = rc.ReadM2VelocityPID(address)
                
                if pid_result[0]:
                    current_settings['settings'][f'velocity_pid_motor{motor_num}'] = {
                        'p': pid_result[1],
                        'i': pid_result[2],
                        'd': pid_result[3],
                        'qpps': pid_result[4],
                        'description': f'Velocity PID parameters for motor {motor_num} (scaled values)'
                    }
            
            # Position PID for both motors
            for motor_num in [1, 2]:
                if motor_num == 1:
                    pos_pid_result = rc.ReadM1PositionPID(address)
                else:
                    pos_pid_result = rc.ReadM2PositionPID(address)
                
                if pos_pid_result[0]:
                    current_settings['settings'][f'position_pid_motor{motor_num}'] = {
                        'kp': pos_pid_result[1],
                        'ki': pos_pid_result[2],
                        'kd': pos_pid_result[3],
                        'kimax': pos_pid_result[4],
                        'deadzone': pos_pid_result[5],
                        'min': pos_pid_result[6],
                        'max': pos_pid_result[7],
                        'description': f'Position PID parameters for motor {motor_num} (scaled values)'
                    }
            
            # Acceleration settings
            m1_accel_result = rc.ReadM1DefaultAccel(address)
            if m1_accel_result[0]:
                current_settings['settings']['acceleration'] = {
                    'motor1_default_accel': m1_accel_result[1],
                    'description': 'Default acceleration for motor 1 (steps/sec²)'
                }
            
            m2_accel_result = rc.ReadM2DefaultAccel(address)
            if m2_accel_result[0]:
                current_settings['settings']['acceleration']['motor2_default_accel'] = m2_accel_result[1]
            
            # Other Settings (Priority 3)
            print(f"Reading other settings from {controller_name}...")
            
            # PWM mode
            pwm_result = rc.ReadPWMMode(address)
            if pwm_result[0]:
                current_settings['settings']['pwm_settings'] = {
                    'pwm_mode': pwm_result[1],
                    'description': 'PWM mode (0=Sign magnitude, 1=Locked antiphase)'
                }
            
            # Deadband
            deadband_result = rc.GetDeadBand(address)
            if deadband_result[0]:
                current_settings['settings']['deadband'] = {
                    'min': deadband_result[1],
                    'max': deadband_result[2],
                    'description': 'Analog input deadband settings'
                }
            
            # Encoder modes
            encoder_result = rc.ReadEncoderModes(address)
            if encoder_result[0]:
                current_settings['settings']['encoder_settings'] = {
                    'motor1_encoder_mode': encoder_result[1],
                    'motor2_encoder_mode': encoder_result[2],
                    'description': 'Encoder modes (0=Quadrature, 1=Single, 2=Single with direction, 3=Single with direction inverted)'
                }
            
            # Configuration
            config_result = rc.GetConfig(address)
            if config_result[0]:
                current_settings['settings']['configuration'] = {
                    'config': config_result[1],
                    'description': 'General configuration flags'
                }
            
            print(f"✓ Successfully read settings from {controller_name}")
            
        except Exception as e:
            print(f"✗ Error reading settings from {controller_name}: {e}")
            self.log_error("settings_read", f"Error reading settings from {controller_name}: {e}")
        
        return current_settings
    
    def compare_settings(self, current_settings: Dict[str, Any], reference_settings: Dict[str, Any]) -> Dict[str, Any]:
        """Compare current settings with reference settings"""
        comparison = {
            'controller_name': current_settings['controller_name'],
            'timestamp': datetime.now().isoformat(),
            'differences': {},
            'summary': {
                'total_settings': 0,
                'matching_settings': 0,
                'different_settings': 0,
                'missing_settings': 0
            }
        }
        
        current = current_settings.get('settings', {})
        reference = reference_settings.get('settings', {})
        
        # Compare all settings
        all_keys = set(current.keys()) | set(reference.keys())
        
        for key in all_keys:
            comparison['summary']['total_settings'] += 1
            
            if key in current and key in reference:
                if current[key] == reference[key]:
                    comparison['summary']['matching_settings'] += 1
                else:
                    comparison['summary']['different_settings'] += 1
                    comparison['differences'][key] = {
                        'current': current[key],
                        'reference': reference[key],
                        'status': 'different'
                    }
            elif key in current:
                comparison['summary']['missing_settings'] += 1
                comparison['differences'][key] = {
                    'current': current[key],
                    'reference': 'Not in reference',
                    'status': 'missing_in_reference'
                }
            else:
                comparison['summary']['missing_settings'] += 1
                comparison['differences'][key] = {
                    'current': 'Not in current',
                    'reference': reference[key],
                    'status': 'missing_in_current'
                }
        
        return comparison
    
    def display_settings_comparison(self, comparison: Dict[str, Any]):
        """Display settings comparison with priority highlighting"""
        print(f"\n=== Settings Comparison for {comparison['controller_name']} ===")
        
        summary = comparison['summary']
        print(f"Total settings: {summary['total_settings']}")
        print(f"Matching settings: {summary['matching_settings']}")
        print(f"Different settings: {summary['different_settings']}")
        print(f"Missing settings: {summary['missing_settings']}")
        
        if not comparison['differences']:
            print("✓ All settings match reference configuration!")
            return
        
        print(f"\n⚠ Found {len(comparison['differences'])} setting differences:")
        
        # Priority 1: Safety Settings
        safety_settings = ['pin_functions', 'voltage_limits', 'logic_voltage_limits', 'current_limits']
        safety_differences = {k: v for k, v in comparison['differences'].items() if k in safety_settings}
        
        if safety_differences:
            print("\n🔴 SAFETY SETTINGS (HIGH PRIORITY):")
            for setting_name, diff in safety_differences.items():
                print(f"  {setting_name}:")
                print(f"    Current: {diff['current']}")
                print(f"    Reference: {diff['reference']}")
                print(f"    Status: {diff['status']}")
        
        # Priority 2: Motion Control Settings
        motion_settings = ['velocity_pid_motor1', 'velocity_pid_motor2', 'position_pid_motor1', 
                          'position_pid_motor2', 'acceleration']
        motion_differences = {k: v for k, v in comparison['differences'].items() if k in motion_settings}
        
        if motion_differences:
            print("\n🟡 MOTION CONTROL SETTINGS (MEDIUM PRIORITY):")
            for setting_name, diff in motion_differences.items():
                print(f"  {setting_name}:")
                print(f"    Current: {diff['current']}")
                print(f"    Reference: {diff['reference']}")
                print(f"    Status: {diff['status']}")
        
        # Priority 3: Other Settings
        other_differences = {k: v for k, v in comparison['differences'].items() 
                           if k not in safety_settings and k not in motion_settings}
        
        if other_differences:
            print("\n🟢 OTHER SETTINGS (LOW PRIORITY):")
            for setting_name, diff in other_differences.items():
                print(f"  {setting_name}:")
                print(f"    Current: {diff['current']}")
                print(f"    Reference: {diff['reference']}")
                print(f"    Status: {diff['status']}")
    
    def create_settings_update_menu(self, comparison: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create numbered menu for settings updates"""
        menu_items = []
        option_number = 1
        
        # Safety settings first (high priority)
        safety_settings = ['pin_functions', 'voltage_limits', 'logic_voltage_limits', 'current_limits']
        for setting_name in safety_settings:
            if setting_name in comparison['differences']:
                menu_items.append({
                    'number': option_number,
                    'setting_name': setting_name,
                    'priority': 'HIGH',
                    'description': f'Update {setting_name} (Safety Setting)',
                    'current': comparison['differences'][setting_name]['current'],
                    'reference': comparison['differences'][setting_name]['reference']
                })
                option_number += 1
        
        # Motion control settings (medium priority)
        motion_settings = ['velocity_pid_motor1', 'velocity_pid_motor2', 'position_pid_motor1', 
                          'position_pid_motor2', 'acceleration']
        for setting_name in motion_settings:
            if setting_name in comparison['differences']:
                menu_items.append({
                    'number': option_number,
                    'setting_name': setting_name,
                    'priority': 'MEDIUM',
                    'description': f'Update {setting_name} (Motion Control)',
                    'current': comparison['differences'][setting_name]['current'],
                    'reference': comparison['differences'][setting_name]['reference']
                })
                option_number += 1
        
        # Other settings (low priority)
        other_settings = [k for k in comparison['differences'].keys() 
                         if k not in safety_settings and k not in motion_settings]
        for setting_name in other_settings:
            menu_items.append({
                'number': option_number,
                'setting_name': setting_name,
                'priority': 'LOW',
                'description': f'Update {setting_name}',
                'current': comparison['differences'][setting_name]['current'],
                'reference': comparison['differences'][setting_name]['reference']
            })
            option_number += 1
        
        return menu_items
    
    def display_update_menu(self, menu_items: List[Dict[str, Any]]):
        """Display the settings update menu"""
        if not menu_items:
            print("✓ No settings need updating!")
            return
        
        print(f"\n=== Settings Update Menu ===")
        print("Select a setting to update (or 0 to exit without changes):")
        
        for item in menu_items:
            priority_color = {
                'HIGH': '🔴',
                'MEDIUM': '🟡',
                'LOW': '🟢'
            }.get(item['priority'], '⚪')
            
            print(f"\n{item['number']}. {priority_color} {item['description']}")
            print(f"    Current: {item['current']}")
            print(f"    Reference: {item['reference']}")
        
        print(f"\n0. Exit without making changes")
        print(f"S. Save current settings to platform_config.json")
    
    def update_setting(self, controller_data: Dict[str, Any], setting_name: str, reference_value: Any) -> bool:
        """Update a specific setting on the RoboClaw controller"""
        rc = controller_data['controller']
        address = controller_data['address']
        
        try:
            print(f"Updating {setting_name} to {reference_value}...")
            
            # Implement setting updates based on setting name
            if setting_name == 'pin_functions':
                s3_mode = reference_value.get('s3_mode', 1)
                s4_mode = reference_value.get('s4_mode', 2)
                s5_mode = reference_value.get('s5_mode', 2)
                result = rc.SetPinFunctions(address, s3_mode, s4_mode, s5_mode)
                
            elif setting_name == 'voltage_limits':
                min_voltage = reference_value.get('main_battery_min', 60)
                max_voltage = reference_value.get('main_battery_max', 300)
                result = rc.SetMainVoltages(address, min_voltage, max_voltage)
                
            elif setting_name == 'logic_voltage_limits':
                min_voltage = reference_value.get('logic_battery_min', 60)
                max_voltage = reference_value.get('logic_battery_max', 300)
                result = rc.SetLogicVoltages(address, min_voltage, max_voltage)
                
            elif setting_name == 'current_limits':
                if 'motor1_max_current' in reference_value:
                    result1 = rc.SetM1MaxCurrent(address, reference_value['motor1_max_current'])
                if 'motor2_max_current' in reference_value:
                    result2 = rc.SetM2MaxCurrent(address, reference_value['motor2_max_current'])
                result = result1 and result2 if 'result1' in locals() and 'result2' in locals() else result1
                
            elif setting_name.startswith('velocity_pid_motor'):
                motor_num = int(setting_name[-1])
                p = reference_value.get('p', 65536)
                i = reference_value.get('i', 32768)
                d = reference_value.get('d', 16384)
                qpps = reference_value.get('qpps', 44000)
                
                if motor_num == 1:
                    result = rc.SetM1VelocityPID(address, p, i, d, qpps)
                else:
                    result = rc.SetM2VelocityPID(address, p, i, d, qpps)
                    
            elif setting_name.startswith('position_pid_motor'):
                motor_num = int(setting_name[-1])
                kp = reference_value.get('kp', 1024)
                ki = reference_value.get('ki', 512)
                kd = reference_value.get('kd', 256)
                kimax = reference_value.get('kimax', 156)
                deadzone = reference_value.get('deadzone', 0)
                min_pos = reference_value.get('min', 0)
                max_pos = reference_value.get('max', 50000)
                
                if motor_num == 1:
                    result = rc.SetM1PositionPID(address, kp, ki, kd, kimax, deadzone, min_pos, max_pos)
                else:
                    result = rc.SetM2PositionPID(address, kp, ki, kd, kimax, deadzone, min_pos, max_pos)
                    
            elif setting_name == 'acceleration':
                if 'motor1_default_accel' in reference_value:
                    result1 = rc.SetM1DefaultAccel(address, reference_value['motor1_default_accel'])
                if 'motor2_default_accel' in reference_value:
                    result2 = rc.SetM2DefaultAccel(address, reference_value['motor2_default_accel'])
                result = result1 and result2 if 'result1' in locals() and 'result2' in locals() else result1
                
            elif setting_name == 'pwm_settings':
                pwm_mode = reference_value.get('pwm_mode', 0)
                result = rc.SetPWMMode(address, pwm_mode)
                
            elif setting_name == 'deadband':
                min_deadband = reference_value.get('min', 0)
                max_deadband = reference_value.get('max', 0)
                result = rc.SetDeadBand(address, min_deadband, max_deadband)
                
            elif setting_name == 'encoder_settings':
                motor1_mode = reference_value.get('motor1_encoder_mode', 0)
                motor2_mode = reference_value.get('motor2_encoder_mode', 0)
                result1 = rc.SetM1EncoderMode(address, motor1_mode)
                result2 = rc.SetM2EncoderMode(address, motor2_mode)
                result = result1 and result2
                
            elif setting_name == 'configuration':
                config = reference_value.get('config', 0)
                result = rc.SetConfig(address, config)
                
            else:
                print(f"⚠ Unknown setting: {setting_name}")
                return False
            
            if result:
                print(f"✓ Successfully updated {setting_name}")
                return True
            else:
                print(f"✗ Failed to update {setting_name}")
                return False
                
        except Exception as e:
            print(f"✗ Error updating {setting_name}: {e}")
            self.log_error("setting_update", f"Error updating {setting_name}: {e}")
            return False
    
    def save_settings_to_config(self, current_settings: Dict[str, Any]) -> bool:
        """Save current settings to platform configuration"""
        try:
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'platform_config.json')
            
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Update settings reference with current values
            if 'roboclaw_settings_reference' not in config:
                config['roboclaw_settings_reference'] = {}
            
            controller_name = current_settings['controller_name']
            config['roboclaw_settings_reference'][controller_name] = {
                'settings': current_settings['settings'],
                'last_updated': datetime.now().isoformat(),
                'updated_by': 'settings_manager'
            }
            
            # Save updated config
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=4)
            
            print(f"✓ Settings saved to platform configuration")
            return True
            
        except Exception as e:
            print(f"Error saving settings to configuration: {e}")
            self.log_error("config_save", str(e))
            return False
    
    def run_settings_manager(self) -> bool:
        """Run complete settings management process"""
        print("RoboClaw Settings Manager Module")
        print("=================================")
        print("This module will:")
        print("1. Connect to all RoboClaw controllers")
        print("2. Read current settings from controllers")
        print("3. Compare with platform_config.json reference")
        print("4. Display differences with priority highlighting")
        print("5. Allow interactive settings updates")
        print("6. Save updated settings to configuration")
        print()
        
        # Step 1: Get controllers from configuration
        controllers = self.get_roboclaw_controllers()
        if not controllers:
            print("✗ No RoboClaw controllers found in configuration")
            return False
        
        # Step 2: Connect to controllers
        connected_controllers = self.connect_to_controllers(controllers)
        if not connected_controllers:
            print("✗ No controllers connected")
            return False
        
        # Step 3: Read current settings from all controllers
        all_current_settings = {}
        for controller_name, controller_data in connected_controllers.items():
            print(f"\nReading settings from {controller_name}...")
            current_settings = self.read_current_settings(controller_name, controller_data)
            all_current_settings[controller_name] = current_settings
        
        # Step 4: Compare settings with reference
        all_comparisons = {}
        for controller_name, current_settings in all_current_settings.items():
            reference_settings = self.settings_reference.get(controller_name, {'settings': {}})
            comparison = self.compare_settings(current_settings, reference_settings)
            all_comparisons[controller_name] = comparison
            
            # Display comparison
            self.display_settings_comparison(comparison)
        
        # Step 5: Interactive settings update
        for controller_name, comparison in all_comparisons.items():
            if comparison['differences']:
                print(f"\n{'='*60}")
                print(f"Settings Update for {controller_name}")
                print('='*60)
                
                menu_items = self.create_settings_update_menu(comparison)
                self.display_update_menu(menu_items)
                
                while True:
                    try:
                        user_input = input("\nEnter option number (or 'S' to save, '0' to exit): ").strip().upper()
                        
                        if user_input == '0':
                            print("Exiting without changes...")
                            break
                        elif user_input == 'S':
                            if self.save_settings_to_config(all_current_settings[controller_name]):
                                print("✓ Settings saved to configuration")
                            break
                        else:
                            try:
                                option_num = int(user_input)
                                if 1 <= option_num <= len(menu_items):
                                    selected_item = menu_items[option_num - 1]
                                    setting_name = selected_item['setting_name']
                                    reference_value = comparison['differences'][setting_name]['reference']
                                    
                                    if self.update_setting(connected_controllers[controller_name], setting_name, reference_value):
                                        print(f"✓ Updated {setting_name}")
                                        # Remove from menu after successful update
                                        menu_items.pop(option_num - 1)
                                        if not menu_items:
                                            print("✓ All settings updated!")
                                            break
                                        self.display_update_menu(menu_items)
                                    else:
                                        print(f"✗ Failed to update {setting_name}")
                                else:
                                    print("Invalid option number")
                            except ValueError:
                                print("Invalid input. Please enter a number.")
                    except KeyboardInterrupt:
                        print("\nSettings update interrupted by user")
                        break
        
        # Step 6: Close all controllers
        for controller_data in connected_controllers.values():
            try:
                controller_data['controller']._port.close()
            except:
                pass
        
        print("\n✓ Settings manager completed successfully!")
        return True

def main():
    """Main function for standalone execution"""
    settings_manager = RoboClawSettingsManager()
    success = settings_manager.run_settings_manager()
    
    if success:
        print("\n✓ Settings manager module completed successfully!")
    else:
        print("\n✗ Settings manager module failed!")
    
    return success

if __name__ == "__main__":
    main() 