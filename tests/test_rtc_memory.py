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


# ---------------------------------------------------------------------------
# Extended 12-byte RTC memory layout tests (BATT-05)
# ---------------------------------------------------------------------------


def test_save_writes_12_bytes_with_v2_flag():
    """save_wifi_config now writes 12-byte layout with 0xBB flag."""
    bssid = b"\xAA\xBB\xCC\xDD\xEE\xFF"
    main.save_wifi_config(bssid, 6)
    FakeRTC = _get_fake_rtc_cls()
    data = FakeRTC._memory_data
    assert len(data) == 12
    assert data[7] == 0xBB  # New flag


def test_load_old_0xAA_layout():
    """Old 8-byte 0xAA layout must still be readable."""
    FakeRTC = _get_fake_rtc_cls()
    old_data = bytearray(8)
    old_data[0:6] = b"\x01\x02\x03\x04\x05\x06"
    old_data[6] = 11
    old_data[7] = 0xAA
    FakeRTC._memory_data = old_data
    bssid, channel = main.load_wifi_config()
    assert bssid == b"\x01\x02\x03\x04\x05\x06"
    assert channel == 11


def test_load_new_0xBB_layout():
    """New 12-byte 0xBB layout must be readable."""
    FakeRTC = _get_fake_rtc_cls()
    new_data = bytearray(12)
    new_data[0:6] = b"\x01\x02\x03\x04\x05\x06"
    new_data[6] = 6
    new_data[7] = 0xBB
    FakeRTC._memory_data = new_data
    bssid, channel = main.load_wifi_config()
    assert bssid == b"\x01\x02\x03\x04\x05\x06"
    assert channel == 6


def test_save_preserves_extended_fields():
    """save_wifi_config must preserve battery/counter bytes when overwriting."""
    FakeRTC = _get_fake_rtc_cls()
    # Pre-populate with existing v2 data including battery voltage and counter
    existing = bytearray(12)
    existing[7] = 0xBB
    existing[8] = 0x68  # 4200 & 0xFF = 0x68
    existing[9] = 0x10  # 4200 >> 8 = 0x10
    existing[10] = 42   # wake counter
    existing[11] = 0x00
    FakeRTC._memory_data = existing
    # Save new WiFi config
    main.save_wifi_config(b"\xAA\xBB\xCC\xDD\xEE\xFF", 6)
    data = FakeRTC._memory_data
    assert data[8] == 0x68  # Battery low byte preserved
    assert data[9] == 0x10  # Battery high byte preserved
    assert data[10] == 42   # Wake counter preserved


def test_save_battery_voltage_roundtrip():
    """save_battery_voltage + load_battery_voltage roundtrip."""
    # First create a valid v2 layout
    main.save_wifi_config(b"\x01\x02\x03\x04\x05\x06", 1)
    main.save_battery_voltage(4200)
    assert main.load_battery_voltage() == 4200


def test_save_battery_voltage_zero():
    """Battery voltage 0 is valid (means no reading yet)."""
    main.save_wifi_config(b"\x01\x02\x03\x04\x05\x06", 1)
    main.save_battery_voltage(0)
    assert main.load_battery_voltage() == 0


def test_save_battery_voltage_max_uint16():
    """Battery voltage at max uint16 (65535 mV)."""
    main.save_wifi_config(b"\x01\x02\x03\x04\x05\x06", 1)
    main.save_battery_voltage(65535)
    assert main.load_battery_voltage() == 65535


def test_load_battery_voltage_old_layout_returns_zero():
    """Battery voltage returns 0 when RTC has old 0xAA layout."""
    FakeRTC = _get_fake_rtc_cls()
    old_data = bytearray(8)
    old_data[7] = 0xAA
    FakeRTC._memory_data = old_data
    assert main.load_battery_voltage() == 0


def test_load_battery_voltage_empty_returns_zero():
    """Battery voltage returns 0 when RTC is uninitialized."""
    assert main.load_battery_voltage() == 0


def test_increment_wake_counter():
    """Wake counter increments from 0 to 1."""
    main.save_wifi_config(b"\x01\x02\x03\x04\x05\x06", 1)
    assert main.load_wake_counter() == 0
    main.increment_wake_counter()
    assert main.load_wake_counter() == 1


def test_increment_wake_counter_wraps():
    """Wake counter wraps from 255 to 0."""
    main.save_wifi_config(b"\x01\x02\x03\x04\x05\x06", 1)
    FakeRTC = _get_fake_rtc_cls()
    FakeRTC._memory_data[10] = 255
    main.increment_wake_counter()
    assert main.load_wake_counter() == 0


def test_load_wake_counter_old_layout_returns_zero():
    """Wake counter returns 0 when RTC has old 0xAA layout."""
    FakeRTC = _get_fake_rtc_cls()
    old_data = bytearray(8)
    old_data[7] = 0xAA
    FakeRTC._memory_data = old_data
    assert main.load_wake_counter() == 0


def test_clear_zeros_12_bytes():
    """clear_wifi_config must zero 12 bytes, not just 8."""
    main.save_wifi_config(b"\xAA\xBB\xCC\xDD\xEE\xFF", 6)
    main.save_battery_voltage(4200)
    main.increment_wake_counter()
    main.clear_wifi_config()
    FakeRTC = _get_fake_rtc_cls()
    assert FakeRTC._memory_data == bytearray(12)


def test_migration_old_to_new():
    """Loading old 0xAA, then saving, migrates to 0xBB."""
    FakeRTC = _get_fake_rtc_cls()
    old_data = bytearray(8)
    old_data[0:6] = b"\x01\x02\x03\x04\x05\x06"
    old_data[6] = 11
    old_data[7] = 0xAA
    FakeRTC._memory_data = old_data
    # Load (should work with old layout)
    bssid, channel = main.load_wifi_config()
    assert bssid == b"\x01\x02\x03\x04\x05\x06"
    # Save (should migrate to new layout)
    main.save_wifi_config(bssid, channel)
    data = FakeRTC._memory_data
    assert len(data) == 12
    assert data[7] == 0xBB
    assert bytes(data[0:6]) == b"\x01\x02\x03\x04\x05\x06"
    assert data[6] == 11
