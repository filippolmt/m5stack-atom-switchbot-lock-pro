# External Integrations

**Analysis Date:** 2026-03-16

## APIs & External Services

**SwitchBot API v1.1:**
- Service: SwitchBot Cloud API (`https://api.switch-bot.com/v1.1`)
- What it's used for: Lock/unlock commands sent to SwitchBot Lock Pro smart lock device
  - Endpoint: `POST /v1.1/devices/{device_id}/commands`
  - Payload: JSON `{"command": "lock"|"unlock", "parameter": "default", "commandType": "command"}`
  - SDK/Client: `urequests` (MicroPython HTTP library)
  - Auth: Token-based with HMAC-SHA256 signature
    - Header `Authorization`: Bearer token string
    - Header `sign`: HMAC-SHA256(token + timestamp + nonce, secret) encoded as Base64 uppercase
    - Header `nonce`: 16-byte random hex string
    - Header `t`: Millisecond timestamp (Unix epoch after NTP sync)

## Data Storage

**Databases:**
- Not applicable - No persistent database used

**File Storage:**
- Local filesystem only - RTC memory used for Wi-Fi BSSID caching (survives deep sleep):
  - Bytes 0-5: MAC address (BSSID) of last connected AP
  - Byte 6: Wi-Fi channel number
  - Byte 7: Valid flag (0xAA when cached)
  - Location: `machine.RTC().memory()` in `main.py` functions `save_wifi_config()`, `load_wifi_config()`

**Caching:**
- RTC memory cache - Fast reconnect by storing strongest-RSSI AP's BSSID + channel from previous successful connection
  - Saves ~1-2 seconds on reconnect after deep sleep (full scan avoided)
  - Fallback: If RTC cache invalid, performs full `wlan.scan()` to find AP by SSID and RSSI

## Authentication & Identity

**Auth Provider:**
- Custom token + secret based auth (SwitchBot proprietary)
  - Implementation: Inline HMAC-SHA256 signature generation in `SwitchBotController._build_auth_headers()`
  - Details:
    - Token sourced from SwitchBot mobile app settings
    - Secret sourced from SwitchBot mobile app settings
    - Signature includes timestamp and nonce to prevent replay attacks
    - No OAuth, no 3rd-party identity service
  - Error handling: `send_command()` returns `"auth_error"` on HTTP 401; no retry on auth failures

## Monitoring & Observability

**Error Tracking:**
- Not integrated - Errors logged to serial console only (115200 baud)
- LED feedback provides real-time device status:
  - Red (3 blinks) = API error
  - Red (6 fast blinks) = Auth error (401)
  - Orange (3 blinks) = Wi-Fi timeout
  - Yellow (2 blinks) = NTP sync failed (continuing)
  - Yellow (4 blinks) = Time sync error (aborted)

**Logs:**
- Serial output to UART (115200 baud)
- Print statements throughout code for debugging
- No log aggregation; manual serial terminal monitoring required

## CI/CD & Deployment

**Hosting:**
- Not cloud-hosted - Firmware runs on M5Stack ATOM microcontroller device in user's home
- Device wakes on button press only; no remote control plane

**CI Pipeline:**
- GitHub Actions - Runs pytest test suite on push and pull requests
- Workflow: Docker builds image → pytest runs 53 unit tests (conftest.py injects MicroPython stubs)
- Tests run on CPython 3.13+ via hardware abstraction in `tests/conftest.py`

**Deployment:**
- Manual via `mpremote`:
  ```bash
  mpremote connect /dev/cu.usbserial-XXXX cp main.py :main.py
  mpremote connect /dev/cu.usbserial-XXXX cp config.py :config.py
  ```
- No OTA (over-the-air) updates implemented

## Environment Configuration

**Required env vars:**
- Not env vars; all config in `config.py` file:
  - `WIFI_SSID` - Network name
  - `WIFI_PASSWORD` - Network password
  - `SWITCHBOT_TOKEN` - SwitchBot API token
  - `SWITCHBOT_SECRET` - SwitchBot API secret
  - `SWITCHBOT_DEVICE_ID` - SwitchBot Lock Pro device ID

**Secrets location:**
- `config.py` (git-ignored) - Stored locally on device; no secret manager integration
- Must be created manually from `config_template.py` template
- Credentials never transmitted except to official SwitchBot API over HTTPS

## Webhooks & Callbacks

**Incoming:**
- Not applicable - Device initiates all connections; no webhook subscriptions

**Outgoing:**
- HTTP POST to SwitchBot API only
- No outgoing webhooks or callbacks implemented

## Network & Wi-Fi

**Wi-Fi:**
- 802.11 b/g/n (2.4 GHz)
- Connection via `network.WLAN(network.STA_IF)` (station mode)
- Optional static IP to reduce DHCP overhead (saves ~500ms-1s)
  - Format in `config.py`: `WIFI_STATIC_IP = ("192.168.1.100", "255.255.255.0", "192.168.1.1", "8.8.8.8")`
  - If not defined, DHCP used
- Cached BSSID fast reconnect (`connect_wifi()` in `main.py` line 402)

**NTP:**
- ntptime module synchronizes system clock via NTP (default server)
- Conditional sync: Skipped if RTC year >= 2024 (survives deep sleep)
- Blocks if network down; non-critical but required for valid API timestamps

**HTTPS/TLS:**
- SwitchBot API requires HTTPS
- mbedTLS used for TLS handshake (ESP32 system heap resident)
- CRITICAL CONSTRAINT: System heap fragmentation can break mbedTLS RSA operations; see CLAUDE.md for forbidden patterns

---

*Integration audit: 2026-03-16*
