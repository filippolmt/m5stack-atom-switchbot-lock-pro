"""
Inject MicroPython hardware stubs into sys.modules so that
``import main`` works on CPython without modifying the firmware source.

This file is loaded by pytest before any test module.
"""

import sys
import types
import time as _time

# ---------------------------------------------------------------------------
# ubinascii -> binascii  (CPython equivalent)
# ---------------------------------------------------------------------------
import binascii

sys.modules["ubinascii"] = binascii

# ---------------------------------------------------------------------------
# ujson -> json  (main.py has its own try/except, but inject early to be safe)
# ---------------------------------------------------------------------------
import json

sys.modules["ujson"] = json

# ---------------------------------------------------------------------------
# machine module stub
# ---------------------------------------------------------------------------
machine = types.ModuleType("machine")


class FakePin:
    IN = 0
    OUT = 1
    PULL_UP = 2

    def __init__(self, pin_num, mode=None, pull=None):
        self.pin_num = pin_num
        self._value = 1  # HIGH = not pressed

    def value(self):
        return self._value


machine.Pin = FakePin
machine.deepsleep = lambda ms=None: None
machine.reset_cause = lambda: 0
machine.DEEPSLEEP_RESET = 2
machine.freq = lambda f=None: f if f else 160_000_000


class FakeRTC:
    _memory_data = bytearray(8)

    def memory(self, data=None):
        if data is not None:
            FakeRTC._memory_data = bytearray(data)
        else:
            return bytes(FakeRTC._memory_data)


machine.RTC = FakeRTC


class FakeWDT:
    def __init__(self, timeout=5000):
        pass

    def feed(self):
        pass


machine.WDT = FakeWDT
sys.modules["machine"] = machine

# ---------------------------------------------------------------------------
# esp32 module stub
# ---------------------------------------------------------------------------
esp32 = types.ModuleType("esp32")
esp32.WAKEUP_ALL_LOW = 0
esp32.wake_on_ext0 = lambda pin=None, level=None: None
sys.modules["esp32"] = esp32

# ---------------------------------------------------------------------------
# network module stub
# ---------------------------------------------------------------------------
network_mod = types.ModuleType("network")
network_mod.STA_IF = 0


class FakeWLAN:
    def __init__(self, interface=0):
        self._active = False
        self._connected = False

    def active(self, val=None):
        if val is not None:
            self._active = val
        return self._active

    def isconnected(self):
        return self._connected

    def connect(self, ssid=None, password=None, bssid=None):
        self._connected = True

    def disconnect(self):
        self._connected = False

    def ifconfig(self):
        return ("192.168.1.100", "255.255.255.0", "192.168.1.1", "8.8.8.8")

    def config(self, **kwargs):
        pass

    def scan(self):
        return []


network_mod.WLAN = FakeWLAN
sys.modules["network"] = network_mod

# ---------------------------------------------------------------------------
# urequests module stub
# ---------------------------------------------------------------------------
urequests_mod = types.ModuleType("urequests")


class FakeResponse:
    def __init__(self, status_code=200, text='{"statusCode":100}'):
        self.status_code = status_code
        self.text = text
        self._closed = False

    def close(self):
        self._closed = True


urequests_mod.post = lambda url, headers=None, data=None: FakeResponse()
sys.modules["urequests"] = urequests_mod

# ---------------------------------------------------------------------------
# neopixel module stub
# ---------------------------------------------------------------------------
neopixel_mod = types.ModuleType("neopixel")


class FakeNeoPixel:
    def __init__(self, pin, count):
        self._pixels = [(0, 0, 0)] * count

    def __setitem__(self, idx, val):
        self._pixels[idx] = val

    def __getitem__(self, idx):
        return self._pixels[idx]

    def write(self):
        pass


neopixel_mod.NeoPixel = FakeNeoPixel
sys.modules["neopixel"] = neopixel_mod

# ---------------------------------------------------------------------------
# ntptime module stub
# ---------------------------------------------------------------------------
ntptime_mod = types.ModuleType("ntptime")
ntptime_mod.settime = lambda: None
sys.modules["ntptime"] = ntptime_mod

# ---------------------------------------------------------------------------
# Monkey-patch time module with MicroPython-specific functions
# ---------------------------------------------------------------------------
if not hasattr(_time, "ticks_ms"):
    _time.ticks_ms = lambda: int(_time.time() * 1000) & 0x3FFFFFFF

if not hasattr(_time, "ticks_diff"):
    _time.ticks_diff = lambda a, b: a - b

if not hasattr(_time, "sleep_ms"):
    _time.sleep_ms = lambda ms: None  # no-op in tests

# ---------------------------------------------------------------------------
# Fake config module
# ---------------------------------------------------------------------------
config = types.ModuleType("config")
config.WIFI_SSID = "TestSSID"
config.WIFI_PASSWORD = "TestPassword"
config.SWITCHBOT_TOKEN = "test_token_abc123"
config.SWITCHBOT_SECRET = "test_secret_xyz789"
config.SWITCHBOT_DEVICE_ID = "DEVICE001"
config.BUTTON_GPIO = 39
sys.modules["config"] = config

# ---------------------------------------------------------------------------
# Import main to trigger module-level code (constants, class defs, etc.)
# ---------------------------------------------------------------------------
import main  # noqa: E402, F401

# ---------------------------------------------------------------------------
# pytest fixtures
# ---------------------------------------------------------------------------
import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_rtc():
    """Reset RTC memory between tests."""
    FakeRTC._memory_data = bytearray(8)
    yield
    FakeRTC._memory_data = bytearray(8)
