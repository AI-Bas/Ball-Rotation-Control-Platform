#!/usr/bin/env python3
"""
Motion Profile Generator for RoboClaw Motors
============================================

Generates sinusoidal motion profiles for motor velocity control.
Provides configurable amplitude, frequency, and duration.

Author: System Demo
Date: 2025-07-02
"""

import math
import time

class MotionProfileGenerator:
    """
    Generates sinusoidal motion profiles for motor control.
    """
    
    def __init__(self):
        """Initialize the motion profile generator."""
        self.default_amplitude = 400  # encoder counts per second
        self.default_frequency = 0.1  # Hz (10 second period)
        self.default_duration = 30    # seconds
        
    def generate_sinusoidal_profile(self, amplitude=None, frequency=None, duration=None):
        """
        Generate a sinusoidal velocity profile.
        
        Args:
            amplitude: Peak velocity in encoder counts per second
            frequency: Frequency in Hz
            duration: Total duration in seconds
            
        Returns:
            dict: Profile configuration and generator function
        """
        # Use defaults if not specified
        amplitude = amplitude or self.default_amplitude
        frequency = frequency or self.default_frequency
        duration = duration or self.default_duration
        
        print(f"Generating sinusoidal profile:")
        print(f"  Amplitude: {amplitude} encoder counts/s")
        print(f"  Frequency: {frequency} Hz (period: {1/frequency:.1f}s)")
        print(f"  Duration: {duration} seconds")
        
        def velocity_function(t):
            """
            Calculate velocity at time t.
            
            Args:
                t: Time in seconds
                
            Returns:
                int: Velocity in encoder counts per second
            """
            if t > duration:
                return 0
            
            # Sinusoidal function: v(t) = A * sin(2π * f * t)
            velocity = amplitude * math.sin(2 * math.pi * frequency * t)
            return int(velocity)
        
        return {
            'amplitude': amplitude,
            'frequency': frequency,
            'duration': duration,
            'velocity_function': velocity_function,
            'type': 'sinusoidal'
        }
    
    def preview_profile(self, profile, sample_rate=0.1):
        """
        Preview a motion profile by printing sample points.
        
        Args:
            profile: Profile dictionary from generate functions
            sample_rate: Time between samples in seconds
        """
        print(f"\nProfile Preview ({profile['type']}):")
        print("Time(s) | Velocity")
        print("-" * 20)
        
        velocity_func = profile['velocity_function']
        duration = profile['duration']
        
        # Sample points
        t = 0
        while t <= duration:
            velocity = velocity_func(t)
            print(f"{t:6.1f} | {velocity:7d}")
            t += sample_rate
            
        # Final point
        velocity = velocity_func(duration)
        print(f"{duration:6.1f} | {velocity:7d}")
    
    def get_user_profile(self):
        """
        Get motion profile parameters from user input.
        
        Returns:
            dict: Profile configuration
        """
        print("\n" + "=" * 50)
        print("SINUSOIDAL MOTION PROFILE CONFIGURATION")
        print("=" * 50)
        
        try:
            amplitude = float(input(f"Amplitude (default {self.default_amplitude}): ") or self.default_amplitude)
            frequency = float(input(f"Frequency in Hz (default {self.default_frequency}): ") or self.default_frequency)
            duration = float(input(f"Duration in seconds (default {self.default_duration}): ") or self.default_duration)
            
            return self.generate_sinusoidal_profile(amplitude, frequency, duration)
            
        except (ValueError, KeyboardInterrupt):
            print("Using default values.")
            return self.generate_sinusoidal_profile()

def main():
    """Test the motion profile generator."""
    generator = MotionProfileGenerator()
    
    print("Sinusoidal Motion Profile Generator Test")
    print("=" * 50)
    
    # Test sinusoidal profile
    print("\n1. Testing sinusoidal profile...")
    sin_profile = generator.generate_sinusoidal_profile(300, 0.2, 20)
    generator.preview_profile(sin_profile, 1.0)
    
    # Test user input
    print("\n2. Testing user input...")
    user_profile = generator.get_user_profile()
    if user_profile:
        generator.preview_profile(user_profile, 1.0)
    else:
        print("User input cancelled.")

if __name__ == "__main__":
    main() 