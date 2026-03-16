# Phase 6: WiFi Channel Fast Reconnect - Context

**Gathered:** 2026-03-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Pass the cached WiFi channel from RTC memory byte 6 to `wlan.connect()` for faster reconnection (~100ms saving). Channel is already cached by `save_wifi_config()` — this phase just uses it. Must fallback gracefully if cached channel is stale/wrong.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
- How to pass channel to `wlan.connect()` — MicroPython may not support `channel` kwarg directly; research needed
- Fallback strategy when cached channel is wrong (existing timeout→full scan fallback should work)
- Whether to validate channel range (1-14) before passing
- Serial output: log when channel is used vs when fallback triggers
- Test strategy: mock `wlan.connect()` to verify channel parameter is passed

</decisions>

<canonical_refs>
## Canonical References

### WiFi Implementation
- `main.py` `connect_wifi()` — Current fast reconnect with BSSID, channel not yet passed
- `main.py` `load_wifi_config()` — Returns `(bssid, channel)`, channel already available
- `.planning/research/PITFALLS.md` — WiFi channel caching gotchas

### Constraints
- `CLAUDE.md` — mbedTLS constraint (WiFi connect is before HTTPS, so channel param is safe)
- Research flag: `wlan.connect()` channel param needs hardware testing

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `load_wifi_config()` already returns `(bssid, channel)` — channel is loaded but only used for diagnostic print
- `connect_wifi()` receives `cached_bssid` and `cached_channel` params — channel param exists but isn't passed to `wlan.connect()`

### Integration Points
- `connect_wifi()` line where `wlan.connect(ssid, password, bssid=cached_bssid)` is called — add channel param here
- Existing fallback: timeout→disconnect→clear cache→full scan is already implemented

</code_context>

<specifics>
## Specific Ideas

No specific requirements — all delegated to Claude. Key unknown: whether MicroPython's `wlan.connect()` accepts a `channel` keyword argument.

</specifics>

<deferred>
## Deferred Ideas

None.

</deferred>

---

*Phase: 06-wifi-channel-fast-reconnect*
*Context gathered: 2026-03-16*
