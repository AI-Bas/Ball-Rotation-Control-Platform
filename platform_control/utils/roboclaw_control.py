#!/usr/bin/env python3
"""
RoboClaw Control Module
RoboClaw-specific motion control functionality and motor interface
"""

import time
import math
from typing import Dict, Any, Optional, List, Tuple

class RoboClawMotorInterface:
    """RoboClaw-specific motor interface implementation"""
    
    def __init__(self, roboclaw_interface):
        """Initialize with RoboClaw interface"""
        self.roboclaw_interface = roboclaw_interface
    
    def set_velocity(self, motor_id: int, velocity: float) -> bool:
        """Set velocity for RoboClaw motor"""
        return self.roboclaw_interface.set_velocity(motor_id, velocity)
    
    def get_velocity(self, motor_id: int) -> Optional[float]:
        """Get current velocity for RoboClaw motor"""
        motor_data = self.roboclaw_interface.get_motor_data(motor_id)
        if motor_data:
            # Extract velocity from motor data
            return motor_data.get("encoder_velocity", 0)
        return None
    
    def get_current(self, motor_id: int) -> Optional[float]:
        """Get current draw for RoboClaw motor"""
        motor_data = self.roboclaw_interface.get_motor_data(motor_id)
        if motor_data:
            # Extract current from motor data
            return motor_data.get("current", 0)
        return None
    
    def get_voltage(self, motor_id: int) -> Optional[float]:
        """Get voltage for RoboClaw motor"""
        motor_data = self.roboclaw_interface.get_motor_data(motor_id)
        if motor_data:
            # Extract voltage from motor data
            return motor_data.get("voltage", 0)
        return None
    
    def get_encoder(self, motor_id: int) -> Optional[int]:
        """Get encoder position for RoboClaw motor"""
        motor_data = self.roboclaw_interface.get_motor_data(motor_id)
        if motor_data:
            # Extract encoder from motor data
            return motor_data.get("encoder_position", 0)
        return None
    
    def stop_motor(self, motor_id: int) -> bool:
        """Stop RoboClaw motor"""
        return self.roboclaw_interface.set_velocity(motor_id, 0)
    
    def stop_all_motors(self) -> bool:
        """Stop all RoboClaw motors"""
        success = True
        for motor_id in range(1, 5):  # Assuming 4 motors
            if not self.stop_motor(motor_id):
                success = False
        return success
    
    def get_motor_status(self, motor_id: int) -> Optional[Dict[str, Any]]:
        """Get comprehensive status for a RoboClaw motor"""
        motor_data = self.roboclaw_interface.get_motor_data(motor_id)
        if not motor_data:
            return None
        
        status = {
            "motor_id": motor_id,
            "velocity": motor_data.get("encoder_velocity", 0),
            "current": motor_data.get("current", 0),
            "voltage": motor_data.get("voltage", 0),
            "encoder": motor_data.get("encoder_position", 0),
            "timestamp": time.time()
        }
        
        return status

class CalibrationUtilities:
    """Utilities for RoboClaw motor calibration and testing"""
    
    @staticmethod
    def calculate_motor_efficiency(initial_current: float, operating_current: float, 
                                 initial_voltage: float, operating_voltage: float) -> float:
        """Calculate motor efficiency based on current and voltage changes"""
        if initial_voltage == 0 or operating_voltage == 0:
            return 0.0
        
        initial_power = initial_current * initial_voltage
        operating_power = operating_current * operating_voltage
        
        if initial_power == 0:
            return 0.0
        
        # Efficiency is the ratio of power increase to voltage increase
        power_increase = operating_power - initial_power
        voltage_increase = operating_voltage - initial_voltage
        
        if voltage_increase == 0:
            return 0.0
        
        return power_increase / voltage_increase
    
    @staticmethod
    def analyze_calibration_results(results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze calibration results and provide insights"""
        analysis = {
            "timestamp": time.time(),
            "motor_analysis": {},
            "overall_analysis": {},
            "recommendations": []
        }
        
        total_motors = len(results.get("motor_results", {}))
        successful_motors = 0
        
        for motor_id, motor_result in results.get("motor_results", {}).items():
            if not motor_result.get("success", False):
                continue
            
            successful_motors += 1
            
            initial = motor_result.get("initial_status", {})
            operating = motor_result.get("operating_status", {})
            
            # Calculate efficiency
            efficiency = CalibrationUtilities.calculate_motor_efficiency(
                initial.get("current", 0),
                operating.get("current", 0),
                initial.get("voltage", 0),
                operating.get("voltage", 0)
            )
            
            motor_analysis = {
                "motor_id": motor_id,
                "efficiency": efficiency,
                "current_change": operating.get("current", 0) - initial.get("current", 0),
                "voltage_change": operating.get("voltage", 0) - initial.get("voltage", 0),
                "velocity_achieved": operating.get("velocity", 0),
                "target_velocity": motor_result.get("velocity", 0)
            }
            
            analysis["motor_analysis"][motor_id] = motor_analysis
        
        # Overall analysis
        analysis["overall_analysis"] = {
            "total_motors": total_motors,
            "successful_motors": successful_motors,
            "success_rate": successful_motors / total_motors if total_motors > 0 else 0,
            "average_efficiency": sum(m.get("efficiency", 0) for m in analysis["motor_analysis"].values()) / len(analysis["motor_analysis"]) if analysis["motor_analysis"] else 0
        }
        
        # Generate recommendations
        if analysis["overall_analysis"]["success_rate"] < 1.0:
            analysis["recommendations"].append("Some motors failed calibration - check connections and power")
        
        if analysis["overall_analysis"]["average_efficiency"] < 0.5:
            analysis["recommendations"].append("Low motor efficiency detected - check mechanical load and friction")
        
        return analysis 