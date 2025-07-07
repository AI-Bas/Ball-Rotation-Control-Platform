"""
kinematic_conversion.py
======================

Centralized kinematic and transmission conversion utilities for the Ball Rotation Control Platform.

Provides:
- Jacobian and inverse Jacobian calculation for 3-wheel omni-ball platform
- Translation <-> rotation conversions for ball motion
- Wheel <-> encoder conversions (rad/s, RPM, pulses)
- Composite conversions for setpoint and feedback mapping
- Error calculation utilities for velocity tracking

All demo and control scripts should use these functions for consistent SI unit handling and correct physical mapping.
"""

import numpy as np
from typing import Tuple, List, Optional

# =============================================================================
# PLATFORM CONSTANTS (SI UNITS)
# =============================================================================

# Physical dimensions
WHEEL_DIAMETER = 0.1  # meters
WHEEL_RADIUS = WHEEL_DIAMETER / 2.0  # meters
BALL_RADIUS = 0.111  # meters

# Transmission parameters
TRANSMISSION_RATIO = 13.0 / 3.0  # encoder_rev / wheel_rev
ENCODER_PULSES_PER_REV = 512  # pulses per encoder revolution

# =============================================================================
# KINEMATIC CONVERSIONS
# =============================================================================

def jacobian(beta: float, rBall: float, rOmni: float, rZ: float, rX: float) -> Tuple[np.ndarray, np.ndarray]:
    """
    Calculates the Jacobian and inverse Jacobian matrices for a ball driven by 3 omniwheels
    Args:
        beta: Angle between wheels in degrees
        rBall: Ball radius in meters
        rOmni: Omniwheel radius in meters
        rZ: Z-offset of wheels in meters
        rX: X-offset of wheels in meters
    Returns:
        Tuple containing (inverse Jacobian matrix, Jacobian matrix)
    """
    # Define angles for each omniwheel
    beta1 = np.radians(0)
    beta2 = np.radians(beta)
    beta3 = np.radians(2 * beta)
    
    # Initialize Jacobian matrix
    jacob = np.zeros((3,3))

    jacob[0,0] = rZ;    jacob[0,1] = rZ * np.cos(beta2);    jacob[0,2] = rZ * np.cos(beta3)
    jacob[1,0] = 0;     jacob[1,1] = -rZ * np.sin(beta2);   jacob[1,2] = -rZ * np.sin(beta3)
    jacob[2,0] = -rX;   jacob[2,1] = -rX;                   jacob[2,2] = -rX

    jacob = (rOmni/rBall**2) * jacob
    
    # Calculate inverse of Jacobian matrix
    jacob_inv = np.linalg.inv(jacob)
    
    return jacob_inv, jacob

def translation_to_rotation(translation_vel: np.ndarray, ball_radius: float) -> np.ndarray:
    """
    Convert ball translation velocity to rotation velocity
    Args:
        translation_vel: [vx, vy] translation velocity vector in m/s
        ball_radius: Ball radius in meters
    Returns:
        [wx, wy, wz] rotation velocity vector in rad/s
    """
    # Convert translation to rotation using 1/r * [-vy, vx, 0]
    rotation_vel = np.array([
        -translation_vel[1] / ball_radius,  # wx = -vy/r (angular velocity around X-axis in rad/s)
        translation_vel[0] / ball_radius,   # wy = vx/r (angular velocity around Y-axis in rad/s)
        0.0                                 # wz = 0 (angular velocity around Z-axis in rad/s)
    ])
    return rotation_vel

def rotation_to_wheel_velocities(rotation_vel: np.ndarray, jacob_inv: np.ndarray) -> np.ndarray:
    """
    Convert desired ball rotation velocity to wheel angular velocities
    Args:
        rotation_vel: [wx, wy, wz] desired ball rotation velocity vector in rad/s
        jacob_inv: Inverse Jacobian matrix (3x3)
    Returns:
        [w1, w2, w3] wheel angular velocities in rad/s
    """
    # Matrix multiplication: jacob_inv (3x3) @ rotation_vel (3x1) = wheel_velocities (3x1)
    return jacob_inv @ rotation_vel

def wheel_velocities_to_rotation(wheel_velocities: np.ndarray, jacob: np.ndarray) -> np.ndarray:
    """
    Convert measured wheel angular velocities to ball rotation velocity
    Args:
        wheel_velocities: [w1, w2, w3] measured wheel angular velocities in rad/s
        jacob: Jacobian matrix (3x3)
    Returns:
        [wx, wy, wz] ball rotation velocity vector in rad/s
    """
    # Matrix multiplication: jacob (3x3) @ wheel_velocities (3x1) = rotation_vel (3x1)
    return jacob @ wheel_velocities

# =============================================================================
# TRANSMISSION CONVERSIONS
# =============================================================================

def rpm_to_rad_s(rpm: float) -> float:
    """
    Convert RPM to radians per second
    Args:
        rpm: Revolutions per minute
    Returns:
        Angular velocity in radians per second
    """
    return rpm * 2 * np.pi / 60.0

def rad_s_to_rpm(rad_s: float) -> float:
    """
    Convert radians per second to RPM
    Args:
        rad_s: Angular velocity in radians per second
    Returns:
        Revolutions per minute
    """
    return rad_s * 60.0 / (2 * np.pi)

def wheel_rpm_to_encoder_rpm(wheel_rpm: float, transmission_ratio: float = TRANSMISSION_RATIO) -> float:
    """
    Convert wheel RPM to encoder RPM using transmission ratio
    Args:
        wheel_rpm: Wheel revolutions per minute
        transmission_ratio: Transmission ratio (encoder_rev / wheel_rev)
    Returns:
        Encoder revolutions per minute
    """
    return wheel_rpm * transmission_ratio

def encoder_rpm_to_wheel_rpm(encoder_rpm: float, transmission_ratio: float = TRANSMISSION_RATIO) -> float:
    """
    Convert encoder RPM to wheel RPM using transmission ratio
    Args:
        encoder_rpm: Encoder revolutions per minute
        transmission_ratio: Transmission ratio (encoder_rev / wheel_rev)
    Returns:
        Wheel revolutions per minute
    """
    return encoder_rpm / transmission_ratio

# =============================================================================
# ENCODER CONVERSIONS
# =============================================================================

def encoder_pulses_to_velocity(pulses_per_second: int, pulses_per_rev: int = ENCODER_PULSES_PER_REV) -> float:
    """
    Convert encoder pulses per second to angular velocity in rad/s
    Args:
        pulses_per_second: Encoder pulses per second
        pulses_per_rev: Encoder pulses per revolution
    Returns:
        Angular velocity in radians per second
    """
    # Convert pulses/s to rev/s
    rev_per_second = pulses_per_second / pulses_per_rev
    
    # Convert rev/s to rad/s
    rad_per_second = rev_per_second * 2 * np.pi
    
    return rad_per_second

def velocity_to_encoder_pulses(rad_per_second: float, pulses_per_rev: int = ENCODER_PULSES_PER_REV) -> int:
    """
    Convert angular velocity in rad/s to encoder pulses per second
    Args:
        rad_per_second: Angular velocity in radians per second
        pulses_per_rev: Encoder pulses per revolution
    Returns:
        Encoder pulses per second
    """
    # Convert rad/s to rev/s
    rev_per_second = rad_per_second / (2 * np.pi)
    
    # Convert rev/s to pulses/s
    pulses_per_second = rev_per_second * pulses_per_rev
    
    return int(pulses_per_second)

def wheel_velocity_to_encoder_pulses(wheel_rad_s: float, 
                                   transmission_ratio: float = TRANSMISSION_RATIO,
                                   pulses_per_rev: int = ENCODER_PULSES_PER_REV) -> int:
    """
    Convert wheel angular velocity to encoder pulses per second
    Args:
        wheel_rad_s: Wheel angular velocity in rad/s
        transmission_ratio: Transmission ratio (encoder_rev / wheel_rev)
        pulses_per_rev: Encoder pulses per revolution
    Returns:
        Encoder pulses per second
    """
    # Convert wheel rad/s to encoder rad/s
    encoder_rad_s = wheel_rad_s * transmission_ratio
    
    # Convert encoder rad/s to pulses/s
    return velocity_to_encoder_pulses(encoder_rad_s, pulses_per_rev)

def encoder_pulses_to_wheel_velocity(pulses_per_second: int,
                                   transmission_ratio: float = TRANSMISSION_RATIO,
                                   pulses_per_rev: int = ENCODER_PULSES_PER_REV) -> float:
    """
    Convert encoder pulses per second to wheel angular velocity
    Args:
        pulses_per_second: Encoder pulses per second
        transmission_ratio: Transmission ratio (encoder_rev / wheel_rev)
        pulses_per_rev: Encoder pulses per revolution
    Returns:
        Wheel angular velocity in rad/s
    """
    # Convert pulses/s to encoder rad/s
    encoder_rad_s = encoder_pulses_to_velocity(pulses_per_second, pulses_per_rev)
    
    # Convert encoder rad/s to wheel rad/s
    wheel_rad_s = encoder_rad_s / transmission_ratio
    
    return wheel_rad_s

# =============================================================================
# MOTOR COMMAND CONVERSIONS (VELOCITY FOCUS)
# =============================================================================

def wheel_angular_velocity_to_tangential_velocity(wheel_angular_velocity: float, wheel_radius: float) -> float:
    """
    Convert wheel angular velocity to tangential velocity
    Args:
        wheel_angular_velocity: Wheel angular velocity in rad/s
        wheel_radius: Wheel radius in meters
    Returns:
        Tangential velocity in m/s
    """
    # Tangential velocity = wheel radius * angular velocity
    tangential_velocity = wheel_radius * wheel_angular_velocity
    return tangential_velocity

def tangential_velocity_to_wheel_angular_velocity(tangential_velocity: float, wheel_radius: float) -> float:
    """
    Convert tangential velocity to wheel angular velocity
    Args:
        tangential_velocity: Tangential velocity in m/s
        wheel_radius: Wheel radius in meters
    Returns:
        Wheel angular velocity in rad/s
    """
    # Angular velocity = tangential velocity / wheel radius
    wheel_angular_velocity = tangential_velocity / wheel_radius
    return wheel_angular_velocity

# =============================================================================
# COMPOSITE CONVERSIONS
# =============================================================================

def translation_setpoint_to_wheel_commands(translation_vel: np.ndarray, 
                                         rotation_vel: np.ndarray,
                                         jacob_inv: np.ndarray,
                                         transmission_ratio: float = TRANSMISSION_RATIO,
                                         pulses_per_rev: int = ENCODER_PULSES_PER_REV) -> List[int]:
    """
    Convert translation and rotation setpoints to wheel encoder commands
    Args:
        translation_vel: [vx, vy] translation velocity in m/s
        rotation_vel: [wx, wy, wz] rotation velocity in rad/s
        jacob_inv: Inverse Jacobian matrix
        transmission_ratio: Transmission ratio
        pulses_per_rev: Encoder pulses per revolution
    Returns:
        List of encoder pulses per second for each wheel
    """
    # Step 1: Convert translation to ball rotation
    translation_rotation = translation_to_rotation(translation_vel, BALL_RADIUS)
    
    # Step 2: Combine with rotation setpoint
    total_rotation = translation_rotation + rotation_vel
    
    # Step 3: Convert to wheel velocities
    wheel_velocities = rotation_to_wheel_velocities(total_rotation, jacob_inv)
    
    # Step 4: Convert to encoder pulses
    encoder_pulses = []
    for wheel_vel in wheel_velocities:
        pulses = wheel_velocity_to_encoder_pulses(wheel_vel, transmission_ratio, pulses_per_rev)
        encoder_pulses.append(pulses)
    
    return encoder_pulses

def wheel_encoder_feedback_to_ball_motion(wheel_pulses: List[int],
                                        jacob: np.ndarray,
                                        transmission_ratio: float = TRANSMISSION_RATIO,
                                        pulses_per_rev: int = ENCODER_PULSES_PER_REV) -> Tuple[np.ndarray, np.ndarray]:
    """
    Convert wheel encoder feedback to ball motion
    Args:
        wheel_pulses: List of encoder pulses per second for each wheel
        jacob: Jacobian matrix
        transmission_ratio: Transmission ratio
        pulses_per_rev: Encoder pulses per revolution
    Returns:
        Tuple of (ball_rotation, ball_translation) in rad/s and m/s
    """
    # Step 1: Convert encoder pulses to wheel velocities
    wheel_velocities = []
    for pulses in wheel_pulses:
        wheel_vel = encoder_pulses_to_wheel_velocity(pulses, transmission_ratio, pulses_per_rev)
        wheel_velocities.append(wheel_vel)
    
    # Step 2: Convert wheel velocities to ball rotation
    ball_rotation = wheel_velocities_to_rotation(np.array(wheel_velocities), jacob)
    
    # Step 3: Convert ball rotation to translation (inverse of translation_to_rotation)
    ball_translation = np.array([
        ball_rotation[1] * BALL_RADIUS,  # vx = wy * r
        -ball_rotation[0] * BALL_RADIUS  # vy = -wx * r
    ])
    
    return ball_rotation, ball_translation

# =============================================================================
# ERROR CALCULATION UTILITIES
# =============================================================================

def calculate_velocity_error(setpoint: float, feedback: float) -> Tuple[float, float]:
    """
    Calculate velocity error and ratio
    Args:
        setpoint: Setpoint velocity in rad/s
        feedback: Feedback velocity in rad/s
    Returns:
        Tuple of (error, ratio)
    """
    error = setpoint - feedback  # Correct error calculation: setpoint - feedback
    ratio = feedback / setpoint if setpoint != 0 else 0.0
    return error, ratio

def calculate_velocity_errors(setpoints: List[float], feedbacks: List[float]) -> List[Tuple[float, float]]:
    """
    Calculate velocity errors and ratios for multiple wheels
    Args:
        setpoints: List of setpoint velocities in rad/s
        feedbacks: List of feedback velocities in rad/s
    Returns:
        List of (error, ratio) tuples
    """
    errors = []
    for setpoint, feedback in zip(setpoints, feedbacks):
        error, ratio = calculate_velocity_error(setpoint, feedback)
        errors.append((error, ratio))
    return errors

# =============================================================================
# CONVERSION VALIDATION
# =============================================================================

def validate_conversion_chain():
    """
    Validate the complete conversion chain
    Returns:
        True if all conversions are consistent
    """
    # Test values
    test_translation = np.array([1.0, 0.0])  # 1 m/s in X direction
    test_rotation = np.array([0.0, 0.0, 1.0])  # 1 rad/s around Z axis
    
    # Create Jacobian matrices
    jacob_inv, jacob = jacobian(120.0, BALL_RADIUS, WHEEL_RADIUS, 0.05, 0.05)
    
    # Forward conversion
    wheel_commands = translation_setpoint_to_wheel_commands(
        test_translation, test_rotation, jacob_inv
    )
    
    # Reverse conversion
    ball_rotation, ball_translation = wheel_encoder_feedback_to_ball_motion(
        wheel_commands, jacob
    )
    
    # Check consistency - separate translation and rotation components
    translation_error = np.linalg.norm(test_translation - ball_translation[:2])
    
    # For rotation, we need to account for the translation contribution
    expected_rotation_from_translation = translation_to_rotation(test_translation, BALL_RADIUS)
    expected_total_rotation = expected_rotation_from_translation + test_rotation
    rotation_error = np.linalg.norm(expected_total_rotation - ball_rotation)
    
    print(f"Translation error: {translation_error:.6f}")
    print(f"Rotation error: {rotation_error:.6f}")
    print(f"Expected total rotation: {expected_total_rotation}")
    print(f"Calculated rotation: {ball_rotation}")
    
    return translation_error < 1e-3 and rotation_error < 1e-3

if __name__ == "__main__":
    # Run validation
    print("Validating conversion chain...")
    if validate_conversion_chain():
        print("✓ All conversions validated successfully")
    else:
        print("✗ Conversion validation failed") 