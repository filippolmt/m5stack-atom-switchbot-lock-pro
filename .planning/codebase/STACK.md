# Technology Stack

**Analysis Date:** 2026-03-16

## Languages

**Primary:**
- MicroPython 1.24.x or later - Firmware code for ESP32 microcontroller, runs on M5Stack ATOM Lite
- Python 3.13+ - Test suite and development tools (not on device)

**Secondary:**
- Bash - Build and deployment scripts (Makefile)

## Runtime

**Environment:**
- ESP32-PICO-D4 microcontroller (M5Stack ATOM Lite) with 4 MB flash, 520 KB RAM
- MicroPython interpreter on ESP32
- Python 3.13+ on host machine for testing

**Package Manager:**
- pip (Python) - for test dependencies only
- Lockfile: `pyproject.toml` (minimal, pytest-only)

## Frameworks

**Core:**
- MicroPython standard library only - No external frameworks; uses built-in modules:
  - `machine` - GPIO, deep sleep, CPU frequency control
  - `network` - Wi-Fi connectivity via WLAN
  - `time` / `ntptime` - System time and NTP synchronization
  - `hashlib` / `hmac` - Cryptographic operations for API authentication
  - `json` / `ujson` - JSON encoding/decoding

**HTTP Client:**
- `urequests` - Lightweight HTTP client for MicroPython (included with MicroPython)

**Hardware:**
- `neopixel` - RGB LED control for status feedback (M5Stack ATOM GPIO 27)

**Testing:**
- pytest 7.x+ - Test runner (host machine only)

**Build/Dev:**
- Docker - Test containerization (Dockerfile.test builds Python 3.14 slim image)
- Make - Build automation (Makefile for test targets)
- `mpremote` - Serial file transfer and execution on ESP32

## Key Dependencies

**Critical (MicroPython built-ins):**
- `machine.Pin` - GPIO pin control (button on GPIO 39)
- `machine.deepsleep()` / `esp32.wake_on_ext0()` - Deep sleep and wake management
- `hashlib.sha256()` - SHA256 hashing for HMAC-SHA256 API signatures
- `urequests.post()` - HTTPS POST to SwitchBot API v1.1

**Optional (fallback support):**
- `hmac` module - Standard HMAC implementation; code falls back to manual RFC 2104 if unavailable
- `os.urandom()` - Cryptographically secure random bytes for nonce; falls back to Linear Congruential Generator (LCG) if missing

**Testing (host only):**
- pytest - Test framework
- No mock libraries used; test stubs injected via `conftest.py` monkey-patching

## Configuration

**Environment:**
- `config.py` (user-created from `config_template.py`) - Contains:
  - `WIFI_SSID`, `WIFI_PASSWORD` - Network credentials
  - `SWITCHBOT_TOKEN`, `SWITCHBOT_SECRET` - API authentication
  - `SWITCHBOT_DEVICE_ID` - Target lock device identifier
  - `BUTTON_GPIO` - GPIO pin for button (default: 39)
  - `WIFI_STATIC_IP` (optional) - Tuple for static IP assignment, skips DHCP (~500ms-1s savings)

**Build:**
- `Dockerfile.test` - Specifies Python 3.14 slim base for test execution
- `Makefile` - Three targets: `test-build`, `test`, `test-clean`
- `pyproject.toml` - Minimal pytest configuration (testpaths, pythonpath)

## Platform Requirements

**Development:**
- Python 3.13+
- pip (for pytest)
- Docker (optional, for containerized testing)
- MicroPython firmware binary (M5STACK_ATOM-*.bin)
- `mpremote` CLI tool

**Production (Device):**
- M5Stack ATOM Lite (ESP32-PICO-D4)
- USB Type-C for flashing and development
- MicroPython v1.24.x+ flashed to ESP32
- Wi-Fi network access
- Active SwitchBot Lock Pro and SwitchBot API credentials

**Power:**
- Deep sleep: ~10 µA
- Active (Wi-Fi + API): ~80-150 mA
- Total press-to-complete cycle: 1-5 seconds (first press with full NTP sync)

---

*Stack analysis: 2026-03-16*
