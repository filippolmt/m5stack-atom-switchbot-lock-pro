# VS Code + MicroPython Setup Guide for M5Stack ATOM

This guide walks you through the full VS Code development environment setup to program your M5Stack ATOM with MicroPython and control your SwitchBot Lock Pro.

## 📋 Prerequisites

### Hardware

- **M5Stack ATOM** (ESP32-PICO-D4)
- USB Type-C cable
- Computer running Windows, macOS, or Linux

### Software

- Python 3.x installed on your computer
- VS Code (Visual Studio Code)
- USB driver for ESP32 (if needed)

---

## 🔧 Part 1: Software Installation

### 1.1 Install Visual Studio Code

1. Download VS Code from: https://code.visualstudio.com/
2. Install following the instructions for your OS
3. Launch VS Code

### 1.2 Install the MicroPython Extension (optional)

1. Open VS Code
2. Go to Extensions (square icon on the left sidebar) or press `Ctrl+Shift+X` (Windows/Linux) / `Cmd+Shift+X` (macOS)
3. Search for **"MicroPico"** (by paulober) and click **Install** if you want IDE integration

### 1.3 Install esptool for flashing

Open a terminal and install `esptool`:

```bash
pip install esptool
```

Verify the installation:

```bash
esptool version
```

---

## 📥 Part 2: Install MicroPython on the M5Stack ATOM

### 2.1 Download the MicroPython Firmware

1. Go to: https://micropython.org/download/M5STACK_ATOM/
2. Download the latest firmware for ESP32 (v1.26.1 or later):
   - Example file: `M5STACK_ATOM-20250911-v1.26.1.bin`
   - Or use: https://micropython.org/resources/firmware/M5STACK_ATOM-20250911-v1.26.1.bin

### 2.2 Identify the Serial Port

**Windows:**

```bash
# In Device Manager, look under "Ports (COM & LPT)"
# Note the COM port (e.g., COM3, COM4, etc.)
```

**macOS/Linux:**

```bash
ls /dev/cu.* # macOS
ls /dev/ttyUSB* # Linux
```

The port should look like:

- macOS: `/dev/cu.usbserial-xxxx` or `/dev/cu.SLAB_USBtoUART`
- Linux: `/dev/ttyUSB0` or `/dev/ttyACM0`

### 2.3 Flash the MicroPython Firmware

**Step 1: Erase flash (important!)**

```bash
PORT="/dev/cu.usbserial-9152F26338" # Replace with your port
esptool --port $PORT --baud 460800 erase-flash
```

**Step 2: Flash the firmware**

```bash
PORT="/dev/cu.usbserial-9152F26338" # Replace with your port
esptool --port $PORT --baud 460800 write-flash 0x1000 M5STACK_ATOM-20250911-v1.26.1.bin
```

Replace:

- `$PORT` with your port
- `M5STACK_ATOM-20250911-v1.26.1.bin` with the downloaded file name

**Notes:**

- During flashing, you may need to hold the BOOT button on the M5Stack ATOM
- The process takes about 30-60 seconds

### 2.4 Verify the Installation

Use a serial terminal to verify:

```bash
# Install screen (macOS/Linux) or use PuTTY (Windows)
screen $PORT 115200

# Or use Python
python -m serial.tools.miniterm $PORT 115200
```

You should see the MicroPython prompt:

```
>>>
```

Try:

```python
>>> print("Hello M5Stack ATOM!")
Hello M5Stack ATOM!
```

Exit with `Ctrl+A` then `K` (screen) or `Ctrl+]` (miniterm).

---

## 💻 Part 3: Configure VS Code for MicroPython

### 3.1 Configure the MicroPico Extension (optional)

1. Open VS Code
2. Press `Ctrl+Shift+P` (Windows/Linux) or `Cmd+Shift+P` (macOS)
3. Type "MicroPico: Configure Project"
4. Select the serial port of your M5Stack ATOM
5. A status bar should appear at the bottom showing the connection

---

## 🔑 Part 4: Obtain SwitchBot Credentials

### 4.1 Get the Bearer Token and Secret

1. Open the **SwitchBot** app on your smartphone
2. Go to **Profile** → **Settings**
3. Go to **App Version** and tap 10 times
4. The **Developer Options** entry appears
5. Enter **Developer Options**
6. Copy both **Token** and **Secret** (both are required for API v1.1 signing)

### 4.2 Get the Device ID

Device listing on API v1.1 requires signed headers (token + secret). Use Python to generate the signature and call the API:

```python
import requests
import hmac
import hashlib
import base64
import time
import uuid

token = "YOUR_TOKEN_HERE"
secret = "YOUR_SECRET_HERE"

nonce = uuid.uuid4().hex
t = str(int(time.time() * 1000))
string_to_sign = token + t + nonce
sign = base64.b64encode(
    hmac.new(secret.encode(), string_to_sign.encode(), digestmod=hashlib.sha256).digest()
).decode().upper()

headers = {
    "Authorization": token,
    "sign": sign,
    "nonce": nonce,
    "t": t,
}

response = requests.get("https://api.switch-bot.com/v1.1/devices", headers=headers)
print(response.status_code, response.text)
```

Find your **Lock Pro** in the device list and copy the `deviceId`.

---

## 🚀 Part 5: Configure and Upload the Code

### 5.1 Clone/Download this Repository

```bash
git clone https://github.com/filippolmt/m5stack-atom-switchbot-lock-pro.git
cd m5stack-atom-switchbot-lock-pro
```

Or download the ZIP from GitHub and extract it.

### 5.2 Open the Project in VS Code

```bash
code .
```

Or: File → Open Folder → select the project folder

### 5.3 Configure Credentials

1. Copy the file `config_template.py` and rename it to `config.py`:

```bash
cp config_template.py config.py
```

2. Open `config.py` in VS Code
3. Edit with your data:

```python
# Wi-Fi configuration
WIFI_SSID = "YourWiFiName"
WIFI_PASSWORD = "YourWiFiPassword"

# SwitchBot API configuration
SWITCHBOT_TOKEN = "YourBearerToken"
SWITCHBOT_SECRET = "YourTokenSecret"
SWITCHBOT_DEVICE_ID = "YourDeviceID"

# GPIO configuration (leave as is for M5Stack ATOM)
BUTTON_GPIO = 39  # GPIO39 is the built-in button

# Debounce configuration (in milliseconds)
DEBOUNCE_MS = 200
```

4. Save the file

### 5.4 Upload Files to the M5Stack ATOM (mpremote)

Use `mpremote` to copy the files (replace the port with yours, e.g., `/dev/cu.usbserial-XXXX` on macOS, `COM3` on Windows, `/dev/ttyUSB0` on Linux):

```bash
mpremote connect /dev/cu.usbserial-XXXX cp main.py :main.py
mpremote connect /dev/cu.usbserial-XXXX cp config.py :config.py
```

### 5.5 Run the Program

**Option 1: Run via mpremote**

```bash
mpremote connect /dev/cu.usbserial-XXXX run main.py
```

**Option 2: Automatic execution at boot**

```bash
# main.py is already executed automatically by MicroPython
```

**Option 3: Manual execution via REPL**

1. Open the serial terminal in VS Code (or use screen/miniterm)
2. In the `>>>` prompt, type:

```python
>>> import main
```

Or:

```python
>>> exec(open('main.py').read())
```

---

## 🎮 Usage

### 6.1 First Run

On first start, you should see in the serial terminal:

```
==================================================
M5Stack ATOM - SwitchBot Lock Pro Controller
==================================================
Connecting to Wi-Fi: YourWiFi...
....
✓ Connected to Wi-Fi!
Network configuration:
  IP:      192.168.1.100
  Netmask: 255.255.255.0
  Gateway: 192.168.1.1
  DNS:     192.168.1.1

✓ SwitchBot controller initialized
  Device ID: xxxxxxxxxxxxx
✓ Button configured on GPIO39
  Debounce: 200ms
  Trigger: IRQ_FALLING (press)

==================================================
System ready! Press the button to toggle lock.
==================================================
```

### 6.2 Normal Use

1. **Press the button** on the M5Stack ATOM (center button)
2. The system sends a command to the SwitchBot Lock Pro
3. In the terminal you will see:

```
>>> Button pressed! <<<
Sending command to SwitchBot Lock Pro...
✓ Command sent successfully! Status: 200
Response: {"statusCode":100,"body":{},"message":"success"}
```

### 6.3 Check System State

You can access the MicroPython REPL while the program is running:

1. Press `Ctrl+C` to stop the loop
2. You will see the `>>>` prompt
3. You can run Python commands or inspect variables

To restart:

```python
>>> import main
```

---

## 🔍 Troubleshooting

### Problem: Cannot connect to the device

**Solution:**

- Make sure the USB cable works (try another cable)
- Install USB drivers: https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers
- On Linux, add your user to the `dialout` group:
  ```bash
  sudo usermod -a -G dialout $USER
  ```
  Then restart the system

### Problem: Error while flashing the firmware

**Solution:**

- Try lowering the baud rate: use `--baud 115200` instead of `460800`
- Hold the BOOT button during flashing
- Use a higher quality USB cable

### Problem: Wi-Fi does not connect

**Solution:**

- Check SSID and password in `config.py`
- Make sure Wi-Fi is 2.4GHz (ESP32 does not support 5GHz)
- Verify the router is reachable

### Problem: SwitchBot API error (status != 200)

**Solution:**

- Check that the token is correct (copy/paste carefully)
- Check that the Device ID is correct
- The command may need to be `"unlock"` or `"lock"` depending on current state
- Check the API response logs for details

### Problem: The button does not respond

**Solution:**

- Verify the GPIO is correct (39 for M5Stack ATOM)
- Try increasing the `DEBOUNCE_MS` value in `config.py`
- Check the serial logs for errors

### Problem: Out of Memory

**Solution:**

- The code includes `gc.collect()` for memory management
- If issues continue, reboot the device
- Consider reducing the number of consecutive requests

---

## 📚 Useful Resources

### Documentation

- **MicroPython:** https://docs.micropython.org/
- **ESP32 MicroPython:** https://docs.micropython.org/en/latest/esp32/quickref.html
- **SwitchBot API:** https://github.com/OpenWonderLabs/SwitchBotAPI
- **M5Stack ATOM:** https://docs.m5stack.com/en/core/atom_lite

### Community

- **MicroPython Forum:** https://forum.micropython.org/
- **M5Stack Community:** https://community.m5stack.com/

### Tools

- **Thonny IDE:** Simpler alternative to VS Code for beginners: https://thonny.org/
- **mpremote:** Official MicroPython tool: `pip install mpremote`

---

## 🔒 Security Notes

⚠️ **IMPORTANT:**

1. **Do NOT commit `config.py` to Git!** It contains sensitive credentials

   - The file is already included in `.gitignore`

2. **Protect your Bearer Token:**

   - Do not share it publicly
   - Do not include it in screenshots or public logs

3. **Secure Wi-Fi:**
   - Use WPA2/WPA3 for your Wi-Fi
   - Do not use public networks for IoT devices
