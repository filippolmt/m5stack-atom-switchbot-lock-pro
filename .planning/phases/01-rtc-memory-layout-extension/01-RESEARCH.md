# Phase 1: RTC Memory Layout Extension - Research

**Researched:** 2026-03-16
**Domain:** ESP32 MicroPython RTC memory layout, byte-level serialization, backward compatibility
**Confidence:** HIGH

## Summary

This phase extends the existing 8-byte RTC memory layout to 12 bytes, adding fields for battery voltage (uint16), wake counter (uint8), and a reserved byte. The key challenge is backward compatibility: devices with firmware using the old 0xAA flag must not crash or lose WiFi BSSID cache functionality after the update.

The technical domain is straightforward -- `machine.RTC().memory()` accepts and returns arbitrary byte buffers up to 2048 bytes on ESP32. The main risks are: (1) violating the mbedTLS heap constraint by adding module-level allocations, and (2) breaking the existing `load_wifi_config()`/`save_wifi_config()` interface that `connect_wifi()` depends on.

**Primary recommendation:** Use flag-byte discrimination (0xAA = old 8-byte layout, 0xBB = new 12-byte layout) with in-place migration. When `load_wifi_config()` detects 0xAA, read only bytes 0-7 and return WiFi data normally. When `save_wifi_config()` is called, always write the full 12-byte layout with 0xBB. This means the first WiFi save after a firmware update automatically migrates to the new format.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Old 0xAA layout must not crash the firmware -- graceful fallback required
- New layout uses 0xBB flag at byte 7 to distinguish from old 0xAA
- Battery voltage stored in millivolts for direct comparison with threshold constants
- Value written by Phase 2 (ADC read), only reserved/initialized here
- Wake counter written by Phase 4, only reserved/initialized here

### Claude's Discretion
- Exact migration logic (in-place vs reset-and-rebuild)
- Endianness of uint16 fields
- Whether to add a version byte or use flag byte as version indicator
- Test coverage for migration edge cases (corrupted data, partial writes)
- Battery voltage format: uint16 little-endian (simplest) or another format if justified
- Wake counter: single byte with wrap-at-255 (simplest) or 16-bit using byte 11
- Reserved byte 11: keep for future use (initialize to 0x00) or use as status bitfield

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| BATT-05 | Layout RTC memory esteso da 8 a 12 byte con backward compatibility (flag 0xBB) | RTC memory API supports up to 2048 bytes; flag-byte discrimination pattern verified; existing code structure mapped for extension points |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `machine.RTC` | MicroPython built-in (1.24.x) | RTC memory read/write across deep sleep | Already used in project; only API for persistent data across deep sleep |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `struct` | MicroPython built-in | Pack/unpack uint16 values to bytes | For battery voltage (bytes 8-9) serialization |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `struct.pack('<H', mv)` for uint16 | Manual `data[8] = mv & 0xFF; data[9] = (mv >> 8) & 0xFF` | Manual approach avoids importing `struct` (one less import = safer for mbedTLS heap). Given the mbedTLS constraint, manual byte manipulation is preferred. |

**Installation:** No new packages needed. All APIs are MicroPython built-ins.

## Architecture Patterns

### RTC Memory Layout (New 12-byte)
```
Byte 0-5:  BSSID (6 bytes) — existing, unchanged
Byte 6:    WiFi channel (1 byte) — existing, unchanged
Byte 7:    Layout flag (0xBB = new 12-byte layout; old firmware uses 0xAA)
Byte 8:    Battery voltage low byte (mV, uint16 little-endian)
Byte 9:    Battery voltage high byte (mV, uint16 little-endian)
Byte 10:   Wake counter (uint8, wraps at 255)
Byte 11:   Reserved (0x00, for future use)
```

### Pattern 1: Flag-Based Layout Discrimination (Read Path)
**What:** `load_wifi_config()` checks byte 7 to determine which layout is present and reads accordingly.
**When to use:** Every call to `load_wifi_config()` -- it must handle both old and new layouts.
**Example:**
```python
_RTC_VALID_FLAG = 0xAA      # Old 8-byte layout
_RTC_VALID_FLAG_V2 = 0xBB   # New 12-byte layout

def load_wifi_config():
    try:
        from machine import RTC
        data = RTC().memory()
        if data and len(data) >= 12 and data[7] == _RTC_VALID_FLAG_V2:
            # New layout: read WiFi + extended fields available
            bssid = bytes(data[0:6])
            raw_channel = data[6]
            channel = raw_channel if 0 < raw_channel <= 14 else None
            return bssid, channel
        elif data and len(data) >= 8 and data[7] == _RTC_VALID_FLAG:
            # Old layout: read WiFi only, extended fields not available
            bssid = bytes(data[0:6])
            raw_channel = data[6]
            channel = raw_channel if 0 < raw_channel <= 14 else None
            return bssid, channel
    except Exception:
        pass
    return None, None
```

### Pattern 2: Always-Write-New-Layout (Write Path)
**What:** `save_wifi_config()` always writes the full 12-byte layout with 0xBB flag. Extended fields are initialized to 0x00 if no battery/counter data exists yet.
**When to use:** Every call to `save_wifi_config()` -- this automatically migrates from old to new layout.
**Example:**
```python
def save_wifi_config(bssid, channel):
    try:
        if not isinstance(bssid, bytes) or len(bssid) != 6:
            return
        from machine import RTC
        # Preserve existing extended data if present
        rtc = RTC()
        old_data = rtc.memory()
        data = bytearray(12)
        data[0:6] = bssid
        data[6] = channel & 0xFF
        data[7] = _RTC_VALID_FLAG_V2
        # Preserve battery voltage and wake counter if upgrading from v2 data
        if old_data and len(old_data) >= 12 and old_data[7] == _RTC_VALID_FLAG_V2:
            data[8:12] = old_data[8:12]
        # else: bytes 8-11 stay 0x00 (initialized by bytearray)
        rtc.memory(data)
    except Exception as e:
        print(f"Could not save Wi-Fi config: {e}")
```

### Pattern 3: Dedicated Accessors for Extended Fields
**What:** Separate functions for reading/writing battery voltage and wake counter. These do NOT call `save_wifi_config()` -- they read the full buffer, modify their bytes, and write back.
**When to use:** Phase 2 will call `save_battery_voltage(mv)`, Phase 4 will call `increment_wake_counter()`.
**Example:**
```python
def save_battery_voltage(millivolts):
    """Write battery voltage (mV) to RTC memory bytes 8-9. Call AFTER WiFi disconnect."""
    try:
        from machine import RTC
        rtc = RTC()
        data = bytearray(rtc.memory())
        if len(data) >= 12 and data[7] == _RTC_VALID_FLAG_V2:
            data[8] = millivolts & 0xFF          # Low byte
            data[9] = (millivolts >> 8) & 0xFF    # High byte
            rtc.memory(data)
    except Exception:
        pass

def load_battery_voltage():
    """Read cached battery voltage (mV) from RTC memory. Returns 0 if unavailable."""
    try:
        from machine import RTC
        data = RTC().memory()
        if data and len(data) >= 12 and data[7] == _RTC_VALID_FLAG_V2:
            return data[8] | (data[9] << 8)
    except Exception:
        pass
    return 0

def increment_wake_counter():
    """Increment wake counter in RTC memory byte 10. Wraps at 255."""
    try:
        from machine import RTC
        rtc = RTC()
        data = bytearray(rtc.memory())
        if len(data) >= 12 and data[7] == _RTC_VALID_FLAG_V2:
            data[10] = (data[10] + 1) & 0xFF
            rtc.memory(data)
    except Exception:
        pass

def load_wake_counter():
    """Read wake counter from RTC memory. Returns 0 if unavailable."""
    try:
        from machine import RTC
        data = RTC().memory()
        if data and len(data) >= 12 and data[7] == _RTC_VALID_FLAG_V2:
            return data[10]
    except Exception:
        pass
    return 0
```

### Pattern 4: Clear Must Zero All 12 Bytes
**What:** `clear_wifi_config()` must zero the full 12 bytes to invalidate both WiFi and extended data.
**Example:**
```python
def clear_wifi_config():
    try:
        from machine import RTC
        RTC().memory(bytearray(12))
    except Exception:
        pass
```

### Anti-Patterns to Avoid
- **Adding new module-level constants for the layout:** Keep `_RTC_VALID_FLAG_V2 = 0xBB` as a module-level constant (it is just an integer, same as the existing `_RTC_VALID_FLAG = 0xAA`). Do NOT add bytearray templates, struct format strings, or other objects at module level.
- **Importing `struct` at module level:** If `struct` is used at all, it must be lazy-imported inside the function. However, manual byte manipulation is preferred to avoid any import.
- **Reading RTC memory twice in save_wifi_config:** The preserve-existing-data pattern requires one extra read. This is acceptable -- RTC memory access is fast (microseconds) and happens after TLS is complete.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| uint16 serialization | Complex struct packing | Manual `data[i] = val & 0xFF; data[i+1] = (val >> 8) & 0xFF` | Two lines of bit manipulation is simpler and avoids `struct` import (mbedTLS safety) |
| Layout versioning | CRC checksum, version header, TLV encoding | Single flag byte (0xAA vs 0xBB) | Only two layouts will ever exist; a flag byte is the simplest discrimination |
| Migration framework | Automatic multi-version migration logic | Flag detection in read path + always-write-new in write path | The "migration" is just: first save after firmware update writes 0xBB instead of 0xAA |

**Key insight:** This is a 12-byte data structure with exactly two versions. Any abstraction beyond flag-byte discrimination is over-engineering.

## Common Pitfalls

### Pitfall 1: mbedTLS Heap Fragmentation from New Code
**What goes wrong:** Adding new module-level imports, globals, or allocations shifts the system heap layout, breaking TLS handshakes with `MBEDTLS_ERR_MPI_ALLOC_FAILED`.
**Why it happens:** ESP32-PICO-D4 (no PSRAM) shares system heap between WiFi driver and mbedTLS. Any allocation change before `urequests.post()` can fragment the contiguous blocks mbedTLS needs.
**How to avoid:** The new constants (`_RTC_VALID_FLAG_V2 = 0xBB`) are small integers -- same as existing `_RTC_VALID_FLAG = 0xAA`. This is safe. Do NOT add new imports, bytearrays, or format strings at module level.
**Warning signs:** `MBEDTLS_ERR_MPI_ALLOC_FAILED` (-17040) in serial output after firmware update.

### Pitfall 2: Breaking load_wifi_config() Return Interface
**What goes wrong:** `connect_wifi()` calls `load_wifi_config()` and expects `(bssid, channel)` or `(None, None)`. If the return signature changes, WiFi fast reconnect breaks silently.
**Why it happens:** Temptation to return extended data (voltage, counter) from `load_wifi_config()`.
**How to avoid:** Keep `load_wifi_config()` returning exactly `(bssid, channel)`. Add separate `load_battery_voltage()` and `load_wake_counter()` functions for extended fields.
**Warning signs:** `TypeError` in `connect_wifi()` when unpacking return value.

### Pitfall 3: Partial Write Corruption
**What goes wrong:** If the device loses power during `RTC().memory(data)`, the buffer may be partially written, leaving an inconsistent state.
**Why it happens:** RTC memory write is not atomic at the application level.
**How to avoid:** The flag byte (0xBB) is at position 7, in the middle of the buffer. If a partial write stops before byte 7, the flag remains 0x00 (invalid) or the old 0xAA (old format detected, extended fields ignored). If it stops after byte 7, bytes 0-7 are valid and extended fields may be garbage -- but extended fields are only informational (voltage, counter) and callers must handle 0 as "no data". This is acceptable.
**Warning signs:** Wake counter resets unexpectedly, battery voltage reads as 0 after a brown-out.

### Pitfall 4: FakeRTC Test Stub Size Mismatch
**What goes wrong:** The `FakeRTC` stub in `conftest.py` uses `bytearray(8)`. Tests for the new 12-byte layout will fail or give misleading results if the stub is not updated.
**Why it happens:** The stub simulates the real `RTC().memory()` behavior but with a fixed-size buffer.
**How to avoid:** Update `FakeRTC._memory_data = bytearray(8)` to handle variable-size writes (the real `RTC().memory()` stores whatever buffer you give it). The `_reset_rtc` fixture must also be updated.

## Code Examples

### Current RTC Memory Code (lines 21-25, 118-161 of main.py)
```python
# Current constants
_RTC_VALID_FLAG = 0xAA  # line 25

# Current save (line 121-133)
def save_wifi_config(bssid, channel):
    try:
        if not isinstance(bssid, bytes) or len(bssid) != 6:
            return
        from machine import RTC
        data = bytearray(8)
        data[0:6] = bssid
        data[6] = channel & 0xFF
        data[7] = _RTC_VALID_FLAG
        RTC().memory(data)
    except Exception as e:
        print(f"Could not save Wi-Fi config: {e}")

# Current load (line 136-151)
def load_wifi_config():
    try:
        from machine import RTC
        data = RTC().memory()
        if data and len(data) >= 8 and data[7] == _RTC_VALID_FLAG:
            bssid = bytes(data[0:6])
            raw_channel = data[6]
            channel = raw_channel if 0 < raw_channel <= 14 else None
            return bssid, channel
    except Exception:
        pass
    return None, None

# Current clear (line 154-160)
def clear_wifi_config():
    try:
        from machine import RTC
        RTC().memory(bytearray(8))
    except Exception:
        pass
```

### FakeRTC Stub That Needs Updating (conftest.py lines 52-63)
```python
# Current stub -- stores exactly 8 bytes
class FakeRTC:
    _memory_data = bytearray(8)

    def memory(self, data=None):
        if data is not None:
            FakeRTC._memory_data = bytearray(data)  # Already handles variable size
        else:
            return bytes(FakeRTC._memory_data)

# The _reset_rtc fixture resets to 8 bytes -- must change to match new default
@pytest.fixture(autouse=True)
def _reset_rtc():
    FakeRTC._memory_data = bytearray(8)  # Change to bytearray(12) or keep at 8 for migration tests
    yield
    FakeRTC._memory_data = bytearray(8)
```

Note: The FakeRTC stub already handles variable-size writes correctly (it creates a new bytearray from whatever data is passed). The fixture reset size is what needs consideration -- resetting to `bytearray(8)` simulates a fresh/old-layout device, which is correct for migration tests but not for tests that assume the new layout is already in place.

## Recommendations for Discretionary Decisions

### Migration Strategy: In-Place (Recommended)
**Decision:** In-place migration via write path. No separate migration step needed.
**Rationale:** When `save_wifi_config()` is called (which happens on every successful WiFi connection), it writes the new 12-byte layout with 0xBB. The read path handles both 0xAA and 0xBB. Zero additional code needed for migration. Zero additional system heap impact.

### Endianness: Little-Endian (Recommended)
**Decision:** Little-endian for uint16 battery voltage.
**Rationale:** ESP32 (Xtensa LX6) is little-endian natively. Using little-endian means the manual byte manipulation (`data[8] = mv & 0xFF; data[9] = (mv >> 8) & 0xFF`) matches the native memory layout. If `struct` were ever used, `'<H'` would be the natural format.

### Wake Counter: Single Byte, Wrap at 255 (Recommended)
**Decision:** uint8 with silent wrap at 255.
**Rationale:** The counter is purely diagnostic. At 10 presses/day, it wraps every ~25 days. This is sufficient for "how many presses since last power loss" diagnostics. Using 16-bit would consume byte 11 (the reserved byte) and add complexity for minimal gain.

### Reserved Byte 11: Keep as 0x00 (Recommended)
**Decision:** Initialize to 0x00, do not use as bitfield yet.
**Rationale:** No current requirement needs it. Keeping it reserved costs nothing and preserves future flexibility (e.g., CRC8, status flags, or expanding wake counter to 16-bit if needed in v2).

### Flag Byte as Version Indicator (Recommended)
**Decision:** Use the flag byte value directly as version discriminator. No separate version byte needed.
**Rationale:** With only two layout versions (0xAA = v1, 0xBB = v2), a separate version byte is unnecessary overhead. If a third layout is ever needed, byte 11 (reserved) could serve as a sub-version.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| 8-byte RTC layout (0xAA) | 12-byte RTC layout (0xBB) | This phase | Enables battery voltage caching and wake counter for Phases 2-4 |
| Single valid flag | Dual-flag discrimination | This phase | Backward compatibility with devices running old firmware |

## Open Questions

1. **RTC memory behavior on fresh flash (erased chip)**
   - What we know: `RTC().memory()` returns a bytes object; on fresh boot it returns whatever was in RTC memory (likely all zeros or random data)
   - What's unclear: Whether `esptool erase_flash` zeros RTC memory specifically, or leaves it random
   - Recommendation: The code already handles this -- neither 0xAA nor 0xBB flag means "no valid data", returning `(None, None)`. No action needed.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (via Docker, Python 3.13) |
| Config file | Dockerfile.test + Makefile |
| Quick run command | `make test` |
| Full suite command | `make test` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BATT-05 | 12-byte layout write with 0xBB flag | unit | `make test` (test_rtc_memory.py) | Needs update |
| BATT-05 | Old 0xAA layout read returns valid WiFi data | unit | `make test` (test_rtc_memory.py) | New test needed |
| BATT-05 | Migration: save after load-of-old upgrades to 0xBB | unit | `make test` (test_rtc_memory.py) | New test needed |
| BATT-05 | Battery voltage read/write roundtrip (bytes 8-9) | unit | `make test` (test_rtc_memory.py) | New test needed |
| BATT-05 | Wake counter read/write/wrap (byte 10) | unit | `make test` (test_rtc_memory.py) | New test needed |
| BATT-05 | clear_wifi_config zeros 12 bytes | unit | `make test` (test_rtc_memory.py) | Needs update |
| BATT-05 | Existing save/load roundtrip still works | unit | `make test` (test_rtc_memory.py) | Exists (must not break) |

### Sampling Rate
- **Per task commit:** `make test`
- **Per wave merge:** `make test`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] Update `FakeRTC._memory_data` default and `_reset_rtc` fixture in `conftest.py` to support 12-byte layout
- [ ] New test cases for: old-layout-read, migration, battery voltage roundtrip, wake counter wrap, clear-12-bytes
- [ ] Existing 9 tests in `test_rtc_memory.py` must continue passing

## Sources

### Primary (HIGH confidence)
- [MicroPython RTC class documentation v1.24.0](https://docs.micropython.org/en/v1.24.0/library/machine.RTC.html) -- RTC.memory() API, 2048-byte limit, accepts buffer protocol objects, returns bytes
- `main.py` lines 21-25, 118-161 -- Current implementation, verified by direct code reading
- `tests/conftest.py` lines 52-63 -- FakeRTC stub behavior, verified by direct code reading
- `tests/test_rtc_memory.py` -- Existing 9 tests, verified by direct code reading

### Secondary (MEDIUM confidence)
- `.planning/research/STACK.md` -- RTC memory extension guidance from prior research
- `.planning/research/PITFALLS.md` -- mbedTLS heap safety constraints

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- using only built-in `machine.RTC`, no new dependencies
- Architecture: HIGH -- flag-byte discrimination is a well-understood pattern; existing code structure is clear
- Pitfalls: HIGH -- mbedTLS constraint is confirmed by project history; interface stability is verified by code reading

**Research date:** 2026-03-16
**Valid until:** 2026-04-16 (stable domain -- MicroPython RTC API does not change frequently)
