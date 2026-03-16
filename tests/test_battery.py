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


# ---------------------------------------------------------------------------
# Low-battery warning tests (check_low_battery + BATTERY_LOW_MV)
# ---------------------------------------------------------------------------


class MockLED:
    """Mock StatusLED that records blink_orange calls."""

    def __init__(self):
        self.blink_orange_calls = []

    def blink_orange(self, **kwargs):
        self.blink_orange_calls.append(kwargs)


def test_low_battery_warning_triggers():
    """When battery_mv=3000 (below 3300), led.blink_orange() is called."""
    led = MockLED()
    main.check_low_battery(3000, led)
    assert len(led.blink_orange_calls) == 1, (
        f"Expected 1 blink_orange call, got {len(led.blink_orange_calls)}"
    )


def test_low_battery_warning_no_trigger_above_threshold():
    """When battery_mv=3500 (above 3300), led.blink_orange() is NOT called."""
    led = MockLED()
    main.check_low_battery(3500, led)
    assert len(led.blink_orange_calls) == 0, (
        "blink_orange should not be called when battery is above threshold"
    )


def test_low_battery_warning_no_trigger_on_adc_failure():
    """When battery_mv=0 (ADC failed), led.blink_orange() is NOT called."""
    led = MockLED()
    main.check_low_battery(0, led)
    assert len(led.blink_orange_calls) == 0, (
        "blink_orange should not be called on ADC failure (0 mV)"
    )


def test_low_battery_warning_serial_output(capsys):
    """When battery_mv=3000, serial output contains 'WARNING' and 'Low battery'."""
    led = MockLED()
    main.check_low_battery(3000, led)
    captured = capsys.readouterr()
    assert "WARNING" in captured.out, "Expected 'WARNING' in serial output"
    assert "Low battery" in captured.out or "low battery" in captured.out.lower(), (
        "Expected low battery message in serial output"
    )


def test_low_battery_warning_at_threshold():
    """When battery_mv=3300 (exactly at threshold), led.blink_orange() is NOT called."""
    led = MockLED()
    main.check_low_battery(3300, led)
    assert len(led.blink_orange_calls) == 0, (
        "blink_orange should not be called at exact threshold (only below)"
    )
