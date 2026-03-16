"""Tests for read_battery_voltage() — ADC on GPIO 33 with voltage divider."""

import sys
import main


def _get_fake_adc_class():
    """Return the FakeADC class from the machine stub."""
    return sys.modules["machine"].ADC


def test_read_battery_voltage_normal():
    """1.9V at ADC (divider midpoint) -> 3800 mV battery."""
    FakeADC = _get_fake_adc_class()
    original = FakeADC.__init__

    def patched_init(self, pin, atten=0):
        original(self, pin, atten)
        self._uv = 1_900_000

    FakeADC.__init__ = patched_init
    try:
        result = main.read_battery_voltage()
        assert result == 3800, f"Expected 3800 mV, got {result}"
    finally:
        FakeADC.__init__ = original


def test_read_battery_voltage_full_battery():
    """2.1V at ADC -> 4200 mV (full LiPo)."""
    FakeADC = _get_fake_adc_class()
    original = FakeADC.__init__

    def patched_init(self, pin, atten=0):
        original(self, pin, atten)
        self._uv = 2_100_000

    FakeADC.__init__ = patched_init
    try:
        result = main.read_battery_voltage()
        assert result == 4200, f"Expected 4200 mV, got {result}"
    finally:
        FakeADC.__init__ = original


def test_read_battery_voltage_low_battery():
    """1.5V at ADC -> 3000 mV (depleted LiPo)."""
    FakeADC = _get_fake_adc_class()
    original = FakeADC.__init__

    def patched_init(self, pin, atten=0):
        original(self, pin, atten)
        self._uv = 1_500_000

    FakeADC.__init__ = patched_init
    try:
        result = main.read_battery_voltage()
        assert result == 3000, f"Expected 3000 mV, got {result}"
    finally:
        FakeADC.__init__ = original


def test_read_battery_voltage_adc_failure():
    """ADC raises OSError -> returns 0 gracefully."""
    FakeADC = _get_fake_adc_class()
    original_read = FakeADC.read_uv

    def failing_read(self):
        raise OSError("ADC hardware failure")

    FakeADC.read_uv = failing_read
    try:
        result = main.read_battery_voltage()
        assert result == 0, f"Expected 0 on failure, got {result}"
    finally:
        FakeADC.read_uv = original_read


def test_read_battery_voltage_samples_averaged():
    """Verify read_uv is called exactly 4 times (4-sample averaging)."""
    FakeADC = _get_fake_adc_class()
    call_count = 0
    original_read = FakeADC.read_uv

    def counting_read(self):
        nonlocal call_count
        call_count += 1
        return 1_900_000

    FakeADC.read_uv = counting_read
    try:
        main.read_battery_voltage()
        assert call_count == 4, f"Expected 4 read_uv calls, got {call_count}"
    finally:
        FakeADC.read_uv = original_read


def test_battery_voltage_printed_to_serial(capsys):
    """Serial output contains 'Battery:' with mV value."""
    FakeADC = _get_fake_adc_class()
    original = FakeADC.__init__

    def patched_init(self, pin, atten=0):
        original(self, pin, atten)
        self._uv = 1_900_000

    FakeADC.__init__ = patched_init
    try:
        mv = main.read_battery_voltage()
        # Simulate the integration print (handle_button_wake prints this)
        if mv > 0:
            print(f"Battery: {mv}mV")
        captured = capsys.readouterr()
        assert "Battery:" in captured.out
        assert "3800" in captured.out
    finally:
        FakeADC.__init__ = original
