# Guida Setup VS Code + MicroPython per M5Stack ATOM

Questa guida ti accompagnerà attraverso la configurazione completa dell'ambiente di sviluppo VS Code per programmare il tuo M5Stack ATOM con MicroPython e controllare il tuo SwitchBot Lock Pro.

## 📋 Prerequisiti

### Hardware
- **M5Stack ATOM** (ESP32-PICO-D4)
- Cavo USB Type-C
- Computer con Windows, macOS o Linux

### Software
- Python 3.x installato sul tuo computer
- VS Code (Visual Studio Code)
- Driver USB per ESP32 (se necessario)

---

## 🔧 Parte 1: Installazione Software

### 1.1 Installare Visual Studio Code

1. Scarica VS Code da: https://code.visualstudio.com/
2. Installa seguendo le istruzioni per il tuo sistema operativo
3. Avvia VS Code

### 1.2 Installare l'estensione MicroPython

1. Apri VS Code
2. Vai su Extensions (icona quadrata sulla barra laterale sinistra) o premi `Ctrl+Shift+X` (Windows/Linux) / `Cmd+Shift+X` (macOS)
3. Cerca **"MicroPico"** o **"Pymakr"** (opzioni consigliate):
   - **MicroPico** (consigliato per semplicità): by paulober
   - **Pymakr** (più features): by Pycom

4. Clicca su "Install" per installare l'estensione

### 1.3 Installare esptool per il flashing

Apri un terminale e installa `esptool`:

```bash
pip install esptool
```

Verifica l'installazione:

```bash
esptool.py version
```

---

## 📥 Parte 2: Installare MicroPython sul M5Stack ATOM

### 2.1 Scaricare il Firmware MicroPython

1. Vai su: https://micropython.org/download/ESP32_GENERIC/
2. Scarica il firmware **v1.26.1** per ESP32:
   - File: `ESP32_GENERIC-20241129-v1.24.1.bin` (o versione simile)
   - Oppure usa: https://micropython.org/resources/firmware/ESP32_GENERIC-20241129-v1.24.1.bin

### 2.2 Identificare la Porta Seriale

**Windows:**
```bash
# Nel Device Manager, cerca "Ports (COM & LPT)"
# Annota la porta COM (es. COM3, COM4, ecc.)
```

**macOS/Linux:**
```bash
ls /dev/tty.* # macOS
ls /dev/ttyUSB* # Linux
```

La porta dovrebbe essere simile a:
- macOS: `/dev/tty.usbserial-xxxx` o `/dev/tty.SLAB_USBtoUART`
- Linux: `/dev/ttyUSB0` o `/dev/ttyACM0`

### 2.3 Flash del Firmware MicroPython

**Passo 1: Cancella la flash (importante!)**

```bash
esptool.py --port COM3 erase_flash
```

Sostituisci `COM3` con la tua porta seriale.

**Passo 2: Flash del firmware**

```bash
esptool.py --chip esp32 --port COM3 --baud 460800 write_flash -z 0x1000 ESP32_GENERIC-20241129-v1.24.1.bin
```

Sostituisci:
- `COM3` con la tua porta
- `ESP32_GENERIC-20241129-v1.24.1.bin` con il nome del file scaricato

**Note:**
- Durante il flash, potrebbe essere necessario tenere premuto il pulsante BOOT sull'M5Stack ATOM
- Il processo richiede circa 30-60 secondi

### 2.4 Verificare l'Installazione

Usa un terminale seriale per verificare:

```bash
# Installa screen (macOS/Linux) o usa PuTTY (Windows)
screen /dev/tty.usbserial-xxxx 115200

# Oppure usa Python
python -m serial.tools.miniterm COM3 115200
```

Dovresti vedere il prompt MicroPython:
```
>>>
```

Prova:
```python
>>> print("Hello M5Stack ATOM!")
Hello M5Stack ATOM!
```

Esci con `Ctrl+A` poi `K` (screen) o `Ctrl+]` (miniterm).

---

## 💻 Parte 3: Configurare VS Code per MicroPython

### 3.1 Configurare l'Estensione MicroPico

1. Apri VS Code
2. Premi `Ctrl+Shift+P` (Windows/Linux) o `Cmd+Shift+P` (macOS)
3. Digita "MicroPico: Configure Project"
4. Seleziona la porta seriale del tuo M5Stack ATOM
5. Dovrebbe apparire una barra di stato in basso che mostra la connessione

### 3.2 Oppure: Configurare Pymakr

Se usi Pymakr:

1. Clicca sull'icona Pymakr nella barra laterale
2. Clicca su "Add Device"
3. Seleziona la porta seriale
4. La configurazione verrà salvata in `pymakr.conf`

---

## 🔑 Parte 4: Ottenere le Credenziali SwitchBot

### 4.1 Ottenere il Token Bearer

1. Apri l'app **SwitchBot** sul tuo smartphone
2. Vai su **Profilo** → **Impostazioni**
3. Vai su **App Version** e tappa 10 volte
4. Apparirà l'opzione **Developer Options**
5. Entra in **Developer Options**
6. Copia il **Token** (questo è il tuo Bearer Token)

### 4.2 Ottenere il Device ID

Il Device ID può essere ottenuto tramite API SwitchBot:

**Metodo 1: Usando curl (Linux/macOS/Windows con Git Bash)**

```bash
curl -X GET "https://api.switch-bot.com/v1.1/devices" \
  -H "Authorization: TUO_TOKEN_QUI"
```

**Metodo 2: Usando Python**

```python
import requests

token = "TUO_TOKEN_QUI"
headers = {"Authorization": token}
response = requests.get("https://api.switch-bot.com/v1.1/devices", headers=headers)
print(response.json())
```

Cerca il tuo **Lock Pro** nell'elenco dei dispositivi e copia il `deviceId`.

---

## 🚀 Parte 5: Configurare e Caricare il Codice

### 5.1 Clonare/Scaricare questo Repository

```bash
git clone https://github.com/filippolmt/m5stack-atom-switchbot-lock-pro.git
cd m5stack-atom-switchbot-lock-pro
```

Oppure scarica lo ZIP da GitHub e estrailo.

### 5.2 Aprire il Progetto in VS Code

```bash
code .
```

Oppure: File → Open Folder → Seleziona la cartella del progetto

### 5.3 Configurare le Credenziali

1. Copia il file `config_template.py` e rinominalo in `config.py`:

```bash
cp config_template.py config.py
```

2. Apri `config.py` in VS Code
3. Modifica con i tuoi dati:

```python
# Configurazione Wi-Fi
WIFI_SSID = "NomeDelTuoWiFi"
WIFI_PASSWORD = "PasswordDelTuoWiFi"

# Configurazione SwitchBot API
SWITCHBOT_TOKEN = "IlTuoBearerToken"
SWITCHBOT_DEVICE_ID = "IlTuoDeviceID"

# Configurazione GPIO (lascia invariato per M5Stack ATOM)
BUTTON_GPIO = 39  # GPIO39 è il pulsante integrato

# Configurazione debounce (in millisecondi)
DEBOUNCE_MS = 200
```

4. Salva il file

### 5.4 Caricare i File sul M5Stack ATOM

**Usando MicroPico:**

1. Assicurati che il dispositivo sia connesso (vedi barra di stato in basso)
2. Apri `config.py`
3. Premi `Ctrl+Shift+P` e seleziona "MicroPico: Upload current file to Pico"
4. Ripeti per `main.py`

**Usando Pymakr:**

1. Clicca con il tasto destro sulla cartella del progetto
2. Seleziona "Upload project to device"
3. Attendi il completamento del caricamento

**Usando ampy (alternativa da command line):**

```bash
# Installa ampy
pip install adafruit-ampy

# Carica i file
ampy --port COM3 put config.py
ampy --port COM3 put main.py
```

### 5.5 Eseguire il Programma

**Opzione 1: Esecuzione automatica**

Rinomina `main.py` in modo che venga eseguito automaticamente al boot:
```bash
# Il file main.py viene già eseguito automaticamente da MicroPython
```

**Opzione 2: Esecuzione manuale via REPL**

1. Apri il terminale seriale in VS Code (o usa screen/miniterm)
2. Nel prompt `>>>`, digita:

```python
>>> import main
```

Oppure:

```python
>>> exec(open('main.py').read())
```

---

## 🎮 Parte 6: Utilizzo

### 6.1 Prima Esecuzione

Al primo avvio, dovresti vedere nel terminale seriale:

```
==================================================
M5Stack ATOM - SwitchBot Lock Pro Controller
==================================================
Connessione a Wi-Fi: NomeDelTuoWiFi...
....
✓ Connesso a Wi-Fi!
Configurazione rete:
  IP:      192.168.1.100
  Netmask: 255.255.255.0
  Gateway: 192.168.1.1
  DNS:     192.168.1.1

✓ Controller SwitchBot inizializzato
  Device ID: xxxxxxxxxxxxx
✓ Pulsante configurato su GPIO39
  Debounce: 200ms
  Trigger: IRQ_FALLING (pressione)

==================================================
Sistema pronto! Premi il pulsante per toggle lock.
==================================================
```

### 6.2 Uso Normale

1. **Premi il pulsante** sull'M5Stack ATOM (il pulsante centrale)
2. Il sistema invierà un comando al SwitchBot Lock Pro
3. Nel terminale vedrai:

```
>>> Pulsante premuto! <<<
Invio comando al SwitchBot Lock Pro...
✓ Comando inviato con successo! Status: 200
Risposta: {"statusCode":100,"body":{},"message":"success"}
```

### 6.3 Verificare lo Stato del Sistema

Puoi accedere al REPL MicroPython mentre il programma è in esecuzione:

1. Premi `Ctrl+C` per interrompere il loop
2. Vedrai il prompt `>>>`
3. Puoi eseguire comandi Python o ispezionare variabili

Per riavviare:
```python
>>> import main
```

---

## 🔍 Troubleshooting

### Problema: Non riesco a connettermi al dispositivo

**Soluzione:**
- Verifica che il cavo USB sia funzionante (prova un altro cavo)
- Installa i driver USB: https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers
- Su Linux, aggiungi il tuo utente al gruppo `dialout`:
  ```bash
  sudo usermod -a -G dialout $USER
  ```
  Poi riavvia il sistema

### Problema: Errore durante il flash del firmware

**Soluzione:**
- Prova a ridurre il baud rate: usa `--baud 115200` invece di `460800`
- Tieni premuto il pulsante BOOT durante il flash
- Usa un cavo USB di qualità migliore

### Problema: Wi-Fi non si connette

**Soluzione:**
- Verifica SSID e password in `config.py`
- Assicurati che il Wi-Fi sia 2.4GHz (ESP32 non supporta 5GHz)
- Verifica che il router sia raggiungibile

### Problema: Errore API SwitchBot (status != 200)

**Soluzione:**
- Verifica che il token sia corretto (copia-incolla attentamente)
- Verifica che il Device ID sia corretto
- Il comando potrebbe richiedere `"unlock"` o `"lock"` a seconda dello stato attuale
- Controlla i log della risposta API per dettagli

### Problema: Il pulsante non risponde

**Soluzione:**
- Verifica che il GPIO sia corretto (39 per M5Stack ATOM)
- Prova ad aumentare il valore di `DEBOUNCE_MS` in `config.py`
- Controlla i log seriali per errori

### Problema: Out of Memory

**Soluzione:**
- Il codice include `gc.collect()` per la gestione della memoria
- Se continui ad avere problemi, riavvia il dispositivo
- Considera di ridurre il numero di richieste consecutive

---

## 📚 Risorse Utili

### Documentazione
- **MicroPython:** https://docs.micropython.org/
- **ESP32 MicroPython:** https://docs.micropython.org/en/latest/esp32/quickref.html
- **SwitchBot API:** https://github.com/OpenWonderLabs/SwitchBotAPI
- **M5Stack ATOM:** https://docs.m5stack.com/en/core/atom_lite

### Community
- **MicroPython Forum:** https://forum.micropython.org/
- **M5Stack Community:** https://community.m5stack.com/

### Tools
- **Thonny IDE:** Alternativa a VS Code, più semplice per principianti: https://thonny.org/
- **mpremote:** Tool ufficiale MicroPython: `pip install mpremote`

---

## 🔒 Note di Sicurezza

⚠️ **IMPORTANTE:**

1. **NON committare `config.py` su Git!** Contiene credenziali sensibili
   - Il file è già incluso in `.gitignore`

2. **Proteggi il tuo Bearer Token:**
   - Non condividerlo pubblicamente
   - Non includerlo in screenshot o log pubblici

3. **Wi-Fi sicuro:**
   - Usa WPA2/WPA3 per il tuo Wi-Fi
   - Non usare reti pubbliche per dispositivi IoT

---

## 🆘 Supporto

Se hai problemi o domande:

1. Controlla la sezione Troubleshooting sopra
2. Verifica i log seriali per messaggi di errore dettagliati
3. Apri una Issue su GitHub: https://github.com/filippolmt/m5stack-atom-switchbot-lock-pro/issues

---

## 📝 Licenza

Vedi il file `LICENSE` nella root del repository.

---

**Buon coding! 🚀**
