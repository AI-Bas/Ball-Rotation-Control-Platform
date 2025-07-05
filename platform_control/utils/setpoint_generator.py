#!/usr/bin/env python3
"""
RoboClaw Setpoint Generator Utility
Generates velocity setpoints and motion profiles for RoboClaw motor control
"""

import numpy as np
import time
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime

class RoboClawSetpointGenerator:
    """Generate motion setpoints for RoboClaw motor control"""
    
    def __init__(self):
        """Initialize setpoint generator"""
        self.current_setpoints = {}
        
    def generate_velocity_setpoint(self, motor_id: int, target_velocity: float,
                                 acceleration: float = 100.0) -> Dict:
        """Generate velocity setpoint for RoboClaw motor"""
        setpoint = {
            "motor_id": motor_id,
            "type": "velocity",
            "target": target_velocity,
            "acceleration": acceleration,
            "timestamp": datetime.now().isoformat()
        }
        
        self.current_setpoints[motor_id] = setpoint
        return setpoint
    
    def generate_position_setpoint(self, motor_id: int, target_position: float, 
                                 duration: float = 1.0, profile: str = "trapezoidal") -> Dict:
        """Generate position setpoint with motion profile for RoboClaw motor"""
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
    
    def generate_calibration_setpoints(self, min_velocity: float = 0.0, max_velocity: float = 2.0, num_points: int = 10) -> Dict[str, Any]:
        """Generate calibration setpoints for velocity testing"""
        velocities = np.linspace(min_velocity, max_velocity, num_points).tolist()
        
        return {
            'velocities': velocities,
            'num_points': num_points,
            'velocity_range': [min_velocity, max_velocity]
        }
    
    def _trapezoidal_profile(self, target: float, duration: float, 
                           samples: int = 100) -> Tuple[List[float], List[float], List[float]]:
        """Generate trapezoidal motion profile"""
        t = np.linspace(0, duration, samples)
        
        # Simple trapezoidal profile
        positions = [target * (ti/duration) for ti in t]
        velocities = [target/duration] * len(t)
        accelerations = [0] * len(t)
        
        return positions, velocities, accelerations
    
    def _smooth_profile(self, target: float, duration: float,
                       samples: int = 100) -> Tuple[List[float], List[float], List[float]]:
        """Generate smooth motion profile"""
        t = np.linspace(0, duration, samples)
        
        # Smooth profile using sine function
        positions = [target * 0.5 * (1 - np.cos(np.pi * ti / duration)) for ti in t]
        velocities = [target * 0.5 * np.pi / duration * np.sin(np.pi * ti / duration) for ti in t]
        accelerations = [target * 0.5 * (np.pi / duration)**2 * np.cos(np.pi * ti / duration) for ti in t]
        
        return positions, velocities, accelerations
    
    def get_current_setpoint(self, motor_id: int) -> Optional[Dict]:
        """Get current setpoint for a motor"""
        return self.current_setpoints.get(motor_id)
    
    def clear_setpoint(self, motor_id: int):
        """Clear setpoint for a motor"""
        if motor_id in self.current_setpoints:
            del self.current_setpoints[motor_id]
    
    def clear_all_setpoints(self):
        """Clear all setpoints"""
        self.current_setpoints.clear()

def main():
    """Test the setpoint generator"""
    generator = RoboClawSetpointGenerator()
    
    # Test velocity setpoint
    velocity_sp = generator.generate_velocity_setpoint(1, 100.0)
    print(f"Velocity setpoint: {velocity_sp}")
    
    # Test position setpoint
    position_sp = generator.generate_position_setpoint(1, 1000.0, 2.0, "trapezoidal")
    print(f"Position setpoint: {position_sp}")
    
    # Test calibration setpoints
    cal_sp = generator.generate_calibration_setpoints(0.0, 100.0, 5)
    print(f"Calibration setpoints: {cal_sp}")

if __name__ == "__main__":
    main() 