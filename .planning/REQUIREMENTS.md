# Requirements: M5Stack ATOM SwitchBot Lock Pro — Battery Optimization

**Defined:** 2026-03-16
**Core Value:** Massima durata della batteria mantenendo l'affidabilità del lock/unlock

## v1 Requirements

Requirements for this milestone. Each maps to roadmap phases.

### Battery Monitoring

- [ ] **BATT-01**: Firmware legge tensione batteria via ADC su GPIO 33 (voltage divider 1:1) ad ogni ciclo wake
- [ ] **BATT-02**: LED arancione lampeggia quando tensione batteria scende sotto soglia low-battery (~3.3V)
- [ ] **BATT-03**: Tensione batteria stampata su seriale ad ogni wake per diagnostica
- [ ] **BATT-04**: Contatore wake cycle memorizzato in RTC memory (incrementato ad ogni pressione)
- [ ] **BATT-05**: Layout RTC memory esteso da 8 a 12 byte con backward compatibility (flag 0xBB)

### LED Optimization

- [ ] **LED-01**: Luminosità LED ridotta da 64 a 32 (default) per risparmio energetico
- [ ] **LED-02**: Durata blink feedback ridotta (halved rispetto ai valori attuali)
- [ ] **LED-03**: Warning LED arancione per low-battery integrato nel flusso wake

### WiFi Optimization

- [ ] **WIFI-01**: Canale WiFi memorizzato in RTC memory passato a `wlan.connect()` per fast reconnect (~100ms più veloce)

### Power Profile

- [ ] **PWR-01**: Costanti configurabili in config.py: luminosità LED, soglie batteria, verbosità logging
- [ ] **PWR-02**: Print seriali ridotte in modalità produzione (configurabile via config.py)
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

- **PWR-04**: Skip LED feedback completamente (modalità ultra-low-power)
- **PWR-05**: Profilo potenza selezionabile (normal/eco/ultra-eco)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Hardware mod (taglio chip USB) | Invalida garanzia, richiede saldatura, non firmware |
| Light sleep mode | 80x più consumo del deep sleep, non adatto a device single-action |
| WiFi power save modes | Rompono TLS handshake (confermato da test) |
| OTA firmware update | Complessità e consumo eccessivi per questo milestone |
| Watchdog timer | Causa MBEDTLS_ERR_MPI_ALLOC_FAILED (confermato) |
| Multi-device support | Un lock per config è sufficiente |
| Percentage display su LED | ADC ESP32 troppo impreciso per stima % affidabile in v1 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| BATT-01 | TBD | Pending |
| BATT-02 | TBD | Pending |
| BATT-03 | TBD | Pending |
| BATT-04 | TBD | Pending |
| BATT-05 | TBD | Pending |
| LED-01 | TBD | Pending |
| LED-02 | TBD | Pending |
| LED-03 | TBD | Pending |
| WIFI-01 | TBD | Pending |
| PWR-01 | TBD | Pending |
| PWR-02 | TBD | Pending |
| PWR-03 | TBD | Pending |
| DOC-01 | TBD | Pending |
| DOC-02 | TBD | Pending |
| DOC-03 | TBD | Pending |

**Coverage:**
- v1 requirements: 15 total
- Mapped to phases: 0
- Unmapped: 15 ⚠️

---
*Requirements defined: 2026-03-16*
*Last updated: 2026-03-16 after initial definition*
