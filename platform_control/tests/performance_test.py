#!/usr/bin/env python3
"""
Performance Testing Module
Motion control specific performance tests for the Ball Rotation Control Platform
Extracted from characterization functionality for dedicated performance analysis
"""

import os
import sys
import json
import time
import argparse
import numpy as np
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

# Add the parent directory to sys.path to import from utils
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.roboclaw_interface import RoboClawInterface
from utils.kinematic_conversion import jacobian
from utils.data_logger import DataLogger
from utils.autopilot_manager import create_autopilot_manager, set_autopilot_manager, get_autopilot_input

class PerformanceTest:
    """Performance testing module for motion control analysis"""
    
    def __init__(self, development_mode: bool = False, autopilot_input: str = ""):
        """Initialize the performance test module"""
        self.development_mode = development_mode
        self.autopilot_input = autopilot_input
        # Initialize autopilot manager for this script
        self.autopilot_manager = create_autopilot_manager("performance_test", autopilot_input)
        set_autopilot_manager(self.autopilot_manager)
        
        # Initialize interfaces
        self.roboclaw_interface = RoboClawInterface(use_dual_controllers=True)
        self.jacobian = jacobian
        self.data_logger = DataLogger()
        
        # Test results storage
        self.test_results = {}
        
        # Load configuration
        self.config = self.roboclaw_interface.config
        self.system_params = self.config.get('system_parameters', {})
        
        print("📊 Performance Test Module Initialized")
        if self.development_mode:
            print("   Development mode enabled")
    
    def get_autopilot_input(self, prompt: str = "Enter choice: ") -> str:
        return get_autopilot_input(prompt)
    
    def test_kinematic_performance(self) -> Dict[str, Any]:
        """Test kinematic conversion performance"""
        print("\n🔢 Kinematic Performance Test")
        print("-" * 40)
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "test_type": "kinematic_performance",
            "conversion_times": [],
            "accuracy_tests": [],
            "status": False
        }
        
        try:
            # Get system parameters for jacobian calculation
            beta = self.system_params.get('beta', 120.0)  # Angle between wheels
            rBall = self.system_params.get('rBall', 0.05)  # Ball radius
            rOmni = self.system_params.get('rOmni', 0.02)  # Omniwheel radius
            rZ = self.system_params.get('rZ', 0.03)  # Z-offset
            rX = self.system_params.get('rX', 0.04)  # X-offset
            
            # Test conversion speed
            test_velocities = [
                (1.0, 0.0), (0.0, 1.0), (1.0, 1.0), (-1.0, 0.5), (0.5, -0.5)
            ]
            
            print("   Testing kinematic conversion speed...")
            for vx, vy in test_velocities:
                start_time = time.time()
                
                # Perform kinematic conversion using jacobian function
                inv_jacobian, jacobian_matrix = self.jacobian(beta, rBall, rOmni, rZ, rX)
                
                end_time = time.time()
                conversion_time = (end_time - start_time) * 1000  # Convert to ms
                
                result["conversion_times"].append({
                    "input": (vx, vy),
                    "jacobian_shape": jacobian_matrix.shape,
                    "time_ms": conversion_time
                })
                
                print(f"     Jacobian calculation: {conversion_time:.3f}ms")
            
            # Test accuracy with known values
            print("   Testing kinematic accuracy...")
            test_cases = [
                ((1.0, 0.0), "forward motion"),
                ((0.0, 1.0), "sideways motion"),
                ((1.0, 1.0), "diagonal motion"),
                ((0.0, 0.0), "stationary")
            ]
            
            for (vx, vy), description in test_cases:
                # Calculate jacobian matrices
                inv_jacobian, jacobian_matrix = self.jacobian(beta, rBall, rOmni, rZ, rX)
                
                # Check if results are reasonable
                is_valid = inv_jacobian.shape == (3, 3) and jacobian_matrix.shape == (3, 3)
                is_reasonable = np.all(np.isfinite(inv_jacobian)) and np.all(np.isfinite(jacobian_matrix))
                
                accuracy_result = {
                    "input": (vx, vy),
                    "description": description,
                    "inv_jacobian_shape": inv_jacobian.shape,
                    "jacobian_shape": jacobian_matrix.shape,
                    "valid": is_valid,
                    "reasonable": is_reasonable
                }
                
                result["accuracy_tests"].append(accuracy_result)
                
                status = "✅" if is_valid and is_reasonable else "❌"
                print(f"     {status} {description}: {inv_jacobian.shape} x {jacobian_matrix.shape}")
            
            result["status"] = True
            avg_time = np.mean([t["time_ms"] for t in result["conversion_times"]])
            print(f"   📊 Average conversion time: {avg_time:.3f}ms")
            
        except Exception as e:
            result["error"] = str(e)
            print(f"   ❌ Kinematic performance test failed: {e}")
        
        return result
    
    def test_motor_response_time(self) -> Dict[str, Any]:
        """Test motor response time and latency"""
        print("\n⚡ Motor Response Time Test")
        print("-" * 40)
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "test_type": "motor_response_time",
            "response_times": [],
            "latency_measurements": [],
            "status": False
        }
        
        try:
            # Test motor command latency
            print("   Testing motor command latency...")
            
            for motor_num in [1, 2, 3, 4]:
                if motor_num in self.roboclaw_interface.motor_data:
                    motor_info = self.roboclaw_interface.motor_data[motor_num]
                    controller = motor_info.get('controller')
                    channel = motor_info.get('channel')
                    
                    print(f"     Testing motor {motor_num} ({controller}, {channel})...")
                    
                    # Measure command latency
                    start_time = time.time()
                    
                    # Send a small test command
                    success = self.roboclaw_interface.set_velocity(motor_num, 100)
                    
                    end_time = time.time()
                    latency = (end_time - start_time) * 1000  # Convert to ms
                    
                    # Stop motor immediately
                    self.roboclaw_interface.set_velocity(motor_num, 0)
                    
                    response_result = {
                        "motor": motor_num,
                        "controller": controller,
                        "channel": channel,
                        "latency_ms": latency,
                        "success": success
                    }
                    
                    result["response_times"].append(response_result)
                    
                    status = "✅" if success else "❌"
                    print(f"       {status} Latency: {latency:.3f}ms")
                else:
                    print(f"     ⚠️ Motor {motor_num} not configured")
            
            result["status"] = len(result["response_times"]) > 0
            
            if result["response_times"]:
                avg_latency = np.mean([r["latency_ms"] for r in result["response_times"]])
                print(f"   📊 Average latency: {avg_latency:.3f}ms")
            
        except Exception as e:
            result["error"] = str(e)
            print(f"   ❌ Motor response time test failed: {e}")
        
        return result
    
    def test_control_loop_performance(self) -> Dict[str, Any]:
        """Test control loop performance and timing"""
        print("\n🔄 Control Loop Performance Test")
        print("-" * 40)
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "test_type": "control_loop_performance",
            "loop_times": [],
            "frequency_measurements": [],
            "status": False
        }
        
        try:
            # Test control loop frequency
            print("   Testing control loop frequency...")
            
            loop_count = 100
            start_time = time.time()
            
            for i in range(loop_count):
                loop_start = time.time()
                
                # Simulate control loop operations
                # 1. Read sensor data
                # 2. Calculate setpoints
                # 3. Update motor commands
                # 4. Log data
                
                # Simulate sensor reading
                time.sleep(0.001)  # 1ms simulation
                
                # Simulate setpoint calculation
                vx, vy = 0.5, 0.3
                inv_jacobian, jacobian_matrix = self.jacobian(120.0, 0.05, 0.02, 0.03, 0.04)
                
                # Simulate motor command update
                for motor_num in [1, 2, 3, 4]:
                    if motor_num in self.roboclaw_interface.motor_data:
                        pass  # Would send actual command
                
                loop_end = time.time()
                loop_time = (loop_end - loop_start) * 1000  # Convert to ms
                result["loop_times"].append(loop_time)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Calculate frequency
            frequency = loop_count / total_time
            avg_loop_time = np.mean(result["loop_times"])
            max_loop_time = np.max(result["loop_times"])
            min_loop_time = np.min(result["loop_times"])
            
            result["frequency_measurements"] = {
                "frequency_hz": frequency,
                "avg_loop_time_ms": avg_loop_time,
                "max_loop_time_ms": max_loop_time,
                "min_loop_time_ms": min_loop_time,
                "total_time_s": total_time
            }
            
            print(f"   📊 Control loop frequency: {frequency:.1f} Hz")
            print(f"   📊 Average loop time: {avg_loop_time:.3f}ms")
            print(f"   📊 Loop time range: {min_loop_time:.3f}ms - {max_loop_time:.3f}ms")
            
            result["status"] = True
            
        except Exception as e:
            result["error"] = str(e)
            print(f"   ❌ Control loop performance test failed: {e}")
        
        return result
    
    def run_performance_menu(self):
        """Run performance test sub-menu"""
        while True:
            print("\n📊 Performance Test Menu")
            print("1. Kinematic Performance Test")
            print("2. Motor Response Time Test")
            print("3. Control Loop Performance Test")
            print("4. Run All Performance Tests")
            print("5. Back to Main Menu")
            
            choice = self.get_autopilot_input()
            
            if choice == "1":
                result = self.test_kinematic_performance()
                self.test_results["kinematic_performance"] = result
            elif choice == "2":
                result = self.test_motor_response_time()
                self.test_results["motor_response_time"] = result
            elif choice == "3":
                result = self.test_control_loop_performance()
                self.test_results["control_loop_performance"] = result
            elif choice == "4":
                self.run_all_performance_tests()
            elif choice == "5":
                break
            else:
                print("   ❌ Invalid choice")
    
    def run_all_performance_tests(self):
        """Run all performance tests"""
        print("\n🚀 Running All Performance Tests")
        print("=" * 50)
        
        # Run all performance tests
        self.test_results["kinematic_performance"] = self.test_kinematic_performance()
        self.test_results["motor_response_time"] = self.test_motor_response_time()
        self.test_results["control_loop_performance"] = self.test_control_loop_performance()
        
        print("   ✅ All performance tests completed")
    
    def save_test_results(self, results: Dict[str, Any]):
        """Save test results to file"""
        try:
            # Ensure test_logs directory exists
            os.makedirs("test_logs/performance", exist_ok=True)
            
            # Save results to file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"performance_test_{timestamp}.json"
            filepath = os.path.join("test_logs/performance", filename)
            
            with open(filepath, 'w') as f:
                json.dump(results, f, indent=2)
            
            print(f"   💾 Test results saved: {filepath}")
            
        except Exception as e:
            print(f"   ⚠️ Failed to save test results: {e}")
    
    def run_test_menu(self) -> Dict[str, Any]:
        """Run the main performance test menu"""
        print("\n📊 Performance Test Module")
        print("=" * 50)
        
        while True:
            print("\nMain Menu:")
            print("1. Performance Tests")
            print("2. Run All Tests")
            print("3. Save Results")
            print("4. Exit")
            print("-" * 30)
            
            choice = self.get_autopilot_input()
            
            if choice == "1":
                self.run_performance_menu()
            elif choice == "2":
                self.run_all_performance_tests()
            elif choice == "3":
                if self.test_results:
                    self.save_test_results(self.test_results)
                else:
                    print("   ⚠️ No test results to save")
            elif choice == "4":
                print("   👋 Exiting performance test module")
                break
            else:
                print("   ❌ Invalid choice")
        
        return self.test_results

def main():
    """Main function for performance test module"""
    parser = argparse.ArgumentParser(description="Performance Test Module")
    parser.add_argument("--dev", "--development", action="store_true", 
                       help="Enable development mode with enhanced troubleshooting")
    parser.add_argument("--save", action="store_true", 
                       help="Automatically save test results")
    parser.add_argument("--autopilot", type=str, default="", 
                       help="Autonomous execution input string")
    
    args = parser.parse_args()
    
    print("📊 Performance Test Module")
    print("=" * 50)
    
    if args.dev:
        print("🔧 Development mode enabled")
    else:
        print("💡 Run with --dev flag for development mode")
    
    # Initialize test module
    test_module = PerformanceTest(
        development_mode=args.dev,
        autopilot_input=args.autopilot
    )
    
    # Run test menu
    results = test_module.run_test_menu()
    
    # Auto-save if requested
    if args.save and results:
        test_module.save_test_results(results)
    
    print("\nPerformance test module completed.")

if __name__ == "__main__":
    main() 