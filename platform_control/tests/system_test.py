#!/usr/bin/env python3
"""
System Test Suite - Central Testing Orchestrator
Modular testing system for Ball Handler Test Platform

This is the central controller that orchestrates all testing modules:
1. Connectivity Tests (connectivity_test.py)
2. RoboClaw Motor Testing (roboclaw_test_menu.py)
3. INA219 Power Sensor Testing (ina219_test_menu.py)
4. Optical Flow Sensor Testing (optical_flow_test_menu.py)
5. Maker Pi Experimental Module Testing (maker_pi_tests.py)
6. Calibration and Characterization Tests (calibration_tests.py)

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
            "orchestrator_version": "2.0",
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
        # RoboClaw tests
        print("\n🔧 Running RoboClaw Tests...")
        try:
            result = subprocess.run([
                sys.executable, "roboclaw_test.py", 
                "--dev" if self.development_mode else "",
                "--save",
                "--autopilot", "123456"
            ], capture_output=True, text=True, cwd=os.path.dirname(__file__))
            
            if result.returncode == 0:
                print("   ✅ RoboClaw tests completed successfully")
                self.test_results["module_results"]["roboclaw"] = {"status": "success", "output": result.stdout}
            else:
                print(f"   ❌ RoboClaw tests failed: {result.stderr}")
                self.test_results["module_results"]["roboclaw"] = {"status": "failed", "error": result.stderr}
        except Exception as e:
            print(f"   ❌ RoboClaw tests error: {e}")
            self.test_results["module_results"]["roboclaw"] = {"status": "error", "error": str(e)}
        return self.test_results["module_results"]["roboclaw"]["status"] == "success"

    def run_ina219_tests(self) -> bool:
        """Run INA219 test module"""
        module_path = os.path.join(os.path.dirname(__file__), "ina219_test_menu.py")
        result = self.run_module_test("INA219", module_path, "1234")
        self.test_results["module_results"]["ina219"] = result
        return result["status"] == "success"

    def run_optical_flow_tests(self) -> bool:
        """Run optical flow test module"""
        module_path = os.path.join(os.path.dirname(__file__), "optical_flow_test_menu.py")
        result = self.run_module_test("Optical Flow", module_path, "123")
        self.test_results["module_results"]["optical_flow"] = result
        return result["status"] == "success"

    def run_maker_pi_tests(self) -> bool:
        """Run Maker Pi test module"""
        module_path = os.path.join(os.path.dirname(__file__), "maker_pi_tests.py")
        result = self.run_module_test("Maker Pi", module_path, "123")
        self.test_results["module_results"]["maker_pi"] = result
        return result["status"] == "success"

    def run_calibration_tests(self) -> bool:
        """Run calibration test module"""
        module_path = os.path.join(os.path.dirname(__file__), "calibration_tests.py")
        result = self.run_module_test("Calibration", module_path, "3")  # Run all tests
        self.test_results["module_results"]["calibration"] = result
        return result["status"] == "success"

    def run_performance_tests(self) -> bool:
        """Run performance test module"""
        # Performance tests
        print("\n📊 Running Performance Tests...")
        try:
            result = subprocess.run([
                sys.executable, "performance_test.py", 
                "--dev" if self.development_mode else "",
                "--save",
                "--autopilot", "12345"
            ], capture_output=True, text=True, cwd=os.path.dirname(__file__))
            
            if result.returncode == 0:
                print("   ✅ Performance tests completed successfully")
                self.test_results["module_results"]["performance"] = {"status": "success", "output": result.stdout}
            else:
                print(f"   ❌ Performance tests failed: {result.stderr}")
                self.test_results["module_results"]["performance"] = {"status": "failed", "error": result.stderr}
        except Exception as e:
            print(f"   ❌ Performance tests error: {e}")
            self.test_results["module_results"]["performance"] = {"status": "error", "error": str(e)}
        return self.test_results["module_results"]["performance"]["status"] == "success"

    def run_all_tests_sequential(self) -> bool:
        """Run all test modules in sequence"""
        print("\n" + "="*80)
        print("🔧 COMPREHENSIVE SYSTEM TEST SUITE")
        print("="*80)
        print(f"⏰ Timestamp: {datetime.now().isoformat()}")
        print(f"🔧 Development Mode: {'ENABLED' if self.development_mode else 'DISABLED'}")
        print(f"💻 Platform: {platform.system()} {platform.release()}")
        print("="*80)
        
        start_time = time.time()
        total_modules = 6
        successful_modules = 0
        
        # Define test modules and their execution order
        test_modules = [
            ("Connectivity Tests", self.run_connectivity_tests),
            ("RoboClaw Tests", self.run_roboclaw_tests),
            ("INA219 Tests", self.run_ina219_tests),
            ("Optical Flow Tests", self.run_optical_flow_tests),
            ("Maker Pi Tests", self.run_maker_pi_tests),
            ("Calibration Tests", self.run_calibration_tests),
            ("Performance Tests", self.run_performance_tests)
        ]
        
        # Execute each module
        for module_name, test_function in test_modules:
            try:
                if test_function():
                    successful_modules += 1
                    print(f"   ✅ {module_name} completed successfully")
                else:
                    print(f"   ❌ {module_name} failed")
            except Exception as e:
                print(f"   💥 {module_name} encountered an error: {e}")
                self.log_error(module_name, str(e), "Module execution failed")
        
        # Calculate execution summary
        total_duration = time.time() - start_time
        success_rate = (successful_modules / total_modules) * 100
        
        self.test_results["execution_summary"] = {
            "total_modules": total_modules,
            "successful_modules": successful_modules,
            "failed_modules": total_modules - successful_modules,
            "success_rate": success_rate,
            "total_duration": total_duration,
            "completion_time": datetime.now().isoformat()
        }
        
        # Display final summary
        print("\n" + "="*80)
        print("📊 EXECUTION SUMMARY")
        print("="*80)
        print(f"Total Modules: {total_modules}")
        print(f"Successful: {successful_modules}")
        print(f"Failed: {total_modules - successful_modules}")
        print(f"Success Rate: {success_rate:.1f}%")
        print(f"Total Duration: {total_duration:.1f} seconds")
        print(f"Average per Module: {total_duration/total_modules:.1f} seconds")
        
        if self.test_results["errors"]:
            print(f"\n⚠ ERRORS ENCOUNTERED ({len(self.test_results['errors'])}):")
            for error in self.test_results["errors"]:
                print(f"   {error['module']}: {error['error']}")
        
        # Save results
        self.save_test_results()
        
        return successful_modules == total_modules

    def display_test_menu(self):
        """Display the main test menu"""
        print("\n" + "="*60)
        print("🔧 BALL ROTATION CONTROL PLATFORM - TEST SUITE")
        print("="*60)
        print("1. Run Connectivity Tests")
        print("2. Run RoboClaw Motor Tests")
        print("3. Run INA219 Power Sensor Tests")
        print("4. Run Optical Flow Sensor Tests")
        print("5. Run Maker Pi Experimental Tests")
        print("6. Run Calibration & Characterization Tests")
        print("7. Run Performance Tests")
        print("8. Run All Tests Sequential")
        print("9. Display System Status")
        print("10. Exit")
        print("="*60)

    def display_system_status(self):
        """Display current system status"""
        print("\n" + "="*60)
        print("📊 SYSTEM STATUS")
        print("="*60)
        print(f"Platform: {platform.system()} {platform.release()}")
        print(f"Python Version: {sys.version}")
        print(f"Development Mode: {'ENABLED' if self.development_mode else 'DISABLED'}")
        print(f"Configuration Loaded: {'✓' if self.platform_config else '✗'}")
        print(f"Test Results: {len(self.test_results['module_results'])} modules")
        print(f"Errors: {len(self.test_results['errors'])}")
        
        if self.test_results["module_results"]:
            print("\n📋 MODULE STATUS:")
            for module, result in self.test_results["module_results"].items():
                status_icon = "✅" if result["status"] == "success" else "❌"
                print(f"   {status_icon} {module}: {result['status']}")

    def save_test_results(self) -> Optional[str]:
        """Save comprehensive test results"""
        try:
            # Ensure test_logs directory exists
            os.makedirs("test_logs/system", exist_ok=True)
            
            # Save results to file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"system_test_orchestrator_results_{timestamp}_dev.json"
            filepath = os.path.join("test_logs/system", filename)
            
            # Save results
            with open(filepath, "w") as f:
                json.dump(self.test_results, f, indent=2)
            
            print(f"\n💾 Comprehensive results saved to {filepath}")
            return filepath
            
        except Exception as e:
            print(f"\n⚠ Could not save results: {e}")
            return None

    def get_autopilot_input(self, prompt: str = "Enter choice: ") -> str:
        return get_autopilot_input(prompt)

def main():
    """Main function for standalone execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description="System Test Orchestrator")
    parser.add_argument("--dev", action="store_true", help="Enable development mode")
    parser.add_argument("--autopilot", type=str, default="", help="Autopilot input string")
    parser.add_argument("--save", action="store_true", help="Save test results")
    
    args = parser.parse_args()
    
    # Initialize orchestrator
    orchestrator = SystemTestOrchestrator(development_mode=args.dev, autopilot_input=args.autopilot)
    
    # Handle autopilot mode
    if args.autopilot:
        print("🤖 AUTOPILOT MODE - Running all tests sequentially")
        orchestrator.run_all_tests_sequential()
        return
    
    # Interactive mode
    while True:
        orchestrator.display_test_menu()
        
        try:
            choice = orchestrator.get_autopilot_input()
            
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
                orchestrator.run_calibration_tests()
            elif choice == "7":
                orchestrator.run_performance_tests()
            elif choice == "8":
                orchestrator.run_all_tests_sequential()
            elif choice == "9":
                orchestrator.display_system_status()
            elif choice == "10":
                print("Exiting...")
                break
            else:
                print("Invalid choice. Please enter a number between 1-10.")
                
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")
    
    return 0

if __name__ == "__main__":
    main()
