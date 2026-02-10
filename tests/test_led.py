"""Tests for StatusLED._scale() brightness math."""

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


def test_scale_quarter_brightness():
    """brightness=64 (default) -> _scale(255) ~ 64."""
    led = main.StatusLED(pin_num=27, brightness=64)
    result = led._scale(255)
    assert result == int(255 * 64 / 255)  # 64


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
