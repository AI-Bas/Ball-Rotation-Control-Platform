#!/usr/bin/env python3
"""
Simple script to detect available COM ports on Windows
"""

import serial.tools.list_ports
import sys

def detect_com_ports():
    """Detect and list all available COM ports"""
    print("Detecting available COM ports...")
    print("=" * 50)
    
    ports = serial.tools.list_ports.comports()
    
    if not ports:
        print("No COM ports found!")
        return []
    
    print(f"Found {len(ports)} COM port(s):")
    print()
    
    for i, port in enumerate(ports, 1):
        print(f"{i}. {port.device}")
        print(f"   Description: {port.description}")
        print(f"   Hardware ID: {port.hwid}")
        print(f"   Manufacturer: {port.manufacturer}")
        print(f"   Product: {port.product}")
        print(f"   VID:PID: {port.vid:04X}:{port.pid:04X}")
        print()
    
    return [port.device for port in ports]

def test_roboclaw_connection(port):
    """Test if a port might be a RoboClaw"""
    try:
        # Try to open the port
        ser = serial.Serial(port, timeout=1)
        
        # Try to read version (this is a common RoboClaw command)
        # Send: 0x80 (address) + 0x15 (GETVERSION command)
        ser.write(bytes([0x80, 0x15]))
        
        # Try to read response
        response = ser.read(48)  # Version string is up to 48 bytes
        
        ser.close()
        
        if response:
            # Check if response looks like a version string
            try:
                version_str = response.decode('ascii').rstrip('\x00')
                if "RoboClaw" in version_str or len(version_str) > 0:
                    return True, version_str
            except:
                pass
        
        return False, None
        
    except Exception as e:
        return False, str(e)

if __name__ == "__main__":
    print("RoboClaw Port Detection Tool")
    print("=" * 50)
    
    # Detect all COM ports
    available_ports = detect_com_ports()
    
    if not available_ports:
        print("No COM ports available. Please check your USB connections.")
        sys.exit(1)
    
    print("Testing each port for RoboClaw compatibility...")
    print("=" * 50)
    
    roboclaw_ports = []
    
    for port in available_ports:
        print(f"Testing {port}...")
        is_roboclaw, result = test_roboclaw_connection(port)
        
        if is_roboclaw:
            print(f"  ✓ {port} appears to be a RoboClaw!")
            print(f"    Version: {result}")
            roboclaw_ports.append(port)
        else:
            print(f"  ✗ {port} is not a RoboClaw or not responding")
            if result:
                print(f"    Error: {result}")
        print()
    
    if roboclaw_ports:
        print("RoboClaw devices found:")
        for i, port in enumerate(roboclaw_ports, 1):
            print(f"  {i}. {port}")
        
        print("\nRecommendation:")
        if len(roboclaw_ports) >= 2:
            print(f"Update platform_config.json:")
            print(f"  RC1 port: {roboclaw_ports[0]}")
            print(f"  RC2 port: {roboclaw_ports[1]}")
        else:
            print(f"Only one RoboClaw found on {roboclaw_ports[0]}")
            print("Check if both controllers are properly connected.")
    else:
        print("No RoboClaw devices detected.")
        print("Please check:")
        print("1. USB connections are secure")
        print("2. RoboClaw drivers are installed")
        print("3. Controllers are powered on") 