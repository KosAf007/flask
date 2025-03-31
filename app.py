from flask import Flask, request, jsonify
import whisper
import os
import logging

app = Flask(__name__)

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info("Starting Flask app...")

model = None  # Не завантажуємо модель одразу

def load_model():
    global model
    if model is None:
        logger.info("Starting to load Whisper model...")
        try:
            model = whisper.load_model("tiny")  # Завантажуємо модель лише при першому запиті
            logger.info("Whisper model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {str(e)}")
            raise
    return model

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
    audio_path = "temp_audio.wav"
    audio_file.save(audio_path)

    try:
        model = load_model()  # Завантажуємо модель перед використанням
        logger.info("Starting transcription...")
        result = model.transcribe(audio_path, language="uk")
        text = result["text"]
        logger.info(f"Transcription successful: {text}")
        return jsonify({"text": text})
    except Exception as e:
        logger.error(f"Transcription failed: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8888))
    app.run(host="0.0.0.0", port=port)