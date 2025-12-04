"""
M5Stack ATOM - SwitchBot Lock Pro Controller
Script principale per controllare SwitchBot Lock Pro tramite pulsante GPIO
"""

import network
import urequests
import time
from machine import Pin
import gc

try:
    import ujson as json
except ImportError:
    import json

try:
    from config import (
        WIFI_SSID,
        WIFI_PASSWORD,
        SWITCHBOT_TOKEN,
        SWITCHBOT_DEVICE_ID,
        BUTTON_GPIO,
        DEBOUNCE_MS
    )
except ImportError:
    print("ERRORE: File config.py non trovato!")
    print("Copia config_template.py in config.py e configura i tuoi dati.")
    raise


class SwitchBotController:
    """Classe per gestire il controllo del SwitchBot Lock Pro"""
    
    API_BASE_URL = "https://api.switch-bot.com/v1.1"
    
    def __init__(self, token, device_id):
        self.token = token
        self.device_id = device_id
        self.last_button_time = 0
        self.debounce_ms = DEBOUNCE_MS
        
    def toggle_lock(self):
        """Invia comando di toggle al SwitchBot Lock Pro"""
        url = f"{self.API_BASE_URL}/devices/{self.device_id}/commands"
        headers = {
            "Authorization": self.token,
            "Content-Type": "application/json"
        }
        
        # Comando per toggle lock
        payload = {
            "command": "unlock",
            "parameter": "default",
            "commandType": "command"
        }
        data = json.dumps(payload)
        
        try:
            print("Invio comando al SwitchBot Lock Pro...")
            response = urequests.post(url, headers=headers, data=data)
            
            if response.status_code == 200:
                print(f"✓ Comando inviato con successo! Status: {response.status_code}")
                print(f"Risposta: {response.text}")
                result = True
            else:
                print(f"✗ Errore nell'invio del comando. Status: {response.status_code}")
                print(f"Risposta: {response.text}")
                result = False
                
            response.close()
            gc.collect()  # Libera memoria
            return result
            
        except Exception as e:
            print(f"✗ Eccezione durante l'invio del comando: {e}")
            gc.collect()
            return False
    
    def button_handler(self, pin):
        """Handler per l'interrupt del pulsante con debounce"""
        current_time = time.ticks_ms()
        
        # Implementa debounce
        if time.ticks_diff(current_time, self.last_button_time) > self.debounce_ms:
            self.last_button_time = current_time
            
            # Verifica che il pulsante sia effettivamente premuto (LOW)
            if pin.value() == 0:
                print("\n>>> Pulsante premuto! <<<")
                self.toggle_lock()


def connect_wifi(ssid, password, timeout=20):
    """
    Connette il dispositivo alla rete Wi-Fi
    
    Args:
        ssid: Nome della rete Wi-Fi
        password: Password della rete Wi-Fi
        timeout: Timeout in secondi per la connessione
        
    Returns:
        True se la connessione ha successo, False altrimenti
    """
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    if wlan.isconnected():
        print("Già connesso alla rete Wi-Fi")
        print(f"IP: {wlan.ifconfig()[0]}")
        return True
    
    print(f"Connessione a Wi-Fi: {ssid}...")
    wlan.connect(ssid, password)
    
    start_time = time.time()
    while not wlan.isconnected():
        if time.time() - start_time > timeout:
            print("✗ Timeout connessione Wi-Fi!")
            return False
        time.sleep(0.5)
        print(".", end="")
    
    print("\n✓ Connesso a Wi-Fi!")
    print(f"Configurazione rete:")
    print(f"  IP:      {wlan.ifconfig()[0]}")
    print(f"  Netmask: {wlan.ifconfig()[1]}")
    print(f"  Gateway: {wlan.ifconfig()[2]}")
    print(f"  DNS:     {wlan.ifconfig()[3]}")
    
    return True


def setup_button(gpio_num, controller):
    """
    Configura il pulsante GPIO con interrupt e debounce
    
    Args:
        gpio_num: Numero del pin GPIO
        controller: Istanza di SwitchBotController
        
    Returns:
        Oggetto Pin configurato
    """
    # Configura il pin con pull-up interno
    # Il pulsante su M5Stack ATOM è attivo LOW
    button = Pin(gpio_num, Pin.IN, Pin.PULL_UP)
    
    # Configura interrupt su fronte di discesa (quando viene premuto)
    button.irq(trigger=Pin.IRQ_FALLING, handler=controller.button_handler)
    
    print(f"✓ Pulsante configurato su GPIO{gpio_num}")
    print(f"  Debounce: {controller.debounce_ms}ms")
    print(f"  Trigger: IRQ_FALLING (pressione)")
    
    return button


def main():
    """Funzione principale"""
    print("\n" + "="*50)
    print("M5Stack ATOM - SwitchBot Lock Pro Controller")
    print("="*50)
    
    # Connetti al Wi-Fi
    if not connect_wifi(WIFI_SSID, WIFI_PASSWORD):
        print("Impossibile continuare senza connessione Wi-Fi")
        return
    
    print()
    
    # Inizializza il controller SwitchBot
    controller = SwitchBotController(SWITCHBOT_TOKEN, SWITCHBOT_DEVICE_ID)
    print(f"✓ Controller SwitchBot inizializzato")
    print(f"  Device ID: {SWITCHBOT_DEVICE_ID}")
    
    # Configura il pulsante
    button = setup_button(BUTTON_GPIO, controller)
    
    print("\n" + "="*50)
    print("Sistema pronto! Premi il pulsante per toggle lock.")
    print("="*50 + "\n")
    
    # Loop principale - mantiene il programma in esecuzione
    try:
        while True:
            time.sleep(1)
            # Puoi aggiungere qui altre funzionalità se necessario
            
    except KeyboardInterrupt:
        print("\n\nInterruzione da tastiera. Spegnimento...")
    finally:
        print("Pulizia risorse...")
        gc.collect()


# Avvia il programma principale
if __name__ == "__main__":
    main()
