from flask import Flask, request, jsonify
import whisper
import os
import logging
import ffmpeg
import uuid
import sys

app = Flask(__name__)

# Налаштування логування
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Видаляємо всі попередні обробники, щоб уникнути конфліктів
for handler in logger.handlers[:]:
    logger.removeHandler(handler)

# Налаштовуємо обробник для виводу в stdout
handler = logging.StreamHandler(stream=sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

logger.info("Starting Flask app...")

# Завантажуємо модель під час старту
logger.info("Loading Whisper model at startup...")
try:
    model = whisper.load_model("base")
    logger.info("Whisper model loaded successfully at startup")
except Exception as e:
    logger.error(f"Failed to load Whisper model at startup: {str(e)}")
    raise

@app.route('/')
def home():
    logger.info("Received request to /")
    return "Whisper Speech-to-Text API"

@app.route("/transcribe", methods=["POST"])
def transcribe():
    logger.info("Received request to /transcribe")
    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400
    
    audio_file = request.files["audio"]
    unique_id = str(uuid.uuid4())
    input_path = f"temp_audio_{unique_id}.ogg"
    audio_path = f"temp_audio_{unique_id}.wav"
    audio_file.save(input_path)

    try:
        # Конвертуємо OGG у WAV
        logger.info("Converting OGG to WAV...")
        stream = ffmpeg.input(input_path)
        stream = ffmpeg.output(stream, audio_path, acodec="pcm_s16le", ac=1, ar="16000")
        process = ffmpeg.run_async(stream, pipe_stdout=True, pipe_stderr=True, overwrite_output=True)
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            logger.error(f"FFmpeg failed with return code {process.returncode}")
            raise Exception(f"FFmpeg failed: {stderr.decode()}")
        
        if stdout:
            for line in stdout.decode().splitlines():
                logger.info(f"FFmpeg stdout: {line.strip()}")
        if stderr:
            for line in stderr.decode().splitlines():
                logger.info(f"FFmpeg stderr: {line.strip()}")
        
        logger.info("Conversion successful")

        # Транскрипція
        logger.info("Starting transcription...")
        logger.info("Loading audio file for transcription...")
        logger.info(f"Audio file path: {audio_path}")
        logger.info("Calling Whisper transcribe...")
        result = model.transcribe(audio_path, language="uk", fp16=False, verbose=True)
        logger.info("Whisper transcribe completed")
        logger.info("Transcription completed, processing result...")
        text = result["text"]
        logger.info(f"Transcription successful: {text}")
        return jsonify({"text": text})
    except Exception as e:
        logger.error(f"Transcription failed: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(input_path):
            os.remove(input_path)
        if os.path.exists(audio_path):
            os.remove(audio_path)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8888))
    app.run(host="0.0.0.0", port=port)