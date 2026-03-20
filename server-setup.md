# 🖥️ Инструкция по деплою на сервер 104.128.132.83

## 📋 Подготовка сервера

### 1. Подключение к серверу
```bash
ssh root@104.128.132.83
```

### 2. Установка Docker и Docker Compose
```bash
# Обновление системы
apt update && apt upgrade -y

# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Установка Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Проверка
docker --version
docker-compose --version
```

## 🚀 Деплой бота

### 1. Клонирование репозитория
```bash
cd /opt
git clone <your-github-repo-url> youtube-bot
cd youtube-bot
```

### 2. Настройка переменных окружения
```bash
# Создаем .env файл
cp .env.example .env
nano .env
```

Добавьте токен бота:
```bash
BOT_TOKEN=your_telegram_bot_token_here
```

### 3. Запуск бота
```bash
# Делаем скрипт деплоя исполняемым
chmod +x deploy.sh

# Запускаем деплой
./deploy.sh
```

### 4. Проверка работы
```bash
# Проверяем статус контейнера
docker-compose ps

# Смотрим логи
docker-compose logs -f

# Перезапуск при необходимости
docker-compose restart
```

## 🔧 Управление

### Полезные команды
```bash
# Показать логи в реальном времени
docker-compose logs -f youtube-bot

# Перезапустить бота
docker-compose restart youtube-bot

# Остановить бота
docker-compose stop youtube-bot

# Полностью остановить и удалить
docker-compose down

# Обновить код и перезапустить
git pull
docker-compose down
docker-compose up -d --build
```

### Мониторинг
```bash
# Проверить использование ресурсов
docker stats youtube-bot

# Проверить диск
df -h

# Проверить память
free -h
```

## 📁 Структура файлов на сервере
```
/opt/youtube-bot/
├── main.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── deploy.sh
├── .env (с токеном)
├── .gitignore
├── .env.example
└── downloads/ (временные файлы)
```

## ⚠️ Важные замечания

1. **Безопасность:** Убедитесь, что .env файл не попадет в Git
2. **Резервное копирование:** Регулярно делайте бэкапы
3. **Мониторинг:** Следите за логами и состоянием контейнера
4. **Обновления:** Регулярно обновляйте yt-dlp для работы с YouTube

## 🚨 Автоматический перезапуск

В `docker-compose.yml` уже настроен `restart: unless-stopped`, что означает:
- Контейнер автоматически перезапустится при падении
- Перезапуск после перезагрузки сервера
- Ручной перезапуск через `docker-compose restart`

## 📊 Логирование

Логи бота доступны через:
```bash
# В реальном времени
docker-compose logs -f

# Последние 100 строк
docker-compose logs --tail=100

# За определенную дату
docker-compose logs --since="2024-01-01" --until="2024-01-02"
```
