from flask import Flask, request, jsonify
import whisper
import os

app = Flask(__name__)
model = whisper.load_model("tiny")  # Легка модель для економії ресурсів

@app.route('/')
def home():
    return "Whisper Speech-to-Text API"

@app.route("/transcribe", methods=["POST"])
def transcribe():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400
    
    audio_file = request.files["audio"]
    audio_path = "temp_audio.wav"
    audio_file.save(audio_path)

    try:
        result = model.transcribe(audio_path, language="uk")  # Вказуємо українську мову
        text = result["text"]
        return jsonify({"text": text})
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)  # Видаляємо тимчасовий файл

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8888))
    app.run(host="0.0.0.0", port=port)