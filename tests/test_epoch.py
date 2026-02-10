"""Tests for epoch conversion logic (highest priority).

Validates that unix_time_ms() returns correct Unix timestamps
on both CPython (epoch 1970) and MicroPython (epoch 2000).
"""

import time
from unittest.mock import patch

import main


def test_unix_epoch_offset_constant():
    """The offset between 1970 and 2000 must be exactly 946684800 seconds."""
    assert main._UNIX_EPOCH_OFFSET_SECONDS == 946684800


def test_is_mp_epoch_false_on_cpython():
    """On CPython, gmtime(0) year is 1970, so _IS_MP_EPOCH must be False."""
    assert main._IS_MP_EPOCH is False


def test_unix_time_ms_returns_13_digit_int():
    """unix_time_ms() must return a 13-digit integer (milliseconds)."""
    result = main.unix_time_ms()
    assert isinstance(result, int)
    assert len(str(result)) == 13


def test_unix_time_ms_in_reasonable_range():
    """Timestamp must be between 2024-01-01 and 2040-01-01."""
    min_ts = 1704067200000  # 2024-01-01 UTC
    max_ts = 2208988800000  # 2040-01-01 UTC
    result = main.unix_time_ms()
    assert min_ts <= result <= max_ts


def test_unix_time_ms_close_to_real_time():
    """unix_time_ms() should be within 2 seconds of time.time()."""
    expected = int(time.time() * 1000)
    result = main.unix_time_ms()
    assert abs(result - expected) < 2000


def test_unix_time_ms_with_mp_epoch():
    """When _IS_MP_EPOCH is True, the offset must be added."""
    # Simulate MicroPython epoch: time.time() returns integer seconds since 2000
    fake_mp_seconds = 100000  # ~1.15 days after 2000-01-01
    expected = (fake_mp_seconds + main._UNIX_EPOCH_OFFSET_SECONDS) * 1000

    with patch.object(main, "_IS_MP_EPOCH", True), \
         patch("time.time", return_value=fake_mp_seconds):
        result = main.unix_time_ms()

    assert result == expected


def test_unix_time_ms_without_mp_epoch():
    """When _IS_MP_EPOCH is False, no offset is added."""
    fake_unix_seconds = 1700000000  # ~2023-11-14
    expected = fake_unix_seconds * 1000

    with patch.object(main, "_IS_MP_EPOCH", False), \
         patch("time.time", return_value=fake_unix_seconds):
        result = main.unix_time_ms()

    assert result == expected
