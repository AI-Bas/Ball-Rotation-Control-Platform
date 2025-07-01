#!/usr/bin/env python3
"""
Connectivity Test Module
Performs system-wide scan of connections and communication protocols.
Light and simple starting point for all modules to use as reference.
"""

import os
import sys
import time
import json
import subprocess
from typing import Dict, Any, Optional, List
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from utils.roboclaw_interface import RoboClawInterface
from utils.power_sensor import PowerSensor
from utils.optical_flow_sensor import OpticalFlowSensor
from utils.maker_pi_interface import MakerPiInterface
from utils.autopilot_manager import create_autopilot_manager, set_autopilot_manager, get_autopilot_input


class ConnectivityTest:
    """System-wide connectivity testing for all hardware modules."""
    
    def __init__(self, development_mode: bool = False, autopilot_mode: bool = False, autopilot_input: str = ""):
        self.development_mode = development_mode
        self.autopilot_mode = autopilot_mode
        self.autopilot_input = autopilot_input
        self.autopilot_manager = create_autopilot_manager("connectivity_test", autopilot_input)
        set_autopilot_manager(self.autopilot_manager)
        self.results = {}
        self.config = self.load_platform_config()
        
    def load_platform_config(self) -> Dict[str, Any]:
        """Load platform configuration."""
        config_path = Path(__file__).parent.parent / "config" / "platform_config.json"
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
            return {}
    
    def detect_roboclaw_ports(self) -> List[str]:
        """Detect available RoboClaw ports."""
        ports = []
        
        # Linux detection
        if os.name == 'posix':
            try:
                result = subprocess.run(['ls', '/dev/ttyACM*'], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    ports.extend(result.stdout.strip().split('\n'))
            except Exception:
                pass
                
            try:
                result = subprocess.run(['ls', '/dev/ttyUSB*'], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    ports.extend(result.stdout.strip().split('\n'))
            except Exception:
                pass
        
        # Windows detection
        else:
            for i in range(10):
                port = f"COM{i}"
                if os.path.exists(port):
                    ports.append(port)
        
        return [p for p in ports if p]
    
    def test_roboclaw_connectivity(self) -> Dict[str, Any]:
        """Test RoboClaw connectivity."""
        result = {
            "status": False,
            "ports_detected": [],
            "controllers_found": 0,
            "details": {}
        }
        
        try:
            ports = self.detect_roboclaw_ports()
            result["ports_detected"] = ports
            
            # Use RoboClawInterface with proper initialization
            roboclaw = RoboClawInterface(use_dual_controllers=False, autopilot_mode=self.autopilot_mode)
            if roboclaw.connect():
                result["controllers_found"] = 1
                result["status"] = True
                result["details"]["roboclaw"] = {
                    "status": "connected",
                    "controllers": "RC1"
                }
            else:
                result["details"]["roboclaw"] = {
                    "status": "failed",
                    "error": "connection test failed"
                }
            
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def test_ina219_connectivity(self) -> Dict[str, Any]:
        """Test INA219 connectivity."""
        result = {
            "status": False,
            "sensors_found": 0,
            "addresses": [],
            "details": {}
        }
        
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
                        result["sensors_found"] += 1
                        result["addresses"].append(hex(addr))
                        result["details"][hex(addr)] = {
                            "status": "connected",
                            "voltage": voltage,
                            "current": sensor.get_current_mA()
                        }
                    else:
                        result["details"][hex(addr)] = {
                            "status": "failed",
                            "error": "no voltage reading"
                        }
                except Exception as e:
                    result["details"][hex(addr)] = {
                        "status": "error",
                        "error": str(e)
                    }
            
            result["status"] = result["sensors_found"] > 0
            
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def test_optical_flow_connectivity(self) -> Dict[str, Any]:
        """Test PAA5100JE-Q optical flow sensor connectivity."""
        result = {
            "status": False,
            "sensor_detected": False,
            "details": {}
        }
        
        try:
            # Create config for OpticalFlowSensor
            sensor_config = {
                'spi_bus': 0,
                'spi_device': 0,
                'cs_pin': 8,
                'reset_pin': 12,
                'motion_pin': 16
            }
            
            sensor = OpticalFlowSensor(sensor_config)
            
            # Test connection by reading motion
            x_vel, y_vel = sensor.read_motion()
            if x_vel is not None and y_vel is not None:
                result["sensor_detected"] = True
                result["status"] = True
                result["details"] = {
                    "status": "connected",
                    "motion_x": x_vel,
                    "motion_y": y_vel
                }
            else:
                result["details"] = {
                    "status": "failed",
                    "error": "no motion reading"
                }
                
        except Exception as e:
            result["details"] = {
                "status": "error",
                "error": str(e)
            }
        
        return result
    
    def test_maker_pi_connectivity(self) -> Dict[str, Any]:
        """Test Maker Pi RP2040 connectivity."""
        result = {
            "status": False,
            "usb_detected": False,
            "uart_detected": False,
            "details": {}
        }
        
        try:
            # Create config for MakerPiInterface
            maker_pi_config = {
                'port': '/dev/ttyACM0',
                'baudrate': 115200,
                'modules': {
                    'experimental_sensors': {'enabled': True},
                    'displays': {'enabled': True},
                    'io_modules': {'enabled': True}
                },
                'circuitpython_detection': {
                    'backup_directory': 'platform_control/tests/maker_pi_settings_backup'
                }
            }
            
            maker_pi = MakerPiInterface(maker_pi_config)
            
            # Test USB connection (CircuitPython drive detection)
            usb_drives = maker_pi.detect_circuitpython_drives()
            if usb_drives:
                result["usb_detected"] = True
                result["details"]["usb"] = {
                    "status": "connected",
                    "drives": list(usb_drives.keys())
                }
            
            # Test UART connection
            if maker_pi.connect():
                result["uart_detected"] = True
                result["details"]["uart"] = {
                    "status": "connected",
                    "port": maker_pi.port
                }
            
            result["status"] = result["usb_detected"] or result["uart_detected"]
            
        except Exception as e:
            result["details"]["error"] = str(e)
        
        return result
    
    def run_connectivity_tests(self) -> Dict[str, Any]:
        """Run all connectivity tests."""
        print("🔌 Running System Connectivity Tests...")
        
        results = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "tests": {}
        }
        
        # Test each hardware module
        results["tests"]["roboclaw"] = self.test_roboclaw_connectivity()
        results["tests"]["ina219"] = self.test_ina219_connectivity()
        results["tests"]["optical_flow"] = self.test_optical_flow_connectivity()
        results["tests"]["maker_pi"] = self.test_maker_pi_connectivity()
        
        # Summary
        total_modules = len(results["tests"])
        connected_modules = sum(1 for test in results["tests"].values() if test.get("status", False))
        
        results["summary"] = {
            "total_modules": total_modules,
            "connected_modules": connected_modules,
            "success_rate": connected_modules / total_modules if total_modules > 0 else 0
        }
        
        # Display results
        self.display_results(results)
        
        return results
    
    def display_results(self, results: Dict[str, Any]):
        """Display connectivity test results."""
        print("\n" + "="*60)
        print("🔌 CONNECTIVITY TEST RESULTS")
        print("="*60)
        
        for module, test_result in results["tests"].items():
            status = "✅" if test_result.get("status", False) else "❌"
            print(f"{status} {module.upper()}: {test_result.get('status', False)}")
            
            if self.development_mode and not test_result.get("status", False):
                print(f"   Details: {test_result.get('details', {})}")
        
        print("\n" + "-"*60)
        summary = results["summary"]
        print(f"📊 SUMMARY: {summary['connected_modules']}/{summary['total_modules']} modules connected")
        print(f"   Success Rate: {summary['success_rate']:.1%}")
        print("="*60)
    
    def save_results(self, results: Dict[str, Any]) -> bool:
        """Save connectivity test results."""
        try:
            log_dir = Path(__file__).parent / "test_logs" / "connectivity"
            log_dir.mkdir(exist_ok=True)
            
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"connectivity_test_{timestamp}.json"
            filepath = log_dir / filename
            
            with open(filepath, 'w') as f:
                json.dump(results, f, indent=2)
            
            print(f"💾 Results saved to: {filepath}")
            return True
            
        except Exception as e:
            print(f"❌ Error saving results: {e}")
            return False


def main():
    """Main function for standalone connectivity testing."""
    import argparse
    
    parser = argparse.ArgumentParser(description="System Connectivity Tests")
    parser.add_argument("--dev", action="store_true", help="Enable development mode")
    parser.add_argument("--save", action="store_true", help="Save results to file")
    parser.add_argument("--autopilot", type=str, help="Autonomous execution string")
    
    args = parser.parse_args()
    
    # Create connectivity tester
    autopilot_mode = args.autopilot is not None
    tester = ConnectivityTest(development_mode=args.dev, autopilot_mode=autopilot_mode, autopilot_input=args.autopilot)
    
    # Run tests
    results = tester.run_connectivity_tests()
    
    # Save results if requested
    if args.save:
        tester.save_results(results)
    
    # Return exit code based on success
    success_rate = results["summary"]["success_rate"]
    exit_code = 0 if success_rate > 0.5 else 1
    
    return exit_code


if __name__ == "__main__":
    exit(main()) 