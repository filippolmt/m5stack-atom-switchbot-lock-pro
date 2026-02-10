# M5Stack ATOM - SwitchBot Lock Pro Controller

Control your **SwitchBot Lock Pro** by simply pressing the button on your **M5Stack ATOM**! 🚪🔐

This project provides a complete solution to integrate your M5Stack ATOM (ESP32) with the SwitchBot API and control a SwitchBot Lock Pro over Wi-Fi.

## 🌟 Features

- ✅ **Deep sleep mode** - Ultra-low power consumption (~10uA idle vs ~80mA active)
- ✅ **Wake on button press** - ESP32 wakes from deep sleep when button is pressed
- ✅ **On-demand Wi-Fi** - Connects only when needed, disconnects immediately after API response
- ✅ **Fast reconnect** - Caches Wi-Fi BSSID (strongest signal) for ~1-2s faster reconnection
- ✅ **Configurable TX power** - Reduce Wi-Fi transmit power to save battery when router is nearby
- ✅ **Multicolor LED feedback** - Different colors indicate status and errors
- ✅ **SwitchBot API v1.1** with signed token + secret headers
- ✅ **Safety watchdog** - 60s WDT resets device if any operation hangs
- ✅ **Auto retry** - Retries API call once on failure
- ✅ **Automated test suite** - 52 tests via Docker (Python 3.13 + pytest)
- ✅ **CI/CD** - GitHub Actions runs tests on push/PR
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
SWITCHBOT_TOKEN = "YourToken"
SWITCHBOT_SECRET = "YourTokenSecret"
SWITCHBOT_DEVICE_ID = "YourDeviceID"

# M5Stack ATOM button GPIO (preconfigured)
BUTTON_GPIO = 39

# Optional: reduce Wi-Fi TX power to save battery (dBm)
# WIFI_TX_POWER = 8  # Uncomment if router is nearby
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
├── tests/               # Automated test suite (runs on CPython via Docker)
│   ├── conftest.py      # Hardware stubs + fake config injection
│   ├── test_epoch.py    # Epoch conversion & timestamp tests
│   ├── test_hmac.py     # HMAC-SHA256 (manual + stdlib paths)
│   ├── test_auth_headers.py  # API authentication headers
│   ├── test_send_command.py  # HTTP retry logic & error handling
│   ├── test_rtc_memory.py    # RTC memory serialization
│   ├── test_led.py      # LED brightness scaling
│   └── test_wifi.py     # Wi-Fi connection logic
├── Dockerfile.test      # Test runner image (Python 3.13 + pytest)
├── Makefile             # make test / make test-clean
├── pyproject.toml       # pytest configuration
├── .github/workflows/test.yml  # CI: tests on push/PR to main
├── SETUP.md             # Full setup guide
├── README.md            # This file
├── LICENSE              # License
└── .gitignore           # Excludes config.py and other sensitive files
```

## 🔧 How It Works

1. **On boot/reset**: Shows startup message, then enters deep sleep (~10uA)
2. **When you press the button**:
   - ESP32 wakes from deep sleep
   - **Short press (<1s)** = UNLOCK (green LED while holding)
   - **Long press (≥1s)** = LOCK (purple LED while holding)
   - Connects to Wi-Fi (fast reconnect if cached)
   - Syncs time via NTP (skipped if RTC valid)
   - Sends lock/unlock command to SwitchBot API
   - Disconnects Wi-Fi immediately after response
   - LED feedback based on result (Wi-Fi off, CPU at 80MHz)
   - Returns to deep sleep
3. **Power consumption**:
   - Deep sleep: ~10uA (can run months on battery)
   - Active (Wi-Fi + API call): ~80-150mA for 2-4 seconds
   - LED feedback: ~25mA for ~0.5s (Wi-Fi off, CPU at 80MHz)
   - With `WIFI_TX_POWER = 8`: ~50-100mA during Wi-Fi (+58% battery life)

## 🎮 Button Controls

| Press Duration | Action | LED While Holding |
|----------------|--------|-------------------|
| **< 1 second** | UNLOCK | 🟢 Green |
| **≥ 1 second** | LOCK | 🟣 Purple |

## 💡 LED Color Guide

| Color | Meaning |
|-------|---------|
| 🟢 **Green (holding)** | Short press - will UNLOCK |
| 🟣 **Purple (holding)** | Long press - will LOCK |
| 🔵 **Blue** | Connecting to Wi-Fi (normal scan) |
| 🩵 **Cyan** | Fast reconnect in progress |
| 🟢 **Green (2 blinks)** | Door unlocked successfully |
| 🟣 **Purple (2 blinks)** | Door locked successfully |
| 🟡 **Yellow (2 blinks)** | NTP sync failed (continuing anyway) |
| 🟡 **Yellow (4 blinks)** | Time sync error |
| 🟠 **Orange (3 blinks)** | Wi-Fi connection timeout |
| 🔴 **Red (3 blinks)** | API error |
| 🔴 **Red (6 fast blinks)** | Authentication error (401) |

## 📡 SwitchBot API

The project uses the SwitchBot API v1.1:

- **Endpoint**: `https://api.switch-bot.com/v1.1/devices/{deviceId}/commands`
- **Authentication**: token + secret with signed headers:
  - `Authorization`: your token
  - `nonce`: random hex string
  - `t`: Unix timestamp in milliseconds (1970 epoch)
  - `sign`: Base64(HMAC-SHA256(token + t + nonce, secret))
- **Commands**: `unlock` or `lock`

MicroPython on ESP32 uses the 2000-01-01 epoch internally. The code converts it to the Unix epoch (1970) before signing and retries an NTP sync if the RTC year looks wrong before sending a command. If the timestamp is off you will get a `401 Unauthorized` from the API.

Full documentation: https://github.com/OpenWonderLabs/SwitchBotAPI

## 🔍 Monitoring and Debug

Connect to the serial terminal (115200 baud) to see:

**Fresh boot:**
```
==================================================
M5Stack ATOM Lite - SwitchBot Lock Pro Controller
          (Deep Sleep Version)
==================================================

Device ID: XXXXXXXXXXXX
Wake button: GPIO39
Long press threshold: 1000ms

Controls:
  Short press (<1s) = UNLOCK (green LED)
  Long press  (>1s) = LOCK   (purple LED)

Entering deep sleep...
  Wake trigger: GPIO39 LOW (button press)
  Power consumption: ~10uA
==================================================
```

**Short press - UNLOCK:**
```
==================================================
WAKE FROM DEEP SLEEP - Button pressed!
==================================================
Button held for 450ms
Action: UNLOCK
Fast reconnect (ch=6)... OK!
✓ RTC time valid, skipping NTP sync

Sending UNLOCK command...
HTTP status: 200
✓ Door unlocked successfully!

Entering deep sleep...
```

**Long press - LOCK:**
```
==================================================
WAKE FROM DEEP SLEEP - Button pressed!
==================================================
Button held for 1523ms
Action: LOCK
Fast reconnect (ch=6)... OK!
✓ RTC time valid, skipping NTP sync

Sending LOCK command...
HTTP status: 200
✓ Door locked successfully!

Entering deep sleep...
```

## 🧪 Automated Tests

Tests run on standard CPython inside Docker — no MicroPython or hardware needed. Hardware modules are replaced by stubs automatically.

```bash
make test          # Build Docker image + run all tests
make test-clean    # Remove the test Docker image
```

Tests also run automatically via GitHub Actions on every push and PR to `main`.

**What's tested** (52 test cases):

| Area | Tests |
|------|-------|
| Epoch conversion | Offset constant, `unix_time_ms()` range and precision |
| HMAC-SHA256 | Manual RFC 2104 vs stdlib, long keys, empty inputs |
| Auth headers | Required keys, uppercase Base64 signature, timestamp format |
| HTTP send_command | Retry logic, 401 no-retry, response cleanup, error codes |
| RTC memory | Save/load roundtrip, invalid BSSID, channel bounds |
| LED brightness | `_scale()` math, clamping at 255 |
| Wi-Fi connect | Already-connected, timeout, fast reconnect, bssid fallback |

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
- Do not share your Token or Secret
- Use a secure Wi-Fi network (WPA2/WPA3)
- Consider using a dedicated VLAN for IoT devices

## 🙏 Acknowledgements

- [MicroPython](https://micropython.org/) - Python for microcontrollers
- [M5Stack](https://m5stack.com/) - Quality ESP32 hardware
- [SwitchBot](https://www.switch-bot.com/) - Smart home devices
