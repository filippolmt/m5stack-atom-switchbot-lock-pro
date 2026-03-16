# Phase 2: Battery Voltage Reading - Research

**Researched:** 2026-03-16
**Domain:** ESP32 MicroPython ADC battery voltage reading
**Confidence:** HIGH

## Summary

Phase 2 adds a `read_battery_voltage()` function that reads the LiPo battery voltage via the ESP32 ADC on GPIO 33 (Atomic Battery Base 1:1 voltage divider) and prints it to serial output on every wake cycle. The RTC memory infrastructure for storing the voltage (`save_battery_voltage()` / `load_battery_voltage()`) was already implemented in Phase 1.

The core implementation is straightforward: create an `ADC` object on Pin 33 with 11dB attenuation, call `read_uv()` for factory-calibrated microvolts, multiply by 2 (voltage divider), convert to millivolts. The critical constraint is that ALL ADC code must execute AFTER `urequests.post()` and WiFi disconnect to avoid mbedTLS system heap fragmentation.

**Primary recommendation:** Implement a single `read_battery_voltage()` function with lazy import of `machine.ADC`, place the call in `handle_button_wake()` after `wlan.active(False)` and before LED feedback. Average 4 samples for noise reduction. Print voltage to serial and save to RTC memory.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
None -- all implementation details delegated to Claude's discretion.

### Claude's Discretion
- Serial output format (e.g., `Battery: 3850mV` or simpler)
- Number of ADC samples to average (single vs multiple for noise reduction)
- ADC attenuation setting (ADC.ATTN_11DB for full 0-3.3V range)
- Whether to save reading to RTC memory via `save_battery_voltage()` (already implemented in Phase 1)
- Voltage divider formula: `V_BAT = read_uv() * 2 / 1_000_000` (1:1 divider with 2x 1MOhm resistors)
- Test strategy for ADC (mock `machine.ADC` in conftest.py)
- Exact placement in `handle_button_wake()` -- after WiFi disconnect, before LED feedback

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| BATT-01 | Firmware legge tensione batteria via ADC su GPIO 33 (voltage divider 1:1) ad ogni ciclo wake | ADC API (`read_uv()` on Pin 33 with ATTN_11DB), voltage divider formula, lazy import pattern |
| BATT-03 | Tensione batteria stampata su seriale ad ogni wake per diagnostica | Serial print pattern with emoji prefix, millivolt format |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `machine.ADC` | MicroPython 1.24.x built-in | Read battery voltage from GPIO 33 | Only ADC API available in MicroPython. `read_uv()` uses factory eFuse calibration. |
| `machine.Pin` | MicroPython 1.24.x built-in | Configure GPIO 33 as ADC input | Already used throughout the codebase |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `machine.RTC` | Built-in | Store voltage in RTC memory | `save_battery_voltage()` already implemented in Phase 1 |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `ADC.read_uv()` | `ADC.read_u16()` + manual formula | `read_uv()` applies per-package eFuse calibration automatically; `read_u16()` requires manual calibration for accuracy |
| 4-sample average | Single sample | Single sample is noisier but simpler; 4 samples add ~negligible time and reduce noise |
| 16-sample average | 4 samples | Diminishing returns; 4 is sufficient for millivolt-level precision on a 200mAh battery monitor |

**Installation:** No new packages needed. All APIs are MicroPython built-ins.

## Architecture Patterns

### Recommended Integration Point

The ADC read fits into the existing `handle_button_wake()` flow at a specific location:

```
handle_button_wake():
  1. Measure button press
  2. CPU -> 160MHz
  3. WiFi connect
  4. NTP sync (if needed)
  5. API lock/unlock
  6. WiFi disconnect          <-- WiFi off here (line ~753)
  7. ** READ BATTERY HERE **  <-- NEW: after WiFi off, before LED feedback
  8. LED feedback blinks
  9. Return result
```

### Pattern 1: Lazy Import ADC Function
**What:** Import `machine.ADC` and `machine.Pin` inside the function body, not at module level
**When to use:** Always -- this is mandatory for mbedTLS heap safety
**Example:**
```python
# Source: Project CLAUDE.md mbedTLS constraint + MicroPython ADC docs
def read_battery_voltage():
    """Read battery voltage in mV. Call AFTER WiFi disconnect."""
    try:
        from machine import ADC, Pin
        adc = ADC(Pin(33), atten=ADC.ATTN_11DB)
        total_uv = 0
        for _ in range(4):
            total_uv += adc.read_uv()
        avg_uv = total_uv // 4
        # 1:1 voltage divider (2x 1MOhm) means ADC sees V_BAT/2
        millivolts = avg_uv * 2 // 1000
        return millivolts
    except Exception as e:
        print(f"ADC read failed: {e}")
        return 0
```

### Pattern 2: Exception Swallowing with Fallback
**What:** Wrap ADC operations in try/except, return 0 on failure
**When to use:** Hardware operations that may fail on different board revisions
**Example:** Already used throughout the codebase (see `save_battery_voltage()`, `load_wifi_config()`)

### Pattern 3: Serial Output with Emoji Prefix
**What:** Print diagnostic values with emoji prefix for quick visual scanning
**When to use:** All serial diagnostic output in this codebase
**Example:**
```python
print(f"Battery: {millivolts}mV")
```

### Anti-Patterns to Avoid
- **Module-level ADC import:** Shifts system heap layout, risks mbedTLS failure
- **ADC read before urequests.post():** Creates hardware peripheral allocation on system heap before TLS
- **ADC read while WiFi active:** RF interference degrades ADC accuracy on ESP32
- **Using ADC.read() (12-bit raw):** No calibration; use `read_uv()` instead

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| ADC voltage calibration | Manual lookup table for ADC nonlinearity | `ADC.read_uv()` | Uses factory eFuse calibration burned into each ESP32 chip |
| Byte serialization for RTC | Custom struct packing | `save_battery_voltage()` / `load_battery_voltage()` | Already implemented in Phase 1 with little-endian uint16 |

**Key insight:** Phase 1 already built the RTC memory persistence layer. Phase 2 only needs to produce the voltage value and call the existing save function.

## Common Pitfalls

### Pitfall 1: ADC Read Before WiFi Disconnect Breaks TLS
**What goes wrong:** Creating `ADC()` object allocates hardware peripheral on the ESP32 system heap. If done before `urequests.post()`, it fragments the heap and causes `MBEDTLS_ERR_MPI_ALLOC_FAILED`.
**Why it happens:** ESP32-PICO-D4 has no PSRAM; system heap is shared between WiFi/mbedTLS and hardware peripherals.
**How to avoid:** Place `read_battery_voltage()` call AFTER `wlan.active(False)` in `handle_button_wake()`.
**Warning signs:** Intermittent TLS handshake failures after adding ADC code.

### Pitfall 2: ADC Noise from WiFi RF Interference
**What goes wrong:** Reading ADC while WiFi radio is active produces noisy, inaccurate values (can be off by 50-100mV+).
**Why it happens:** 2.4GHz RF couples into the ADC analog front-end on the same silicon.
**How to avoid:** Read AFTER `wlan.disconnect()` and `wlan.active(False)`. The natural flow already disconnects WiFi before the insertion point.
**Warning signs:** Voltage readings that fluctuate wildly between wake cycles.

### Pitfall 3: ESP32 ADC Nonlinearity at Range Extremes
**What goes wrong:** ADC with 11dB attenuation is nonlinear below 150mV and above 2450mV.
**Why it happens:** Fundamental ESP32 ADC hardware limitation.
**How to avoid:** With the 1:1 divider, a full 4.2V LiPo reads as ~2.1V at the ADC pin -- well within the linear range (150mV-2450mV). A depleted 3.0V battery reads as ~1.5V -- also in range. No mitigation needed for this specific hardware.
**Warning signs:** Readings that plateau or jump at battery extremes.

### Pitfall 4: Voltage Divider Continuous Drain
**What goes wrong:** The 1M/1M resistor divider continuously draws current from the battery, even during deep sleep.
**Why it happens:** Ohm's law: I = V/(R1+R2) = 3.7V/2MOhm = 1.85uA.
**How to avoid:** With 1MOhm resistors, drain is only ~1.85uA -- acceptable compared to the ~4-11mA board-level deep sleep current noted in STATE.md. No mitigation needed.
**Warning signs:** N/A -- this is an acceptable continuous drain for this design.

## Code Examples

### Read Battery Voltage (Complete Implementation)
```python
# Source: MicroPython v1.24.0 ADC docs + project patterns
def read_battery_voltage():
    """
    Read battery voltage in millivolts from GPIO 33 (Atomic Battery Base).
    Uses lazy import to avoid system heap allocation before TLS.
    Call AFTER WiFi disconnect.
    Returns voltage in mV (e.g., 3850 for 3.85V), or 0 on failure.
    """
    try:
        from machine import ADC, Pin
        adc = ADC(Pin(33), atten=ADC.ATTN_11DB)
        total_uv = 0
        for _ in range(4):
            total_uv += adc.read_uv()
        avg_uv = total_uv // 4
        # 1:1 voltage divider (2x 1MOhm): ADC sees V_BAT / 2
        millivolts = avg_uv * 2 // 1000
        return millivolts
    except Exception as e:
        print(f"ADC read failed: {e}")
        return 0
```

### Integration in handle_button_wake()
```python
# After WiFi disconnect (existing code around line 753), before LED feedback:
    # ... existing WiFi disconnect code ...

    # Read battery voltage (safe: WiFi is off, TLS is done)
    battery_mv = read_battery_voltage()
    if battery_mv > 0:
        print(f"Battery: {battery_mv}mV")
        save_battery_voltage(battery_mv)
    else:
        print("Battery: read failed")

    # ... existing LED feedback code ...
```

### FakeADC Test Stub
```python
# Source: Project test patterns from conftest.py
class FakeADC:
    ATTN_0DB = 0
    ATTN_2_5DB = 1
    ATTN_6DB = 2
    ATTN_11DB = 3

    def __init__(self, pin, atten=0):
        self._pin = pin
        self._atten = atten
        self._uv = 1_900_000  # Default: ~3800mV battery (1.9V at divider)

    def read_uv(self):
        return self._uv
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `ADC.read()` (raw 12-bit) | `ADC.read_uv()` (calibrated microvolts) | MicroPython 1.20+ | Factory eFuse calibration, millivolt accuracy |
| `ADC(pin_number)` | `ADC(Pin(33), atten=ADC.ATTN_11DB)` | MicroPython 1.19+ | Keyword atten in constructor, cleaner API |
| `adc.atten()` separate call | `atten=` in constructor | MicroPython 1.19+ | Single-line initialization |

**Deprecated/outdated:**
- `ADC.read()` returning raw 0-4095: Still works but `read_uv()` is preferred for calibrated results
- `ADC.width()` for setting resolution: Deprecated in favor of `read_u16()` returning 16-bit normalized values

## Open Questions

1. **ADC accuracy on this specific Atomic Battery Base**
   - What we know: `read_uv()` uses eFuse calibration, 1:1 divider with 1MOhm resistors
   - What's unclear: Real-world accuracy vs multimeter on this specific board revision
   - Recommendation: Implement now, validate with multimeter during hardware testing (not a blocker for Phase 2)

2. **Whether to add a small delay after WiFi off before ADC read**
   - What we know: RF interference affects ADC; WiFi is fully off before our read point
   - What's unclear: Whether `wlan.active(False)` fully settles the RF before returning
   - Recommendation: Add a 10ms `time.sleep_ms(10)` between WiFi off and ADC read as a safety margin. Cost is negligible.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (via Docker, Python 3.13) |
| Config file | Makefile `test` target, `tests/conftest.py` for stubs |
| Quick run command | `make test` |
| Full suite command | `make test` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BATT-01 | `read_battery_voltage()` returns correct mV from ADC | unit | `make test` (pytest discovers test_battery.py) | No -- Wave 0 |
| BATT-01 | Voltage divider formula: ADC uV * 2 / 1000 = mV | unit | `make test` | No -- Wave 0 |
| BATT-01 | Lazy import of ADC inside function (not module level) | unit | `make test` | No -- Wave 0 |
| BATT-01 | ADC failure returns 0 | unit | `make test` | No -- Wave 0 |
| BATT-01 | Multiple samples averaged | unit | `make test` | No -- Wave 0 |
| BATT-03 | Voltage printed to serial on wake | integration | `make test` (capture stdout) | No -- Wave 0 |
| BATT-01 | Battery voltage saved to RTC memory | unit | `make test` | Partially (save/load roundtrip exists in test_rtc_memory.py) |

### Sampling Rate
- **Per task commit:** `make test`
- **Per wave merge:** `make test`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_battery.py` -- covers BATT-01 and BATT-03 (read_battery_voltage function tests)
- [ ] `FakeADC` class in `tests/conftest.py` -- mock for `machine.ADC` with configurable `read_uv()` return value
- [ ] No framework install needed -- pytest already configured

## Sources

### Primary (HIGH confidence)
- [MicroPython v1.24.0 machine.ADC docs](https://docs.micropython.org/en/v1.24.0/library/machine.ADC.html) -- constructor signature, `read_uv()` return type, keyword `atten` parameter
- [MicroPython v1.24.0 ESP32 Quick Reference](https://docs.micropython.org/en/v1.24.0/esp32/quickref.html) -- ADC pin assignments (ADC1: GPIO 32-39), attenuation ranges, `read_uv()` calibration notes
- Project `CLAUDE.md` -- mbedTLS heap constraints, forbidden patterns before `urequests.post()`
- Project `.planning/research/STACK.md` -- GPIO 33, 1:1 divider formula, `read_uv()` recommendation
- Project `.planning/research/PITFALLS.md` -- ADC nonlinearity, WiFi RF interference, timing constraints

### Secondary (MEDIUM confidence)
- [M5Stack Atomic Battery Base docs](https://docs.m5stack.com/en/atom/Atomic%20Battery%20Base) -- GPIO 33 ADC pin, 1M/1M voltage divider (verified in STACK.md)

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- MicroPython built-in ADC API, well-documented, verified against v1.24.0 docs
- Architecture: HIGH -- Integration point is clear (after WiFi disconnect), pattern matches existing codebase (lazy import, exception swallowing)
- Pitfalls: HIGH -- All pitfalls are documented in project history (mbedTLS heap) or ESP32 hardware docs (ADC nonlinearity, RF interference)

**Research date:** 2026-03-16
**Valid until:** 2026-04-16 (stable domain, MicroPython ADC API is mature)
