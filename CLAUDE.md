# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MicroPython firmware for M5Stack ATOM Lite (ESP32) controlling a SwitchBot Lock Pro via API v1.1. Single-file architecture (`main.py`) with deep sleep between button presses. Short press = UNLOCK, long press (≥1s) = LOCK.

## Development Commands

```bash
# Tests (Docker, no hardware needed)
make test                                              # 106 tests in Docker
python -m pytest tests/test_battery.py::test_name -v   # Single test locally

# Upload to device
mpremote connect /dev/cu.usbserial-XXXX cp main.py :main.py
mpremote connect /dev/cu.usbserial-XXXX cp config.py :config.py
```

## ESP32 System Heap / mbedTLS Constraint (CRITICAL)

The ESP32-PICO-D4 has a **system heap** (invisible to Python) used by WiFi/mbedTLS for TLS/RSA. Fragmentation causes `MBEDTLS_ERR_MPI_ALLOC_FAILED`.

### NEVER do before `urequests.post()`:
- `gc.collect()` — finalizers fragment system heap
- Module-level caching/computation — shifts heap layout at boot
- `machine.ADC()` — DMA buffer allocation on system heap
- `WDT(timeout=...)` — hardware timer on system heap
- Extra `import` statements — each shifts system heap layout
- `wlan.config(pm=0)` — increases WiFi heap usage

### Safe patterns:
- `gc.collect()` AFTER HTTP requests only
- Lazy imports inside functions, not module-level
- ADC reads (`read_battery_voltage()`) AFTER WiFi disconnect
- `try: from config import X / except: X = default` — config already loaded
- Minimal module-level globals

## RTC Memory Layout (v2, 12 bytes)

| Bytes | Content | Flag |
|-------|---------|------|
| 0-5 | BSSID | |
| 6 | WiFi channel | |
| 7 | Valid flag | 0xBB (v2) or 0xAA (legacy 8-byte) |
| 8-9 | Battery voltage (uint16 LE mV) | |
| 10 | Wake counter (uint8, wraps 255) | |
| 11 | Reserved | |

## Configuration (`config.py`, git-ignored)

Required: `WIFI_SSID`, `WIFI_PASSWORD`, `SWITCHBOT_TOKEN`, `SWITCHBOT_SECRET`, `SWITCHBOT_DEVICE_ID`, `BUTTON_GPIO`

Optional: `WIFI_STATIC_IP`, `LED_BRIGHTNESS` (default 32), `BATTERY_LOW_MV` (default 3300), `LOG_LEVEL` ("verbose"/"minimal"/"silent")

## Testing Architecture

`tests/conftest.py` injects fake MicroPython modules into `sys.modules` BEFORE `import main`. Key stubs: `FakeRTC` (variable-size memory), `FakeWLAN`, `FakeADC`, `FakeNeoPixel`. The `_reset_rtc` fixture resets RTC memory between tests.

## Wake Cycle Data Flow

```
Boot → increment_wake_counter → measure_button_press → CPU 160MHz →
WiFi connect (BSSID+channel cache) → NTP (skip if valid) →
API lock/unlock → WiFi disconnect → CPU 80MHz →
ADC battery read → LED feedback → low battery check →
NeoPixel GPIO hold → Deep Sleep (GPIO 39)
```
