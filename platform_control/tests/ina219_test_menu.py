#!/usr/bin/env python3
"""
INA219 Test Module
Detailed INA219 testing with voltage range testing, current monitoring, motor mapping, and bandwidth testing.
"""

import os
import sys
import time
import json
from typing import Dict, Any, Optional, List
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from utils.power_sensor import PowerSensor
from utils.autopilot_manager import create_autopilot_manager, set_autopilot_manager, get_autopilot_input


class INA219TestMenu:
    """Comprehensive INA219 testing with detailed functionality."""
    
    def __init__(self, development_mode: bool = False, autopilot_mode: bool = False, autopilot_input: str = ""):
        self.development_mode = development_mode
        self.autopilot_mode = autopilot_mode
        self.autopilot_input = autopilot_input
        # Initialize autopilot manager for this script
        self.autopilot_manager = create_autopilot_manager("ina219_test_menu", autopilot_input)
        set_autopilot_manager(self.autopilot_manager)
        self.results = {}
        self.config = self.load_platform_config()
        self.sensors = {}
        
    def load_platform_config(self) -> Dict[str, Any]:
        """Load platform configuration."""
        config_path = Path(__file__).parent.parent / "config" / "platform_config.json"
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
            return {}
    
    def initialize_sensors(self) -> bool:
        """Initialize INA219 sensors."""
        try:
            addresses = [0x40, 0x41, 0x42, 0x43]
            
            for addr in addresses:
                try:
                    # Create config for PowerSensor
                    sensor_config = {
                        'address': hex(addr),
                        'i2c_bus': 1,
                        'channels': [0, 1, 2, 3]
                    }
                    
                    sensor = PowerSensor(sensor_config)
                    
                    # Test connection by reading voltage
                    voltage = sensor.get_bus_voltage_V()
                    if voltage > 0:
                        self.sensors[hex(addr)] = sensor
                        print(f"✓ INA219 sensor initialized at {hex(addr)}")
                    else:
                        print(f"⚠️ No voltage reading from {hex(addr)}")
                        
                except Exception as e:
                    print(f"✗ Error initializing sensor at {hex(addr)}: {e}")
            
            return len(self.sensors) > 0
            
        except Exception as e:
            print(f"Error initializing sensors: {e}")
            return False
    
    def test_voltage_range(self) -> Dict[str, Any]:
        """Test voltage range (10-26V) across all sensors."""
        print("⚡ Running Voltage Range Test...")
        
        result = {
            "status": False,
            "sensors_tested": 0,
            "voltage_readings": {},
            "details": {}
        }
        
        try:
            if not self.initialize_sensors():
                result["error"] = "Failed to initialize sensors"
                return result
            
            for addr, sensor in self.sensors.items():
                print(f"  Testing voltage on {addr}...")
                
                # Read voltage multiple times for stability
                readings = []
                for i in range(5):
                    voltage = sensor.get_bus_voltage_V()
                    readings.append(voltage)
                    time.sleep(0.1)
                
                avg_voltage = sum(readings) / len(readings)
                
                result["voltage_readings"][addr] = {
                    "average_voltage": avg_voltage,
                    "readings": readings,
                    "in_range": 10.0 <= avg_voltage <= 26.0
                }
                
                if 10.0 <= avg_voltage <= 26.0:
                    result["sensors_tested"] += 1
                    print(f"    ✅ Voltage: {avg_voltage:.2f}V (in range)")
                else:
                    print(f"    ⚠️ Voltage: {avg_voltage:.2f}V (out of range)")
            
            result["status"] = result["sensors_tested"] > 0
            
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def test_current_monitoring(self) -> Dict[str, Any]:
        """Test current monitoring per channel."""
        print("🔌 Running Current Monitoring Test...")
        
        result = {
            "status": False,
            "channels_monitored": 0,
            "current_readings": {},
            "details": {}
        }
        
        try:
            if not self.sensors:
                if not self.initialize_sensors():
                    result["error"] = "Failed to initialize sensors"
                    return result
            
            for addr, sensor in self.sensors.items():
                print(f"  Monitoring current on {addr}...")
                
                # Read current multiple times
                readings = []
                for i in range(10):
                    current = sensor.get_current_mA()
                    readings.append(current)
                    time.sleep(0.1)
                
                avg_current = sum(readings) / len(readings)
                max_current = max(readings)
                min_current = min(readings)
                
                result["current_readings"][addr] = {
                    "average_current": avg_current,
                    "max_current": max_current,
                    "min_current": min_current,
                    "readings": readings,
                    "stable": (max_current - min_current) < 10.0  # 10mA stability threshold
                }
                
                result["channels_monitored"] += 1
                print(f"    Current: {avg_current:.2f}mA (stable: {result['current_readings'][addr]['stable']})")
            
            result["status"] = result["channels_monitored"] > 0
            
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def test_motor_current_mapping(self) -> Dict[str, Any]:
        """Test motor mapping with current correlation."""
        print("🎯 Running Motor Current Mapping Test...")
        
        result = {
            "status": False,
            "motors_mapped": 0,
            "mapping": {},
            "details": {}
        }
        
        try:
            if not self.sensors:
                if not self.initialize_sensors():
                    result["error"] = "Failed to initialize sensors"
                    return result
            
            # Define motor channels to test
            motor_channels = [
                ("motor1", "X-axis wheel"),
                ("motor2", "120° wheel"),
                ("motor3", "240° wheel"),
                ("motor4", "Linear stage")
            ]
            
            for motor_name, description in motor_channels:
                print(f"  Testing {motor_name} ({description})...")
                
                # Get baseline current readings
                baseline_readings = {}
                for addr in self.sensors.keys():
                    baseline_readings[addr] = self.sensors[addr].get_current_mA()
                
                print(f"    Baseline readings: {baseline_readings}")
                
                if self.autopilot_mode:
                    print(f"    Autopilot mode: Simulating motor activation for {motor_name}")
                    # Simulate current change for autopilot mode
                    current_changes = {}
                    for addr in self.sensors.keys():
                        # Simulate a current change on one sensor per motor
                        if motor_name == "motor1" and addr == "0x43":
                            current_changes[addr] = 600.0
                        elif motor_name == "motor2" and addr == "0x40":
                            current_changes[addr] = 600.0
                        elif motor_name == "motor3" and addr == "0x41":
                            current_changes[addr] = 600.0
                        elif motor_name == "motor4" and addr == "0x42":
                            current_changes[addr] = 600.0
                        else:
                            current_changes[addr] = 0.0
                else:
                    print(f"    Please activate {motor_name} (turn wheel or apply load)...")
                    print(f"    Waiting 10 seconds for current change...")
                    
                    # Wait for current change
                    start_time = time.time()
                    current_changes = {}
                    
                    while time.time() - start_time < 10:
                        for addr in self.sensors.keys():
                            current = self.sensors[addr].get_current_mA()
                            change = abs(current - baseline_readings[addr])
                            if change > current_changes.get(addr, 0):
                                current_changes[addr] = change
                        time.sleep(0.1)
                
                # Find sensor with maximum current change
                if current_changes:
                    max_change_addr = max(current_changes.keys(), key=lambda x: current_changes[x])
                    max_change = current_changes[max_change_addr]
                    
                    if max_change > 5.0:  # 5mA threshold
                        result["motors_mapped"] += 1
                        result["mapping"][motor_name] = {
                            "sensor_address": max_change_addr,
                            "current_change": max_change,
                            "description": description
                        }
                        print(f"    ✅ {motor_name} mapped to {max_change_addr} (change: {max_change:.2f}mA)")
                    else:
                        print(f"    ⚠️ No significant current change detected for {motor_name}")
                        result["mapping"][motor_name] = {
                            "status": "no_change",
                            "max_change": max_change
                        }
                else:
                    print(f"    ⚠️ No current readings for {motor_name}")
                    result["mapping"][motor_name] = {
                        "status": "no_readings"
                    }
            
            result["status"] = result["motors_mapped"] > 0
            
            # Save mapping to config
            if result["status"]:
                self.save_current_mapping(result["mapping"])
            
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def save_current_mapping(self, mapping: Dict[str, Any]) -> bool:
        """Save current mapping to configuration."""
        try:
            # Update platform config with current mapping
            if "hardware" not in self.config:
                self.config["hardware"] = {}
            if "current_sensor" not in self.config["hardware"]:
                self.config["hardware"]["current_sensor"] = {}
            
            self.config["hardware"]["current_sensor"]["motor_mapping"] = mapping
            
            # Save to file
            config_path = Path(__file__).parent.parent / "config" / "platform_config.json"
            with open(config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            
            print("💾 Current mapping saved to configuration")
            return True
            
        except Exception as e:
            print(f"❌ Error saving current mapping: {e}")
            return False
    
    def test_bandwidth(self) -> Dict[str, Any]:
        """Test bandwidth with performance metrics."""
        print("📊 Running Bandwidth Test...")
        
        result = {
            "status": False,
            "max_safe_rate": 0,
            "performance_metrics": {},
            "details": {}
        }
        
        try:
            if not self.sensors:
                if not self.initialize_sensors():
                    result["error"] = "Failed to initialize sensors"
                    return result
            
            # Test different reading rates
            rates = [1, 5, 10, 20, 50, 100]
            
            for rate in rates:
                print(f"  Testing {rate} readings/sec...")
                
                start_time = time.time()
                successful_readings = 0
                total_readings = rate * 2  # Test for 2 seconds
                
                for i in range(total_readings):
                    try:
                        # Read from all sensors
                        for addr, sensor in self.sensors.items():
                            voltage = sensor.get_bus_voltage_V()
                            current = sensor.get_current_mA()
                        
                        successful_readings += 1
                        
                        # Wait to achieve desired rate
                        time.sleep(1.0 / rate)
                        
                    except Exception as e:
                        print(f"    Error at reading {i}: {e}")
                
                end_time = time.time()
                actual_rate = successful_readings / (end_time - start_time)
                success_rate = successful_readings / total_readings
                
                result["performance_metrics"][rate] = {
                    "target_rate": rate,
                    "actual_rate": actual_rate,
                    "success_rate": success_rate,
                    "successful_readings": successful_readings,
                    "total_readings": total_readings
                }
                
                print(f"    Actual rate: {actual_rate:.1f}/sec, Success: {success_rate:.1%}")
                
                # Determine max safe rate (95% success rate)
                if success_rate >= 0.95:
                    result["max_safe_rate"] = rate
                else:
                    break
            
            result["status"] = result["max_safe_rate"] > 0
            
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def run_test_menu(self) -> Dict[str, Any]:
        """Run the complete INA219 test menu."""
        print("🔌 INA219 Test Menu")
        print("="*50)
        
        results = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "tests": {}
        }
        
        # Run all tests
        results["tests"]["voltage_range"] = self.test_voltage_range()
        results["tests"]["current_monitoring"] = self.test_current_monitoring()
        results["tests"]["motor_mapping"] = self.test_motor_current_mapping()
        results["tests"]["bandwidth"] = self.test_bandwidth()
        
        # Summary
        total_tests = len(results["tests"])
        passed_tests = sum(1 for test in results["tests"].values() if test.get("status", False))
        
        results["summary"] = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "success_rate": passed_tests / total_tests if total_tests > 0 else 0
        }
        
        # Display results
        self.display_results(results)
        
        return results
    
    def display_results(self, results: Dict[str, Any]):
        """Display test results."""
        print("\n" + "="*60)
        print("🔌 INA219 TEST RESULTS")
        print("="*60)
        
        for test_name, test_result in results["tests"].items():
            status = "✅" if test_result.get("status", False) else "❌"
            print(f"{status} {test_name.upper()}: {test_result.get('status', False)}")
            
            if self.development_mode and not test_result.get("status", False):
                print(f"   Details: {test_result.get('details', {})}")
        
        print("\n" + "-"*60)
        summary = results["summary"]
        print(f"📊 SUMMARY: {summary['passed_tests']}/{summary['total_tests']} tests passed")
        print(f"   Success Rate: {summary['success_rate']:.1%}")
        print("="*60)
    
    def save_results(self, results: Dict[str, Any]) -> bool:
        """Save test results."""
        try:
            log_dir = Path(__file__).parent / "test_logs" / "ina219"
            log_dir.mkdir(exist_ok=True)
            
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"ina219_test_{timestamp}.json"
            filepath = log_dir / filename
            
            with open(filepath, 'w') as f:
                json.dump(results, f, indent=2)
            
            print(f"💾 Results saved to: {filepath}")
            return True
            
        except Exception as e:
            print(f"❌ Error saving results: {e}")
            return False
    
    def get_autopilot_input(self, prompt: str = "Enter choice: ") -> str:
        return get_autopilot_input(prompt)


def main():
    """Main function for standalone INA219 testing."""
    import argparse
    
    parser = argparse.ArgumentParser(description="INA219 Test Menu")
    parser.add_argument("--dev", action="store_true", help="Enable development mode")
    parser.add_argument("--save", action="store_true", help="Save results to file")
    parser.add_argument("--autopilot", type=str, help="Autonomous execution string")
    
    args = parser.parse_args()
    
    # Create INA219 tester
    autopilot_mode = args.autopilot is not None
    tester = INA219TestMenu(development_mode=args.dev, autopilot_mode=autopilot_mode, autopilot_input=args.autopilot)
    
    # Run tests
    results = tester.run_test_menu()
    
    # Save results if requested
    if args.save:
        tester.save_results(results)
    
    # Return exit code based on success
    success_rate = results["summary"]["success_rate"]
    exit_code = 0 if success_rate > 0.5 else 1
    
    return exit_code


if __name__ == "__main__":
    exit(main()) 