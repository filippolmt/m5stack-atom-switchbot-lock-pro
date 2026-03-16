# Phase 7: Power Configuration Constants - Context

**Gathered:** 2026-03-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Add optional configurable constants to config.py for LED brightness, battery thresholds, and logging verbosity. main.py reads these with try/except fallback to sensible defaults (same pattern as WIFI_STATIC_IP).

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
- Exact constant names: `LED_BRIGHTNESS`, `BATTERY_LOW_THRESHOLD`, `BATTERY_CRITICAL_THRESHOLD`
- Default values when not set in config.py (current hardcoded values)
- Pattern: `try: from config import X; except: X = default` at usage points or top of main.py
- Whether to group config reads in a single section or keep lazy per-usage
- Update config_template.py with new optional constants and comments
- Test strategy: mock config module with/without optional constants

</decisions>

<canonical_refs>
## Canonical References

### Existing Config Pattern
- `main.py` `WIFI_STATIC_IP` handling — try/except import pattern
- `config_template.py` — Template for user config

### Constants to Make Configurable
- `main.py` `LED_BRIGHTNESS = 32` (Phase 5)
- `main.py` `BATTERY_LOW_MV = 3300` (Phase 3)

</canonical_refs>

<code_context>
## Existing Code Insights

### Established Patterns
- `WIFI_STATIC_IP`: try/except with `hasattr(config, ...)` or direct try/except import
- All config values loaded early, used throughout

### Integration Points
- `main.py` constants section — add config overrides
- `config_template.py` — add new optional constants with documentation

</code_context>

<specifics>
## Specific Ideas

No specific requirements — all delegated to Claude.

</specifics>

<deferred>
## Deferred Ideas

None.

</deferred>

---

*Phase: 07-power-configuration-constants*
*Context gathered: 2026-03-16*
