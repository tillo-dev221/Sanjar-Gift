from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject
from typing import Callable, Dict, Any, Awaitable


class StateResetMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if isinstance(event, Message):
            if event.text and event.text.startswith("/"):
                state = data.get("state")
                if state:
                    current = await state.get_state()
                    if current:
                        await state.clear()

        return await handler(event, data)