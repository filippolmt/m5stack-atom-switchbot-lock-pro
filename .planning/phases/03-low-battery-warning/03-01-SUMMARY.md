---
phase: 03-low-battery-warning
plan: 01
subsystem: firmware
tags: [micropython, esp32, battery, led, adc, tdd]

# Dependency graph
requires:
  - phase: 02-battery-voltage-reading
    provides: "read_battery_voltage() function returning mV from GPIO 33 ADC"
provides:
  - "BATTERY_LOW_MV constant (3300mV threshold)"
  - "check_low_battery(battery_mv, led) function with orange LED blink"
  - "Low-battery warning wired into handle_button_wake() after LED feedback"
affects: [04-rtc-battery-cache, 05-battery-trend]

# Tech tracking
tech-stack:
  added: []
  patterns: ["post-feedback secondary LED warning pattern"]

key-files:
  created: [tests/test_battery.py (5 new tests appended)]
  modified: [main.py]

key-decisions:
  - "check_low_battery() as standalone function for testability (not inline in handle_button_wake)"
  - "Shorter blink timing (200ms on, 150ms off) vs default orange (300ms/200ms) to minimize wake time"
  - "Threshold at 3300mV -- triggers below, not at exact value"

patterns-established:
  - "Secondary LED warning pattern: additional blink sequence after primary feedback, before led.off()"

requirements-completed: [BATT-02, LED-03]

# Metrics
duration: 2min
completed: 2026-03-16
---

# Phase 3 Plan 1: Low-Battery Warning Summary

**Orange LED blink warning when battery < 3300mV, with ADC failure guard and TDD coverage**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-16T20:44:23Z
- **Completed:** 2026-03-16T20:46:14Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- BATTERY_LOW_MV = 3300 constant for low-battery threshold
- check_low_battery() function with orange LED blink and serial WARNING message
- Wired into handle_button_wake() after normal lock/unlock LED feedback
- 5 new tests covering all boundary conditions (below, above, at threshold, ADC failure, serial output)
- All 78 tests pass (73 existing + 5 new)

## Task Commits

Each task was committed atomically:

1. **Task 1: RED -- Write failing tests for low-battery warning** - `cc4d6e4` (test)
2. **Task 2: GREEN -- Implement BATTERY_LOW_MV, check_low_battery(), wire into handle_button_wake()** - `28dc007` (feat)

_Note: TDD tasks -- RED then GREEN commits_

## Files Created/Modified
- `main.py` - Added BATTERY_LOW_MV constant, check_low_battery() function, wired into handle_button_wake()
- `tests/test_battery.py` - Added 5 new test functions for low-battery warning logic

## Decisions Made
- check_low_battery() extracted as standalone function rather than inline conditional -- enables direct unit testing with mock LED
- Shorter blink timing (200ms on, 150ms off) to minimize additional wake time since this is a secondary indicator
- Guard on battery_mv > 0 prevents false warnings when ADC fails (returns 0)
- Threshold check uses strict less-than (not <=) so exactly 3300mV does not trigger warning

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Low-battery warning functional and tested
- battery_mv value already cached in RTC memory (from Phase 2) -- available for trend analysis in future phases
- check_low_battery() pattern can be extended with additional warning levels if needed

---
*Phase: 03-low-battery-warning*
*Completed: 2026-03-16*
