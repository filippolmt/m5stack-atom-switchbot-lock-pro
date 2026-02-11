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
│   6. Wi-Fi disconnect               │
│   7. LED feedback (color by result) │
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
- **Epoch conversion**: MicroPython uses year 2000 epoch, SwitchBot API requires Unix epoch (1970). `unix_time_ms()` detects epoch at call time via `time.gmtime(0)[0]` and adds `946684800` seconds offset when needed.
- **RTC memory layout**: Bytes 0-5 = BSSID (used for reconnect), Byte 6 = channel (diagnostic only), Byte 7 = valid flag (0xAA)
- **Memory management**: `gc.collect()` after HTTP requests only. See **ESP32 System Heap / mbedTLS Constraint** below.

## ESP32 System Heap / mbedTLS Constraint (CRITICAL)

The ESP32-PICO-D4 (no PSRAM) has two separate heaps: the **Python GC heap** (`gc.mem_free()`) and the **system heap** (used by the WiFi driver and mbedTLS for TLS/RSA operations). `gc.mem_free()` only reports the Python heap — the system heap is invisible to Python code.

**mbedTLS requires large contiguous blocks on the system heap** for RSA public key operations during the TLS handshake. If the system heap is fragmented, TLS fails with `MBEDTLS_ERR_MPI_ALLOC_FAILED` (-17040) or `MBEDTLS_ERR_RSA_PUBLIC_FAILED` / `MBEDTLS_ERR_PK_INVALID_PUBKEY`, even when Python heap shows 127KB+ free.

### DO NOT do any of the following before `urequests.post()`:

| Forbidden Pattern | Why It Breaks TLS |
|---|---|
| `gc.collect()` before POST | Frees Python objects whose finalizers release system heap memory mid-allocation, creating fragmentation gaps |
| Module-level caching (e.g. `_IS_MP_EPOCH = time.gmtime(0)[0] == 2000`) | Changes system heap layout at boot, shifting where mbedTLS allocates |
| `wlan.config(pm=0)` (WiFi PS_NONE) | Increases WiFi driver system heap usage, competing with mbedTLS |
| `WDT(timeout=...)` | Allocates hardware timer resources from system heap, confirmed to cause MBEDTLS_ERR_MPI_ALLOC_FAILED |
| `usocket.setdefaulttimeout()` | May interfere with TLS socket internals |
| Extra `import` statements (e.g. `import urandom`) | Each import adds bytecode + module objects, shifting system heap layout at boot. Confirmed: adding `urandom` fallbacks to `random_bytes()` triggered MBEDTLS_ERR_MPI_ALLOC_FAILED |

### Safe patterns:
- `gc.collect()` **after** HTTP requests (cleanup only)
- BSSID caching via `wlan.config('bssid')` with `wlan.scan()` fallback (scan may help consolidate system heap)
- Inline epoch detection inside `unix_time_ms()` (no module-level allocation)
- Lazy imports inside functions (e.g. `random_bytes()`, static IP) instead of module-level
- Minimal module-level globals — every global allocation shifts the system heap layout

## Performance & Power Optimizations

| Optimization | Savings | Implementation |
|--------------|---------|----------------|
| Skip NTP | ~500ms-1s | `is_time_valid()` checks RTC year >= 2024 |
| Fast reconnect | ~1-2s | BSSID cached in RTC memory (strongest RSSI, skips full AP scan) |
| Static IP | ~500ms-1s | Optional `WIFI_STATIC_IP` in config.py (skips DHCP) |
| CPU scaling | ~20% CPU power | 80MHz idle/LED, 160MHz only for Wi-Fi/API |
| Early WiFi disconnect | ~100-120mA for ~800ms | WiFi off before LED feedback blinks |
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
- `WIFI_STATIC_IP` (tuple: IP, subnet, gateway, DNS). Skips DHCP negotiation, saves ~500ms-1s per connection. Example: `("192.168.1.100", "255.255.255.0", "192.168.1.1", "8.8.8.8")`

**Note**: `WIFI_TX_POWER` was removed due to ESP32 system heap constraints (see ESP32 mbedTLS section).

## Testing

### Automated Tests (Docker)
```bash
make test          # Build image + run 53 tests in Docker (Python 3.13)
make test-clean    # Remove test Docker image
```

Tests run on CPython via hardware stubs injected in `tests/conftest.py`. No MicroPython or hardware required.

| Test File | What It Covers |
|-----------|----------------|
| `test_epoch.py` | `unix_time_ms()`, epoch offset constant, inline epoch detection, gmtime-broken fallback |
| `test_hmac.py` | `hmac_sha256_digest()` manual RFC 2104 vs stdlib |
| `test_auth_headers.py` | `_build_auth_headers()` structure, HMAC signature |
| `test_send_command.py` | HTTP retry, response.close(), 401 no-retry, attribute-raise cleanup |
| `test_rtc_memory.py` | `save/load_wifi_config()` byte serialization |
| `test_led.py` | `StatusLED._scale()` brightness math |
| `test_wifi.py` | `connect_wifi()` timeout, already-connected |

### Manual Validation (on hardware)
1. Monitor serial output at 115200 baud
2. Press button, observe LED and serial response
3. First press: Full Wi-Fi scan + NTP sync
4. Subsequent presses: Fast reconnect, NTP skipped
