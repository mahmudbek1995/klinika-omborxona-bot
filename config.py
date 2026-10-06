import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Adminlarning Telegram ID raqamlari
raw_admins = os.getenv("ADMINS", "")
ADMIN_IDS = [int(admin_id.strip()) for admin_id in raw_admins.split(",") if admin_id.strip().isdigit()]

# SQLite baza fayli yo'li
DB_NAME = os.getenv("DB_NAME", "omborxona.db")

# Web ilova sozlamalari
WEB_HOST = os.getenv("WEB_HOST", "0.0.0.0")
WEB_PORT = int(os.getenv("PORT", os.getenv("WEB_PORT", "8080")))
WEB_APP_URL = os.getenv("WEB_APP_URL", f"http://localhost:{WEB_PORT}")
