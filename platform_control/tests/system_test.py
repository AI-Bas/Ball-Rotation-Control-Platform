#!/usr/bin/env python3
"""
System Test Suite - Central Testing Orchestrator
Modular testing system for Ball Handler Test Platform

This is the central controller that orchestrates all testing modules:
1. Connectivity Tests (connectivity_test.py)
2. RoboClaw Motor Testing (roboclaw_test.py)
3. INA219 Power Sensor Testing (ina219_test_menu.py)
4. Optical Flow Sensor Testing (optical_flow_test_menu.py)
5. Maker Pi Experimental Module Testing (maker_pi_tests.py)
6. Calibration and Characterization Tests (calibration_test.py)
7. Performance Testing (performance_test.py)
8. Code Integration Testing (code_integration_test.py)

Each module is maintained through hardware abstraction layers and follows
the system architecture defined in system_design_architecture.yaml
"""

import sys
import os
import json
import time
import subprocess
import platform
from datetime import datetime
from typing import Dict, Any, Optional, List
import signal
# Add the parent directory to sys.path to import from utils
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.autopilot_manager import create_autopilot_manager, set_autopilot_manager, get_autopilot_input

class SystemTestOrchestrator:
    """Central system test orchestrator with module integration"""
    
    def __init__(self, development_mode: bool = False, autopilot_input: str = ""):
        """Initialize the system test orchestrator"""
        self.development_mode = development_mode
        self.autopilot_input = autopilot_input
        # Initialize autopilot manager for this script
        self.autopilot_manager = create_autopilot_manager("system_test", autopilot_input)
        set_autopilot_manager(self.autopilot_manager)
        self.test_results = {
            "timestamp": datetime.now().isoformat(),
            "development_mode": development_mode,
            "orchestrator_version": "3.0",
            "module_results": {},
            "system_status": "initialized",
            "errors": [],
            "performance_metrics": {},
            "execution_summary": {}
        }
        self.platform_config = self.load_platform_config()
        
        # Signal handling for graceful exit
        signal.signal(signal.SIGINT, self._signal_handler)
        
        if development_mode:
            print("🔧 DEVELOPMENT MODE ENABLED - Enhanced troubleshooting and automation")

    def _signal_handler(self, signum, frame):
        """Handle Ctrl+C gracefully"""
        print("\n\n⚠️  Interrupt received. Gracefully shutting down...")
        self.save_test_results()
        print("Test results saved. Exiting...")
        sys.exit(0)

    def load_platform_config(self) -> Dict[str, Any]:
        """Load platform configuration"""
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'platform_config.json')
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load platform_config.json: {e}")
            return {}

    def log_error(self, module: str, error: str, context: str = ""):
        """Log an error during testing"""
        error_entry = {
            "module": module,
            "error": error,
            "context": context,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results["errors"].append(error_entry)
        
        if self.development_mode:
            print(f"   ❌ ERROR in {module}: {error}")
            if context:
                print(f"      Context: {context}")

    def run_module_test(self, module_name: str, module_path: str, autopilot_input: str = "") -> Dict[str, Any]:
        """Run a specific test module and capture results"""
        print(f"\n{'='*60}")
        print(f"🔧 RUNNING {module_name.upper()} TEST MODULE")
        print(f"{'='*60}")
        
        start_time = time.time()
        result = {
            "module": module_name,
            "start_time": datetime.now().isoformat(),
            "status": "unknown",
            "exit_code": -1,
            "output": "",
            "error": "",
            "duration": 0
        }
        
        try:
            # Build command with development mode and autopilot
            cmd = [
                sys.executable, module_path,
                "--dev" if self.development_mode else "",
                "--save",
                f"--autopilot", autopilot_input
            ]
            cmd = [arg for arg in cmd if arg]  # Remove empty strings
            
            print(f"   Executing: {' '.join(cmd)}")
            
            # Run the module
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            result["exit_code"] = process.returncode
            result["output"] = process.stdout
            result["error"] = process.stderr
            result["duration"] = time.time() - start_time
            
            if process.returncode == 0:
                result["status"] = "success"
                print(f"   ✅ {module_name} completed successfully")
            else:
                result["status"] = "failed"
                print(f"   ❌ {module_name} failed with exit code {process.returncode}")
                if process.stderr:
                    print(f"      Error: {process.stderr.strip()}")
            
        except subprocess.TimeoutExpired:
            result["status"] = "timeout"
            result["error"] = "Module execution timed out after 5 minutes"
            print(f"   ⏰ {module_name} timed out")
            self.log_error(module_name, "Execution timeout", "Module took too long to complete")
            
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            print(f"   💥 {module_name} encountered an error: {e}")
            self.log_error(module_name, str(e), "Module execution failed")
        
        return result

    def run_connectivity_tests(self) -> bool:
        """Run connectivity test module"""
        module_path = os.path.join(os.path.dirname(__file__), "connectivity_test.py")
        result = self.run_module_test("Connectivity", module_path, "1")
        self.test_results["module_results"]["connectivity"] = result
        return result["status"] == "success"

    def run_roboclaw_tests(self) -> bool:
        """Run RoboClaw test module"""
        module_path = os.path.join(os.path.dirname(__file__), "roboclaw_test.py")
        result = self.run_module_test("RoboClaw", module_path, "1")
        self.test_results["module_results"]["roboclaw"] = result
        return result["status"] == "success"

    def run_ina219_tests(self) -> bool:
        """Run INA219 test module"""
        module_path = os.path.join(os.path.dirname(__file__), "ina219_test_menu.py")
        result = self.run_module_test("INA219", module_path, "1")
        self.test_results["module_results"]["ina219"] = result
        return result["status"] == "success"

    def run_optical_flow_tests(self) -> bool:
        """Run optical flow test module"""
        module_path = os.path.join(os.path.dirname(__file__), "optical_flow_test_menu.py")
        result = self.run_module_test("Optical Flow", module_path, "1")
        self.test_results["module_results"]["optical_flow"] = result
        return result["status"] == "success"

    def run_maker_pi_tests(self) -> bool:
        """Run Maker Pi test module"""
        module_path = os.path.join(os.path.dirname(__file__), "maker_pi_tests.py")
        result = self.run_module_test("Maker Pi", module_path, "1")
        self.test_results["module_results"]["maker_pi"] = result
        return result["status"] == "success"

    def run_calibration_tests(self) -> bool:
        """Run calibration test module"""
        module_path = os.path.join(os.path.dirname(__file__), "calibration_test.py")
        result = self.run_module_test("Calibration", module_path, "1")
        self.test_results["module_results"]["calibration"] = result
        return result["status"] == "success"

    def run_performance_tests(self) -> bool:
        """Run performance test module"""
        module_path = os.path.join(os.path.dirname(__file__), "performance_test.py")
        result = self.run_module_test("Performance", module_path, "1")
        self.test_results["module_results"]["performance"] = result
        return result["status"] == "success"

    def run_code_integration_tests(self) -> bool:
        """Run code integration test module"""
        module_path = os.path.join(os.path.dirname(__file__), "code_integration_test.py")
        result = self.run_module_test("Code Integration", module_path, "1")
        self.test_results["module_results"]["code_integration"] = result
        return result["status"] == "success"

    def run_all_tests_sequential(self) -> bool:
        """Run all test modules in sequence following system architecture"""
        print("\n🚀 RUNNING COMPLETE SYSTEM TEST SUITE")
        print("=" * 60)
        print("Following system architecture module by module...")
        
        test_modules = [
            ("Connectivity", self.run_connectivity_tests),
            ("RoboClaw", self.run_roboclaw_tests),
            ("INA219", self.run_ina219_tests),
            ("Optical Flow", self.run_optical_flow_tests),
            ("Maker Pi", self.run_maker_pi_tests),
            ("Performance", self.run_performance_tests),
            ("Code Integration", self.run_code_integration_tests),
            ("Calibration", self.run_calibration_tests)
        ]
        
        successful_tests = 0
        total_tests = len(test_modules)
        
        for module_name, test_function in test_modules:
            print(f"\n📋 Testing {module_name}...")
            try:
                if test_function():
                    successful_tests += 1
                    print(f"   ✅ {module_name} test passed")
                else:
                    print(f"   ❌ {module_name} test failed")
            except Exception as e:
                print(f"   💥 {module_name} test error: {e}")
                self.log_error(module_name, str(e), "Test execution failed")
        
        # Update system status
        success_rate = (successful_tests / total_tests) * 100
        self.test_results["system_status"] = f"completed_{successful_tests}_{total_tests}"
        self.test_results["execution_summary"] = {
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "success_rate": success_rate,
            "completion_time": datetime.now().isoformat()
        }
        
        print(f"\n📊 SYSTEM TEST SUMMARY")
        print(f"   Total Tests: {total_tests}")
        print(f"   Successful: {successful_tests}")
        print(f"   Success Rate: {success_rate:.1f}%")
        
        return successful_tests == total_tests

    def display_test_menu(self):
        """Display the main test menu"""
        print("\n🔧 System Test Suite Menu")
        print("=" * 50)
        print("1. Connectivity Tests")
        print("2. RoboClaw Motor Tests")
        print("3. INA219 Power Sensor Tests")
        print("4. Optical Flow Sensor Tests")
        print("5. Maker Pi Experimental Tests")
        print("6. Performance Tests")
        print("7. Code Integration Tests")
        print("8. Calibration Tests")
        print("9. Run All Tests (Sequential)")
        print("10. Display System Status")
        print("11. Save Test Results")
        print("12. Exit")
        print("=" * 50)

    def display_system_status(self):
        """Display current system status"""
        print("\n📊 System Status")
        print("=" * 30)
        print(f"   Status: {self.test_results['system_status']}")
        print(f"   Development Mode: {self.development_mode}")
        print(f"   Orchestrator Version: {self.test_results['orchestrator_version']}")
        print(f"   Errors: {len(self.test_results['errors'])}")
        
        if self.test_results['module_results']:
            print("\n   Module Results:")
            for module, result in self.test_results['module_results'].items():
                status = result.get('status', 'unknown')
                print(f"      {module}: {status}")
        
        if self.test_results['execution_summary']:
            summary = self.test_results['execution_summary']
            print(f"\n   Last Execution:")
            print(f"      Success Rate: {summary.get('success_rate', 0):.1f}%")
            print(f"      Tests: {summary.get('successful_tests', 0)}/{summary.get('total_tests', 0)}")

    def save_test_results(self) -> Optional[str]:
        """Save test results to file"""
        try:
            # Create test_logs directory if it doesn't exist
            logs_dir = os.path.join(os.path.dirname(__file__), "test_logs", "system")
            os.makedirs(logs_dir, exist_ok=True)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"system_test_results_{timestamp}.json"
            filepath = os.path.join(logs_dir, filename)
            
            # Save results
            with open(filepath, 'w') as f:
                json.dump(self.test_results, f, indent=2)
            
            print(f"   ✅ Test results saved to: {filepath}")
            return filepath
            
        except Exception as e:
            print(f"   ❌ Failed to save test results: {e}")
            return None

    def get_autopilot_input(self, prompt: str = "Enter choice: ") -> str:
        """Get input with autopilot support"""
        return get_autopilot_input(prompt)

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="System Test Suite Orchestrator")
    parser.add_argument("--dev", action="store_true", help="Enable development mode")
    parser.add_argument("--save", action="store_true", help="Save test results")
    parser.add_argument("--autopilot", type=str, default="", help="Autopilot input string")
    
    args = parser.parse_args()
    
    # Initialize orchestrator
    orchestrator = SystemTestOrchestrator(
        development_mode=args.dev,
        autopilot_input=args.autopilot
    )
    
    print("🔧 System Test Suite Orchestrator v3.0")
    print("=" * 50)
    
    try:
        while True:
            orchestrator.display_test_menu()
            
            choice = orchestrator.get_autopilot_input("Enter choice (1-12): ")
            
            if choice == "1":
                orchestrator.run_connectivity_tests()
            elif choice == "2":
                orchestrator.run_roboclaw_tests()
            elif choice == "3":
                orchestrator.run_ina219_tests()
            elif choice == "4":
                orchestrator.run_optical_flow_tests()
            elif choice == "5":
                orchestrator.run_maker_pi_tests()
            elif choice == "6":
                orchestrator.run_performance_tests()
            elif choice == "7":
                orchestrator.run_code_integration_tests()
            elif choice == "8":
                orchestrator.run_calibration_tests()
            elif choice == "9":
                orchestrator.run_all_tests_sequential()
            elif choice == "10":
                orchestrator.display_system_status()
            elif choice == "11":
                orchestrator.save_test_results()
            elif choice == "12":
                print("\n👋 Exiting System Test Suite...")
                break
            else:
                print("❌ Invalid choice. Please enter 1-12.")
            
            if args.save:
                orchestrator.save_test_results()
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupt received. Exiting...")
    
    finally:
        if args.save:
            orchestrator.save_test_results()

if __name__ == "__main__":
    import argparse
    main()
