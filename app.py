from flask import Flask, request, jsonify
import whisper
import os
import logging
import ffmpeg
import uuid
import sys
import threading
import shutil
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Налаштування логування
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Очищаємо попередні обробники логування
for handler in logger.handlers[:]:
    logger.removeHandler(handler)

# Налаштування обробника для виведення логів у stdout
handler = logging.StreamHandler(stream=sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

logger.info("Starting Flask app...")

# Налаштування тимчасової директорії для файлів
TEMP_DIR = "temp_files"
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)
    logger.info(f"Created temporary directory: {TEMP_DIR}")

# Завантаження моделі Whisper при старті
logger.info("Loading Whisper model at startup...")
try:
    model = whisper.load_model("base")
    logger.info("Whisper model loaded successfully at startup")
except Exception as e:
    logger.error(f"Failed to load Whisper model at startup: {str(e)}")
    raise

# Максимальний розмір файлу (у байтах, наприклад, 10 MB)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

# Дозволені розширення файлів
ALLOWED_EXTENSIONS = {'.ogg', '.oga', '.wav', '.mp3'}

def allowed_file(filename):
    """Перевіряє, чи має файл дозволене розширення."""
    return os.path.splitext(filename)[1].lower() in ALLOWED_EXTENSIONS

def cleanup_files(*file_paths):
    """Очищає тимчасові файли."""
    for file_path in file_paths:
        try:
            if file_path and os.path.exists(file_path):
                if os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                else:
                    os.remove(file_path)
                logger.info(f"Cleaned up file: {file_path}")
        except Exception as e:
            logger.error(f"Failed to clean up file {file_path}: {str(e)}")

@app.route('/')
def home():
    """Тестовий ендпоінт для перевірки роботи сервісу."""
    logger.info("Received request to /")
    return "Whisper Speech-to-Text API"

@app.route("/transcribe", methods=["POST"])
def transcribe():
    """Ендпоінт для транскрипції аудіофайлів."""
    logger.info("Received request to /transcribe")
    logger.info(f"Request headers: {request.headers}")

    # Перевірка розміру запиту
    content_length = request.content_length
    if content_length and content_length > MAX_FILE_SIZE:
        logger.error(f"File too large: {content_length} bytes, max allowed: {MAX_FILE_SIZE} bytes")
        return jsonify({"error": "File too large, maximum size is 10 MB"}), 413

    content_type = request.headers.get('Content-Type', '')
    logger.info(f"Content-Type: {content_type}")

    unique_id = str(uuid.uuid4())
    input_path = os.path.join(TEMP_DIR, f"temp_audio_{unique_id}.ogg")
    audio_path = os.path.join(TEMP_DIR, f"temp_audio_{unique_id}.wav")

    try:
        # Обробка вхідних даних
        if content_type == 'application/octet-stream':
            # Обробка бінарних даних напряму
            logger.info("Processing binary data (application/octet-stream)")
            data = request.get_data()
            if not data:
                logger.error("No data provided in request")
                return jsonify({"error": "No data provided"}), 400

            # Перевірка розміру даних
            if len(data) > MAX_FILE_SIZE:
                logger.error(f"Binary data too large: {len(data)} bytes, max allowed: {MAX_FILE_SIZE} bytes")
                return jsonify({"error": "Binary data too large, maximum size is 10 MB"}), 413

            # Зберігаємо бінарні дані у файл
            with open(input_path, 'wb') as f:
                f.write(data)
            logger.info(f"Saved binary data to {input_path}")

        else:
            # Обробка multipart/form-data
            logger.info(f"Request files: {request.files}")
            logger.info(f"Request form: {request.form}")
            if "audio" not in request.files:
                logger.error("No audio file provided in request")
                return jsonify({"error": "No audio file provided"}), 400

            audio_file = request.files["audio"]
            filename = secure_filename(audio_file.filename)
            if not allowed_file(filename):
                logger.error(f"Invalid file extension for {filename}, allowed: {ALLOWED_EXTENSIONS}")
                return jsonify({"error": f"Invalid file extension, allowed: {ALLOWED_EXTENSIONS}"}), 400

            logger.info(f"Audio file received: {filename}")

            # Перевірка розміру файлу
            audio_file.seek(0, os.SEEK_END)
            file_size = audio_file.tell()
            audio_file.seek(0)
            if file_size > MAX_FILE_SIZE:
                logger.error(f"File too large: {file_size} bytes, max allowed: {MAX_FILE_SIZE} bytes")
                return jsonify({"error": "File too large, maximum size is 10 MB"}), 413

            # Зберігаємо файл
            audio_file.save(input_path)
            logger.info(f"Saved audio file to {input_path}")

        # Перевірка, чи файл створено
        if not os.path.exists(input_path):
            logger.error(f"Failed to save file: {input_path}")
            return jsonify({"error": "Failed to save audio file"}), 500

        # Конвертація OGG у WAV
        logger.info("Converting OGG to WAV...")
        try:
            stream = ffmpeg.input(input_path)
            stream = ffmpeg.output(stream, audio_path, acodec="pcm_s16le", ac=1, ar="16000")
            process = ffmpeg.run_async(stream, pipe_stdout=True, pipe_stderr=True, overwrite_output=True)
            stdout, stderr = process.communicate()

            if process.returncode != 0:
                logger.error(f"FFmpeg failed with return code {process.returncode}")
                raise Exception(f"FFmpeg failed: {stderr.decode() if stderr else 'Unknown error'}")

            if stdout:
                for line in stdout.decode().splitlines():
                    logger.info(f"FFmpeg stdout: {line.strip()}")
            if stderr:
                for line in stderr.decode().splitlines():
                    logger.info(f"FFmpeg stderr: {line.strip()}")

            logger.info("Conversion successful")
            file_size = os.path.getsize(audio_path) / 1024
            logger.info(f"Converted WAV file size: {file_size:.2f} KB")
        except Exception as e:
            logger.error(f"FFmpeg conversion failed: {str(e)}")
            raise Exception(f"Failed to convert audio: {str(e)}")

        # Перевірка, чи WAV-файл створено
        if not os.path.exists(audio_path):
            logger.error(f"Failed to convert file: {audio_path}")
            return jsonify({"error": "Failed to convert audio file"}), 500

        # Транскрипція
        logger.info("Starting transcription...")
        logger.info(f"Audio file path: {audio_path}")
        logger.info("Calling Whisper transcribe...")

        result = [None]
        exception = [None]

        def run_transcription():
            try:
                result[0] = model.transcribe(audio_path, fp16=False, verbose=True)
            except Exception as e:
                exception[0] = e

        # Запускаємо транскрипцію у окремому потоці з таймаутом
        transcription_thread = threading.Thread(target=run_transcription)
        transcription_thread.start()
        transcription_thread.join(timeout=300)  # Таймаут 5 хвилин

        if transcription_thread.is_alive():
            logger.error("Transcription timed out after 300 seconds")
            raise Exception("Transcription timed out")

        if exception[0] is not None:
            logger.error(f"Whisper transcription failed: {str(exception[0])}")
            raise exception[0]

        logger.info("Whisper transcribe completed")
        logger.info("Transcription completed, processing result...")
        text = result[0]["text"]
        logger.info(f"Transcription successful: {text}")

        # Повертаємо результат
        response = jsonify({"text": text})
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        return response

    except Exception as e:
        logger.error(f"Transcription failed: {str(e)}")
        return jsonify({"error": str(e)}), 500

    finally:
        # Очищаємо тимчасові файли
        cleanup_files(input_path, audio_path)

@app.errorhandler(500)
def internal_error(error):
    """Обробка внутрішніх помилок сервера."""
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({"error": "Internal server error"}), 500

@app.errorhandler(413)
def request_entity_too_large(error):
    """Обробка помилки, коли файл занадто великий."""
    logger.error("Request entity too large")
    return jsonify({"error": "File too large, maximum size is 10 MB"}), 413

@app.errorhandler(400)
def bad_request(error):
    """Обробка помилки неправильного запиту."""
    logger.error(f"Bad request: {str(error)}")
    return jsonify({"error": "Bad request"}), 400

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8888))
    app.run(host="0.0.0.0", port=port, debug=False)