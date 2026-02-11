"""
M5Stack ATOM Lite - SwitchBot Lock Pro Controller (Deep Sleep Version)
- Deep sleep for minimal power consumption (~10uA)
- Wake on button press (GPIO 39)
- Short press (<1s) = UNLOCK, Long press (>=1s) = LOCK
- Wi-Fi with fast reconnect (cached BSSID) + optional static IP
- SwitchBot API v1.1 authentication (token + secret + HMAC-SHA256)
- Multicolor LED feedback for status and errors
- Returns to deep sleep after command execution
"""

import network
import urequests
import time
from machine import Pin, deepsleep, reset_cause, DEEPSLEEP_RESET, freq
import esp32
import gc
import ubinascii
import hashlib

# RTC memory layout for fast reconnect:
# Bytes 0-5: BSSID (6 bytes)
# Byte 6: Wi-Fi channel (1 byte)
# Byte 7: Valid flag (0xAA = valid)
_RTC_VALID_FLAG = 0xAA

# Try to use hmac if available, otherwise fall back to the manual version
try:
    import hmac

    HAVE_HMAC = True
except ImportError:
    HAVE_HMAC = False

def random_bytes(n):
    """Generate n random bytes for nonce. Lazy import to reduce module-level allocations."""
    try:
        import os
        return os.urandom(n)
    except (ImportError, AttributeError, OSError):
        pass  # os.urandom unavailable; fall through to LCG
    # LCG fallback (deterministic but sufficient for nonce uniqueness)
    b = bytearray(n)
    seed = time.ticks_ms() & 0xFFFFFFFF
    for i in range(n):
        seed = (1103515245 * seed + 12345) & 0xFFFFFFFF
        b[i] = seed & 0xFF
    return bytes(b)


try:
    import ujson as json
except ImportError:
    import json

# MicroPython on ESP32 uses epoch 2000-01-01. SwitchBot needs Unix epoch (1970).
_UNIX_EPOCH_OFFSET_SECONDS = 946684800  # seconds between 1970-01-01 and 2000-01-01

try:
    from config import (
        WIFI_SSID,
        WIFI_PASSWORD,
        SWITCHBOT_TOKEN,
        SWITCHBOT_SECRET,
        SWITCHBOT_DEVICE_ID,
        BUTTON_GPIO,
    )
except ImportError:
    print("ERROR: File config.py not found!")
    print("Copy config_template.py to config.py and fill in your data.")
    raise


def sync_time_via_ntp():
    """Sync the system clock via NTP (needed for the correct timestamp)."""
    try:
        import ntptime

        print("Synchronizing time via NTP...")
        ntptime.settime()  # Set UTC time
        print("✓ Time synchronized via NTP (UTC).")
    except Exception as e:
        print("✗ Unable to synchronize time via NTP:", e)
        print("  WARNING: if the clock is wrong, the SwitchBot API can reply with 401.")


def ensure_time_synced(min_year=2024):
    """
    Ensure the RTC has a sensible UTC year before signing requests.
    Returns True if the time looks valid; otherwise tries NTP once.
    """
    try:
        current_year = time.gmtime()[0]
        if current_year < min_year:
            print(f"Clock seems unsynchronized (year={current_year}). Trying NTP...")
            sync_time_via_ntp()
            current_year = time.gmtime()[0]

        if current_year < min_year:
            print(
                f"Clock still invalid after NTP (year={current_year}). Aborting request."
            )
            return False
        return True
    except Exception as e:
        print("✗ Unable to verify system time:", e)
        return False


def is_time_valid(min_year=2024):
    """Check if RTC time is already valid (survives deep sleep)."""
    try:
        return time.gmtime()[0] >= min_year
    except Exception:
        return False  # Assume time invalid if gmtime() fails


# --------------------- RTC MEMORY FOR FAST RECONNECT --------------------- #


def save_wifi_config(bssid, channel):
    """Save Wi-Fi BSSID and channel to RTC memory for fast reconnect."""
    try:
        if not isinstance(bssid, bytes) or len(bssid) != 6:
            return
        from machine import RTC
        data = bytearray(8)
        data[0:6] = bssid
        data[6] = channel & 0xFF
        data[7] = _RTC_VALID_FLAG
        RTC().memory(data)
    except Exception as e:
        print(f"Could not save Wi-Fi config: {e}")


def load_wifi_config():
    """
    Load Wi-Fi config from RTC memory.
    Returns (bssid, channel) or (None, None) if not available.
    """
    try:
        from machine import RTC
        data = RTC().memory()
        if data and len(data) >= 8 and data[7] == _RTC_VALID_FLAG:
            bssid = bytes(data[0:6])
            raw_channel = data[6]
            channel = raw_channel if 0 < raw_channel <= 14 else None
            return bssid, channel
    except Exception:
        pass  # RTC memory unavailable or corrupted; return defaults below
    return None, None


def clear_wifi_config():
    """Clear saved Wi-Fi config from RTC memory."""
    try:
        from machine import RTC
        RTC().memory(bytearray(8))
    except Exception:
        pass  # Best-effort clear; ignore if RTC unavailable


def unix_time_ms():
    """
    Return current Unix time in milliseconds.
    MicroPython on ESP32 reports seconds from 2000-01-01, so convert when needed.
    """
    seconds = time.time()
    # Detect MicroPython epoch (2000) and adjust to Unix epoch (1970)
    try:
        if time.gmtime(0)[0] == 2000:
            seconds += _UNIX_EPOCH_OFFSET_SECONDS
    except Exception:
        seconds += _UNIX_EPOCH_OFFSET_SECONDS  # gmtime broken; assume MP epoch
    return int(seconds * 1000)


def hmac_sha256_digest(secret_bytes, msg_bytes):
    """
    Return HMAC-SHA256(secret, msg) digest as bytes.
    Use the hmac module when present, otherwise a manual implementation.
    """
    if HAVE_HMAC:
        mac = hmac.new(secret_bytes, msg_bytes, hashlib.sha256)
        return mac.digest()

    # Manual HMAC-SHA256 implementation (RFC 2104)
    block_size = 64
    key = secret_bytes
    if len(key) > block_size:
        key = hashlib.sha256(key).digest()
    if len(key) < block_size:
        key = key + b"\x00" * (block_size - len(key))

    o_key_pad = bytes([k ^ 0x5C for k in key])
    i_key_pad = bytes([k ^ 0x36 for k in key])

    inner = hashlib.sha256(i_key_pad + msg_bytes).digest()
    return hashlib.sha256(o_key_pad + inner).digest()


# --------------------- ATOM LITE LED MANAGEMENT --------------------- #
# On-board RGB LED on ATOM Lite -> GPIO 27


class StatusLED:
    def __init__(self, pin_num=27, brightness=64):
        import neopixel

        self.brightness = brightness  # 0-255
        self.np = neopixel.NeoPixel(Pin(pin_num, Pin.OUT), 1)
        self.off()

    def _scale(self, val):
        # Apply global brightness
        return min(255, int(val * self.brightness / 255))

    def set_rgb(self, r, g, b):
        self.np[0] = (self._scale(r), self._scale(g), self._scale(b))
        self.np.write()

    def off(self):
        self.set_rgb(0, 0, 0)

    # Solid colors
    def green(self):
        self.set_rgb(0, 255, 0)

    def red(self):
        self.set_rgb(255, 0, 0)

    def blue(self):
        self.set_rgb(0, 0, 255)

    def yellow(self):
        self.set_rgb(255, 255, 0)

    def orange(self):
        self.set_rgb(255, 128, 0)

    def purple(self):
        self.set_rgb(128, 0, 255)

    def cyan(self):
        self.set_rgb(0, 255, 255)

    # Blink methods
    def _blink(self, color_func, times, on_ms, off_ms):
        for _ in range(times):
            color_func()
            time.sleep_ms(on_ms)
            self.off()
            time.sleep_ms(off_ms)

    def blink_red(self, times=3, on_ms=200, off_ms=200):
        self._blink(self.red, times, on_ms, off_ms)

    def blink_green(self, times=1, on_ms=300, off_ms=100):
        self._blink(self.green, times, on_ms, off_ms)

    def blink_blue(self, times=2, on_ms=200, off_ms=200):
        self._blink(self.blue, times, on_ms, off_ms)

    def blink_yellow(self, times=2, on_ms=300, off_ms=200):
        self._blink(self.yellow, times, on_ms, off_ms)

    def blink_orange(self, times=3, on_ms=300, off_ms=200):
        self._blink(self.orange, times, on_ms, off_ms)

    def blink_purple(self, times=2, on_ms=200, off_ms=200):
        self._blink(self.purple, times, on_ms, off_ms)

    def blink_fast_red(self, times=6, on_ms=100, off_ms=100):
        """Fast red blink for auth errors (401)"""
        self._blink(self.red, times, on_ms, off_ms)


# --------------------- SWITCHBOT CONTROLLER --------------------- #


class SwitchBotController:
    """Class that manages the SwitchBot Lock Pro"""

    API_BASE_URL = "https://api.switch-bot.com/v1.1"

    def __init__(self, token, secret, device_id):
        self.token = token
        self.secret = secret
        self.device_id = device_id

    def _generate_nonce(self):
        """Generate a random nonce (hex string)."""
        rb = random_bytes(16)
        return ubinascii.hexlify(rb).decode()

    def _build_auth_headers(self):
        """
        Build authentication headers for API v1.1:
        - Authorization: token
        - sign: HMAC-SHA256(token + t + nonce, secret) base64 upper-case
        - nonce: random string
        - t: timestamp in milliseconds (string)
        """
        # SwitchBot expects UNIX epoch (1970). After NTP sync, time.time() is correct.
        t_ms = unix_time_ms()
        nonce = self._generate_nonce()

        data_str = "{}{}{}".format(self.token, t_ms, nonce)
        digest = hmac_sha256_digest(
            self.secret.encode("utf-8"), data_str.encode("utf-8")
        )

        # SwitchBot API v1.1 requires the Base64-encoded HMAC signature in uppercase
        sign_b64 = ubinascii.b2a_base64(digest).strip().decode().upper()

        headers = {
            "Authorization": self.token,
            "sign": sign_b64,
            "nonce": nonce,
            "t": str(t_ms),
            "Content-Type": "application/json; charset=utf8",
        }
        return headers

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
        url = f"{self.API_BASE_URL}/devices/{self.device_id}/commands"

        if not ensure_time_synced():
            return "time_error"

        # Command to lock or unlock the door
        payload = {
            "command": command,
            "parameter": "default",
            "commandType": "command",
        }
        data = json.dumps(payload)

        for attempt in range(retries + 1):
            if attempt > 0:
                print(f"Retry {attempt}/{retries}...")
                time.sleep_ms(500)  # Brief delay before retry

            # Regenerate headers for each attempt (fresh timestamp/nonce)
            headers = self._build_auth_headers()

            try:
                print(f"Sending {command.upper()} command...")
                response = urequests.post(url, headers=headers, data=data)

                if response is None:
                    print("✗ No response from the API.")
                    gc.collect()
                    continue  # Retry

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
                        pass  # Socket may already be closed

                gc.collect()
                print("HTTP status:", status)
                print("Response:", text)

                if status == 200:
                    return "success"

                if status == 401:
                    print("✗ Authentication failed (401). Check token/secret.")
                    return "auth_error"

            except Exception as e:
                print(f"✗ Exception while sending the command: {e}")
                gc.collect()
                continue  # Retry

        return "api_error"



# --------------------- WIFI SETUP --------------------- #


def connect_wifi(ssid, password, timeout=10, cached_bssid=None, cached_channel=None):
    """
    Connect the device to the Wi-Fi network with fast reconnect support.

    Uses cached BSSID from RTC memory for faster reconnection
    after deep sleep (~1-2s faster).

    Args:
        ssid: Wi-Fi network name
        password: Wi-Fi password
        timeout: Connection timeout in seconds
        cached_bssid: Pre-loaded BSSID bytes (avoids double RTC read)
        cached_channel: Pre-loaded channel number

    Returns:
        True if connection succeeds, False otherwise
    """
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if wlan.isconnected():
        print("Already connected to Wi-Fi")
        print(f"IP: {wlan.ifconfig()[0]}")
        return True

    # Use static IP if configured (skips DHCP, saves ~500ms-1s)
    try:
        from config import WIFI_STATIC_IP
        wlan.ifconfig(WIFI_STATIC_IP)
        print(f"Static IP: {WIFI_STATIC_IP[0]}")
    except (ImportError, AttributeError):
        pass  # WIFI_STATIC_IP not configured; use DHCP
    except (ValueError, OSError) as e:
        print(f"  Static IP rejected, using DHCP: {e}")  # Malformed tuple or driver error

    # Try fast reconnect using cached BSSID (use pre-loaded or read from RTC)
    if cached_bssid is None:
        cached_bssid, cached_channel = load_wifi_config()
    if cached_bssid:
        print(f"Fast reconnect (ch={cached_channel})...", end="")
        try:
            wlan.connect(ssid, password, bssid=cached_bssid)
        except TypeError:
            wlan.connect(ssid, password)

        # Short timeout for fast reconnect
        start = time.ticks_ms()
        while not wlan.isconnected():
            if time.ticks_diff(time.ticks_ms(), start) > 4000:  # 4s fast timeout
                print(" timeout")
                wlan.disconnect()
                clear_wifi_config()  # Clear invalid cache
                break
            time.sleep_ms(50)

        if wlan.isconnected():
            print(" OK!")
            print(f"  IP: {wlan.ifconfig()[0]}")
            return True

        print("Fast reconnect failed, trying normal scan...")

    # Normal connection with full scan
    print(f"Connecting to Wi-Fi: {ssid}...")
    wlan.connect(ssid, password)

    start = time.ticks_ms()
    while not wlan.isconnected():
        if time.ticks_diff(time.ticks_ms(), start) > timeout * 1000:
            print("\n✗ Wi-Fi connection timeout!")
            try:
                wlan.disconnect()
                wlan.active(False)
            except Exception:
                pass  # Best-effort WiFi cleanup on timeout; ignore errors
            return False
        time.sleep_ms(50)
        print(".", end="")

    print("\n✓ Connected to Wi-Fi!")
    print(f"  IP: {wlan.ifconfig()[0]}")

    # Cache connected AP's BSSID for fast reconnect.
    # Try wlan.config('bssid') first (instant), fall back to scan (~1-2s).
    try:
        bssid = wlan.config('bssid')
        if isinstance(bssid, bytes) and len(bssid) == 6 and bssid != b'\x00\x00\x00\x00\x00\x00':
            channel = wlan.config('channel') if hasattr(wlan, 'config') else 0
            save_wifi_config(bssid, channel)
            print(f"  Cached ch={channel} for fast reconnect")
        else:
            raise ValueError("no bssid from config")
    except Exception:
        # Fallback: scan for best-RSSI AP.
        # NOTE: scan forces WiFi driver buffer reallocation, which may help
        # defragment system heap for mbedTLS RSA operations.
        try:
            best_ap = None
            for ap in wlan.scan():
                if ap[0].decode() == ssid:
                    if not best_ap or ap[3] > best_ap[3]:
                        best_ap = ap
            if best_ap:
                save_wifi_config(bytes(best_ap[1]), best_ap[2])
                print(f"  Cached ch={best_ap[2]} for fast reconnect (scan)")
        except Exception as e:
            print(f"  Could not cache Wi-Fi config: {e}")

    return True


def enter_deep_sleep(button_gpio):
    """
    Configure wake-on-button and enter deep sleep.

    Args:
        button_gpio: GPIO pin number for wake button
    """
    print("\nEntering deep sleep...")
    print(f"  Wake trigger: GPIO{button_gpio} LOW (button press)")
    print("  Power consumption: ~10uA")
    print("=" * 50)

    # Configure wake on EXT0 (single pin, level-triggered)
    # GPIO 39 is RTC_GPIO3, supports deep sleep wake
    # Note: GPIO 39 is input-only, has external pull-up on ATOM Lite
    wake_pin = Pin(button_gpio, Pin.IN)
    esp32.wake_on_ext0(pin=wake_pin, level=esp32.WAKEUP_ALL_LOW)

    # Small delay to allow serial output to flush
    time.sleep_ms(100)

    # Enter deep sleep indefinitely (wake only on button)
    deepsleep()


def set_cpu_freq(mhz):
    """Set CPU frequency in MHz. Valid: 80, 160, 240."""
    try:
        freq(mhz * 1_000_000)
    except Exception:
        pass  # Frequency change unsupported or invalid; continue at current speed


# Duration threshold for long press (milliseconds)
LONG_PRESS_MS = 1000


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
    # GPIO 39 is input-only, has external pull-up on ATOM Lite
    button = Pin(button_gpio, Pin.IN)
    start = time.ticks_ms()
    led.green()  # Start with green (short press = unlock)
    is_long = False

    # Wait for button release, showing feedback
    while button.value() == 0:  # Button pressed = LOW
        elapsed = time.ticks_diff(time.ticks_ms(), start)

        # Switch LED to purple once on long press transition
        if not is_long and elapsed >= LONG_PRESS_MS:
            led.purple()  # Long press = lock
            is_long = True

        if elapsed > timeout_ms:
            break
        time.sleep_ms(50)

    duration = time.ticks_diff(time.ticks_ms(), start)
    led.off()
    return duration


def handle_button_wake(led):
    """
    Handle wake from deep sleep due to button press.
    Measures press duration to determine lock vs unlock:
    - Short press (<1s): UNLOCK
    - Long press (>=1s): LOCK

    LED Color Feedback:
    - Green (while holding): Short press detected (unlock)
    - Purple (while holding): Long press detected (lock)
    - Blue: Connecting to Wi-Fi (normal scan)
    - Cyan: Fast reconnect in progress
    - Green (2 blinks): Unlock success
    - Purple (2 blinks): Lock success
    - Yellow (2 blinks): NTP sync failed (continuing anyway)
    - Orange (3 blinks): Wi-Fi timeout
    - Red (3 blinks): API error
    - Red fast (6 blinks): Auth error (401)

    Args:
        led: StatusLED instance

    Returns:
        str: Result code from send_command or "wifi_error"
    """
    print("\n" + "=" * 50)
    print("WAKE FROM DEEP SLEEP - Button pressed!")
    print("=" * 50)

    # Measure button press duration (with visual feedback)
    press_duration = measure_button_press(BUTTON_GPIO, led)
    is_lock = press_duration >= LONG_PRESS_MS
    command = "lock" if is_lock else "unlock"

    print(f"Button held for {press_duration}ms")
    print(f"Action: {command.upper()}")

    # Boost CPU for Wi-Fi operations
    set_cpu_freq(160)

    # Check if fast reconnect is available
    cached_bssid, cached_channel = load_wifi_config()
    if cached_bssid:
        led.cyan()  # Cyan = fast reconnect
        print(f"Fast reconnect available (ch={cached_channel})")
    else:
        led.blue()  # Blue = normal Wi-Fi scan

    # Connect to Wi-Fi (pass cached values to avoid double RTC read)
    if not connect_wifi(WIFI_SSID, WIFI_PASSWORD, timeout=10,
                        cached_bssid=cached_bssid,
                        cached_channel=cached_channel):
        print("✗ Cannot connect to Wi-Fi")
        led.off()
        led.blink_orange(times=3, on_ms=300, off_ms=200)
        set_cpu_freq(80)
        return "wifi_error"

    # Wi-Fi connected - show action color
    if is_lock:
        led.purple()
    else:
        led.green()

    # Only sync NTP if time is invalid (RTC survives deep sleep)
    ntp_ok = True
    if is_time_valid():
        print("✓ RTC time valid, skipping NTP sync")
    else:
        print("RTC time invalid, syncing NTP...")
        try:
            sync_time_via_ntp()
            if not is_time_valid():
                ntp_ok = False
        except Exception:
            ntp_ok = False

        if not ntp_ok:
            print("⚠ NTP sync failed, attempting anyway...")
            led.off()
            led.blink_yellow(times=2, on_ms=300, off_ms=200)
            if is_lock:
                led.purple()
            else:
                led.green()

    # Initialize controller and send command (with 1 retry)
    controller = SwitchBotController(
        SWITCHBOT_TOKEN, SWITCHBOT_SECRET, SWITCHBOT_DEVICE_ID
    )

    result = controller.send_command(command=command, retries=1)

    # Disconnect Wi-Fi early to save power during LED feedback (~100-120mA)
    try:
        wlan = network.WLAN(network.STA_IF)
        wlan.disconnect()
        wlan.active(False)
    except Exception:
        pass  # Best-effort WiFi shutdown; device enters deep sleep next

    # LED feedback based on result (Wi-Fi already off, saving power)
    led.off()
    if result == "success":
        if is_lock:
            print("✓ Door locked successfully!")
            led.blink_purple(times=2, on_ms=300, off_ms=100)
        else:
            print("✓ Door unlocked successfully!")
            led.blink_green(times=2, on_ms=300, off_ms=100)
    elif result == "auth_error":
        print("✗ Authentication error (401)")
        led.blink_fast_red(times=6, on_ms=100, off_ms=100)
    elif result == "time_error":
        print("✗ Time sync error")
        led.blink_yellow(times=4, on_ms=200, off_ms=200)
    else:  # api_error or other
        print("✗ API error")
        led.blink_red(times=3, on_ms=200, off_ms=200)

    led.off()

    # Deep sleep resets CPU and RAM, no need for set_cpu_freq(80) or gc.collect()
    return result


# --------------------- MAIN --------------------- #


def main():
    """
    Main entry point - Deep Sleep Version

    Flow:
    1. Check if waking from deep sleep (button press)
    2. If yes: measure press duration, lock or unlock, return to sleep
    3. If no (fresh boot): show startup message, go to sleep
    """
    # Initialize status LED first for immediate feedback
    led = StatusLED(pin_num=27, brightness=64)

    # Check wake reason
    if reset_cause() == DEEPSLEEP_RESET:
        # Woke up from deep sleep = button was pressed
        handle_button_wake(led)
    else:
        # Fresh boot (power on or reset)
        print("\n" + "=" * 50)
        print("M5Stack ATOM Lite - SwitchBot Lock Pro Controller")
        print("          (Deep Sleep Version)")
        print("=" * 50)
        print(f"\nDevice ID: {SWITCHBOT_DEVICE_ID}")
        print(f"Wake button: GPIO{BUTTON_GPIO}")
        print(f"Long press threshold: {LONG_PRESS_MS}ms")
        print("\nControls:")
        print("  Short press (<1s) = UNLOCK (green LED)")
        print("  Long press  (>1s) = LOCK   (purple LED)")

        # Brief LED flash to indicate ready (green then purple)
        led.blink_green(times=1, on_ms=300, off_ms=100)
        led.blink_purple(times=1, on_ms=300, off_ms=100)

    # Always return to deep sleep
    led.off()
    enter_deep_sleep(BUTTON_GPIO)


# Start the main program
if __name__ == "__main__":
    main()
