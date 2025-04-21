import os
import tempfile
import traceback
import subprocess
import logging
from huggingface_hub import logging as hf_logging
import json
import threading

# Configurar el nivel de logging de huggingface_hub
hf_logging.set_verbosity_info()
# Configurar el nivel de logging general
logging.basicConfig(level=logging.INFO)

os.environ["KMP_DUPLICATE_LIB_OK"] = "True"

from flask import Flask, request, jsonify, send_from_directory, render_template
from faster_whisper import WhisperModel
from flask_cors import CORS, cross_origin

app = Flask(
    __name__, static_folder="web", static_url_path=""
)  # Añadimos static_folder y static_url_path
# Configurar CORS para permitir peticiones desde cualquier origen
CORS(app)

# Inicializar los modelos Whisper
try:
    print("Initializing Whisper models...")
    device = "cpu"  # Usar CPU dentro del contenedor
    #device = "cuda"
    model_dir = "/app/models"
    model_es = WhisperModel("large-v3-turbo", device=device, download_root=model_dir)
    model_eu = WhisperModel("xezpeleta/whisper-large-v3-eu-ct2", device=device, download_root=model_dir)
    print(f"Whisper models initialized. Using device: {device}")
except Exception as e:
    print(f"Error initializing Whisper models: {e}")
    traceback.print_exc()
    exit(1)  # Salir con un código de error

# Variables globales para el estado del servidor
transcription_status = {"status": "free", "file": None}
transcription_lock = threading.Lock()
transcription_queue = [] # Cola de transcripciones

# Ruta absoluta a la carpeta de audios (¡AJUSTA ESTA RUTA A TU CONFIGURACIÓN!)
AUDIO_DIRECTORY = os.path.abspath("/app/audios")  # Ruta dentro del contenedor
# Ruta absoluta a la carpeta de audios normalizados
NORMALIZED_AUDIO_DIRECTORY = os.path.abspath(
    "/app/normalized_audios"
)  # Ruta dentro del contenedor
# Ruta absoluta a la carpeta de transcripciones
TRANSCRIPTION_DIRECTORY = os.path.abspath(
    "/app/transcriptions"
)  # Ruta dentro del contenedor

EVALUATION_DIRECTORY = os.path.abspath(
    "/app/evaluations"
)
REFTEXT_DIRECTORY = os.path.abspath(
    "/app/textos"
)

# Crear los directorios si no existen
for directory in [AUDIO_DIRECTORY, NORMALIZED_AUDIO_DIRECTORY, TRANSCRIPTION_DIRECTORY, EVALUATION_DIRECTORY, REFTEXT_DIRECTORY]:
    if not os.path.exists(directory):
        os.makedirs(directory)

def convert_to_wav(input_file, output_file):
    """Convierte un archivo de audio a WAV usando ffmpeg."""
    print(f"Convirtiendo a WAV: {input_file}...")
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-i",
                input_file,
                "-vn",  # Sin video
                "-acodec",
                "pcm_s16le",  # Formato WAV
                "-ar",
                "16000",  # Frecuencia de muestreo
                "-ac",
                "1",  # Mono
                "-y",  # Sobreescribir el archivo de salida
                output_file,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        print(f"Archivo convertido a WAV: {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"Error al convertir a WAV: {e}")
        print(f"Salida de error: {e.stderr}")
        raise

def normalize_audio(input_file, output_file):
    """Normaliza el volumen de un archivo de audio usando ffmpeg."""
    print(f"Normalizando audio: {input_file}...")
    temp_output_file = output_file.replace(".wav", "_temp_norm.wav")
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-i",
                input_file,
                "-ar",
                "16000",
                "-af",
                "loudnorm=I=-16:TP=-1.5:LRA=11",  # Normalización de volumen
                "-y",  # Sobreescribir el archivo de salida
                temp_output_file,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        print(f"Audio normalizado. Archivo guardado en: {temp_output_file}")
        os.replace(temp_output_file, output_file)
        print(f"Archivo movido a: {output_file}")
        if input_file != output_file:
            os.remove(input_file)
            print(f"Archivo de entrada eliminado: {input_file}")
    except subprocess.CalledProcessError as e:
        print(f"Error al normalizar el audio: {e}")
        print(f"Salida de error: {e.stderr}")
        raise
    finally:
        if os.path.exists(temp_output_file):
            print(f"Eliminando archivo temporal: {temp_output_file}")
            os.remove(temp_output_file)

def transcribe_audio(audio_path, retranscribe):
    try:
        print(f"transcribe_audio: Iniciando transcripcion para {audio_path}")
        # Obtener el nombre del archivo sin extension
        file_name_without_extension = os.path.splitext(os.path.basename(audio_path))[0]
        # Ruta del archivo en AUDIO_DIRECTORY
        #audio_file_in_directory = os.path.join(AUDIO_DIRECTORY, os.path.basename(audio_path))
        audio_file_in_directory = audio_path
        # Copiar el archivo a AUDIO_DIRECTORY
        #print(f"Copiando {audio_path} a {audio_file_in_directory}")
        #os.makedirs(os.path.dirname(audio_file_in_directory), exist_ok=True)
        #os.replace(audio_path, audio_file_in_directory)
        #print(f"Archivo copiado a {audio_file_in_directory}")
        # Crear un archivo temporal para el wav
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav_file:
            temp_wav_path = temp_wav_file.name
            print(f"transcribe_audio: Archivo temporal wav creado en: {temp_wav_path}")
        # Convertir a WAV
        print(f"transcribe_audio: Convirtiendo a WAV: {audio_file_in_directory}")
        convert_to_wav(audio_file_in_directory, temp_wav_path)
        # Guardar el archivo normalizado directamente en la carpeta
        normalized_audio_file = os.path.join(NORMALIZED_AUDIO_DIRECTORY, f"{file_name_without_extension}_normalized.wav")
        # Normalizar el audio
        print(f"transcribe_audio: Normalizando audio: {temp_wav_path}")
        normalize_audio(temp_wav_path, normalized_audio_file)
        print(f"transcribe_audio: Archivo normalizado guardado en: {normalized_audio_file}")

        # Detectar el idioma
        print(f"transcribe_audio: Detectando idioma")
        segments, info = model_es.transcribe(normalized_audio_file, task="transcribe")
        detected_language = info.language
        print(f"transcribe_audio: Idioma detectado: {detected_language}")
        # Seleccionar el modelo y el idioma según el idioma detectado
        if detected_language == "es":
            model = model_es
            language = "es"
            initial_prompt = "Texto leido por un niño"
        else:
            model = model_eu
            language = "eu"
            initial_prompt = "Haur batek irakurritako testua"
        # Transcribir el audio
        print(f"transcribe_audio: Transcribiendo audio")
        segments, info = model.transcribe(
            normalized_audio_file,
            word_timestamps=True,
            chunk_length=12,
            suppress_blank=False,
            patience=2,
            language=language,
            initial_prompt=initial_prompt
        )
        print("transcribe_audio: Transcripcion completada")

        transcription = []
        for segment in segments:
            for word in segment.words:
                transcription.append({
                    'word': word.word,
                    'start': word.start,
                    'end': word.end,
                    'probability': word.probability
                })
                print(f"  [%.2fs -> %.2fs] {word.word} {word.probability}" % (word.start, word.end))
        # Guardar la transcripcion directamente en la carpeta
        transcription_file = os.path.join(TRANSCRIPTION_DIRECTORY, f"{file_name_without_extension}.json")
        with open(transcription_file, 'w', encoding='utf-8') as f:
            json.dump(transcription, f, ensure_ascii=False, indent=4)
        print(f"transcribe_audio: Transcripcion guardada en: {transcription_file}")
        return transcription
    except Exception as e:
        print(f"transcribe_audio: Error during transcription: {e}")
        traceback.print_exc()
        return None
    
def process_next_in_queue():
    """Procesa el siguiente archivo en la cola de transcripción."""
    global transcription_queue
    print(f"process_next_in_queue: Comprobando cola. Estado: {transcription_status['status']}, Cola: {transcription_queue}")
    if transcription_status['status'] == 'free' and transcription_queue:
        next_audio_path = transcription_queue.pop(0)
        print(f"process_next_in_queue: Procesando el siguiente archivo en la cola: {next_audio_path}")
        start_transcription_thread(next_audio_path)
    else:
        print("process_next_in_queue: No hay archivos en la cola o el servidor esta ocupado.")

def start_transcription_thread(audio_path):
    """Inicia la transcripción en un hilo separado."""
    print("start_transcription_thread: Iniciando")
    # Ya no se adquiere el lock aquí.
    transcription_status['status'] = 'busy'
    transcription_status['file'] = audio_path
    print(f"start_transcription_thread: Iniciando hilo para {audio_path}. Estado: {transcription_status}")
    thread = threading.Thread(target=transcribe_audio_with_callback, args=(audio_path, False, transcription_complete_callback))
    thread.start()
    print(f"start_transcription_thread: Hilo iniciado para {audio_path}")

def transcribe_audio_with_callback(audio_path, retranscribe, callback):
    try:
        print(f"transcribe_audio_with_callback: Iniciando transcripcion con callback para {audio_path}")
        transcribe_audio(audio_path, retranscribe)
        print(f"transcribe_audio_with_callback: Transcripcion completada para {audio_path}")
    except Exception as e:
        print(f"transcribe_audio_with_callback: Error in transcribe_audio_with_callback: {e}")
        traceback.print_exc()
    finally:
        print(f"transcribe_audio_with_callback: Ejecutando callback para {audio_path}")
        callback()

def transcription_complete_callback():
    # Ya no se adquiere el lock aquí.
    print(f"transcription_complete_callback: Liberando lock. Estado anterior: {transcription_status}")
    transcription_status['status'] = 'free'
    transcription_status['file'] = None
    print(f"transcription_complete_callback: Lock liberado. Estado actual: {transcription_status}")
    process_next_in_queue()

@app.route('/checkestado', methods=['GET'])
@cross_origin()
def check_estado():
    filename = request.args.get('filename')
    texto = request.args.get('texto')

    print(f"check_estado: Comprobando si el lock esta bloqueado: {transcription_lock.locked()}")
    print(f"check_estado: filename={filename}, texto={texto}")  # PRINT
    if not filename:
        print("check_estado: Error - Filename is required")  # PRINT
        return jsonify({'error': 'Filename is required'}), 400
    print("check_estado: Antes de entrar en el lock")
    with transcription_lock:  # CAMBIO
        print(f"check_estado: Dentro del lock. Lock bloqueado: {transcription_lock.locked()}")
        # Buscar el archivo en AUDIO_DIRECTORY
        print("check_estado: Buscando archivo en AUDIO_DIRECTORY")  # PRINT
        audio_path = None
        for file in os.listdir(AUDIO_DIRECTORY):
            if file.startswith(filename + "."):
                audio_path = os.path.join(AUDIO_DIRECTORY, file)
                print(f"check_estado: Archivo encontrado: {audio_path}")  # PRINT
                break

        if not audio_path:
            print("check_estado: Error - Audio file not found")  # PRINT
            return jsonify({'estado': 'error', 'message': 'Audio file not found'}), 404

        # Verificar si el archivo de transcripción existe
        transcription_file = os.path.join(TRANSCRIPTION_DIRECTORY, f"{filename}.json")
        print(f"check_estado: Comprobando transcripcion: {transcription_file}")  # PRINT
        if not os.path.exists(transcription_file):
            print("check_estado: No hay transcripcion")  # PRINT
            # Si no está transcrito
            print("check_estado: Comprobando estado del servidor")  # PRINT
            if transcription_status['status'] == 'busy':
                print("check_estado: Servidor ocupado")  # PRINT
                if transcription_status['file'] == audio_path:
                    print(f"check_estado: El archivo {os.path.basename(transcription_status['file'])} se esta procesando")  # PRINT
                    return jsonify({'estado': 'procesando', 'file': os.path.basename(transcription_status['file'])})
                else:
                    print(f"check_estado: El archivo {os.path.basename(audio_path)} se ha añadido a la cola")  # PRINT
                    if audio_path not in transcription_queue:
                        transcription_queue.append(audio_path)
                    print(f"check_estado: Cola actual: {transcription_queue}")
                    return jsonify({'estado': 'en_cola', 'file': os.path.basename(audio_path), 'file_procesando': os.path.basename(transcription_status['file'])})
            else:
                print(f"check_estado: Transcribiendo {os.path.basename(audio_path)}")  # PRINT
                start_transcription_thread(audio_path)
                #return jsonify({'estado': 'procesando', 'file': os.path.basename(audio_path)})
                return jsonify({'estado': 'procesando'})

        # Si está transcrito, verificar si está evaluado
        evaluation_file = os.path.join(EVALUATION_DIRECTORY, f"{filename}.json")
        print(f"check_estado: Comprobando evaluacion: {evaluation_file}")  # PRINT
        if not os.path.exists(evaluation_file):
            print("check_estado: No hay evaluacion")  # PRINT
            #return jsonify({'estado': 'procesado', 'evaluado': 'no_evaluado'})
            return jsonify({'estado': 'procesado'})
        else:
            print("check_estado: Evaluado")  # PRINT
            #return jsonify({'estado': 'procesado', 'evaluado': 'evaluado'})
            return jsonify({'estado': 'procesado'})


@app.route('/transcribe', methods=['POST'])
@cross_origin()
def transcribe():
    global transcription_status
    with transcription_lock:
        if transcription_status['status'] == 'busy':
            return jsonify({'error': 'Server is busy', 'file': transcription_status['file']}), 409

    data = request.get_json()
    audio_path = data.get('audio_path')
    retranscribe = data.get('retranscribe', False)
    if not audio_path:
        return jsonify({'error': 'No audio path provided'}), 400
    
    # Comprobar si el archivo existe
    if not os.path.exists(audio_path):
        print(f"Error: El archivo {audio_path} no existe")
        return jsonify({'error': f'El archivo {audio_path} no existe'}), 404
    
    transcription = transcribe_audio(audio_path, retranscribe)
    if transcription is None:
        return jsonify({'error': 'Transcription failed'}), 500
    '''
    # Enviar la transcripcion al php
    try:
        response = requests.post('http://localhost:3000/update_transcription.php', json={'audio_path': audio_path, 'transcription': transcription})
        response.raise_for_status()  # Lanza una excepción si la respuesta no es exitosa
        print("Transcripcion enviada al php")
    except requests.exceptions.RequestException as e:
        print(f"Error al enviar la transcripcion al php: {e}")
        return jsonify({'error': 'Transcription failed'}), 500
    '''
    return jsonify({'transcription': transcription})


@app.route("/statusServerTranscription", methods=["GET"])
@cross_origin()
def status():
    global transcription_status
    with transcription_lock:
        return jsonify(transcription_status)

# Nueva ruta para verificar la existencia de un archivo de transcripción
@app.route('/checkaudio', methods=['GET'])
@cross_origin()
def check_audio():
    nombre_audio = request.args.get('filename')
    if not nombre_audio:
        return jsonify({'error': 'Missing filename parameter'}), 400

    # Verificar en AUDIO_DIRECTORY
    audio_exists = any(nombre_audio in f for f in os.listdir(AUDIO_DIRECTORY))

    # Verificar en NORMALIZED_AUDIO_DIRECTORY
    normalized_audio_exists = any(f"{nombre_audio}_normalized" in f for f in os.listdir(NORMALIZED_AUDIO_DIRECTORY))

    # Verificar en TRANSCRIPTION_DIRECTORY
    transcription_exists = any(f"{nombre_audio}." in f for f in os.listdir(TRANSCRIPTION_DIRECTORY))

    is_transcribed = audio_exists and normalized_audio_exists and transcription_exists

    if is_transcribed:
        return jsonify({
            'status': 'success',
            'message': f'Audio {nombre_audio} has been fully transcribed.',
            'isTranscribed': is_transcribed,
            'action': 'navigateToDiffTextPage',
            'filename': nombre_audio
        })
    else:
        missing_in = []
        if not audio_exists:
            missing_in.append('audio')
        if not normalized_audio_exists:
            missing_in.append('normalized_audio')
        if not transcription_exists:
            missing_in.append('transcription')

        return jsonify({
            'status': 'error',
            'message': f'Audio {nombre_audio} is missing in: {", ".join(missing_in)}',
            'isTranscribed': is_transcribed,
            'action': 'showError'
        }), 404


@app.route('/get_data')
def get_data():
    filename = request.args.get('filename')
    reference_text = request.args.get('referenceText')
    print(f"get_data: filename={filename}, reference_text={reference_text}")

    if not filename:
        return jsonify({'error': 'Filename is required'}), 400

    # Construir rutas a los archivos
    transcription_file = os.path.join(TRANSCRIPTION_DIRECTORY, f"{filename}.json")
    normalized_audio_file = os.path.join(NORMALIZED_AUDIO_DIRECTORY, f"{filename}_normalized.wav")

    # Determinar el archivo de texto de referencia
    if reference_text:
        reference_text_file = os.path.join(REFTEXT_DIRECTORY, f"{reference_text}.txt")
    else:
        reference_text_file = os.path.join(REFTEXT_DIRECTORY, f"{filename}.txt")

    # Verificar si el archivo de transcripción existe
    if not os.path.exists(transcription_file):
        return jsonify({'error': 'Transcription file not found'}), 404

    # Cargar la transcripción
    with open(transcription_file, 'r', encoding='utf-8') as f:
        transcription_data = json.load(f)

    # Verificar si el archivo de audio normalizado existe
    if os.path.exists(normalized_audio_file):
        normalized_audio_url = f"/normalized_audios/{filename}_normalized.wav"
    else:
        normalized_audio_url = None

    # Verificar si el archivo de texto de referencia existe
    if os.path.exists(reference_text_file):
        with open(reference_text_file, 'r', encoding='utf-8') as f:
            reference_text_content = f.read()
    else:
        reference_text_content = None

    print(reference_text_content)

    return jsonify({
        'transcription': transcription_data,
        'normalized_audio_url': normalized_audio_url,
        'reference_text': reference_text_content
    })


@app.route('/check_file_exists', methods=['GET'])
def check_file_exists():
    filename = request.args.get('filename')
    if not filename:
        return jsonify({'error': 'Filename is required'}), 400
    filepath = os.path.join(EVALUATION_DIRECTORY, filename)
    exists = os.path.exists(filepath)
    return jsonify({'exists': exists})

@app.route('/save_analysis_data', methods=['POST'])
def save_analysis_data():
    filename = request.args.get('filename')  # Obtener el nombre del archivo de los parámetros de la URL
    if not filename:
        return jsonify({'error': 'Filename is required'}), 400
    filepath = os.path.join(EVALUATION_DIRECTORY, filename)
    try:
        data = request.get_json()
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)
        return jsonify({'message': 'Data saved successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/load_analysis_data', methods=['GET'])
def load_analysis_data():
    filename = request.args.get('filename')
    if not filename:
        return jsonify({'error': 'Filename is required'}), 400
    filepath = os.path.join(EVALUATION_DIRECTORY, filename)
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            return jsonify(data), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    else:
        return jsonify({'error': 'File not found'}), 404

@app.route('/delete_analysis_data', methods=['DELETE'])
def delete_analysis_data():
    filename = request.args.get('filename')
    if not filename:
        return jsonify({'error': 'Filename is required'}), 400
    filepath = os.path.join(EVALUATION_DIRECTORY, filename)
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
            return jsonify({'message': 'File deleted successfully'}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    else:
        return jsonify({'error': 'File not found'}), 404

# Servir archivos estáticos desde las carpetas
@app.route("/normalized_audios/<path:filename>")
def serve_normalized_audio(filename):
    return send_from_directory(NORMALIZED_AUDIO_DIRECTORY, filename)


@app.route("/transcriptions/<path:filename>")
def serve_transcription(filename):
    return send_from_directory(TRANSCRIPTION_DIRECTORY, filename)


# Ruta para servir el index.html de Flutter
@app.route("/")
def serve_flutter():
    return send_from_directory(app.static_folder, "index.html")


# Ruta para servir cualquier otro archivo estático de Flutter
@app.route("/<path:path>")
def serve_flutter_static(path):
    if os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return serve_flutter()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)
