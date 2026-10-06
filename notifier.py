import logging
from aiogram import Bot
from config import ADMIN_IDS, BOT_TOKEN

logger = logging.getLogger(__name__)

# Global bot instance
_bot_instance: Bot | None = None

def set_bot_instance(bot: Bot):
    global _bot_instance
    _bot_instance = bot

def get_bot_instance() -> Bot:
    global _bot_instance
    if _bot_instance is None:
        _bot_instance = Bot(token=BOT_TOKEN)
    return _bot_instance

async def notify_admin(text: str, reply_markup=None):
    """
    Barcha Glavniy Adminlarga (aynan 475334833 ga) Telegram orqali xabar yuborish.
    """
    bot = get_bot_instance()
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Adminga ({admin_id}) xabar yuborishda xatolik: {e}")
