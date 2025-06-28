import os
import sys
import json
import time
import platform
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
import serial

# Add the parent directory to sys.path to import from utils
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.roboclaw_interface import RoboClawInterface

class RoboClawTroubleshooter:
    """Helper for troubleshooting RoboClaw connectivity issues."""
    @staticmethod
    def handle_serial_timeout(port, channel=None, log_func=None):
        msg = f"\n[!] Serial timeout or no response from RoboClaw on port {port}"
        if channel:
            msg += f", channel {channel}"
        msg += ".\n"
        msg += "Possible causes:\n"
        msg += " - Incorrect COM port or port in use by another application\n"
        msg += " - USB/RS232 cable not connected or faulty\n"
        msg += " - RoboClaw not powered or not in correct mode\n"
        msg += " - Incorrect address or baudrate configuration\n"
        msg += " - Driver not installed or permissions issue\n"
        msg += " - Address conflict (multiple controllers with same address)\n"
        msg += "\nTroubleshooting steps:\n"
        msg += " 1. Check physical connections and power.\n"
        msg += " 2. Verify correct COM port in platform_config.json.\n"
        msg += " 3. Try disconnecting/reconnecting USB.\n"
        msg += " 4. Use Windows Device Manager to check port status.\n"
        msg += " 5. Ensure only one app is using the port.\n"
        msg += " 6. If using RS232, check wiring and jumpers.\n"
        msg += " 7. Try swapping cables or ports.\n"
        msg += " 8. If both controllers have same address, change one using IonMotion.\n"
        print(msg)
        if log_func:
            log_func("connectivity", msg)

# Remove the ConnectivityAndTroubleshootingTests class and any code that instantiates or uses it 