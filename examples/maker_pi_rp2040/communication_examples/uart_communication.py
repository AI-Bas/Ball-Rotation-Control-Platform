#!/usr/bin/env python3
"""
UART Communication Example for Maker Pi RP2040
Demonstrates JSON protocol over serial communication between Raspberry Pi 5 and RP2040
"""

import serial
import json
import time
from typing import Dict, Any, Optional

class MakerPiCommunication:
    """UART communication class for Maker Pi RP2040"""
    
    def __init__(self, port: str = "/dev/ttyACM0", baudrate: int = 115200, timeout: float = 1.0):
        """
        Initialize UART communication
        Args:
            port: Serial port (e.g., /dev/ttyACM0)
            baudrate: Communication speed (115200 recommended)
            timeout: Read timeout in seconds
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_conn = None
        
    def connect(self) -> bool:
        """Connect to Maker Pi RP2040 via UART"""
        try:
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout
            )
            print(f"✓ Connected to Maker Pi RP2040 on {self.port}")
            return True
        except Exception as e:
            print(f"✗ Failed to connect to Maker Pi RP2040: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from Maker Pi RP2040"""
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            print("✓ Disconnected from Maker Pi RP2040")
    
    def send_command(self, command: str, data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Send JSON command to Maker Pi RP2040
        Args:
            command: Command name (e.g., 'read_sensors', 'set_leds')
            data: Additional data for the command
        Returns:
            True if command sent successfully
        """
        if not self.serial_conn or not self.serial_conn.is_open:
            print("✗ Not connected to Maker Pi RP2040")
            return False
        
        try:
            message = {
                "command": command,
                "timestamp": time.time(),
                "id": int(time.time() * 1000) % 10000  # Simple ID generation
            }
            
            if data:
                message["data"] = data
            
            json_message = json.dumps(message) + "\n"
            self.serial_conn.write(json_message.encode())
            print(f"✓ Sent command: {command}")
            return True
            
        except Exception as e:
            print(f"✗ Failed to send command: {e}")
            return False
    
    def read_response(self) -> Optional[Dict[str, Any]]:
        """
        Read JSON response from Maker Pi RP2040
        Returns:
            Parsed JSON response or None if failed
        """
        if not self.serial_conn or not self.serial_conn.is_open:
            print("✗ Not connected to Maker Pi RP2040")
            return None
        
        try:
            if self.serial_conn.in_waiting:
                response = self.serial_conn.readline().decode().strip()
                if response:
                    return json.loads(response)
            return None
            
        except Exception as e:
            print(f"✗ Failed to read response: {e}")
            return None
    
    def send_and_receive(self, command: str, data: Optional[Dict[str, Any]] = None, timeout: float = 2.0) -> Optional[Dict[str, Any]]:
        """
        Send command and wait for response
        Args:
            command: Command to send
            data: Additional data
            timeout: Response timeout in seconds
        Returns:
            Response data or None if failed
        """
        if not self.send_command(command, data):
            return None
        
        # Wait for response
        start_time = time.time()
        while time.time() - start_time < timeout:
            response = self.read_response()
            if response:
                return response
            time.sleep(0.01)
        
        print(f"✗ Timeout waiting for response to command: {command}")
        return None

def main():
    """Main function demonstrating UART communication"""
    print("=" * 60)
    print("MAKER PI RP2040 UART COMMUNICATION EXAMPLE")
    print("=" * 60)
    
    # Initialize communication
    comm = MakerPiCommunication()
    
    # Try to connect
    if not comm.connect():
        print("⚠ Could not connect to Maker Pi RP2040")
        print("  Make sure the RP2040 is running CircuitPython with UART enabled")
        print("  Check that the correct serial port is being used")
        return
    
    try:
        # Example 1: Read sensor data
        print("\n1. Reading sensor data...")
        response = comm.send_and_receive("read_sensors")
        if response:
            print(f"   Response: {response}")
        else:
            print("   No response received")
        
        # Example 2: Set LED states
        print("\n2. Setting LED states...")
        led_data = {
            "leds": [True, False, True, False],  # Pattern
            "brightness": 0.5
        }
        response = comm.send_and_receive("set_leds", led_data)
        if response:
            print(f"   Response: {response}")
        
        # Example 3: Get system status
        print("\n3. Getting system status...")
        response = comm.send_and_receive("get_status")
        if response:
            print(f"   Response: {response}")
        
        # Example 4: Set motor speeds
        print("\n4. Setting motor speeds...")
        motor_data = {
            "motor1": 0.5,   # 50% speed
            "motor2": -0.3   # -30% speed
        }
        response = comm.send_and_receive("set_motors", motor_data)
        if response:
            print(f"   Response: {response}")
        
        # Example 5: Continuous monitoring
        print("\n5. Continuous monitoring (5 seconds)...")
        start_time = time.time()
        while time.time() - start_time < 5:
            response = comm.send_and_receive("read_sensors")
            if response:
                print(f"   Sensors: {response.get('data', {})}")
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\n⚠ Communication interrupted by user")
    
    finally:
        # Cleanup
        comm.disconnect()
        print("\n✓ Communication example completed")

if __name__ == "__main__":
    main() 