import asyncio
import logging
import sys
import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, ADMIN_IDS, WEB_HOST, WEB_PORT, WEB_APP_URL
import database as db
from web_app import app as web_app

from handlers import start, kirim, chiqim, ombor, kam_qolgan, hisobot

# Loglarni sozlash
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def keep_alive_ping():
    """Render bepul serveri uxlab qolmasligi uchun har 10 daqiqada o'zini o'zi chaqirib turish"""
    await asyncio.sleep(60)  # Dastlabki yuklanishdan so'ng 1 daqiqa kutish
    import aiohttp
    url = f"{WEB_APP_URL.rstrip('/')}/api/stats" if WEB_APP_URL.startswith("http") else None
    if not url:
        return
        
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                    logger.debug(f"Keep-alive self-ping yuborildi: {resp.status}")
        except Exception as e:
            logger.debug(f"Keep-alive ping xatosi (muhim emas): {e}")
        await asyncio.sleep(600)  # Har 10 daqiqada (Render 15 daqiqada uxlaydi)

async def run_bot_polling(dp: Dispatcher, bot: Bot):
    """Tarmoq xatolariga chidamli (avtomatik qayta ulanuvchi) bot polling"""
    while True:
        try:
            logger.info("Telegram Bot polling ishga tushmoqda...")
            await dp.start_polling(bot, handle_signals=False)
            break
        except (asyncio.CancelledError, KeyboardInterrupt):
            logger.info("Bot to'xtatildi.")
            break
        except Exception as e:
            logger.warning(f"Telegram tarmoq uzilishi ({type(e).__name__}): {e}. 3 soniyadan so'ng qayta ulanadi...")
            await asyncio.sleep(3)

async def main():
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error(
            "\n" + "=" * 60 + "\n"
            "❌ XATOLIK: BOT_TOKEN ko'rsatilmagan!\n"
            "Iltimos, .env faylini oching va @BotFather dan olingan bot tokeningizni kiriting:\n"
            "BOT_TOKEN=1234567890:ABCdef...\n"
            + "=" * 60
        )
        return

    # Ma'lumotlar bazasini ishga tushirish
    await db.init_db()
    logger.info("Ma'lumotlar bazasi muvaffaqiyatli ishga tushirildi.")

    bot = Bot(token=BOT_TOKEN)
    from notifier import set_bot_instance
    set_bot_instance(bot)
    dp = Dispatcher(storage=MemoryStorage())

    # Routerlarni ulash
    dp.include_router(start.router)
    dp.include_router(kirim.router)
    dp.include_router(chiqim.router)
    dp.include_router(ombor.router)
    dp.include_router(kam_qolgan.router)
    dp.include_router(hisobot.router)

    # Eski kutilayotgan yangilanishlarni tozalash (xavfsiz rejimda)
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception as e:
        logger.warning(f"delete_webhook xatosi (davom etiladi): {e}")

    # Uvicorn Web Server konfiguratsiyasi
    uvicorn_config = uvicorn.Config(
        app=web_app,
        host=WEB_HOST,
        port=WEB_PORT,
        log_level="warning"
    )
    server = uvicorn.Server(uvicorn_config)
    logger.info(f"🌐 Web Dashboard va API server ishga tushdi: http://localhost:{WEB_PORT}")

    try:
        await asyncio.gather(
            run_bot_polling(dp, bot),
            server.serve(),
            keep_alive_ping()
        )
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Dastur to'xtatildi.")
