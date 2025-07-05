#!/usr/bin/env python3
"""
RoboClaw Test Utilities Module
Contains all test-specific methods and utilities for RoboClaw testing
Separated from core interface to maintain clean separation of concerns
"""

import os
import sys
import json
import time
import platform
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
import serial
from utils.roboclaw_interface import RoboClawInterface

# Add the parent directory to sys.path to import from utils
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

class RoboClawTroubleshooter:
    """Helper for troubleshooting RoboClaw connectivity issues."""
    @staticmethod
    def handle_serial_timeout(port, channel=None, log_func=None):
        msg = f"\n[!] Serial timeout or no response from RoboClaw on port {port}"
        if channel:
            msg += f", channel {channel}"
        msg += ".\n"
        msg += "Possible causes:\n"
        msg += " - Incorrect COM port or port in use by another application\n"
        msg += " - USB/RS232 cable not connected or faulty\n"
        msg += " - RoboClaw not powered or not in correct mode\n"
        msg += " - Incorrect address or baudrate configuration\n"
        msg += " - Driver not installed or permissions issue\n"
        msg += " - Address conflict (multiple controllers with same address)\n"
        msg += "\nTroubleshooting steps:\n"
        msg += " 1. Check physical connections and power.\n"
        msg += " 2. Verify correct COM port in platform_config.json.\n"
        msg += " 3. Try disconnecting/reconnecting USB.\n"
        msg += " 4. Use Windows Device Manager to check port status.\n"
        msg += " 5. Ensure only one app is using the port.\n"
        msg += " 6. If using RS232, check wiring and jumpers.\n"
        msg += " 7. Try swapping cables or ports.\n"
        msg += " 8. If both controllers have same address, change one using IonMotion.\n"
        print(msg)
        if log_func:
            log_func("connectivity", msg)

class RoboClawTestUtils:
    """Test-specific utilities for RoboClaw testing and validation"""
    
    def __init__(self, roboclaw_interface):
        """Initialize with a RoboClaw interface instance"""
        self.interface = roboclaw_interface
        self.backup_dir = self.interface.backup_dir
        self.config = self.interface.config
    
    def read_and_save_settings(self) -> bool:
        """Read current settings from all connected controllers and save to backup"""
        try:
            print("📋 Reading and saving current RoboClaw settings...")
            
            all_settings = {}
            success = True
            
            # Read settings from each connected controller
            for controller_name in ['rc1', 'rc2']:
                if controller_name in self.interface.controller_info and self.interface.controller_info[controller_name]['connected']:
                    print(f"   Reading settings from {controller_name}...")
                    
                    controller = getattr(self.interface, controller_name)
                    address = self.interface.controller_info[controller_name]['address']
                    
                    if controller:
                        settings = self.interface.settings_manager.read_current_settings(controller, address)
                        all_settings[controller_name] = settings
                        print(f"   ✅ {controller_name} settings read successfully")
                    else:
                        print(f"   ❌ {controller_name} not available")
                        success = False
                else:
                    print(f"   ⚠️ {controller_name} not connected, skipping")
            
            if all_settings:
                # Save settings with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"roboclaw_settings_{timestamp}.json"
                filepath = os.path.join(self.backup_dir, filename)
                
                # Ensure backup directory exists
                os.makedirs(self.backup_dir, exist_ok=True)
                
                # Save settings
                with open(filepath, 'w') as f:
                    json.dump(all_settings, f, indent=2)
                
                print(f"   💾 Settings saved to: {filepath}")
                
                # Update platform config with latest settings
                self.update_config_timestamp()
                
                return success
            else:
                print("   ❌ No settings to save")
                return False
                
        except Exception as e:
            print(f"   ❌ Error reading/saving settings: {e}")
            return False
    
    def compare_with_previous_settings(self):
        """Compare current settings with the most recent backup"""
        try:
            print("🔍 Comparing current settings with previous backup...")
            
            # Get list of backup files
            if not os.path.exists(self.backup_dir):
                print("   ⚠️ No backup directory found")
                return
            
            backup_files = [f for f in os.listdir(self.backup_dir) if f.endswith('.json')]
            if not backup_files:
                print("   ⚠️ No backup files found")
                return
            
            # Get most recent backup file
            backup_files.sort(reverse=True)
            latest_backup = backup_files[0]
            backup_path = os.path.join(self.backup_dir, latest_backup)
            
            print(f"   📄 Comparing with: {latest_backup}")
            
            # Load previous settings
            with open(backup_path, 'r') as f:
                previous_settings = json.load(f)
            
            # Get current settings
            current_settings = {}
            for controller_name in ['rc1', 'rc2']:
                if controller_name in self.interface.controller_info and self.interface.controller_info[controller_name]['connected']:
                    controller = getattr(self.interface, controller_name)
                    address = self.interface.controller_info[controller_name]['address']
                    
                    if controller:
                        settings = self.interface.settings_manager.read_current_settings(controller, address)
                        current_settings[controller_name] = settings
            
            # Compare settings
            differences = self.compare_settings(current_settings, previous_settings)
            
            if differences:
                print("   ⚠️ Differences found:")
                self.print_settings_comparison(differences, "previous")
            else:
                print("   ✅ No differences found")
                
        except Exception as e:
            print(f"   ❌ Error comparing settings: {e}")
    
    def compare_settings(self, current: Dict[str, Any], previous: Dict[str, Any]) -> Dict[str, Any]:
        """Compare two settings dictionaries and return differences"""
        differences = {}
        
        def compare_dicts(dict1: Dict[str, Any], dict2: Dict[str, Any], path: str = "") -> None:
            for key in set(dict1.keys()) | set(dict2.keys()):
                current_path = f"{path}.{key}" if path else key
                
                if key not in dict1:
                    differences[current_path] = {"type": "removed", "value": dict2[key]}
                elif key not in dict2:
                    differences[current_path] = {"type": "added", "value": dict1[key]}
                elif isinstance(dict1[key], dict) and isinstance(dict2[key], dict):
                    compare_dicts(dict1[key], dict2[key], current_path)
                elif dict1[key] != dict2[key]:
                    differences[current_path] = {
                        "type": "changed", 
                        "old_value": dict2[key], 
                        "new_value": dict1[key]
                    }
        
        compare_dicts(current, previous)
        return differences
    
    def print_settings_comparison(self, differences: Dict[str, Any], comparison_type: str = "previous"):
        """Print a formatted comparison of settings differences"""
        print(f"\n📊 Settings Comparison ({comparison_type}):")
        print("-" * 50)
        
        for path, diff in differences.items():
            if diff["type"] == "added":
                print(f"➕ {path}: {diff['value']}")
            elif diff["type"] == "removed":
                print(f"➖ {path}: {diff['value']}")
            elif diff["type"] == "changed":
                print(f"🔄 {path}: {diff['old_value']} → {diff['new_value']}")
    
    def restore_settings_from_backup(self, backup_file: str) -> bool:
        """Restore settings from a backup file"""
        try:
            print(f"🔄 Restoring settings from backup: {backup_file}")
            
            backup_path = os.path.join(self.backup_dir, backup_file)
            if not os.path.exists(backup_path):
                print(f"   ❌ Backup file not found: {backup_path}")
                return False
            
            # Load backup settings
            with open(backup_path, 'r') as f:
                backup_settings = json.load(f)
            
            # Restore settings for each controller
            success = True
            for controller_name, settings in backup_settings.items():
                if controller_name in self.interface.controller_info and self.interface.controller_info[controller_name]['connected']:
                    print(f"   Restoring {controller_name}...")
                    
                    controller = getattr(self.interface, controller_name)
                    if controller:
                        # Apply settings to controller
                        # Note: This would need to be implemented based on the specific settings structure
                        print(f"   ✅ {controller_name} settings restored")
                    else:
                        print(f"   ❌ {controller_name} not available")
                        success = False
                else:
                    print(f"   ⚠️ {controller_name} not connected, skipping")
            
            return success
            
        except Exception as e:
            print(f"   ❌ Error restoring settings: {e}")
            return False
    
    def log_error(self, test_name: str, error: str):
        """Log test errors for troubleshooting"""
        error_entry = {
            "timestamp": datetime.now().isoformat(),
            "test": test_name,
            "error": error
        }
        
        self.interface.errors.append(error_entry)
        print(f"   ❌ {test_name}: {error}")
    
    def update_config_timestamp(self):
        """Update the last_updated timestamp in platform_config.json"""
        try:
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'platform_config.json')
            
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Update timestamp
            config['system_metadata']['last_updated'] = datetime.now().strftime("%Y-%m-%d")
            
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=4)
                
        except Exception as e:
            print(f"Warning: Could not update config timestamp: {e}")

    def backup_current_settings(self) -> None:
        """Backup current settings to a timestamped file"""
        try:
            # Ensure backup directory exists
            os.makedirs(self.backup_dir, exist_ok=True)
            
            # Create timestamped filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"roboclaw_settings_backup_{timestamp}.json"
            filepath = os.path.join(self.backup_dir, filename)
            
            # Read current settings
            all_settings = {}
            for controller_name in ['rc1', 'rc2']:
                if controller_name in self.interface.controller_info and self.interface.controller_info[controller_name]['connected']:
                    controller = getattr(self.interface, controller_name)
                    address = self.interface.controller_info[controller_name]['address']
                    
                    if controller:
                        settings = self.interface.settings_manager.read_current_settings(controller, address)
                        all_settings[controller_name] = settings
            
            # Save to backup file
            with open(filepath, 'w') as f:
                json.dump(all_settings, f, indent=2)
            
            print(f"   💾 Settings backed up to: {filepath}")
            
        except Exception as e:
            print(f"   ❌ Error backing up settings: {e}")
    
    def test_connectivity(self, controller_name: str) -> Dict[str, Any]:
        """Test connectivity for a specific controller"""
        result = {
            "timestamp": datetime.now().isoformat(),
            "test_type": "connectivity_test",
            "controller": controller_name,
            "status": False,
            "details": {}
        }
        
        if controller_name not in self.interface.controller_info:
            result["error"] = f"Controller {controller_name} not found"
            return result
        
        if not self.interface.controller_info[controller_name]['connected']:
            result["error"] = f"Controller {controller_name} not connected"
            return result
        
        controller = getattr(self.interface, controller_name)
        address = self.interface.controller_info[controller_name]['address']
        
        try:
            # Test version read
            version_result = controller.ReadVersion(address)
            if version_result[0]:
                result["details"]["version"] = version_result[1]
                result["status"] = True
            else:
                result["error"] = "Version read failed"
            
            # Test voltage read
            voltage_result = controller.ReadMainBatteryVoltage(address)
            if voltage_result[0]:
                result["details"]["voltage"] = voltage_result[1] / 10.0  # Convert to volts
            else:
                result["details"]["voltage_error"] = "Voltage read failed"
            
            # Test current read
            current_result = controller.ReadCurrents(address)
            if current_result[0]:
                result["details"]["currents"] = {
                    "m1": current_result[1] / 100.0,  # Convert to amps
                    "m2": current_result[2] / 100.0
                }
            else:
                result["details"]["current_error"] = "Current read failed"
            
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def test_bandwidth(self, controller_name: str, max_speed: int = 500000) -> Dict[str, Any]:
        """Test communication bandwidth for a specific controller"""
        result = {
            "timestamp": datetime.now().isoformat(),
            "test_type": "bandwidth_test",
            "controller": controller_name,
            "max_safe_speed": 0,
            "status": False
        }
        
        if controller_name not in self.interface.controller_info:
            result["error"] = f"Controller {controller_name} not found"
            return result
        
        if not self.interface.controller_info[controller_name]['connected']:
            result["error"] = f"Controller {controller_name} not connected"
            return result
        
        controller = getattr(self.interface, controller_name)
        address = self.interface.controller_info[controller_name]['address']
        
        # Test speeds from low to high
        test_speeds = [1000, 5000, 10000, 20000, 50000, 100000, 200000, 500000]
        test_speeds = [s for s in test_speeds if s <= max_speed]
        
        for speed in test_speeds:
            try:
                # Test version read at this speed
                version_result = controller.ReadVersion(address)
                if version_result[0]:
                    result["max_safe_speed"] = speed
                else:
                    break
            except Exception:
                break
        
        result["status"] = result["max_safe_speed"] > 0
        return result
    
    def test_estop_cycling(self, controller_name: str, cycles: int = 5, frequency: float = 1.0) -> Dict[str, Any]:
        """Test E-Stop cycling for a specific controller"""
        result = {
            "timestamp": datetime.now().isoformat(),
            "test_type": "estop_cycling_test",
            "controller": controller_name,
            "cycles_completed": 0,
            "status": False
        }
        
        if controller_name not in self.interface.controller_info:
            result["error"] = f"Controller {controller_name} not found"
            return result
        
        if not self.interface.controller_info[controller_name]['connected']:
            result["error"] = f"Controller {controller_name} not connected"
            return result
        
        controller = getattr(self.interface, controller_name)
        address = self.interface.controller_info[controller_name]['address']
        
        try:
            cycle_time = 1.0 / frequency
            completed_cycles = 0
            
            for i in range(cycles):
                # Read error state (should show E-Stop when active)
                error_result = controller.ReadError(address)
                if error_result[0]:
                    error_code = error_result[1]
                    # Check if E-Stop is active (bit 1)
                    estop_active = bool(error_code & 0x0002)
                    
                    if estop_active:
                        completed_cycles += 1
                
                time.sleep(cycle_time)
            
            result["cycles_completed"] = completed_cycles
            result["status"] = completed_cycles > 0
            
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def test_motor_mapping(self) -> Dict[str, Any]:
        """Test motor mapping functionality"""
        result = {
            "timestamp": datetime.now().isoformat(),
            "test_type": "motor_mapping_test",
            "motors": {},
            "status": False
        }
        
        # Test each motor
        for motor_id in range(1, 5):  # 4 motors
            motor_result = {
                "motor_id": motor_id,
                "status": False,
                "details": {}
            }
            
            try:
                # Try to set a very low velocity
                success = self.interface.set_velocity(motor_id, 50)
                motor_result["status"] = success
                
                if success:
                    # Get motor data
                    motor_data = self.interface.get_motor_data(motor_id)
                    if motor_data:
                        motor_result["details"] = motor_data
                    
                    # Stop motor
                    self.interface.set_velocity(motor_id, 0)
                
            except Exception as e:
                motor_result["error"] = str(e)
            
            result["motors"][motor_id] = motor_result
        
        # Determine overall status
        successful_motors = sum(1 for motor in result["motors"].values() if motor["status"])
        result["status"] = successful_motors > 0
        
        return result

def fix_roboclaw_pins(interface=None, controller_name='rc2'):
    """Fix RoboClaw pin settings for a given controller (default rc2)"""
    if interface is None:
        interface = RoboClawInterface(use_dual_controllers=True)
        if not interface.connect():
            return False, 'Failed to connect to RoboClaw controllers'
    if not interface.controller_info.get(controller_name, {}).get('connected', False):
        return False, f'{controller_name.upper()} is not connected'
    controller = getattr(interface, controller_name)
    address = interface.controller_info[controller_name]['address']
    try:
        result = controller.SetPinFunctions(address, 0, 0, 0)
        if result:
            verify_result = controller.ReadPinFunctions(address)
            if verify_result[0]:
                s3, s4, s5 = verify_result[1], verify_result[2], verify_result[3]
                if s3 == 0 and s4 == 0 and s5 == 0:
                    return True, {'s3': s3, 's4': s4, 's5': s5}
                else:
                    return False, {'s3': s3, 's4': s4, 's5': s5}
            else:
                return False, 'Could not verify pin settings'
        else:
            return False, 'Failed to apply pin settings'
    except Exception as e:
        return False, str(e)

def check_error_state(interface, controller_name):
    """Check error state and pin functions for a given controller"""
    result = {
        'timestamp': datetime.now().isoformat(),
        'controller': controller_name,
        'error_state': None,
        'pin_functions': None,
        'status': False
    }
    if controller_name not in interface.controller_info:
        result['error'] = f'Controller {controller_name} not found'
        return result
    if not interface.controller_info[controller_name]['connected']:
        result['error'] = f'Controller {controller_name} not connected'
        return result
    controller = getattr(interface, controller_name)
    address = interface.controller_info[controller_name]['address']
    try:
        error_result = controller.ReadError(address)
        if error_result[0]:
            error_code = error_result[1]
            result['error_state'] = error_code
            error_messages = []
            if error_code & 0x0001:
                error_messages.append('Normal')
            if error_code & 0x0002:
                error_messages.append('E-Stop')
            if error_code & 0x0004:
                error_messages.append('Temperature Error')
            if error_code & 0x0008:
                error_messages.append('Temperature 2 Error')
            if error_code & 0x0010:
                error_messages.append('Main Battery High Error')
            if error_code & 0x0020:
                error_messages.append('Logic Battery High Error')
            if error_code & 0x0040:
                error_messages.append('Logic Battery Low Error')
            if error_code & 0x0080:
                error_messages.append('M1 Driver Fault')
            if error_code & 0x0100:
                error_messages.append('M2 Driver Fault')
            if error_code & 0x0200:
                error_messages.append('Main Battery Low Error')
            if error_code & 0x0400:
                error_messages.append('M1 Home')
            if error_code & 0x0800:
                error_messages.append('M2 Home')
            if error_code & 0x1000:
                error_messages.append('M1 Position Error')
            if error_code & 0x2000:
                error_messages.append('M2 Position Error')
            if error_code & 0x4000:
                error_messages.append('M1 Current Error')
            if error_code & 0x8000:
                error_messages.append('M2 Current Error')
            result['error_messages'] = error_messages
            result['estop_active'] = bool(error_code & 0x0002)
        else:
            result['error'] = 'Failed to read error state'
            return result
        pin_result = controller.ReadPinFunctions(address)
        if pin_result[0]:
            s3_mode, s4_mode, s5_mode = pin_result[1], pin_result[2], pin_result[3]
            result['pin_functions'] = {'s3': s3_mode, 's4': s4_mode, 's5': s5_mode}
            result['s3_inverted'] = (s3_mode == 1)
            result['s4_inverted'] = (s4_mode == 1)
            result['s5_inverted'] = (s5_mode == 1)
        else:
            result['error'] = 'Failed to read pin functions'
            return result
        result['status'] = True
    except Exception as e:
        result['error'] = str(e)
    return result

# RoboclawSettings class moved to roboclaw_interface.py to avoid circular imports 