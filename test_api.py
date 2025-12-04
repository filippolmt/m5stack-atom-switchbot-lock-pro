"""
Test Script per SwitchBot API
Usa questo script per testare le credenziali SwitchBot prima di caricare il codice sul dispositivo.
"""

import requests
import json

# Configura le tue credenziali qui
SWITCHBOT_TOKEN = "TuoBearerToken"
SWITCHBOT_DEVICE_ID = "TuoDeviceID"

API_BASE_URL = "https://api.switch-bot.com/v1.1"


def test_get_devices():
    """Test per ottenere la lista di tutti i dispositivi"""
    url = f"{API_BASE_URL}/devices"
    headers = {
        "Authorization": SWITCHBOT_TOKEN,
        "Content-Type": "application/json"
    }
    
    print("=" * 60)
    print("Test: Ottenere lista dispositivi")
    print("=" * 60)
    
    try:
        response = requests.get(url, headers=headers)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("\n✓ Successo!")
            print("\nDispositivi trovati:")
            print(json.dumps(data, indent=2))
        else:
            print(f"\n✗ Errore!")
            print(f"Risposta: {response.text}")
            
    except Exception as e:
        print(f"\n✗ Eccezione: {e}")


def test_get_device_status():
    """Test per ottenere lo stato di un dispositivo specifico"""
    url = f"{API_BASE_URL}/devices/{SWITCHBOT_DEVICE_ID}/status"
    headers = {
        "Authorization": SWITCHBOT_TOKEN,
        "Content-Type": "application/json"
    }
    
    print("\n" + "=" * 60)
    print("Test: Ottenere stato dispositivo")
    print("=" * 60)
    
    try:
        response = requests.get(url, headers=headers)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("\n✓ Successo!")
            print("\nStato dispositivo:")
            print(json.dumps(data, indent=2))
        else:
            print(f"\n✗ Errore!")
            print(f"Risposta: {response.text}")
            
    except Exception as e:
        print(f"\n✗ Eccezione: {e}")


def test_send_command(command="unlock"):
    """Test per inviare un comando al dispositivo"""
    url = f"{API_BASE_URL}/devices/{SWITCHBOT_DEVICE_ID}/commands"
    headers = {
        "Authorization": SWITCHBOT_TOKEN,
        "Content-Type": "application/json"
    }
    
    data = {
        "command": command,
        "parameter": "default",
        "commandType": "command"
    }
    
    print("\n" + "=" * 60)
    print(f"Test: Inviare comando '{command}' al dispositivo")
    print("=" * 60)
    print(f"\nATTENZIONE: Questo comando controllerà realmente il tuo lock!")
    confirm = input("Vuoi continuare? (s/n): ")
    
    if confirm.lower() != 's':
        print("Comando annullato.")
        return
    
    try:
        response = requests.post(url, headers=headers, json=data)
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("\n✓ Comando inviato con successo!")
            print("\nRisposta:")
            print(json.dumps(result, indent=2))
        else:
            print(f"\n✗ Errore!")
            print(f"Risposta: {response.text}")
            
    except Exception as e:
        print(f"\n✗ Eccezione: {e}")


def main():
    """Funzione principale per i test"""
    print("\n" + "=" * 60)
    print("SwitchBot API Test Script")
    print("=" * 60)
    
    if SWITCHBOT_TOKEN == "TuoBearerToken":
        print("\n❌ ERRORE: Devi configurare SWITCHBOT_TOKEN!")
        print("Modifica questo file e inserisci il tuo token.")
        return
        
    if SWITCHBOT_DEVICE_ID == "TuoDeviceID":
        print("\n❌ ERRORE: Devi configurare SWITCHBOT_DEVICE_ID!")
        print("Modifica questo file e inserisci il tuo device ID.")
        print("\nPuoi ottenere il device ID eseguendo prima solo test_get_devices()")
        return
    
    print("\nMenu Test:")
    print("1. Ottenere lista dispositivi")
    print("2. Ottenere stato dispositivo")
    print("3. Inviare comando UNLOCK")
    print("4. Eseguire tutti i test (no comando)")
    print("0. Esci")
    
    choice = input("\nScegli un'opzione: ")
    
    if choice == "1":
        test_get_devices()
    elif choice == "2":
        test_get_device_status()
    elif choice == "3":
        test_send_command("unlock")
    elif choice == "4":
        test_get_devices()
        test_get_device_status()
    elif choice == "0":
        print("Arrivederci!")
        return
    else:
        print("Opzione non valida!")
        return
    
    print("\n" + "=" * 60)
    print("Test completato!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
