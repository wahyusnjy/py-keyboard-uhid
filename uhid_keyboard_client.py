#!/usr/bin/env python3
"""
UHID Keyboard Client for scrcpy WebSocket server
Sends keyboard events via UHID (Type 100)
"""

import asyncio
import websockets
import struct
import time

# Message types
TYPE_UHID_KEYBOARD = 100
TYPE_INJECT_KEYCODE = 102

# HID Keycodes
HID_KEYS = {
    'TAB': 0x2B,
    'ENTER': 0x28,
    'ESCAPE': 0x29,
    'BACKSPACE': 0x2A,
    'SPACE': 0x2C,
    'RIGHT': 0x4F,
    'LEFT': 0x50,
    'DOWN': 0x51,
    'UP': 0x52,
    'DELETE': 0x4C,
    'HOME': 0x4A,
    'END': 0x4D,
    'PAGE_UP': 0x4B,
    'PAGE_DOWN': 0x4E,
    # Letters
    'A': 0x04, 'B': 0x05, 'C': 0x06, 'D': 0x07,
    'E': 0x08, 'F': 0x09, 'G': 0x0A, 'H': 0x0B,
    'I': 0x0C, 'J': 0x0D, 'K': 0x0E, 'L': 0x0F,
    'M': 0x10, 'N': 0x11, 'O': 0x12, 'P': 0x13,
    'Q': 0x14, 'R': 0x15, 'S': 0x16, 'T': 0x17,
    'U': 0x18, 'V': 0x19, 'W': 0x1A, 'X': 0x1B,
    'Y': 0x1C, 'Z': 0x1D,
    # Numbers
    '1': 0x1E, '2': 0x1F, '3': 0x20, '4': 0x21,
    '5': 0x22, '6': 0x23, '7': 0x24, '8': 0x25,
    '9': 0x26, '0': 0x27,
}

# Modifiers
MOD_CTRL = 0x01
MOD_SHIFT = 0x02
MOD_ALT = 0x04
MOD_GUI = 0x08


class UhidKeyboard:
    def __init__(self, ws_url='ws://localhost:8886', device_name=None):
        self.ws_url = ws_url
        self.ws = None
        self.device_name = device_name or ws_url
    
    async def connect(self, timeout=10):
        """Connect to WebSocket server"""
        print(f"🔗 [{self.device_name}] Connecting to {self.ws_url}...")
        try:
            # Add timeout to prevent hanging
            self.ws = await asyncio.wait_for(
                websockets.connect(self.ws_url),
                timeout=timeout
            )
            print(f"✅ [{self.device_name}] Connected!")
            
            # Read device info (first message from server) with timeout
            msg = await asyncio.wait_for(
                self.ws.recv(),
                timeout=5
            )
            if isinstance(msg, str):
                print(f"📱 [{self.device_name}] Device info: {msg[:100]}...")
        except asyncio.TimeoutError:
            raise Exception(f"Connection timeout after {timeout}s - Server may not be running")
        except ConnectionRefusedError:
            raise Exception(f"Connection refused - Is the server running on {self.ws_url}?")
        except Exception as e:
            raise Exception(f"Connection failed: {str(e)}")
    
    async def send_uhid_key(self, modifiers: int, keycode: int):
        """Send UHID keyboard event (9 bytes)"""
        msg = bytearray(9)
        msg[0] = TYPE_UHID_KEYBOARD
        msg[1] = modifiers
        msg[2] = 0  # reserved
        msg[3] = keycode
        # msg[4-8] = 0 (additional keys)
        
        await self.ws.send(bytes(msg))
    
    async def send_key(self, key: str, ctrl=False, shift=False, alt=False, gui=False, silent=False):
        """Send key press + release"""
        keycode = HID_KEYS.get(key.upper())
        if keycode is None:
            if not silent:
                print(f"❌ [{self.device_name}] Unknown key: {key}")
            return
        
        # Build modifiers
        modifiers = 0
        if ctrl: modifiers |= MOD_CTRL
        if shift: modifiers |= MOD_SHIFT
        if alt: modifiers |= MOD_ALT
        if gui: modifiers |= MOD_GUI
        
        # Press
        await self.send_uhid_key(modifiers, keycode)
        if not silent:
            print(f"⌨️  [{self.device_name}] Sent: {key.upper()}{' (Ctrl)' if ctrl else ''}{' (Shift)' if shift else ''}")
        
        # Release after 50ms
        await asyncio.sleep(0.05)
        await self.send_uhid_key(0, 0)
    
    async def send_text(self, text: str, silent=False):
        """Send text string (letters and spaces)"""
        for char in text:
            if char == ' ':
                await self.send_key('SPACE', silent=silent)
            else:
                await self.send_key(char.upper(), silent=silent)
            await asyncio.sleep(0.1)
    
    async def close(self):
        """Close WebSocket connection"""
        if self.ws:
            await self.ws.close()
            print(f"🔌 [{self.device_name}] Disconnected")


class MultiDeviceKeyboard:
    """Manages multiple UHID keyboard connections"""
    
    def __init__(self):
        self.devices = {}  # device_name -> UhidKeyboard
    
    def add_device(self, device_name: str, ws_url: str):
        """Add a device to manage"""
        if device_name in self.devices:
            print(f"⚠️  Device '{device_name}' already exists!")
            return
        
        self.devices[device_name] = UhidKeyboard(ws_url, device_name)
        print(f"➕ Added device: {device_name} ({ws_url})")
    
    def remove_device(self, device_name: str):
        """Remove a device"""
        if device_name in self.devices:
            del self.devices[device_name]
            print(f"➖ Removed device: {device_name}")
        else:
            print(f"❌ Device '{device_name}' not found!")
    
    async def connect_all(self):
        """Connect to all devices"""
        print(f"\n🔗 Connecting to {len(self.devices)} device(s)...\n")
        
        tasks = []
        for name, kb in self.devices.items():
            tasks.append(kb.connect())
        
        # Connect all devices concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check for errors
        failed = []
        for i, (name, result) in enumerate(zip(self.devices.keys(), results)):
            if isinstance(result, Exception):
                print(f"❌ Failed to connect to {name}: {result}")
                failed.append(name)
        
        if failed:
            print(f"\n⚠️  {len(failed)} device(s) failed to connect")
        else:
            print(f"\n✅ All {len(self.devices)} device(s) connected!\n")
        
        return len(failed) == 0
    
    async def send_key_to(self, device_name: str, key: str, **modifiers):
        """Send key to specific device"""
        if device_name not in self.devices:
            print(f"❌ Device '{device_name}' not found!")
            return
        
        await self.devices[device_name].send_key(key, **modifiers)
    
    async def send_key_to_all(self, key: str, **modifiers):
        """Broadcast key to all devices"""
        print(f"📡 Broadcasting '{key}' to {len(self.devices)} device(s)...")
        
        tasks = []
        for kb in self.devices.values():
            tasks.append(kb.send_key(key, silent=True, **modifiers))
        
        await asyncio.gather(*tasks, return_exceptions=True)
        print(f"✅ Broadcast complete!")
    
    async def send_text_to(self, device_name: str, text: str):
        """Send text to specific device"""
        if device_name not in self.devices:
            print(f"❌ Device '{device_name}' not found!")
            return
        
        await self.devices[device_name].send_text(text)
    
    async def send_text_to_all(self, text: str):
        """Broadcast text to all devices"""
        print(f"📡 Broadcasting text '{text}' to {len(self.devices)} device(s)...")
        
        tasks = []
        for kb in self.devices.values():
            tasks.append(kb.send_text(text, silent=True))
        
        await asyncio.gather(*tasks, return_exceptions=True)
        print(f"✅ Broadcast complete!")
    
    def list_devices(self):
        """List all managed devices"""
        if not self.devices:
            print("📋 No devices added yet")
            return
        
        print(f"\n📋 Managed Devices ({len(self.devices)}):")
        for name, kb in self.devices.items():
            status = "🟢 Connected" if kb.ws and not kb.ws.closed else "🔴 Disconnected"
            print(f"  • {name}: {kb.ws_url} - {status}")
        print()
    
    async def close_all(self):
        """Close all device connections"""
        print(f"\n🔌 Closing {len(self.devices)} connection(s)...")
        
        tasks = []
        for kb in self.devices.values():
            tasks.append(kb.close())
        
        await asyncio.gather(*tasks, return_exceptions=True)
        print("✅ All connections closed")


async def demo():
    """Demo: Send various keyboard commands"""
    kb = UhidKeyboard()
    
    try:
        await kb.connect()
        
        print("\n🎮 Demo: Sending keyboard commands...\n")
        
        # Test Tab key
        print("1. Sending Tab...")
        await kb.send_key('TAB')
        await asyncio.sleep(1)
        
        # Test Enter
        print("2. Sending Enter...")
        await kb.send_key('ENTER')
        await asyncio.sleep(1)
        
        # Test arrows
        print("3. Sending arrow keys...")
        await kb.send_key('RIGHT')
        await asyncio.sleep(0.5)
        await kb.send_key('DOWN')
        await asyncio.sleep(0.5)
        await kb.send_key('LEFT')
        await asyncio.sleep(0.5)
        await kb.send_key('UP')
        await asyncio.sleep(1)
        
        # Test Ctrl combinations
        print("4. Sending Ctrl+C...")
        await kb.send_key('C', ctrl=True)
        await asyncio.sleep(1)
        
        print("5. Sending Ctrl+V...")
        await kb.send_key('V', ctrl=True)
        await asyncio.sleep(1)
        
        # Test text
        print("6. Sending text 'HELLO'...")
        await kb.send_text('HELLO')
        
        print("\n✅ Demo complete!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await kb.close()


async def interactive():
    """Interactive mode: Send keys from keyboard input"""
    kb = UhidKeyboard()
    
    try:
        await kb.connect()
        
        print("\n🎮 Interactive Mode")
        print("Commands:")
        print("  TAB, ENTER, ESCAPE, SPACE")
        print("  UP, DOWN, LEFT, RIGHT")
        print("  A-Z, 0-9")
        print("  CTRL+C (type: c ctrl)")
        print("  quit - Exit")
        print()
        
        while True:
            cmd = input("Key> ").strip().upper()
            
            if cmd == 'QUIT':
                break
            
            # Parse modifiers
            parts = cmd.split()
            key = parts[0]
            ctrl = 'CTRL' in parts
            shift = 'SHIFT' in parts
            alt = 'ALT' in parts
            
            await kb.send_key(key, ctrl=ctrl, shift=shift, alt=alt)
        
    except KeyboardInterrupt:
        print("\n👋 Bye!")
    finally:
        await kb.close()


async def multi_device_demo():
    """Demo: Managing multiple devices"""
    multi = MultiDeviceKeyboard()
    
    try:
        # Add devices
        print("🎯 Multi-Device Demo\n")
        multi.add_device("Phone1", "ws://localhost:8886")
        multi.add_device("Phone2", "ws://localhost:8887")
        multi.add_device("Tablet", "ws://localhost:8888")
        
        # List devices
        multi.list_devices()
        
        # Connect to all devices
        await multi.connect_all()
        
        # Broadcast to all devices
        print("\n1️⃣ Broadcasting TAB to all devices...")
        await multi.send_key_to_all('TAB')
        await asyncio.sleep(1)
        
        # Send to specific device
        print("\n2️⃣ Sending ENTER to Phone1 only...")
        await multi.send_key_to('Phone1', 'ENTER')
        await asyncio.sleep(1)
        
        # Broadcast text
        print("\n3️⃣ Broadcasting text 'HELLO' to all devices...")
        await multi.send_text_to_all('HELLO')
        await asyncio.sleep(1)
        
        # Send text to specific device
        print("\n4️⃣ Sending 'WORLD' to Tablet only...")
        await multi.send_text_to('Tablet', 'WORLD')
        await asyncio.sleep(1)
        
        # Broadcast Ctrl+C
        print("\n5️⃣ Broadcasting Ctrl+C to all devices...")
        await multi.send_key_to_all('C', ctrl=True)
        
        print("\n✅ Multi-device demo complete!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await multi.close_all()


async def multi_device_interactive():
    """Interactive mode for multiple devices"""
    multi = MultiDeviceKeyboard()
    
    try:
        print("\n🎮 Multi-Device Interactive Mode")
        print("\nFirst, add your devices:")
        print("Example: add Phone1 ws://localhost:8886")
        print("\nCommands:")
        print("  add <name> <ws_url>     - Add a device")
        print("  remove <name>           - Remove a device")
        print("  list                    - List all devices")
        print("  connect                 - Connect to all devices")
        print("  all <key>               - Send key to all devices")
        print("  send <device> <key>     - Send key to specific device")
        print("  text <device> <text>    - Send text to specific device")
        print("  broadcast <text>        - Send text to all devices")
        print("  quit                    - Exit")
        print()
        
        connected = False
        
        while True:
            cmd = input("Multi> ").strip()
            
            if not cmd:
                continue
            
            parts = cmd.split(maxsplit=2)
            action = parts[0].lower()
            
            if action == 'quit':
                break
            
            elif action == 'add' and len(parts) >= 3:
                multi.add_device(parts[1], parts[2])
            
            elif action == 'remove' and len(parts) >= 2:
                multi.remove_device(parts[1])
            
            elif action == 'list':
                multi.list_devices()
            
            elif action == 'connect':
                connected = await multi.connect_all()
            
            elif action == 'all' and len(parts) >= 2:
                if not connected:
                    print("❌ Please connect first!")
                    continue
                key = parts[1].upper()
                await multi.send_key_to_all(key)
            
            elif action == 'send' and len(parts) >= 3:
                if not connected:
                    print("❌ Please connect first!")
                    continue
                device = parts[1]
                key = parts[2].upper()
                await multi.send_key_to(device, key)
            
            elif action == 'text' and len(parts) >= 3:
                if not connected:
                    print("❌ Please connect first!")
                    continue
                device = parts[1]
                text = parts[2]
                await multi.send_text_to(device, text)
            
            elif action == 'broadcast' and len(parts) >= 2:
                if not connected:
                    print("❌ Please connect first!")
                    continue
                text = parts[1]
                await multi.send_text_to_all(text)
            
            else:
                print("❌ Unknown command or missing parameters")
        
    except KeyboardInterrupt:
        print("\n👋 Bye!")
    finally:
        await multi.close_all()


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        mode = sys.argv[1]
        
        if mode == 'demo':
            # Single device demo
            asyncio.run(demo())
        elif mode == 'multi-demo':
            # Multi device demo
            asyncio.run(multi_device_demo())
        elif mode == 'multi':
            # Multi device interactive
            asyncio.run(multi_device_interactive())
        else:
            print("Usage:")
            print("  python uhid_keyboard_client.py           - Single device interactive")
            print("  python uhid_keyboard_client.py demo      - Single device demo")
            print("  python uhid_keyboard_client.py multi     - Multi device interactive")
            print("  python uhid_keyboard_client.py multi-demo - Multi device demo")
    else:
        # Interactive mode (single device)
        asyncio.run(interactive())
