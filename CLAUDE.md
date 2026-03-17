# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MicroPython firmware for M5Stack ATOM Lite (ESP32) controlling a SwitchBot Lock Pro via API v1.1. Single-file architecture (`main.py`) with deep sleep between button presses. Short press = UNLOCK, long press (≥1s) = LOCK.

## Development Commands

```bash
# Tests (Docker, no hardware needed)
make test                                              # 53 tests in Docker
python -m pytest tests/test_wifi.py::test_name -v      # Single test locally

# Flash firmware (use 115200 baud — 460800 causes disconnects on some boards)
esptool --port $PORT --baud 115200 erase-flash
esptool --port $PORT --baud 115200 write_flash 0x1000 M5STACK_ATOM-*.bin

# Upload to device
mpremote connect /dev/cu.usbserial-XXXX cp main.py :main.py
mpremote connect /dev/cu.usbserial-XXXX cp config.py :config.py
```

## ESP32 System Heap / mbedTLS Constraint (CRITICAL)

The ESP32-PICO-D4 has a **system heap** (invisible to Python) used by WiFi/mbedTLS for TLS/RSA. Any change to module-level code (new functions, imports, constants, dicts) shifts the heap layout and causes `MBEDTLS_ERR_MPI_ALLOC_FAILED`. **Confirmed: even adding a single `Pin()` allocation or function definition breaks TLS.**

### NEVER do:
- Add new module-level functions, constants, dicts, or imports
- `gc.collect()`, `machine.ADC()`, or `Pin()` allocations before `urequests.post()`
- `WDT(timeout=...)`, `wlan.config(pm=0)`, extra `import` statements

### Safe changes:
- Modify **existing numeric values** only (brightness, timing, delays) — same bytecode structure
- `gc.collect()` AFTER HTTP requests
- Lazy imports inside **existing** functions
- `try: from config import X / except: pass` inside **existing** functions

## Configuration

Copy `config_template.py` to `config.py` (git-ignored). Required: `WIFI_SSID`, `WIFI_PASSWORD`, `SWITCHBOT_TOKEN`, `SWITCHBOT_SECRET`, `SWITCHBOT_DEVICE_ID`, `BUTTON_GPIO`. Optional: `WIFI_STATIC_IP`.

## RTC Memory Layout (8 bytes)

| Bytes | Content |
|-------|---------|
| 0-5 | BSSID (for fast reconnect) |
| 6 | WiFi channel |
| 7 | Valid flag (0xAA) |

## Testing

`tests/conftest.py` injects fake MicroPython modules (`machine`, `network`, `neopixel`, `urequests`, `ntptime`, `config`) into `sys.modules` BEFORE `import main`. Key stubs: `FakeRTC`, `FakeWLAN`, `FakeNeoPixel`. The `_reset_rtc` fixture resets RTC memory between tests.
