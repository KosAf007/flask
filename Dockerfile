FROM python:3.10-slim

# Встановлення FFmpeg, git і залежностей для компіляції
RUN apt-get update && apt-get install -y ffmpeg git build-essential && \
    ffmpeg -version && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 1 --timeout 600 --preload app:app