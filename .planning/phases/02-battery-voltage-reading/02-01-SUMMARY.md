---
phase: 02-battery-voltage-reading
plan: 01
subsystem: firmware
tags: [adc, esp32, micropython, battery, gpio33, voltage-divider]

# Dependency graph
requires:
  - phase: 01-rtc-memory-layout-extension
    provides: save_battery_voltage() and load_battery_voltage() RTC memory accessors
provides:
  - read_battery_voltage() function with lazy ADC import and 4-sample averaging
  - Battery voltage serial output on every wake cycle
  - FakeADC test stub for machine.ADC mocking
affects: [03-low-battery-warning, 09-documentation]

# Tech tracking
tech-stack:
  added: [machine.ADC, machine.Pin (lazy import inside function)]
  patterns: [lazy-import ADC for mbedTLS heap safety, 4-sample ADC averaging, voltage divider formula]

key-files:
  created: [tests/test_battery.py]
  modified: [main.py, tests/conftest.py]

key-decisions:
  - "ADC read placed after WiFi disconnect to avoid mbedTLS heap fragmentation and RF interference"
  - "4-sample averaging for noise reduction with negligible time cost"
  - "Lazy import of machine.ADC inside function body (not module level) per mbedTLS constraint"

patterns-established:
  - "FakeADC stub pattern: configurable read_uv() return value for ADC testing on CPython"
  - "Battery read placement: always after wlan.active(False), before LED feedback"

requirements-completed: [BATT-01, BATT-03]

# Metrics
duration: 2min
completed: 2026-03-16
---

# Phase 2 Plan 1: Battery Voltage Reading Summary

**ADC battery voltage reading on GPIO 33 with lazy import, 4-sample averaging, and voltage divider formula (avg_uv * 2 // 1000)**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-16T20:26:29Z
- **Completed:** 2026-03-16T20:28:10Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- read_battery_voltage() reads GPIO 33 ADC with ATTN_11DB, averages 4 samples, applies 1:1 voltage divider formula
- ADC failure returns 0 gracefully (never crashes the wake cycle)
- Battery voltage printed to serial and saved to RTC memory on every wake
- FakeADC test stub enables full ADC testing on CPython without hardware

## Task Commits

Each task was committed atomically:

1. **Task 1: RED -- FakeADC stub and failing battery tests** - `0a02333` (test)
2. **Task 2: GREEN -- Implement read_battery_voltage() and wire into handle_button_wake()** - `b738e37` (feat)

_TDD: RED/GREEN phases each committed separately_

## Files Created/Modified
- `main.py` - Added read_battery_voltage() function and integration in handle_button_wake() after WiFi disconnect
- `tests/conftest.py` - Added FakeADC class with configurable read_uv() and registered as machine.ADC
- `tests/test_battery.py` - 6 unit tests covering normal/full/low voltage, ADC failure, 4-sample averaging, serial output

## Decisions Made
- ADC read placed after WiFi disconnect -- avoids mbedTLS heap fragmentation and WiFi RF interference on ADC
- 4-sample averaging -- reduces noise with negligible time cost (~microseconds per read_uv call)
- Lazy import of machine.ADC/Pin inside function body -- mandatory per CLAUDE.md mbedTLS constraint
- No delay between WiFi off and ADC read -- wlan.active(False) fully settles RF before returning

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- read_battery_voltage() available for Phase 3 (low battery warning) to add threshold checks
- Battery mV value saved to RTC memory for Phase 9 (documentation with real autonomy estimates)
- Test infrastructure (FakeADC) ready for extending battery-related tests

---
*Phase: 02-battery-voltage-reading*
*Completed: 2026-03-16*

## Self-Check: PASSED

- [x] tests/test_battery.py exists
- [x] tests/conftest.py exists
- [x] main.py exists
- [x] Commit 0a02333 (Task 1 RED) exists
- [x] Commit b738e37 (Task 2 GREEN) exists
