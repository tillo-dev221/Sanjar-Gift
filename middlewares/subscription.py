from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
from typing import Callable, Dict, Any, Awaitable
from database import get_user, get_channels, is_admin_user
from keyboards import subscribe_keyboard


class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user_id = None
        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id

        if not user_id:
            return await handler(event, data)

        if await is_admin_user(user_id):
            return await handler(event, data)

        bot = data.get("bot")
        if not bot:
            return await handler(event, data)

        channels = await get_channels()
        if not channels:
            return await handler(event, data)

        user = await get_user(user_id)
        if not user:
            return await handler(event, data)

        try:
            is_banned = user["is_banned"]
        except (KeyError, IndexError):
            is_banned = 0

        if is_banned:
            if isinstance(event, Message):
                await event.answer("🚫 Siz bloklangansiz")
            elif isinstance(event, CallbackQuery):
                await event.answer("🚫 Siz bloklangansiz", show_alert=True)
            return

        not_subscribed = []
        for ch in channels:
            try:
                chat_id = ch["channel_id"]
                member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
                if member.status in ("left", "kicked"):
                    not_subscribed.append(ch)
            except Exception as e:
                print(f"Obuna tekshirish xatosi ({ch['channel_username']}): {e}")
                continue

        if not not_subscribed:
            return await handler(event, data)

        lang = user["language"] if user["language"] else "uz"

        if isinstance(event, CallbackQuery):
            if event.data == "check_sub":
                return await handler(event, data)
            await event.answer("⚠️ Avval kanallarga obuna bo'ling!", show_alert=True)

        keyboard = subscribe_keyboard(not_subscribed, lang)
        text = "⚠️ <b>Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:</b>"

        if isinstance(event, Message):
            await event.answer(text, reply_markup=keyboard, parse_mode="HTML")

        return