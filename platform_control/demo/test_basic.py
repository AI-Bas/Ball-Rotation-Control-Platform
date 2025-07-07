#!/usr/bin/env python3
"""
Basic Test Script
================

Test basic functionality before rebuilding demo system.

Author: System Demo
Date: 2025-07-06
"""

import sys
import os
import time
import math
import numpy as np

# Add the utils directory to the path to import modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'utils'))

def test_imports():
    """Test that all imports work."""
    print("Testing imports...")
    
    try:
        from roboclaw_3 import Roboclaw
        print("✓ roboclaw_3 import successful")
    except ImportError as e:
        print(f"✗ roboclaw_3 import failed: {e}")
        return False
    
    try:
        from kinematic_conversion import (
            jacobian, translation_to_rotation, rotation_to_wheel_velocities,
            wheel_velocities_to_rotation, wheel_velocity_to_encoder_pulses,
            encoder_pulses_to_wheel_velocity, calculate_velocity_error
        )
        print("✓ kinematic_conversion imports successful")
    except ImportError as e:
        print(f"✗ kinematic_conversion import failed: {e}")
        return False
    
    return True

def test_kinematic_conversions():
    """Test kinematic conversion functions."""
    print("\nTesting kinematic conversions...")
    
    from kinematic_conversion import (
        jacobian, translation_to_rotation, rotation_to_wheel_velocities,
        wheel_velocities_to_rotation, BALL_RADIUS, WHEEL_RADIUS
    )
    
    # Test Jacobian calculation
    try:
        jacob_inv, jacob = jacobian(120.0, BALL_RADIUS, WHEEL_RADIUS, -0.73, 0.85)
        print(f"✓ Jacobian calculation successful")
        print(f"  Jacobian shape: {jacob.shape}")
        print(f"  Inverse Jacobian shape: {jacob_inv.shape}")
    except Exception as e:
        print(f"✗ Jacobian calculation failed: {e}")
        return False
    
    # Test translation to rotation conversion
    try:
        translation_vel = np.array([1.0, 0.0])  # 1 m/s in X direction
        ball_rotation = translation_to_rotation(translation_vel, BALL_RADIUS)
        print(f"✓ Translation to rotation conversion successful")
        print(f"  Input: {translation_vel} m/s")
        print(f"  Output: {ball_rotation} rad/s")
    except Exception as e:
        print(f"✗ Translation to rotation conversion failed: {e}")
        return False
    
    # Test rotation to wheel velocities conversion
    try:
        wheel_velocities = rotation_to_wheel_velocities(ball_rotation, jacob_inv)
        print(f"✓ Rotation to wheel velocities conversion successful")
        print(f"  Input: {ball_rotation} rad/s")
        print(f"  Output: {wheel_velocities} rad/s")
    except Exception as e:
        print(f"✗ Rotation to wheel velocities conversion failed: {e}")
        return False
    
    # Test reverse conversion
    try:
        ball_rotation_back = wheel_velocities_to_rotation(wheel_velocities, jacob)
        print(f"✓ Wheel velocities to rotation conversion successful")
        print(f"  Input: {wheel_velocities} rad/s")
        print(f"  Output: {ball_rotation_back} rad/s")
        
        # Check consistency
        error = np.linalg.norm(ball_rotation - ball_rotation_back)
        print(f"  Conversion error: {error:.6f}")
        if error < 1e-3:
            print("✓ Conversion chain is consistent")
        else:
            print("✗ Conversion chain has significant error")
            return False
    except Exception as e:
        print(f"✗ Wheel velocities to rotation conversion failed: {e}")
        return False
    
    return True

def test_velocity_converter():
    """Test velocity conversion functions."""
    print("\nTesting velocity converter...")
    
    from kinematic_conversion import (
        wheel_velocity_to_encoder_pulses, encoder_pulses_to_wheel_velocity,
        TRANSMISSION_RATIO, ENCODER_PULSES_PER_REV
    )
    
    # Test wheel velocity to encoder pulses
    try:
        wheel_vel_rad_s = 2.0  # 2 rad/s
        encoder_pulses = wheel_velocity_to_encoder_pulses(wheel_vel_rad_s)
        print(f"✓ Wheel velocity to encoder pulses conversion successful")
        print(f"  Input: {wheel_vel_rad_s} rad/s")
        print(f"  Output: {encoder_pulses} pulses/s")
        
        # Manual calculation for verification
        wheel_rev_s = wheel_vel_rad_s / (2 * math.pi)
        encoder_rev_s = wheel_rev_s * TRANSMISSION_RATIO
        expected_pulses = encoder_rev_s * ENCODER_PULSES_PER_REV
        print(f"  Expected: {int(expected_pulses)} pulses/s")
        
        if abs(encoder_pulses - expected_pulses) < 1:
            print("✓ Conversion matches manual calculation")
        else:
            print("✗ Conversion doesn't match manual calculation")
            return False
    except Exception as e:
        print(f"✗ Wheel velocity to encoder pulses conversion failed: {e}")
        return False
    
    # Test encoder pulses to wheel velocity
    try:
        wheel_vel_back = encoder_pulses_to_wheel_velocity(encoder_pulses)
        print(f"✓ Encoder pulses to wheel velocity conversion successful")
        print(f"  Input: {encoder_pulses} pulses/s")
        print(f"  Output: {wheel_vel_back} rad/s")
        
        # Check consistency
        error = abs(wheel_vel_rad_s - wheel_vel_back)
        print(f"  Conversion error: {error:.6f}")
        if error < 1e-3:
            print("✓ Conversion is consistent")
        else:
            print("✗ Conversion has significant error")
            return False
    except Exception as e:
        print(f"✗ Encoder pulses to wheel velocity conversion failed: {e}")
        return False
    
    return True

def test_error_calculation():
    """Test error calculation functions."""
    print("\nTesting error calculation...")
    
    from kinematic_conversion import calculate_velocity_error
    
    # Test error calculation
    try:
        setpoint = 2.0  # rad/s
        feedback = 1.8  # rad/s
        error, ratio = calculate_velocity_error(setpoint, feedback)
        
        print(f"✓ Error calculation successful")
        print(f"  Setpoint: {setpoint} rad/s")
        print(f"  Feedback: {feedback} rad/s")
        print(f"  Error: {error} rad/s")
        print(f"  Ratio: {ratio}")
        
        # Verify error calculation (setpoint - feedback)
        expected_error = setpoint - feedback
        expected_ratio = feedback / setpoint
        
        if abs(error - expected_error) < 1e-6 and abs(ratio - expected_ratio) < 1e-6:
            print("✓ Error calculation is correct")
        else:
            print("✗ Error calculation is incorrect")
            return False
    except Exception as e:
        print(f"✗ Error calculation failed: {e}")
        return False
    
    return True

def main():
    """Run all tests."""
    print("=" * 50)
    print("BASIC FUNCTIONALITY TESTS")
    print("=" * 50)
    
    tests = [
        ("Imports", test_imports),
        ("Kinematic Conversions", test_kinematic_conversions),
        ("Velocity Converter", test_velocity_converter),
        ("Error Calculation", test_error_calculation)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        if test_func():
            passed += 1
            print(f"✓ {test_name} PASSED")
        else:
            print(f"✗ {test_name} FAILED")
    
    print(f"\n{'='*50}")
    print(f"TEST RESULTS: {passed}/{total} tests passed")
    print("=" * 50)
    
    if passed == total:
        print("✓ All tests passed! Basic functionality is working.")
        return True
    else:
        print("✗ Some tests failed. Please fix issues before proceeding.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 