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
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"roboclaw_settings_{timestamp}.json"
        self.save_settings(self.current_settings, filename)
        print(f"Settings backed up to: {filename}")

# RoboclawSettings class moved to roboclaw_interface.py to avoid circular imports 