from aiogram import Router, F, Bot
from aiogram.types import Message
from database import (
    get_user, get_referals, get_setting,
    get_user_account_age_days, get_user_referals_today
)

router = Router()

MIN_ACCOUNT_AGE_DAYS = 1
MAX_REFERALS_PER_DAY = 5


@router.message(F.text.in_(["👥 Referal", "👥 Реферал", "👥 Referral"]))
async def show_referal(message: Message, bot: Bot):
    user = await get_user(message.from_user.id)
    if not user:
        return

    lang = user["language"] if user["language"] else "uz"

    account_age = await get_user_account_age_days(message.from_user.id)
    if account_age < MIN_ACCOUNT_AGE_DAYS:
        await message.answer(
            f"⚠️ <b>Akkauntingiz juda yangi!</b>\n\n"
            f"Referal tizimidan foydalanish uchun kamida "
            f"<b>{MIN_ACCOUNT_AGE_DAYS} kun</b> kutish kerak.\n\n"
            f"📅 Akkaunt yoshi: {account_age} kun",
            parse_mode="HTML"
        )
        return

    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start={message.from_user.id}"

    referals = await get_referals(message.from_user.id)
    count = len(referals)

    bonus = int(await get_setting("referal_bonus") or 1000)
    earned = count * bonus

    today_count = await get_user_referals_today(message.from_user.id)

    text = (
        f"👥 <b>Referal tizimi</b>\n\n"
        f"🔗 Sizning havolangiz:\n"
        f"<code>{link}</code>\n\n"
        f"👥 Taklif qilganlar: <b>{count}</b>\n"
        f"💰 Ishlangan: <b>{earned:,} so'm</b>\n"
        f"📊 Bugun: <b>{today_count}/{MAX_REFERALS_PER_DAY}</b>\n\n"
        f"💡 Har bir do'stingiz uchun <b>{bonus:,} so'm</b> olasiz!\n\n"
        f"⚠️ <b>Diqqat:</b>\n"
        f"• Faqat <b>+998</b> raqamli foydalanuvchilar\n"
        f"• Kuniga <b>{MAX_REFERALS_PER_DAY} ta</b> limit\n"
        f"• Akkaunt kamida <b>{MIN_ACCOUNT_AGE_DAYS} kun</b> eski bo'lishi kerak"
    )

    await message.answer(text, parse_mode="HTML")
