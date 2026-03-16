# Architecture Patterns

**Domain:** ESP32 MicroPython battery optimization for deep sleep wake-cycle firmware
**Researched:** 2026-03-16

## Recommended Architecture

The existing wake-cycle architecture is sound. Optimization integrates as refinements within each phase of the existing cycle, not as structural changes. The monolithic single-file approach must be preserved due to the mbedTLS system heap constraint.

### Wake Cycle Phases with Optimization Points

```
Phase 0: DEEP SLEEP (~10uA ESP32 + ~2.55uA boost converter)
    |
    v  [GPIO 39 LOW trigger]
Phase 1: BOOT & BUTTON MEASUREMENT (~80MHz, ~30-40mA without WiFi)
    |  OPT-1: Reduce LED brightness during hold measurement
    |  OPT-2: ADC battery read here (before WiFi, no heap risk)
    |  OPT-3: Low-battery abort (skip WiFi entirely if critical)
    |
    v
Phase 2: WIFI CONNECTION (~160MHz, ~80-150mA)
    |  OPT-4: Already optimized (BSSID cache, static IP)
    |  OPT-5: Reduce polling interval from 50ms (marginal)
    |
    v
Phase 3: NTP SYNC (conditional, ~100-150mA)
    |  OPT-6: Already optimized (skip if RTC valid)
    |
    v
Phase 4: API CALL via HTTPS (~100-150mA)
    |  *** mbedTLS DANGER ZONE - NO NEW ALLOCATIONS ***
    |  OPT-7: Reduce retry delay from 500ms to 300ms
    |
    v
Phase 5: WIFI DISCONNECT (~5-20mA briefly)
    |  OPT-8: Already optimized (early disconnect)
    |
    v
Phase 6: LED FEEDBACK (~5-20mA NeoPixel, ~30mA CPU at 80MHz)
    |  OPT-9: Reduce blink count and duration
    |  OPT-10: Lower LED brightness for feedback blinks
    |  OPT-11: Skip feedback entirely in ultra-low-power mode
    |
    v
Phase 7: ENTER DEEP SLEEP
    |  OPT-12: Remove 100ms serial flush delay (saves 100ms * ~30mA)
    |  OPT-13: Disable print statements (conditional compile flag)
    |
    v  [back to Phase 0]
```

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| StatusLED | RGB feedback with brightness control | Button measurement, result display |
| SwitchBotController | API authentication and HTTP POST | WiFi layer (needs active connection) |
| BatteryMonitor (NEW) | ADC reading on GPIO 33, voltage calculation | Main loop (pre-WiFi gate), LED (low-battery warning) |
| RTC Memory Cache | BSSID/channel persistence across sleep | WiFi fast reconnect |
| Power Config (NEW) | Centralized power profile settings | All components (brightness, timeouts, verbosity) |

### Data Flow for Battery Monitoring

```
Wake from deep sleep
    |
    v
ADC read GPIO 33 (11dB attenuation, 12-bit)
    |
    v
V_BAT = read_uv() * 2 / 1_000_000  (voltage divider is 1:1)
    |
    +--> V_BAT < 3.3V? --> CRITICAL: Red blink, skip WiFi, sleep immediately
    |
    +--> V_BAT < 3.5V? --> WARNING: Brief orange LED, proceed but shorter timeouts
    |
    +--> V_BAT >= 3.5V --> NORMAL: Proceed as usual
    |
    v
[Continue to button measurement]
```

**Battery voltage thresholds (Li-Ion 3.7V nominal):**
- 4.2V = Full charge
- 3.7V = ~50% capacity
- 3.5V = ~20% capacity (warning threshold)
- 3.3V = ~5% capacity (critical, risk of brownout under WiFi load)
- 3.0V = Empty (ETA9085 minimum input)

## Patterns to Follow

### Pattern 1: Pre-WiFi Battery Gate

**What:** Read battery voltage before activating WiFi. If critically low, abort and sleep to preserve remaining charge.
**When:** Every wake cycle, before Phase 2.
**Why:** WiFi draws 80-150mA. If battery is at 3.3V with 200mAh capacity, a WiFi cycle could brownout the device and corrupt flash. Better to skip and preserve enough charge for a few more attempts later (after potential charging).
**mbedTLS Safety:** SAFE. ADC read is a hardware register read, no system heap allocation.

```python
def read_battery_voltage():
    """Read battery voltage via Atomic Battery Base voltage divider on GPIO 33."""
    from machine import ADC, Pin
    adc = ADC(Pin(33))
    adc.atten(ADC.ATTN_11DB)  # 0-3.3V range
    # Voltage divider is 1:1 (two 1M ohm resistors)
    # So actual battery voltage = ADC voltage * 2
    uv = adc.read_uv()
    return uv * 2  # returns microvolts of actual battery voltage
```

**Confidence:** MEDIUM - GPIO 33 confirmed as battery ADC pin for ATOM series from M5Stack docs. The `read_uv()` method is factory-calibrated and available in MicroPython >= 1.19. Needs hardware validation.

### Pattern 2: Configurable Power Profile

**What:** A set of constants in config.py that control power behavior.
**When:** Applied at boot, no runtime overhead.
**Why:** Different users may want different tradeoffs (fast feedback vs. max battery life).
**mbedTLS Safety:** SAFE. Constants are integers loaded from config module at import time, same as existing WIFI_SSID etc.

```python
# In config.py:
# Power profile: "normal" or "power_save"
POWER_PROFILE = "power_save"

# LED brightness (0-255, default 64)
LED_BRIGHTNESS = 32  # Half of current default

# Skip LED feedback after success (saves ~400-800ms of wake time)
LED_FEEDBACK_ENABLED = True

# Enable serial logging (False saves ~1-3ms per print call)
SERIAL_LOGGING = True
```

### Pattern 3: Lazy Import with Scope Control

**What:** Import ADC and battery modules only when needed, inside the function that uses them.
**When:** For any new functionality that adds imports.
**Why:** Each module-level import shifts system heap layout, risking mbedTLS failure.
**mbedTLS Safety:** SAFE if import happens in Phase 1 (before WiFi). The system heap impact of the import will be settled before mbedTLS needs contiguous blocks.

### Pattern 4: Conditional Logging

**What:** Gate all `print()` calls behind a flag check.
**When:** When battery optimization is prioritized over debuggability.
**Why:** Each `print()` call involves UART transmission at 115200 baud. A typical wake cycle has 20-30 print statements. At ~1ms per short line, this is 20-30ms total -- marginal but adds up. More importantly, it reduces UART driver activity which has minor power implications.
**mbedTLS Safety:** SAFE. Removing print calls reduces allocations, never increases them.

```python
# At top of main.py, after config import:
try:
    from config import SERIAL_LOGGING
except ImportError:
    SERIAL_LOGGING = True

def log(msg):
    if SERIAL_LOGGING:
        print(msg)
```

**Note:** This is LOW priority. The power savings are marginal (~1-2mA for UART, 20-30ms total). Only implement if all higher-value optimizations are done.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Module-Level ADC Initialization

**What:** Creating ADC object at module level for battery reading.
**Why bad:** Adds a hardware peripheral allocation to module-level scope, shifting system heap layout. This is exactly the pattern that caused mbedTLS failures with WDT and `wlan.config(pm=0)`.
**Instead:** Lazy-initialize ADC inside a function, call it in Phase 1 before WiFi is activated.

### Anti-Pattern 2: Battery Logging to Flash

**What:** Writing battery voltage history to a file for trend analysis.
**Why bad:** Flash writes on ESP32 are slow (~10-50ms), consume power, and -- critically -- involve system heap allocations for the filesystem layer. This could fragment the heap before the HTTPS call.
**Instead:** If history is needed, store a single "last voltage" value in RTC memory (which already has a defined layout). Extend the existing 8-byte RTC layout to include 2 bytes for voltage.

### Anti-Pattern 3: WiFi Power Save Mode

**What:** Setting `wlan.config(pm=wlan.PM_POWERSAVE)` or `wlan.config(pm=0)` to reduce WiFi power during active connection.
**Why bad:** Already documented as breaking mbedTLS. WiFi power save mode changes the WiFi driver's system heap usage pattern.
**Instead:** Keep WiFi at default power settings. The wake cycle is so short (1-5s) that WiFi power save mode provides negligible benefit and high risk.

### Anti-Pattern 4: Light Sleep Between Phases

**What:** Using `machine.lightsleep()` between WiFi connect and API call to save power during idle waits.
**Why bad:** Light sleep may cause WiFi disconnection (unreliable behavior documented in MicroPython discussions). Reconnecting would double the wake time and power consumption.
**Instead:** Keep the linear synchronous flow. The phases are sequential and fast enough that light sleep between them is not worth the reconnection risk.

### Anti-Pattern 5: Multiple ADC Samples for Accuracy

**What:** Taking 10-50 ADC samples and averaging for better battery voltage accuracy.
**Why bad:** Each `read_uv()` call takes ~10-20us, so 50 samples is only ~1ms -- not a power concern. BUT: the averaging loop allocates temporary lists/values that shift heap. More importantly, single `read_uv()` with factory calibration is accurate enough for battery level thresholds (we need +/-0.1V precision, not millivolt accuracy).
**Instead:** Take 2-3 readings and use the median. Minimal allocation, sufficient accuracy.

## Optimization Safety Matrix

Each optimization rated for mbedTLS safety, power impact, and implementation risk.

| ID | Optimization | Wake Phase | mbedTLS Safe? | Power Savings | Risk | Priority |
|----|-------------|-----------|---------------|---------------|------|----------|
| OPT-1 | Lower LED brightness (64->32) | Phase 1,6 | SAFE (no heap) | ~5-15mA during blinks | None | P1 |
| OPT-2 | ADC battery read | Phase 1 | SAFE (before WiFi) | Enables low-bat abort | Low | P1 |
| OPT-3 | Low-battery abort | Phase 1 | SAFE (skips WiFi) | Saves entire WiFi cycle | Low | P1 |
| OPT-7 | Reduce retry delay 500->300ms | Phase 4 | SAFE (timing only) | 200ms * ~120mA = 24mAs | None | P2 |
| OPT-9 | Shorter LED feedback | Phase 6 | SAFE (no heap) | ~200-400ms * ~20mA | None | P1 |
| OPT-10 | Lower feedback brightness | Phase 6 | SAFE (no heap) | ~5-15mA during blinks | None | P1 |
| OPT-11 | Skip feedback (config flag) | Phase 6 | SAFE (no heap) | ~400-800ms * ~20mA | UX impact | P3 |
| OPT-12 | Remove serial flush delay | Phase 7 | SAFE (timing only) | 100ms * ~30mA = 3mAs | Debug impact | P2 |
| OPT-13 | Conditional logging | All | SAFE (reduces alloc) | ~1-2mA, 20-30ms | Debug impact | P3 |
| NEW | RTC memory battery cache | Phase 1 | SAFE (before WiFi) | Enables trend tracking | Low | P2 |

## Suggested Implementation Order

Based on dependencies between optimizations and risk/reward:

### Wave 1: Zero-Risk Quick Wins (no mbedTLS concern)
1. **OPT-1 + OPT-10: LED brightness reduction** - Change `brightness=64` default to `brightness=32` or make configurable via config.py. Single constant change.
2. **OPT-9: Shorter LED feedback** - Reduce blink counts and durations. Pure timing changes.
3. **OPT-12: Remove serial flush delay** - Change `time.sleep_ms(100)` to `time.sleep_ms(10)` or remove in `enter_deep_sleep()`.

**Dependency:** None. These are independent changes.

### Wave 2: Battery Monitoring Foundation
4. **OPT-2: ADC battery read** - Add `read_battery_voltage()` function with lazy ADC import. Must be called in Phase 1 before WiFi activation.
5. **OPT-3: Low-battery abort** - Add voltage threshold check after OPT-2. Requires OPT-2.
6. **RTC memory extension** - Extend 8-byte layout to 10 bytes: add 2 bytes for last battery voltage (millivolts as uint16). Requires OPT-2.

**Dependency:** OPT-3 depends on OPT-2. RTC extension depends on OPT-2.

### Wave 3: Configurable Power Profile
7. **Power profile in config.py** - Add `LED_BRIGHTNESS`, `LED_FEEDBACK_ENABLED`, `POWER_PROFILE` constants with try/except import (backward compatible).
8. **OPT-7: Reduce retry delay** - Make retry delay configurable or reduce default.
9. **OPT-13: Conditional logging** - Add `log()` wrapper function, gate existing `print()` calls.

**Dependency:** Wave 3 items are independent of each other but benefit from Wave 1+2 being stable.

### Wave 4: Advanced (only if needed)
10. **OPT-11: Skip feedback entirely** - Config flag to disable LED feedback for maximum battery life.
11. **Autonomy estimation** - Calculate and log estimated remaining battery life based on voltage + usage pattern.

## RTC Memory Layout Extension

Current layout (8 bytes):
```
Byte 0-5: BSSID (6 bytes)
Byte 6:   WiFi channel (1 byte)
Byte 7:   Valid flag (0xAA)
```

Proposed layout (12 bytes, backward compatible):
```
Byte 0-5:  BSSID (6 bytes)
Byte 6:    WiFi channel (1 byte)
Byte 7:    Valid flag (0xAA for WiFi-only, 0xBB for WiFi+battery)
Byte 8-9:  Last battery voltage in mV, uint16 big-endian (0-65535)
Byte 10:   Wake counter (0-255, wraps, for usage tracking)
Byte 11:   Reserved
```

**Backward compatibility:** If byte 7 is 0xAA (old format), only read bytes 0-7. If 0xBB (new format), read all 12 bytes. Old firmware reading new data sees 0xBB as invalid flag and falls back to no-cache, which is safe.

## Power Budget Analysis

### Current Wake Cycle (typical fast reconnect)

| Phase | Duration | Current (3.3V) | Energy (mAs) |
|-------|----------|----------------|--------------|
| Boot + button (80MHz) | ~200ms | ~35mA | 7.0 |
| WiFi connect (160MHz, fast) | ~1500ms | ~120mA | 180.0 |
| NTP (skipped) | 0ms | 0mA | 0.0 |
| API call (160MHz) | ~800ms | ~120mA | 96.0 |
| WiFi disconnect | ~50ms | ~20mA | 1.0 |
| LED feedback | ~800ms | ~25mA | 20.0 |
| Serial flush | ~100ms | ~30mA | 3.0 |
| **Total** | **~3450ms** | | **307 mAs** |

### Optimized Wake Cycle (after all Wave 1+2 changes)

| Phase | Duration | Current (3.3V) | Energy (mAs) | Change |
|-------|----------|----------------|--------------|--------|
| Boot + button + ADC (80MHz) | ~220ms | ~35mA | 7.7 | +0.7 (ADC read) |
| WiFi connect (160MHz, fast) | ~1500ms | ~120mA | 180.0 | unchanged |
| NTP (skipped) | 0ms | 0mA | 0.0 | unchanged |
| API call (160MHz) | ~800ms | ~120mA | 96.0 | unchanged |
| WiFi disconnect | ~50ms | ~20mA | 1.0 | unchanged |
| LED feedback (dimmer, shorter) | ~400ms | ~18mA | 7.2 | -12.8 |
| Serial flush (reduced) | ~10ms | ~30mA | 0.3 | -2.7 |
| **Total** | **~2980ms** | | **292.2 mAs** | **-4.8%** |

### Autonomy Estimate

With 200mAh battery at 3.7V, boosted to 5V (ETA9085 ~85% efficiency):
- Usable capacity: 200mAh * 3.7V / 5V / 0.85 = ~104mAh at 5V rail (conservative)
- But ESP32 runs at 3.3V from LDO, so effective: ~200mAh * 0.85 = ~170mAh usable
- Deep sleep drain: ~12.55uA (10uA ESP32 + 2.55uA boost converter)
- Standby life (no presses): 170mAh / 0.01255mA = ~13,545 hours = ~564 days
- Per wake cycle (optimized): 292.2 mAs = 0.081 mAh
- At 10 presses/day: 0.81 mAh/day active + 0.30 mAh/day standby = 1.11 mAh/day
- **Estimated autonomy: ~153 days** (10 presses/day, optimized)
- Current (pre-optimization): 307 mAs/cycle = 0.085 mAh, 0.85 + 0.30 = 1.15 mAh/day = ~148 days

The power savings from firmware optimization alone are modest (~3-5% improvement) because WiFi dominates the power budget. The biggest lever is reducing wake time (fewer/shorter WiFi cycles), not reducing current during wake.

## Key Architectural Insight

**WiFi is 92% of the energy budget per wake cycle.** All non-WiFi optimizations combined save less than 5% of total energy. The highest-value optimization is anything that avoids a WiFi cycle entirely:

1. **Low-battery abort** (OPT-3): Saves 100% of a WiFi cycle when battery is critical
2. **Hypothetical: BLE instead of WiFi** (out of scope but noted): BLE uses 10-30mA vs WiFi's 80-150mA
3. **Reducing WiFi connect time** further: Already well-optimized with BSSID cache + static IP

The LED and logging optimizations are worth doing because they are zero-risk and every milliamp-second counts with a 200mAh battery, but expectations should be calibrated: the real wins are in avoiding unnecessary WiFi cycles.

## Sources

- [M5Stack Atomic Battery Base docs](https://docs.m5stack.com/en/atom/Atomic%20Battery%20Base) - GPIO 33 ADC pin, voltage divider circuit (MEDIUM confidence)
- [MicroPython ESP32 Quick Reference - ADC](https://docs.micropython.org/en/latest/esp32/quickref.html) - ADC API, read_uv(), attenuation (HIGH confidence)
- [MicroPython Discussion #10153](https://github.com/orgs/micropython/discussions/10153) - Boot optimization from deep sleep (MEDIUM confidence)
- [MicroPython Discussion #12092](https://github.com/orgs/micropython/discussions/12092) - Light sleep vs deep sleep WiFi behavior (MEDIUM confidence)
- [Adafruit NeoPixel Power Guide](https://learn.adafruit.com/adafruit-neopixel-uberguide/powering-neopixels) - Single pixel up to 60mA at full white (HIGH confidence)
- [ESP-IDF Low Power WiFi Guide](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-guides/low-power-mode/low-power-mode-wifi.html) - WiFi power modes (MEDIUM confidence, ESP-IDF not MicroPython)
- [PJRC WS2812 Current Measurements](https://www.pjrc.com/how-much-current-do-ws2812-neopixel-leds-really-use/) - Actual current measurements per pixel (HIGH confidence)

---

*Architecture analysis: 2026-03-16*
