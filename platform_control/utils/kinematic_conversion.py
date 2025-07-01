import numpy as np
from typing import Tuple

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
    jacobInv = np.linalg.inv(jacob)
    
    return jacobInv, jacob

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
        -translation_vel[1] / ball_radius,  # wx = -vy/r
        translation_vel[0] / ball_radius,   # wy = vx/r
        0.0                                 # wz = 0
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