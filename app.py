from flask import Flask, request, jsonify
import whisper
import os
import logging
import ffmpeg
import uuid

app = Flask(__name__)

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info("Starting Flask app...")

# Завантажуємо модель під час старту
logger.info("Loading Whisper model at startup...")
try:
    model = whisper.load_model("tiny")
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
        ffmpeg.run(stream, overwrite_output=True)
        logger.info("Conversion successful")

        # Транскрипція
        logger.info("Starting transcription...")
        result = model.transcribe(audio_path, language="uk", fp16=False, verbose=True)
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