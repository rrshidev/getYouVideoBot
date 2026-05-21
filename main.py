import os
import asyncio
import logging
from typing import Optional
from urllib.parse import urlparse

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile
import yt_dlp
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=os.getenv("BOT_TOKEN"))
CHANNEL_ID = os.getenv("CHANNEL_ID")
MAX_SIZE_MB = 50
MAX_BYTES = MAX_SIZE_MB * 1024 * 1024
dp = Dispatcher()

QUALITIES = [
    ('1080p', 'bestvideo[height<=1080]+bestaudio/best[height<=1080]/bestvideo+bestaudio/best'),
    ('720p',  'bestvideo[height<=720]+bestaudio/best[height<=720]/bestvideo+bestaudio/best'),
    ('480p',  'bestvideo[height<=480]+bestaudio/worst[height<=480]/worst'),
    ('360p',  'bestvideo[height<=360]+bestaudio/worst[height<=360]/worst'),
]

class YouTubeDownloader:
    def __init__(self):
        self.base_opts = {
            'merge_output_format': 'mp4',
            'outtmpl': 'downloads/%(title)s.%(ext)s',
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web', 'ios'],
                    'skip': ['dash', 'hls']
                }
            }
        }

    def is_youtube_url(self, url: str) -> bool:
        parsed = urlparse(url)
        return parsed.netloc in ['youtube.com', 'www.youtube.com', 'youtu.be', 'm.youtube.com']

    async def auto_download(self, url: str) -> Optional[str]:
        for label, fmt in QUALITIES:
            logger.info(f"Пробую {label}...")
            try:
                opts = self.base_opts.copy()
                opts['format'] = fmt
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    filename = ydl.prepare_filename(info)

                    file_size = os.path.getsize(filename)
                    if file_size <= MAX_BYTES:
                        logger.info(f"{label}: {file_size/(1024*1024):.1f}MB — OK")
                        return filename

                    logger.warning(f"{label}: {file_size/(1024*1024):.1f}MB > {MAX_SIZE_MB}MB, пробую ниже")
                    os.remove(filename)

            except Exception as e:
                logger.warning(f"{label} не подошёл: {e}")
                continue

        return None

downloader = YouTubeDownloader()

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "👋 Привет! Я бот для скачивания видео с YouTube.\n\n"
        "Просто отправь мне ссылку на видео — я сам выберу лучшее качество\n"
        f"в пределах {MAX_SIZE_MB}MB и отправлю в канал {CHANNEL_ID}."
    )

@dp.message(F.text)
async def handle_text(message: Message):
    url = message.text.strip()

    if not downloader.is_youtube_url(url):
        await message.answer("❌ Это не похоже на ссылку YouTube.")
        return

    status_msg = await message.answer("⏳ Анализирую и скачиваю...")

    filename = await downloader.auto_download(url)

    if not filename:
        await status_msg.edit_text(
            f"❌ Не удалось скачать видео ни в одном качестве.\n"
            f"Возможно, файл слишком большой (>50MB) или видео недоступно."
        )
        return

    try:
        video = FSInputFile(filename)
        await bot.send_video(
            chat_id=CHANNEL_ID,
            video=video,
            caption=f"📹 Источник видео: {url}"
        )
        logger.info(f"Видео отправлено в канал {CHANNEL_ID}")

        await status_msg.edit_text(
            f"✅ Видео отправлено в канал {CHANNEL_ID}\n\n"
            f"📹 {url}"
        )

    except Exception as e:
        logger.error(f"Ошибка при отправке в канал: {e}")
        await status_msg.edit_text(
            f"❌ Не удалось отправить видео в канал.\n"
            f"Убедись, что бот добавлен как администратор {CHANNEL_ID}.\n\n"
            f"Ошибка: {e}"
        )

    finally:
        if os.path.exists(filename):
            os.remove(filename)

async def main():
    os.makedirs('downloads', exist_ok=True)
    logger.info("Запуск YouTube бота...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
