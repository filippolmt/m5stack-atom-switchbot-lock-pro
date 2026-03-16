---
phase: 02-battery-voltage-reading
verified: 2026-03-16T20:45:00Z
status: passed
score: 6/6 must-haves verified
re_verification: false
---

# Phase 2: Battery Voltage Reading Verification Report

**Phase Goal:** User can see the battery voltage on serial output every time the device wakes
**Verified:** 2026-03-16T20:45:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `read_battery_voltage()` returns correct millivolts from ADC GPIO 33 with 1:1 voltage divider formula | VERIFIED | `main.py:238-250` — lazy imports ADC/Pin(33), ATTN_11DB, 4-sample avg, `avg_uv * 2 // 1000`; confirmed by 3 value tests (3800/4200/3000 mV) |
| 2 | ADC failure returns 0 (never crashes) | VERIFIED | `main.py:248-250` — `except Exception` returns 0; `test_read_battery_voltage_adc_failure` passes |
| 3 | Battery voltage is printed to serial on every wake cycle | VERIFIED | `main.py:781-784` — `print(f"Battery: {battery_mv}mV")` and `print("Battery: read failed")` inside `handle_button_wake()`; `test_battery_voltage_printed_to_serial` confirms output contains "Battery:" and value |
| 4 | Battery voltage is saved to RTC memory via `save_battery_voltage()` | VERIFIED | `main.py:782` — `save_battery_voltage(battery_mv)` called inside `handle_button_wake()` when mv > 0 |
| 5 | ADC read happens after WiFi disconnect, never before `urequests.post()` | VERIFIED | `main.py:771-784` — `wlan.active(False)` at line 774, `read_battery_voltage()` at line 779; battery read is 5 lines after WiFi teardown |
| 6 | `machine.ADC` is lazy-imported inside the function, not at module level | VERIFIED | Module-level import at `main.py:15` is `from machine import Pin, deepsleep, reset_cause, DEEPSLEEP_RESET, freq` — no ADC; `from machine import ADC, Pin` only at `main.py:239` inside `read_battery_voltage()` |

**Score:** 6/6 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `main.py` | `read_battery_voltage()` + integration in `handle_button_wake()` | VERIFIED | Function at line 231; called in `handle_button_wake` at line 779; `save_battery_voltage(battery_mv)` at line 782 |
| `tests/test_battery.py` | Unit tests for battery voltage reading (min 40 lines, 6 tests) | VERIFIED | File exists; 6 test functions (`def test_` count = 6); 118 lines |
| `tests/conftest.py` | FakeADC stub for machine module | VERIFIED | `FakeADC` class at line 76; `machine.ADC = FakeADC` at line 93; stub provides `ATTN_0DB/2_5DB/6DB/11DB` constants and `read_uv()` |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `main.py:handle_button_wake` | `main.py:read_battery_voltage` | function call after `wlan.active(False)` | WIRED | `read_battery_voltage()` at line 779, immediately after WiFi teardown block ending at line 776 |
| `main.py:read_battery_voltage` | `main.py:save_battery_voltage` | saves mV to RTC memory | WIRED | `save_battery_voltage(battery_mv)` at line 782, conditional on `battery_mv > 0` |
| `tests/conftest.py` | `tests/test_battery.py` | FakeADC stub injected into machine module | WIRED | `sys.modules["machine"].ADC` retrieved in `_get_fake_adc_class()`; all 6 tests use it to configure/intercept ADC behaviour |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| BATT-01 | `02-01-PLAN.md` | Firmware legge tensione batteria via ADC su GPIO 33 (voltage divider 1:1) ad ogni ciclo wake | SATISFIED | `read_battery_voltage()` with `ADC(Pin(33), atten=ADC.ATTN_11DB)`, formula `avg_uv * 2 // 1000`, called unconditionally in `handle_button_wake()` |
| BATT-03 | `02-01-PLAN.md` | Tensione batteria stampata su seriale ad ogni wake per diagnostica | SATISFIED | `print(f"Battery: {battery_mv}mV")` at `main.py:781`; fallback `print("Battery: read failed")` at `main.py:784` — serial output occurs regardless of ADC success |

No orphaned requirements found — REQUIREMENTS.md maps only BATT-01 and BATT-03 to Phase 2, and both are claimed in the plan.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | — | — | — | — |

No TODO/FIXME/placeholder comments found in modified files. No empty implementations. No module-level ADC import. No `gc.collect()` before the ADC read.

### Human Verification Required

#### 1. Real hardware ADC accuracy

**Test:** Flash firmware to M5Stack ATOM with Atomic Battery Base attached. Monitor serial at 115200 baud during a button press. Measure actual battery voltage with a multimeter simultaneously.
**Expected:** Serial output shows "Battery: XXXXmV" where XXXX is within ~50 mV of the multimeter reading, accounting for ADC linearity on ESP32.
**Why human:** Voltage divider ratio and ADC calibration accuracy cannot be verified without physical hardware.

#### 2. ADC read timing after WiFi RF shutdown

**Test:** On hardware, observe whether there is any ADC noise immediately after `wlan.active(False)`. The plan decided to skip the optional 10ms delay.
**Expected:** Battery voltage reading is stable (consistent across presses at the same charge level, no outlier values).
**Why human:** RF-induced ADC noise can only be measured empirically on the actual ESP32-PICO-D4 with the specific PCB layout.

### Gaps Summary

No gaps. All truths verified, all artifacts substantive and wired, all requirements satisfied, no anti-patterns detected. 73 tests pass (make test exits 0).

---

_Verified: 2026-03-16T20:45:00Z_
_Verifier: Claude (gsd-verifier)_
