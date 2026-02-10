# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MicroPython firmware for M5Stack ATOM Lite (ESP32) that controls a SwitchBot Lock Pro via the SwitchBot API v1.1. Uses deep sleep for ultra-low power consumption (~10uA idle).

- **Short press (<1s)**: UNLOCK the door
- **Long press (≥1s)**: LOCK the door

Device wakes on button press, measures hold duration, executes lock/unlock, then returns to deep sleep.

## Development Commands

### Upload to Device
```bash
mpremote connect /dev/cu.usbserial-XXXX cp main.py :main.py
mpremote connect /dev/cu.usbserial-XXXX cp config.py :config.py
```

### Run/Test via Serial
```bash
mpremote connect /dev/cu.usbserial-XXXX run main.py
# Or connect serial terminal:
screen /dev/cu.usbserial-XXXX 115200
```

### Flash MicroPython Firmware (One-time)
```bash
esptool --port $PORT --baud 460800 erase-flash
esptool --port $PORT --baud 460800 write_flash 0x1000 M5STACK_ATOM-*.bin
```

## Architecture

**Single-file architecture** (`main.py`) with deep sleep for minimal power consumption:

### Core Components
1. **StatusLED** - RGB NeoPixel on GPIO 27 with multicolor feedback
2. **SwitchBotController** - API v1.1 authentication (HMAC-SHA256) and HTTP
3. **RTC Memory** - Caches Wi-Fi BSSID for fast reconnect + channel for diagnostics (survives deep sleep)

### Data Flow
```
Boot/Wake
    ↓
Check reset_cause()
    ↓
┌─────────────────────────────────────┐
│ DEEPSLEEP_RESET (button press)      │
│   1. Measure press duration         │
│      - <1s = UNLOCK (green LED)     │
│      - ≥1s = LOCK (purple LED)      │
│   2. CPU → 160MHz                   │
│   3. Wi-Fi connect (fast if cached) │
│   4. NTP sync (skip if RTC valid)   │
│   5. API lock/unlock (retry once)   │
│   6. LED feedback (color by result) │
│   7. Wi-Fi disconnect               │
│   8. CPU → 80MHz                    │
└─────────────────────────────────────┘
    ↓
Deep Sleep (wake on GPIO 39 LOW)
```

### Button Controls
| Press Duration | Action | LED While Holding |
|----------------|--------|-------------------|
| < 1 second | UNLOCK | Green |
| ≥ 1 second | LOCK | Purple |

### LED Color Codes
| Color | Meaning |
|-------|---------|
| Green (holding) | Short press - will UNLOCK |
| Purple (holding) | Long press - will LOCK |
| Blue | Wi-Fi connecting (normal scan) |
| Cyan | Fast reconnect in progress |
| Green (2 blinks) | Success - door unlocked |
| Purple (2 blinks) | Success - door locked |
| Yellow (2 blinks) | NTP sync failed (continuing) |
| Yellow (4 blinks) | Time sync error |
| Orange (3 blinks) | Wi-Fi timeout |
| Red (3 blinks) | API error |
| Red (6 fast) | Auth error (401) |

## Critical Implementation Details

- **Deep sleep**: `esp32.wake_on_ext0()` on GPIO 39. Power: ~10uA sleep vs ~80-150mA active.
- **Epoch conversion**: MicroPython uses year 2000 epoch, SwitchBot API requires Unix epoch (1970). `unix_time_ms()` adds `946684800` seconds offset.
- **RTC memory layout**: Bytes 0-5 = BSSID (used for reconnect), Byte 6 = channel (diagnostic only), Byte 7 = valid flag (0xAA)
- **Memory management**: `gc.collect()` after HTTP requests
- **Watchdog timer**: 60s WDT in `handle_button_wake()` with `feed()` at checkpoints (post-WiFi, post-NTP, post-API). Resets device if any single phase hangs.

## Performance & Power Optimizations

| Optimization | Savings | Implementation |
|--------------|---------|----------------|
| Skip NTP | ~500ms-1s | `is_time_valid()` checks RTC year >= 2024 |
| Fast reconnect | ~1-2s | BSSID cached in RTC memory (strongest RSSI, skips full AP scan) |
| CPU scaling | ~20% CPU power | 80MHz idle/LED, 160MHz only for Wi-Fi/API |
| Early WiFi disconnect | ~100-120mA for ~800ms | WiFi off before LED feedback blinks |
| Configurable TX power | ~30-50mA during WiFi | `WIFI_TX_POWER` in config.py (dBm) |
| Shorter LED blinks | ~400ms wake time | Halved blink durations |
| API retry | +reliability | Single retry, skip on 401 errors |

**Result**: First press ~3-5s, subsequent presses ~1-2s

## Key Functions

- `handle_button_wake(led)` - Main wake handler, measures press duration, lock/unlock
- `measure_button_press(gpio, led)` - Measures button hold time with visual feedback
- `connect_wifi()` - Wi-Fi with fast reconnect support
- `save_wifi_config()` / `load_wifi_config()` - RTC memory cache
- `send_command(command, retries)` - API call for "lock" or "unlock"
- `set_cpu_freq(mhz)` - CPU frequency scaling (80/160/240)
- `StatusLED` colors: `green()`, `red()`, `blue()`, `cyan()`, `yellow()`, `orange()`, `purple()`
- `StatusLED` blinks: `blink_*()`, `blink_fast_red()`
- `LONG_PRESS_MS` - Threshold constant (1000ms default)

## Configuration

Copy `config_template.py` to `config.py` and fill in credentials. **config.py is git-ignored**.

Required values:
- `WIFI_SSID`, `WIFI_PASSWORD`
- `SWITCHBOT_TOKEN`, `SWITCHBOT_SECRET` (from SwitchBot app)
- `SWITCHBOT_DEVICE_ID`
- `BUTTON_GPIO` (default: 39 for M5Stack ATOM)

Optional:
- `WIFI_TX_POWER` (dBm, default: max ~20.5dBm). Lower values save battery if router is nearby. Examples: 8 (very close), 13 (same room), 17 (one wall).

## Testing

### Automated Tests (Docker)
```bash
make test          # Build image + run 52 tests in Docker (Python 3.13)
make test-clean    # Remove test Docker image
```

Tests run on CPython via hardware stubs injected in `tests/conftest.py`. No MicroPython or hardware required.

| Test File | What It Covers |
|-----------|----------------|
| `test_epoch.py` | `unix_time_ms()`, `_IS_MP_EPOCH`, epoch offset constant |
| `test_hmac.py` | `hmac_sha256_digest()` manual RFC 2104 vs stdlib |
| `test_auth_headers.py` | `_build_auth_headers()` structure, HMAC signature |
| `test_send_command.py` | HTTP retry, response.close(), 401 no-retry |
| `test_rtc_memory.py` | `save/load_wifi_config()` byte serialization |
| `test_led.py` | `StatusLED._scale()` brightness math |
| `test_wifi.py` | `connect_wifi()` timeout, already-connected |

### Manual Validation (on hardware)
1. Monitor serial output at 115200 baud
2. Press button, observe LED and serial response
3. First press: Full Wi-Fi scan + NTP sync
4. Subsequent presses: Fast reconnect, NTP skipped
