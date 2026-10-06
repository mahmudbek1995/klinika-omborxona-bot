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

    # Eski kutilayotgan yangilanishlarni tozalash
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Telegram Bot muvaffaqiyatli ishga tushdi...")

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
        # Bot va Web serverni parallel ishga tushirish
        await asyncio.gather(
            dp.start_polling(bot),
            server.serve()
        )
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Dastur to'xtatildi.")
