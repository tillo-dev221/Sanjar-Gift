import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "")
DB_PATH = os.getenv("DB_PATH", "gift_bot.db")