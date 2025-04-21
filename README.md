# Resumen de Funcionalidades de la API de Transcripción de Audio

Esta API, desarrollada en Python con Flask, proporciona servicios para la transcripción de audio, normalización de audio, gestión de archivos y evaluación de transcripciones. Utiliza modelos de reconocimiento de voz de la librería `faster-whisper` para realizar las transcripciones.

## Creación de la Imagen y Ejecución del Contenedor Docker

### Creación de la Imagen Docker

Para crear la imagen Docker, ejecuta el siguiente comando en el directorio donde se encuentra el `Dockerfile`:

```bash
docker build -t whisper-api:latest .
```

Este comando construirá una imagen llamada `whisper-api` con la etiqueta `latest`.

### Ejecución del Contenedor Docker

Para ejecutar el contenedor, utiliza el siguiente comando, ajustando las rutas de los volúmenes según tu configuración:
(Recuerda sustituir por las rutas reales)

```bash
docker run -d -p 5001:5001 --name whisper-api-container -v /audios:/app/audios -v /normalized_audios:/app/normalized_ audios -v /transcriptions:/app/transcriptions -v /evaluations:/app/evaluations -v /textos:/app/textos whisper-api:latest
```
**Explicación de los parámetros:**

*   `-d`: Ejecuta el contenedor en segundo plano (detached mode).
*   `-p 5001:5001`: Mapea el puerto 5001 del contenedor al puerto 5001 del host.
*   `--name whisper-api-container`: Asigna el nombre `whisper-api-container
*   `-v /audios:/app/audios`: Monta el directorio `/audios` del host en el directorio `/app/audios` del contenedor. Aquí se guardarán los audios originales.
*   `-v /normalized_audios:/app/normalized_audios`: Monta el directorio `/normalized_audios` del host en el directorio `/app/normalized_audios` del contenedor. Aquí se guardarán los audios normalizados.
*   `-v /transcriptions:/app/transcriptions`: Monta el directorio `/transcriptions` del host en el directorio `/app/transcriptions` del contenedor. Aquí se guardarán las transcripciones.
*   `-v /evaluations:/app/evaluations`: Monta el directorio `/evaluations` del host en el directorio `/app/evaluations` del contenedor. Aquí se guardarán los archivos de evaluación.
*   `-v /textos:/app/textos`: Monta el directorio `/textos` del host en el directorio `/app/textos` del contenedor. Aquí se guardarán los textos de referencia.
*   `whisper-api:latest`: Especifica la imagen que se va a ejecutar.

**Importante:** Ajusta las rutas de los volúmenes a las rutas correctas en tu sistema.

## Ejemplos de Uso

### Comprobar el Estado de un Audio (`/checkestado`)

Para comprobar el estado de un audio, puedes usar la siguiente URL, reemplazando `34-1-3489` por el nombre del archivo de audio (sin extensión):
```bash
curl http://localhost:5001/checkestado?filename=34-1-3489
```
**Posibles respuestas:**

*   **`{"estado": "procesando"}`:** El archivo se está procesando actualmente.
*   **`{"estado": "en_cola", "file": "34-1-3489.wav", "file_procesando": "otro_archivo.wav"}`:** El archivo está en la cola, esperando a ser procesado. `file` indica el archivo que esta en cola y `file_procesando` el que se esta procesando.
*   **`{"estado": "procesado"}`:** El archivo ya ha sido procesado.
*   **`{"estado": "error", "message": "Audio file not found"}`:** El archivo no se ha encontrado.
* **`{"estado": "procesando", "file": "34-1-3489.wav"}`:** El archivo se esta procesando.

### Gestión de la Cola de Transcripciones

Si envías varias peticiones a `/checkestado` para diferentes archivos mientras el servidor está ocupado, los archivos se añadirán a la cola. Por ejemplo:

1.  Envías una petición para `http://localhost:5001/checkestado?filename=audio1`.
2.  El servidor empieza a procesar `audio1`.
3.  Envías otra petición para `http://localhost:5001/checkestado?filename=audio2`.
4.  Como el servidor está ocupado, `audio2` se añade a la cola. La respuesta será: `{"estado": "en_cola", "file": "audio2.wav", "file_procesando": "audio1.wav"}`
5.  Cuando `audio1` termine de procesarse, el servidor automáticamente empezará a procesar `audio2`.

### Ejemplo de JSON de Transcripción

Cuando un archivo se transcribe correctamente, se guarda un archivo JSON en `/app/transcriptions`. Un ejemplo de este archivo JSON podría ser:

```json
json [ { "word": "Hola", "start": 0.5, "end": 1.0, "probability": 0.95 }, { "word": "mundo", "start": 1.2, "end": 1.8, "probability": 0.92 }, { "word": "esto", "start": 2.0, "end": 2.3, "probability": 0.88 }, { "word": "es", "start": 2.3, "end": 2.4, "probability": 0.90 }, { "word": "una", "start": 2.4, "end": 2.6, "probability": 0.85 }, { "word": "prueba", "start": 2.6, "end": 3.2, "probability": 0.93 } ]
```
Este JSON contiene una lista de objetos, donde cada objeto representa una palabra transcrita con su tiempo de inicio (`start`), tiempo de fin (`end`) y la probabilidad de que la palabra haya sido transcrita correctamente (`probability`).

## Funcionalidades Principales

1.  **Transcripción de Audio:**
    *   **`transcribe_audio(audio_path, retranscribe)`:**
        *   Recibe la ruta de un archivo de audio.
        *   Convierte el audio a formato WAV (16kHz, mono) usando `ffmpeg`.
        *   Normaliza el volumen del audio usando `ffmpeg` con la librería `loudnorm`.
        *   Detecta el idioma del audio (español o euskera).
        *   Utiliza el modelo `faster-whisper` adecuado para transcribir el audio.
        *   Guarda la transcripción en formato JSON en la carpeta `/app/transcriptions`.
        *   Devuelve la transcripción como una lista de palabras con sus tiempos de inicio y fin.
    * **`transcribe_audio_with_callback(audio_path, retranscribe, callback)`:**
        * Realiza la transcripcion de un audio y ejecuta un callback cuando termina.
    * **`start_transcription_thread(audio_path)`:**
        * Inicia la transcripcion en un hilo separado.
    * **`process_next_in_queue()`:**
        * Procesa el siguiente audio en la cola de transcripciones.
    * **`transcription_complete_callback()`:**
        * Se ejecuta cuando termina una transcripcion, libera el estado del servidor y llama a `process_next_in_queue()`
2.  **Gestión de la Cola de Transcripciones:**
    *   La API gestiona una cola de transcripciones (`transcription_queue`).
    *   Si el servidor está ocupado, los nuevos archivos se añaden a la cola.
    *   Cuando una transcripción termina, se procesa el siguiente archivo en la cola.
    *   Se utiliza un `threading.Lock()` (`transcription_lock`) para garantizar la seguridad de los hilos.
    *   Se utiliza un diccionario (`transcription_status`) para gestionar el estado del servidor.

3.  **Normalización de Audio:**
    *   **`normalize_audio(input_file, output_file)`:**
        *   Normaliza el volumen del audio a -16 LUFS con un True Peak de -1.5 dB.
        *   Utiliza `ffmpeg` para realizar la normalización.
        *   Guarda el audio normalizado en la carpeta `/app/normalized_audios`.

4.  **Conversión de Formato de Audio:**
    *   **`convert_to_wav(input_file, output_file)`:**
        *   Convierte archivos de audio a formato WAV (16kHz, mono) usando `ffmpeg`.

5.  **Endpoints de la API:**
    *   **`/checkestado` (GET):**
        *   Comprueba el estado de un archivo de audio específico.
        *   Devuelve si el archivo está en cola, en proceso, procesado o si no se encuentra.
        *   Gestiona la cola de transcripciones.
    *   **`/transcribe` (POST):**
        *   Recibe la ruta de un archivo de audio y lo transcribe.
        *   Devuelve la transcripción en formato JSON.
        *   Si el servidor está ocupado, devuelve un error 409.
    *   **`/statusServerTranscription` (GET):**
        *   Devuelve el estado actual del servidor (libre u ocupado) y el archivo que se está procesando.
    *   **`/checkaudio` (GET):**
        *   Comprueba si un archivo de audio ha sido transcrito completamente (audio original, audio normalizado y transcripción).
    *   **`/get_data` (GET):**
        *   Devuelve la transcripción, la URL del audio normalizado y el texto de referencia (si existe) para un archivo de audio dado.
    *   **`/check_file_exists` (GET):**
        *   Comprueba si un archivo de evaluación existe en la carpeta `/app/evaluations`.
    *   **`/save_analysis_data` (POST):**
        *   Guarda datos de análisis en formato JSON en la carpeta `/app/evaluations`.
    *   **`/load_analysis_data` (GET):**
        *   Carga datos de análisis desde un archivo JSON en la carpeta `/app/evaluations`.
    *   **`/delete_analysis_data` (DELETE):**
        *   Borra un archivo de análisis de la carpeta `/app/evaluations`.
    *   **`/normalized_audios/<path:filename>` (GET):**
        *   Sirve archivos de audio normalizados desde la carpeta `/app/normalized_audios`.
    *   **`/transcriptions/<path:filename>` (GET):**
        *   Sirve archivos de transcripción desde la carpeta `/app/transcriptions`.
    *   **`/` (GET):**
        *   Sirve el archivo `index.html` de la aplicación Flutter.
    *   **`/<path:path>` (GET):**
        *   Sirve cualquier otro archivo estático de la aplicación Flutter.

6.  **Manejo de Errores:**
    *   La API incluye manejo de errores para:
        *   Archivos no encontrados.
        *   Errores en la conversión o normalización de audio.
        *   Errores en la transcripción.
        *   Servidor ocupado.
        *   Falta de parámetros requeridos.
    *   Devuelve códigos de estado HTTP apropiados (400, 404, 409, 500).

7.  **Estructura de Directorios:**
    *   `/app/audios`: Contiene los archivos de audio originales.
    *   `/app/normalized_audios`: Contiene los archivos de audio normalizados.
    *   `/app/transcriptions`: Contiene las transcripciones en formato JSON.
    *   `/app/evaluations`: Contiene los archivos de evaluación en formato JSON.
    *   `/app/textos`: Contiene los archivos de texto de referencia.
    *   `/app/models`: Contiene los modelos de `faster-whisper`.
    *   `/web`: Contiene los archivos estáticos de la aplicacion Flutter.

8. **Dependencias:**
    * `flask`
    * `faster-whisper`
    * `flask-cors`
    * `ffmpeg`
    * `huggingface_hub`
    * `python-dotenv`

## Consideraciones

*   La API está diseñada para ejecutarse dentro de un contenedor Docker.
*   Utiliza `ffmpeg` para la conversión y normalización de audio, por lo que debe estar instalado en el sistema o en el contenedor.
*   Los modelos de `faster-whisper` se descargan automáticamente en la carpeta `/app/models`.
*   Se utiliza `CORS` para permitir peticiones desde cualquier origen.
* Se utiliza `threading` para gestionar la cola de transcripciones.
* Se utiliza `logging` para registrar los eventos.
