# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-16)

**Core value:** Massima durata della batteria mantenendo l'affidabilita del lock/unlock
**Current focus:** Phase 1: RTC Memory Layout Extension

## Current Position

Phase: 1 of 9 (RTC Memory Layout Extension)
Plan: 0 of 0 in current phase
Status: Ready to plan
Last activity: 2026-03-16 — Roadmap created

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: -
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**
- Last 5 plans: -
- Trend: -

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- mbedTLS heap constraint: all new code (ADC reads, imports) must execute AFTER urequests.post()
- RTC memory extension uses 0xBB flag for backward compatibility with existing 0xAA layout
- Battery voltage read happens after WiFi disconnect, never during active connection

### Pending Todos

None yet.

### Blockers/Concerns

- Research flag: GPIO 33 ADC accuracy on Atomic Battery Base needs hardware validation (Phase 2)
- Research flag: WiFi channel parameter in wlan.connect() needs hardware testing (Phase 6)
- Board-level deep sleep current is 4-11mA (not 10uA) — battery life estimates must use real measurements

## Session Continuity

Last session: 2026-03-16
Stopped at: Roadmap and state files created
Resume file: None
