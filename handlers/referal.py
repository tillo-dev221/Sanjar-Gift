from aiogram import Router, F
from aiogram.types import Message
from database import get_user, get_referals, get_setting

router = Router()


@router.message(F.text.in_(["👥 Referal", "👥 Реферал", "👥 Referral"]))
async def show_referal(message: Message, bot):
    user = await get_user(message.from_user.id)
    if not user:
        return
    lang = user["language"]

    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start={message.from_user.id}"

    referals = await get_referals(message.from_user.id)
    count = len(referals)
    bonus = int(await get_setting("referal_bonus") or 1000)
    earned = count * bonus

    text = (
        f"👥 <b>Referal tizimi</b>\n\n"
        f"🔗 Sizning havolangiz:\n"
        f"<code>{link}</code>\n\n"
        f"👥 Taklif qilganlar: {count}\n"
        f"💰 Ishlangan: {earned:,} so'm\n\n"
        f"💡 Har bir do'stingiz uchun <b>{bonus:,} so'm</b> olasiz!"
    )

    await message.answer(text, parse_mode="HTML")