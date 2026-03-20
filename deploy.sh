#!/bin/bash

# Скрипт для деплоя YouTube бота на сервер

echo "🚀 Начинаем деплой YouTube Downloader Bot..."

# Проверяем наличие Docker и Docker Compose
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен. Установите Docker сначала."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose не установлен. Установите Docker Compose сначала."
    exit 1
fi

# Проверяем наличие .env файла
if [ ! -f .env ]; then
    echo "❌ Файл .env не найден. Создайте его на основе .env.example"
    echo "cp .env.example .env"
    exit 1
fi

# Создаем папку для загрузок если ее нет
mkdir -p downloads

# Останавливаем старые контейнеры
echo "🛑 Останавливаем старые контейнеры..."
docker-compose down

# Собираем и запускаем новый контейнер
echo "🔨 Собираем образ..."
docker-compose build

echo "🚀 Запускаем бота..."
docker-compose up -d

# Проверяем статус
echo "📊 Проверяем статус..."
docker-compose ps

# Показываем логи
echo "📋 Показываем последние логи..."
docker-compose logs --tail=20

echo "✅ Деплой завершен!"
echo "🤖 Бот должен быть доступен в Telegram"
echo "📝 Для просмотра логов: docker-compose logs -f"
echo "🛑 Для остановки: docker-compose down"
