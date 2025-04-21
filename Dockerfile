# syntax=docker/dockerfile:1

# Etapa para CPU
# Usa una imagen base con Python
FROM python:3.10-slim-buster AS cpu

WORKDIR /app
ENV PIP_CACHE_DIR=/root/.cache/pip

# Instala las dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Crear el entorno virtual
RUN python3 -m venv /opt/venv

# Instala dependencias python
COPY requirements-whisper.txt .
RUN --mount=type=cache,mode=0755,target=/root/.cache/pip /opt/venv/bin/pip install --no-cache-dir -r requirements-whisper.txt

# Instala faster-whisper
RUN --mount=type=cache,mode=0755,target=/root/.cache/pip /opt/venv/bin/pip install --no-cache-dir faster-whisper

# Descargar el modelo large-v3-turbo
RUN /opt/venv/bin/python -c "from faster_whisper import WhisperModel; WhisperModel('large-v3-turbo', device='cpu', download_root='/app/models')"
# Descargar el modelo whisper-large-v3-eu-ct2
RUN /opt/venv/bin/python -c "from faster_whisper import WhisperModel; WhisperModel('xezpeleta/whisper-large-v3-eu-ct2', device='cpu', download_root='/app/models')"

# Copia el código de la aplicación
COPY app.py .

# Crea un usuario no root
RUN useradd -ms /bin/bash appuser
# Cambia el propietario de las carpetas a appuser
RUN chown -R appuser /app /opt/venv /app/models
# Cambia al usuario appuser
USER appuser

# Expone el puerto
EXPOSE 5001

# Comando para ejecutar la aplicación
CMD ["/opt/venv/bin/python", "app.py"]