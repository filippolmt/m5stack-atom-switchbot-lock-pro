"""Tests for power micro-optimizations.

Validates:
- Serial flush delay reduced to 20ms
- NeoPixel GPIO 27 held LOW during deep sleep
- gpio_hold_en called for pin hold
- API retry delay reduced to 300ms
- CPU frequency reset to 80MHz after WiFi disconnect
"""

from unittest.mock import MagicMock, patch, call

import main


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

class FakeResponse:
    """Minimal HTTP response stub."""

    def __init__(self, status_code=200, text='{"statusCode":100}'):
        self.status_code = status_code
        self.text = text
        self._closed = False

    def close(self):
        self._closed = True


def _make_controller():
    return main.SwitchBotController(
        token="tok", secret="sec", device_id="dev"
    )


# ---------------------------------------------------------------------------
# Test 1: enter_deep_sleep flush delay is 20ms
# ---------------------------------------------------------------------------

def test_flush_delay_is_20ms():
    """enter_deep_sleep should call time.sleep_ms(20) not 100."""
    sleep_calls = []
    original_sleep_ms = main.time.sleep_ms

    def track_sleep(ms):
        sleep_calls.append(ms)

    with patch.object(main.time, "sleep_ms", side_effect=track_sleep), \
         patch.object(main, "deepsleep"):
        main.enter_deep_sleep(39)

    # The last sleep_ms before deepsleep should be 20
    assert 20 in sleep_calls, f"Expected 20ms flush delay, got calls: {sleep_calls}"
    assert 100 not in sleep_calls, f"Old 100ms delay still present: {sleep_calls}"


# ---------------------------------------------------------------------------
# Test 2: NeoPixel GPIO 27 set as OUTPUT and driven LOW
# ---------------------------------------------------------------------------

def test_neopixel_gpio_held_low():
    """enter_deep_sleep should set Pin(27, OUT) and drive it LOW."""
    pin_creations = []
    pin_values = []

    class TrackingPin:
        IN = 0
        OUT = 1

        def __init__(self, num, mode=None, pull=None):
            pin_creations.append((num, mode))
            self._num = num

        def value(self, v=None):
            if v is not None:
                pin_values.append((self._num, v))
            return 1

    with patch.object(main, "Pin", TrackingPin), \
         patch.object(main, "deepsleep"), \
         patch.object(main.time, "sleep_ms"):
        main.enter_deep_sleep(39)

    # Should have Pin(27, OUT) creation
    assert (27, TrackingPin.OUT) in pin_creations, \
        f"Pin(27, OUT) not found in: {pin_creations}"
    # Should drive pin 27 LOW
    assert (27, 0) in pin_values, \
        f"Pin 27 value(0) not found in: {pin_values}"


# ---------------------------------------------------------------------------
# Test 3: gpio_hold_en called for pin hold
# ---------------------------------------------------------------------------

def test_gpio_hold_en_called():
    """enter_deep_sleep should call esp32.gpio_hold_en(27)."""
    hold_calls = []

    def track_hold(pin):
        hold_calls.append(pin)

    with patch.object(main.esp32, "gpio_hold_en", side_effect=track_hold), \
         patch.object(main, "deepsleep"), \
         patch.object(main.time, "sleep_ms"):
        main.enter_deep_sleep(39)

    assert 27 in hold_calls, f"gpio_hold_en(27) not called, got: {hold_calls}"


# ---------------------------------------------------------------------------
# Test 4: API retry delay is 300ms
# ---------------------------------------------------------------------------

def test_retry_delay_is_300ms():
    """send_command retry should use 300ms delay, not 500ms."""
    sleep_calls = []
    original_sleep_ms = main.time.sleep_ms

    def track_sleep(ms):
        sleep_calls.append(ms)

    ctrl = _make_controller()
    # First call returns 500 (failure), second returns 200 (success)
    responses = [FakeResponse(500), FakeResponse(200)]
    post_mock = MagicMock(side_effect=responses)

    with patch("main.ensure_time_synced", return_value=True), \
         patch.object(main.urequests, "post", post_mock), \
         patch.object(main.time, "sleep_ms", side_effect=track_sleep):
        result = ctrl.send_command("unlock", retries=1)

    assert result == "success"
    assert 300 in sleep_calls, f"Expected 300ms retry delay, got: {sleep_calls}"
    assert 500 not in sleep_calls, f"Old 500ms delay still present: {sleep_calls}"


# ---------------------------------------------------------------------------
# Test 5: CPU freq reset to 80MHz after WiFi disconnect
# ---------------------------------------------------------------------------

def test_cpu_freq_reset_after_wifi():
    """handle_button_wake should call set_cpu_freq(80) after WiFi disconnect."""
    freq_calls = []

    original_freq = main.freq

    def track_freq(f=None):
        if f is not None:
            freq_calls.append(f)
        return 160_000_000

    # Patch main.freq directly (it's imported via 'from machine import freq')
    main.freq = track_freq

    # Set up FakeWLAN that auto-connects
    import network
    original_wlan = network.WLAN

    class AutoConnectWLAN:
        def __init__(self, iface=0):
            self._active = False
            self._connected = False

        def active(self, val=None):
            if val is not None:
                self._active = val
            return self._active

        def isconnected(self):
            return self._connected

        def connect(self, *args, **kwargs):
            self._connected = True

        def disconnect(self):
            self._connected = False

        def ifconfig(self, config=None):
            return ("192.168.1.100", "255.255.255.0", "192.168.1.1", "8.8.8.8")

        def config(self, key=None, **kwargs):
            if key == 'bssid':
                return b'\x01\x02\x03\x04\x05\x06'
            if key == 'channel':
                return 6
            return None

        def scan(self):
            return []

    network.WLAN = AutoConnectWLAN

    try:
        led = main.StatusLED(pin_num=27, brightness=32)

        with patch("main.ensure_time_synced", return_value=True), \
             patch.object(main.urequests, "post", return_value=FakeResponse(200)), \
             patch.object(main, "measure_button_press", return_value=500), \
             patch.object(main.time, "sleep_ms"):
            result = main.handle_button_wake(led)

        assert result == "success"
        # Should see 160MHz (boost) then 80MHz (after WiFi disconnect)
        assert 80_000_000 in freq_calls, \
            f"set_cpu_freq(80) not called after WiFi disconnect. freq calls: {freq_calls}"

        # Verify 80MHz comes AFTER 160MHz
        idx_160 = None
        idx_80 = None
        for i, f in enumerate(freq_calls):
            if f == 160_000_000 and idx_160 is None:
                idx_160 = i
            if f == 80_000_000 and idx_80 is None:
                idx_80 = i
        assert idx_160 is not None, "160MHz not found"
        assert idx_80 is not None, "80MHz not found"
        assert idx_80 > idx_160, \
            f"80MHz (idx={idx_80}) should come after 160MHz (idx={idx_160})"
    finally:
        main.freq = original_freq
        network.WLAN = original_wlan
