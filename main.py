import os
import sys
import ssl
import asyncio
import logging
from typing import Optional
from urllib.parse import urlparse

# Глобальный SSL-патч для OpenSSL 3.x + YouTube (UNEXPECTED_EOF)
try:
    _ctx = ssl.create_default_context()
    _ctx.check_hostname = False
    _ctx.verify_mode = ssl.CERT_NONE
    # Python 3.12+ флаг для игнорирования EOF от YouTube
    if hasattr(ssl, 'OP_IGNORE_UNEXPECTED_EOF'):
        _ctx.options |= ssl.OP_IGNORE_UNEXPECTED_EOF
    ssl._create_default_https_context = lambda: _ctx
except Exception:
    pass

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
    ('any',   'best'),
    ('low',   'worst'),
]

class YouTubeDownloader:
    def __init__(self):
        # Прокси для обхода блокировок (SOCKS5/HTTP). Не задан — идём напрямую
        proxy = os.getenv('YT_PROXY', '')
        cookie_file = 'cookies.txt'
        if not os.path.exists(cookie_file):
            cookie_file = ''
        self.base_opts = {
            'merge_output_format': 'mp4',
            'outtmpl': 'downloads/%(title)s.%(ext)s',
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'source_address': '0.0.0.0',
            'nocheckcertificate': True,
            'socket_timeout': 30,
            'extractor_retries': 3,
            'file_access_retries': 5,
            'retry_sleep_func': lambda n: min(n * 2, 10),
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'identity',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            },
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web', 'ios'],
                }
            },
            'external_downloader': 'native',
        }
        if cookie_file:
            self.base_opts['cookiefile'] = cookie_file
        # Имитация TLS-отпечатка браузера для обхода блокировок
        try:
            import curl_cffi
            self.base_opts['impersonate'] = 'chrome'
            logger.info("curl_cffi доступен, включена имитация Chrome")
        except ImportError:
            logger.info("curl_cffi не установлен, имитация отключена")
        if proxy:
            self.base_opts['proxy'] = proxy
            logger.info(f"Используется прокси: {proxy}")

    def build_opts(self, fmt: str, use_legacy: bool = False) -> dict:
        opts = self.base_opts.copy()
        opts['format'] = fmt
        if use_legacy:
            opts['extractor_args'] = {
                'youtube': {
                    'player_client': ['android', 'web'],
                    'max_comments': ['0'],
                }
            }
            opts['legacy_server_connect'] = True
            opts['source_address'] = '0.0.0.0'
        return opts

    def is_youtube_url(self, url: str) -> bool:
        parsed = urlparse(url)
        return parsed.netloc in ['youtube.com', 'www.youtube.com', 'youtu.be', 'm.youtube.com']

    async def auto_download(self, url: str) -> Optional[str]:
        # Пробуем сначала нормальный режим, потом legacy если не сработало
        for use_legacy in [False, True]:
            mode = "legacy" if use_legacy else "normal"
            for label, fmt in QUALITIES:
                logger.info(f"Пробую {label} ({mode})...")
                try:
                    opts = self.build_opts(fmt, use_legacy)
                    opts['quiet'] = False
                    opts['no_warnings'] = False
                    with yt_dlp.YoutubeDL(opts) as ydl:
                        info = ydl.extract_info(url, download=True)
                        formats = info.get('formats', [])
                        logger.warning(f"Получено форматов: {len(formats)}")
                        if formats:
                            for f in formats[:5]:
                                logger.warning(f"  формат: {f.get('format_id')} {f.get('height')}p {f.get('ext')}")
                        filename = ydl.prepare_filename(info)

                        file_size = os.path.getsize(filename)
                        if file_size <= MAX_BYTES:
                            logger.info(f"{label} ({mode}): {file_size/(1024*1024):.1f}MB — OK")
                            return filename

                        logger.warning(f"{label} ({mode}): {file_size/(1024*1024):.1f}MB > {MAX_SIZE_MB}MB, пробую ниже")
                        os.remove(filename)

                except Exception as e:
                    logger.warning(f"{label} ({mode}) не подошёл: [{type(e).__name__}] {e}")
                    import traceback
                    logger.debug(traceback.format_exc())
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

async def update_ytdlp():
    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, '-m', 'pip', 'install', '--upgrade',
            'https://github.com/yt-dlp/yt-dlp/archive/master.tar.gz',
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
        )
        await proc.wait()
        if proc.returncode == 0:
            logger.info("yt-dlp обновлён до nightly")
        else:
            logger.warning("Не удалось обновить yt-dlp, продолжаю с текущей версией")
    except Exception as e:
        logger.warning(f"Ошибка обновления yt-dlp: {e}")

async def main():
    os.makedirs('downloads', exist_ok=True)
    logger.info("Запуск YouTube бота...")
    import yt_dlp.version
    logger.info(f"yt-dlp версия: {yt_dlp.version.__version__}")
    await update_ytdlp()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
