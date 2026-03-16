# Requirements: M5Stack ATOM SwitchBot Lock Pro — Battery Optimization

**Defined:** 2026-03-16
**Core Value:** Massima durata della batteria mantenendo l'affidabilita del lock/unlock

## v1 Requirements

Requirements for this milestone. Each maps to roadmap phases.

### Battery Monitoring

- [x] **BATT-01**: Firmware legge tensione batteria via ADC su GPIO 33 (voltage divider 1:1) ad ogni ciclo wake
- [ ] **BATT-02**: LED arancione lampeggia quando tensione batteria scende sotto soglia low-battery (~3.3V)
- [x] **BATT-03**: Tensione batteria stampata su seriale ad ogni wake per diagnostica
- [ ] **BATT-04**: Contatore wake cycle memorizzato in RTC memory (incrementato ad ogni pressione)
- [x] **BATT-05**: Layout RTC memory esteso da 8 a 12 byte con backward compatibility (flag 0xBB)

### LED Optimization

- [ ] **LED-01**: Luminosita LED ridotta da 64 a 32 (default) per risparmio energetico
- [ ] **LED-02**: Durata blink feedback ridotta (halved rispetto ai valori attuali)
- [ ] **LED-03**: Warning LED arancione per low-battery integrato nel flusso wake

### WiFi Optimization

- [ ] **WIFI-01**: Canale WiFi memorizzato in RTC memory passato a `wlan.connect()` per fast reconnect (~100ms piu veloce)

### Power Profile

- [ ] **PWR-01**: Costanti configurabili in config.py: luminosita LED, soglie batteria, verbosita logging
- [ ] **PWR-02**: Print seriali ridotte in modalita produzione (configurabile via config.py)
- [ ] **PWR-03**: Livello di logging configurabile (verbose/minimal/silent)

### Documentation

- [ ] **DOC-01**: README aggiornato con autonomia reale stimata (12-40h con Atomic Battery Base 200mAh)
- [ ] **DOC-02**: Sezione dedicata alla battery base con specifiche, guida alla ricarica, e aspettative realistiche
- [ ] **DOC-03**: CLAUDE.md aggiornato con vincoli ADC e layout RTC memory esteso

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Advanced Battery

- **BATT-06**: Abort operazione WiFi/API se batteria sotto soglia critica (<3.1V)
- **BATT-07**: Stima percentuale batteria con curva di scarica LiPo (lookup table)
- **BATT-08**: Storico tensione batteria in flash per trend analysis

### Advanced Power

- **PWR-04**: Skip LED feedback completamente (modalita ultra-low-power)
- **PWR-05**: Profilo potenza selezionabile (normal/eco/ultra-eco)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Hardware mod (taglio chip USB) | Invalida garanzia, richiede saldatura, non firmware |
| Light sleep mode | 80x piu consumo del deep sleep, non adatto a device single-action |
| WiFi power save modes | Rompono TLS handshake (confermato da test) |
| OTA firmware update | Complessita e consumo eccessivi per questo milestone |
| Watchdog timer | Causa MBEDTLS_ERR_MPI_ALLOC_FAILED (confermato) |
| Multi-device support | Un lock per config e sufficiente |
| Percentage display su LED | ADC ESP32 troppo impreciso per stima % affidabile in v1 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| BATT-01 | Phase 2 | Complete |
| BATT-02 | Phase 3 | Pending |
| BATT-03 | Phase 2 | Complete |
| BATT-04 | Phase 4 | Pending |
| BATT-05 | Phase 1 | Complete |
| LED-01 | Phase 5 | Pending |
| LED-02 | Phase 5 | Pending |
| LED-03 | Phase 3 | Pending |
| WIFI-01 | Phase 6 | Pending |
| PWR-01 | Phase 7 | Pending |
| PWR-02 | Phase 8 | Pending |
| PWR-03 | Phase 8 | Pending |
| DOC-01 | Phase 9 | Pending |
| DOC-02 | Phase 9 | Pending |
| DOC-03 | Phase 9 | Pending |

**Coverage:**
- v1 requirements: 15 total
- Mapped to phases: 15
- Unmapped: 0

---
*Requirements defined: 2026-03-16*
*Last updated: 2026-03-16 after roadmap creation*
