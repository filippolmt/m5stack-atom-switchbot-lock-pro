# Testing

## Framework & Runner

- **Framework**: pytest (CPython 3.13)
- **Runner**: Docker container via `make test`
- **Image**: `Dockerfile.test` builds a Python 3.13 image
- **Commands**:
  - `make test` — Build image + run all tests
  - `make test-clean` — Remove test Docker image

Tests run on **CPython**, not MicroPython. Hardware is fully stubbed.

## Test Structure

```
tests/
├── conftest.py              # Hardware stubs + fixtures
├── test_auth_headers.py     # _build_auth_headers() structure, HMAC signature
├── test_epoch.py            # unix_time_ms(), epoch offset, gmtime fallback
├── test_hmac.py             # hmac_sha256_digest() RFC 2104 vs stdlib
├── test_led.py              # StatusLED._scale() brightness math
├── test_rtc_memory.py       # save/load_wifi_config() byte serialization
├── test_send_command.py     # HTTP retry, response.close(), 401 no-retry
└── test_wifi.py             # connect_wifi() timeout, already-connected
```

**Total**: 53 tests across 7 test files.

## Hardware Stub Strategy (`conftest.py`)

The key architectural decision: `conftest.py` injects fake MicroPython modules into `sys.modules` **before** `import main` runs. This lets the entire firmware source load on CPython unchanged.

### Stubbed Modules

| MicroPython Module | Stub | Key Behavior |
|---|---|---|
| `machine` | `FakePin`, `FakeRTC`, `FakeWDT` | Pin reads HIGH (not pressed), RTC memory is mutable bytearray |
| `esp32` | Module with constants | `wake_on_ext0` is no-op |
| `network` | `FakeWLAN` | `connect()` sets `_connected = True`, `scan()` returns `[]` |
| `urequests` | `FakeResponse` | Returns `status_code=200`, `text='{"statusCode":100}'` |
| `neopixel` | `FakeNeoPixel` | Stores pixel values, `write()` is no-op |
| `ntptime` | Module | `settime()` is no-op |
| `ubinascii` | Maps to `binascii` | CPython equivalent |
| `ujson` | Maps to `json` | CPython equivalent |
| `config` | Fake credentials | Test SSID, token, secret, device ID |

### Time Polyfills

CPython `time` module is monkey-patched with:
- `time.ticks_ms()` — wraps `time.time() * 1000`
- `time.ticks_diff(a, b)` — simple `a - b`
- `time.sleep_ms(ms)` — no-op (tests run fast)

## Fixtures

| Fixture | Scope | Purpose |
|---|---|---|
| `_reset_rtc` | autouse, function | Resets `FakeRTC._memory_data` to zeros before/after each test |

## Test Patterns

### Mocking

Tests use `unittest.mock.patch` to override stub behavior:

```python
# Override urequests.post to simulate errors
with patch("main.urequests.post", side_effect=OSError("timeout")):
    result = main.send_command("lock")
    assert result == "api_error"
```

### Common Patterns

- **Error simulation**: Patch functions to raise `OSError`, `Exception`
- **Roundtrip testing**: Save data → load data → verify equality (RTC memory)
- **Boundary testing**: Edge values for epoch, brightness scaling
- **Deterministic crypto**: Known inputs → verify against expected HMAC output
- **Resource cleanup**: Verify `response.close()` called even on errors

## Coverage

- **Enforcement**: None (no coverage threshold configured)
- **Gaps**: Button press timing, end-to-end wake→sleep flow, WiFi static IP edge cases, NTP failure recovery (all hardware-dependent)
- **Philosophy**: Test what can be tested on CPython; hardware-dependent behavior validated manually via serial monitor

## pytest Configuration

No `pytest.ini` or `pyproject.toml` configuration found. Tests discovered by default conventions (`test_*.py` files in `tests/` directory).

---
*Mapped: 2026-03-16*
