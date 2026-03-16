# Feature Landscape

**Domain:** Battery-optimized ESP32 IoT button device (200mAh, deep sleep, WiFi wake-on-press)
**Researched:** 2026-03-16

## CRITICAL FINDING: Deep Sleep Current is NOT 10uA

**The PROJECT.md and CLAUDE.md claim ~10uA deep sleep current. This is the bare ESP32 spec, NOT the M5Stack ATOM Lite board.**

Real-world measurements from multiple sources show the ATOM Lite draws **4-11mA in deep sleep** due to:
- USB/serial converter chip (always on, cannot be disabled): ~3-5mA
- NeoPixel WS2812B quiescent current (even when "off"): ~1mA
- 3.3V LDO regulator quiescent current: ~0.5-1mA

Add the ETA9085E10 boost converter standby current (~2.55uA, negligible vs board draw).

**This changes ALL battery life calculations dramatically.**

Confidence: HIGH -- multiple independent measurements on GitHub issues and M5Stack community forums agree on 4-11mA range.

Sources:
- [Deep sleep current too high - Issue #13](https://github.com/m5stack/M5Atom/issues/13)
- [Deep sleep high current on Atom - M5Stack Community](https://community.m5stack.com/topic/3188/deep-sleep-high-current-on-atom)
- [Light / Deep sleep example - M5Stack Community](https://community.m5stack.com/topic/2505/light-deep-sleep-example)

---

## Battery Life Calculations

### Parameters

| Parameter | Optimistic | Realistic | Pessimistic |
|-----------|-----------|-----------|-------------|
| Battery capacity | 200mAh | 200mAh | 200mAh |
| Deep sleep current (board) | 4mA | 7mA | 11mA |
| Boost converter standby | ~0.003mA | ~0.003mA | ~0.003mA |
| Boost efficiency | 90% | 87% | 85% |
| Active current (WiFi+API) | 80mA | 115mA | 150mA |
| Wake duration per press | 1.5s | 3s | 5s |
| Presses per day | 5 | 7 | 10 |
| Battery usable capacity | 90% (180mAh) | 85% (170mAh) | 80% (160mAh) |

Note: Usable capacity accounts for LiPo discharge curve -- voltage drops below boost converter minimum input before fully depleted.

### Calculation Method

```
Sleep current from battery = Board sleep current / boost efficiency
Active current from battery = Board active current / boost efficiency

Daily sleep hours = 24 - (wake_seconds * presses / 3600)
Daily sleep consumption = sleep_current_from_battery * sleep_hours (mAh)
Daily active consumption = active_current_from_battery * (wake_seconds * presses / 3600) (mAh)
Daily total = sleep + active
Battery life = usable_capacity / daily_total
```

### Scenario 1: Optimistic (best case)

```
Sleep current from battery = 4mA / 0.90 = 4.44mA
Active current from battery = 80mA / 0.90 = 88.9mA

Daily wake time = 1.5s * 5 = 7.5s = 0.00208h
Daily sleep time = 23.998h
Daily sleep consumption = 4.44 * 23.998 = 106.6mAh
Daily active consumption = 88.9 * 0.00208 = 0.185mAh
Daily total = 106.8mAh

Battery life = 180 / 106.8 = 1.69 days (~40 hours)
```

### Scenario 2: Realistic (expected)

```
Sleep current from battery = 7mA / 0.87 = 8.05mA
Active current from battery = 115mA / 0.87 = 132.2mA

Daily wake time = 3s * 7 = 21s = 0.00583h
Daily sleep time = 23.994h
Daily sleep consumption = 8.05 * 23.994 = 193.2mAh
Daily active consumption = 132.2 * 0.00583 = 0.771mAh
Daily total = 193.9mAh

Battery life = 170 / 193.9 = 0.88 days (~21 hours)
```

### Scenario 3: Pessimistic (worst case)

```
Sleep current from battery = 11mA / 0.85 = 12.94mA
Active current from battery = 150mA / 0.85 = 176.5mA

Daily wake time = 5s * 10 = 50s = 0.01389h
Daily sleep time = 23.986h
Daily sleep consumption = 12.94 * 23.986 = 310.4mAh
Daily active consumption = 176.5 * 0.01389 = 2.45mAh
Daily total = 312.8mAh

Battery life = 160 / 312.8 = 0.51 days (~12 hours)
```

### Key Insight

**The dominant power consumer is deep sleep current, NOT active usage.** Active consumption is negligible (<1% of total). Even with zero button presses, the battery drains in 1-2 days.

| Scenario | Battery Life | Sleep % of Total |
|----------|-------------|-----------------|
| Optimistic | ~40 hours | 99.8% |
| Realistic | ~21 hours | 99.6% |
| Pessimistic | ~12 hours | 99.2% |

**Reducing wake time from 5s to 1.5s saves less than 0.5% of battery.** Wake time optimizations are nearly irrelevant compared to the sleep current problem.

---

## Table Stakes

Features users expect. Missing = product feels incomplete for a battery-powered device.

| Feature | Why Expected | Complexity | Status | Notes |
|---------|--------------|------------|--------|-------|
| Low-battery warning LED | User needs to know when to recharge | Low | NOT IMPLEMENTED | Blink red/orange on wake when voltage below threshold |
| Battery voltage monitoring via ADC | Foundation for all battery features | Low | NOT IMPLEMENTED | GPIO 33 with 1:1 voltage divider (2x 1MOhm). Formula: `V_BAT = ADC_mV * 2` |
| Graceful low-battery shutdown | Prevent deep discharge damage to LiPo | Low | NOT IMPLEMENTED | If V_BAT < 3.3V, show red LED and refuse operation |
| LED brightness reduction | Single biggest controllable power save | Low | PARTIALLY (brightness=64) | Current default 64/255 is already reduced. Consider 16-32 for battery mode |
| Reliable lock/unlock on every press | Core function must work | N/A | IMPLEMENTED | Already working with retry logic |
| Visual feedback for action result | User must know if command succeeded | N/A | IMPLEMENTED | Color-coded LED blinks already present |

## Differentiators

Features that improve battery life or UX beyond basic expectations.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Battery percentage estimation | Show approximate charge level via LED color on wake | Medium | LiPo voltage-to-percentage is non-linear. Use lookup table: 4.2V=100%, 3.7V=50%, 3.3V=0% |
| Adaptive LED feedback | Skip LED blinks when battery is critically low | Low | Save ~50-100ms of LED current per press. Marginal but free |
| Press counter in RTC memory | Track usage for diagnostics and battery estimation | Low | RTC memory has 2048 bytes, only 8 used. Store 16-bit press counter at bytes 8-9 |
| WiFi channel caching (active use) | Currently cached but only diagnostic. Using channel in connect() saves ~100ms | Low | Channel is already stored at byte 6 but not passed to wlan.connect(). Fix: pass channel param |
| Boot-to-command fast path | Minimize Python overhead between wake and API call | Medium | Profile actual boot path, identify delays. MicroPython boot overhead is 200-500ms |
| USB power detection | Detect if USB is plugged in, skip battery warnings | Low | Check VBUS presence or voltage level to distinguish battery vs USB power |

## Anti-Features

Features to explicitly NOT build given the 200mAh constraint.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| OTA firmware updates | Adds WiFi time, code complexity, flash writes. With 12-40h battery life, device is always near a USB port anyway | Use mpremote for updates when charging |
| Web configuration portal | WiFi AP mode draws 100-200mA continuously. Even 30 seconds would use more power than 100 button presses | Keep config.py file-based |
| Bluetooth/BLE secondary interface | ESP32 BLE draws 30-100mA. No benefit for a 2-button device | Single WiFi path is sufficient |
| Periodic health check / heartbeat | Any periodic wake destroys battery. Even 1 wake/hour at 3s = 3s * 24 = 72s of active time, but sleep current dominates anyway | Only wake on button press |
| Multi-device support | More API calls = more wake time. Complexity adds code size (heap pressure) | One device per ATOM Lite |
| Watchdog timer (WDT) | CONFIRMED to cause MBEDTLS_ERR_MPI_ALLOC_FAILED on this hardware | Rely on deep sleep as natural reset. If API call hangs, timeout + deep sleep recovers |
| WiFi power save mode (PS_NONE) | CONFIRMED to increase system heap usage, breaking TLS | Leave default modem sleep during active period |
| Light sleep mode instead of deep sleep | On ATOM Lite, light sleep draws ~2-5mA (CPU paused but peripherals on) vs 4-11mA deep sleep. Marginal improvement but loses RTC reliability and adds code complexity | Stick with deep sleep. The board-level sleep current is dominated by USB/serial chip, not ESP32 core |
| Complex battery fuel gauge IC | Hardware modification needed (I2C device like MAX17043). Overkill for 200mAh cell with simple voltage divider already available | Use ADC on GPIO 33 with voltage lookup table |
| Aggressive wake time optimization beyond existing | Currently 1-5s. Even halving to 0.5-2.5s saves <0.5% battery due to sleep current dominance | Focus effort on battery monitoring and UX, not microsecond shaving |

## Feature Dependencies

```
Battery voltage monitoring (ADC GPIO 33)
  --> Low-battery warning LED
  --> Graceful low-battery shutdown
  --> Battery percentage estimation
  --> Adaptive LED feedback (depends on knowing battery level)

RTC memory layout expansion
  --> Press counter storage
  --> (Future: more cached state)

WiFi channel caching fix
  --> (Independent, no dependencies. Uses existing data in RTC byte 6)

USB power detection
  --> (Independent. Needed to suppress false low-battery warnings when charging)
```

## MVP Recommendation

Given the battery life reality (12-40 hours, dominated by sleep current), the highest-value features are:

### Priority 1: Battery Monitoring (Table Stakes)
1. **Battery voltage reading via ADC on GPIO 33** -- Foundation for everything else
2. **Low-battery warning** -- Red LED blink on wake when voltage < 3.5V
3. **Graceful shutdown** -- Refuse operation below 3.3V to protect LiPo

Rationale: With only 12-40 hours of battery life, users WILL encounter dead batteries. They need advance warning.

### Priority 2: Quick Wins (Low effort, tangible benefit)
4. **WiFi channel caching fix** -- Pass cached channel to `wlan.connect()`. Already have the data, just not using it. Saves ~100ms per reconnect.
5. **LED brightness further reduction** -- Drop from 64 to 24-32. Saves ~0.5mA during blink periods. Marginal but trivial to implement.
6. **Press counter in RTC memory** -- 4 lines of code. Useful for battery life estimation and diagnostics.

### Defer: Nice-to-Haves
- **Battery percentage estimation**: Non-linear LiPo curve makes this more complex than it looks. Simple threshold warnings are more reliable.
- **USB power detection**: Only needed if users complain about false low-battery warnings while charging.
- **Adaptive LED feedback**: Only saves power during the <1% active time. Not worth the code complexity.

### Explicitly Skip
- Any feature targeting wake time reduction -- the math shows it's irrelevant
- Any feature requiring hardware modification
- Any feature that adds module-level allocations (mbedTLS heap constraint)

## Honest Assessment of Battery Optimization Value

**The uncomfortable truth:** With a 200mAh battery and 4-11mA board sleep current, no software optimization will achieve multi-day battery life. The dominant power consumer (USB/serial chip, LDO, NeoPixel quiescent) cannot be addressed in software.

**What software CAN do:**
- Provide battery monitoring so users know when to charge (HIGH value)
- Shave 100-500ms off wake time (saves <0.5% battery, but improves perceived responsiveness)
- Reduce LED brightness (marginal battery savings, but visible UX improvement)

**What would actually extend battery life:**
- Hardware: Cut trace to USB/serial chip power (voids warranty, saves 3-5mA = 40-70% of sleep current)
- Hardware: Use a different board with proper low-power design (bare ESP32-WROOM + efficient LDO = 40-100uA deep sleep)
- Battery: Use a larger battery base or external LiPo

**Realistic expectation:** Software optimizations might push battery life from ~21 hours to ~23 hours. The primary value of this milestone should be **battery monitoring and UX**, not raw power savings.

## Sources

- [M5Stack ATOM Deep Sleep Issue #13](https://github.com/m5stack/M5Atom/issues/13) -- actual current measurements
- [M5Stack Community - Deep sleep high current](https://community.m5stack.com/topic/3188/deep-sleep-high-current-on-atom)
- [Atomic Battery Base Documentation](https://docs.m5stack.com/en/atom/Atomic%20Battery%20Base) -- GPIO 33 ADC, voltage divider specs
- [ESP32 Sleep Modes & Power Consumption](https://lastminuteengineers.com/esp32-sleep-modes-power-consumption/)
- [ESP32 WiFi Fast Connect - arduino-esp32 Issue #1675](https://github.com/espressif/arduino-esp32/issues/1675) -- BSSID+channel optimization
- [ESP32 Battery Voltage Monitoring](https://forum.allaboutcircuits.com/threads/esp32-and-monitoring-battery-voltage.185181/)
- [ESP-IDF Low Power Mode - WiFi Scenarios](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-guides/low-power-mode/low-power-mode-wifi.html)
- [DIYI0T - Reduce ESP32 Power Consumption](https://diyi0t.com/reduce-the-esp32-power-consumption/)

---
*Mapped: 2026-03-16*
