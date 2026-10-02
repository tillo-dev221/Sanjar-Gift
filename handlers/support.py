from aiogram import Router, F
from aiogram.types import Message
from database import get_user, get_setting

router = Router()


@router.message(F.text.in_(["📞 Support", "📞 Поддержка", "📞 Support"]))
async def show_support(message: Message):
    user = await get_user(message.from_user.id)
    lang = user["language"] if user else "uz"
    username = await get_setting("support_username") or "Sanjarbek00011"

    text = (
        f"📞 <b>Qo'llab-quvvatlash</b>\n\n"
        f"Savollaringiz bo'lsa, admin bilan bog'laning:\n\n"
        f"👤 @{username}"
    )

    await message.answer(text, parse_mode="HTML")