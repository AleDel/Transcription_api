# Audio Transcription API

This API, developed in Python with Flask, provides services for audio transcription, audio normalization, file management, and transcription evaluation. It uses speech recognition models from the `faster-whisper` library to perform transcriptions.

## Docker Image Creation and Container Execution

### Build the Docker image

To build the Docker image, run the following command in the directory where the `Dockerfile` is located:

```bash
docker build -t whisper-api:latest .
```

This command will build an image called `whisper-api` with the `latest` tag.

### Run the container

To run the container, use the following command, adjusting the volume paths according to your setup:
(Remember to replace them with the real paths)

```bash
docker run -d -p 5001:5001 --name whisper-api-container -v /audios:/app/audios -v /normalized_audios:/app/normalized_audios -v /transcriptions:/app/transcriptions -v /evaluations:/app/evaluations -v /textos:/app/textos whisper-api:latest
```

**Parameter explanation:**

- `-d`: runs the container in detached mode
- `-p 5001:5001`: maps port 5001 from the container to port 5001 on the host
- `--name whisper-api-container`: assigns the name `whisper-api-container`
- `-v /audios:/app/audios`: mounts the host `/audios` directory into `/app/audios` inside the container. This is where original audio files will be stored.
- `-v /normalized_audios:/app/normalized_audios`: mounts the host `/normalized_audios` directory into `/app/normalized_audios` inside the container. This is where normalized audio files will be stored.
- `-v /transcriptions:/app/transcriptions`: mounts the host `/transcriptions` directory into `/app/transcriptions` inside the container. This is where transcriptions will be stored.
- `-v /evaluations:/app/evaluations`: mounts the host `/evaluations` directory into `/app/evaluations` inside the container. This is where evaluation files will be stored.
- `-v /textos:/app/textos`: mounts the host `/textos` directory into `/app/textos` inside the container. This is where reference texts will be stored.
- `whisper-api:latest`: specifies the image to run

**Important:** adjust the volume paths to the correct locations on your system.

## Usage Examples

### Check audio status (`/checkestado`)

To check the status of an audio file, use the following URL, replacing `34-1-3489` with the audio file name (without extension):

```bash
curl http://localhost:5001/checkestado?filename=34-1-3489
```

**Possible responses:**

- `{"estado": "procesando"}`: the file is currently being processed
- `{"estado": "en_cola", "file": "34-1-3489.wav", "file_procesando": "otro_archivo.wav"}`: the file is queued, waiting to be processed. `file` indicates the queued file and `file_procesando` the one being processed
- `{"estado": "procesado"}`: the file has already been processed
- `{"estado": "error", "message": "Audio file not found"}`: the file was not found
- `{"estado": "procesando", "file": "34-1-3489.wav"}`: the file is being processed

### Transcription queue management

If you send multiple requests to `/checkestado` for different files while the server is busy, the files will be added to the queue. For example:

1. Send a request to `http://localhost:5001/checkestado?filename=audio1`.
2. The server starts processing `audio1`.
3. Send another request to `http://localhost:5001/checkestado?filename=audio2`.
4. Since the server is busy, `audio2` is added to the queue. The response will be: `{"estado": "en_cola", "file": "audio2.wav", "file_procesando": "audio1.wav"}`
5. When `audio1` finishes processing, the server will automatically start processing `audio2`.

### Example transcription JSON

When a file is successfully transcribed, a JSON file is saved in `/app/transcriptions`. An example of this JSON file could be:

```json
json [ { "word": "Hello", "start": 0.5, "end": 1.0, "probability": 0.95 }, { "word": "world", "start": 1.2, "end": 1.8, "probability": 0.92 }, { "word": "this", "start": 2.0, "end": 2.3, "probability": 0.88 }, { "word": "is", "start": 2.3, "end": 2.4, "probability": 0.90 }, { "word": "a", "start": 2.4, "end": 2.6, "probability": 0.85 }, { "word": "test", "start": 2.6, "end": 3.2, "probability": 0.93 } ]
```

This JSON contains a list of objects, where each object represents a transcribed word with its start time (`start`), end time (`end`), and the probability that the word was transcribed correctly (`probability`).

## Main features

1. **Audio transcription:**
   - **`transcribe_audio(audio_path, retranscribe)`:**
     - Receives the path to an audio file.
     - Converts the audio to WAV format (16kHz, mono) using `ffmpeg`.
     - Normalizes the audio volume using `ffmpeg` with the `loudnorm` filter.
     - Detects the language of the audio (Spanish or Basque).
     - Uses the appropriate `faster-whisper` model to transcribe the audio.
     - Saves the transcription as JSON in `/app/transcriptions`.
     - Returns the transcription as a list of words with their start and end times.
   - **`transcribe_audio_with_callback(audio_path, retranscribe, callback)`:**
     - Transcribes an audio file and executes a callback when it finishes.
   - **`start_transcription_thread(audio_path)`:**
     - Starts transcription in a separate thread.
   - **`process_next_in_queue()`:**
     - Processes the next audio file in the transcription queue.
   - **`transcription_complete_callback()`:**
     - Runs when a transcription finishes, releases the server state, and calls `process_next_in_queue()`.

2. **Transcription queue management:**
   - The API manages a transcription queue (`transcription_queue`).
   - If the server is busy, new files are added to the queue.
   - When a transcription finishes, the next file in the queue is processed.
   - A `threading.Lock()` (`transcription_lock`) is used to ensure thread safety.
   - A `transcription_status` dictionary is used to manage the server state.

3. **Audio normalization:**
   - **`normalize_audio(input_file, output_file)`:**
     - Normalizes the audio volume to -16 LUFS with a True Peak of -1.5 dB.
     - Uses `ffmpeg` to perform the normalization.
     - Saves the normalized audio in `/app/normalized_audios`.

4. **Audio format conversion:**
   - **`convert_to_wav(input_file, output_file)`:**
     - Converts audio files to WAV format (16kHz, mono) using `ffmpeg`.

5. **API endpoints:**
   - **`/checkestado` (GET):**
     - Checks the status of a specific audio file.
     - Returns whether the file is queued, processing, processed, or not found.
     - Manages the transcription queue.
   - **`/transcribe` (POST):**
     - Receives the path to an audio file and transcribes it.
     - Returns the transcription in JSON format.
     - If the server is busy, returns a 409 error.
   - **`/statusServerTranscription` (GET):**
     - Returns the current server state (free or busy) and the file being processed.
   - **`/checkaudio` (GET):**
     - Checks whether an audio file has been fully transcribed (original audio, normalized audio, and transcription).
   - **`/get_data` (GET):**
     - Returns the transcription, the normalized audio URL, and the reference text (if available) for a given audio file.
   - **`/check_file_exists` (GET):**
     - Checks whether an evaluation file exists in `/app/evaluations`.
   - **`/save_analysis_data` (POST):**
     - Saves analysis data as JSON in `/app/evaluations`.
   - **`/load_analysis_data` (GET):**
     - Loads analysis data from a JSON file in `/app/evaluations`.
   - **`/delete_analysis_data` (DELETE):**
     - Deletes an analysis file from `/app/evaluations`.
   - **`/normalized_audios/<path:filename>` (GET):**
     - Serves normalized audio files from `/app/normalized_audios`.
   - **`/transcriptions/<path:filename>` (GET):**
     - Serves transcription files from `/app/transcriptions`.
   - **`/` (GET):**
     - Serves the Flutter app's `index.html` file.
   - **`/<path:path>` (GET):**
     - Serves any other static file from the Flutter app.

6. **Error handling:**
   - The API handles errors for:
     - missing files
     - errors during audio conversion or normalization
     - transcription errors
     - busy server state
     - missing required parameters
   - It returns appropriate HTTP status codes (400, 404, 409, 500).

7. **Directory structure:**
   - `/app/audios`: contains original audio files
   - `/app/normalized_audios`: contains normalized audio files
   - `/app/transcriptions`: contains transcription JSON files
   - `/app/evaluations`: contains evaluation JSON files
   - `/app/textos`: contains reference text files
   - `/app/models`: contains `faster-whisper` models
   - `/web`: contains the Flutter app's static files

8. **Dependencies:**
   - `flask`
   - `faster-whisper`
   - `flask-cors`
   - `ffmpeg`
   - `huggingface_hub`
   - `python-dotenv`

## Notes

- The API is designed to run inside a Docker container.
- `ffmpeg` is required for audio conversion and normalization, so it must be installed in the system or container.
- `faster-whisper` models are automatically downloaded into `/app/models`.
- `CORS` is enabled to allow requests from any origin.
- `threading` is used to manage the transcription queue.
- `logging` is used to record events.
