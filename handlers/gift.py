from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import (
    get_user, get_gifts, get_gift, create_order, update_order_status,
    get_setting, update_balance, get_order
)
from keyboards import (
    gifts_keyboard, confirm_keyboard, payment_keyboard, admin_order_keyboard
)
from locales import t
from config import ADMIN_ID

router = Router()


class GiftState(StatesGroup):
    waiting_username = State()
    waiting_receipt = State()


@router.message(F.text.in_(["🎁 Giftlar", "🎁 Подарки", "🎁 Gifts"]))
async def show_gifts(message: Message):
    user = await get_user(message.from_user.id)
    lang = user["language"] if user else "uz"
    gifts = await get_gifts()

    if not gifts:
        await message.answer("❌ Giftlar mavjud emas")
        return

    await message.answer(
        t(lang, "gifts_menu"),
        reply_markup=gifts_keyboard(gifts, lang),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("ugift_"))
async def gift_selected(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    if len(parts) < 2:
        await callback.answer("❌ Xatolik", show_alert=True)
        return

    try:
        gift_id = int(parts[1])
    except ValueError:
        await callback.answer("❌ Xatolik", show_alert=True)
        return

    gift = await get_gift(gift_id)
    user = await get_user(callback.from_user.id)
    lang = user["language"] if user else "uz"

    if not gift:
        await callback.answer("❌ Gift topilmadi", show_alert=True)
        return

    if not gift["is_active"]:
        await callback.answer("❌ Bu gift o'chirilgan", show_alert=True)
        return

    await state.update_data(
        gift_id=gift_id,
        gift_name=gift["name"],
        gift_price=gift["price"]
    )
    await state.set_state(GiftState.waiting_username)

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(
        t(lang, "gift_info", name=gift["name"], price=gift["price"]),
        parse_mode="HTML"
    )


@router.message(GiftState.waiting_username)
async def get_username(message: Message, state: FSMContext):
    username = message.text.strip()
    user = await get_user(message.from_user.id)
    lang = user["language"] if user else "uz"

    if not username.startswith("@"):
        await message.answer(t(lang, "invalid_username"))
        return

    if len(username) < 4:
        await message.answer(t(lang, "invalid_username"))
        return

    data = await state.get_data()
    if not data.get("gift_id"):
        await message.answer(t(lang, "error"))
        await state.clear()
        return

    await state.update_data(recipient=username)

    await message.answer(
        t(lang, "gift_confirm",
          name=data["gift_name"],
          price=data["gift_price"],
          recipient=username),
        reply_markup=confirm_keyboard(data["gift_id"], lang),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("uconfirm_"))
async def confirm_gift(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user = await get_user(callback.from_user.id)
    lang = user["language"] if user else "uz"

    if not data.get("gift_id"):
        await callback.answer("❌ Xatolik", show_alert=True)
        return

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    await callback.message.answer(
        t(lang, "confirm_pay"),
        reply_markup=payment_keyboard(data["gift_id"], lang)
    )


@router.callback_query(F.data.startswith("upay_card_"))
async def pay_card(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user = await get_user(callback.from_user.id)
    lang = user["language"] if user else "uz"

    if not data.get("gift_id"):
        await callback.answer("❌ Xatolik", show_alert=True)
        return

    card = await get_setting("card_number") or "0000 0000 0000 0000"
    owner = await get_setting("card_owner") or "Admin"

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    await callback.message.answer(
        t(lang, "gift_confirmed",
          card=card, owner=owner,
          price=data["gift_price"]),
        parse_mode="HTML"
    )

    order_id = await create_order(
        user_id=callback.from_user.id,
        gift_id=data["gift_id"],
        gift_name=data["gift_name"],
        gift_price=data["gift_price"],
        recipient=data["recipient"]
    )

    await state.update_data(order_id=order_id)
    await state.set_state(GiftState.waiting_receipt)


@router.callback_query(F.data.startswith("upay_balance_"))
async def pay_balance(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    user = await get_user(callback.from_user.id)
    lang = user["language"] if user else "uz"

    if not data.get("gift_id"):
        await callback.answer("❌ Xatolik", show_alert=True)
        return

    if user["balance"] < data["gift_price"]:
        await callback.answer(
            t(lang, "not_enough_balance"),
            show_alert=True
        )
        return

    await update_balance(callback.from_user.id, -data["gift_price"])

    order_id = await create_order(
        user_id=callback.from_user.id,
        gift_id=data["gift_id"],
        gift_name=data["gift_name"],
        gift_price=data["gift_price"],
        recipient=data["recipient"]
    )

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    await callback.message.answer(
        t(lang, "order_paid_from_balance",
          name=data["gift_name"],
          price=data["gift_price"]),
        parse_mode="HTML"
    )

    order = await get_order(order_id)
    admin_text = (
        f"🔔 <b>Yangi buyurtma #{order_id}</b> (balansdan)\n\n"
        f"👤 {callback.from_user.full_name}\n"
        f"🆔 <code>{callback.from_user.id}</code>\n\n"
        f"🎁 Gift: {order['gift_name']}\n"
        f"💰 Narxi: {order['gift_price']:,} so'm\n"
        f"🎯 Qabul qiluvchi: {order['recipient']}"
    )

    try:
        await bot.send_message(
            ADMIN_ID,
            admin_text,
            parse_mode="HTML",
            reply_markup=admin_order_keyboard(order_id)
        )
        print(f"✅ Admin xabar yuborildi: balance order #{order_id}")
    except Exception as e:
        print(f"❌ ADMIN XABAR XATOSI: {e}")

    await state.clear()


@router.message(GiftState.waiting_receipt, F.photo)
async def receipt_photo(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    user = await get_user(message.from_user.id)
    lang = user["language"] if user else "uz"

    photo = message.photo[-1]
    order_id = data.get("order_id")

    if not order_id:
        await message.answer(t(lang, "error"))
        await state.clear()
        return

    await update_order_status(order_id, "pending", receipt_file_id=photo.file_id)

    order = await get_order(order_id)
    if not order:
        await message.answer(t(lang, "error"))
        await state.clear()
        return

    admin_text = (
        f"🔔 <b>Yangi buyurtma #{order_id}</b>\n\n"
        f"👤 Foydalanuvchi: {message.from_user.full_name}\n"
        f"🆔 ID: <code>{message.from_user.id}</code>\n"
        f"📱 Username: @{message.from_user.username or 'yoq'}\n\n"
        f"🎁 Gift: {order['gift_name']}\n"
        f"💰 Narxi: {order['gift_price']:,} so'm\n"
        f"🎯 Qabul qiluvchi: {order['recipient']}\n\n"
        f"📸 Chek quyida:"
    )

    try:
        admin_msg = await bot.send_photo(
            ADMIN_ID,
            photo=photo.file_id,
            caption=admin_text,
            parse_mode="HTML",
            reply_markup=admin_order_keyboard(order_id)
        )
        await update_order_status(
            order_id, "pending",
            receipt_file_id=photo.file_id,
            admin_message_id=admin_msg.message_id
        )
        print(f"✅ Admin xabar yuborildi: order #{order_id}")
    except Exception as e:
        print(f"❌ ADMIN XABAR XATOSI: {e}")
        await message.answer(f"❌ Admin xabar yuborishda xatolik: {e}")
        return

    await message.answer(
        t(lang, "receipt_received"),
        parse_mode="HTML"
    )
    await state.clear()


@router.message(GiftState.waiting_receipt, ~F.photo)
async def receipt_not_photo(message: Message):
    user = await get_user(message.from_user.id)
    lang = user["language"] if user else "uz"
    await message.answer(
        "📸 Iltimos, chekni <b>rasm</b> sifatida yuboring.",
        parse_mode="HTML"
    )