# Phase 3: Low Battery Warning - Context

**Gathered:** 2026-03-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Add orange LED warning when battery voltage is below a threshold. Warning appears after normal lock/unlock LED feedback, not replacing it. Uses battery voltage from `read_battery_voltage()` (Phase 2). This phase does NOT include battery-critical abort (v2 feature).

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
- Voltage threshold for low-battery warning (suggested ~3.3V = 3300mV based on LiPo discharge curve)
- Number of orange blinks (2-3 suggested, consistent with existing feedback patterns)
- Placement: after lock/unlock feedback blinks, before deep sleep
- Whether to print a warning message to serial alongside the LED
- Warning on every wake vs throttled (every wake is simpler and ensures user sees it)
- Threshold should be a constant (e.g., `BATTERY_LOW_MV = 3300`) for Phase 7 configurability

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Battery Voltage
- `main.py` `read_battery_voltage()` — Returns millivolts, already called in `handle_button_wake()`
- `main.py` `save_battery_voltage()` / `load_battery_voltage()` — RTC memory cache

### LED Patterns
- `main.py` `StatusLED` class — `orange()` method and `blink_*()` pattern methods
- `main.py` `handle_button_wake()` — LED feedback section (after WiFi disconnect, before deep sleep)

### Constraints
- `CLAUDE.md` "ESP32 System Heap / mbedTLS Constraint" — No new allocations before HTTPS

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `StatusLED.orange()`: Already exists for setting orange color
- `StatusLED.blink_orange()` or similar: May need to be added (check if exists)
- `read_battery_voltage()`: Returns mV, already in wake flow
- Existing blink patterns: `blink_green()`, `blink_red()`, etc. — template for `blink_orange()`

### Established Patterns
- LED feedback after WiFi disconnect and before deep sleep
- Blink methods use `time.sleep_ms()` loops
- Result-dependent LED: success = green/purple, error = red/yellow

### Integration Points
- `handle_button_wake()`: Add low-battery check after existing LED feedback, before `enter_deep_sleep()`
- `battery_mv` variable already available from Phase 2's `read_battery_voltage()` call
- Phase 7 will make the threshold configurable via `config.py`

</code_context>

<specifics>
## Specific Ideas

No specific requirements — all implementation details delegated to Claude.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 03-low-battery-warning*
*Context gathered: 2026-03-16*
