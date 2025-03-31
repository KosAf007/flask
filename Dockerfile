FROM python:3.10-slim

# Встановлення FFmpeg, git і залежностей для компіляції
RUN apt-get update && apt-get install -y ffmpeg git build-essential && \
    ffmpeg -version && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
# Очищаємо кеш pip і встановлюємо залежності
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD gunicorn --bind 0.0.0.0:$PORT --workers 2 --threads 2 --timeout 120 --preload app:app