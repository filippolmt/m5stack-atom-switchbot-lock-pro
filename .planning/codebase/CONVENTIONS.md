# Coding Conventions

**Analysis Date:** 2026-03-16

## Naming Patterns

**Files:**
- Firmware: `main.py` - Entry point for device firmware
- Configuration: `config.py` - User credentials (git-ignored); template provided at `config_template.py`
- Tests: `test_*.py` format in `tests/` directory
- Pattern: snake_case for all file names

**Functions:**
- snake_case for all functions: `unix_time_ms()`, `save_wifi_config()`, `connect_wifi()`, `measure_button_press()`
- Private functions prefixed with single underscore: `_build_auth_headers()`, `_generate_nonce()`, `_blink()`, `_scale()`
- Factory/helper functions in lowercase: `_make_controller()` in tests
- Constants in UPPER_CASE: `LONG_PRESS_MS`, `_UNIX_EPOCH_OFFSET_SECONDS`, `_RTC_VALID_FLAG`

**Variables:**
- snake_case for local/instance variables: `press_duration`, `cached_bssid`, `fake_wlan`, `fake_resp`
- Instance attributes snake_case: `self.token`, `self.brightness`, `self.device_id`
- Class variables UPPER_CASE when they are constants: `API_BASE_URL` (class constant in `SwitchBotController`)
- Fake/mock variables prefixed with `fake_`: `fake_gmtime`, `fake_wlan`, `fake_resp`

**Types:**
- Classes: PascalCase: `StatusLED`, `SwitchBotController`, `FakeResponse`, `FakeWLAN`, `FakeRTC`
- No explicit type hints (MicroPython convention for resource-constrained devices)
- Function docstrings describe input/output types

## Code Style

**Formatting:**
- No explicit formatter configured (no `.prettierrc`, `.black`, or `pyproject.toml [tool.black]`)
- Style follows PEP 8 conventions by convention
- Indentation: 4 spaces (Python standard)
- Line length: Generally kept reasonable; long comments/docstrings wrap

**Linting:**
- No linting configured in repo (no `.pylintrc`, `.flake8`)
- Tests run in Docker (Python 3.14-slim) with pytest; no linting step in CI

**Example formatting from `main.py`:**
```python
def measure_button_press(button_gpio, led, timeout_ms=5000):
    """
    Measure how long the button is held after wake.
    Shows visual feedback during measurement.

    Args:
        button_gpio: GPIO pin number of button
        led: StatusLED instance for feedback
        timeout_ms: Maximum time to wait for release

    Returns:
        int: Duration in milliseconds, or timeout_ms if not released
    """
    button = Pin(button_gpio, Pin.IN)
    start = time.ticks_ms()
    led.green()
    is_long = False

    while button.value() == 0:
        elapsed = time.ticks_diff(time.ticks_ms(), start)
        if not is_long and elapsed >= LONG_PRESS_MS:
            led.purple()
            is_long = True
        if elapsed > timeout_ms:
            break
        time.sleep_ms(50)

    duration = time.ticks_diff(time.ticks_ms(), start)
    led.off()
    return duration
```

## Import Organization

**Order:**
1. MicroPython built-in modules: `import network`, `import urequests`, `import time`, `from machine import Pin, deepsleep, reset_cause, DEEPSLEEP_RESET, freq`
2. Hardware/hardware-like modules: `import esp32`, `import gc`, `import ubinascii`, `import hashlib`
3. Conditional imports (try/except): `hmac`, `ujson` (with CPython fallback), `ntptime`
4. Custom modules: `from config import (...)`

**Lazy imports inside functions:**
- Modules imported conditionally inside functions to reduce module-level heap allocations (ESP32 constraint):
  - `random_bytes()` imports `os` or `urandom` on demand
  - `sync_time_via_ntp()` imports `ntptime` on demand
  - `connect_wifi()` imports `WIFI_STATIC_IP` from config on demand
  - `StatusLED.__init__()` imports `neopixel` on demand
  - `save_wifi_config()` and `load_wifi_config()` import `RTC` on demand

**Path Aliases:**
- No path aliases used; all imports are standard library or local

## Error Handling

**Patterns:**

1. **Exception swallowing with pass:** Used for best-effort operations where failure is acceptable
   ```python
   try:
       from config import WIFI_STATIC_IP
       wlan.ifconfig(WIFI_STATIC_IP)
   except (ImportError, AttributeError):
       pass  # WIFI_STATIC_IP not configured; use DHCP
   except (ValueError, OSError) as e:
       print(f"  Static IP rejected, using DHCP: {e}")
   ```

2. **Specific exception catching:** Different handling per exception type
   ```python
   try:
       response = urequests.post(url, headers=headers, data=data)
       if response is None:
           print("✗ No response from the API.")
           gc.collect()
           continue
       try:
           status = response.status_code
           text = response.text
       except Exception:
           status = -1
           text = "<no text>"
       finally:
           try:
               response.close()
           except Exception:
               pass
   except Exception as e:
       print(f"✗ Exception while sending the command: {e}")
   ```

3. **No retry on auth errors:** 401 returns immediately without retry
   ```python
   if status == 401:
       print("✗ Authentication failed (401). Check token/secret.")
       return "auth_error"
   ```

4. **Resource cleanup with finally:** Ensures response.close() is always called
   ```python
   finally:
       try:
           response.close()
       except Exception:
           pass  # Socket may already be closed
   ```

5. **Safe defaults:** Functions return None or False on error, not raising exceptions to caller
   ```python
   def load_wifi_config():
       try:
           # ...
       except Exception:
           pass
       return None, None  # Default if error
   ```

## Logging

**Framework:** console via `print()` - no logging library

**Patterns:**

1. **Status messages with ✓/✗ symbols:**
   ```python
   print("✓ Time synchronized via NTP (UTC).")
   print("✗ Unable to synchronize time via NTP:", e)
   print("✗ Authentication failed (401). Check token/secret.")
   ```

2. **Section markers:** Equals signs for readability
   ```python
   print("=" * 50)
   print("WAKE FROM DEEP SLEEP - Button pressed!")
   print("=" * 50)
   ```

3. **Progress dots:** For long operations (Wi-Fi connection)
   ```python
   print(f"Connecting to Wi-Fi: {ssid}...", end="")
   # ...
   print(".", end="")
   ```

4. **Verbose output:** Device diagnostics printed to serial
   ```python
   print(f"Button held for {press_duration}ms")
   print(f"Action: {command.upper()}")
   print(f"  IP: {wlan.ifconfig()[0]}")
   ```

## Comments

**When to Comment:**

1. **Critical algorithm explanations:** Especially for time zone handling
   ```python
   # MicroPython on ESP32 uses epoch 2000-01-01. SwitchBot needs Unix epoch (1970).
   # Detect MicroPython epoch (2000) and adjust to Unix epoch (1970)
   if time.gmtime(0)[0] == 2000:
       seconds += _UNIX_EPOCH_OFFSET_SECONDS
   ```

2. **Non-obvious hardware constraints:** Documented above code
   ```python
   # RTC memory layout for fast reconnect:
   # Bytes 0-5: BSSID (6 bytes)
   # Byte 6: Wi-Fi channel (1 byte)
   # Byte 7: Valid flag (0xAA = valid)
   ```

3. **Workarounds for firmware quirks:**
   ```python
   # GPIO 39 is input-only, has external pull-up on ATOM Lite
   button = Pin(button_gpio, Pin.IN)
   ```

4. **WARNING comments for critical sections:**
   ```python
   # NOTE: scan forces WiFi driver buffer reallocation, which may help
   # defragment system heap for mbedTLS RSA operations.
   ```

**Docstring Format:**
- Google-style docstrings with triple-quotes for functions
- Sections: description, Args (optional), Returns (optional)
```python
def send_command(self, command="unlock", retries=1):
    """
    Send lock/unlock command to the SwitchBot Lock Pro.

    Args:
        command: "unlock" or "lock" (default: "unlock")
        retries: Number of retry attempts on failure (default: 1)

    Returns:
        str: Result code - "success", "auth_error", "api_error",
             "time_error", "network_error"
    """
```

## Function Design

**Size:**
- Prefer focused functions: most are 10-50 lines
- Core business logic in well-named helpers: `measure_button_press()`, `send_command()`, `connect_wifi()`
- Related color methods grouped in `StatusLED` class

**Parameters:**
- Prefer positional args for required parameters
- Default values for optional: `timeout=10`, `brightness=64`, `retries=1`
- Avoid **kwargs; use explicit named parameters: `cached_bssid=None`, `cached_channel=None`
- Functions accept hardware abstractions: `led` parameter allows testing without hardware

**Return Values:**
- Prefer specific types: `bool` for success/failure, `str` for status codes, tuples for multi-value returns
- Status codes as strings for readability: `"success"`, `"auth_error"`, `"api_error"`, `"time_error"`, `"network_error"`, `"wifi_error"`
- Single responsibility: `send_command()` returns status, doesn't handle LED feedback

## Module Design

**Exports:**
- Main module `main.py` contains all firmware code; no separate module files
- Classes exported: `StatusLED`, `SwitchBotController`
- Functions exported: `connect_wifi()`, `sync_time_via_ntp()`, `ensure_time_synced()`, `send_command()`, `handle_button_wake()`, `main()`
- Internal constants with underscore: `_UNIX_EPOCH_OFFSET_SECONDS`, `_RTC_VALID_FLAG`

**Barrel Files:**
- Not used (single-file firmware architecture)

**Organization in main.py:**
1. Module docstring and imports (lines 1-72)
2. Epoch handling utilities (lines 74-176)
3. RTC memory for fast reconnect (lines 121-161)
4. HMAC and crypto utilities (lines 163-199)
5. StatusLED class definition (lines 206-276)
6. SwitchBotController class definition (lines 281-395)
7. Wi-Fi connection logic (lines 402-510)
8. Deep sleep management (lines 513-543)
9. Button handling and measurement (lines 546-711)
10. Main entry point (lines 716-756)

---

*Convention analysis: 2026-03-16*
