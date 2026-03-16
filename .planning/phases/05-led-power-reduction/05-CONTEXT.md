# Phase 5: LED Power Reduction - Context

**Gathered:** 2026-03-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Reduce LED brightness from 64 to 32 and halve all blink durations to save energy per wake cycle. LED feedback must remain visible in normal indoor lighting. This is a pure constant/timing change — zero heap risk.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
- Exact new brightness value (32 recommended, down from 64)
- Exact new blink durations (halve all current values)
- Whether to extract brightness as a named constant (e.g., `LED_BRIGHTNESS = 32`) for Phase 7 configurability
- Test strategy: verify `_scale()` still works, verify blink timing constants changed

</decisions>

<canonical_refs>
## Canonical References

### LED Implementation
- `main.py` `StatusLED` class — `__init__` sets brightness, `_scale()` applies it
- `main.py` blink methods — `blink_green()`, `blink_red()`, `blink_orange()`, etc.

### Constraints
- `CLAUDE.md` — No mbedTLS risk here, pure constant changes

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `StatusLED.__init__(pin, num_leds, brightness)`: brightness parameter already exists
- `StatusLED._scale(value)`: Scales RGB by brightness/255 ratio
- All `blink_*()` methods use `time.sleep_ms()` with hardcoded durations

### Integration Points
- `main()` creates `StatusLED` with `brightness=64` — change to 32
- All blink methods have sleep_ms durations to halve
- Phase 7 will make brightness configurable via config.py

</code_context>

<specifics>
## Specific Ideas

No specific requirements — all delegated to Claude.

</specifics>

<deferred>
## Deferred Ideas

None.

</deferred>

---

*Phase: 05-led-power-reduction*
*Context gathered: 2026-03-16*
