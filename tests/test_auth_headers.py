"""Tests for SwitchBotController._build_auth_headers().

Validates that authentication headers contain all required keys
and that the HMAC signature is correctly formatted.
"""

import base64
import hashlib
import hmac
from unittest.mock import patch

import main


def _make_controller():
    return main.SwitchBotController(
        token="test_token",
        secret="test_secret",
        device_id="DEV001",
    )


def test_headers_contain_all_required_keys():
    """API v1.1 requires Authorization, sign, nonce, t, Content-Type."""
    ctrl = _make_controller()
    headers = ctrl._build_auth_headers()
    required = {"Authorization", "sign", "nonce", "t", "Content-Type"}
    assert required.issubset(headers.keys())


def test_authorization_is_token():
    """Authorization header must be the raw token."""
    ctrl = _make_controller()
    headers = ctrl._build_auth_headers()
    assert headers["Authorization"] == "test_token"


def test_t_is_string_of_digits():
    """t must be a string of 13 digits (millisecond timestamp)."""
    ctrl = _make_controller()
    headers = ctrl._build_auth_headers()
    t = headers["t"]
    assert isinstance(t, str)
    assert t.isdigit()
    assert len(t) == 13


def test_nonce_is_hex_string():
    """nonce must be a hex string (32 chars for 16 random bytes)."""
    ctrl = _make_controller()
    headers = ctrl._build_auth_headers()
    nonce = headers["nonce"]
    assert len(nonce) == 32
    int(nonce, 16)  # Must parse as hex without error


def test_sign_is_uppercase_base64():
    """sign must be uppercase Base64-encoded HMAC-SHA256."""
    ctrl = _make_controller()
    headers = ctrl._build_auth_headers()
    sign = headers["sign"]
    # Must be uppercase
    assert sign == sign.upper()
    # Must be valid base64
    base64.b64decode(sign)


def test_sign_matches_independent_computation():
    """Verify signature against an independent HMAC-SHA256 computation."""
    ctrl = _make_controller()

    # Fix nonce and timestamp for deterministic verification
    fixed_nonce = "a" * 32
    fixed_t_ms = 1700000000000

    with patch.object(ctrl, "_generate_nonce", return_value=fixed_nonce), \
         patch("main.unix_time_ms", return_value=fixed_t_ms):
        headers = ctrl._build_auth_headers()

    # Independently compute expected signature
    data_str = f"test_token{fixed_t_ms}{fixed_nonce}"
    expected_digest = hmac.new(
        b"test_secret", data_str.encode(), hashlib.sha256
    ).digest()
    expected_sign = base64.b64encode(expected_digest).decode().upper()

    assert headers["sign"] == expected_sign
    assert headers["t"] == str(fixed_t_ms)
    assert headers["nonce"] == fixed_nonce


def test_content_type_header():
    """Content-Type must specify JSON with UTF-8."""
    ctrl = _make_controller()
    headers = ctrl._build_auth_headers()
    assert headers["Content-Type"] == "application/json; charset=utf8"
