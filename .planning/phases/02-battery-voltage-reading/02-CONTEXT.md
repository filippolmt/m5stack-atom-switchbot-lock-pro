# Phase 2: Battery Voltage Reading - Context

**Gathered:** 2026-03-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Read battery voltage via ADC on GPIO 33 (Atomic Battery Base voltage divider 1:1) and print to serial output on every wake cycle. Save reading to RTC memory for cross-wake comparison. This phase adds the ADC reading function and wires it into the wake flow — low-battery warning (Phase 3) uses this data.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
- Serial output format (e.g., `⚡ Battery: 3850mV` or simpler)
- Number of ADC samples to average (single vs multiple for noise reduction)
- ADC attenuation setting (ADC.ATTN_11DB for full 0-3.3V range)
- Whether to save reading to RTC memory via `save_battery_voltage()` (already implemented in Phase 1)
- Voltage divider formula: `V_BAT = read_uv() * 2 / 1_000_000` (1:1 divider with 2x 1MOhm resistors)
- Test strategy for ADC (mock `machine.ADC` in conftest.py)
- Exact placement in `handle_button_wake()` — after WiFi disconnect, before LED feedback

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### ADC Implementation
- `main.py` lines 180-210 — `save_battery_voltage()` and `load_battery_voltage()` (from Phase 1)
- `.planning/research/STACK.md` — ADC GPIO 33 config, `read_uv()` method, voltage divider formula
- `.planning/research/PITFALLS.md` — ADC nonlinearity, noise, timing constraints

### Wake Flow Integration
- `main.py` `handle_button_wake()` — Where to insert ADC read (after WiFi disconnect)
- `CLAUDE.md` "ESP32 System Heap / mbedTLS Constraint" — ADC MUST be after urequests.post()

### Test Infrastructure
- `tests/conftest.py` — Hardware stubs, needs `machine.ADC` stub added
- `tests/test_rtc_memory.py` — Existing battery voltage roundtrip tests from Phase 1

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `save_battery_voltage(millivolts)`: Already implemented in Phase 1, writes to RTC bytes 8-9
- `load_battery_voltage()`: Already implemented, reads cached voltage from RTC memory
- Lazy import pattern: `from machine import RTC` inside functions — replicate for ADC

### Established Patterns
- Lazy imports inside functions (mbedTLS safety)
- Exception swallowing with fallback values
- Print with emoji prefix for serial output (`✓`, `✗`, `⚠`)

### Integration Points
- `handle_button_wake()`: Insert ADC read after `wlan.active(False)` and before LED feedback
- `conftest.py`: Needs `FakeADC` class added to `machine` module stub
- Phase 3 will use the voltage value for low-battery threshold check

</code_context>

<specifics>
## Specific Ideas

No specific requirements — user delegated all implementation details to Claude. Key constraints:
1. ADC read MUST happen after WiFi disconnect (mbedTLS heap safety)
2. Lazy import of `machine.ADC` inside the reading function
3. Use `read_uv()` for factory-calibrated readings if available on MicroPython v1.24.x

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 02-battery-voltage-reading*
*Context gathered: 2026-03-16*
