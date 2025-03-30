import os
import requests
import json
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv('/opt/syncthing-monitor/.env')

def enviar_alerta_telegram(mensaje):
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    params = {"chat_id": chat_id, "text": mensaje}
    requests.post(url, params=params)

def cargar_estado_previo():
    estado_file = os.getenv('ESTADO_FILE')
    if os.path.exists(estado_file):
        with open(estado_file, "r") as f:
            return json.load(f)
    return {}

def guardar_estado_actual(estado):
    with open(os.getenv('ESTADO_FILE'), "w") as f:
        json.dump(estado, f)

try:
    # Configuración desde variables de entorno
    api_url = os.getenv('SYNCTHING_API_URL')
    api_key = os.getenv('SYNCTHING_API_KEY')
    
    # Obtener lista de dispositivos
    response = requests.get(
        f"{api_url}/rest/system/config",
        headers={"X-API-Key": api_key},
        verify=False
    )
    config = response.json()
    device_map = {d["deviceID"]: d.get("name", d["deviceID"]) for d in config["devices"]}

    # Obtener estado de conexiones
    estado_actual = requests.get(
        f"{api_url}/rest/system/connections",
        headers={"X-API-Key": api_key},
        verify=False
    ).json()["connections"]

    estado_previo = cargar_estado_previo()
    alertas = []

    for device_id in device_map:
        nombre = device_map[device_id]
        conectado_ahora = estado_actual.get(device_id, {}).get("connected", False)
        conectado_antes = estado_previo.get(device_id, False)

        if conectado_ahora != conectado_antes:
            alertas.append(
                f"✅ {nombre} reconectado" if conectado_ahora
                else f"🚨 {nombre} desconectado"
            )

    if alertas:
        mensaje = "\n".join(alertas)
        enviar_alerta_telegram(mensaje)
        print("Alertas enviadas:", mensaje)

    guardar_estado_actual({
        device_id: estado_actual.get(device_id, {}).get("connected", False)
        for device_id in device_map
    })

except Exception as e:
    print("Error:", str(e))
    enviar_alerta_telegram(f"⚠️ Error en el script: {str(e)}")