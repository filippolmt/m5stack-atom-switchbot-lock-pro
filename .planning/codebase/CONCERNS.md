# Codebase Concerns

## Technical Debt

### High Priority

- **Single-file monolith**: `main.py` is 756 lines containing all logic (LED, WiFi, crypto, API, state machine). Difficult to test components in isolation.
- **Fragile HMAC fallback**: Manual RFC 2104 HMAC-SHA256 implementation used when `hmac` module unavailable. Subtle bugs possible.
- **Random bytes via LCG**: `random_bytes()` falls back to Linear Congruential Generator when `os.urandom` unavailable. LCG output is predictable — nonces generated this way are weak.
- **Hardcoded thresholds**: `LONG_PRESS_MS = 1000`, WiFi timeout, retry counts all hardcoded without config validation.
- **RTC memory corruption undetected**: Only checks `0xAA` valid flag at byte 7. No CRC or checksum on BSSID bytes 0-5.

### Medium Priority

- **No modular decomposition**: All classes and functions in one file due to ESP32 heap constraints, but makes development harder.
- **Epoch detection on every call**: `unix_time_ms()` calls `time.gmtime(0)[0]` each invocation instead of caching (caching forbidden due to mbedTLS heap constraint).

## Known Bugs / Issues

- **Static IP silent fallback**: If `WIFI_STATIC_IP` tuple is malformed, device silently falls back to DHCP with only a print message. User may not notice.
- **Fast reconnect channel validation weak**: Cached channel (byte 6) is diagnostic only — not used for reconnect. If BSSID moves channels, reconnect may be slower.
- **Epoch detection overhead**: Repeated `gmtime(0)` calls add small but unnecessary overhead per API call.

## Security Concerns

- **HMAC nonce predictability**: When `os.urandom` unavailable, LCG-generated nonces are predictable. An attacker could replay or forge API signatures (mitigated by SwitchBot's server-side timestamp validation).
- **Plaintext credentials**: `config.py` stores WiFi password, SwitchBot token/secret in plaintext on flash. Physical access = credential extraction.
- **Time-based signature spoofing**: API signatures include timestamp. If NTP sync fails and RTC drifts, signatures may be rejected (fail-safe) or could theoretically be replayed within the validity window (low severity).

## Performance Bottlenecks

- **Full WiFi scan on cache miss**: When RTC BSSID cache is invalid, full AP scan takes 10-30 seconds.
- **NTP sync on first boot**: Adds 3-5 seconds to first wake cycle.
- **Manual HMAC-SHA256**: Python-level HMAC computation is slower than native. Necessary due to MicroPython module availability.

## Fragile Areas

- **Button press measurement**: `measure_button_press()` polling loop timing depends on CPU frequency. At 80MHz idle, timing accuracy may drift.
- **RTC memory state assumptions**: Code assumes RTC memory survives deep sleep perfectly. Brown-out or power glitch could corrupt without detection.
- **WiFi config cache inconsistency**: If AP changes BSSID (router replacement, mesh roaming), cached BSSID causes repeated connection failures until cache naturally expires.
- **Exception handling breadth**: Many `except Exception` blocks catch everything, potentially masking unexpected errors.

## Scaling Limits

- **RTC memory**: Only 8 bytes used (of 2048 available). Current layout is fixed — adding more cached state requires layout migration.
- **Single device**: One SwitchBot Lock Pro per config. No support for multiple devices or device discovery.
- **No API rate limiting**: Rapid button presses could hit SwitchBot API rate limits.

## Critical Dependencies

- **MicroPython v1.24.1**: Firmware version locked. Other versions may have different mbedTLS behavior or heap layout.
- **mbedTLS system heap**: The most critical constraint. Any code change that shifts system heap allocation can break TLS. See CLAUDE.md "ESP32 System Heap / mbedTLS Constraint" section.

## Test Coverage Gaps

- Button press measurement timing accuracy (hardware-dependent)
- End-to-end wake → lock/unlock → sleep flow (requires hardware)
- NTP sync failure recovery paths
- WiFi static IP edge cases (malformed tuples)
- API error response parsing for non-standard HTTP responses
- RTC memory corruption recovery

---
*Mapped: 2026-03-16*
