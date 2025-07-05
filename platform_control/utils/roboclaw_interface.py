#!/usr/bin/env python3
"""
Simplified RoboClaw Interface Module
Streamlined interface that uses roboclaw_3.py directly without duplication
Under 400 lines with essential functionality only
"""

import os
import json
import time
from datetime import datetime
from .roboclaw_3 import Roboclaw

class RoboClawInterface:
    def __init__(self, use_dual_controllers: bool = True, autopilot_mode: bool = False):
        self.use_dual_controllers = use_dual_controllers
        self.autopilot_mode = autopilot_mode
        self.connected = False
        self.config = self.load_platform_config()
        self.roboclaw_config = self.config.get('hardware', {}).get('roboclaw', {})
        self.rc1 = None
        self.rc2 = None
        self.controller_info = {}
        self.setup_controllers()

    def load_platform_config(self):
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'platform_config.json')
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading platform config: {e}")
            return {}

    def _parse_address(self, address_value):
        if isinstance(address_value, str):
            if address_value.startswith('0x'):
                return int(address_value, 16)
            else:
                return int(address_value)
        return address_value

    def setup_controllers(self):
        """Setup controllers with proper addressing to avoid conflicts"""
        controllers = self.roboclaw_config.get('controllers', {})
        
        # Use the same address for both controllers since they're on different USB ports
        # This avoids conflicts while allowing both to work
        address_mapping = {
            'rc1': 0x80,  # Primary controller
            'rc2': 0x80   # Secondary controller (same address, different port)
        }
        
        for controller_name in ['rc1', 'rc2']:
            if controller_name in controllers:
                controller_config = controllers[controller_name]
                # Use the address mapping instead of config address
                self.controller_info[controller_name] = {
                    'port': controller_config.get('port', ''),
                    'address': address_mapping[controller_name],  # Use same address
                    'connected': False,
                    'description': controller_config.get('description', ''),
                    'original_address': controller_config.get('address', '0x80')  # Keep original for reference
                }
            else:
                self.controller_info[controller_name] = {
                    'port': '',
                    'address': address_mapping[controller_name],  # Use same address
                    'connected': False,
                    'description': '',
                    'original_address': '0x80'
                }

    def connect(self):
        print("🔌 Connecting to RoboClaw controllers...")
        success = False
        controllers_to_connect = ['rc1']
        if self.use_dual_controllers:
            controllers_to_connect.append('rc2')
        for controller_name in controllers_to_connect:
            if controller_name not in self.controller_info:
                print(f"   ❌ {controller_name} not configured")
                continue
            controller_info = self.controller_info[controller_name]
            port = controller_info['port']
            address = controller_info['address']
            if not port:
                print(f"   ❌ {controller_name} port not configured")
                continue
            print(f"   🔗 Connecting to {controller_name} on {port}...")
            roboclaw = Roboclaw(port, 0, timeout=0.5, retries=2)
            if not roboclaw.Open():
                print(f"   ❌ Failed to open {controller_name} on {port}")
                continue
            version_result = roboclaw.ReadVersion(address)
            if version_result[0]:
                print(f"   ✅ {controller_name} connected successfully")
                print(f"      Version: {version_result[1]}")
                self.controller_info[controller_name]['connected'] = True
                setattr(self, controller_name, roboclaw)
                success = True  # At least one controller connected
            else:
                print(f"   ❌ {controller_name} connection failed - no response")
                roboclaw._port.close()
        self.connected = success
        return success

    def disconnect(self):
        for controller_name in ['rc1', 'rc2']:
            if hasattr(self, controller_name):
                controller = getattr(self, controller_name)
                if controller and hasattr(controller, '_port'):
                    controller._port.close()
                self.controller_info[controller_name]['connected'] = False
        self.connected = False

    def set_velocity(self, motor_id: int, velocity: float) -> bool:
        if not self.connected:
            print("❌ Not connected to controllers")
            return False
        motor_mapping = self.roboclaw_config.get('motor_mapping', {})
        motor_key = f"motor{motor_id}"
        if motor_key not in motor_mapping:
            print(f"❌ Motor {motor_id} not mapped")
            return False
        motor_config = motor_mapping[motor_key]
        controller_name = motor_config.get('controller', 'rc1')
        channel = motor_config.get('channel', 'A')
        if controller_name not in self.controller_info or not self.controller_info[controller_name]['connected']:
            print(f"❌ Controller {controller_name} not connected")
            return False
        controller = getattr(self, controller_name)
        address = self.controller_info[controller_name]['address']
        qpps = int(velocity * 100)
        try:
            if channel == 'A':
                result = controller.SpeedM1(address, qpps)
            elif channel == 'B':
                result = controller.SpeedM2(address, qpps)
            else:
                print(f"❌ Invalid channel {channel}")
                return False
            if result:
                print(f"✅ Motor {motor_id} velocity set to {velocity}")
                return True
            else:
                print(f"❌ Failed to set motor {motor_id} velocity")
                return False
        except Exception as e:
            print(f"❌ Error setting motor {motor_id} velocity: {e}")
            return False

    def get_motor_data(self, motor_id: int):
        if not self.connected:
            return None
        motor_mapping = self.roboclaw_config.get('motor_mapping', {})
        motor_key = f"motor{motor_id}"
        if motor_key not in motor_mapping:
            return None
        motor_config = motor_mapping[motor_key]
        controller_name = motor_config.get('controller', 'rc1')
        channel = motor_config.get('channel', 'A')
        if controller_name not in self.controller_info or not self.controller_info[controller_name]['connected']:
            return None
        controller = getattr(self, controller_name)
        address = self.controller_info[controller_name]['address']
        try:
            data = {
                'motor_id': motor_id,
                'controller': controller_name,
                'channel': channel,
                'timestamp': time.time()
            }
            if channel == 'A':
                encoder_result = controller.ReadEncM1(address)
                speed_result = controller.ReadSpeedM1(address)
            else:
                encoder_result = controller.ReadEncM2(address)
                speed_result = controller.ReadSpeedM2(address)
            if encoder_result[0]:
                data['encoder_position'] = encoder_result[1]
                data['encoder_velocity'] = encoder_result[2]
            if speed_result[0]:
                data['speed'] = speed_result[1]
                data['speed_status'] = speed_result[2]
            current_result = controller.ReadCurrents(address)
            if current_result[0]:
                if channel == 'A':
                    data['current'] = current_result[1]
                else:
                    data['current'] = current_result[2]
            voltage_result = controller.ReadMainBatteryVoltage(address)
            if voltage_result[0]:
                data['voltage'] = voltage_result[1] / 10.0
            return data
        except Exception as e:
            print(f"❌ Error reading motor {motor_id} data: {e}")
            return None

    def read_error_state(self, controller_name: str = 'rc1'):
        """Read error state from controller"""
        if not self.connected or controller_name not in self.controller_info:
            return None
        if not self.controller_info[controller_name]['connected']:
            return None
        controller = getattr(self, controller_name)
        address = self.controller_info[controller_name]['address']
        try:
            error_result = controller.ReadError(address)
            if error_result[0]:
                error_code = error_result[1]
                error_info = self.decode_error(error_code)
                return {
                    'controller': controller_name,
                    'error_code': error_code,
                    'error_info': error_info,
                    'timestamp': time.time()
                }
        except Exception as e:
            print(f"❌ Error reading error state: {e}")
        return None

    def decode_error(self, error_code: int):
        """Decode RoboClaw error code"""
        errors = {
            0x00000000: "Normal",
            0x00000001: "M1 CMD timeout",
            0x00000002: "M2 CMD timeout", 
            0x00000004: "M1POS",
            0x00000008: "M2POS",
            0x00000010: "M1SPD",
            0x00000020: "M2SPD",
            0x00000040: "M1ACC",
            0x00000080: "M2ACC",
            0x00000100: "M1OV",
            0x00000200: "M2OV",
            0x00000400: "M1ST",
            0x00000800: "M2ST",
            0x00001000: "M1P",
            0x00002000: "M2P",
            0x00004000: "M1I",
            0x00008000: "M2I",
            0x00010000: "M1D",
            0x00020000: "M2D",
            0x00040000: "M1V",
            0x00080000: "M2V",
            0x00100000: "M1T",
            0x00200000: "M2T",
            0x00400000: "M1E",
            0x00800000: "M2E",
            0x01000000: "M1M",
            0x02000000: "M2M",
            0x04000000: "M1S",
            0x08000000: "M2S",
            0x10000000: "M1L",
            0x20000000: "M2L",
            0x40000000: "M1R",
            0x80000000: "M2R"
        }
        active_errors = []
        for code, description in errors.items():
            if error_code & code:
                active_errors.append(description)
        return {
            'active_errors': active_errors,
            'error_count': len(active_errors),
            'is_error': error_code != 0
        }

    def test_estop_functionality(self, controller_name: str = 'rc1') -> bool:
        """Test E-Stop functionality with human confirmation"""
        if not self.connected or controller_name not in self.controller_info:
            print("❌ Controller not connected")
            return False
        if not self.controller_info[controller_name]['connected']:
            print("❌ Controller not connected")
            return False
        print(f"\n🛑 Testing E-Stop functionality on {controller_name}")
        print("This test requires human confirmation of E-Stop behavior.")
        print("The E-Stop should be NON-LATCHING (mode 1) - it should reset automatically when released.")
        if not self.autopilot_mode:
            input("Press Enter when ready to test E-Stop...")
        controller = getattr(self, controller_name)
        address = self.controller_info[controller_name]['address']
        try:
            # Read pin functions to verify E-Stop configuration
            pin_result = controller.ReadPinFunctions(address)
            if pin_result[0]:
                s3_mode = pin_result[1]
                print(f"   📌 S3 pin mode: {s3_mode} (1 = E-Stop)")
                if s3_mode != 1:
                    print("   ⚠️ S3 pin not configured for E-Stop (mode 1)")
                    print("   🔧 Configuring S3 pin for E-Stop...")
                    controller.SetPinFunctions(address, 1, 2, 2)  # S3=E-Stop, S4=S5=Voltage clamp
                    print("   ✅ S3 pin configured for E-Stop")
            # Test E-Stop by reading error state
            print("   🔍 Reading E-Stop state...")
            error_state = self.read_error_state(controller_name)
            if error_state and error_state['error_info']['is_error']:
                print("   ⚠️ E-Stop is active (errors detected)")
                print("   📋 Active errors:")
                for error in error_state['error_info']['active_errors']:
                    print(f"      - {error}")
            else:
                print("   ✅ E-Stop is not active (no errors)")
            if not self.autopilot_mode:
                input("Press Enter to continue...")
            return True
        except Exception as e:
            print(f"❌ Error testing E-Stop: {e}")
            return False

    def monitor_motor_channels(self):
        """Monitor all motor channels for encoder changes"""
        if not self.connected:
            print("❌ Not connected to controllers")
            return False
        
        print("\n📊 Motor Channel Monitoring")
        print("Monitoring all motor channels for encoder changes...")
        print("Press any key to stop monitoring")
        print("-" * 50)
        
        # Get all motor mappings
        motor_mapping = self.roboclaw_config.get('motor_mapping', {})
        monitored_channels = {}
        
        # Initialize monitoring for each motor
        for motor_id in range(1, 5):
            motor_key = f"motor{motor_id}"
            if motor_key in motor_mapping:
                motor_config = motor_mapping[motor_key]
                controller_name = motor_config.get('controller', 'rc1')
                channel = motor_config.get('channel', 'A')
                
                if controller_name in self.controller_info and self.controller_info[controller_name]['connected']:
                    controller = getattr(self, controller_name)
                    address = self.controller_info[controller_name]['address']
                    
                    # Read initial position
                    if channel == 'A':
                        encoder_result = controller.ReadEncM1(address)
                    else:
                        encoder_result = controller.ReadEncM2(address)
                    
                    if encoder_result[0]:
                        monitored_channels[motor_id] = {
                            'controller': controller_name,
                            'channel': channel,
                            'controller_obj': controller,
                            'address': address,
                            'initial_position': encoder_result[1],
                            'last_position': encoder_result[1],
                            'last_change': 0
                        }
                        print(f"   Motor {motor_id}: {controller_name}, Channel {channel}, Initial: {encoder_result[1]}")
        
        if not monitored_channels:
            print("   ❌ No motors available for monitoring")
            return False
        
        print("\nMonitoring started. Press any key to stop...")
        
        try:
            import select
            import sys
            
            while True:
                # Check for key press (non-blocking)
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    break
                
                # Monitor each channel
                for motor_id, info in monitored_channels.items():
                    try:
                        if info['channel'] == 'A':
                            encoder_result = info['controller_obj'].ReadEncM1(info['address'])
                        else:
                            encoder_result = info['controller_obj'].ReadEncM2(info['address'])
                        
                        if encoder_result[0]:
                            current_position = encoder_result[1]
                            change = current_position - info['last_position']
                            
                            if change != 0:
                                info['last_position'] = current_position
                                info['last_change'] = change
                                total_change = current_position - info['initial_position']
                                
                                print(f"   Motor {motor_id} ({info['controller']}, {info['channel']}): "
                                      f"Pos={current_position}, Change={change:+d}, Total={total_change:+d}")
                    except Exception as e:
                        print(f"   ❌ Error monitoring motor {motor_id}: {e}")
                
                time.sleep(0.1)  # 100ms monitoring interval
                
        except KeyboardInterrupt:
            pass
        
        print("\n📊 Monitoring Summary:")
        for motor_id, info in monitored_channels.items():
            total_change = info['last_position'] - info['initial_position']
            print(f"   Motor {motor_id} ({info['controller']}, {info['channel']}): "
                  f"Total change = {total_change:+d}")
        
        return True

    def identify_motor_mapping(self):
        """New motor mapping system - asks for motor movement and monitors encoder changes"""
        if not self.connected:
            print("❌ Not connected to controllers")
            return False
        
        print("\n🔍 Motor Mapping Identification - New System")
        print("=" * 60)
        print("This process will:")
        print("1. Ask you to move Motor 1, then monitor which encoder changes")
        print("2. Ask you to move Motor 2, then monitor which encoder changes")
        print("3. Continue for Motor 3 and Motor 4")
        print("4. Press Enter to skip any motor")
        print("5. Show summary and option to save mapping")
        print("=" * 60)
        
        # Initialize monitoring for all channels
        monitored_channels = {}
        identified_motors = {}
        
        # Setup monitoring for all possible channels
        for controller_name in ['rc1', 'rc2']:
            if controller_name in self.controller_info and self.controller_info[controller_name]['connected']:
                controller = getattr(self, controller_name)
                address = self.controller_info[controller_name]['address']
                
                # Monitor both channels A and B for each controller
                for channel in ['A', 'B']:
                    channel_key = f"{controller_name}_{channel}"
                    
                    # Read initial encoder position
                    if channel == 'A':
                        encoder_result = controller.ReadEncM1(address)
                    else:
                        encoder_result = controller.ReadEncM2(address)
                    
                    if encoder_result[0]:
                        monitored_channels[channel_key] = {
                            'controller': controller_name,
                            'channel': channel,
                            'controller_obj': controller,
                            'address': address,
                            'initial_position': encoder_result[1],
                            'last_position': encoder_result[1],
                            'motor_id': None  # Will be assigned when detected
                        }
                        print(f"   📊 Monitoring {controller_name} Channel {channel}: Initial position = {encoder_result[1]}")
        
        if not monitored_channels:
            print("❌ No channels available for monitoring")
            return False
        
        # Test each motor individually
        for motor_id in range(1, 5):
            print(f"\n🔄 Testing Motor {motor_id}")
            print("-" * 40)
            
            if not self.autopilot_mode:
                input(f"Please move Motor {motor_id} (turn the wheel) and press Enter when ready...")
            else:
                print(f"   🤖 Autopilot: Testing Motor {motor_id}")
                time.sleep(2)  # Give time for movement
            
            # Monitor all channels for changes
            start_time = time.time()
            timeout = 10  # 10 second timeout
            detected_channel = None
            
            while time.time() - start_time < timeout:
                for channel_key, channel_info in monitored_channels.items():
                    if channel_info['motor_id'] is not None:
                        continue  # This channel already assigned
                    
                    try:
                        # Read current encoder position
                        if channel_info['channel'] == 'A':
                            encoder_result = channel_info['controller_obj'].ReadEncM1(channel_info['address'])
                        else:
                            encoder_result = channel_info['controller_obj'].ReadEncM2(channel_info['address'])
                        
                        if encoder_result[0]:
                            current_position = encoder_result[1]
                            change = current_position - channel_info['last_position']
                            
                            # Check for significant movement (more than 100 counts)
                            if abs(change) > 100:
                                print(f"   ✅ Detected movement on {channel_key}: Change = {change:+d}")
                                detected_channel = channel_key
                                channel_info['motor_id'] = motor_id
                                channel_info['last_position'] = current_position
                                
                                # Calculate total change from initial
                                total_change = current_position - channel_info['initial_position']
                                
                                identified_motors[motor_id] = {
                                    'controller': channel_info['controller'],
                                    'channel': channel_info['channel'],
                                    'address': channel_info['address'],
                                    'encoder_change': total_change,
                                    'detection_time': time.time(),
                                    'channel_key': channel_key
                                }
                                break
                    except Exception as e:
                        print(f"   ❌ Error monitoring {channel_key}: {e}")
                
                if detected_channel:
                    break
                
                time.sleep(0.1)  # 100ms monitoring interval
            
            if detected_channel:
                print(f"   ✅ Motor {motor_id} mapped to {detected_channel}")
            else:
                print(f"   ⏭️ Motor {motor_id} skipped (no movement detected)")
        
        # Show summary
        if identified_motors:
            print("\n📋 Motor Mapping Summary:")
            print("=" * 50)
            for motor_id, info in identified_motors.items():
                print(f"   Motor {motor_id}: {info['controller']}, Channel {info['channel']}")
                print(f"      Address: 0x{info['address']:02X}")
                print(f"      Encoder change: {info['encoder_change']}")
                print(f"      Channel key: {info['channel_key']}")
            
            # Ask to save mapping
            if not self.autopilot_mode:
                save_choice = input("\nSave this mapping to platform_config.json? (y/n): ").lower().strip()
                if save_choice == 'y':
                    self.update_motor_mapping_new(identified_motors)
                    return True
                else:
                    print("Mapping not saved")
                    return False
            else:
                self.update_motor_mapping_new(identified_motors)
                return True
        else:
            print("❌ No motors identified")
            return False

    def verify_motor_mapping(self):
        if not self.connected:
            print("❌ Not connected to controllers")
            return False
        print("\n🔍 Motor Mapping Verification")
        print("Testing each mapped motor with forward/backward commands...")
        motor_mapping = self.roboclaw_config.get('motor_mapping', {})
        verified_motors = {}
        for motor_id in range(1, 5):
            motor_key = f"motor{motor_id}"
            if motor_key not in motor_mapping:
                continue
            motor_config = motor_mapping[motor_key]
            controller_name = motor_config.get('controller', 'rc1')
            channel = motor_config.get('channel', 'A')
            if controller_name not in self.controller_info or not self.controller_info[controller_name]['connected']:
                continue
            controller = getattr(self, controller_name)
            address = self.controller_info[controller_name]['address']
            print(f"\n🔄 Verifying Motor {motor_id} ({controller_name}, channel {channel})")
            try:
                if channel == 'A':
                    initial_result = controller.ReadEncM1(address)
                else:
                    initial_result = controller.ReadEncM2(address)
                if not initial_result[0]:
                    print(f"   ❌ Failed to read initial encoder for motor {motor_id}")
                    continue
                initial_position = initial_result[1]
                print(f"   📊 Initial position: {initial_position}")
                test_velocity = 500
                if channel == 'A':
                    controller.SpeedM1(address, test_velocity)
                else:
                    controller.SpeedM2(address, test_velocity)
                print(f"   ⚡ Sent forward command (velocity: {test_velocity})")
                time.sleep(1.0)
                if channel == 'A':
                    during_result = controller.ReadEncM1(address)
                else:
                    during_result = controller.ReadEncM2(address)
                if during_result[0]:
                    during_position = during_result[1]
                    forward_change = during_position - initial_position
                    print(f"   📊 During movement: {during_position} (change: {forward_change})")
                    if channel == 'A':
                        controller.SpeedM1(address, 0)
                    else:
                        controller.SpeedM2(address, 0)
                    time.sleep(0.5)
                    if channel == 'A':
                        controller.SpeedM1(address, -test_velocity)
                    else:
                        controller.SpeedM2(address, -test_velocity)
                    print(f"   ⚡ Sent backward command (velocity: -{test_velocity})")
                    time.sleep(1.0)
                    if channel == 'A':
                        final_result = controller.ReadEncM1(address)
                    else:
                        final_result = controller.ReadEncM2(address)
                    if final_result[0]:
                        final_position = final_result[1]
                        total_change = final_position - initial_position
                        if channel == 'A':
                            controller.SpeedM1(address, 0)
                        else:
                            controller.SpeedM2(address, 0)
                        print(f"   📊 Final position: {final_position} (total change: {total_change})")
                        if abs(forward_change) > 50 and abs(total_change) > 50:
                            verified_motors[motor_id] = {
                                'controller': controller_name,
                                'channel': channel,
                                'forward_change': forward_change,
                                'total_change': total_change,
                                'verification_time': time.time()
                            }
                            print(f"   ✅ Motor {motor_id} verification successful")
                        else:
                            print(f"   ❌ Motor {motor_id} insufficient movement detected")
                    else:
                        print(f"   ❌ Failed to read final position for motor {motor_id}")
                        if channel == 'A':
                            controller.SpeedM1(address, 0)
                        else:
                            controller.SpeedM2(address, 0)
                else:
                    print(f"   ❌ Failed to read position during movement for motor {motor_id}")
                    if channel == 'A':
                        controller.SpeedM1(address, 0)
                    else:
                        controller.SpeedM2(address, 0)
            except Exception as e:
                print(f"   ❌ Error verifying motor {motor_id}: {e}")
                try:
                    if channel == 'A':
                        controller.SpeedM1(address, 0)
                    else:
                        controller.SpeedM2(address, 0)
                except:
                    pass
        if verified_motors:
            print("\n📋 Motor Verification Results:")
            for motor_id, info in verified_motors.items():
                print(f"   ✅ Motor {motor_id}: {info['controller']}, channel {info['channel']}")
                print(f"      Forward change: {info['forward_change']}")
                print(f"      Total change: {info['total_change']}")
            return True
        else:
            print("❌ No motors verified successfully")
            return False

    def update_motor_mapping(self, identified_motors):
        try:
            motor_mapping = self.roboclaw_config.get('motor_mapping', {})
            for motor_id, info in identified_motors.items():
                motor_key = f"motor{motor_id}"
                if motor_key in motor_mapping:
                    motor_mapping[motor_key].update({
                        'controller': info['controller'],
                        'channel': info['channel'],
                        'encoder_change': info['encoder_change'],
                        'detection_time': info['detection_time'],
                        'last_updated': datetime.now().isoformat(),
                        'updated_by': 'automated_motor_mapping'
                    })
            self.roboclaw_config['motor_mapping'] = motor_mapping
            self.config['hardware']['roboclaw'] = self.roboclaw_config
            config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'platform_config.json')
            with open(config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
            print("✅ Motor mapping updated in platform configuration")
        except Exception as e:
            print(f"❌ Error updating motor mapping: {e}")

    def update_motor_mapping_new(self, identified_motors):
        try:
            motor_mapping = self.roboclaw_config.get('motor_mapping', {})
            for motor_id, info in identified_motors.items():
                motor_key = f"motor{motor_id}"
                if motor_key in motor_mapping:
                    motor_mapping[motor_key].update({
                        'controller': info['controller'],
                        'channel': info['channel'],
                        'encoder_change': info['encoder_change'],
                        'detection_time': info['detection_time'],
                        'last_updated': datetime.now().isoformat(),
                        'updated_by': 'automated_motor_mapping'
                    })
            self.roboclaw_config['motor_mapping'] = motor_mapping
            self.config['hardware']['roboclaw'] = self.roboclaw_config
            config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'platform_config.json')
            with open(config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
            print("✅ Motor mapping updated in platform configuration")
        except Exception as e:
            print(f"❌ Error updating motor mapping: {e}")

    def run_connectivity_test(self) -> bool:
        """Run comprehensive connectivity test"""
        print("\n🔌 RoboClaw Connectivity Test")
        print("=" * 50)
        
        # Test connection
        if not self.connect():
            print("❌ Connection test failed")
            return False
        
        print("✅ Connection test passed")
        
        # Test motor mapping
        if not self.identify_motor_mapping():
            print("❌ Motor mapping test failed")
            return False
        
        print("✅ Motor mapping test passed")
        
        # Test E-Stop functionality
        for controller_name in ['rc1', 'rc2']:
            if controller_name in self.controller_info and self.controller_info[controller_name]['connected']:
                if not self.test_estop_functionality(controller_name):
                    print(f"❌ E-Stop test failed for {controller_name}")
                    return False
                print(f"✅ E-Stop test passed for {controller_name}")
        
        # Check for errors
        for controller_name in ['rc1', 'rc2']:
            if controller_name in self.controller_info and self.controller_info[controller_name]['connected']:
                error_state = self.read_error_state(controller_name)
                if error_state and error_state['error_info']['is_error']:
                    print(f"⚠️ Errors detected on {controller_name}:")
                    for error in error_state['error_info']['active_errors']:
                        print(f"   - {error}")
                else:
                    print(f"✅ No errors on {controller_name}")
        
        print("\n✅ All connectivity tests passed")
        return True

    def test_roboclaw_addresses(self):
        """Test different addresses for RoboClaw controllers to find correct configuration"""
        print("\n🔍 RoboClaw Address Testing")
        print("=" * 50)
        print("Testing different addresses for each controller...")
        
        # Test addresses from 0x80 to 0x89
        test_addresses = list(range(0x80, 0x8A))  # 0x80 to 0x89
        
        results = {}
        
        for controller_name in ['rc1', 'rc2']:
            if controller_name not in self.controller_info:
                continue
                
            port = self.controller_info[controller_name]['port']
            if not port:
                print(f"   ⚠️ {controller_name} port not configured")
                continue
                
            print(f"\n🔧 Testing {controller_name} on {port}")
            print("-" * 30)
            
            controller_results = {}
            
            for address in test_addresses:
                try:
                    # Create temporary RoboClaw instance
                    temp_roboclaw = Roboclaw(port, 0, timeout=0.5, retries=1)
                    if not temp_roboclaw.Open():
                        continue
                    
                    # Try to read version
                    version_result = temp_roboclaw.ReadVersion(address)
                    if version_result[0]:
                        print(f"   ✅ Address 0x{address:02X}: {version_result[1]}")
                        controller_results[address] = {
                            'version': version_result[1],
                            'status': 'connected'
                        }
                    else:
                        print(f"   ❌ Address 0x{address:02X}: No response")
                        controller_results[address] = {
                            'status': 'no_response'
                        }
                    
                    temp_roboclaw._port.close()
                    
                except Exception as e:
                    print(f"   ❌ Address 0x{address:02X}: Error - {e}")
                    controller_results[address] = {
                        'status': 'error',
                        'error': str(e)
                    }
            
            results[controller_name] = controller_results
            
            # Find best address for this controller
            best_address = None
            for address, result in controller_results.items():
                if result['status'] == 'connected':
                    best_address = address
                    break
            
            if best_address:
                print(f"   🎯 Recommended address for {controller_name}: 0x{best_address:02X}")
                # Update the controller info
                self.controller_info[controller_name]['address'] = best_address
            else:
                print(f"   ❌ No working address found for {controller_name}")
        
        return results

    def __del__(self):
        self.disconnect() 