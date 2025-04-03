# Usa una imagen ligera de Python
FROM python:3.11-slim

# Establecer el directorio de trabajo
WORKDIR /app

# Copiar los archivos del script y el entorno
COPY syncthing_monitor.py /app/script.py

# Instalar dependencias
RUN pip install requests python-dotenv

# Comando para ejecutar el script
CMD ["python", "/app/script.py"]
