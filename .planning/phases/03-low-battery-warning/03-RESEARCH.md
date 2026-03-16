# Phase 3: Low Battery Warning - Research

**Researched:** 2026-03-16
**Domain:** MicroPython LED feedback / LiPo battery thresholds
**Confidence:** HIGH

## Summary

This phase adds an orange LED warning when battery voltage drops below a configurable threshold. The implementation is minimal: a single constant (`BATTERY_LOW_MV`), a conditional check on the already-available `battery_mv` variable, and a call to the existing `blink_orange()` method. All building blocks exist in `main.py` today.

The key design decision is **placement**: the warning must appear after the normal lock/unlock LED feedback (green/purple/red blinks) but before `enter_deep_sleep()`. This ensures the user always sees the primary action result first, then gets a secondary "battery low" alert. No new imports, no new classes, no system heap risk.

**Primary recommendation:** Add a `BATTERY_LOW_MV = 3300` constant and a 3-line conditional block in `handle_button_wake()` after the existing LED feedback section, before `led.off()` / deep sleep.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
No locked decisions -- all implementation details delegated to Claude's discretion.

### Claude's Discretion
- Voltage threshold for low-battery warning (suggested ~3.3V = 3300mV based on LiPo discharge curve)
- Number of orange blinks (2-3 suggested, consistent with existing feedback patterns)
- Placement: after lock/unlock feedback blinks, before deep sleep
- Whether to print a warning message to serial alongside the LED
- Warning on every wake vs throttled (every wake is simpler and ensures user sees it)
- Threshold should be a constant (e.g., `BATTERY_LOW_MV = 3300`) for Phase 7 configurability

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| BATT-02 | LED arancione lampeggia quando tensione batteria scende sotto soglia low-battery (~3.3V) | Threshold constant `BATTERY_LOW_MV = 3300`, conditional check on `battery_mv`, `blink_orange()` already exists |
| LED-03 | Warning LED arancione per low-battery integrato nel flusso wake | Insert after existing LED feedback block in `handle_button_wake()`, before deep sleep entry |
</phase_requirements>

## Standard Stack

No new libraries required. This phase uses only existing code:

| Component | Location | Purpose |
|-----------|----------|---------|
| `StatusLED.blink_orange()` | `main.py` line 357 | Already exists: 3 blinks, 300ms on, 200ms off |
| `read_battery_voltage()` | `main.py` line 231 | Returns mV, already called in `handle_button_wake()` |
| `battery_mv` variable | `main.py` line 779 | Already available in wake flow scope |

**Installation:** None needed.

## Architecture Patterns

### Integration Point

The exact insertion point in `handle_button_wake()` is after the LED feedback block (lines 787-803) and before the final `led.off()` on line 805.

Current flow:
```
WiFi disconnect -> read_battery_voltage() -> LED feedback (success/error) -> led.off() -> return result
```

New flow:
```
WiFi disconnect -> read_battery_voltage() -> LED feedback (success/error) -> LOW BATTERY WARNING -> led.off() -> return result
```

### Pattern: Constant + Conditional + Existing Method

```python
# At module level, near LONG_PRESS_MS (line 637)
BATTERY_LOW_MV = 3300  # Low battery threshold in millivolts

# In handle_button_wake(), after LED feedback block, before final led.off()
if battery_mv > 0 and battery_mv < BATTERY_LOW_MV:
    print(f"WARNING: Low battery ({battery_mv}mV < {BATTERY_LOW_MV}mV)")
    led.blink_orange(times=3, on_ms=200, off_ms=150)
```

**Why `battery_mv > 0`:** Avoids false warning when ADC read fails (returns 0).

### Anti-Patterns to Avoid
- **New import or class for this:** Overkill. A constant and 3 lines of code is all that's needed.
- **Replacing normal feedback:** The warning is additive, never replaces success/error blinks.
- **Module-level battery check:** Must stay inside `handle_button_wake()` where `battery_mv` is already computed.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Orange blink pattern | Custom blink loop | `led.blink_orange()` | Already exists with standard timing |
| Battery voltage read | New ADC code | `battery_mv` variable | Already computed in the same function |

## Common Pitfalls

### Pitfall 1: Warning Before Normal Feedback
**What goes wrong:** User sees orange first, gets confused about whether lock/unlock succeeded.
**Why it happens:** Inserting the check too early in the function.
**How to avoid:** Place the low-battery check strictly AFTER the success/error LED feedback block.
**Warning signs:** Orange blinks appear before green/purple/red blinks.

### Pitfall 2: False Warning on ADC Failure
**What goes wrong:** `battery_mv == 0` (ADC failed) triggers the `< 3300` check.
**Why it happens:** Forgetting that 0 means "read failed," not "battery dead."
**How to avoid:** Guard with `battery_mv > 0` before threshold comparison.
**Warning signs:** Orange warning on every boot even with full battery.

### Pitfall 3: System Heap Impact
**What goes wrong:** Adding code before the HTTPS POST breaks TLS.
**Why it happens:** Any new allocation before `urequests.post()` can fragment the system heap.
**How to avoid:** The constant `BATTERY_LOW_MV = 3300` is a simple integer at module level -- safe. The conditional runs AFTER WiFi disconnect and HTTPS, so no heap risk.
**Warning signs:** `MBEDTLS_ERR_MPI_ALLOC_FAILED` errors.

### Pitfall 4: Blink Duration Adds Wake Time
**What goes wrong:** Too many blinks extend the wake cycle, wasting battery.
**Why it happens:** Choosing too many blinks or long durations.
**How to avoid:** Use 3 blinks with shorter timing (200ms on, 150ms off = ~1050ms total). This matches the existing pattern scale while being perceptible.
**Warning signs:** Total wake time noticeably longer on low battery.

## Code Examples

### Recommended Implementation

```python
# Module-level constant (near LONG_PRESS_MS on line 637)
BATTERY_LOW_MV = 3300  # Low battery warning threshold (mV)

# In handle_button_wake(), after line 803 (end of LED feedback block),
# before the final led.off() on line 805:

    # Low battery warning (after normal feedback, before deep sleep)
    if battery_mv > 0 and battery_mv < BATTERY_LOW_MV:
        print(f"WARNING: Low battery ({battery_mv}mV)")
        led.blink_orange(times=3, on_ms=200, off_ms=150)

    led.off()
```

### Threshold Rationale

LiPo discharge curve context:
- 4.2V = full charge
- 3.7V = nominal voltage (~50%)
- 3.3V = low warning zone (~10-15% remaining)
- 3.0V = critically low (damage risk below this)

3300mV is standard for "low battery warning" -- enough remaining capacity for several more operations, but signals the user should recharge soon. Phase 7 will make this configurable via `config.py`.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No battery monitoring | Phase 2 added `read_battery_voltage()` | Phase 2 (this project) | Battery voltage now available in wake flow |
| No battery warning | Phase 3 adds orange LED warning | This phase | User gets visual low-battery feedback |

## Open Questions

1. **Exact blink timing for low-battery**
   - What we know: Existing `blink_orange()` defaults are 3 blinks, 300ms on, 200ms off (~1500ms total)
   - Recommendation: Use slightly shorter timing (200ms on, 150ms off = ~1050ms) since this is a secondary indicator and we want to minimize wake time. But the default `blink_orange()` call with no args is also acceptable and simpler.

2. **LED color table in CLAUDE.md**
   - What we know: CLAUDE.md documents LED color meanings
   - Recommendation: DOC-03 (Phase 9) will update CLAUDE.md. For now, just add a comment in code.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (Docker, Python 3.13) |
| Config file | Dockerfile.test + Makefile |
| Quick run command | `make test` |
| Full suite command | `make test` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BATT-02 | Orange blink when battery_mv < BATTERY_LOW_MV | unit | `make test` (test in test_battery.py) | Needs new tests |
| BATT-02 | No warning when battery_mv == 0 (ADC failure) | unit | `make test` (test in test_battery.py) | Needs new tests |
| BATT-02 | No warning when battery_mv >= BATTERY_LOW_MV | unit | `make test` (test in test_battery.py) | Needs new tests |
| LED-03 | Warning appears after lock/unlock feedback | unit | `make test` (test in test_battery.py) | Needs new tests |

### Sampling Rate
- **Per task commit:** `make test`
- **Per wave merge:** `make test`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_battery.py` -- Add tests for low-battery warning logic (BATT-02, LED-03)
- [ ] Test must verify: (1) orange blink called when voltage < threshold, (2) no blink when voltage == 0, (3) no blink when voltage >= threshold, (4) warning appears after normal feedback

### Testing Strategy

Testing the low-battery warning requires testing `handle_button_wake()` behavior, which involves mocking multiple subsystems (WiFi, API, button press, ADC). Two approaches:

**Option A (recommended): Extract helper, test directly.**
Extract the low-battery check into a small testable function or test the conditional logic in isolation by checking that `blink_orange` is called on the LED when conditions are met.

**Option B: Integration test of handle_button_wake().**
More complex -- requires mocking `connect_wifi`, `SwitchBotController.send_command`, `measure_button_press`, `network.WLAN`, etc. Higher confidence but significantly more setup.

Recommendation: Option A -- test the conditional logic directly. The integration (placement in `handle_button_wake()`) can be verified by code review.

## Sources

### Primary (HIGH confidence)
- `main.py` -- Direct code inspection of current implementation
- `CLAUDE.md` -- ESP32 system heap constraints, LED color codes
- `tests/conftest.py` -- Test infrastructure and FakeADC stub
- `tests/test_battery.py` -- Existing battery test patterns

### Secondary (MEDIUM confidence)
- LiPo discharge curve thresholds (3.3V low warning) -- widely established in battery-powered device firmware

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- No new libraries, all components exist
- Architecture: HIGH -- Clear insertion point, 3 lines of code
- Pitfalls: HIGH -- Well-understood from existing codebase patterns and CLAUDE.md constraints

**Research date:** 2026-03-16
**Valid until:** 2026-04-16 (stable -- no external dependencies)
