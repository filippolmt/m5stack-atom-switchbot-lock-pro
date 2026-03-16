# Phase 1: RTC Memory Layout Extension - Context

**Gathered:** 2026-03-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Extend RTC memory from 8 to 12 bytes to support battery voltage caching and wake counter alongside existing WiFi BSSID cache. Must maintain backward compatibility with old 0xAA layout. No new user-facing features in this phase — purely data structure foundation for Phases 2-4.

</domain>

<decisions>
## Implementation Decisions

### Migration Strategy
- Claude's choice: migrate in-place vs reset — pick what's simplest and safest given mbedTLS heap constraint
- Old 0xAA layout must not crash the firmware — graceful fallback required
- New layout uses 0xBB flag at byte 7 to distinguish from old 0xAA

### Battery Voltage Format (Bytes 8-9)
- Claude's choice: last reading as uint16 little-endian (simplest, avoids extra complexity) or another format if justified
- Value stored in millivolts for direct comparison with threshold constants
- Written by Phase 2 (ADC read), only reserved/initialized here

### Wake Counter (Byte 10)
- Claude's choice: single byte with wrap-at-255 (simplest) or 16-bit using byte 11 if justified
- Counter is for diagnostics — doesn't need to be precise over weeks
- Written by Phase 4, only reserved/initialized here

### Reserved Byte (Byte 11)
- Claude's choice: keep for future use (initialize to 0x00) or use as status bitfield if it saves a byte elsewhere
- If used as bitfield, document which bits mean what

### Claude's Discretion
- Exact migration logic (in-place vs reset-and-rebuild)
- Endianness of uint16 fields
- Whether to add a version byte or use flag byte as version indicator
- Test coverage for migration edge cases (corrupted data, partial writes)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### RTC Memory Implementation
- `main.py` lines 21-25 — Current RTC memory layout constants and valid flag
- `main.py` lines 118-161 — Current `save_wifi_config()`, `load_wifi_config()`, `clear_wifi_config()` functions

### Constraints
- `CLAUDE.md` "ESP32 System Heap / mbedTLS Constraint" section — Critical: no new module-level allocations, lazy imports only
- `.planning/research/STACK.md` — ADC reading approach, RTC memory extension guidance
- `.planning/research/PITFALLS.md` — mbedTLS safety for RTC memory changes

### Test Coverage
- `tests/test_rtc_memory.py` — Existing tests for save/load WiFi config roundtrip
- `tests/conftest.py` lines 52-63 — FakeRTC stub with 8-byte memory

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `save_wifi_config(bssid, channel)`: Writes 8-byte bytearray to `RTC().memory()`. Template for extended write.
- `load_wifi_config()`: Reads and validates via `_RTC_VALID_FLAG`. Template for extended read with flag detection.
- `clear_wifi_config()`: Zeros 8 bytes. Must be updated to zero 12 bytes.
- `FakeRTC` in conftest.py: Uses `bytearray(8)` — must be updated to `bytearray(12)` for extended layout tests.

### Established Patterns
- **Lazy import**: `from machine import RTC` inside each function, not at module level — must continue this pattern
- **Exception swallowing**: All RTC operations wrapped in try/except with fallback to defaults — maintain this
- **Flag-based validation**: `data[7] == _RTC_VALID_FLAG` guards against corrupted/uninitialized memory

### Integration Points
- `connect_wifi()` calls `load_wifi_config()` and `save_wifi_config()` — these interfaces must stay compatible
- `handle_button_wake()` calls `load_wifi_config()` early — extended read shouldn't add overhead here
- Phase 2 will add battery voltage write after WiFi disconnect
- Phase 4 will add counter increment at wake start

</code_context>

<specifics>
## Specific Ideas

No specific requirements — user delegated all format decisions to Claude. Key constraint is backward compatibility with existing devices that have 0xAA layout in RTC memory.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 01-rtc-memory-layout-extension*
*Context gathered: 2026-03-16*
