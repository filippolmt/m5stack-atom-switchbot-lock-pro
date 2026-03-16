# Codebase Structure

**Analysis Date:** 2026-03-16

## Directory Layout

```
m5stack-atom-switchbot-lock-pro/
├── main.py                    # Firmware entry point and all application logic (756 lines)
├── config_template.py         # Template for credentials (git-ignored when copied to config.py)
├── config.py                  # User configuration (git-ignored) - NEVER committed
├── tests/                     # Automated test suite (CPython-based, no hardware required)
│   ├── conftest.py           # Pytest hardware stubs (machine, network, urequests, etc.)
│   ├── test_epoch.py         # Unix epoch conversion tests (8 tests)
│   ├── test_hmac.py          # HMAC-SHA256 RFC 2104 tests
│   ├── test_auth_headers.py  # API authentication header generation tests
│   ├── test_send_command.py  # HTTP retry logic and response cleanup tests (8 tests)
│   ├── test_rtc_memory.py    # RTC memory serialization tests (10 tests)
│   ├── test_led.py           # LED brightness scaling tests
│   └── test_wifi.py          # Wi-Fi connection logic tests (fast reconnect, fallback, etc.)
├── .planning/codebase/       # GSD documentation (this directory)
├── Makefile                  # Test infrastructure: docker build/run
├── Dockerfile.test           # Docker image for test execution (Python 3.13)
├── pyproject.toml            # Pytest configuration
├── README.md                 # User-facing documentation
├── SETUP.md                  # Hardware setup and calibration guide
├── CLAUDE.md                 # Developer instructions (architecture notes, memory constraints)
├── LICENSE                   # MIT license
└── .gitignore               # Ignores config.py, __pycache__, .pytest_cache, etc.
```

## Directory Purposes

**Project Root:**
- Purpose: Single-file MicroPython firmware with configuration and test suite
- Contains: Firmware entry point, configuration template, test harness, build/deployment tools
- Key files: `main.py`, `config_template.py`, `Makefile`

**tests/:**
- Purpose: Automated test suite running on CPython (not MicroPython hardware)
- Contains: 7 test modules covering epoch, cryptography, API client, Wi-Fi, LED, and RTC memory
- Key files: `conftest.py` (hardware stubs), individual `test_*.py` modules
- Note: Hardware stubs (`FakePin`, `FakeWLAN`, `FakeResponse`, etc.) in `conftest.py` allow testing without ESP32

## Key File Locations

**Entry Points:**
- `main.py` (line 754-756): `if __name__ == "__main__": main()` — firmware entry point on device boot
- `tests/conftest.py` (line 201): `import main` — test fixture that loads firmware module with stubs
- `Makefile`: `test` target builds Docker image and runs pytest

**Configuration:**
- `config_template.py`: Template with all required variables (Wi-Fi, SwitchBot token/secret, GPIO pin, optional static IP)
- `config.py`: User configuration file (git-ignored); firmware loads via `from config import ...` (line 60-71)

**Core Logic:**
- `main.py` (line 716-752): `main()` — orchestrator; checks reset cause, routes to button handler or boot splash
- `main.py` (line 587-711): `handle_button_wake()` — button press handler; measures duration, controls Wi-Fi/API sequence
- `main.py` (line 281-395): `SwitchBotController` class — API client; builds headers, sends commands, handles responses
- `main.py` (line 206-276): `StatusLED` class — LED control; color methods, blink sequences with brightness scaling

**Testing:**
- `tests/conftest.py`: Hardware stubs injected before test modules load; defines `FakePin`, `FakeWLAN`, `FakeResponse`, `FakeRTC`, etc.
- `tests/test_send_command.py`: HTTP retry behavior, response cleanup, status code mapping (8 tests)
- `tests/test_wifi.py`: Wi-Fi connection logic including fast reconnect, timeout fallback (7 tests)
- `tests/test_epoch.py`: Unix timestamp conversion with epoch detection (8 tests)
- `tests/test_rtc_memory.py`: RTC memory roundtrip serialization (10 tests)
- `tests/test_auth_headers.py`: API authentication header structure
- `tests/test_hmac.py`: HMAC-SHA256 manual implementation vs. stdlib
- `tests/test_led.py`: LED brightness scaling formula

## Naming Conventions

**Files:**
- `main.py`: Single firmware application file (MicroPython standard)
- `config.py`: User-provided configuration (from `config_template.py`)
- `config_template.py`: Reference template showing all required config keys
- `test_*.py`: Test modules following pytest convention (auto-discovered by `pythonpath = ["."]` in `pyproject.toml`)
- `Makefile`: Build/test orchestration (one-file embedded project standard)
- `Dockerfile.test`: Docker test environment builder

**Functions (in main.py):**
- PascalCase for classes: `StatusLED`, `SwitchBotController`, `FakePin` (stubs in conftest)
- snake_case for functions: `connect_wifi()`, `measure_button_press()`, `handle_button_wake()`, `send_command()`
- UPPER_CASE for constants: `LONG_PRESS_MS`, `_RTC_VALID_FLAG`, `_UNIX_EPOCH_OFFSET_SECONDS`, `API_BASE_URL` (class constant)
- Leading underscore for private methods/constants: `_blink()`, `_scale()`, `_generate_nonce()`, `_build_auth_headers()`, `_UNIX_EPOCH_OFFSET_SECONDS`

**Variables:**
- `led`: StatusLED instance
- `wlan`: WLAN interface object from `network.WLAN()`
- `press_duration`: Button press duration in milliseconds (int)
- `is_lock`: Boolean derived from `press_duration >= LONG_PRESS_MS`
- `cached_bssid`, `cached_channel`: Wi-Fi config from RTC memory (bytes, int or None)
- `bssid`: 6-byte MAC address (bytes)

**Imports:**
- Standard library: `network`, `urequests`, `time`, `machine`, `esp32`, `gc`, `ubinascii`, `hashlib`
- MicroPython-specific or conditionally imported: `hmac` (optional), `ujson`/`json` (try/except), `ntptime`, `neopixel`
- No absolute imports of other project modules (single-file architecture)

## Where to Add New Code

**New Feature (e.g., button debounce, custom LED sequence):**
- Primary code: Add functions to `main.py` immediately before their first use (e.g., debounce utility before `measure_button_press()`)
- Tests: Add `test_<feature>.py` in `tests/` directory
- Stubs: Update `tests/conftest.py` if hardware abstraction needed
- Configuration: Add new config keys to `config_template.py` and load in main.py try/except block

**New Component/Module:**
- **If reusable:** Create as a class in `main.py` (e.g., `SwitchBotController` pattern)
- **If test-heavy:** Add tests before implementation in `tests/test_<component>.py`
- **If hardware-dependent:** Stub in `conftest.py` before implementing logic

**Utilities:**
- **Shared helpers** (time, crypto, Wi-Fi): Add to top of `main.py` after imports, above class definitions
- **Hardware abstractions:** Encapsulate in classes (`StatusLED` pattern) to enable stubbing
- **Configuration options:** Always add to `config_template.py` with defaults, load with try/except in main.py to allow omission

**Testing Strategy:**
- **Unit tests** (most of the suite): Mock external modules, test logic in isolation
- **Integration tests** (few): Verify end-to-end flows like `connect_wifi()` → cached BSSID fallback
- **No E2E tests on hardware:** All tests run on CPython via Docker

## Special Directories

**tests/:**
- Purpose: Test suite for continuous integration
- Generated: No; all files are source
- Committed: Yes
- Run: `make test` (Docker) or `pytest tests/` (local)

**.planning/codebase/:**
- Purpose: GSD documentation generated by mapping commands
- Generated: Yes; created by `/gsd:map-codebase`
- Committed: Yes (in .gitignore but safe to add)
- Contents: ARCHITECTURE.md, STRUCTURE.md, CONVENTIONS.md, TESTING.md, CONCERNS.md (as applicable)

**__pycache__/, .pytest_cache/:**
- Purpose: Python and pytest caches
- Generated: Yes; by Python and pytest during test runs
- Committed: No (in .gitignore)

## Architecture for MicroPython Deployment

**On Device (M5Stack ATOM Lite):**
- `main.py` is uploaded to ESP32 SPIFFS via `mpremote cp main.py :main.py`
- `config.py` is uploaded separately (contains secrets)
- Device boots from `main.py`; firmware self-starts on power-on via `if __name__ == "__main__": main()`

**Testing (CPython in Docker):**
- `conftest.py` stubs all MicroPython modules before importing `main.py`
- Tests import `main` and call functions with mocked hardware
- No ESP32 required; runs in Python 3.13 container

**Separation of Concerns:**
- `main.py`: Single-file firmware (MicroPython-compatible, no external dependencies except MicroPython stdlib)
- `tests/`: CPython test suite (uses `unittest.mock` and pytest; no firmware-specific code)
- `config.py`: User secrets (git-ignored; must be created from template)
- `conftest.py`: Bridge between CPython tests and MicroPython firmware

---

*Structure analysis: 2026-03-16*
