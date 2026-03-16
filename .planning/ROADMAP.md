# Roadmap: Battery Optimization Milestone

## Overview

This milestone transforms the M5Stack ATOM SwitchBot Lock Pro firmware from a power-unaware device into a battery-conscious system. The work progresses from foundational data structures (RTC memory extension), through battery monitoring and power reduction, to configurability and documentation. Every change respects the mbedTLS system heap constraint: no new allocations before `urequests.post()`.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: RTC Memory Layout Extension** - Extend RTC memory from 8 to 12 bytes with backward compatibility
- [ ] **Phase 2: Battery Voltage Reading** - Read battery voltage via ADC on GPIO 33 and output to serial
- [ ] **Phase 3: Low Battery Warning** - Orange LED warning when battery is below threshold
- [ ] **Phase 4: Wake Cycle Counter** - Track wake cycles in RTC memory for diagnostics
- [ ] **Phase 5: LED Power Reduction** - Reduce LED brightness and blink durations to save energy
- [ ] **Phase 6: WiFi Channel Fast Reconnect** - Pass cached WiFi channel to wlan.connect() for faster reconnect
- [ ] **Phase 7: Power Configuration Constants** - Configurable constants in config.py for LED, battery, and logging
- [ ] **Phase 8: Logging Control** - Configurable serial output verbosity for production use
- [ ] **Phase 9: Documentation Update** - README and CLAUDE.md updated with battery specs and autonomy estimates

## Phase Details

### Phase 1: RTC Memory Layout Extension
**Goal**: RTC memory structure supports battery voltage caching and wake counter without breaking existing WiFi BSSID cache
**Depends on**: Nothing (first phase)
**Requirements**: BATT-05
**Success Criteria** (what must be TRUE):
  1. RTC memory layout uses 12 bytes with new flag 0xBB distinguishing it from old 8-byte layout (0xAA)
  2. Device with old 0xAA layout gracefully falls back — WiFi BSSID cache still works after firmware update
  3. Bytes 8-9 reserved for battery voltage (mV), byte 10 for wake counter, byte 11 reserved
  4. Existing save_wifi_config/load_wifi_config functions work correctly with the extended layout
**Plans**: 1 plan

Plans:
- [ ] 01-01-PLAN.md — Extend RTC memory to 12 bytes with TDD (tests + implementation)

### Phase 2: Battery Voltage Reading
**Goal**: User can see the battery voltage on serial output every time the device wakes
**Depends on**: Phase 1
**Requirements**: BATT-01, BATT-03
**Success Criteria** (what must be TRUE):
  1. Battery voltage is read via ADC on GPIO 33 after WiFi disconnect (never before urequests.post())
  2. Voltage value (in millivolts) is printed to serial output on every wake cycle
  3. ADC read uses lazy import of machine.ADC inside the function, not at module level
  4. 20+ consecutive wake cycles complete without mbedTLS errors (TLS handshake still works)
**Plans**: 1 plan

Plans:
- [ ] 02-01-PLAN.md — TDD: read_battery_voltage() with FakeADC stub, tests, and wake flow integration

### Phase 3: Low Battery Warning
**Goal**: User receives visible warning when battery is running low, before the device dies
**Depends on**: Phase 2
**Requirements**: BATT-02, LED-03
**Success Criteria** (what must be TRUE):
  1. Orange LED blinks when battery voltage is below configurable threshold (default ~3.3V)
  2. Low-battery warning appears after the normal lock/unlock feedback, not replacing it
  3. Warning is visible on every wake cycle while battery is below threshold
**Plans**: 1 plan

Plans:
- [ ] 03-01-PLAN.md — TDD: BATTERY_LOW_MV constant, check_low_battery() function, and orange LED warning

### Phase 4: Wake Cycle Counter
**Goal**: User can track how many times the device has been used since last power cycle for diagnostics
**Depends on**: Phase 1
**Requirements**: BATT-04
**Success Criteria** (what must be TRUE):
  1. Wake counter in RTC memory byte 10 increments on every button press wake
  2. Counter value is printed to serial output alongside battery voltage
  3. Counter wraps at 255 (single byte) without corrupting other RTC memory fields
**Plans**: 1 plan

Plans:
- [ ] 04-01-PLAN.md — Wire increment_wake_counter() into handle_button_wake() with serial output and tests

### Phase 5: LED Power Reduction
**Goal**: LED feedback uses less energy per wake cycle while remaining visible
**Depends on**: Nothing (independent of battery monitoring phases)
**Requirements**: LED-01, LED-02
**Success Criteria** (what must be TRUE):
  1. Default LED brightness is 32 (down from 64), reducing NeoPixel current draw
  2. All blink durations are halved compared to current values
  3. LED feedback remains clearly visible in normal indoor lighting
**Plans**: 1 plan

Plans:
- [ ] 05-01-PLAN.md — Halve LED brightness (64->32) and all blink durations, add LED_BRIGHTNESS constant

### Phase 6: WiFi Channel Fast Reconnect
**Goal**: WiFi reconnection is faster by passing cached channel to wlan.connect()
**Depends on**: Phase 1
**Requirements**: WIFI-01
**Success Criteria** (what must be TRUE):
  1. Cached WiFi channel from RTC memory byte 6 is passed to wlan.connect() as channel parameter
  2. Reconnect time measurably improves (~100ms faster) on serial output timestamps
  3. Device still connects successfully if cached channel is stale or wrong (fallback works)
**Plans**: 1 plan

Plans:
- [ ] 06-01-PLAN.md — Pass cached channel to wlan.connect() with 3-tier TypeError fallback and tests

### Phase 7: Power Configuration Constants
**Goal**: User can tune power-related behavior via config.py without modifying main.py
**Depends on**: Phase 3, Phase 5
**Requirements**: PWR-01
**Success Criteria** (what must be TRUE):
  1. config.py supports optional constants: LED_BRIGHTNESS, BATTERY_LOW_MV
  2. main.py reads these with try/except fallback to sensible defaults (same pattern as WIFI_STATIC_IP)
  3. Changing LED_BRIGHTNESS in config.py visibly changes LED behavior on next wake
**Plans**: 1 plan

Plans:
- [ ] 07-01-PLAN.md — Make LED_BRIGHTNESS and BATTERY_LOW_MV configurable via config.py with try/except fallback

### Phase 8: Logging Control
**Goal**: Serial output can be reduced or silenced for production use to save power
**Depends on**: Phase 7
**Requirements**: PWR-02, PWR-03
**Success Criteria** (what must be TRUE):
  1. config.py supports LOG_LEVEL constant with values: "verbose", "minimal", "silent"
  2. In "minimal" mode, only errors and battery voltage are printed
  3. In "silent" mode, no serial output occurs (saves time spent on UART transmission)
  4. Default behavior (no LOG_LEVEL set) matches current verbose output for backward compatibility
**Plans**: 1 plan

Plans:
- [ ] 08-01-PLAN.md — Create log() function with level filtering and replace all print() calls

### Phase 9: Documentation Update
**Goal**: README and CLAUDE.md reflect the new battery monitoring capabilities and realistic autonomy estimates
**Depends on**: Phase 2, Phase 3, Phase 5, Phase 8
**Requirements**: DOC-01, DOC-02, DOC-03
**Success Criteria** (what must be TRUE):
  1. README contains realistic battery life estimate (12-40h range with Atomic Battery Base 200mAh)
  2. README has dedicated battery base section with specs, recharge guidance, and realistic expectations
  3. CLAUDE.md documents ADC constraint (read after WiFi disconnect), extended RTC memory layout, and new config.py constants
**Plans**: TBD

Plans:
- [ ] 09-01: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8 -> 9
Note: Phase 4 and Phase 5 can run in parallel with Phase 2-3 (independent tracks).

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. RTC Memory Layout Extension | 0/1 | Planning complete | - |
| 2. Battery Voltage Reading | 0/1 | Planning complete | - |
| 3. Low Battery Warning | 0/1 | Planning complete | - |
| 4. Wake Cycle Counter | 0/1 | Planning complete | - |
| 5. LED Power Reduction | 0/1 | Planning complete | - |
| 6. WiFi Channel Fast Reconnect | 0/1 | Planning complete | - |
| 7. Power Configuration Constants | 0/1 | Planning complete | - |
| 8. Logging Control | 0/1 | Planning complete | - |
| 9. Documentation Update | 0/0 | Not started | - |
