---
phase: 05-led-power-reduction
verified: 2026-03-16T00:00:00Z
status: human_needed
score: 2/3 must-haves verified (3rd requires hardware)
human_verification:
  - test: "Upload firmware and observe LED during button press and result feedback"
    expected: "LEDs are clearly visible in normal indoor lighting at reduced brightness (32/255) and halved blink durations"
    why_human: "Perceived LED visibility at brightness=32 cannot be verified programmatically — requires eye confirmation on actual hardware"
---

# Phase 5: LED Power Reduction Verification Report

**Phase Goal:** LED feedback uses less energy per wake cycle while remaining visible
**Verified:** 2026-03-16
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Default LED brightness is 32 (halved from 64) | VERIFIED | `LED_BRIGHTNESS = 32` at main.py:33; `StatusLED.__init__` default is `brightness=LED_BRIGHTNESS` (line 307); `main()` passes `brightness=LED_BRIGHTNESS` (line 844); `brightness=64` not found anywhere in main.py |
| 2 | All blink durations are halved compared to previous values | VERIFIED | All 7 blink method defaults confirmed halved; all 9 explicit call sites in `handle_button_wake`, `check_low_battery`, and `main()` confirmed halved (see detail below) |
| 3 | LED remains functional (scale math still correct at brightness=32) | VERIFIED | `test_scale_default_brightness` confirms `_scale(255) == 32` at brightness=32; `test_default_brightness_is_32` and `test_led_brightness_constant` confirm new defaults; `test_blink_defaults_halved` verifies signatures via `inspect` |

**Score:** 2/3 truths fully automated-verified (truth 3 is code-verified; truth 3 success criterion 3 from ROADMAP requires human)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `main.py` | StatusLED with reduced brightness and halved blink durations; `LED_BRIGHTNESS = 32` constant | VERIFIED | Constant at line 33; default in `__init__` at line 307; all blink methods and call sites updated |
| `tests/test_led.py` | Tests for new brightness default and blink duration constants | VERIFIED | 74-line file with `test_default_brightness_is_32`, `test_led_brightness_constant`, `test_scale_default_brightness`, `test_blink_defaults_halved` — all substantive, testing actual values |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `main.py` (module level) | `LED_BRIGHTNESS = 32` | constant definition | VERIFIED | Line 33: `LED_BRIGHTNESS = 32` |
| `StatusLED.__init__` | `LED_BRIGHTNESS` constant | default parameter value | VERIFIED | Line 307: `def __init__(self, pin_num=27, brightness=LED_BRIGHTNESS)` |
| `main()` | `StatusLED` constructor | `brightness=LED_BRIGHTNESS` argument | VERIFIED | Line 844: `led = StatusLED(pin_num=27, brightness=LED_BRIGHTNESS)` |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| LED-01 | 05-01-PLAN.md | Luminosita LED ridotta da 64 a 32 (default) per risparmio energetico | SATISFIED | `LED_BRIGHTNESS = 32` defined and used as default throughout; `brightness=64` absent from codebase |
| LED-02 | 05-01-PLAN.md | Durata blink feedback ridotta (halved rispetto ai valori attuali) | SATISFIED | All 7 method defaults halved; all 9 explicit call sites halved |

**Blink method defaults — halved values confirmed:**

| Method | on_ms | off_ms | Previous | Status |
|--------|-------|--------|----------|--------|
| `blink_red` | 100 | 100 | 200/200 | VERIFIED |
| `blink_green` | 150 | 50 | 300/100 | VERIFIED |
| `blink_blue` | 100 | 100 | 200/200 | VERIFIED |
| `blink_yellow` | 150 | 100 | 300/200 | VERIFIED |
| `blink_orange` | 150 | 100 | 300/200 | VERIFIED |
| `blink_purple` | 100 | 100 | 200/200 | VERIFIED |
| `blink_fast_red` | 50 | 50 | 100/100 | VERIFIED |

**Explicit call sites — halved values confirmed:**

| Call site | Location | on_ms | off_ms | Status |
|-----------|----------|-------|--------|--------|
| `blink_orange` — wifi error | `handle_button_wake` line 748 | 150 | 100 | VERIFIED |
| `blink_yellow` — NTP warning | `handle_button_wake` line 774 | 150 | 100 | VERIFIED |
| `blink_purple` — lock success | `handle_button_wake` line 808 | 150 | 50 | VERIFIED |
| `blink_green` — unlock success | `handle_button_wake` line 811 | 150 | 50 | VERIFIED |
| `blink_fast_red` — auth error | `handle_button_wake` line 814 | 50 | 50 | VERIFIED |
| `blink_yellow` — time error | `handle_button_wake` line 817 | 100 | 100 | VERIFIED |
| `blink_red` — API error | `handle_button_wake` line 820 | 100 | 100 | VERIFIED |
| `blink_orange` — low battery | `check_low_battery` line 260 | 100 | 75 | VERIFIED |
| `blink_green` — fresh boot green | `main()` line 864 | 150 | 50 | VERIFIED |
| `blink_purple` — fresh boot purple | `main()` line 865 | 150 | 50 | VERIFIED |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | - | - | - | - |

No stubs, placeholders, TODOs, empty handlers, or leftover `brightness=64` found.

### Human Verification Required

#### 1. LED Visibility at Reduced Brightness

**Test:** Upload firmware to the M5Stack ATOM Lite:
```bash
mpremote connect /dev/cu.usbserial-XXXX cp main.py :main.py
```
Then power-cycle the device and perform:
1. Observe the fresh boot LED flash (green then purple) — dimmer and faster than before
2. Short press (less than 1 second) — confirm green blinks on success are visible
3. Long press (more than 1 second) — confirm purple blinks on success are visible

**Expected:** All LED feedback colors (green, purple, orange, red, yellow, cyan, blue) remain clearly visible to a human in normal indoor lighting at the reduced brightness of 32/255 (approximately 12.5% of full brightness)

**Why human:** Perceived LED brightness and visibility at `LED_BRIGHTNESS = 32` cannot be determined from code alone. The NeoPixel driver scales RGB values linearly, but human visual perception is non-linear and depends on ambient lighting conditions. Code confirms the math is correct; only on-device observation can confirm visibility.

### Gaps Summary

No automated gaps. All code changes are implemented correctly and completely. The only open item is the on-device visual confirmation that reduced brightness (32) remains visible in practice — this is ROADMAP success criterion 3 and requires human observation.

---

_Verified: 2026-03-16_
_Verifier: Claude (gsd-verifier)_
