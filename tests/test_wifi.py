"""Tests for connect_wifi() behavior."""

from unittest.mock import MagicMock, patch

import main


def test_already_connected_returns_true():
    """If WLAN is already connected, return True without calling connect()."""
    fake_wlan = MagicMock()
    fake_wlan.isconnected.return_value = True
    fake_wlan.ifconfig.return_value = ("192.168.1.1", "", "", "")

    with patch("main.network.WLAN", return_value=fake_wlan):
        result = main.connect_wifi("SSID", "PASS")

    assert result is True
    fake_wlan.connect.assert_not_called()


def test_timeout_returns_false():
    """If connection never succeeds within timeout, return False."""
    fake_wlan = MagicMock()
    fake_wlan.isconnected.return_value = False

    # Make ticks_diff always exceed timeout to exit loop immediately
    with patch("main.network.WLAN", return_value=fake_wlan), \
         patch("main.load_wifi_config", return_value=(None, None)), \
         patch("time.ticks_diff", return_value=999_999):
        result = main.connect_wifi("SSID", "PASS", timeout=5)

    assert result is False


def test_successful_connection():
    """Normal connection flow completes successfully."""
    call_count = 0

    def isconnected_side_effect():
        nonlocal call_count
        call_count += 1
        # Connected after first check in the while loop
        return call_count > 1

    fake_wlan = MagicMock()
    fake_wlan.isconnected.side_effect = isconnected_side_effect
    fake_wlan.ifconfig.return_value = ("192.168.1.100", "", "", "")
    fake_wlan.scan.return_value = []

    with patch("main.network.WLAN", return_value=fake_wlan), \
         patch("main.load_wifi_config", return_value=(None, None)), \
         patch("time.ticks_diff", return_value=0):
        result = main.connect_wifi("SSID", "PASS")

    assert result is True


def test_fast_reconnect_succeeds():
    """Cached BSSID/channel -> fast reconnect path, bssid passed to connect()."""
    cached_bssid = b"\xAA\xBB\xCC\xDD\xEE\xFF"
    cached_channel = 6
    call_count = 0

    def isconnected_side_effect():
        nonlocal call_count
        call_count += 1
        # Not connected on initial check, connected after connect()
        return call_count > 2

    fake_wlan = MagicMock()
    fake_wlan.isconnected.side_effect = isconnected_side_effect
    fake_wlan.ifconfig.return_value = ("192.168.1.100", "", "", "")

    with patch("main.network.WLAN", return_value=fake_wlan), \
         patch("main.load_wifi_config", return_value=(cached_bssid, cached_channel)), \
         patch("time.ticks_diff", return_value=0):
        result = main.connect_wifi("SSID", "PASS")

    assert result is True
    # bssid must be passed to connect() for fast reconnect
    fake_wlan.connect.assert_called_once_with("SSID", "PASS", bssid=cached_bssid)


def test_fast_reconnect_timeout_falls_back_to_normal():
    """Fast reconnect times out -> clears cache, falls back to normal scan."""
    cached_bssid = b"\xAA\xBB\xCC\xDD\xEE\xFF"
    call_count = 0

    def isconnected_side_effect():
        nonlocal call_count
        call_count += 1
        # Never connected during fast reconnect, connected during normal scan
        return call_count > 4

    fake_wlan = MagicMock()
    fake_wlan.isconnected.side_effect = isconnected_side_effect
    fake_wlan.ifconfig.return_value = ("192.168.1.100", "", "", "")
    fake_wlan.scan.return_value = []

    # First ticks_diff calls return >4000 (fast reconnect timeout),
    # then 0 for normal scan loop
    ticks_values = iter([5000, 5000, 0, 0, 0])

    with patch("main.network.WLAN", return_value=fake_wlan), \
         patch("main.load_wifi_config", return_value=(cached_bssid, 6)), \
         patch("main.clear_wifi_config") as mock_clear, \
         patch("time.ticks_diff", side_effect=lambda a, b: next(ticks_values, 0)):
        result = main.connect_wifi("SSID", "PASS")

    assert result is True
    mock_clear.assert_called_once()  # Cache cleared after fast reconnect failure
    assert fake_wlan.connect.call_count == 2  # fast + normal


def test_fast_reconnect_bssid_typeerror_fallback():
    """If bssid kwarg raises TypeError, fallback connect without bssid."""
    cached_bssid = b"\xAA\xBB\xCC\xDD\xEE\xFF"
    call_count = 0

    def isconnected_side_effect():
        nonlocal call_count
        call_count += 1
        return call_count > 2

    def connect_side_effect(ssid=None, password=None, bssid=None):
        if bssid is not None:
            raise TypeError("unexpected keyword argument 'bssid'")

    fake_wlan = MagicMock()
    fake_wlan.isconnected.side_effect = isconnected_side_effect
    fake_wlan.connect.side_effect = connect_side_effect
    fake_wlan.ifconfig.return_value = ("192.168.1.100", "", "", "")

    with patch("main.network.WLAN", return_value=fake_wlan), \
         patch("main.load_wifi_config", return_value=(cached_bssid, 6)), \
         patch("time.ticks_diff", return_value=0):
        result = main.connect_wifi("SSID", "PASS")

    assert result is True
    # Second call should be without bssid (fallback)
    assert fake_wlan.connect.call_count == 2
    fake_wlan.connect.assert_any_call("SSID", "PASS")
