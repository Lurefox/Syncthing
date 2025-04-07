import os
import requests
import json
import time
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Obtener el directorio de estado
estado_dir = os.getenv('ESTADO_DIR', '/app/data')
estado_file = os.path.join(estado_dir, "estado.json")

# Crear el directorio si no existe
os.makedirs(estado_dir, exist_ok=True)

# Tiempo de espera antes de alertar una desconexión (en segundos)
TIEMPO_ESPERA_DESCONEXION = 600  # 10 minutos

def enviar_alerta_telegram(mensaje):
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    params = {"chat_id": chat_id, "text": mensaje}
    requests.post(url, params=params)

def cargar_estado_previo():
    if os.path.exists(estado_file):
        with open(estado_file, "r") as f:
            return json.load(f)
    return {}

def guardar_estado_actual(estado):
    with open(estado_file, "w") as f:
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
    alertas = {}
    tiempo_actual = int(time.time())

    for device_id in device_map:
        nombre = device_map[device_id]
        conectado_ahora = estado_actual.get(device_id, {}).get("connected", False)
        info_previa = estado_previo.get(device_id, {})

        if isinstance(info_previa, dict):
            conectado_antes = info_previa.get("conectado", False)
            tiempo_desconexion = info_previa.get("desconexion_time", None)
        else:
            conectado_antes = info_previa
            tiempo_desconexion = None

        # Si el dispositivo se desconectó y antes estaba conectado
        if not conectado_ahora and conectado_antes:
            if tiempo_desconexion is None:
                estado_previo[device_id] = {
                    "conectado": False,
                    "desconexion_time": tiempo_actual
                }
            else:
                if tiempo_actual - tiempo_desconexion >= TIEMPO_ESPERA_DESCONEXION:
                    alertas[device_id] = f"🚨 {nombre} desconectado por más de 10 minutos"
                    # No actualizamos el tiempo para evitar repetir la alerta

        # Si el dispositivo se reconectó
        elif conectado_ahora and not conectado_antes:
            alertas[device_id] = f"✅ {nombre} reconectado"
            estado_previo[device_id] = {"conectado": True}

        # Si sigue conectado y no hubo cambio
        elif conectado_ahora:
            estado_previo[device_id] = {"conectado": True}

        # Si sigue desconectado pero sin cumplir los 10 minutos aún
        elif not conectado_ahora and not conectado_antes:
            estado_previo[device_id] = info_previa  # Mantiene desconexion_time

    # Enviar alertas si hay cambios
    if alertas:
        mensaje = "\n".join(alertas.values())
        enviar_alerta_telegram(mensaje)
        print("Alertas enviadas:", mensaje)

    # Guardar estado en el archivo
    guardar_estado_actual(estado_previo)

except Exception as e:
    print("Error:", str(e))
    enviar_alerta_telegram(f"⚠️ Error en el script: {str(e)}")
