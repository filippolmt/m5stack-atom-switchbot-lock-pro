"""Tests for StatusLED._scale() brightness math and LED defaults."""

import inspect

import main


def test_scale_full_brightness():
    """brightness=255 -> _scale(255) = 255."""
    led = main.StatusLED(pin_num=27, brightness=255)
    assert led._scale(255) == 255


def test_scale_half_brightness():
    """brightness=128 -> _scale(255) ~ 128."""
    led = main.StatusLED(pin_num=27, brightness=128)
    result = led._scale(255)
    assert result == int(255 * 128 / 255)  # 128


def test_scale_default_brightness():
    """brightness=32 (new default) -> _scale(255) = 32."""
    led = main.StatusLED(pin_num=27, brightness=32)
    result = led._scale(255)
    assert result == 32


def test_scale_zero_input():
    """_scale(0) must always be 0."""
    led = main.StatusLED(pin_num=27, brightness=255)
    assert led._scale(0) == 0


def test_scale_clamps_at_255():
    """Result must never exceed 255."""
    led = main.StatusLED(pin_num=27, brightness=255)
    assert led._scale(300) == 255


def test_scale_zero_brightness():
    """brightness=0 -> everything is 0."""
    led = main.StatusLED(pin_num=27, brightness=0)
    assert led._scale(255) == 0
    assert led._scale(128) == 0


def test_default_brightness_is_32():
    """StatusLED default brightness should be 32 (halved from 64)."""
    led = main.StatusLED(pin_num=27)
    assert led.brightness == 32


def test_led_brightness_constant():
    """Module-level LED_BRIGHTNESS constant should be 32."""
    assert main.LED_BRIGHTNESS == 32


def test_blink_defaults_halved():
    """Blink method defaults should be halved from original values."""
    # blink_green: on_ms=150 (was 300), off_ms=50 (was 100)
    sig_green = inspect.signature(main.StatusLED.blink_green)
    assert sig_green.parameters["on_ms"].default == 150
    assert sig_green.parameters["off_ms"].default == 50

    # blink_red: on_ms=100 (was 200), off_ms=100 (was 200)
    sig_red = inspect.signature(main.StatusLED.blink_red)
    assert sig_red.parameters["on_ms"].default == 100
    assert sig_red.parameters["off_ms"].default == 100

    # blink_fast_red: on_ms=50 (was 100), off_ms=50 (was 100)
    sig_fast = inspect.signature(main.StatusLED.blink_fast_red)
    assert sig_fast.parameters["on_ms"].default == 50
    assert sig_fast.parameters["off_ms"].default == 50
