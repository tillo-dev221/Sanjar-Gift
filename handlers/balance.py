from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import get_user, get_setting
from keyboards import balance_keyboard
from locales import t
from config import ADMIN_ID

router = Router()


class TopupState(StatesGroup):
    waiting_amount = State()
    waiting_receipt = State()


@router.message(F.text.in_(["💰 Balans", "💰 Баланс", "💰 Balance"]))
async def show_balance(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        return
    lang = user["language"]
    await message.answer(
        t(lang, "balance_menu", balance=user["balance"]),
        reply_markup=balance_keyboard(lang),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "topup")
async def topup_start(callback: CallbackQuery, state: FSMContext):
    user = await get_user(callback.from_user.id)
    lang = user["language"] if user else "uz"

    await callback.message.delete()
    await callback.message.answer(
        "💰 To'ldirmoqchi bo'lgan summani kiriting (so'mda):\n\n<i>Misol: 10000</i>",
        parse_mode="HTML"
    )
    await state.set_state(TopupState.waiting_amount)


@router.message(TopupState.waiting_amount)
async def topup_amount(message: Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    lang = user["language"] if user else "uz"

    try:
        amount = int(message.text.replace(" ", "").replace(",", ""))
        if amount < 1000:
            raise ValueError
    except ValueError:
        await message.answer("❌ Noto'g'ri summa. Kamida 1000 so'm.")
        return

    card = await get_setting("card_number") or "0000 0000 0000 0000"
    owner = await get_setting("card_owner") or "Admin"

    await state.update_data(amount=amount)

    await message.answer(
        f"💳 <b>To'lov ma'lumotlari</b>\n\n"
        f"💰 Summa: <b>{amount:,} so'm</b>\n\n"
        f"💳 Karta: <code>{card}</code>\n"
        f"👤 Egasi: {owner}\n\n"
        f"📸 To'lov chekini rasm sifatida yuboring.",
        parse_mode="HTML"
    )
    await state.set_state(TopupState.waiting_receipt)


@router.message(TopupState.waiting_receipt, F.photo)
async def topup_receipt(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    user = await get_user(message.from_user.id)
    lang = user["language"] if user else "uz"

    amount = data.get("amount")
    photo = message.photo[-1]

    admin_text = (
        f"💳 <b>Balans to'ldirish so'rovi</b>\n\n"
        f"👤 {message.from_user.full_name}\n"
        f"🆔 <code>{message.from_user.id}</code>\n"
        f"📱 @{message.from_user.username or 'yoq'}\n\n"
        f"💰 Summa: <b>{amount:,} so'm</b>\n\n"
        f"📸 Chek:"
    )

    try:
        await bot.send_photo(
            ADMIN_ID,
            photo=photo.file_id,
            caption=admin_text,
            parse_mode="HTML",
            reply_markup=topup_admin_keyboard(message.from_user.id, amount)
        )
        print(f"✅ Admin xabar yuborildi: topup {amount}")
    except Exception as e:
        print(f"❌ TOPUP XABAR XATOSI: {e}")
        await message.answer(f"❌ Xatolik: {e}")
        return

    await message.answer(
        f"✅ Chekingiz qabul qilindi!\n\n"
        f"💰 Summa: {amount:,} so'm\n"
        f"⏳ Admin tasdiqlashini kuting.",
        parse_mode="HTML"
    )
    await state.clear()


@router.message(TopupState.waiting_receipt, ~F.photo)
async def topup_not_photo(message: Message):
    await message.answer("📸 Iltimos, chekni <b>rasm</b> sifatida yuboring.", parse_mode="HTML")


def topup_admin_keyboard(user_id, amount):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="✅ Tasdiqlash",
            callback_data=f"topup_approve_{user_id}_{amount}"
        )],
        [InlineKeyboardButton(
            text="❌ Rad etish",
            callback_data=f"topup_reject_{user_id}_{amount}"
        )],
    ])