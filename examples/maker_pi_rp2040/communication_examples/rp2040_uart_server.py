# CircuitPython UART Server for Maker Pi RP2040
# This code runs on the RP2040 and handles JSON commands from Raspberry Pi 5
# 
# NOTE: This code uses CircuitPython libraries that are only available on the RP2040
# The import errors shown by the linter are expected since this runs in CircuitPython
# environment, not on the Raspberry Pi Python environment.

import board
import busio
import json
import time
import digitalio
import pwmio
from adafruit_motor import motor

# Initialize UART communication
uart = busio.UART(board.TX, board.RX, baudrate=115200)

# Initialize LEDs (example for Maker Pi RP2040)
led_pins = [board.GP0, board.GP1, board.GP2, board.GP3, board.GP4, board.GP5, board.GP6, board.GP7]
leds = []
for pin in led_pins:
    led = digitalio.DigitalInOut(pin)
    led.direction = digitalio.Direction.OUTPUT
    leds.append(led)

# Initialize motors (example for Maker Pi RP2040)
m1a = pwmio.PWMOut(board.GP8, frequency=50)
m1b = pwmio.PWMOut(board.GP9, frequency=50)
motor1 = motor.DCMotor(m1a, m1b)

m2a = pwmio.PWMOut(board.GP10, frequency=50)
m2b = pwmio.PWMOut(board.GP11, frequency=50)
motor2 = motor.DCMotor(m2a, m2b)

# Simulated sensor data
sensor_data = {
    "temperature": 25.0,
    "humidity": 60.0,
    "pressure": 1013.25,
    "light": 500
}

def set_leds(led_states, brightness=1.0):
    """Set LED states based on command"""
    for i, state in enumerate(led_states):
        if i < len(leds):
            leds[i].value = state
    return {"status": "ok", "message": f"LEDs set to {led_states}"}

def set_motors(motor_speeds):
    """Set motor speeds based on command"""
    if "motor1" in motor_speeds:
        motor1.throttle = motor_speeds["motor1"]
    if "motor2" in motor_speeds:
        motor2.throttle = motor_speeds["motor2"]
    return {"status": "ok", "message": f"Motors set to {motor_speeds}"}

def read_sensors():
    """Read sensor data (simulated)"""
    # Simulate sensor reading
    sensor_data["temperature"] += (time.monotonic() % 10 - 5) * 0.1
    sensor_data["humidity"] += (time.monotonic() % 10 - 5) * 0.5
    return {"status": "ok", "data": sensor_data}

def get_status():
    """Get system status"""
    return {
        "status": "ok",
        "data": {
            "uptime": time.monotonic(),
            "free_memory": "32KB",  # Simulated
            "cpu_usage": "15%",     # Simulated
            "led_count": len(leds),
            "motor_count": 2
        }
    }

def process_command(command_data):
    """Process incoming JSON command"""
    command = command_data.get("command", "")
    
    if command == "read_sensors":
        return read_sensors()
    elif command == "set_leds":
        data = command_data.get("data", {})
        led_states = data.get("leds", [False] * len(leds))
        brightness = data.get("brightness", 1.0)
        return set_leds(led_states, brightness)
    elif command == "set_motors":
        data = command_data.get("data", {})
        return set_motors(data)
    elif command == "get_status":
        return get_status()
    else:
        return {"status": "error", "message": f"Unknown command: {command}"}

def send_response(response_data):
    """Send JSON response back to Raspberry Pi"""
    response = {
        "status": response_data.get("status", "ok"),
        "timestamp": time.monotonic(),
        "data": response_data.get("data", {}),
        "message": response_data.get("message", "")
    }
    
    json_response = json.dumps(response) + "\n"
    uart.write(json_response.encode())

def main():
    """Main loop for UART communication"""
    print("CircuitPython UART Server Started")
    print("Waiting for commands from Raspberry Pi...")
    
    # Blink LEDs to indicate ready
    for i in range(3):
        for led in leds:
            led.value = True
        time.sleep(0.2)
        for led in leds:
            led.value = False
        time.sleep(0.2)
    
    while True:
        if uart.in_waiting:
            try:
                # Read command
                command_line = uart.readline().decode().strip()
                if command_line:
                    print(f"Received: {command_line}")
                    
                    # Parse JSON command
                    command_data = json.loads(command_line)
                    
                    # Process command
                    response = process_command(command_data)
                    
                    # Send response
                    send_response(response)
                    print(f"Sent: {response}")
                    
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
                send_response({"status": "error", "message": "Invalid JSON"})
            except Exception as e:
                print(f"Error processing command: {e}")
                send_response({"status": "error", "message": str(e)})
        
        # Small delay to prevent busy waiting
        time.sleep(0.01)

if __name__ == "__main__":
    main() 