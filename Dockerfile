FROM python:3.12-slim

WORKDIR /app

# Системные зависимости + обновление CA-сертификатов
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    ca-certificates \
    && update-ca-certificates --fresh \
    && rm -rf /var/lib/apt/lists/*

# Копируем requirements и устанавливаем Python зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Устанавливаем свежайший yt-dlp из исходников (nightly) — ПОСЛЕ requirements
RUN pip install --no-cache-dir --force-reinstall https://github.com/yt-dlp/yt-dlp/archive/master.tar.gz

# Копируем код бота
COPY . .

RUN mkdir -p downloads

EXPOSE 8080

# Скрипт запуска
RUN echo '#!/bin/sh\npython main.py' > /app/start.sh && chmod +x /app/start.sh

CMD ["/app/start.sh"]
