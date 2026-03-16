# M5Stack ATOM - SwitchBot Lock Pro Controller

Control your **SwitchBot Lock Pro** by simply pressing the button on your **M5Stack ATOM**! 🚪🔐

This project provides a complete solution to integrate your M5Stack ATOM (ESP32) with the SwitchBot API and control a SwitchBot Lock Pro over Wi-Fi.

## 🌟 Features

- ✅ **Deep sleep mode** - Ultra-low power consumption (~10uA ESP32 idle)
- ✅ **Wake on button press** - ESP32 wakes from deep sleep when button is pressed
- ✅ **On-demand Wi-Fi** - Connects only when needed, disconnects immediately after API response
- ✅ **Fast reconnect** - Caches Wi-Fi BSSID + channel for ~1-2s faster reconnection after deep sleep
- ✅ **Optional static IP** - Skip DHCP negotiation for ~500ms-1s faster connection
- ✅ **Battery monitoring** - Reads voltage via ADC GPIO 33 (Atomic Battery Base compatible)
- ✅ **Low battery warning** - Orange LED blinks when voltage drops below threshold
- ✅ **Wake cycle counter** - Tracks usage count in RTC memory for diagnostics
- ✅ **Configurable power profile** - LED brightness, battery thresholds, and logging via config.py
- ✅ **Logging control** - Three levels: verbose/minimal/silent for production power savings
- ✅ **Multicolor LED feedback** - Different colors indicate status and errors (brightness optimized)
- ✅ **SwitchBot API v1.1** with signed token + secret headers
- ✅ **Auto retry** - Retries API call once on failure
- ✅ **NeoPixel GPIO hold** - Holds LED data pin LOW during deep sleep to reduce quiescent current
- ✅ **Automated test suite** - 106 tests via Docker (Python 3.13 + pytest)
- ✅ **CI/CD** - GitHub Actions runs tests on push/PR
- ✅ **Complete setup guide** for VS Code + MicroPython

## 📋 Requirements

### Hardware

- **M5Stack ATOM Lite** (ESP32-PICO-D4)
- USB Type-C cable
- **SwitchBot Lock Pro** (set up and working)
- **Atomic Battery Base** (200mAh, optional) - for portable battery-powered operation

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

# Optional: static IP to skip DHCP (saves ~500ms-1s per connection)
# WIFI_STATIC_IP = ("192.168.1.100", "255.255.255.0", "192.168.1.1", "8.8.8.8")

# Power configuration (optional)
# LED_BRIGHTNESS = 32        # 0-255, lower = less power
# BATTERY_LOW_MV = 3300      # Low battery warning threshold (mV)
# LOG_LEVEL = "verbose"      # "verbose", "minimal", or "silent"
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
│   ├── test_rtc_memory.py    # RTC memory serialization (12-byte v2 layout)
│   ├── test_led.py      # LED brightness scaling & defaults
│   ├── test_battery.py  # ADC voltage reading & low-battery warning
│   ├── test_logging.py  # Log level filtering
│   ├── test_power_optimizations.py  # CPU freq, GPIO hold, timing
│   └── test_wifi.py     # Wi-Fi connection & channel caching
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

1. **On boot/reset**: Shows startup message, then enters deep sleep
2. **When you press the button**:
   - ESP32 wakes from deep sleep, increments wake counter
   - **Short press (<1s)** = UNLOCK (green LED while holding)
   - **Long press (≥1s)** = LOCK (purple LED while holding)
   - Connects to Wi-Fi (fast reconnect with BSSID + channel cache)
   - Syncs time via NTP (skipped if RTC valid)
   - Sends lock/unlock command to SwitchBot API
   - Disconnects Wi-Fi, scales CPU to 80MHz
   - Reads battery voltage via ADC (GPIO 33)
   - LED feedback based on result
   - Orange LED warning if battery below threshold
   - NeoPixel GPIO held LOW, enters deep sleep
3. **Power consumption**:
   - Deep sleep: ~4-11mA (board-level, USB/serial chip always on)
   - Active (Wi-Fi + API call): ~80-150mA for 1-5 seconds
   - LED feedback: ~12mA for ~0.25s (brightness 32, Wi-Fi already off)

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
| 🟠 **Orange (3 blinks, after feedback)** | Low battery warning (<3.3V) |
| 🔴 **Red (3 blinks)** | API error |
| 🔴 **Red (6 fast blinks)** | Authentication error (401) |

## 🔋 Atomic Battery Base

The project supports the [M5Stack Atomic Battery Base](https://docs.m5stack.com/en/atom/Atomic%20Battery%20Base) (200mAh, 3.7V) for portable operation.

### Specifications

| Property | Value |
|----------|-------|
| Battery | 3.7V @ 200mAh LiPo |
| Boost converter | ETA9085E10 (5V output) |
| Charging IC | LGS4056HDA (USB-C, 223mA) |
| Standby current | 2.55uA (boost converter) |
| Battery monitoring | GPIO 33 via 1:1 voltage divider (2x 1MOhm) |

### Realistic Battery Life

**Important:** The M5Stack ATOM Lite draws **4-11mA in deep sleep** (not 10uA) due to the always-on USB/serial chip. The firmware mitigates NeoPixel quiescent current via GPIO hold during sleep. With the 200mAh battery:

- **Estimated autonomy: 18-50 hours** depending on board revision (with GPIO hold optimization)
- Without GPIO hold: 12-40 hours
- Wake cycle consumption (~80-150mA for 1-5s) is <0.5% of total drain
- **Sleep current dominates** — the USB/serial chip (3-5mA) is the main drain and cannot be disabled in software
- For longer battery life, consider a larger battery (750-1000mAh → 3-8 days)

### Charging

- Connect USB-C to charge (blue LED = charging, green LED = full)
- Dip switch: **boost** for normal operation, **charge** when connected to USB
- Full charge: ~1 hour at 223mA

### Power Configuration

Tune power behavior in `config.py`:

```python
LED_BRIGHTNESS = 32        # 0-255 (default 32, lower = less power)
BATTERY_LOW_MV = 3300      # Low battery warning threshold (mV)
LOG_LEVEL = "minimal"      # "verbose", "minimal", or "silent"
```

Setting `LOG_LEVEL = "silent"` saves ~50-100ms per wake cycle by skipping UART transmission.

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

**Short press - UNLOCK (fast reconnect):**
```
==================================================
WAKE FROM DEEP SLEEP - Button pressed!
==================================================
Wake #42
Button held for 450ms
Action: UNLOCK
Fast reconnect available (ch=1)
Fast reconnect (ch=1)... [ch=1] OK!
  IP: 192.168.178.87
✓ RTC time valid, skipping NTP sync
Sending UNLOCK command...
HTTP status: 200
Response: {"statusCode":100,"body":{},"message":"success"}
Battery: 3850mV | Wake #42
✓ Door unlocked successfully!

Entering deep sleep...
```

**Long press - LOCK (first boot, normal scan):**
```
==================================================
WAKE FROM DEEP SLEEP - Button pressed!
==================================================
Wake #1
Button held for 1552ms
Action: LOCK
Connecting to Wi-Fi: MySSID...
..........................
✓ Connected to Wi-Fi!
  IP: 192.168.178.87
  Cached ch=1 for fast reconnect
RTC time invalid, syncing NTP...
Synchronizing time via NTP...
✓ Time synchronized via NTP (UTC).
Sending LOCK command...
HTTP status: 200
Response: {"statusCode":100,"body":{},"message":"success"}
Battery: 4120mV | Wake #1
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

**What's tested** (106 test cases):

| Area | Tests |
|------|-------|
| Epoch conversion | Offset constant, `unix_time_ms()` range and precision |
| HMAC-SHA256 | Manual RFC 2104 vs stdlib, long keys, empty inputs |
| Auth headers | Required keys, uppercase Base64 signature, timestamp format |
| HTTP send_command | Retry logic, 401 no-retry, response cleanup, attribute-raise resilience |
| RTC memory | Save/load roundtrip, 12-byte layout migration, battery voltage, wake counter |
| LED brightness | `_scale()` math, brightness constant, blink defaults |
| Battery monitoring | ADC voltage reading, low-battery warning, configurable threshold |
| Logging | Log level filtering, kwargs passthrough, defaults |
| Power optimizations | CPU freq reset, serial flush timing, GPIO hold, retry delay |
| Wi-Fi connect | Already-connected, timeout, fast reconnect, channel passing, fallback chain |

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
