import os
import asyncio
import logging
from typing import Optional
from urllib.parse import urlparse, parse_qs

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.enums import ParseMode
import yt_dlp
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота
bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()

# Класс для работы с YouTube
class YouTubeDownloader:
    def __init__(self):
        self.ydl_opts = {
            'format': 'best[height<=720]/best[height<=480]/best[height<=360]/best',
            'merge_output_format': 'mp4',
            'outtmpl': 'downloads/%(title)s.%(ext)s',
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web']
                }
            }
        }
    
    def is_youtube_url(self, url: str) -> bool:
        """Проверка, является ли URL ссылкой на YouTube"""
        parsed = urlparse(url)
        return parsed.netloc in ['youtube.com', 'www.youtube.com', 'youtu.be', 'm.youtube.com']
    
    async def get_video_info(self, url: str) -> Optional[dict]:
        """Получение информации о видео"""
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info
        except Exception as e:
            logger.error(f"Ошибка при получении информации о видео: {e}")
            return None
    
    async def download_video(self, url: str, quality: str = '720p') -> Optional[str]:
        """Скачивание видео"""
        try:
            # Создаем папку для загрузок, если ее нет
            os.makedirs('downloads', exist_ok=True)
            
            # Настройка качества - более гибкие форматы
            if quality == '360p':
                format_string = 'worst[height<=360]/worst[height<=480]/worst'
            elif quality == '480p':
                format_string = 'worst[height<=480]/worst[height<=360]/worst'
            elif quality == '720p':
                format_string = 'best[height<=720]/best[height<=480]/best[height<=360]/best'
            elif quality == '1080p':
                format_string = 'best[height<=1080]/best[height<=720]/best[height<=480]/best'
            else:
                format_string = 'best[height<=720]/best[height<=480]/best[height<=360]/best'
            
            self.ydl_opts['format'] = format_string
            
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                
                # Проверяем размер файла
                file_size = os.path.getsize(filename)
                if file_size > 50 * 1024 * 1024:  # 50MB
                    logger.warning(f"Файл слишком большой: {file_size / (1024*1024):.1f}MB")
                    return None
                
                return filename
        except Exception as e:
            logger.error(f"Ошибка при скачивании видео: {e}")
            return None

downloader = YouTubeDownloader()

# Обработчик команды /start
@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "👋 Привет! Я бот для скачивания видео с YouTube.\n\n"
        "Просто отправь мне ссылку на видео, и я скачаю его для тебя.\n\n"
        "Поддерживаемые форматы:\n"
        "• 360p, 480p, 720p, 1080p\n\n"
        "⚠️ Внимание: Скачивание видео может нарушать условия использования YouTube."
    )

# Обработчик текстовых сообщений (проверка на YouTube ссылки)
@dp.message(F.text)
async def handle_text(message: Message):
    url = message.text.strip()
    
    if not downloader.is_youtube_url(url):
        await message.answer("❌ Это не похоже на ссылку YouTube. Пожалуйста, отправьте корректную ссылку.")
        return
    
    # Показываем сообщение о загрузке
    processing_msg = await message.answer("⏳ Анализирую видео...")
    
    try:
        # Получаем информацию о видео
        info = await downloader.get_video_info(url)
        if not info:
            await processing_msg.edit_text("❌ Не удалось получить информацию о видео. Попробуйте другую ссылку.")
            return
        
        title = info.get('title', 'Без названия')
        duration = info.get('duration', 0)
        duration_str = f"{duration // 60}:{duration % 60:02d}" if duration else "Неизвестно"
        
        # Создаем клавиатуру для выбора качества
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="360p", callback_data=f"download_360p_{url}"),
                InlineKeyboardButton(text="480p", callback_data=f"download_480p_{url}")
            ],
            [
                InlineKeyboardButton(text="720p", callback_data=f"download_720p_{url}"),
                InlineKeyboardButton(text="1080p", callback_data=f"download_1080p_{url}")
            ]
        ])
        
        await processing_msg.edit_text(
            f"📹 **{title}**\n\n"
            f"⏱️ Длительность: {duration_str}\n"
            f"🎥 Выберите качество для скачивания:",
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        logger.error(f"Ошибка при обработке ссылки: {e}")
        await processing_msg.edit_text("❌ Произошла ошибка при обработке ссылки. Попробуйте еще раз.")

# Обработчик нажатий на кнопки качества
@dp.callback_query(F.data.startswith('download_'))
async def handle_quality_selection(callback: types.CallbackQuery):
    try:
        # Разбираем callback_data
        parts = callback.data.split('_', 2)
        quality = parts[1]
        url = parts[2]
        
        await callback.answer(f"Начинаю скачивание в качестве {quality}...")
        
        # Показываем сообщение о загрузке
        loading_msg = await callback.message.edit_text("⏳ Скачиваю видео... Это может занять несколько минут.")
        
        # Скачиваем видео
        filename = await downloader.download_video(url, quality)
        
        if not filename:
            await loading_msg.edit_text("❌ Не удалось скачать видео. Возможно, файл слишком большой (>50MB) или видео недоступно.")
            return
        
        # Отправляем видео
        try:
            video = FSInputFile(filename)
            await bot.send_video(
                chat_id=callback.message.chat.id,
                video=video,
                caption="✅ Видео успешно скачано!"
            )
            
            await loading_msg.delete()
            
            # Удаляем временный файл
            os.remove(filename)
            
        except Exception as e:
            logger.error(f"Ошибка при отправке видео: {e}")
            await loading_msg.edit_text("❌ Не удалось отправить видео. Файл может быть слишком большим.")
            
            # Удаляем временный файл
            if os.path.exists(filename):
                os.remove(filename)
                
    except Exception as e:
        logger.error(f"Ошибка при обработке кнопки: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)

async def main():
    # Создаем папку для загрузок
    os.makedirs('downloads', exist_ok=True)
    
    # Запускаем бота
    logger.info("Запуск YouTube бота...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
