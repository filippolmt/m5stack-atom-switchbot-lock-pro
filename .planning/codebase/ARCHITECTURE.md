# Architecture

**Analysis Date:** 2026-03-16

## Pattern Overview

**Overall:** Monolithic embedded firmware with event-driven state machine architecture (deep sleep/wake cycles).

**Key Characteristics:**
- Single entry point (`main()`) that branches on reset reason (deep sleep wake vs. cold boot)
- Deep sleep between button presses; device wakes only on GPIO 39 LOW signal
- Synchronous request/response flow: measure press → connect Wi-Fi → authenticate → send command → sleep
- Zero persistent state except RTC memory cache; state is ephemeral per wake cycle
- Modular class-based design: `StatusLED` (I/O abstraction), `SwitchBotController` (API client)
- Function-level utilities for cross-cutting concerns: time sync, Wi-Fi, RTC memory, cryptography

## Layers

**Device Drivers & Hardware Abstraction:**
- Purpose: Encapsulate ESP32 and M5Stack ATOM Lite peripherals
- Location: `main.py` lines 206-276 (`StatusLED` class) and scattered hardware calls (GPIO, deep sleep, RTC)
- Contains: NeoPixel LED control, button GPIO polling, CPU frequency scaling, RTC memory read/write
- Depends on: MicroPython `machine`, `neopixel`, `esp32` modules
- Used by: Button measurement (`measure_button_press()`), main loop (`handle_button_wake()`)

**Authentication & Cryptography:**
- Purpose: SwitchBot API v1.1 HMAC-SHA256 authentication headers
- Location: `main.py` lines 178-323 (`hmac_sha256_digest()`, `SwitchBotController._build_auth_headers()`)
- Contains: HMAC-SHA256 (stdlib or manual RFC 2104 fallback), nonce generation, timestamp signing
- Depends on: `hashlib`, `ubinascii`, `time` for millisecond conversion with epoch detection
- Used by: `SwitchBotController.send_command()`

**Networking & API Client:**
- Purpose: Wi-Fi management with fast reconnect, HTTP request retry, response cleanup
- Location: `main.py` lines 399-510 (`connect_wifi()`), `SwitchBotController` class (lines 281-395)
- Contains: WLAN connection with BSSID/channel caching, static IP support, retry loop on HTTP failures, 401 auth-error bypass, response socket cleanup
- Depends on: `network.WLAN`, `urequests.post()`, RTC memory for BSSID cache
- Used by: `handle_button_wake()` → Wi-Fi layer → API layer

**Time Synchronization:**
- Purpose: Ensure RTC validity for HMAC signing and timestamp generation
- Location: `main.py` lines 74-176 (`sync_time_via_ntp()`, `ensure_time_synced()`, `is_time_valid()`, `unix_time_ms()`)
- Contains: NTP client wrapper, epoch detection (2000 vs 1970), RTC year validation, Unix timestamp conversion
- Depends on: `ntptime` module, `time` module with epoch detection via `gmtime(0)[0]`
- Used by: `handle_button_wake()` (conditional), `send_command()` (time validation gate)

**RTC Memory Persistence:**
- Purpose: Cache Wi-Fi BSSID and channel across deep sleep cycles for fast reconnect
- Location: `main.py` lines 118-161 (`save_wifi_config()`, `load_wifi_config()`, `clear_wifi_config()`)
- Contains: 8-byte RTC memory layout (BSSID 6 bytes, channel 1 byte, valid flag 1 byte), roundtrip serialization
- Depends on: `machine.RTC()`
- Used by: `connect_wifi()` (cache load), post-connection (cache save)

**State Machine & Control Flow:**
- Purpose: Orchestrate wake reason detection, button measurement, command dispatch, and sleep return
- Location: `main.py` lines 587-751 (`handle_button_wake()`, `main()`)
- Contains: Reset cause checking, press duration measurement, LED feedback sequences, Wi-Fi→API command chain
- Depends on: All lower layers (LED, time, network, API)
- Used by: `__main__` entry point (line 754)

## Data Flow

**Cold Boot or Power-On Reset:**

1. `main()` is called
2. `StatusLED` is initialized (GPIO 27, brightness 64)
3. `reset_cause()` is checked:
   - If **not** `DEEPSLEEP_RESET`: show startup splash, blink LEDs, go to sleep
   - If **is** `DEEPSLEEP_RESET`: continue to button wake handler

**Button Press / Wake from Deep Sleep:**

1. Device wakes on GPIO 39 LOW (external pull-up, active-low button)
2. `handle_button_wake()` measures button press duration:
   - Read GPIO 39 voltage level while pressed
   - Show green LED while <1000ms (indicates short press = unlock)
   - Switch to purple LED when ≥1000ms (indicates long press = lock)
   - Return elapsed milliseconds
3. Determine action: `is_lock = press_duration >= LONG_PRESS_MS` (1000ms)
4. Boost CPU to 160MHz for Wi-Fi performance
5. Load cached BSSID/channel from RTC memory:
   - If cached: show cyan LED, attempt fast 4-second reconnect
   - If not cached or timeout: show blue LED, perform full network scan
6. `connect_wifi()` executes:
   - Try fast reconnect with BSSID (if available)
   - On fast timeout: clear cache, fall back to full scan
   - On success: cache BSSID+channel for next wake
7. Check RTC time validity (year ≥ 2024):
   - If valid: skip NTP, reuse existing timestamp
   - If invalid: sync via NTP, validate, show yellow warning if failed
8. Create `SwitchBotController` and send command:
   - Build auth headers with HMAC-SHA256 (token + timestamp + nonce)
   - `urequests.post()` to SwitchBot API v1.1
   - On 401: return immediately (auth_error), no retry
   - On other failures (500, network): retry once after 500ms delay
   - Always call `response.close()` to release socket
9. Disconnect Wi-Fi early (save ~120mA during LED feedback)
10. Show result LED feedback:
    - Success + unlock: green 2 blinks
    - Success + lock: purple 2 blinks
    - Auth error (401): red 6 fast blinks
    - Time error: yellow 4 blinks
    - API error: red 3 blinks
11. Scale CPU back to 80MHz and enter deep sleep on GPIO 39 LOW

**State Management:**

- **RTC memory (persists across sleep):** BSSID, channel, valid flag
- **Ephemeral state (lost on sleep):** Button press duration, press action (lock/unlock), Wi-Fi connection, RTC time, API response
- **No application state file:** Each cycle is independent; firmware does not maintain state in flash

## Key Abstractions

**StatusLED:**
- Purpose: Encapsulate NeoPixel RGB control with brightness scaling and blink sequences
- Examples: `main.py` lines 206-276
- Pattern: Stateful object; brightness applied globally, colors mixed via RGB tuples, blinks via loops
- Methods: `set_rgb()`, `off()`, color methods (`green()`, `red()`, etc.), blink methods (`blink_red()`, `blink_green()`, etc.)

**SwitchBotController:**
- Purpose: API client wrapper for SwitchBot Lock Pro commands
- Examples: `main.py` lines 281-395
- Pattern: Encapsulates endpoint, token, secret, device_id; builds authentication headers, sends HTTP POST, maps response codes to result strings
- Methods: `_generate_nonce()`, `_build_auth_headers()`, `send_command(command, retries)`
- Returns: String result codes (`"success"`, `"auth_error"`, `"api_error"`, `"time_error"`, `"network_error"`)

**RTC Memory Layout:**
- Purpose: Atomic 8-byte cache for Wi-Fi fast reconnect across deep sleep
- Examples: `main.py` lines 121-151
- Pattern: Fixed-size bytearray; bytes 0-5 = BSSID, byte 6 = channel, byte 7 = valid flag (0xAA)
- Functions: `save_wifi_config(bssid, channel)`, `load_wifi_config()`, `clear_wifi_config()`

**Epoch Detection:**
- Purpose: Handle MicroPython (epoch 2000) vs. CPython/Unix (epoch 1970) time differences
- Examples: `main.py` lines 56-57, 163-175
- Pattern: Detect at runtime via `time.gmtime(0)[0]` (fallback to 2000 if gmtime breaks), add offset when needed
- Constant: `_UNIX_EPOCH_OFFSET_SECONDS = 946684800` (seconds between 1970 and 2000)

## Entry Points

**`main()` (lines 716-752):**
- Location: `main.py` lines 716-752
- Triggers: Execution on device boot (explicit in line 754-756)
- Responsibilities:
  - Initialize status LED
  - Check `reset_cause()` to determine wake reason
  - Branch to `handle_button_wake()` if waking from deep sleep, otherwise show boot splash
  - Always call `enter_deep_sleep()` at the end

**`handle_button_wake()` (lines 587-711):**
- Location: `main.py` lines 587-711
- Triggers: Called from `main()` when `reset_cause() == DEEPSLEEP_RESET`
- Responsibilities:
  - Measure button press duration via `measure_button_press()`
  - Determine lock vs. unlock based on duration
  - Manage Wi-Fi connection with fast reconnect
  - Validate RTC time, sync NTP if needed
  - Create controller and send command with retries
  - Provide LED feedback for each result code
  - Disconnect Wi-Fi early to save power

## Error Handling

**Strategy:** Fail-open with LED feedback; device always returns to sleep regardless of errors.

**Patterns:**

1. **Time validation without abort:** If NTP fails, show yellow warning blink but continue with API request (SwitchBot may accept stale timestamp).
2. **No retry on 401 (auth error):** Indicates bad token/secret; retrying won't help.
3. **Retry on 500/network errors:** Single retry (default `retries=1`), 500ms delay between attempts.
4. **Response cleanup:** Always call `response.close()` in try/finally to release sockets (memory-critical on ESP32).
5. **Wi-Fi cleanup:** Always disconnect and deactivate Wi-Fi after command, even if LED feedback loop runs after.
6. **Exception catching with fallback:** GPS/RTC failures caught; falls back to defaults or skips optional steps.
7. **GPIO polling with soft timeout:** Button measurement times out after 5s (releases GPIO if button stuck).

## Cross-Cutting Concerns

**Logging:** Console via `print()` statements; logged to serial at 115200 baud.
- Info level: `print("✓ ...")` (checkmark prefix)
- Error level: `print("✗ ...")` (X prefix)
- Warning level: `print("⚠ ...")` (warning triangle prefix)
- Progress dots: `print(".", end="")` during Wi-Fi connection loops

**Validation:**
- RTC year check (`min_year=2024`) before allowing HTTP requests
- BSSID length and type check before RTC save (6 bytes)
- Wi-Fi channel range validation (1-14)
- Response status code mapping (200=success, 401=auth_error, other=api_error)

**Authentication:**
- Token + timestamp + nonce signed with secret via HMAC-SHA256 in uppercase base64
- Headers: `Authorization` (token), `sign` (signature), `nonce`, `t` (timestamp), `Content-Type`
- Credentials loaded from `config.py` module (git-ignored)

---

*Architecture analysis: 2026-03-16*
