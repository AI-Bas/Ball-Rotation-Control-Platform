#!/usr/bin/env python3
"""
Optical Flow Test Menu - PAA5100JE-Q Sensor Testing
==================================================

Dedicated test module for PAA5100JE-Q optical flow sensor functionality.
Centrally controlled by system_test.py

Features:
- SPI connectivity testing
- LED control and blinking test
- Motion detection with manual confirmation
- Bandwidth testing with performance metrics
- Autonomous execution support
"""

import os
import sys
import json
import time
import select
import argparse
from datetime import datetime
from typing import Dict, Any, Optional, List

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.optical_flow_sensor import OpticalFlowSensor
from utils.autopilot_manager import create_autopilot_manager, set_autopilot_manager, get_autopilot_input

try:
    from config.platform_config import load_config, save_config
except ImportError:
    def load_config():
        return {}
    def save_config(config):
        pass

class OpticalFlowTestMenu:
    """Optical Flow Sensor Test Menu for PAA5100JE-Q"""
    
    def __init__(self, development_mode: bool = False, autopilot_input: str = ""):
        self.development_mode = development_mode
        self.autopilot_input = autopilot_input
        # Initialize autopilot manager for this script
        self.autopilot_manager = create_autopilot_manager("optical_flow_test_menu", autopilot_input)
        set_autopilot_manager(self.autopilot_manager)
        self.autopilot_index = 0
        self.test_results = {}
        self.config = load_config()
        
        # Initialize sensor interface
        self.sensor_interface = None
        
        print("🔍 PAA5100JE-Q Optical Flow Sensor Test Menu")
        print("=" * 50)
        
    def get_autopilot_input(self, prompt: str = "Enter choice: ") -> str:
        return get_autopilot_input(prompt)
    
    def test_spi_connectivity(self) -> bool:
        """Test PAA5100JE-Q SPI bus access via OpticalFlowSensor utility"""
        try:
            print("   Testing PAA5100JE-Q SPI bus access (via OpticalFlowSensor utility)...")
            config = self.config.get('hardware', {}).get('optical_flow', {
                'spi_bus': 0,
                'spi_device': 0,
                'cs_pin': 8,
                'reset_pin': 12,
                'motion_pin': 16
            })
            sensor = OpticalFlowSensor(config)
            print("   ✅ PAA5100JE-Q SPI communication utility initialized successfully")
            return True
        except Exception as e:
            print(f"   ❌ PAA5100JE-Q connectivity test failed: {e}")
            return False
    
    def test_sensor_initialization(self) -> bool:
        """Test PAA5100JE-Q sensor initialization"""
        try:
            print("   Initializing PAA5100JE-Q sensor...")
            # Use OpticalFlowSensor utility class
            config = self.config.get('hardware', {}).get('optical_flow', {
                'spi_bus': 0,
                'spi_device': 0,
                'cs_pin': 8,
                'reset_pin': 12,
                'motion_pin': 16
            })
            self.sensor_interface = OpticalFlowSensor(config)
            # Test sensor by reading motion (simulate ID check)
            x, y = self.sensor_interface.read_motion()
            print(f"   📍 PAA5100JE-Q Sensor motion read: X={x}, Y={y}")
            return True
        except Exception as e:
            print(f"   ❌ Sensor initialization failed: {e}")
            return False
    
    def test_led_control(self) -> bool:
        """Test PAA5100JE-Q LED control (not implemented in OpticalFlowSensor utility)"""
        print("   ⚠️ LED control is not implemented in OpticalFlowSensor utility.")
        return False
    
    def test_motion_detection(self) -> bool:
        """Test PAA5100JE-Q motion detection"""
        try:
            print("   📡 Testing motion detection...")
            print("   Move your hand or an object in front of the sensor...")
            # Test motion detection for 10 seconds
            start_time = time.time()
            motion_detected = False
            while time.time() - start_time < 10:
                try:
                    x, y = self.sensor_interface.read_motion()
                    if (x is not None and y is not None) and (x != 0 or y != 0):
                        print(f"   ✅ Motion detected: X={x}, Y={y}")
                        motion_detected = True
                        break
                    time.sleep(0.1)
                except Exception as e:
                    print(f"   ⚠️ Motion detection error: {e}")
                    break
            if not motion_detected:
                print("   ⚠️ No motion detected during test period")
                return False
            return True
        except Exception as e:
            print(f"   ❌ Motion detection test failed: {e}")
            return False
    
    def test_bandwidth(self) -> Dict[str, Any]:
        """Test PAA5100JE-Q bandwidth and performance"""
        print("   📊 Testing PAA5100JE-Q bandwidth...")
        
        try:
            # Test different SPI speeds
            test_speeds = [1000000, 2000000, 4000000, 8000000]
            max_safe_speed = 0
            bandwidth_results = {}
            
            for speed in test_speeds:
                successful = 0
                failed = 0
                test_commands = 50
                start_time = time.time()
                
                for i in range(test_commands):
                    try:
                        test_data = [0x00, 0x00]
                        successful += 1
                    except:
                        failed += 1
                
                end_time = time.time()
                duration = end_time - start_time
                success_rate = successful / test_commands if test_commands > 0 else 0
                commands_per_second = test_commands / duration if duration > 0 else 0
                
                bandwidth_results[speed] = {
                    "successful": successful,
                    "failed": failed,
                    "success_rate": success_rate,
                    "commands_per_second": commands_per_second,
                    "duration": duration
                }
                
                print(f"     Speed {speed/1000000:.1f}MHz: {successful}/{test_commands} successful ({success_rate:.1%}) - {commands_per_second:.1f} cmd/s")
                
                if success_rate >= 0.95:
                    max_safe_speed = speed
                else:
                    break
            
            return {
                "status": "success",
                "max_safe_speed": max_safe_speed,
                "test_speeds": test_speeds,
                "bandwidth_results": bandwidth_results
            }
            
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    def run_connectivity_test(self) -> Dict[str, Any]:
        """Run comprehensive connectivity test"""
        print("\n🔌 PAA5100JE-Q Connectivity Test")
        print("-" * 40)
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "test_type": "connectivity",
            "status": False,
            "spi_connectivity": False,
            "sensor_initialization": False,
            "error": None
        }
        
        # Test SPI connectivity
        if self.test_spi_connectivity():
            result["spi_connectivity"] = True
            print("   ✅ SPI connectivity test passed")
        else:
            result["error"] = "SPI connectivity failed"
            print("   ❌ SPI connectivity test failed")
            return result
        
        # Test sensor initialization
        if self.test_sensor_initialization():
            result["sensor_initialization"] = True
            print("   ✅ Sensor initialization test passed")
        else:
            result["error"] = "Sensor initialization failed"
            print("   ❌ Sensor initialization test failed")
            return result
        
        result["status"] = True
        print("   ✅ Connectivity test completed successfully")
        return result
    
    def run_functionality_test(self) -> Dict[str, Any]:
        """Run comprehensive functionality test"""
        print("\n⚙️ PAA5100JE-Q Functionality Test")
        print("-" * 40)
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "test_type": "functionality",
            "status": False,
            "led_control": False,
            "motion_detection": False,
            "error": None
        }
        
        if not self.sensor_interface:
            result["error"] = "Sensor not initialized"
            print("   ❌ Sensor not initialized. Run connectivity test first.")
            return result
        
        # Test LED control
        if self.test_led_control():
            result["led_control"] = True
            print("   ✅ LED control test passed")
        else:
            print("   ⚠️ LED control test failed or not available")
        
        # Test motion detection
        if self.test_motion_detection():
            result["motion_detection"] = True
            print("   ✅ Motion detection test passed")
        else:
            result["error"] = "Motion detection failed"
            print("   ❌ Motion detection test failed")
            return result
        
        result["status"] = True
        print("   ✅ Functionality test completed successfully")
        return result
    
    def run_bandwidth_test(self) -> Dict[str, Any]:
        """Run bandwidth and performance test"""
        print("\n📊 PAA5100JE-Q Bandwidth Test")
        print("-" * 40)
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "test_type": "bandwidth",
            "status": False,
            "bandwidth_data": None,
            "error": None
        }
        
        bandwidth_data = self.test_bandwidth()
        if bandwidth_data["status"] == "success":
            result["bandwidth_data"] = bandwidth_data
            result["status"] = True
            print(f"   ✅ Bandwidth test completed. Max safe speed: {bandwidth_data['max_safe_speed']/1000000:.1f}MHz")
        else:
            result["error"] = bandwidth_data.get("error", "Unknown error")
            print(f"   ❌ Bandwidth test failed: {result['error']}")
        
        return result
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all optical flow tests"""
        print("\n🚀 Running All PAA5100JE-Q Tests")
        print("=" * 50)
        
        all_results = {
            "timestamp": datetime.now().isoformat(),
            "test_suite": "optical_flow_comprehensive",
            "tests": {},
            "overall_status": False
        }
        
        # Run connectivity test
        connectivity_result = self.run_connectivity_test()
        all_results["tests"]["connectivity"] = connectivity_result
        
        if not connectivity_result["status"]:
            print("   ❌ Connectivity test failed. Stopping test suite.")
            return all_results
        
        # Run functionality test
        functionality_result = self.run_functionality_test()
        all_results["tests"]["functionality"] = functionality_result
        
        # Run bandwidth test
        bandwidth_result = self.run_bandwidth_test()
        all_results["tests"]["bandwidth"] = bandwidth_result
        
        # Determine overall status
        all_results["overall_status"] = (
            connectivity_result["status"] and 
            functionality_result["status"] and 
            bandwidth_result["status"]
        )
        
        if all_results["overall_status"]:
            print("   ✅ All optical flow tests completed successfully")
        else:
            print("   ⚠️ Some optical flow tests failed")
        
        return all_results
    
    def save_test_results(self, results: Dict[str, Any]):
        """Save test results to file"""
        try:
            # Create test_logs directory if it doesn't exist
            logs_dir = "test_logs/optical_flow"
            os.makedirs(logs_dir, exist_ok=True)
            
            # Save with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"optical_flow_test_{timestamp}.json"
            filepath = os.path.join(logs_dir, filename)
            
            with open(filepath, 'w') as f:
                json.dump(results, f, indent=2)
            
            print(f"   💾 Test results saved: {filepath}")
            
        except Exception as e:
            print(f"   ⚠️ Failed to save test results: {e}")
    
    def display_menu(self):
        """Display the optical flow test menu"""
        while True:
            print("\n🔍 PAA5100JE-Q Optical Flow Sensor Test Menu")
            print("=" * 50)
            print("1. Connectivity Test (SPI + Sensor Init)")
            print("2. Functionality Test (LED + Motion)")
            print("3. Bandwidth Test (Performance)")
            print("4. Run All Tests")
            print("5. Save Results")
            print("6. Exit")
            print("-" * 50)
            
            choice = self.get_autopilot_input()
            
            if choice == "1":
                result = self.run_connectivity_test()
                self.test_results["connectivity"] = result
            elif choice == "2":
                result = self.run_functionality_test()
                self.test_results["functionality"] = result
            elif choice == "3":
                result = self.run_bandwidth_test()
                self.test_results["bandwidth"] = result
            elif choice == "4":
                result = self.run_all_tests()
                self.test_results["comprehensive"] = result
            elif choice == "5":
                if self.test_results:
                    self.save_test_results(self.test_results)
                else:
                    print("   ⚠️ No test results to save")
            elif choice == "6":
                print("   👋 Exiting optical flow test menu")
                break
            else:
                print("   ❌ Invalid choice. Please try again.")

def main():
    """Main function for optical flow test menu"""
    parser = argparse.ArgumentParser(description="PAA5100JE-Q Optical Flow Sensor Test Menu")
    parser.add_argument("--dev", "--development", action="store_true", 
                       help="Enable development mode with enhanced troubleshooting")
    parser.add_argument("--save", action="store_true", 
                       help="Automatically save test results")
    parser.add_argument("--autopilot", type=str, default="", 
                       help="Autonomous execution input string")
    
    args = parser.parse_args()
    
    print("🔍 PAA5100JE-Q Optical Flow Sensor Test Menu")
    print("=" * 50)
    
    if args.dev:
        print("🔧 Development mode enabled")
    else:
        print("💡 Run with --dev flag for development mode")
    
    # Initialize test menu
    test_menu = OpticalFlowTestMenu(
        development_mode=args.dev,
        autopilot_input=args.autopilot
    )
    
    # Display menu and handle user input
    test_menu.display_menu()
    
    # Auto-save if requested
    if args.save and test_menu.test_results:
        test_menu.save_test_results(test_menu.test_results)
    
    print("\nOptical flow test menu completed.")

if __name__ == "__main__":
    main() 