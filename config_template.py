# Configuration for M5Stack ATOM - SwitchBot Lock Pro
# Copy this file to config.py and edit with your data

# Wi-Fi configuration
WIFI_SSID = "[ENTER_SSID]"
WIFI_PASSWORD = "[ENTER_PASSWORD]"

# SwitchBot API configuration
SWITCHBOT_TOKEN = "[ENTER_TOKEN]"
SWITCHBOT_SECRET = "[ENTER_SECRET]"
SWITCHBOT_DEVICE_ID = "[ENTER_DEVICE_ID_LOCK_PRO]"

# GPIO configuration
BUTTON_GPIO = 39  # GPIO39 is the built-in button on M5Stack ATOM

# Wi-Fi TX power in dBm (optional, saves battery if router is nearby)
# Default max is ~20.5dBm (~150mA). Lower values reduce current draw.
# Examples: 8 (~2dBm, very close), 13 (~8.5dBm, same room), 17 (~15dBm, one wall)
# Comment out or remove to use default max power.
# WIFI_TX_POWER = 8
