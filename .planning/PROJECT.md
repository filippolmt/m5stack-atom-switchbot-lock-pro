# M5Stack ATOM SwitchBot Lock Pro — Battery Optimization

## What This Is

Ottimizzazione del firmware MicroPython per M5Stack ATOM Lite che controlla una SwitchBot Lock Pro, con l'obiettivo di massimizzare la durata della batteria Atomic Battery Base (200mAh, 3.7V). Il dispositivo usa deep sleep tra le pressioni del pulsante e si sveglia solo per lock/unlock.

## Core Value

Massima durata della batteria mantenendo l'affidabilità del lock/unlock. Ogni milliampere e ogni millisecondo di wake time contano.

## Requirements

### Validated

<!-- Shipped and confirmed valuable — inferred from existing codebase. -->

- ✓ Short press (<1s) = UNLOCK, long press (≥1s) = LOCK — existing
- ✓ Deep sleep con wake su GPIO 39 (~10µA idle) — existing
- ✓ SwitchBot API v1.1 con HMAC-SHA256 authentication — existing
- ✓ Fast reconnect WiFi con BSSID cache in RTC memory — existing
- ✓ NTP sync condizionale (skip se RTC valido) — existing
- ✓ CPU frequency scaling (80/160MHz) — existing
- ✓ LED feedback con colori per stato (lock/unlock/errore) — existing
- ✓ Retry singolo su errore API (no retry su 401) — existing
- ✓ Early WiFi disconnect prima dei LED feedback — existing
- ✓ Static IP opzionale per skip DHCP — existing

### Active

<!-- Current scope. Building toward these. -->

- [ ] Ridurre consumo energetico durante il ciclo wake (target: -30% wake time)
- [ ] LED minimali: ridurre durata/luminosità blink per risparmiare energia
- [ ] Wake più veloce: ottimizzare path critico boot→comando→sleep
- [ ] Monitoraggio livello batteria via voltage divider della Atomic Battery Base
- [ ] Calcolo e documentazione autonomia stimata con profilo d'uso reale
- [ ] Ottimizzazione interazione con ETA9085E10 boost converter (standby 2.55µA)
- [ ] Improvement firmware: qualsiasi ottimizzazione che riduca il consumo senza sacrificare affidabilità

### Out of Scope

- WiFi configuration via web interface — complessità eccessiva per il risparmio energetico
- Multi-device support — un solo lock per config, requisito attuale soddisfacente
- OTA firmware update — aggiunge complessità e consumo, non prioritario
- Watchdog timer — rimosso in precedenza perché causa MBEDTLS_ERR_MPI_ALLOC_FAILED

## Context

- **Hardware**: M5Stack ATOM Lite (ESP32-PICO-D4, no PSRAM, 4MB flash, 520KB RAM)
- **Batteria**: Atomic Battery Base 200mAh, 3.7V, boost a 5V via ETA9085E10, standby 2.55µA, operating 39.55mA
- **Consumo attuale**: ~10µA deep sleep, ~80-150mA attivo (WiFi+API), ciclo 1-5s
- **Uso tipico**: 5-10 pressioni/giorno (uso domestico)
- **Vincolo critico**: mbedTLS system heap fragmentation — nessuna allocazione prima di `urequests.post()` (vedi CLAUDE.md)
- **Boost converter**: ETA9085E10 ha efficienza variabile — il consumo reale dalla batteria è maggiore del consumo dell'ESP32 per le perdite di conversione

## Constraints

- **mbedTLS heap**: Nessuna nuova allocazione system heap prima delle chiamate HTTPS — vincolo hardware non negoziabile
- **Single-file**: Architettura monolitica (`main.py`) per minimizzare import e heap usage
- **MicroPython v1.24.x**: Versione firmware bloccata per compatibilità mbedTLS
- **200mAh capacity**: Batteria piccola — ogni ottimizzazione conta
- **Boost efficiency**: ~85-90% tipica per ETA9085E10, quindi consumo effettivo dalla batteria = consumo ESP32 / efficienza

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Priorità massima durata vs features | L'utente preferisce sacrificare features per durata batteria | — Pending |
| LED minimali ma non eliminati | Serve feedback minimo per sapere se il comando è andato a buon fine | — Pending |
| Monitoraggio batteria via ADC | La battery base ha voltage divider, lettura possibile via GPIO | — Pending |

---
*Last updated: 2026-03-16 after initialization*
