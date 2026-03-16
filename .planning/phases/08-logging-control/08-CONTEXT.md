# Phase 8: Logging Control - Context

**Gathered:** 2026-03-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Add configurable serial output verbosity via `LOG_LEVEL` in config.py. Three levels: "verbose" (current default), "minimal" (errors + battery only), "silent" (no output). Saves UART transmission time in production.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
- Implementation: global `log()` function that checks LOG_LEVEL, or conditional wrapper
- Whether to replace all `print()` calls with `log()` or just wrap with conditionals
- Which prints are "minimal" level (errors, battery voltage, wake counter)
- Whether "silent" truly suppresses everything or keeps critical errors
- Default LOG_LEVEL when not in config.py: "verbose" (backward compatible)
- Test strategy: capture stdout, verify filtering by level

</decisions>

<canonical_refs>
## Canonical References

### Logging Points
- `main.py` — all `print()` calls throughout the file
- Phase 7 config pattern — LOG_LEVEL loaded same way as other config constants

### Constraints
- `CLAUDE.md` — no new module-level imports (but a simple function definition is safe)

</canonical_refs>

<code_context>
## Existing Code Insights

### Established Patterns
- `print(f"✓ ...")` for success, `print(f"✗ ...")` for error, `print(f"⚠ ...")` for warning
- No existing logging framework — all direct print()

### Integration Points
- Every `print()` call in main.py needs awareness of LOG_LEVEL
- Phase 7 will have established the config.py override pattern

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

*Phase: 08-logging-control*
*Context gathered: 2026-03-16*
