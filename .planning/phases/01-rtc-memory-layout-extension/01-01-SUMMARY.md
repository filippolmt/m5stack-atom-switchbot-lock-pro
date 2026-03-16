---
phase: 01-rtc-memory-layout-extension
plan: 01
subsystem: database
tags: [rtc-memory, esp32, micropython, backward-compatibility, byte-serialization]

# Dependency graph
requires: []
provides:
  - "12-byte RTC memory layout with dual-flag discrimination (0xAA/0xBB)"
  - "save_battery_voltage/load_battery_voltage accessors (uint16 LE, bytes 8-9)"
  - "increment_wake_counter/load_wake_counter accessors (uint8, byte 10)"
  - "Backward-compatible load_wifi_config for old 0xAA layout"
affects: [02-battery-voltage-reading, 04-wake-counter, 06-wifi-channel-optimization]

# Tech tracking
tech-stack:
  added: []
  patterns: [flag-byte-discrimination, manual-byte-manipulation, preserve-extended-fields-on-write]

key-files:
  created: []
  modified: [main.py, tests/test_rtc_memory.py]

key-decisions:
  - "Little-endian uint16 for battery voltage (matches ESP32 native endianness)"
  - "Manual byte manipulation instead of struct import (mbedTLS heap safety)"
  - "FakeRTC fixture kept at bytearray(8) default to simulate old-layout device for migration tests"

patterns-established:
  - "Flag-byte discrimination: 0xAA = old 8-byte, 0xBB = new 12-byte RTC layout"
  - "Preserve-on-write: save_wifi_config reads existing extended fields before overwriting"
  - "Dedicated accessors: battery voltage and wake counter have separate read/write functions"

requirements-completed: [BATT-05]

# Metrics
duration: 2min
completed: 2026-03-16
---

# Phase 1 Plan 1: RTC Memory Layout Extension Summary

**12-byte RTC memory layout with 0xBB flag, backward-compatible 0xAA read, and battery voltage/wake counter accessors using manual byte manipulation**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-16T20:06:05Z
- **Completed:** 2026-03-16T20:08:32Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Extended RTC memory from 8 to 12 bytes with new 0xBB flag for layout discrimination
- Backward compatibility: devices with old 0xAA layout continue to work after firmware update
- New accessor functions ready for Phase 2 (battery voltage) and Phase 4 (wake counter)
- Zero new module-level imports or allocations (mbedTLS heap safety maintained)
- 67 total tests pass (54 existing + 13 new)

## Task Commits

Each task was committed atomically:

1. **Task 1: Write failing tests for 12-byte RTC memory layout (RED)** - `a6a301e` (test)
2. **Task 2: Implement 12-byte RTC memory layout in main.py (GREEN)** - `8edc703` (feat)

## Files Created/Modified
- `main.py` - Extended RTC memory layout: new constant _RTC_VALID_FLAG_V2, updated save/load/clear, new battery voltage and wake counter accessors
- `tests/test_rtc_memory.py` - 13 new tests for migration, extended fields, backward compat, battery voltage roundtrip, wake counter wrap

## Decisions Made
- Little-endian uint16 for battery voltage (matches ESP32 native Xtensa LX6 endianness)
- Manual byte manipulation (`data[8] = mv & 0xFF`) instead of importing struct (avoids mbedTLS heap fragmentation)
- FakeRTC fixture default kept at bytearray(8) to simulate old-layout/fresh devices for migration tests
- Reserved byte 11 initialized to 0x00, kept for future use

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- RTC memory layout foundation complete
- Phase 2 can call `save_battery_voltage(mv)` and `load_battery_voltage()` directly
- Phase 4 can call `increment_wake_counter()` and `load_wake_counter()` directly
- No blockers

## Self-Check: PASSED

All files and commits verified.

---
*Phase: 01-rtc-memory-layout-extension*
*Completed: 2026-03-16*
