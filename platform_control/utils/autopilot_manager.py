"""
Intelligent Autopilot Manager for Test Scripts
Handles input queuing, prompt detection, and automatic input provision
"""

import sys
import time
from typing import List, Optional, Dict, Any
import threading
import queue

class AutopilotManager:
    """Intelligent autopilot manager for handling user input prompts automatically"""
    
    def __init__(self, input_sequence: str = "", test_plan: Optional[List[str]] = None):
        """
        Initialize autopilot manager
        
        Args:
            input_sequence: String of inputs to parse character by character
            test_plan: List of specific inputs for complex test scenarios
        """
        self.input_sequence = input_sequence
        self.test_plan = test_plan or []
        self.current_index = 0
        self.input_queue = queue.Queue()
        self.prompt_detected = False
        self.last_prompt_time = 0
        self.input_history = []
        self.menu_depth = 0
        
        # Parse input sequence into queue
        if input_sequence:
            for char in input_sequence:
                self.input_queue.put(char)
        
        # Add test plan inputs
        for input_item in self.test_plan:
            self.input_queue.put(input_item)
    
    def get_next_input(self) -> str:
        """Get next input from queue"""
        try:
            input_val = self.input_queue.get_nowait()
            self.input_history.append(input_val)
            return input_val
        except queue.Empty:
            return "4"  # Default to exit/back option
    
    def has_more_inputs(self) -> bool:
        """Check if more inputs are available"""
        return not self.input_queue.empty()
    
    def detect_prompt(self, output: str) -> bool:
        """Detect if output contains a user input prompt"""
        prompt_indicators = [
            "Enter choice:",
            "Enter choice (",
            "Would you like to",
            "Please enter",
            "Select option",
            "Choose",
            "Input:",
            "user input needed",
            "!! user input needed!!",
            "Enter choice: !! user input needed here",
            "Enter choice: !! user input needed!! errer !!! fix !!",
            "Enter choice (1-",
            "Enter choice (1-4):",
            "Enter choice (1-6):",
            "Enter choice (1-5):"
        ]
        
        for indicator in prompt_indicators:
            if indicator.lower() in output.lower():
                return True
        return False
    
    def provide_input(self, prompt_output: str = "") -> str:
        """Provide appropriate input based on prompt context"""
        if self.detect_prompt(prompt_output):
            self.prompt_detected = True
            self.last_prompt_time = time.time()
            self.menu_depth += 1
            
            # Intelligent input selection based on prompt context
            if "exit" in prompt_output.lower() or "quit" in prompt_output.lower():
                return "4"  # Exit option
            elif "back" in prompt_output.lower():
                return "5"  # Back option
            elif "yes" in prompt_output.lower() or "continue" in prompt_output.lower():
                return "y"
            elif "no" in prompt_output.lower() or "skip" in prompt_output.lower():
                return "n"
            elif "1-4" in prompt_output:
                # Sub-menu with 4 options, likely need to go back
                return "4"
            elif "1-5" in prompt_output:
                # Sub-menu with 5 options, likely need to go back
                return "5"
            elif "1-6" in prompt_output:
                # Sub-menu with 6 options, likely need to go back
                return "6"
            else:
                return self.get_next_input()
        
        return self.get_next_input()
    
    def create_test_plan(self, script_name: str) -> List[str]:
        """Create comprehensive test plan for specific script"""
        test_plans = {
            "connectivity_test": ["1"],  # Run connectivity test
            "roboclaw_test": ["1", "2", "3", "4", "5", "6", "6", "6", "6", "6", "6", "6"],  # Full test cycle
            "ina219_test_menu": ["1", "2", "3", "4"],  # All power sensor tests
            "optical_flow_test_menu": ["1", "2", "3", "4", "5", "6"],  # Full optical flow test
            "maker_pi_tests": ["1", "2", "3", "4", "5", "6"],  # Full maker pi test
            "calibration_tests": ["1", "2", "3", "4", "5", "6"],  # Full calibration test
            "performance_test": ["1", "2", "3", "4", "4"],  # All performance tests + exit
            "code_integration_test": ["1", "2", "3", "4"],  # Code integration tests
            "system_test": ["1", "2", "3", "4", "5", "6"]  # Full system test
        }
        
        return test_plans.get(script_name, ["4"])  # Default to exit
    
    def add_input_sequence(self, sequence: List[str]):
        """Add additional input sequence to queue"""
        for input_item in sequence:
            self.input_queue.put(input_item)
    
    def get_input_history(self) -> List[str]:
        """Get history of inputs used"""
        return self.input_history.copy()
    
    def reset(self):
        """Reset autopilot state"""
        self.current_index = 0
        self.prompt_detected = False
        self.last_prompt_time = 0
        self.input_history = []
        self.menu_depth = 0

def create_autopilot_manager(script_name: str, input_sequence: str = "") -> AutopilotManager:
    """Factory function to create autopilot manager for specific script"""
    test_plan = AutopilotManager().create_test_plan(script_name)
    return AutopilotManager(input_sequence, test_plan)

# Global autopilot manager instance
_autopilot_manager: Optional[AutopilotManager] = None

def get_autopilot_manager() -> Optional[AutopilotManager]:
    """Get global autopilot manager instance"""
    return _autopilot_manager

def set_autopilot_manager(manager: AutopilotManager):
    """Set global autopilot manager instance"""
    global _autopilot_manager
    _autopilot_manager = manager

def get_autopilot_input(prompt: str = "") -> str:
    """Get input from autopilot manager or user"""
    manager = get_autopilot_manager()
    if manager and manager.has_more_inputs():
        return manager.provide_input(prompt)
    return input(prompt)

def is_autopilot_mode() -> bool:
    """Check if autopilot mode is active"""
    return _autopilot_manager is not None 