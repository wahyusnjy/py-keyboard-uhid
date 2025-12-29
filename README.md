# py-keyboard-uhid

🎮 **Python WebSocket-based UHID Keyboard Control for Android Devices**

Project ini memungkinkan Anda untuk mengontrol satu atau beberapa perangkat Android secara bersamaan menggunakan keyboard virtual melalui protokol UHID (USB HID). Komunikasi dilakukan melalui WebSocket dan menggunakan scrcpy server sebagai bridge.

## ✨ Fitur

- ✅ **Multi-device Support** - Kontrol beberapa perangkat Android secara bersamaan
- ✅ **UHID Keyboard** - Emulasi keyboard HID USB yang native
- ✅ **WebSocket Control** - Komunikasi real-time melalui WebSocket
- ✅ **Broadcast Mode** - Kirim perintah ke semua perangkat sekaligus
- ✅ **Web-based Control Panel** - Kontrol melalui browser web
- ✅ **Device Search** - Filter/cari device berdasarkan nama atau serial
- ✅ **Interactive CLI** - Mode interaktif untuk testing
- ✅ **Auto-discovery** - Deteksi otomatis perangkat yang terhubung
- ✅ **Modifier Keys** - Support Ctrl, Shift, Alt, GUI/Super
- ✅ **Text Input** - Kirim teks lengkap, bukan hanya key tunggal

## 📋 Persyaratan

### Sistem Requirements
- Python 3.7+
- ADB (Android Debug Bridge) terinstall dan ada di PATH
- Perangkat Android dengan USB debugging enabled
- Scrcpy server JAR file

### Python Dependencies
```
websockets==15.0.1
```

## 🚀 Instalasi

### 1. Clone atau Download Project
```bash
cd ~/Documents/riset/py-keyboard-uhid
```

### 2. Setup Virtual Environment (Opsional tapi Direkomendasikan)
```bash
python3 -m venv .venv
source .venv/bin/activate  # Mac/Linux
# atau
.venv\Scripts\activate  # Windows
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Siapkan Scrcpy Server JAR
Pastikan file `scrcpy_server_new.jar` berada di folder `file_jar/`:
```
py-keyboard-uhid/
├── file_jar/
│   └── scrcpy_server_new.jar
```

### 5. Setup ADB
Pastikan ADB terinstall dan bisa diakses dari terminal:
```bash
adb version
```

### 6. Hubungkan Perangkat Android
- Enable **Developer Options** di Android
- Enable **USB Debugging**
- Hubungkan via USB dan accept debugging prompt
- Verifikasi koneksi:
```bash
adb devices
```

## 📖 Cara Penggunaan

### Mode 1: Web Control Server (Recommended)

Mode ini menyediakan web interface untuk kontrol multi-device yang mudah.

```bash
python ws-control-server.py
```

**Fitur:**
- Auto-discovery semua perangkat yang terhubung
- Auto-setup JAR deployment
- Auto-setup port forwarding
- Web-based control panel
- Broadcast ke semua perangkat

**Akses:**
- Buka `control_panel.html` di browser Anda
- WebSocket server berjalan di `ws://localhost:7777`

### Mode 2: Single Device Interactive

Mode CLI interaktif untuk kontrol satu perangkat:

```bash
python uhid_keyboard_client.py
```

**Commands:**
```
TAB, ENTER, ESCAPE, SPACE
UP, DOWN, LEFT, RIGHT
A-Z, 0-9
CTRL+C (ketik: c ctrl)
quit - Exit
```

### Mode 3: Single Device Demo

Menjalankan demo sequence otomatis:

```bash
python uhid_keyboard_client.py demo
```

### Mode 4: Multi-Device Interactive

Mode CLI untuk kontrol beberapa perangkat:

```bash
python uhid_keyboard_client.py multi
```

**Commands:**
```
add <name> <ws_url>     - Tambah device
remove <name>           - Hapus device
list                    - List semua devices
connect                 - Connect ke semua devices
all <key>              - Kirim key ke semua devices
send <device> <key>    - Kirim key ke device tertentu
text <device> <text>   - Kirim text ke device tertentu
broadcast <text>       - Kirim text ke semua devices
quit                   - Exit
```

**Contoh:**
```bash
Multi> add Phone1 ws://localhost:8886
Multi> add Phone2 ws://localhost:8887
Multi> connect
Multi> all TAB
Multi> send Phone1 ENTER
Multi> broadcast HELLO
```

### Mode 5: Multi-Device Demo

Demo otomatis untuk multi-device:

```bash
python uhid_keyboard_client.py multi-demo
```

## 🎯 Contoh Use Cases

### 1. Testing App di Multiple Devices
```python
# Broadcast input yang sama ke semua devices untuk testing
await multi.send_key_to_all('TAB')
await multi.send_text_to_all('test@example.com')
await multi.send_key_to_all('ENTER')
```

### 2. Automation Script
```python
from uhid_keyboard_client import UhidKeyboard
import asyncio

async def auto_login():
    kb = UhidKeyboard('ws://localhost:8886')
    await kb.connect()
    
    await kb.send_text('username')
    await kb.send_key('TAB')
    await kb.send_text('password')
    await kb.send_key('ENTER')
    
    await kb.close()

asyncio.run(auto_login())
```

### 3. Custom Control Panel
Buat HTML file Anda sendiri yang connect ke WebSocket server:
```javascript
const ws = new WebSocket('ws://localhost:7777');

// Send keyboard event
ws.send(JSON.stringify({
    type: 'keyboard',
    device: 'broadcast',  // atau specific serial
    key: 'ENTER',
    modifiers: {
        ctrl: false,
        shift: false,
        alt: false
    }
}));

// Send text
ws.send(JSON.stringify({
    type: 'text',
    device: 'serial_number',
    text: 'Hello World'
}));
```

## 🔧 Konfigurasi

### Mengubah Port Default

**WebSocket Control Server:**
```python
server = WebSocketControlServer(
    browser_ws_port=7777,      # Browser WebSocket
    start_device_port=8886      # Starting port untuk devices
)
```

**Single Device Client:**
```python
kb = UhidKeyboard('ws://localhost:8886')
```

### Custom JAR Path
```python
server = WebSocketControlServer(
    jar_path='/custom/path/to/scrcpy-server.jar'
)
```

## 📦 Struktur Project

```
py-keyboard-uhid/
├── uhid_keyboard_client.py   # UHID keyboard client & multi-device manager
├── ws-control-server.py       # WebSocket control server
├── requirements.txt           # Python dependencies
├── .gitignore                # Git ignore rules
├── file_jar/                 # JAR files directory
│   └── scrcpy_server_new.jar
└── README.md                 # Dokumentasi (file ini)
```

## 🔑 Supported Keys

### Special Keys
```
TAB, ENTER, ESCAPE, BACKSPACE, SPACE
DELETE, HOME, END, PAGE_UP, PAGE_DOWN
UP, DOWN, LEFT, RIGHT
```

### Letters
```
A-Z (case insensitive)
```

### Numbers
```
0-9
```

### Modifiers
```
CTRL (Ctrl)
SHIFT (Shift)
ALT (Alt)
GUI (Windows/Command key)
```

## 🐛 Troubleshooting

### Device Not Detected
```bash
# Check ADB connection
adb devices

# Restart ADB server
adb kill-server
adb start-server
```

### Port Already in Use
Server akan otomatis mencoba kill process yang menggunakan port. Jika masih error:
```bash
# Manual kill
lsof -ti:8886 | xargs kill -9
```

### Cannot Connect to WebSocket
Pastikan scrcpy server berjalan dengan benar:
```bash
# Check port listening
lsof -i :8886
```

### JAR File Not Found
```bash
# Verify JAR location
ls -lh file_jar/scrcpy_server_new.jar
```

### Server Crashes
Check device logs:
```bash
adb logcat | grep scrcpy
```

### WebSocket Keepalive Timeout
Jika browser menampilkan error "keepalive ping timeout":
- Server sudah dikonfigurasi dengan ping interval 20s dan timeout 60s
- Browser akan otomatis reconnect dalam 3 detik
- Pastikan tidak ada firewall yang memblokir WebSocket

### Connection "did not receive a valid HTTP response"
Jika device gagal connect dengan pesan ini:
```bash
# Kill semua process scrcpy di device
adb shell "pkill -9 scrcpy"
adb shell "pkill -9 app_process"

# Restart server
python3 ws-control-server.py
```

## 🎓 Technical Details

### UHID Protocol
Project ini menggunakan UHID (Userspace HID) untuk emulasi keyboard hardware-level. Message format:

```
Byte 0: Message Type (100 = UHID_KEYBOARD)
Byte 1: Modifiers (Ctrl, Shift, Alt, GUI)
Byte 2: Reserved (0)
Byte 3: HID Keycode
Byte 4-8: Additional keys (0)
```

### WebSocket Messages

**Device List (Server → Browser):**
```json
{
  "type": "devices",
  "devices": [
    {
      "serial": "device_serial",
      "name": "Device-Name",
      "port": 8886,
      "ws_url": "ws://localhost:8886",
      "connected": true
    }
  ]
}
```

**Keyboard Event (Browser → Server):**
```json
{
  "type": "keyboard",
  "device": "serial_or_broadcast",
  "key": "ENTER",
  "modifiers": {
    "ctrl": false,
    "shift": false,
    "alt": false
  }
}
```

**Text Input (Browser → Server):**
```json
{
  "type": "text",
  "device": "serial_or_broadcast",
  "text": "Hello World"
}
```

## 🤝 Contributing

Contributions are welcome! Feel free to:
- Report bugs
- Suggest features
- Submit pull requests

## 📄 License

Project ini dibuat untuk keperluan riset dan pembelajaran. Gunakan dengan bijak dan sesuai peraturan yang berlaku.

## 🙏 Credits

- Menggunakan [scrcpy](https://github.com/Genymobile/scrcpy) server untuk komunikasi dengan Android
- WebSocket implementation menggunakan [websockets](https://websockets.readthedocs.io/) library

## 📞 Support

Jika ada pertanyaan atau issue, silakan buat issue di repository atau hubungi maintainer.

---

**Happy Coding! 🚀**
