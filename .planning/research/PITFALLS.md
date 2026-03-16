# Domain Pitfalls

**Domain:** ESP32 MicroPython battery optimization (200mAh, deep sleep, HTTPS)
**Researched:** 2026-03-16

## Critical Pitfalls

Mistakes that cause rewrites, bricked TLS, or dramatically wrong battery life estimates.

### Pitfall 1: mbedTLS System Heap Fragmentation from "Innocent" Optimizations

**What goes wrong:** Any new allocation on the ESP32 system heap before `urequests.post()` breaks TLS handshakes. This project has already been burned by this — WDT, `gc.collect()` before POST, module-level caching, extra imports, and `wlan.config(pm=0)` all caused `MBEDTLS_ERR_MPI_ALLOC_FAILED`. Battery optimization work will naturally tempt developers to add new code paths (ADC reads, voltage calculations, power mode changes) that shift the system heap layout.

**Why it happens:** The ESP32-PICO-D4 has no PSRAM. The system heap (invisible to Python's `gc.mem_free()`) is shared between WiFi driver and mbedTLS. mbedTLS needs large contiguous blocks for RSA operations. Any allocation that fragments this space kills TLS.

**Consequences:** Intermittent or consistent HTTPS failures. The failure mode is insidious: it may work 9 out of 10 times, then fail under slightly different heap conditions. Debugging is extremely difficult because `gc.mem_free()` shows plenty of memory.

**Prevention:**
- ALL new code that runs before `urequests.post()` must be reviewed for system heap impact
- ADC battery reads MUST happen AFTER the API call, never before
- No new module-level imports, no new global variables, no new hardware initializations before POST
- Test every change with at least 20 consecutive wake-lock-sleep cycles to catch intermittent failures
- Keep a "known working" firmware snapshot to revert to when TLS breaks

**Detection:** `MBEDTLS_ERR_MPI_ALLOC_FAILED` (-17040), `MBEDTLS_ERR_RSA_PUBLIC_FAILED`, or `MBEDTLS_ERR_PK_INVALID_PUBKEY` in serial output. May appear only after several cycles.

**Phase relevance:** Every phase. This constraint must be the first check on every code change.

**Confidence:** HIGH — confirmed by project history, documented in CLAUDE.md.

---

### Pitfall 2: Boost Converter Quiescent Current Dominates Battery Life in Deep Sleep

**What goes wrong:** Developers calculate battery life based on ESP32 deep sleep current (~10uA) and get wildly optimistic estimates. In reality, the ETA9085E10 boost converter's standby current (2.55uA per datasheet, but real-world is often higher) plus the USB-to-serial chip on the M5Stack ATOM Lite add significant parasitic drain. The ATOM Lite's USB/serial chip (likely CH552 or similar) cannot be disabled and draws current even with no USB connected.

**Why it happens:** Battery life math uses `capacity / sleep_current` but ignores:
1. Boost converter quiescent current (2.55uA datasheet, possibly 10-50uA real-world)
2. USB-to-serial chip leakage (reported 1-11mA on M5Stack ATOM boards in community forums)
3. NeoPixel WS2812 standby current (~0.5-1mA even when "off" on some boards)
4. Voltage divider continuous drain if battery monitoring resistors are always connected
5. Boost converter efficiency losses during active periods (~85-90% means 10-15% wasted)

**Consequences:** Predicted battery life of "months" turns into days or weeks. Users lose trust in the optimization work.

**Prevention:**
- Measure ACTUAL deep sleep current with a precision ammeter (uCurrent Gold or similar) at the battery terminals, not at the ESP32 VCC
- Account for ALL components: ESP32 + boost converter + USB chip + NeoPixel + any voltage divider
- Use measured values in battery life calculations, never datasheet values alone
- If USB chip draws >1mA during sleep, that alone limits a 200mAh battery to ~200 hours (~8 days) regardless of ESP32 optimizations

**Detection:** Measure deep sleep current at battery terminals. If it is over 100uA, something besides the ESP32 is drawing power.

**Phase relevance:** Battery monitoring phase (must measure before optimizing), and autonomy estimation phase.

**Confidence:** MEDIUM — M5Stack community reports vary; the specific ATOM Lite + Atomic Battery Base combination needs real measurement.

**Sources:**
- [Deep sleep high current on Atom - M5Stack Community](https://community.m5stack.com/topic/3188/deep-sleep-high-current-on-atom)
- [Deep sleep current too high - M5Atom GitHub](https://github.com/m5stack/M5Atom/issues/13)

---

### Pitfall 3: ESP32 ADC Nonlinearity Makes Battery Percentage Unreliable

**What goes wrong:** The ESP32 ADC is notoriously nonlinear, especially at the extremes of its range with 11dB attenuation. Developers read raw ADC values, apply a linear voltage divider formula, and get battery percentages that jump around, show 80% then suddenly drop to 20%, or read 0% when the battery still has charge.

**Why it happens:**
- With 11dB attenuation, linearity degrades above ~2.6V and below ~0.15V
- The ESP32 ADC is effectively 9 bits of signal + 3 bits of noise (not true 12-bit)
- Factory eFuse calibration helps but does not fix the fundamental nonlinearity
- LiPo discharge curves are themselves nonlinear (flat in the middle, steep at ends)
- Single-sample reads are noisy; WiFi activity on ADC2 pins causes additional interference

**Consequences:** Battery level indicator is misleading. User sees "60%" and then the device dies 10 minutes later, or sees "10%" and the device lasts another week.

**Prevention:**
- Use `ADC.read_uv()` instead of `ADC.read()` — it applies factory calibration automatically
- Use only ADC1 pins (GPIO 32-39) — ADC2 conflicts with WiFi
- Take multiple samples (8-16) and average to reduce noise
- Apply a LiPo discharge curve lookup table (not linear interpolation) for percentage
- Read voltage AFTER WiFi is disconnected to avoid RF interference on ADC
- Consider reporting raw voltage instead of percentage — it is more honest
- Keep the measured voltage in the "sweet spot" of 150mV-2450mV via appropriate voltage divider ratios

**Detection:** Compare ADC readings against a known-good multimeter across the full battery range (4.2V to 3.0V). If readings deviate more than 5%, calibration is needed.

**Phase relevance:** Battery monitoring implementation phase.

**Confidence:** HIGH — well-documented ESP32 ADC limitation.

**Sources:**
- [ESP32 ADC Non-linear Issues - ESP32 Forum](https://www.esp32.com/viewtopic.php?t=2881)
- [MicroPython ESP32 Quick Reference - ADC](https://docs.micropython.org/en/latest/esp32/quickref.html)

---

### Pitfall 4: WiFi Power Save Mode Breaks HTTPS/TLS

**What goes wrong:** The project already discovered that `wlan.config(pm=0)` (WiFi PS_NONE, which disables power saving) breaks TLS by increasing WiFi driver system heap usage. But the opposite is also dangerous: aggressive WiFi power save modes (modem sleep with high DTIM intervals) can cause packet loss during TLS handshakes, leading to connection timeouts or corrupted handshakes.

**Why it happens:** WiFi modem sleep powers down the radio between beacon intervals. During a TLS handshake, multiple round-trips happen in quick succession. If the radio is asleep when a server response arrives, the packet is lost. Maximum modem sleep can miss broadcast data entirely.

**Consequences:** Intermittent TLS handshake failures that look like network issues. The device wastes MORE power retrying failed connections than it would have saved with power save mode.

**Prevention:**
- Do NOT change WiFi power management settings at all — the current default works and any change risks heap or TLS issues
- Keep WiFi active time as short as possible instead: connect, POST, disconnect immediately
- The current "early WiFi disconnect" pattern is the correct approach — minimize time connected rather than trying to reduce power while connected
- If WiFi power save must be explored, test with at least 100 consecutive wake cycles

**Detection:** Increased rate of `OSError` or timeout exceptions from `urequests.post()`. Connection succeeds but TLS handshake times out.

**Phase relevance:** Any phase that touches WiFi code.

**Confidence:** HIGH — ESP-IDF documentation confirms modem sleep packet loss risk; project history confirms heap issues with PM settings.

**Sources:**
- [ESP-IDF Low Power Mode in Wi-Fi Scenarios](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-guides/low-power-mode/low-power-mode-wifi.html)

---

## Moderate Pitfalls

### Pitfall 5: NeoPixel (WS2812) Draws Current Even When "Off"

**What goes wrong:** The WS2812 NeoPixel on GPIO 27 has a quiescent current of ~0.5-1mA even when displaying black (all LEDs off). On a 200mAh battery, 1mA of continuous NeoPixel drain alone limits battery life to ~200 hours (~8 days), completely overshadowing the ESP32's 10uA deep sleep current.

**Why it happens:** The WS2812 has an internal controller IC that draws standby current from its VCC pin regardless of the data line state. The M5Stack ATOM Lite has the NeoPixel permanently wired to the 3.3V rail — there is no way to power-gate it in software.

**Prevention:**
- Ensure NeoPixel data line is set to output LOW before entering deep sleep (sends "all off" frame)
- Use `gpio_hold` to keep the data pin LOW during deep sleep (prevents floating pin from accidentally triggering the WS2812)
- Measure actual NeoPixel standby current for this specific board — it varies by component revision
- Consider hardware modification (MOSFET on NeoPixel VCC) only if measured current is significant and software mitigation insufficient
- Minimize LED ON time during active cycles — current blink durations should be as short as perceptible

**Detection:** Measure current with and without the NeoPixel data line held LOW. If deep sleep current drops noticeably, the NeoPixel was part of the problem.

**Phase relevance:** LED optimization phase, deep sleep current measurement phase.

**Confidence:** MEDIUM — WS2812 standby current is documented; specific M5Stack ATOM Lite NeoPixel behavior needs measurement.

**Sources:**
- [Best solution for ESP32 + Neopixel and battery life - ESP32 Forum](https://www.esp32.com/viewtopic.php?t=9029)

---

### Pitfall 6: Voltage Divider for Battery Monitoring Drains the Battery

**What goes wrong:** A simple resistive voltage divider for ADC battery monitoring continuously leaks current through the resistor network, even during deep sleep. With typical 100K/100K resistors and a 3.7V battery, the divider draws ~18.5uA continuously — nearly double the ESP32's deep sleep current.

**Why it happens:** Ohm's law. A voltage divider is always conducting. Developers design for ADC range compatibility and forget about continuous current draw.

**Prevention:**
- Use high-value resistors (1M/1M minimum, preferably 10M/10M if ADC input impedance allows)
- Better: use a GPIO to enable/disable the voltage divider via a MOSFET — read only when needed, then cut power
- Best: check if the Atomic Battery Base already has a voltage divider on a known pin (check the schematic) before adding external components
- If the M5Stack ATOM Lite exposes GPIO 35 (which is input-only and connected to some battery bases), try reading it first
- Add a large capacitor (100nF) at the ADC input to stabilize readings when using high-value resistors

**Detection:** Calculate: `V_battery / (R1 + R2)` gives continuous current. Compare against ESP32 deep sleep current. If divider current exceeds 10uA, it is a significant parasitic load.

**Phase relevance:** Battery monitoring hardware design phase.

**Confidence:** HIGH — basic electronics; applies universally.

---

### Pitfall 7: Battery Life Estimates Ignore Active Duty Cycle Correctly

**What goes wrong:** Developers calculate battery life as `capacity / sleep_current` and get months of runtime, then are surprised when the battery dies in weeks. The active-period current (80-150mA for 1-5 seconds) is substantial. With 10 presses/day at 3 seconds average and 120mA, that is 1mAh/day from active use alone — small compared to sleep drain, but non-trivial.

**Why it happens:** The duty cycle math is often done wrong:
- Forgetting to account for boost converter efficiency losses (divide active current by 0.85-0.90)
- Not counting WiFi scan failures (full scan = 10-30 seconds at 120mA)
- Ignoring first-boot vs subsequent-boot differences (first boot is 3-5x longer)
- Not factoring in API retries

**Prevention:**
- Use the full formula: `battery_life = capacity / (sleep_current + (active_current * active_time * presses_per_day / 86400))`
- Apply boost converter efficiency: `real_current = measured_current / efficiency`
- Model worst-case scenario separately: all presses are cold-start (no BSSID cache), every press requires retry
- Include self-discharge of LiPo cells (~3-5% per month)

**Detection:** Track actual battery voltage over time and compare against predicted curve.

**Phase relevance:** Autonomy estimation phase.

**Confidence:** HIGH — mathematical certainty.

---

### Pitfall 8: MicroPython Boot Overhead Cannot Be Eliminated

**What goes wrong:** Developers try to optimize the wake-to-action time but hit a floor imposed by MicroPython's interpreter startup. MicroPython boot on ESP32 takes 200-500ms before `main.py` even starts executing. This includes the VM initialization, frozen module loading, and `boot.py` execution.

**Why it happens:** MicroPython is an interpreted language running on top of the ESP-IDF. The interpreter must initialize on every wake from deep sleep (deep sleep resets the CPU). This is fundamentally different from Arduino/C where code runs almost immediately.

**Prevention:**
- Accept the MicroPython boot overhead as a fixed cost (~200-500ms)
- Focus optimization effort on the parts you CAN control: WiFi connection time, NTP sync, API call duration
- Do NOT attempt to optimize boot by pre-compiling to `.mpy` files — the savings are minimal (10-20ms) and adding file I/O complexity is not worth it for a single-file firmware
- Keep `boot.py` empty or nonexistent
- Avoid `import` statements that are not needed for every wake cycle

**Detection:** Time from wake to first line of `main.py` execution using GPIO toggling or serial timestamp.

**Phase relevance:** Wake time optimization phase. Sets expectations for minimum achievable wake time.

**Confidence:** MEDIUM — boot time varies by MicroPython version and frozen modules.

**Sources:**
- [Building Ultra Low Power with MicroPython - GitHub Discussion](https://github.com/orgs/micropython/discussions/12111)

---

### Pitfall 9: ADC Reading During WiFi Active State Gives Wrong Values

**What goes wrong:** Reading battery voltage via ADC while WiFi is connected produces noisy, inaccurate readings. The WiFi radio generates significant electromagnetic interference that couples into the ADC input, especially on ADC2 pins (but ADC1 is also affected to a lesser degree).

**Why it happens:** The ESP32's WiFi radio and ADC share the same silicon. RF transmission at 2.4GHz induces noise on the ADC analog front-end. ADC2 pins are explicitly shared with WiFi and cannot be used at all when WiFi is active.

**Prevention:**
- Read battery voltage AFTER `wlan.disconnect()` and `wlan.active(False)`, never while WiFi is connected
- Use only ADC1 pins (GPIO 32-39) — ADC2 is completely unavailable during WiFi
- Wait 10-50ms after WiFi off before ADC read for RF to settle
- This naturally fits the existing code flow: wake -> button -> WiFi -> API -> WiFi off -> ADC read -> LED -> sleep

**Detection:** Compare ADC readings taken with WiFi on vs WiFi off. If they differ by more than 50mV, RF interference is a factor.

**Phase relevance:** Battery monitoring implementation phase.

**Confidence:** HIGH — documented ESP32 hardware limitation.

**Sources:**
- [ESP-IDF ADC Documentation](https://docs.espressif.com/projects/esp-idf/en/v4.4/esp32/api-reference/peripherals/adc.html)

---

## Minor Pitfalls

### Pitfall 10: GPIO 39 (Button) Cannot Use Internal Pull-up

**What goes wrong:** GPIO 39 on the ESP32 is input-only and does NOT support internal pull-up or pull-down resistors. Developers may try to configure `Pin(39, Pin.IN, Pin.PULL_UP)` and it silently does nothing, leading to floating input and spurious wakes from deep sleep.

**Why it happens:** GPIOs 34-39 on the ESP32 are input-only with no internal pull resistors. The M5Stack ATOM Lite has an external pull-up on GPIO 39 for the button, so this works correctly in practice — but if custom wiring is added for other wake sources, this limitation must be remembered.

**Prevention:**
- The current design is correct (M5Stack has external pull-up on GPIO 39)
- If adding any new ext0/ext1 wake sources, verify the GPIO supports pull-up/down or add external resistors
- Document this constraint so future modifications don't break wake behavior

**Phase relevance:** Any phase adding new hardware interactions.

**Confidence:** HIGH — ESP32 datasheet fact.

---

### Pitfall 11: RTC Memory Corruption After Brown-Out

**What goes wrong:** The RTC memory (used for BSSID cache) survives deep sleep but can be corrupted by brown-out events when the battery voltage drops near the cutoff. The current validation (single 0xAA flag byte) catches some corruption but not all — a corrupted BSSID that happens to have 0xAA in byte 7 will be used for reconnection, causing slow WiFi connects.

**Why it happens:** As the battery depletes, voltage droops during high-current events (WiFi TX). If voltage drops below the brown-out detector threshold momentarily, RTC memory contents become unpredictable.

**Prevention:**
- Add a CRC8 checksum to the RTC memory layout (uses only 1 extra byte)
- Monitor battery voltage before entering deep sleep; if below a threshold (e.g., 3.3V), invalidate RTC cache
- Consider using more of the 2048 available RTC bytes for redundant storage

**Detection:** Unexpectedly slow WiFi connections (10-30 seconds instead of <2 seconds) when battery is low.

**Phase relevance:** Battery monitoring phase (can use voltage reading to gate cache validity).

**Confidence:** MEDIUM — theoretical but plausible, especially with a small 200mAh battery.

---

### Pitfall 12: `time.sleep_ms()` During Button Measurement Wastes Power

**What goes wrong:** The button press measurement loop uses polling with small delays. If the delay is too long, button release detection is sluggish. If too short, the CPU burns more power spinning. With an 80MHz CPU, even a tight polling loop draws ~20-30mA.

**Why it happens:** MicroPython has no interrupt-driven button duration measurement. Polling is the only option in the current architecture.

**Prevention:**
- Keep CPU at 80MHz during button measurement (already implemented)
- Use `time.sleep_ms(10)` between polls — 10ms granularity is sufficient for 1000ms threshold detection
- The total button measurement time (1-2 seconds) at 20-30mA is a small fraction of total wake energy; do not over-optimize this

**Detection:** Profile current draw during button hold phase with an oscilloscope or power profiler.

**Phase relevance:** Wake time optimization phase (low priority).

**Confidence:** HIGH — basic power consumption math.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Battery voltage monitoring (ADC) | Nonlinear ADC readings, wrong GPIO choice, divider drain | Use ADC1 pins, `read_uv()`, high-value resistors, read after WiFi off |
| Deep sleep current reduction | USB chip dominates, NeoPixel standby current | Measure at battery terminals first; identify actual current consumers before optimizing |
| Wake time optimization | MicroPython boot floor, heap fragmentation from new code | Accept 200-500ms floor; test every change for TLS compatibility |
| Autonomy estimation | Optimistic calculations ignoring boost converter losses and parasitic drains | Use measured values, model worst case, include self-discharge |
| LED power reduction | Blink timing changes may be imperceptible | Test with real users; minimum 50ms ON to be visible |
| WiFi optimization | Any WiFi config change risks heap or TLS breakage | Do not touch WiFi power management settings; optimize connection time instead |
| Boost converter interaction | Efficiency varies with load; datasheet values are typical not minimum | Measure actual efficiency at both sleep and active loads |

## Sources

- [MicroPython Discussions - Optimising energy consumption on ESP32 boot from deepsleep](https://github.com/orgs/micropython/discussions/10153)
- [MicroPython Discussions - Best practices for deep sleeping an ESP32](https://github.com/orgs/micropython/discussions/17715)
- [MicroPython Discussions - Building Ultra Low Power with MicroPython](https://github.com/orgs/micropython/discussions/12111)
- [ESP32 Forum - Deep sleep high current on Atom](https://community.m5stack.com/topic/3188/deep-sleep-high-current-on-atom)
- [M5Stack ATOM deep sleep current issue - GitHub](https://github.com/m5stack/M5Atom/issues/13)
- [ESP32 Forum - ADC Non-linear Issues](https://www.esp32.com/viewtopic.php?t=2881)
- [ESP32 Forum - Best solution for ESP32 + Neopixel and battery life](https://www.esp32.com/viewtopic.php?t=9029)
- [ESP-IDF Low Power Mode in Wi-Fi Scenarios](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-guides/low-power-mode/low-power-mode-wifi.html)
- [MicroPython ESP32 Quick Reference - ADC](https://docs.micropython.org/en/latest/esp32/quickref.html)
- [Atomic Battery Base - M5Stack Docs](https://docs.m5stack.com/en/atom/Atomic%20Battery%20Base)
- [ESP32 Deep Sleep Battery Sensors Guide](https://esp32.co.uk/esp32-battery-powered-sensors-deep-sleep-low-power-design-guide/)

---
*Researched: 2026-03-16*
