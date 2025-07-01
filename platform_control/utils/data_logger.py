"""
Data Logger Utility for Ball Rotation Control Platform

This module provides comprehensive logging capabilities for all operational variables
from all sensors and RoboClaw feedback. It includes dynamic buffering, continuous
operation, and test duration logging with accurate timestamps.
"""

import time
import json
import csv
import os
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
import queue
import numpy as np


@dataclass
class LogEntry:
    """Data structure for a single log entry"""
    timestamp: float
    module: str
    variable: str
    value: Any
    unit: str
    status: str = "normal"
    error: Optional[str] = None


@dataclass
class SafetyEvent:
    """Data structure for safety events"""
    timestamp: float
    event_type: str  # "over_current", "over_voltage", "e_stop", "voltage_clamp"
    severity: str    # "warning", "error", "critical"
    value: float
    threshold: float
    module: str
    description: str


class DataLogger:
    """
    Comprehensive data logger for all operational variables
    
    Features:
    - Dynamic buffering with configurable size
    - Continuous operation logging
    - Test duration logging
    - Real-time error calculation between setpoint and measured values
    - Safety monitoring with over-current/voltage detection
    - Exception handling and filtering
    - CSV export with accurate timestamps
    """
    
    def __init__(self, 
                 buffer_size: int = 1000,
                 log_interval: float = 0.01,  # 100Hz logging
                 enable_safety_monitoring: bool = True,
                 safety_thresholds: Optional[Dict[str, float]] = None):
        """
        Initialize the data logger
        
        Args:
            buffer_size: Maximum number of entries in memory buffer
            log_interval: Time between log entries in seconds
            enable_safety_monitoring: Enable safety event monitoring
            safety_thresholds: Dictionary of safety thresholds
        """
        self.buffer_size = buffer_size
        self.log_interval = log_interval
        self.enable_safety_monitoring = enable_safety_monitoring
        
        # Default safety thresholds
        self.safety_thresholds = safety_thresholds or {
            "over_current_ma": 5000.0,    # 5A
            "over_voltage_v": 15.0,       # 15V
            "under_voltage_v": 10.0,      # 10V
            "temperature_c": 80.0,        # 80°C
            "e_stop_timeout_s": 1.0       # 1 second
        }
        
        # Data storage
        self.log_buffer = queue.Queue(maxsize=buffer_size)
        self.safety_events = []
        self.error_calculations = {}
        
        # Threading
        self.logging_active = False
        self.logging_thread = None
        self.lock = threading.Lock()
        
        # Statistics
        self.stats = {
            "total_entries": 0,
            "dropped_entries": 0,
            "safety_events": 0,
            "start_time": None,
            "last_log_time": None
        }
        
        # Module-specific data sources
        self.data_sources = {}
        
        # Create logs directory
        self.logs_dir = "test_logs/data_logs"
        os.makedirs(self.logs_dir, exist_ok=True)
    
    def add_data_source(self, module: str, data_function: Callable[[], Dict[str, Any]]):
        """
        Add a data source for a specific module
        
        Args:
            module: Module name (e.g., "roboclaw", "ina219", "paa5100")
            data_function: Function that returns current data as dict
        """
        self.data_sources[module] = data_function
    
    def start_logging(self, mode: str = "continuous"):
        """
        Start the logging process
        
        Args:
            mode: "continuous" for ongoing operation, "test" for test duration
        """
        if self.logging_active:
            print("⚠️ Logging already active")
            return
        
        self.logging_active = True
        self.stats["start_time"] = time.time()
        self.stats["last_log_time"] = time.time()
        
        print(f"📊 Starting data logging in {mode} mode...")
        print(f"   Buffer size: {self.buffer_size}")
        print(f"   Log interval: {self.log_interval:.3f}s ({1/self.log_interval:.1f}Hz)")
        print(f"   Safety monitoring: {'enabled' if self.enable_safety_monitoring else 'disabled'}")
        
        # Start logging thread
        self.logging_thread = threading.Thread(target=self._logging_loop, args=(mode,))
        self.logging_thread.daemon = True
        self.logging_thread.start()
    
    def stop_logging(self):
        """Stop the logging process"""
        if not self.logging_active:
            return
        
        self.logging_active = False
        if self.logging_thread:
            self.logging_thread.join(timeout=5.0)
        
        print("📊 Data logging stopped")
        print(f"   Total entries: {self.stats['total_entries']}")
        print(f"   Dropped entries: {self.stats['dropped_entries']}")
        print(f"   Safety events: {self.stats['safety_events']}")
    
    def _logging_loop(self, mode: str):
        """Main logging loop"""
        last_log_time = time.time()
        
        while self.logging_active:
            try:
                current_time = time.time()
                
                # Check if it's time to log
                if current_time - last_log_time >= self.log_interval:
                    self._collect_and_log_data(current_time)
                    last_log_time = current_time
                    self.stats["last_log_time"] = current_time
                
                # Small sleep to prevent busy waiting
                time.sleep(0.001)
                
            except Exception as e:
                print(f"❌ Logging error: {e}")
                self._log_error("data_logger", "logging_loop_error", str(e))
    
    def _collect_and_log_data(self, timestamp: float):
        """Collect data from all sources and log it"""
        try:
            # Collect data from all registered sources
            for module, data_function in self.data_sources.items():
                try:
                    data = data_function()
                    if data:
                        self._log_module_data(module, data, timestamp)
                except Exception as e:
                    self._log_error(module, "data_collection_error", str(e))
            
            # Calculate errors between setpoint and measured values
            self._calculate_errors(timestamp)
            
            # Check safety conditions
            if self.enable_safety_monitoring:
                self._check_safety_conditions(timestamp)
            
        except Exception as e:
            print(f"❌ Data collection error: {e}")
    
    def _log_module_data(self, module: str, data: Dict[str, Any], timestamp: float):
        """Log data for a specific module"""
        for variable, value_info in data.items():
            try:
                if isinstance(value_info, dict):
                    value = value_info.get('value', value_info)
                    unit = value_info.get('unit', '')
                    status = value_info.get('status', 'normal')
                else:
                    value = value_info
                    unit = ''
                    status = 'normal'
                
                # Create log entry
                entry = LogEntry(
                    timestamp=timestamp,
                    module=module,
                    variable=variable,
                    value=value,
                    unit=unit,
                    status=status
                )
                
                # Add to buffer (non-blocking)
                try:
                    self.log_buffer.put_nowait(entry)
                    self.stats["total_entries"] += 1
                except queue.Full:
                    # Remove oldest entry and add new one
                    try:
                        self.log_buffer.get_nowait()
                        self.log_buffer.put_nowait(entry)
                        self.stats["dropped_entries"] += 1
                    except:
                        pass
                
            except Exception as e:
                self._log_error(module, f"variable_log_error_{variable}", str(e))
    
    def _calculate_errors(self, timestamp: float):
        """Calculate errors between setpoint and measured values"""
        try:
            # Get current setpoints and measurements
            setpoints = self._get_current_setpoints()
            measurements = self._get_current_measurements()
            
            for variable in setpoints:
                if variable in measurements:
                    setpoint = setpoints[variable]
                    measured = measurements[variable]
                    
                    if isinstance(setpoint, (int, float)) and isinstance(measured, (int, float)):
                        error = measured - setpoint
                        
                        # Store error calculation
                        self.error_calculations[variable] = {
                            "timestamp": timestamp,
                            "setpoint": setpoint,
                            "measured": measured,
                            "error": error,
                            "absolute_error": abs(error)
                        }
                        
                        # Log error
                        entry = LogEntry(
                            timestamp=timestamp,
                            module="error_calculation",
                            variable=f"{variable}_error",
                            value=error,
                            unit="",
                            status="normal"
                        )
                        
                        try:
                            self.log_buffer.put_nowait(entry)
                        except queue.Full:
                            pass
                
        except Exception as e:
            self._log_error("error_calculation", "calculation_error", str(e))
    
    def _check_safety_conditions(self, timestamp: float):
        """Check for safety violations"""
        try:
            # Get current measurements
            measurements = self._get_current_measurements()
            
            # Check over-current conditions
            for motor in range(1, 5):
                current_key = f"motor_{motor}_current"
                if current_key in measurements:
                    current = measurements[current_key]
                    if abs(current) > self.safety_thresholds["over_current_ma"]:
                        self._log_safety_event(
                            timestamp=timestamp,
                            event_type="over_current",
                            severity="error",
                            value=current,
                            threshold=self.safety_thresholds["over_current_ma"],
                            module=f"motor_{motor}",
                            description=f"Motor {motor} current {current:.1f}mA exceeds threshold"
                        )
            
            # Check voltage conditions
            for channel in range(4):
                voltage_key = f"ina219_channel_{channel}_voltage"
                if voltage_key in measurements:
                    voltage = measurements[voltage_key]
                    if voltage > self.safety_thresholds["over_voltage_v"]:
                        self._log_safety_event(
                            timestamp=timestamp,
                            event_type="over_voltage",
                            severity="error",
                            value=voltage,
                            threshold=self.safety_thresholds["over_voltage_v"],
                            module=f"ina219_channel_{channel}",
                            description=f"Channel {channel} voltage {voltage:.2f}V exceeds threshold"
                        )
                    elif voltage < self.safety_thresholds["under_voltage_v"]:
                        self._log_safety_event(
                            timestamp=timestamp,
                            event_type="under_voltage",
                            severity="warning",
                            value=voltage,
                            threshold=self.safety_thresholds["under_voltage_v"],
                            module=f"ina219_channel_{channel}",
                            description=f"Channel {channel} voltage {voltage:.2f}V below threshold"
                        )
            
            # Check temperature conditions
            for motor in range(1, 5):
                temp_key = f"motor_{motor}_temperature"
                if temp_key in measurements:
                    temp = measurements[temp_key]
                    if temp > self.safety_thresholds["temperature_c"]:
                        self._log_safety_event(
                            timestamp=timestamp,
                            event_type="over_temperature",
                            severity="error",
                            value=temp,
                            threshold=self.safety_thresholds["temperature_c"],
                            module=f"motor_{motor}",
                            description=f"Motor {motor} temperature {temp:.1f}°C exceeds threshold"
                        )
                
        except Exception as e:
            self._log_error("safety_monitoring", "safety_check_error", str(e))
    
    def _log_safety_event(self, timestamp: float, event_type: str, severity: str,
                         value: float, threshold: float, module: str, description: str):
        """Log a safety event"""
        event = SafetyEvent(
            timestamp=timestamp,
            event_type=event_type,
            severity=severity,
            value=value,
            threshold=threshold,
            module=module,
            description=description
        )
        
        with self.lock:
            self.safety_events.append(event)
            self.stats["safety_events"] += 1
        
        print(f"🚨 SAFETY EVENT: {description}")
    
    def _log_error(self, module: str, error_type: str, error_message: str):
        """Log an error"""
        entry = LogEntry(
            timestamp=time.time(),
            module=module,
            variable=error_type,
            value=error_message,
            unit="",
            status="error",
            error=error_message
        )
        
        try:
            self.log_buffer.put_nowait(entry)
        except queue.Full:
            pass
    
    def _get_current_setpoints(self) -> Dict[str, float]:
        """Get current setpoints (placeholder - implement based on your system)"""
        # This should be implemented to return current setpoints from your control system
        return {}
    
    def _get_current_measurements(self) -> Dict[str, float]:
        """Get current measurements from the log buffer"""
        measurements = {}
        
        # Extract latest measurements from buffer
        buffer_list = list(self.log_buffer.queue)
        for entry in buffer_list:
            if isinstance(entry.value, (int, float)):
                measurements[f"{entry.module}_{entry.variable}"] = entry.value
        
        return measurements
    
    def save_logs_to_csv(self, filename: Optional[str] = None) -> str:
        """
        Save all logged data to CSV file
        
        Args:
            filename: Optional filename, auto-generated if not provided
            
        Returns:
            Path to saved CSV file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"data_log_{timestamp}.csv"
        
        filepath = os.path.join(self.logs_dir, filename)
        
        try:
            with open(filepath, 'w', newline='') as csvfile:
                fieldnames = ['timestamp', 'module', 'variable', 'value', 'unit', 'status', 'error']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                
                # Write all entries from buffer
                while not self.log_buffer.empty():
                    entry = self.log_buffer.get()
                    writer.writerow(asdict(entry))
            
            print(f"💾 Data logs saved to: {filepath}")
            return filepath
            
        except Exception as e:
            print(f"❌ Failed to save logs: {e}")
            return ""
    
    def save_safety_events_to_csv(self, filename: Optional[str] = None) -> str:
        """Save safety events to CSV file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"safety_events_{timestamp}.csv"
        
        filepath = os.path.join(self.logs_dir, filename)
        
        try:
            with open(filepath, 'w', newline='') as csvfile:
                fieldnames = ['timestamp', 'event_type', 'severity', 'value', 'threshold', 'module', 'description']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                
                with self.lock:
                    for event in self.safety_events:
                        writer.writerow(asdict(event))
            
            print(f"💾 Safety events saved to: {filepath}")
            return filepath
            
        except Exception as e:
            print(f"❌ Failed to save safety events: {e}")
            return ""
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get logging statistics"""
        with self.lock:
            stats = self.stats.copy()
            stats["buffer_size"] = self.log_buffer.qsize()
            stats["safety_events_count"] = len(self.safety_events)
            stats["data_sources_count"] = len(self.data_sources)
            
            if stats["start_time"]:
                stats["uptime_seconds"] = time.time() - stats["start_time"]
            
            return stats
    
    def clear_buffer(self):
        """Clear the log buffer"""
        while not self.log_buffer.empty():
            self.log_buffer.get()
        
        with self.lock:
            self.safety_events.clear()
            self.error_calculations.clear()
        
        print("🗑️ Log buffer cleared")


# Example usage and integration functions
def create_roboclaw_data_source(roboclaw_interface):
    """Create a data source function for RoboClaw"""
    def roboclaw_data_source():
        data = {}
        try:
            # Get encoder readings
            for motor in range(1, 5):
                # This would need to be implemented based on your RoboClaw interface
                # data[f"motor_{motor}_position"] = roboclaw_interface.get_encoder_position(motor)
                # data[f"motor_{motor}_velocity"] = roboclaw_interface.get_encoder_velocity(motor)
                # data[f"motor_{motor}_current"] = roboclaw_interface.get_motor_current(motor)
                pass
        except Exception as e:
            data["error"] = str(e)
        return data
    return roboclaw_data_source


def create_ina219_data_source(ina219_interface):
    """Create a data source function for INA219"""
    def ina219_data_source():
        data = {}
        try:
            # Get current and voltage readings for all channels
            for channel in range(4):
                # This would need to be implemented based on your INA219 interface
                # data[f"ina219_channel_{channel}_current"] = ina219_interface.get_current(channel)
                # data[f"ina219_channel_{channel}_voltage"] = ina219_interface.get_voltage(channel)
                # data[f"ina219_channel_{channel}_power"] = ina219_interface.get_power(channel)
                pass
        except Exception as e:
            data["error"] = str(e)
        return data
    return ina219_data_source


def create_paa5100_data_source(paa5100_interface):
    """Create a data source function for PAA5100JE-Q"""
    def paa5100_data_source():
        data = {}
        try:
            # Get motion data
            # motion = paa5100_interface.get_motion()
            # data["paa5100_dx"] = motion.get("dx", 0)
            # data["paa5100_dy"] = motion.get("dy", 0)
            # data["paa5100_quality"] = motion.get("quality", 0)
            pass
        except Exception as e:
            data["error"] = str(e)
        return data
    return paa5100_data_source


if __name__ == "__main__":
    # Example usage
    logger = DataLogger(buffer_size=1000, log_interval=0.01)
    
    # Add data sources (these would be your actual interfaces)
    # logger.add_data_source("roboclaw", create_roboclaw_data_source(roboclaw_interface))
    # logger.add_data_source("ina219", create_ina219_data_source(ina219_interface))
    # logger.add_data_source("paa5100", create_paa5100_data_source(paa5100_interface))
    
    # Start logging
    logger.start_logging(mode="continuous")
    
    try:
        # Run for some time
        time.sleep(10)
    finally:
        # Stop and save
        logger.stop_logging()
        logger.save_logs_to_csv()
        logger.save_safety_events_to_csv()
        
        # Print statistics
        stats = logger.get_statistics()
        print(f"📊 Logging Statistics: {stats}") 