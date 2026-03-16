# Phase 4: Wake Cycle Counter - Context

**Gathered:** 2026-03-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Increment a wake counter in RTC memory byte 10 on every button press wake. Print counter value to serial alongside battery voltage. Counter wraps at 255 (single byte). Uses `increment_wake_counter()` and `load_wake_counter()` from Phase 1.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
- Serial output format (e.g., `Wake #42 | Battery: 3850mV` or separate line)
- Where to increment in `handle_button_wake()` — early (before WiFi) is fine since it's just a byte write to RTC
- Whether to print counter even on cold boot (reset_cause != DEEPSLEEP_RESET)
- Test strategy: mock RTC memory, verify increment and wrap behavior

</decisions>

<canonical_refs>
## Canonical References

### RTC Memory Functions
- `main.py` `increment_wake_counter()` and `load_wake_counter()` — Already implemented in Phase 1
- `main.py` RTC memory layout — Byte 10 = wake counter

### Integration
- `main.py` `handle_button_wake()` — Where to add increment and print
- `CLAUDE.md` — mbedTLS constraint (RTC write is safe before WiFi — no system heap impact)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `increment_wake_counter()`: Already implemented, increments byte 10 with wrap at 255
- `load_wake_counter()`: Already implemented, reads byte 10

### Integration Points
- `handle_button_wake()`: Add increment early in flow, print with battery voltage

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

*Phase: 04-wake-cycle-counter*
*Context gathered: 2026-03-16*
