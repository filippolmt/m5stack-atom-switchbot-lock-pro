# M5Stack ATOM - SwitchBot Lock Pro Controller

Control your **SwitchBot Lock Pro** by simply pressing the button on your **M5Stack ATOM**! 🚪🔐

This project provides a complete solution to integrate your M5Stack ATOM (ESP32) with the SwitchBot API and control a SwitchBot Lock Pro over Wi-Fi.

## 🌟 Features

- ✅ **Automatic Wi-Fi connection** with simple configuration
- ✅ **GPIO button handling** with interrupt and hardware debounce
- ✅ **SwitchBot API v1.1** with signed token + secret headers
- ✅ **Memory management** optimized for ESP32
- ✅ **Robust code** with thorough error handling
- ✅ **Complete setup guide** for VS Code + MicroPython

## 📋 Requirements

### Hardware

- **M5Stack ATOM** (ESP32-PICO-D4)
- USB Type-C cable
- **SwitchBot Lock Pro** (set up and working)

### Software

- **MicroPython v1.24.x or later** (tested with v1.24.1) for ESP32
- **VS Code** (optional) for editing
- `mpremote` for file upload and execution
- Python 3.x on your computer
- SwitchBot account with API token and secret (for API v1.1 signing)

## 🚀 Quick Start

### 1. Environment Setup (First Time)

Follow the full guide in **[SETUP.md](SETUP.md)** to:

- Install VS Code and the MicroPython extension
- Flash MicroPython onto your M5Stack ATOM
- Configure the development environment
- Obtain SwitchBot credentials (Token and Device ID)

### 2. Configuration

```bash
# Clone the repository
git clone https://github.com/filippolmt/m5stack-atom-switchbot-lock-pro.git
cd m5stack-atom-switchbot-lock-pro

# Copy and configure the settings file
cp config_template.py config.py
```

Edit `config.py` with your details:

```python
# Wi-Fi configuration
WIFI_SSID = "YourSSID"
WIFI_PASSWORD = "YourPassword"

# SwitchBot API configuration
SWITCHBOT_TOKEN = "YourBearerToken"
SWITCHBOT_SECRET = "YourTokenSecret"
SWITCHBOT_DEVICE_ID = "YourDeviceID"

# M5Stack ATOM button GPIO (preconfigured)
BUTTON_GPIO = 39
```

### 3. Upload to the Device (mpremote)

1. Connect the M5Stack ATOM via USB and identify the serial port (e.g., `/dev/cu.usbserial-XXXX` on macOS, `COM3` on Windows, `/dev/ttyUSB0` on Linux).
2. Upload the files with `mpremote` (replace the port with yours):
   ```bash
   mpremote connect /dev/cu.usbserial-XXXX cp main.py :main.py
   mpremote connect /dev/cu.usbserial-XXXX cp config.py :config.py
   ```

### 4. Run It

Execute the script via `mpremote`:

```bash
mpremote connect /dev/cu.usbserial-XXXX run main.py
```

Then press the button on the M5Stack ATOM to control the lock.

## 📁 Project Structure

```
.
├── main.py              # Main MicroPython script
├── config_template.py   # Configuration template
├── config.py            # Configuration (create locally, not in git)
├── SETUP.md             # Full setup guide
├── README.md            # This file
├── LICENSE              # License
└── .gitignore           # Excludes config.py and other sensitive files
```

## 🔧 How It Works

1. **On boot**: the device automatically connects to the configured Wi-Fi
2. **Initialization**: sets up the SwitchBot controller and the GPIO button
3. **Main loop**: listens for button presses
4. **When you press the button**:
   - Hardware debounce avoids accidental multiple presses
   - Sends a POST request to the SwitchBot API
   - Issues a fixed **unlock** command (always unlocks the lock)
   - Shows the result in the serial terminal

## 📡 SwitchBot API

The project uses the SwitchBot API v1.1:

- **Endpoint**: `https://api.switch-bot.com/v1.1/devices/{deviceId}/commands`
- **Authentication**: token + secret with signed headers:
  - `Authorization`: your token
  - `nonce`: random hex string
  - `t`: Unix timestamp in milliseconds (1970 epoch)
  - `sign`: Base64(HMAC-SHA256(token + t + nonce, secret))
- **Command**: `unlock` (always unlocks the lock)

MicroPython on ESP32 uses the 2000-01-01 epoch internally. The code converts it to the Unix epoch (1970) before signing and retries an NTP sync if the RTC year looks wrong before sending a command. If the timestamp is off you will get a `401 Unauthorized` from the API.

Full documentation: https://github.com/OpenWonderLabs/SwitchBotAPI

## 🔍 Monitoring and Debug

Connect to the serial terminal (115200 baud) to see:

```
==================================================
M5Stack ATOM - SwitchBot Lock Pro Controller
==================================================
Connecting to Wi-Fi: MyWiFi...
✓ Connected to Wi-Fi!
Network configuration:
  IP:      192.168.1.100
  ...

✓ SwitchBot controller initialized
✓ Button configured on GPIO39

==================================================
System ready! Press the button to unlock the door.
==================================================

>>> Button pressed! <<<
Sending command to SwitchBot Lock Pro...
✓ Command sent successfully! Status: 200
```

## 🛠️ Troubleshooting

See the **Troubleshooting** section in [SETUP.md](SETUP.md) for:

- Connection issues with the device
- Errors while flashing the firmware
- Wi-Fi connection problems
- SwitchBot API errors
- Button issues
- Memory handling

## 🔒 Security

⚠️ **IMPORTANT:**

- `config.py` contains sensitive credentials and is excluded from Git
- Do not share your Bearer Token
- Use a secure Wi-Fi network (WPA2/WPA3)
- Consider using a dedicated VLAN for IoT devices

## 🙏 Acknowledgements

- [MicroPython](https://micropython.org/) - Python for microcontrollers
- [M5Stack](https://m5stack.com/) - Quality ESP32 hardware
- [SwitchBot](https://www.switch-bot.com/) - Smart home devices
