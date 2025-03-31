FROM python:3.9-slim

# Встановлення FFmpeg, git і залежностей для компіляції
RUN apt-get update && apt-get install -y ffmpeg git build-essential && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["gunicorn", "--bind", "0.0.0.0:$PORT", "app:app"]