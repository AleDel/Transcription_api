# Resumen de Funcionalidades de la API de Transcripción de Audio

Esta API, desarrollada en Python con Flask, proporciona servicios para la transcripción de audio, normalización de audio, gestión de archivos y evaluación de transcripciones. Utiliza modelos de reconocimiento de voz de la librería `faster-whisper` para realizar las transcripciones.

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
