import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN
from database import init_db
from handlers import start, gift, balance, referal, support, admin
from middlewares import SubscriptionMiddleware, StateResetMiddleware
from keyboards import get_bot_commands

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    await init_db()
    logger.info("Ma'lumotlar bazasi tayyor")

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    await bot.set_my_commands(get_bot_commands('uz', is_admin=False))
    await bot.set_my_description(
        "🎁 SANJAR GIFT — Gift sotish boti\n\n"
        "Bu yerda siz o'zingizga yoki do'stlaringizga gift sotib olishingiz mumkin.\n\n"
        "✅ Tez va oson\n"
        "💰 Hamyonbop narxlar\n"
        "🔒 Xavfsiz"
    )
    await bot.set_my_short_description("🎁 Gift sotish boti — tez, oson, xavfsiz")

    state_reset_middleware = StateResetMiddleware()
    dp.message.middleware(state_reset_middleware)

    subscription_middleware = SubscriptionMiddleware()
    dp.message.middleware(subscription_middleware)
    dp.callback_query.middleware(subscription_middleware)

    dp.include_router(start.router)
    dp.include_router(gift.router)
    dp.include_router(balance.router)
    dp.include_router(referal.router)
    dp.include_router(support.router)
    dp.include_router(admin.router)

    logger.info("Bot ishga tushdi")

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi")