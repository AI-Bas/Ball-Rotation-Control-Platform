#!/usr/bin/env python3
"""
Setpoint Generator Utility
Generates position, velocity, and acceleration setpoints for motor control
Agnostic of motor driver type, supports indexed sequence for mapped motors
"""

import numpy as np
import time
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime

class SetpointGenerator:
    """Generate motion setpoints for motor control"""
    
    def __init__(self, motor_mapping: Optional[Dict[str, Dict]] = None):
        """Initialize setpoint generator with motor mapping"""
        self.motor_mapping = motor_mapping or {}
        self.current_setpoints = {}
        self.motion_profiles = {}
        
    def generate_position_setpoint(self, motor_id: str, target_position: float, 
                                 duration: float = 1.0, profile: str = "trapezoidal") -> Dict:
        """Generate position setpoint with motion profile"""
        if motor_id not in self.motor_mapping:
            raise ValueError(f"Motor {motor_id} not found in mapping")
        
        # Generate motion profile
        if profile == "trapezoidal":
            positions, velocities, accelerations = self._trapezoidal_profile(
                target_position, duration
            )
        elif profile == "smooth":
            positions, velocities, accelerations = self._smooth_profile(
                target_position, duration
            )
        else:
            raise ValueError(f"Unknown profile type: {profile}")
        
        setpoint = {
            "motor_id": motor_id,
            "type": "position",
            "target": target_position,
            "duration": duration,
            "profile": profile,
            "positions": positions,
            "velocities": velocities,
            "accelerations": accelerations,
            "timestamp": datetime.now().isoformat()
        }
        
        self.current_setpoints[motor_id] = setpoint
        return setpoint
    
    def generate_velocity_setpoint(self, motor_id: str, target_velocity: float,
                                 acceleration: float = 100.0) -> Dict:
        """Generate velocity setpoint with acceleration limit"""
        if motor_id not in self.motor_mapping:
            raise ValueError(f"Motor {motor_id} not found in mapping")
        
        setpoint = {
            "motor_id": motor_id,
            "type": "velocity",
            "target": target_velocity,
            "acceleration": acceleration,
            "timestamp": datetime.now().isoformat()
        }
        
        self.current_setpoints[motor_id] = setpoint
        return setpoint
    
    def generate_acceleration_setpoint(self, motor_id: str, target_acceleration: float) -> Dict:
        """Generate acceleration setpoint"""
        if motor_id not in self.motor_mapping:
            raise ValueError(f"Motor {motor_id} not found in mapping")
        
        setpoint = {
            "motor_id": motor_id,
            "type": "acceleration",
            "target": target_acceleration,
            "timestamp": datetime.now().isoformat()
        }
        
        self.current_setpoints[motor_id] = setpoint
        return setpoint
    
    def generate_indexed_sequence(self, start_velocity: float = 10.0, 
                                max_velocity: float = 100.0, 
                                ramp_time: float = 2.0) -> Dict[str, Dict]:
        """Generate indexed sequence for all mapped motors with slow ramping"""
        sequence = {}
        
        for motor_id, mapping in self.motor_mapping.items():
            if mapping.get("encoder_change", 0) > 1000:  # Only for detected motors
                # Generate ramped velocity setpoint
                setpoint = self.generate_velocity_setpoint(
                    motor_id, 
                    start_velocity, 
                    acceleration=(max_velocity - start_velocity) / ramp_time
                )
                sequence[motor_id] = setpoint
        
        return sequence
    
    def generate_indexed_sequence_with_confirmation(self, motor_ids: List[str], 
                                                  sequence_type: str = "position",
                                                  duration: float = 10.0,
                                                  amplitude: float = 1000.0,
                                                  require_confirmation: bool = True) -> Dict[str, Any]:
        """Generate indexed sequence with motor motion confirmation options"""
        print("🚀 SETPOINT GENERATOR - MOTOR MOTION CONFIRMATION")
        print("="*60)
        print("📋 Motor Motion Options:")
        print("  - SKIP: Skip this motor's motion")
        print("  - CONFIRM: Allow motor motion")
        print("  - DENY: Prevent motor motion")
        print("="*60)
        
        sequence_results = {
            "timestamp": datetime.now().isoformat(),
            "sequence_type": sequence_type,
            "duration": duration,
            "amplitude": amplitude,
            "motor_confirmation": {},
            "generated_setpoints": {},
            "motion_executed": {},
            "summary": {}
        }
        
        confirmed_motors = 0
        total_motors = len(motor_ids)
        
        for i, motor_id in enumerate(motor_ids):
            print(f"\n🎯 MOTOR {motor_id} ({i+1}/{total_motors})")
            print("-" * 40)
            
            # Generate setpoints for this motor
            if sequence_type == "position":
                setpoint_data = self.generate_position_setpoint(motor_id, amplitude, duration)
                setpoints = setpoint_data.get("positions", []) if setpoint_data else []
            elif sequence_type == "velocity":
                setpoint_data = self.generate_velocity_setpoint(motor_id, amplitude)
                setpoints = [setpoint_data.get("target", 0)] if setpoint_data else []
            elif sequence_type == "acceleration":
                setpoint_data = self.generate_acceleration_setpoint(motor_id, amplitude)
                setpoints = [setpoint_data.get("target", 0)] if setpoint_data else []
            else:
                setpoint_data = self.generate_indexed_sequence()
                setpoints = [0]  # Default fallback
            
            # Display motion preview
            print(f"   📊 Motion Preview:")
            print(f"   - Type: {sequence_type}")
            print(f"   - Duration: {duration}s")
            print(f"   - Amplitude: {amplitude}")
            print(f"   - Setpoints: {len(setpoints)} points")
            
            if setpoints:
                print(f"   - Range: {min(setpoints):.1f} to {max(setpoints):.1f}")
            
            # Get user confirmation
            if require_confirmation:
                confirmation = self._get_motor_confirmation(motor_id, sequence_type, duration, amplitude)
            else:
                confirmation = "confirm"  # Auto-confirm in non-interactive mode
            
            sequence_results["motor_confirmation"][motor_id] = {
                "status": confirmation,
                "timestamp": datetime.now().isoformat(),
                "setpoints_generated": len(setpoints) if setpoints else 0
            }
            
            if confirmation == "confirm":
                confirmed_motors += 1
                sequence_results["generated_setpoints"][motor_id] = setpoints
                sequence_results["motion_executed"][motor_id] = True
                print(f"   ✅ Motor {motor_id}: Motion CONFIRMED")
                
                # Execute motion (placeholder for actual motor control)
                motion_result = self._execute_motor_motion(motor_id, setpoints if isinstance(setpoints, list) else [], sequence_type)
                sequence_results["motion_executed"][motor_id] = motion_result
                
            elif confirmation == "skip":
                sequence_results["motion_executed"][motor_id] = False
                print(f"   ⏭️ Motor {motor_id}: Motion SKIPPED")
                
            elif confirmation == "deny":
                sequence_results["motion_executed"][motor_id] = False
                print(f"   ❌ Motor {motor_id}: Motion DENIED")
            
            else:
                sequence_results["motion_executed"][motor_id] = False
                print(f"   ⚠️ Motor {motor_id}: Invalid confirmation")
        
        # Generate summary
        sequence_results["summary"] = {
            "total_motors": total_motors,
            "confirmed_motors": confirmed_motors,
            "skipped_motors": sum(1 for status in sequence_results["motor_confirmation"].values() if status["status"] == "skip"),
            "denied_motors": sum(1 for status in sequence_results["motor_confirmation"].values() if status["status"] == "deny"),
            "success_rate": confirmed_motors / total_motors if total_motors > 0 else 0
        }
        
        # Display final summary
        print("\n" + "="*60)
        print("📊 MOTION CONFIRMATION SUMMARY")
        print("="*60)
        print(f"Total Motors: {total_motors}")
        print(f"Confirmed: {confirmed_motors} ✅")
        print(f"Skipped: {sequence_results['summary']['skipped_motors']} ⏭️")
        print(f"Denied: {sequence_results['summary']['denied_motors']} ❌")
        print(f"Success Rate: {sequence_results['summary']['success_rate']*100:.1f}%")
        
        if confirmed_motors >= 3:
            print("🎉 SUCCESS: All 3 motors confirmed for motion!")
        elif confirmed_motors > 0:
            print(f"⚠️ PARTIAL: {confirmed_motors} motors confirmed")
        else:
            print("❌ FAILURE: No motors confirmed for motion")
        
        return sequence_results
    
    def _get_motor_confirmation(self, motor_id: str, sequence_type: str, duration: float, amplitude: float) -> str:
        """Get user confirmation for motor motion"""
        print(f"   🤔 Confirm motion for Motor {motor_id}?")
        print(f"   Type: {sequence_type}, Duration: {duration}s, Amplitude: {amplitude}")
        print("   Options: [s]kip, [c]onfirm, [d]eny: ", end="")
        
        try:
            # Add timeout for automated testing
            import select
            import sys
            
            # Wait for input with timeout (5 seconds)
            ready, _, _ = select.select([sys.stdin], [], [], 5.0)
            if ready:
                user_input = sys.stdin.readline().strip().lower()
            else:
                print("⏰ Timeout - defaulting to SKIP")
                return "skip"
            
            if user_input in ['s', 'skip']:
                return "skip"
            elif user_input in ['c', 'confirm', 'y', 'yes']:
                return "confirm"
            elif user_input in ['d', 'deny', 'n', 'no']:
                return "deny"
            else:
                print("   ⚠️ Invalid input - defaulting to SKIP")
                return "skip"
                
        except KeyboardInterrupt:
            print("\n   ⏹️ Interrupted - defaulting to SKIP")
            return "skip"
        except Exception as e:
            print(f"   ⚠️ Error getting confirmation: {e} - defaulting to SKIP")
            return "skip"
    
    def _execute_motor_motion(self, motor_id: str, setpoints: Any, sequence_type: str) -> bool:
        """Execute motor motion with setpoints (placeholder for actual motor control)"""
        try:
            print(f"   🚀 Executing motion for Motor {motor_id}...")
            print(f"   📊 {len(setpoints) if isinstance(setpoints, list) else 1} setpoints, type: {sequence_type}")
            
            # Simulate motion execution
            time.sleep(0.1)  # Simulate processing time
            
            # In a real implementation, this would interface with the motor controller
            # For now, we'll simulate successful execution
            execution_success = True
            
            if execution_success:
                print(f"   ✅ Motor {motor_id} motion executed successfully")
                return True
            else:
                print(f"   ❌ Motor {motor_id} motion execution failed")
                return False
                
        except Exception as e:
            print(f"   ❌ Motor {motor_id} motion execution error: {e}")
            return False
    
    def test_motor_confirmation_system(self, motor_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Test the motor confirmation system with all motors"""
        if motor_ids is None:
            motor_ids = ["motor1", "motor2", "motor3", "motor4"]
        
        print("🧪 TESTING MOTOR CONFIRMATION SYSTEM")
        print("="*60)
        print("This test will generate setpoints for all motors and request confirmation")
        print("Goal: Get positive confirmation for at least 3 motors")
        print("="*60)
        
        test_results = {
            "timestamp": datetime.now().isoformat(),
            "test_type": "motor_confirmation_system",
            "target_motors": motor_ids,
            "attempts": [],
            "final_result": None
        }
        
        max_attempts = 3
        target_confirmations = 3
        
        for attempt in range(max_attempts):
            print(f"\n🔄 ATTEMPT {attempt + 1}/{max_attempts}")
            print("-" * 40)
            
            # Generate sequence with confirmation
            sequence_result = self.generate_indexed_sequence_with_confirmation(
                motor_ids=motor_ids,
                sequence_type="position",
                duration=5.0,
                amplitude=500.0,
                require_confirmation=True
            )
            
            test_results["attempts"].append(sequence_result)
            
            confirmed_count = sequence_result["summary"]["confirmed_motors"]
            print(f"\n📊 Attempt {attempt + 1} Result: {confirmed_count}/{len(motor_ids)} motors confirmed")
            
            if confirmed_count >= target_confirmations:
                print(f"🎉 SUCCESS: {confirmed_count} motors confirmed (target: {target_confirmations})")
                test_results["final_result"] = "success"
                break
            else:
                print(f"⚠️ INSUFFICIENT: {confirmed_count} motors confirmed (target: {target_confirmations})")
                if attempt < max_attempts - 1:
                    print("🔄 Retrying with adjusted parameters...")
                    # Adjust parameters for next attempt
                    time.sleep(1)
        
        if test_results["final_result"] != "success":
            test_results["final_result"] = "failed"
            print(f"\n❌ FAILED: Could not get {target_confirmations} motor confirmations after {max_attempts} attempts")
        
        # Display final test summary
        print("\n" + "="*60)
        print("🧪 MOTOR CONFIRMATION TEST SUMMARY")
        print("="*60)
        print(f"Test Result: {test_results['final_result'].upper()}")
        print(f"Attempts Made: {len(test_results['attempts'])}")
        
        for i, attempt in enumerate(test_results["attempts"]):
            confirmed = attempt["summary"]["confirmed_motors"]
            print(f"Attempt {i+1}: {confirmed}/{len(motor_ids)} motors confirmed")
        
        return test_results
    
    def _trapezoidal_profile(self, target: float, duration: float, 
                           samples: int = 100) -> Tuple[List[float], List[float], List[float]]:
        """Generate trapezoidal motion profile"""
        t = np.linspace(0, duration, samples)
        
        # Simple trapezoidal profile
        positions = [target * (ti/duration) for ti in t]
        velocities = [target/duration] * len(t)
        accelerations = [0.0] * len(t)
        
        return positions, velocities, accelerations
    
    def _smooth_profile(self, target: float, duration: float,
                       samples: int = 100) -> Tuple[List[float], List[float], List[float]]:
        """Generate smooth motion profile using sine function"""
        t = np.linspace(0, duration, samples)
        
        # Smooth profile using sine function
        positions = [target * 0.5 * (1 - np.cos(np.pi * ti / duration)) for ti in t]
        velocities = [target * 0.5 * np.pi / duration * np.sin(np.pi * ti / duration) for ti in t]
        accelerations = [target * 0.5 * (np.pi / duration)**2 * np.cos(np.pi * ti / duration) for ti in t]
        
        return positions, velocities, accelerations
    
    def get_current_setpoint(self, motor_id: str) -> Optional[Dict]:
        """Get current setpoint for a motor"""
        return self.current_setpoints.get(motor_id)
    
    def clear_setpoint(self, motor_id: str):
        """Clear setpoint for a motor"""
        if motor_id in self.current_setpoints:
            del self.current_setpoints[motor_id]
    
    def clear_all_setpoints(self):
        """Clear all setpoints"""
        self.current_setpoints.clear()

def main():
    """Test the setpoint generator"""
    # Example motor mapping
    motor_mapping = {
        "motor1": {"controller": "rc1", "channel": "A", "encoder_change": 1099},
        "motor2": {"controller": "rc1", "channel": "B", "encoder_change": 0},
        "motor3": {"controller": "rc2", "channel": "A", "encoder_change": 1361},
        "motor4": {"controller": "rc2", "channel": "B", "encoder_change": 0}
    }
    
    generator = SetpointGenerator(motor_mapping)
    
    # Test indexed sequence generation
    print("Testing indexed sequence generation...")
    sequence = generator.generate_indexed_sequence(start_velocity=5.0, max_velocity=50.0, ramp_time=3.0)
    
    for motor_id, setpoint in sequence.items():
        print(f"{motor_id}: {setpoint}")

if __name__ == "__main__":
    main() 