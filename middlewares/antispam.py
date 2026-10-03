from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
from typing import Callable, Dict, Any, Awaitable
import time
from collections import defaultdict


class AntiSpamMiddleware(BaseMiddleware):
    def __init__(self):
        self.user_requests = defaultdict(list)
        self.blocked_users = {}
        self.SPAM_WINDOW = 60
        self.SPAM_LIMIT = 20
        self.BLOCK_DURATION = 300

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

        if isinstance(event, Message):
            if event.text and event.text.startswith("/start"):
                return await handler(event, data)
            if event.contact:
                return await handler(event, data)

        now = time.time()

        if user_id in self.blocked_users:
            if now < self.blocked_users[user_id]:
                remaining = int(self.blocked_users[user_id] - now)
                if isinstance(event, Message):
                    await event.answer(
                        f"🚫 <b>Siz vaqtincha bloklandingiz!</b>\n\n"
                        f"⏳ Qolgan vaqt: {remaining} sekund\n\n"
                        f"Sabab: juda ko'p so'rov",
                        parse_mode="HTML"
                    )
                return
            else:
                del self.blocked_users[user_id]

        self.user_requests[user_id] = [
            t for t in self.user_requests[user_id]
            if now - t < self.SPAM_WINDOW
        ]

        if len(self.user_requests[user_id]) >= self.SPAM_LIMIT:
            self.blocked_users[user_id] = now + self.BLOCK_DURATION
            if isinstance(event, Message):
                await event.answer(
                    f"🚫 <b>Juda ko'p so'rov!</b>\n\n"
                    f"Siz {self.BLOCK_DURATION // 60} daqiqaga bloklandingiz.\n"
                    f"Sabab: spam",
                    parse_mode="HTML"
                )
            return

        self.user_requests[user_id].append(now)

        return await handler(event, data)
