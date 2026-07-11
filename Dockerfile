FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    ca-certificates \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем свежайший yt-dlp из исходников (nightly)
RUN pip install --no-cache-dir --force-reinstall https://github.com/yt-dlp/yt-dlp/archive/master.tar.gz

# Копируем requirements и устанавливаем Python зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код бота
COPY . .

# Создаем папку для загрузок
RUN mkdir -p downloads

# Устанавливаем права доступа
RUN chmod +x /app

# Открываем порт (хотя для бота он не нужен, но для здоровья)
EXPOSE 8080

# Команда запуска
CMD ["python", "main.py"]
