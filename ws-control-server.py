#!/usr/bin/env python3
"""
WebSocket Control Server
Provides web-based control panel for multiple Android devices
"""

import asyncio
import json
import subprocess
import time
import socket
from pathlib import Path
from typing import Dict, List, Optional
import websockets
from websockets.asyncio.server import serve
from uhid_keyboard_client import UhidKeyboard

class DeviceInfo:
    """Information about a managed device"""
    def __init__(self, serial: str, name: str, port: int, ws_url: str):
        self.serial = serial
        self.name = name
        self.port = port
        self.ws_url = ws_url
        self.uhid_client: Optional[UhidKeyboard] = None
        self.connected = False
        self.process = None


class WebSocketControlServer:
    """WebSocket server for browser-based multi-device control"""
    
    def __init__(self, browser_ws_port=7777, start_device_port=8886, jar_path=None):
        self.browser_ws_port = browser_ws_port
        self.start_device_port = start_device_port
        self.jar_path = jar_path or str(Path(__file__).parent / "file_jar" / "scrcpy_server_new.jar")
        
        self.devices: Dict[str, DeviceInfo] = {}
        self.next_port = start_device_port
        self.browser_clients = set()
        
    def run_adb_command(self, command: str, device_serial: Optional[str] = None) -> tuple:
        """Execute adb command"""
        if device_serial:
            cmd = f"adb -s {device_serial} {command}"
        else:
            cmd = f"adb {command}"
        
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
        except Exception as e:
            return False, "", str(e)
    
    def get_connected_devices(self) -> List[str]:
        """Get list of connected device serials from adb"""
        success, output, _ = self.run_adb_command("devices")
        if not success:
            return []
        
        devices = []
        for line in output.split('\n')[1:]:
            if line.strip() and '\tdevice' in line:
                serial = line.split('\t')[0]
                devices.append(serial)
        
        return devices
    
    def get_device_name(self, serial: str) -> str:
        """Get device model name"""
        success, output, _ = self.run_adb_command("shell getprop ro.product.model", serial)
        model = output.replace(' ', '-') if success and output else "Device"
        serial_suffix = serial[-4:] if len(serial) >= 4 else serial
        return f"{model}-{serial_suffix}"
    
    def kill_old_servers(self, serial: str):
        """Kill old scrcpy servers on device"""
        print(f"🧹 [{serial}] Killing old servers...")
        
        # Multiple kill methods
        self.run_adb_command("shell \"pkill -9 -f scrcpy || true\"", serial)
        self.run_adb_command("shell \"pkill -9 -f app_process || true\"", serial)
        self.run_adb_command("shell \"killall -9 scrcpy-server 2>/dev/null || true\"", serial)
        
        time.sleep(1)
    
    def push_jar_to_device(self, serial: str) -> bool:
        """Push scrcpy-server.jar to device"""
        remote_jar = "/data/local/tmp/scrcpy-server.jar"
        
        print(f"📦 [{serial}] Deploying JAR file...")
        
        # Remove old JAR if exists
        print(f"  → Removing old JAR...")
        self.run_adb_command(f"shell \"rm -f {remote_jar}\"", serial)
        
        # Check local JAR exists
        if not Path(self.jar_path).exists():
            print(f"❌ [{serial}] Local JAR not found: {self.jar_path}")
            return False
        
        # Push new JAR
        print(f"  → Pushing JAR from {Path(self.jar_path).name}...")
        success, output, error = self.run_adb_command(
            f"push {self.jar_path} {remote_jar}",
            serial
        )
        
        if not success:
            print(f"❌ [{serial}] Failed to push JAR: {error}")
            return False
        
        # Verify JAR on device
        success, size_output, _ = self.run_adb_command(
            f"shell \"ls -lh {remote_jar} | awk '{{print \\$5}}'\"",
            serial
        )
        
        if success and size_output:
            print(f"  ✅ JAR deployed: {size_output.strip()}")
        
        # Get MD5 for verification
        success, md5_output, _ = self.run_adb_command(
            f"shell \"md5sum {remote_jar} | awk '{{print \\$1}}'\"",
            serial
        )
        
        if success and md5_output:
            md5_hash = md5_output.strip()
            print(f"  🔐 MD5: {md5_hash[:16]}...")
        
        return True
    
    
    def check_port_listening(self, port: int, timeout: int = 10) -> bool:
        """Check if port is listening"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                with socket.create_connection(("localhost", port), timeout=1):
                    return True
            except (socket.error, ConnectionRefusedError):
                time.sleep(0.5)
        return False
    
    def check_port_conflict(self, port: int) -> bool:
        """Check if port is already in use"""
        try:
            with socket.create_connection(("localhost", port), timeout=1):
                return True  # Port is in use
        except (socket.error, ConnectionRefusedError):
            return False  # Port is free
    
    def resolve_port_conflict(self, port: int):
        """Kill process using the port"""
        print(f"⚠️  Port {port} is in use, attempting to free it...")
        
        # Try to find and kill process using port
        try:
            result = subprocess.run(
                f"lsof -ti:{port}",
                shell=True,
                capture_output=True,
                text=True
            )
            if result.stdout:
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    subprocess.run(f"kill -9 {pid}", shell=True)
                    print(f"✅ Killed process {pid} using port {port}")
                time.sleep(1)
        except:
            pass
    
    def setup_port_forward(self, serial: str, port: int) -> bool:
        """Setup adb port forwarding"""
        print(f"🔌 [{serial}] Setting up port forwarding: {port}")
        success, _, error = self.run_adb_command(f"forward tcp:{port} tcp:{port}", serial)
        
        if success:
            print(f"✅ [{serial}] Port {port} forwarded")
            return True
        else:
            print(f"❌ [{serial}] Port forward failed: {error}")
            return False
    
    def start_server(self, serial: str, port: int) -> Optional[subprocess.Popen]:
        """Start scrcpy server on device"""
        print(f"🚀 [{serial}] Starting server on port {port}...")
        
        cmd = (
            f'adb -s {serial} shell "CLASSPATH=/data/local/tmp/scrcpy-server.jar '
            f'app_process / com.genymobile.scrcpy.Server '
            f'3.3.3 web info {port} false - false true"'
        )
        
        process = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        
        # Check if process started
        time.sleep(1)
        if process.poll() is not None:
            output, _ = process.communicate()
            print(f"❌ [{serial}] Server failed to start")
            if output:
                print(f"📜 Server output:\n{output[:500]}\n")
            return None
        
        # Wait for port to be ready
        print(f"⏳ [{serial}] Waiting for server to listen on port {port}...")
        if self.check_port_listening(port, timeout=10):
            print(f"✅ [{serial}] Server is ready on port {port}")
            return process
        else:
            print(f"❌ [{serial}] Server didn't start listening on port {port}")
            process.terminate()
            return None
    
    async def setup_device(self, serial: str) -> bool:
        """Setup a single device"""
        print(f"\n{'='*60}")
        print(f"🔧 Setting up device: {serial}")
        print(f"{'='*60}\n")
        
        # Get device name
        device_name = self.get_device_name(serial)
        
        # Kill old servers
        self.kill_old_servers(serial)
        
        # Push JAR to device
        if not self.push_jar_to_device(serial):
            print(f"❌ [{serial}] Failed to deploy JAR, skipping device")
            return False
        
        # Find available port
        port = self.next_port
        while self.check_port_conflict(port):
            print(f"⚠️  Port {port} already in use")
            self.resolve_port_conflict(port)
            if self.check_port_conflict(port):
                port += 1
                continue
            break
        
        self.next_port = port + 1
        
        # Setup port forward
        if not self.setup_port_forward(serial, port):
            return False
        
        # Start server
        process = self.start_server(serial, port)
        if not process:
            return False
        
        # Create device info
        ws_url = f"ws://localhost:{port}"
        device_info = DeviceInfo(serial, device_name, port, ws_url)
        device_info.process = process
        device_info.uhid_client = UhidKeyboard(ws_url, device_name)
        
        # Connect UHID client
        try:
            await device_info.uhid_client.connect(timeout=10)
            device_info.connected = True
            print(f"✅ [{serial}] UHID client connected")
        except Exception as e:
            print(f"❌ [{serial}] Failed to connect UHID client: {e}")
            device_info.connected = False
        
        self.devices[serial] = device_info
        
        print(f"\n✅ Device {serial} ({device_name}) ready on port {port}\n")
        
        # Notify browser clients
        await self.broadcast_device_list()
        
        return True
    
    async def discover_all_devices(self):
        """Discover and setup all connected devices"""
        print("\n🔍 Discovering connected devices...\n")
        
        serials = self.get_connected_devices()
        
        if not serials:
            print("❌ No devices connected!")
            return
        
        print(f"📱 Found {len(serials)} device(s):\n")
        for i, serial in enumerate(serials, 1):
            name = self.get_device_name(serial)
            print(f"  {i}. {serial} ({name})")
        print()
        
        # Setup all devices
        for serial in serials:
            await self.setup_device(serial)
        
        print(f"\n{'='*60}")
        print(f"✅ Setup complete: {len(self.devices)}/{len(serials)} device(s) ready")
        print(f"{'='*60}\n")
    
    def get_device_list_message(self) -> dict:
        """Get device list message for browser"""
        devices_data = []
        for serial, dev in self.devices.items():
            devices_data.append({
                "serial": serial,
                "name": dev.name,
                "port": dev.port,
                "ws_url": dev.ws_url,
                "connected": dev.connected
            })
        
        return {
            "type": "devices",
            "devices": devices_data
        }
    
    async def broadcast_device_list(self):
        """Send device list to all connected browser clients"""
        if not self.browser_clients:
            return
        
        message = json.dumps(self.get_device_list_message())
        websockets.broadcast(self.browser_clients, message)
    
    async def handle_browser_message(self, websocket, message_data: dict):
        """Handle message from browser"""
        msg_type = message_data.get("type")
        
        if msg_type == "keyboard":
            # Keyboard input
            device_serial = message_data.get("device")
            key = message_data.get("key")
            modifiers = message_data.get("modifiers", {})
            
            if device_serial == "broadcast":
                # Broadcast to all devices
                for dev in self.devices.values():
                    if dev.connected and dev.uhid_client:
                        try:
                            await dev.uhid_client.send_key(
                                key,
                                ctrl=modifiers.get("ctrl", False),
                                shift=modifiers.get("shift", False),
                                alt=modifiers.get("alt", False),
                                silent=True
                            )
                        except Exception as e:
                            print(f"❌ Error sending to {dev.name}: {e}")
                
                await websocket.send(json.dumps({
                    "type": "ack",
                    "status": "success",
                    "message": f"Broadcast key '{key}' to all devices"
                }))
            else:
                # Send to specific device
                dev = self.devices.get(device_serial)
                if dev and dev.connected and dev.uhid_client:
                    try:
                        await dev.uhid_client.send_key(
                            key,
                            ctrl=modifiers.get("ctrl", False),
                            shift=modifiers.get("shift", False),
                            alt=modifiers.get("alt", False),
                            silent=True
                        )
                        await websocket.send(json.dumps({
                            "type": "ack",
                            "status": "success",
                            "message": f"Sent key '{key}' to {dev.name}"
                        }))
                    except Exception as e:
                        await websocket.send(json.dumps({
                            "type": "ack",
                            "status": "error",
                            "message": str(e)
                        }))
        
        elif msg_type == "text":
            # Text input
            device_serial = message_data.get("device")
            text = message_data.get("text")
            
            if device_serial == "broadcast":
                for dev in self.devices.values():
                    if dev.connected and dev.uhid_client:
                        try:
                            await dev.uhid_client.send_text(text, silent=True)
                        except:
                            pass
            else:
                dev = self.devices.get(device_serial)
                if dev and dev.connected and dev.uhid_client:
                    await dev.uhid_client.send_text(text, silent=True)
        
        elif msg_type == "get_devices":
            # Request device list
            await websocket.send(json.dumps(self.get_device_list_message()))
    
    async def browser_handler(self, websocket):
        """Handle browser WebSocket connections"""
        self.browser_clients.add(websocket)
        print(f"🌐 Browser connected from {websocket.remote_address}")
        
        # Send current device list
        await websocket.send(json.dumps(self.get_device_list_message()))
        
        try:
            async for message in websocket:
                try:
                    message_data = json.loads(message)
                    await self.handle_browser_message(websocket, message_data)
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "Invalid JSON"
                    }))
                except Exception as e:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": str(e)
                    }))
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.browser_clients.remove(websocket)
            print(f"🌐 Browser disconnected from {websocket.remote_address}")
    
    async def start(self):
        """Start the WebSocket server"""
        # Discover and setup devices
        await self.discover_all_devices()
        
        # Start WebSocket server for browser with proper ping/pong configuration
        print(f"\n🚀 Starting WebSocket server on port {self.browser_ws_port}...")
        async with serve(
            self.browser_handler, 
            "localhost", 
            self.browser_ws_port,
            ping_interval=20,  # Send ping every 20 seconds
            ping_timeout=60,   # Wait 60 seconds for pong response
            close_timeout=10   # Wait 10 seconds for close frame
        ):
            print(f"✅ WebSocket server running on ws://localhost:{self.browser_ws_port}")
            print(f"📡 Keepalive: ping every 20s, timeout 60s")
            print(f"\n📖 Open control_panel.html in your browser to control devices\n")
            await asyncio.Future()  # Run forever
    
    def cleanup(self):
        """Cleanup all devices"""
        print("\n🧹 Cleaning up devices...\n")
        for serial, dev in self.devices.items():
            if dev.process and dev.process.poll() is None:
                dev.process.terminate()
            self.run_adb_command(f"forward --remove tcp:{dev.port}")


async def main():
    server = WebSocketControlServer()
    
    try:
        await server.start()
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down...")
    finally:
        server.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
