"""Tests for RTC memory Wi-Fi config serialization.

Validates save/load roundtrip, boundary conditions, and invalid data handling.
"""

import sys

import main


def _get_fake_rtc_cls():
    """Return the FakeRTC class used by the machine stub."""
    return sys.modules["machine"].RTC


def test_roundtrip_save_load():
    """save -> load must return the same BSSID and channel."""
    bssid = b"\xAA\xBB\xCC\xDD\xEE\xFF"
    channel = 6
    main.save_wifi_config(bssid, channel)
    loaded_bssid, loaded_channel = main.load_wifi_config()
    assert loaded_bssid == bssid
    assert loaded_channel == channel


def test_empty_rtc_returns_none():
    """Uninitialized RTC memory -> (None, None)."""
    bssid, channel = main.load_wifi_config()
    assert bssid is None
    assert channel is None


def test_invalid_bssid_not_bytes():
    """Non-bytes BSSID should not be saved."""
    FakeRTC = _get_fake_rtc_cls()
    original = bytes(FakeRTC._memory_data)
    main.save_wifi_config("not-bytes", 6)
    # RTC memory must be unchanged
    assert bytes(FakeRTC._memory_data) == original


def test_invalid_bssid_wrong_length():
    """BSSID with wrong length (not 6 bytes) should not be saved."""
    FakeRTC = _get_fake_rtc_cls()
    original = bytes(FakeRTC._memory_data)
    main.save_wifi_config(b"\xAA\xBB\xCC", 6)  # only 3 bytes
    assert bytes(FakeRTC._memory_data) == original


def test_channel_zero_returns_bssid_with_none_channel():
    """Channel 0 is invalid; BSSID still returned, channel is None."""
    bssid = b"\x01\x02\x03\x04\x05\x06"
    main.save_wifi_config(bssid, 0)
    loaded_bssid, loaded_channel = main.load_wifi_config()
    assert loaded_bssid == bssid
    assert loaded_channel is None


def test_channel_above_14_returns_bssid_with_none_channel():
    """Channel > 14 is invalid; BSSID still returned, channel is None."""
    bssid = b"\x01\x02\x03\x04\x05\x06"
    main.save_wifi_config(bssid, 15)
    loaded_bssid, loaded_channel = main.load_wifi_config()
    assert loaded_bssid == bssid
    assert loaded_channel is None


def test_channel_14_valid():
    """Channel 14 is the maximum valid Wi-Fi channel."""
    bssid = b"\x01\x02\x03\x04\x05\x06"
    main.save_wifi_config(bssid, 14)
    loaded_bssid, loaded_channel = main.load_wifi_config()
    assert loaded_bssid == bssid
    assert loaded_channel == 14


def test_channel_1_valid():
    """Channel 1 is the minimum valid Wi-Fi channel."""
    bssid = b"\x01\x02\x03\x04\x05\x06"
    main.save_wifi_config(bssid, 1)
    loaded_bssid, loaded_channel = main.load_wifi_config()
    assert loaded_bssid == bssid
    assert loaded_channel == 1


def test_clear_wifi_config():
    """clear_wifi_config must invalidate the stored data."""
    bssid = b"\xAA\xBB\xCC\xDD\xEE\xFF"
    main.save_wifi_config(bssid, 11)
    main.clear_wifi_config()
    loaded_bssid, loaded_channel = main.load_wifi_config()
    assert loaded_bssid is None
    assert loaded_channel is None
