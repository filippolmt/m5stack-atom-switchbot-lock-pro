"""
M5Stack ATOM Lite - SwitchBot Lock Pro Controller
- Wi-Fi connection
- SwitchBot API v1.1 authentication (token + secret + HMAC-SHA256)
- Physical button (built-in or external) for UNLOCK
- LED feedback:
    - Solid green while sending the command
    - If HTTP 200: green for 1s, then OFF
    - If HTTP != 200: 3 red blinks, then OFF
"""

import network
import urequests
import time
from machine import Pin
import gc
import ubinascii
import hashlib

# Try to use hmac if available, otherwise fall back to the manual version
try:
    import hmac

    HAVE_HMAC = True
except ImportError:
    HAVE_HMAC = False

# Random bytes for nonce (compatible with different MicroPython builds)
try:
    import urandom as _urandom_mod

    def random_bytes(n):
        # Use urandom() if it exists.
        if hasattr(_urandom_mod, "urandom"):
            return _urandom_mod.urandom(n)
        # Otherwise use getrandbits() to generate n bytes.
        if hasattr(_urandom_mod, "getrandbits"):
            return bytes([_urandom_mod.getrandbits(8) for _ in range(n)])
        # LCG fallback based on time.ticks_ms()
        import time as _time_mod

        b = bytearray(n)
        seed = _time_mod.ticks_ms() & 0xFFFFFFFF
        for i in range(n):
            seed = (1103515245 * seed + 12345) & 0xFFFFFFFF
            b[i] = seed & 0xFF
        return bytes(b)

except ImportError:
    # If urandom is missing, try os.urandom when available
    import os as _os_mod
    import time as _time_mod

    def random_bytes(n):
        if hasattr(_os_mod, "urandom"):
            return _os_mod.urandom(n)
        # Final fallback: LCG
        b = bytearray(n)
        seed = _time_mod.ticks_ms() & 0xFFFFFFFF
        for i in range(n):
            seed = (1103515245 * seed + 12345) & 0xFFFFFFFF
            b[i] = seed & 0xFF
        return bytes(b)


try:
    import ujson as json
except ImportError:
    import json

try:
    from config import (
        WIFI_SSID,
        WIFI_PASSWORD,
        SWITCHBOT_TOKEN,
        SWITCHBOT_SECRET,
        SWITCHBOT_DEVICE_ID,
        BUTTON_GPIO,
        DEBOUNCE_MS,
    )
except ImportError:
    print("ERROR: File config.py not found!")
    print("Copy config_template.py to config.py and fill in your data.")
    raise


UNIX_EPOCH_OFFSET = 946684800  # Seconds between 1970-01-01 and MicroPython epoch (2000-01-01)


def sync_time_via_ntp():
    """Sync the system clock via NTP (needed for the correct timestamp)."""
    try:
        import ntptime

        print("Synchronizing time via NTP...")
        ntptime.settime()  # Set UTC time
        print("✓ Time synchronized via NTP (UTC).")
    except Exception as e:
        print("✗ Unable to synchronize time via NTP:", e)
        print(
            "  WARNING: if the clock is wrong, the SwitchBot API can reply with 401."
        )


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

    def green(self):
        # Moderate green
        self.set_rgb(0, 255, 0)

    def red(self):
        self.set_rgb(255, 0, 0)

    def blink_red(self, times=3, on_ms=200, off_ms=200):
        for _ in range(times):
            self.red()
            time.sleep_ms(on_ms)
            self.off()
            time.sleep_ms(off_ms)

    def blink_green(self, times=1, on_ms=300, off_ms=100):
        for _ in range(times):
            self.green()
            time.sleep_ms(on_ms)
            self.off()
            time.sleep_ms(off_ms)


# --------------------- SWITCHBOT CONTROLLER --------------------- #


class SwitchBotController:
    """Class that manages the SwitchBot Lock Pro"""

    API_BASE_URL = "https://api.switch-bot.com/v1.1"

    def __init__(self, token, secret, device_id):
        self.token = token
        self.secret = secret
        self.device_id = device_id
        self.last_button_time = 0
        self.debounce_ms = DEBOUNCE_MS
        self.button_event = False  # flag set by the IRQ
        self.busy = False  # true while an HTTP request is running

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
        t_ms = int(time.time() * 1000)
        nonce = self._generate_nonce()

        data_str = "{}{}{}".format(self.token, t_ms, nonce)
        digest = hmac_sha256_digest(
            self.secret.encode("utf-8"), data_str.encode("utf-8")
        )

        # Base64 signature (keep original case; changing case breaks the signature)
        sign_b64 = ubinascii.b2a_base64(digest).strip().decode()

        headers = {
            "Authorization": self.token,
            "sign": sign_b64,
            "nonce": nonce,
            "t": str(t_ms),
            "Content-Type": "application/json; charset=utf8",
        }
        return headers

    def toggle_lock(self):
        """Send UNLOCK command to the SwitchBot Lock Pro. Returns True/False."""
        url = f"{self.API_BASE_URL}/devices/{self.device_id}/commands"

        headers = self._build_auth_headers()

        # Command to open the door (unlock)
        payload = {
            "command": "unlock",
            "parameter": "default",
            "commandType": "command",
        }
        data = json.dumps(payload)

        try:
            print("Sending UNLOCK command to SwitchBot Lock Pro...")
            response = urequests.post(url, headers=headers, data=data)

            if response is None:
                print("✗ No response from the API.")
                return False

            try:
                status = response.status_code
                text = response.text
            except Exception:
                status = -1
                text = "<no text>"

            print("HTTP status:", status)
            print("Response body:", text)

            result = status == 200

            response.close()
            gc.collect()
            return result

        except Exception as e:
            print(f"✗ Exception while sending the command: {e}")
            gc.collect()
            return False

    # ---- BUTTON HANDLING ---- #

    def button_handler(self, pin):
        """
        IRQ handler: does NOT make HTTP calls.
        It only sets a flag if:
        - debounce time has passed
        - the button is actually LOW
        - there isn't already a request in progress (busy)
        """
        current_time = time.ticks_ms()

        if time.ticks_diff(current_time, self.last_button_time) > self.debounce_ms:
            if pin.value() == 0 and not self.busy:
                self.last_button_time = current_time
                self.button_event = True

    def process_button_event(self, led):
        """
        Call from the main loop.
        If button_event is True, runs UNLOCK once
        with LED feedback.
        """
        if not self.button_event or self.busy:
            return

        # Consume the event
        self.button_event = False
        self.busy = True

        print("\n>>> Button pressed! Starting UNLOCK sequence...")

        # Solid green LED: sending the command
        led.green()

        # API call
        success = self.toggle_lock()

        if success:
            print("✓ API returned 200, unlocking door.")
            # Keep green on for 1 second
            time.sleep(1)
            led.off()
        else:
            print("✗ API did not return 200, error.")
            # 3 red blinks
            led.off()
            led.blink_red(times=3, on_ms=200, off_ms=200)
            led.off()

        self.busy = False


# --------------------- WIFI & BUTTON SETUP --------------------- #


def connect_wifi(ssid, password, timeout=20):
    """
    Connect the device to the Wi-Fi network

    Args:
        ssid: Wi-Fi network name
        password: Wi-Fi password
        timeout: Connection timeout in seconds

    Returns:
        True if connection succeeds, False otherwise
    """
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if wlan.isconnected():
        print("Already connected to Wi-Fi")
        print(f"IP: {wlan.ifconfig()[0]}")
        return True

    print(f"Connecting to Wi-Fi: {ssid}...")
    wlan.connect(ssid, password)

    start_time = time.time()
    while not wlan.isconnected():
        if time.time() - start_time > timeout:
            print("✗ Wi-Fi connection timeout!")
            return False
        time.sleep(0.5)
        print(".", end="")

    print("\n✓ Connected to Wi-Fi!")
    print("Network configuration:")
    print(f"  IP:      {wlan.ifconfig()[0]}")
    print(f"  Netmask: {wlan.ifconfig()[1]}")
    print(f"  Gateway: {wlan.ifconfig()[2]}")
    print(f"  DNS:     {wlan.ifconfig()[3]}")

    return True


def setup_button(gpio_num, controller):
    """
    Configure the GPIO button with interrupt and debounce

    Args:
        gpio_num: GPIO pin number
        controller: SwitchBotController instance

    Returns:
        Configured Pin object
    """
    # Button on ATOM Lite: active LOW with internal pull-up
    button = Pin(gpio_num, Pin.IN, Pin.PULL_UP)

    # Falling-edge interrupt
    button.irq(trigger=Pin.IRQ_FALLING, handler=controller.button_handler)

    print(f"✓ Button configured on GPIO{gpio_num}")
    print(f"  Debounce: {controller.debounce_ms}ms")
    print("  Trigger: IRQ_FALLING (press)")

    return button


# --------------------- MAIN --------------------- #


def main():
    """Main entry point"""
    print("\n" + "=" * 50)
    print("M5Stack ATOM Lite - SwitchBot Lock Pro Controller")
    print("=" * 50)

    # Initialize status LED
    led = StatusLED(pin_num=27, brightness=64)
    led.off()

    # Connect to Wi-Fi
    if not connect_wifi(WIFI_SSID, WIFI_PASSWORD):
        print("Cannot continue without Wi-Fi connection")
        # Solid red LED indicates a critical error
        led.red()
        return

    # Sync time to have the correct timestamp
    sync_time_via_ntp()
    print()

    # Initialize the SwitchBot controller
    controller = SwitchBotController(
        SWITCHBOT_TOKEN, SWITCHBOT_SECRET, SWITCHBOT_DEVICE_ID
    )
    print("✓ SwitchBot controller initialized")
    print(f"  Device ID: {SWITCHBOT_DEVICE_ID}")

    # Configure the button
    _button = setup_button(BUTTON_GPIO, controller)

    print("\n" + "=" * 50)
    print("System ready!")
    print("Press the button ONCE to unlock the door.")
    print("Green LED: command sending / success.")
    print("3 red blinks: API error.")
    print("=" * 50 + "\n")

    # Main loop - keep the program running
    try:
        while True:
            # Handle any button press
            controller.process_button_event(led)
            time.sleep_ms(50)  # lightweight loop
    except KeyboardInterrupt:
        print("\n\nKeyboard interrupt. Shutting down...")
    finally:
        print("Cleaning up resources...")
        led.off()
        gc.collect()


# Start the main program
if __name__ == "__main__":
    main()
