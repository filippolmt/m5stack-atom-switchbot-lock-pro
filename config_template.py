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

# Static IP (optional, saves ~500ms-1s per connection by skipping DHCP)
# Format: (IP, subnet mask, gateway, DNS)
# WIFI_STATIC_IP = ("192.168.1.100", "255.255.255.0", "192.168.1.1", "8.8.8.8")
