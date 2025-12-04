# M5Stack ATOM - SwitchBot Lock Pro Controller

Controlla il tuo **SwitchBot Lock Pro** premendo semplicemente il pulsante del tuo **M5Stack ATOM**! 🚪🔐

Questo progetto fornisce una soluzione completa per integrare il tuo M5Stack ATOM (ESP32) con l'API SwitchBot per controllare un SwitchBot Lock Pro tramite Wi-Fi.

## 🌟 Caratteristiche

- ✅ **Connessione Wi-Fi** automatica con configurazione semplice
- ✅ **Lettura pulsante GPIO** con interrupt e debounce hardware
- ✅ **Integrazione API SwitchBot** con autenticazione Bearer token
- ✅ **Gestione memoria** ottimizzata per ESP32
- ✅ **Codice robusto** con gestione errori completa
- ✅ **Setup guidato** completo per VS Code + MicroPython

## 📋 Requisiti

### Hardware
- **M5Stack ATOM** (ESP32-PICO-D4)
- Cavo USB Type-C
- **SwitchBot Lock Pro** (configurato e funzionante)

### Software
- **MicroPython v1.26.1** (o compatibile) per ESP32
- **VS Code** con estensione MicroPython (MicroPico o Pymakr)
- Python 3.x sul tuo computer
- Account SwitchBot con API token

## 🚀 Quick Start

### 1. Setup Ambiente (Prima Volta)

Segui la guida completa in **[SETUP.md](SETUP.md)** per:
- Installare VS Code e l'estensione MicroPython
- Flashare MicroPython sul tuo M5Stack ATOM
- Configurare l'ambiente di sviluppo
- Ottenere le credenziali SwitchBot (Token e Device ID)

### 2. Configurazione

```bash
# Clona il repository
git clone https://github.com/filippolmt/m5stack-atom-switchbot-lock-pro.git
cd m5stack-atom-switchbot-lock-pro

# Copia e configura il file di configurazione
cp config_template.py config.py
```

Modifica `config.py` con i tuoi dati:

```python
# Configurazione Wi-Fi
WIFI_SSID = "TuoSSID"
WIFI_PASSWORD = "TuaPassword"

# Configurazione SwitchBot API
SWITCHBOT_TOKEN = "TuoBearerToken"
SWITCHBOT_DEVICE_ID = "TuoDeviceID"

# GPIO pulsante M5Stack ATOM (già preconfigurato)
BUTTON_GPIO = 39
```

### 3. Upload sul Dispositivo

1. Apri il progetto in VS Code
2. Connetti il M5Stack ATOM via USB
3. Carica i file sul dispositivo:
   - `config.py`
   - `main.py`

### 4. Esegui!

Il programma si avvia automaticamente. Premi il pulsante sull'M5Stack ATOM per controllare il lock!

## 📁 Struttura del Progetto

```
.
├── main.py              # Script principale MicroPython
├── config_template.py   # Template di configurazione
├── config.py           # Configurazione (da creare, non in git)
├── SETUP.md            # Guida setup completa
├── README.md           # Questo file
├── LICENSE             # Licenza
└── .gitignore          # Esclude config.py e altri file sensibili
```

## 🔧 Come Funziona

1. **All'avvio**: Il dispositivo si connette automaticamente al Wi-Fi configurato
2. **Inizializzazione**: Configura il controller SwitchBot e il pulsante GPIO
3. **Loop principale**: Rimane in ascolto di pressioni del pulsante
4. **Quando premi il pulsante**: 
   - Debounce hardware evita pressioni multiple accidentali
   - Invia una richiesta POST all'API SwitchBot
   - Toggle dello stato del lock (unlock/lock)
   - Mostra il risultato nel terminale seriale

## 📡 API SwitchBot

Il progetto utilizza l'API SwitchBot v1.1:

- **Endpoint**: `https://api.switch-bot.com/v1.1/devices/{deviceId}/commands`
- **Autenticazione**: Bearer token
- **Comando**: `unlock` (toggle basato sullo stato attuale)

Documentazione completa: https://github.com/OpenWonderLabs/SwitchBotAPI

## 🔍 Monitoring e Debug

Connetti al terminale seriale (115200 baud) per vedere:

```
==================================================
M5Stack ATOM - SwitchBot Lock Pro Controller
==================================================
Connessione a Wi-Fi: MioWiFi...
✓ Connesso a Wi-Fi!
Configurazione rete:
  IP:      192.168.1.100
  ...

✓ Controller SwitchBot inizializzato
✓ Pulsante configurato su GPIO39

==================================================
Sistema pronto! Premi il pulsante per toggle lock.
==================================================

>>> Pulsante premuto! <<<
Invio comando al SwitchBot Lock Pro...
✓ Comando inviato con successo! Status: 200
```

## 🛠️ Troubleshooting

Consulta la sezione **Troubleshooting** in [SETUP.md](SETUP.md) per:
- Problemi di connessione al dispositivo
- Errori durante il flash del firmware
- Problemi di connessione Wi-Fi
- Errori API SwitchBot
- Problemi con il pulsante
- Gestione memoria

## 🔒 Sicurezza

⚠️ **IMPORTANTE:**

- `config.py` contiene credenziali sensibili ed è escluso da Git
- Non condividere il tuo Bearer Token
- Usa una rete Wi-Fi sicura (WPA2/WPA3)
- Considera l'uso di una VLAN dedicata per dispositivi IoT

## 🤝 Contribuire

Contributi sono benvenuti! Per favore:

1. Fai un fork del progetto
2. Crea un branch per la tua feature (`git checkout -b feature/AmazingFeature`)
3. Commit le tue modifiche (`git commit -m 'Add some AmazingFeature'`)
4. Push al branch (`git push origin feature/AmazingFeature`)
5. Apri una Pull Request

## 📝 Licenza

Distribuito sotto licenza MIT. Vedi `LICENSE` per maggiori informazioni.

## 🙏 Riconoscimenti

- [MicroPython](https://micropython.org/) - Python per microcontrollori
- [M5Stack](https://m5stack.com/) - Hardware ESP32 di qualità
- [SwitchBot](https://www.switch-bot.com/) - Smart home devices

## 📞 Supporto

- 📖 [Guida Setup Completa](SETUP.md)
- 🐛 [Segnala un Bug](https://github.com/filippolmt/m5stack-atom-switchbot-lock-pro/issues)
- 💬 [Discussioni](https://github.com/filippolmt/m5stack-atom-switchbot-lock-pro/discussions)

---

**Made with ❤️ for the IoT community**