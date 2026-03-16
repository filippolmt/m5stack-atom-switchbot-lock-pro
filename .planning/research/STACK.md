# Technology Stack: Battery Optimization

**Project:** M5Stack ATOM SwitchBot Lock Pro - Battery Optimization Milestone
**Researched:** 2026-03-16
**Focus:** Power measurement, ADC battery reading, ESP32 low-power modes, MicroPython power APIs

## Recommended Stack

### Battery Voltage Reading (ADC)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `machine.ADC` (GPIO 33) | MicroPython 1.24.x+ | Read battery voltage from Atomic Battery Base | GPIO 33 = ADC1_CH5 (safe with WiFi active). The Atomic Battery Base uses GPIO 33 as battery ADC pin with a 1M/1M voltage divider. ADC1 is the only block available in MicroPython on ESP32 -- ADC2 is blocked by WiFi driver. |
| `ADC.read_uv()` | MicroPython 1.20+ | Factory-calibrated voltage reading in microvolts | Uses per-package eFuse calibration values. More accurate than raw `read_u16()` + manual conversion. Returns millivolt resolution (multiples of 1000uV). |
| `ADC.ATTN_11DB` | Built-in | Set attenuation for 150mV-2450mV range | With the 1M/1M voltage divider, V_BAT/2 reaches the ADC pin. A 4.2V full LiPo reads as ~2.1V, well within the 11dB range. |

**Confidence:** HIGH -- M5Stack official docs confirm GPIO 33 and 1M/1M divider. MicroPython ADC API is stable and well-documented.

**Battery Voltage Formula:**
```python
V_BAT = ADC_reading_uv * 2 / 1_000_000  # Convert uV to V, multiply by 2 for divider
```

Or using the M5Stack documented formula:
```python
V_BAT = 3.3 * (raw_12bit / 4095) * 2  # If using raw ADC reads
```

**Code Example (safe pattern for this project):**
```python
from machine import ADC, Pin

def read_battery_voltage():
    """Read battery voltage. Call AFTER urequests.post() to avoid system heap issues."""
    adc = ADC(Pin(33), atten=ADC.ATTN_11DB)
    uv = adc.read_uv()
    voltage = uv * 2 / 1_000_000  # 1M/1M divider doubles the reading
    return voltage
```

### Power Modes (ESP32 via MicroPython)

| Mode | Current Draw | MicroPython API | Use Case in This Project |
|------|-------------|-----------------|--------------------------|
| **Deep Sleep** | ~10uA (ESP32) + ~2.55uA (ETA9085E10) | `machine.deepsleep()` + `esp32.wake_on_ext0()` | Already implemented. Primary idle mode. |
| **Light Sleep** | ~0.8mA | `machine.lightsleep(ms)` | NOT recommended for this project (see below) |
| **Active (WiFi)** | ~80-150mA | N/A (default) | Current wake cycle |
| **Active (no WiFi, 80MHz)** | ~20-30mA | `machine.freq(80_000_000)` | Already used for LED feedback |

**Light Sleep Assessment:** NOT recommended for this use case. Deep sleep at ~10uA is already 80x better than light sleep at ~0.8mA. Light sleep preserves RAM state but adds complexity with no benefit -- this device does a single action per wake and returns to sleep. The wake-from-deep-sleep path is already optimized with RTC memory caching.

**Confidence:** HIGH -- Deep sleep is already the correct choice. Light sleep would be a regression.

### Power Measurement Tools

| Tool | Cost | Purpose | Why This One |
|------|------|---------|-------------|
| **Nordic PPK2** (Power Profiler Kit II) | ~$90 | Measure current from 200nA to 1A with 100nA resolution | Gold standard for embedded power profiling. Can act as power supply (SMU mode) or inline ammeter. Captures deep sleep (~10uA) through WiFi bursts (~150mA) in a single trace. Software is free (nRF Connect). |
| **INA219 breakout** (inline, I2C) | ~$5-10 | Continuous inline current monitoring on the device itself | Measures voltage, current, and power via I2C. MicroPython library available (`pyb_ina219`). 12-bit ADC, up to 3.2A, ~0.8mA resolution. Good for logging but NOT recommended for production (adds I2C overhead and system heap allocation). |
| **USB multimeter (e.g., Fnirsi FNB58)** | ~$20-30 | Quick sanity check of total USB power draw | Good for ballpark measurements during development. Cannot capture uA-level deep sleep current. |

**Recommendation:** Use **Nordic PPK2** for profiling during development. Do NOT add INA219 to the production firmware -- it would require I2C setup that risks system heap fragmentation before TLS operations.

**Confidence:** HIGH for PPK2 recommendation (widely used in ESP32 community). MEDIUM for INA219 library compatibility (not tested on this specific MicroPython build).

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `machine.ADC` | Built-in | Battery voltage reading | Every wake cycle, AFTER API call completes |
| `machine.RTC` | Built-in | Store battery state across deep sleep cycles | Extend existing RTC memory layout (bytes 8+) |
| `esp32` module | Built-in | Wake source config, wake cause detection | Already used; no changes needed |
| `gc` module | Built-in | Memory cleanup after HTTP | Already used correctly (post-request only) |

**No new external libraries needed.** All battery optimization uses built-in MicroPython modules.

## Critical Constraints (mbedTLS Heap)

These constraints from the existing codebase MUST be respected in all battery optimization work:

### DO NOT add before `urequests.post()`:
| Forbidden | Why |
|-----------|-----|
| `ADC()` initialization | Creates hardware peripheral allocation on system heap |
| `INA219` I2C setup | I2C driver allocates from system heap |
| Any new `import` | Shifts system heap layout |
| `WDT()` | Confirmed to cause MBEDTLS_ERR_MPI_ALLOC_FAILED |
| `gc.collect()` | Fragments system heap via finalizers |

### Safe patterns for battery optimization:
| Pattern | Why Safe |
|---------|----------|
| ADC reading AFTER `urequests.post()` and `gc.collect()` | TLS handshake already complete |
| Store battery level in RTC memory AFTER WiFi disconnect | No system heap contention |
| Reduce LED brightness/duration | Only changes NeoPixel timing, no heap impact |
| Shorter `time.sleep_ms()` values | Pure timing, no allocation |
| Read battery on fresh boot (non-deepsleep reset) | No WiFi/TLS involved |

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| ADC method | `read_uv()` | `read_u16()` + manual calibration | `read_uv()` uses factory eFuse calibration, more accurate out of the box |
| Sleep mode | Deep sleep only | Light sleep for faster wake | Light sleep draws 80x more current; wake time savings minimal vs deep sleep + fast reconnect |
| Battery monitoring | ADC on GPIO 33 | External fuel gauge (MAX17048) | Adds I2C bus, system heap risk, unnecessary complexity for 200mAh cell |
| Power profiler | Nordic PPK2 | Otii Arc | Otii Arc is $500+; PPK2 at $90 covers the needed range (200nA-1A) |
| Current sensor | None in production | INA219 inline | System heap allocation risk; development-only tool |
| Voltage reference | Internal eFuse calibration | External voltage reference IC | Overkill; eFuse calibration is +-2% which is sufficient for battery % estimation |

## RTC Memory Layout Extension

Current layout (bytes 0-7) is used for WiFi fast reconnect. Extend for battery data:

```
Byte 0-5:  BSSID (existing)
Byte 6:    WiFi channel (existing)
Byte 7:    Valid flag 0xAA (existing)
Byte 8-9:  Last battery voltage (mV, uint16 big-endian) [NEW]
Byte 10:   Battery percentage (0-100) [NEW]
Byte 11:   Battery data valid flag 0xBB [NEW]
```

**Confidence:** HIGH -- RTC memory survives deep sleep and has 512 bytes available on ESP32.

## Battery Voltage to Percentage Mapping

LiPo discharge curve (3.7V nominal, 4.2V full, 3.0V cutoff):

| Voltage | Approximate % | Note |
|---------|--------------|------|
| >= 4.20V | 100% | Fully charged |
| 4.06V | 90% | |
| 3.98V | 80% | |
| 3.92V | 70% | |
| 3.87V | 60% | |
| 3.82V | 50% | |
| 3.79V | 40% | |
| 3.77V | 30% | |
| 3.74V | 20% | Consider low battery warning |
| 3.68V | 10% | Urgent warning |
| <= 3.00V | 0% | Cutoff -- ETA9085E10 will shut down |

**Note:** These are approximate values for a typical LiPo cell. The actual curve varies by cell chemistry and load. For a 200mAh cell with burst loads (WiFi), voltage sag under load can be significant. Read voltage AFTER WiFi disconnect for more stable readings.

**Confidence:** MEDIUM -- Standard LiPo curve, but actual behavior with ETA9085E10 boost converter may shift thresholds. Needs real-world calibration.

## Estimated Battery Life Calculation

Given: 200mAh battery, ETA9085E10 boost efficiency ~85-90%

**Deep sleep consumption (from battery perspective):**
- ESP32 deep sleep: ~10uA
- ETA9085E10 standby: ~2.55uA
- Total: ~12.55uA
- Effective from battery (at 3.7V boosted to 5V, ~85% eff): ~12.55 * (5/3.7) / 0.85 = ~20uA

**Per-press consumption:**
- Active time: ~2-3s (optimized fast reconnect)
- Average active current: ~100mA (WiFi + CPU)
- Energy per press: ~100mA * 2.5s / 3600 = ~0.069mAh
- Effective from battery: ~0.069 / 0.85 * (5/3.7) = ~0.11mAh per press

**Scenarios (10 presses/day):**
- Daily active: ~1.1mAh
- Daily sleep: ~0.48mAh (20uA * 24h)
- Daily total: ~1.58mAh
- **Estimated battery life: ~126 days** (200mAh / 1.58mAh)

**Confidence:** LOW -- This is a theoretical estimate. Real-world factors (self-discharge, boost converter efficiency curve at different loads, WiFi retry scenarios, temperature) will reduce this. Needs PPK2 validation.

## Installation

No new packages needed. All APIs are MicroPython built-ins.

```bash
# Development tools (host machine)
# Nordic PPK2 software
# Download nRF Connect for Desktop from https://www.nordicsemi.com/Products/Development-tools/nrf-connect-for-desktop

# Existing deployment (unchanged)
mpremote connect /dev/cu.usbserial-XXXX cp main.py :main.py
mpremote connect /dev/cu.usbserial-XXXX cp config.py :config.py
```

## Sources

- [M5Stack Atomic Battery Base documentation](https://docs.m5stack.com/en/atom/Atomic%20Battery%20Base) -- GPIO 33 ADC pin, 1M/1M voltage divider, ETA9085E10 specs
- [MicroPython ESP32 Quick Reference v1.24.0](https://docs.micropython.org/en/v1.24.0/esp32/quickref.html) -- ADC API, sleep modes, pin assignments
- [MicroPython machine.ADC class documentation](https://docs.micropython.org/en/latest/library/machine.ADC.html) -- `read_uv()`, attenuation constants
- [Nordic Power Profiler Kit II](https://www.nordicsemi.com/Products/Development-hardware/Power-Profiler-Kit-2) -- PPK2 specifications and capabilities
- [pyb_ina219 MicroPython library](https://github.com/chrisb2/pyb_ina219) -- INA219 current sensor for development use
- [ESP-IDF Sleep Modes documentation](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-reference/system/sleep_modes.html) -- ESP32 power modes reference
- [ESP32 ADC2 WiFi limitation](https://randomnerdtutorials.com/esp32-pinout-reference-gpios/) -- ADC2 unusable with WiFi, ADC1 (GPIO 32-39) is safe

---

*Stack research: 2026-03-16*
