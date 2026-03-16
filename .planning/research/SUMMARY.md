# Project Research Summary

**Project:** M5Stack ATOM SwitchBot Lock Pro — Battery Optimization Milestone
**Domain:** ESP32 MicroPython embedded IoT firmware (deep sleep, HTTPS, 200mAh LiPo)
**Researched:** 2026-03-16
**Confidence:** MEDIUM (HIGH for constraints, MEDIUM for battery life projections)

## Executive Summary

This milestone adds battery monitoring and power optimization to an existing, working MicroPython firmware for the M5Stack ATOM Lite. The codebase already implements the correct high-level power strategy (deep sleep + wake-on-button, fast WiFi reconnect via BSSID cache, NTP skip, early WiFi disconnect). Research confirms this architecture is sound and should not be restructured. The most critical finding is that the documented ~10uA deep sleep current is the bare ESP32 spec — the actual M5Stack ATOM Lite board draws 4-11mA in deep sleep due to a permanently-on USB/serial chip, NeoPixel quiescent current, and LDO losses. This single fact invalidates the ~126-day battery life estimate in STACK.md and replaces it with a realistic 12-40 hour range, dominated almost entirely by sleep current.

The recommended approach is three-phased: first, implement battery monitoring (ADC read on GPIO 33 after WiFi disconnect, low-battery warning, graceful shutdown threshold); second, apply zero-risk quick wins (LED brightness reduction, shorter blink durations, remove serial flush delay); third, add configurable power profiles and conditional logging. The primary value of this milestone is giving users battery state visibility so they know when to recharge — software optimizations can at best push battery life from ~21 hours to ~23 hours because the dominant drain (USB/serial chip hardware) cannot be addressed in firmware.

The overriding risk throughout all changes is mbedTLS system heap fragmentation. The ESP32-PICO-D4 shares a single system heap between the WiFi driver and TLS stack. Any new allocation — ADC object creation, extra imports, global variables, hardware peripheral setup — that happens before `urequests.post()` can cause `MBEDTLS_ERR_MPI_ALLOC_FAILED`. This project has already been burned by this issue multiple times (WDT, gc.collect(), wlan.config(pm=0), extra imports). Every code change must be evaluated against this constraint first. The safe execution order is: battery read AFTER WiFi disconnect, lazy imports inside functions, no new module-level allocations.

## Key Findings

### Recommended Stack

No new external libraries are needed. All battery monitoring uses built-in MicroPython modules: `machine.ADC` on GPIO 33 (ADC1, safe with WiFi), `ADC.read_uv()` for factory-calibrated readings, `ADC.ATTN_11DB` for the 150mV-2450mV range that covers V_BAT/2 with the existing 1M/1M voltage divider. RTC memory (512 bytes available, only 8 currently used) can be extended to cache battery voltage across deep sleep cycles. The Nordic PPK2 (~$90) is the recommended development tool for measuring actual current at the battery terminals across the full deep sleep to WiFi-active range.

**Core technologies:**
- `machine.ADC` (GPIO 33, built-in): Battery voltage via 1M/1M divider on Atomic Battery Base — only ADC1 pins are safe when WiFi is active
- `ADC.read_uv()` (MicroPython 1.20+): Factory-calibrated uV reading — more accurate than raw reads, handles ESP32 ADC nonlinearity partially
- `machine.RTC` / raw RTC memory (built-in): Extend existing 8-byte layout to 12 bytes to cache battery voltage (mV) and wake counter
- Nordic PPK2 (development tool, ~$90): 100nA–1A range covers both deep sleep and WiFi burst current in a single trace

### Expected Features

**Must have (table stakes):**
- Battery voltage reading via ADC on GPIO 33 — foundation for all battery features; Atomic Battery Base exposes GPIO 33 with 1M/1M divider
- Low-battery warning LED on wake — users WILL encounter dead batteries with 12-40h runtime; they need advance notice
- Graceful low-battery shutdown — refuse WiFi operation below 3.3V to prevent LiPo deep discharge and flash corruption from brownout

**Should have (quick wins with measurable benefit):**
- LED brightness reduction (64 -> 24-32) — trivial single-constant change, reduces active current during blinks
- Shorter LED feedback blinks — reduce blink count and duration; saves ~400ms of NeoPixel draw per press
- WiFi channel caching fix — byte 6 of RTC memory already stores the channel but is never passed to `wlan.connect()`; passing it saves ~100ms per reconnect
- Wake counter in RTC memory — 4 lines of code, useful for diagnostics and estimating per-press energy consumption
- Remove serial flush delay — `time.sleep_ms(100)` before deep sleep saves ~3mAs per press

**Defer (v2+ or skip entirely):**
- Battery percentage estimation — non-linear LiPo curve + ESP32 ADC nonlinearity makes this unreliable without hardware calibration; raw voltage thresholds are more honest
- USB power detection — only needed if false low-battery warnings on USB become a user complaint
- Adaptive LED feedback — only saves power during the <1% active fraction; not worth code complexity
- OTA updates, web config portal, BLE, periodic heartbeat — all explicitly anti-features given the 200mAh constraint

### Architecture Approach

The existing single-file monolithic architecture in `main.py` must be preserved. The mbedTLS system heap constraint makes any refactoring that moves imports to module level potentially fatal for TLS. Optimizations integrate as targeted refinements within the existing 7-phase wake cycle (Boot, Button measurement, WiFi, NTP, API call, WiFi disconnect, LED feedback, Deep sleep). A new `BatteryMonitor` logical component handles ADC reads and threshold decisions, but it must be implemented as functions within `main.py` using lazy imports, not as a separate module.

**Major components:**
1. **StatusLED** (existing) — add brightness configurability via config.py constant; reduce default brightness and blink durations
2. **BatteryMonitor** (new, implemented inline) — ADC GPIO 33 read AFTER WiFi disconnect, voltage-to-threshold comparison, low-battery abort path, RTC memory caching of last voltage
3. **RTC Memory Cache** (extend existing) — expand 8-byte WiFi cache to 12 bytes: add uint16 battery voltage (mV, big-endian) at bytes 8-9, wake counter at byte 10, reserved byte 11
4. **Power Config** (new constants in config.py) — `LED_BRIGHTNESS`, `LED_FEEDBACK_ENABLED`, `POWER_PROFILE` as optional config.py additions with try/except fallback defaults
5. **SwitchBotController** (existing, unchanged) — must not be touched; any change before `urequests.post()` risks TLS failure

### Critical Pitfalls

1. **mbedTLS system heap fragmentation** — Any code added before `urequests.post()` that allocates on the system heap (ADC init, extra imports, global vars, hardware peripheral setup, gc.collect()) will cause intermittent or consistent `MBEDTLS_ERR_MPI_ALLOC_FAILED`. Mitigation: ADC reads MUST happen after WiFi disconnect; all new imports must be lazy (inside functions); test every change with 20+ consecutive cycles.

2. **Board-level deep sleep current is 4-11mA, not 10uA** — The USB/serial chip on ATOM Lite cannot be disabled in software and dominates sleep current. Any battery life calculation using the ESP32 datasheet sleep current (10uA) will be off by 400-1100x. Mitigation: measure at battery terminals with PPK2 before quoting any battery life figure.

3. **ADC reading while WiFi is active gives wrong values** — ESP32 WiFi radio introduces RF noise into ADC readings. ADC2 pins are completely blocked by WiFi; ADC1 pins (GPIO 32-39) are less affected but still noisy during active transmission. Mitigation: always read battery voltage AFTER `wlan.active(False)`, wait 10-50ms for RF to settle.

4. **ESP32 ADC nonlinearity** — The ESP32 ADC with 11dB attenuation is effectively 9 bits of signal with 3 bits of noise. `read_uv()` applies factory eFuse calibration which helps at mid-range but does not fix nonlinearity at extremes. Mitigation: use 2-3 sample median (not 10+ samples), report voltage thresholds not percentages, compare against multimeter readings to validate.

5. **RTC memory corruption at low battery** — Brown-out events during WiFi TX at low voltage can corrupt RTC memory (BSSID cache). The current 0xAA flag byte may not catch all corruption. Mitigation: add voltage gate before trusting RTC cache; invalidate cache when V_BAT < 3.3V; optionally add CRC8 in the reserved byte 11.

## Implications for Roadmap

### Phase 1: Battery Monitoring Foundation
**Rationale:** Battery monitoring is the prerequisite for all other battery-related features AND the highest-user-value deliverable. Without it, users have no visibility into a device that lasts only 12-40 hours. This phase must come first because all subsequent phases (warnings, shutdown, power profiling) depend on having a reliable voltage reading.
**Delivers:** `read_battery_voltage()` function, low-battery warning LED (orange blink on wake when V_BAT < 3.5V), graceful shutdown path (red blink + skip WiFi when V_BAT < 3.3V), battery voltage cached in RTC memory (bytes 8-9)
**Addresses:** Table stakes features — battery voltage reading, low-battery warning, graceful shutdown
**Avoids:** Pitfall 1 (mbedTLS) — ADC read placed AFTER WiFi disconnect; Pitfall 3 (ADC while WiFi active); lazy import pattern enforced

### Phase 2: LED and Timing Quick Wins
**Rationale:** These changes are zero heap impact (pure constant and timing changes), independent of Phase 1, and require no new imports. They are grouped together because they share the same risk level (none) and touch the same code areas (StatusLED, sleep entry). Can be done in parallel with Phase 1 planning but should be committed separately for clean git history.
**Delivers:** LED brightness reduced (64 -> 32 default), blink durations halved, serial flush delay removed (100ms -> 10ms or removed), `LED_BRIGHTNESS` constant added to config.py
**Addresses:** Differentiator features — LED brightness reduction, shorter feedback blinks
**Avoids:** Pitfall 1 (these changes have no heap impact) — confirm by running mbedTLS safety checklist after each change

### Phase 3: WiFi and RTC Cache Improvements
**Rationale:** The WiFi channel caching fix (passing byte 6 to `wlan.connect()`) is a genuine improvement with ~100ms savings and zero risk. The RTC memory layout extension (wake counter, battery voltage cache) enables diagnostics and persistence of battery state across cycles. These are grouped because both touch RTC memory handling and WiFi connect code.
**Delivers:** `wlan.connect(ssid, password, channel=cached_channel)` fix, extended RTC layout to 12 bytes with backward-compatible flag (0xBB vs 0xAA), wake counter at byte 10
**Addresses:** Differentiator features — WiFi channel caching, press counter
**Avoids:** Pitfall 11 (RTC corruption) — add voltage gate to invalidate cache at low battery

### Phase 4: Configurable Power Profile
**Rationale:** Power profile configuration gives advanced users control over tradeoffs without changing firmware. This comes last because it wraps the constants established in Phases 1-3 into a cohesive config.py interface. Conditional logging is low-value but rounds out the phase.
**Delivers:** `POWER_PROFILE`, `LED_FEEDBACK_ENABLED` constants in config.py with try/except backward-compatible imports; optional `log()` wrapper function gating all `print()` calls; `LED_FEEDBACK_ENABLED = False` path skipping LED blinks entirely
**Addresses:** Differentiator features — adaptive LED feedback, configurable power modes
**Avoids:** Pitfall 1 — try/except config imports settled before mbedTLS zone; conditional logging reduces allocations, never increases them

### Phase Ordering Rationale

- Phase 1 must come first: battery monitoring is both the highest-value deliverable and the prerequisite for low-battery warnings in all subsequent phases.
- Phase 2 can be parallelized with Phase 1 in branches but should be merged first — it is pure refactoring with no dependencies and establishes stable baselines before Phase 1 adds new code paths.
- Phase 3 requires Phase 1 to be stable (RTC layout extension builds on the voltage caching introduced in Phase 1).
- Phase 4 is a configurability wrapper and should come last, after all concrete behaviors are locked in.
- The mbedTLS constraint enforces a strict code ordering within each phase: new code that might affect the system heap must be placed after `urequests.post()` in the call graph, not before.

### Research Flags

Phases likely needing deeper research or hardware validation during implementation:
- **Phase 1:** GPIO 33 ADC on the specific Atomic Battery Base + ATOM Lite combination needs hardware validation. The 1M/1M voltage divider is documented but `read_uv()` accuracy across the 3.0-4.2V range on this exact hardware is unverified. Measure against a multimeter before shipping.
- **Phase 1:** The 3.3V shutdown threshold needs real-world calibration. Under WiFi load, battery voltage sags significantly; a reading of 3.3V at rest may correspond to brownout conditions under 120mA WiFi draw.
- **Phase 3:** WiFi channel parameter behavior in MicroPython's `wlan.connect()` is not exhaustively documented. Test on hardware that the channel hint is actually used and does not cause connection failures on channel changes.

Phases with standard patterns (no additional research needed):
- **Phase 2:** Pure constant and timing changes — no uncertainty, standard patterns, well-understood risk profile.
- **Phase 4:** try/except config import pattern is already used in the codebase for `WIFI_STATIC_IP`. Same pattern applies directly.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All APIs are MicroPython built-ins with stable documentation. No new libraries needed. ADC GPIO 33 confirmed by M5Stack official docs. |
| Features | HIGH | Board-level sleep current measurements are from multiple independent community sources. Feature prioritization is well-supported by the math. The anti-features list is definitive. |
| Architecture | MEDIUM | Wake cycle phases and mbedTLS constraint are HIGH confidence. Specific ADC placement (post-WiFi) and RTC layout extension are sound but need hardware smoke-testing. Power budget numbers are estimates, not measurements. |
| Pitfalls | HIGH | mbedTLS constraint is confirmed by project history. ESP32 ADC nonlinearity and ADC/WiFi conflict are documented hardware limitations. Board sleep current has multiple community confirmations. |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **Actual board sleep current:** The 4-11mA range from community reports needs measurement on this specific unit (ATOM Lite + Atomic Battery Base combination). Use PPK2 before finalizing battery life claims or warning thresholds.
- **ADC accuracy calibration:** Compare `read_uv()` readings against a known-good multimeter across 3.0-4.2V range. If error exceeds 100mV, adjust voltage thresholds accordingly or add a calibration offset constant in config.py.
- **mbedTLS safety of post-WiFi ADC read:** The architecture research states ADC reads after WiFi disconnect are safe. This has not been empirically tested on this specific firmware. Run 50+ consecutive cycles after adding the ADC read to confirm no new TLS failures.
- **WiFi channel param in wlan.connect():** MicroPython docs mention channel as a `wlan.connect()` parameter but behavior with stale/wrong channel hints is not documented. Test fallback behavior.

## Sources

### Primary (HIGH confidence)
- [M5Stack Atomic Battery Base documentation](https://docs.m5stack.com/en/atom/Atomic%20Battery%20Base) — GPIO 33 ADC pin, 1M/1M voltage divider, ETA9085E10 specs
- [MicroPython ESP32 Quick Reference v1.24.0](https://docs.micropython.org/en/v1.24.0/esp32/quickref.html) — ADC API, sleep modes, pin assignments
- [MicroPython machine.ADC class](https://docs.micropython.org/en/latest/library/machine.ADC.html) — `read_uv()`, attenuation constants
- [ESP-IDF ADC Documentation](https://docs.espressif.com/projects/esp-idf/en/v4.4/esp32/api-reference/peripherals/adc.html) — ADC2/WiFi conflict

### Secondary (MEDIUM confidence)
- [M5Stack ATOM deep sleep high current — GitHub Issue #13](https://github.com/m5stack/M5Atom/issues/13) — 4-11mA board sleep current measurements
- [M5Stack Community — Deep sleep high current on Atom](https://community.m5stack.com/topic/3188/deep-sleep-high-current-on-atom) — corroborating community measurements
- [ESP32 Forum — ADC Non-linear Issues](https://www.esp32.com/viewtopic.php?t=2881) — ADC nonlinearity documentation
- [ESP-IDF Low Power Mode in Wi-Fi Scenarios](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-guides/low-power-mode/low-power-mode-wifi.html) — WiFi PM and packet loss risk
- [MicroPython Discussion #10153](https://github.com/orgs/micropython/discussions/10153) — boot overhead from deep sleep
- [Nordic Power Profiler Kit II](https://www.nordicsemi.com/Products/Development-hardware/Power-Profiler-Kit-2) — PPK2 specifications

### Tertiary (LOW confidence — needs hardware validation)
- Battery life estimates (all scenarios) — based on unverified board sleep current range; treat as order-of-magnitude only until PPK2 measurement confirms actual sleep draw
- ADC voltage-to-percentage lookup table — standard LiPo curve may shift under ETA9085E10 boost converter load; requires calibration against real discharge cycles

---
*Research completed: 2026-03-16*
*Ready for roadmap: yes*
