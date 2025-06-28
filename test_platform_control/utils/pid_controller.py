import numpy as np
from typing import Tuple

class PIDController:
    def __init__(self, kp: float, ki: float, kd: float):
        """
        Initialize the PID controller
        Args:
            kp: Proportional gain
            ki: Integral gain
            kd: Derivative gain
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        
        # Initialize error terms
        self.previous_error = 0.0
        self.integral = 0.0
        
    def compute(self, error: float, dt: float) -> float:
        """
        Compute PID control output
        Args:
            error: Current error
            dt: Time step
        Returns:
            Control output
        """
        # Compute integral term
        self.integral += error * dt
        
        # Compute derivative term
        derivative = (error - self.previous_error) / dt if dt > 0 else 0
        
        # Compute PID output
        output = (self.kp * error + 
                 self.ki * self.integral + 
                 self.kd * derivative)
        
        # Update previous error
        self.previous_error = error
        
        return output
        
    def reset(self):
        """Reset the controller state"""
        self.previous_error = 0.0
        self.integral = 0.0
        
    def set_gains(self, kp: float, ki: float, kd: float):
        """
        Update PID gains
        Args:
            kp: New proportional gain
            ki: New integral gain
            kd: New derivative gain
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd 