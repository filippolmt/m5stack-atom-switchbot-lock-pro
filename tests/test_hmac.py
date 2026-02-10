"""Tests for HMAC-SHA256 implementation.

Validates both the stdlib hmac path and the manual RFC 2104 fallback
produce identical digests.
"""

import hashlib
import hmac as stdlib_hmac
from unittest.mock import patch

import main


def _reference_hmac(key: bytes, msg: bytes) -> bytes:
    """Compute HMAC-SHA256 using Python stdlib (ground truth)."""
    return stdlib_hmac.new(key, msg, hashlib.sha256).digest()


def test_hmac_module_path():
    """With HAVE_HMAC=True, result matches stdlib reference."""
    key = b"test-secret"
    msg = b"test-message"
    with patch.object(main, "HAVE_HMAC", True):
        result = main.hmac_sha256_digest(key, msg)
    assert result == _reference_hmac(key, msg)


def test_hmac_manual_path():
    """With HAVE_HMAC=False, manual RFC 2104 matches stdlib reference."""
    key = b"test-secret"
    msg = b"test-message"
    with patch.object(main, "HAVE_HMAC", False):
        result = main.hmac_sha256_digest(key, msg)
    assert result == _reference_hmac(key, msg)


def test_hmac_both_paths_identical():
    """Both code paths produce the same digest."""
    key = b"my-api-secret-key"
    msg = b"token1234567890nonce"
    with patch.object(main, "HAVE_HMAC", True):
        result_module = main.hmac_sha256_digest(key, msg)
    with patch.object(main, "HAVE_HMAC", False):
        result_manual = main.hmac_sha256_digest(key, msg)
    assert result_module == result_manual


def test_hmac_long_key():
    """Keys longer than 64 bytes are hashed before use (RFC 2104)."""
    long_key = b"x" * 100
    msg = b"data"
    with patch.object(main, "HAVE_HMAC", False):
        result = main.hmac_sha256_digest(long_key, msg)
    assert result == _reference_hmac(long_key, msg)


def test_hmac_empty_message():
    """Empty message should still produce a valid digest."""
    key = b"secret"
    msg = b""
    with patch.object(main, "HAVE_HMAC", False):
        result = main.hmac_sha256_digest(key, msg)
    assert result == _reference_hmac(key, msg)
    assert len(result) == 32  # SHA-256 digest = 32 bytes


def test_hmac_empty_key():
    """Empty key should still produce a valid digest (padded to block size)."""
    key = b""
    msg = b"some data"
    with patch.object(main, "HAVE_HMAC", False):
        result = main.hmac_sha256_digest(key, msg)
    assert result == _reference_hmac(key, msg)


def test_hmac_digest_length():
    """All digests must be exactly 32 bytes (SHA-256)."""
    key = b"k"
    msg = b"m"
    for have_hmac in (True, False):
        with patch.object(main, "HAVE_HMAC", have_hmac):
            result = main.hmac_sha256_digest(key, msg)
        assert len(result) == 32
