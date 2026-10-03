from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import (
    get_stats, get_all_users, get_gifts, get_channels,
    add_channel, remove_channel, get_setting, set_setting,
    update_balance, get_order, update_order_status, get_user,
    is_admin_user, get_admins, add_admin, remove_admin,
    log_admin_action, get_admin_log, get_owner, transfer_ownership,
    add_gift, update_gift, delete_gift, toggle_gift, get_all_gifts, get_gift
)
from keyboards import (
    admin_menu, admin_back, admin_order_keyboard,
    admin_manage_keyboard, confirm_transfer_keyboard,
    confirm_remove_admin_keyboard, admin_gifts_keyboard,
    admin_gift_edit_keyboard, confirm_delete_gift_keyboard,
    cancel_admin_keyboard, color_choice_keyboard,
    channels_delete_keyboard
)
from locales import t
from config import ADMIN_ID

router = Router()


class AdminState(StatesGroup):
    waiting_broadcast = State()
    waiting_channel = State()
    waiting_reject_reason = State()
    waiting_card = State()
    waiting_card_owner = State()
    waiting_referal_bonus = State()
    waiting_admin_id = State()
    waiting_remove_id = State()
    waiting_transfer_id = State()


class GiftManageState(StatesGroup):
    waiting_name = State()
    waiting_price = State()
    waiting_emoji = State()
    waiting_color = State()
    waiting_new_name = State()
    waiting_new_price = State()
    waiting_new_emoji = State()
    waiting_new_color = State()


async def check_admin(user_id: int) -> bool:
    return await is_admin_user(user_id)


@router.message(F.text == "⚙️ Admin Panel")
async def admin_panel_button(message: Message, state: FSMContext):
    if not await check_admin(message.from_user.id):
        return

    await state.clear()

    await message.answer(
        "🔧 <b>Admin Panel</b>\n\nKerakli bo'limni tanlang:",
        reply_markup=admin_menu(),
        parse_mode="HTML"
    )


@router.message(Command("admin"))
async def admin_panel(message: Message, state: FSMContext):
    if not await check_admin(message.from_user.id):
        return

    await state.clear()

    await message.answer(
        "🔧 <b>Admin Panel</b>\n\nKerakli bo'limni tanlang:",
        reply_markup=admin_menu(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin_menu")
async def back_admin_menu(callback: CallbackQuery):
    if not await check_admin(callback.from_user.id):
        return
    await callback.message.edit_text(
        "🔧 <b>Admin Panel</b>\n\nKerakli bo'limni tanlang:",
        reply_markup=admin_menu(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if not await check_admin(callback.from_user.id):
        return
    s = await get_stats()
    text = (
        f"📊 <b>Statistika</b>\n\n"
        f"👥 Foydalanuvchilar: <b>{s['users']}</b>\n"
        f"📦 Buyurtmalar: <b>{s['orders']}</b>\n"
        f"⏳ Kutilayotgan: <b>{s['pending']}</b>\n"
        f"✅ Tasdiqlangan: <b>{s['approved']}</b>\n"
        f"💰 Umumiy summa: <b>{s['total']:,} so'm</b>"
    )
    await callback.message.edit_text(text, reply_markup=admin_back(), parse_mode="HTML")


@router.callback_query(F.data == "admin_orders")
async def admin_orders(callback: CallbackQuery):
    if not await check_admin(callback.from_user.id):
        return
    from database import DB_PATH
    import aiosqlite
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM orders WHERE status = 'pending' ORDER BY created_at DESC LIMIT 10"
        ) as cursor:
            orders = await cursor.fetchall()

    if not orders:
        await callback.message.edit_text(
            "📦 Kutilayotgan buyurtmalar yo'q",
            reply_markup=admin_back()
        )
        return

    text = "📦 <b>Kutilayotgan buyurtmalar</b>\n\n"
    for o in orders:
        text += f"#{o['id']} — {o['gift_name']} — {o['recipient']}\n"

    await callback.message.edit_text(text, reply_markup=admin_back(), parse_mode="HTML")


@router.callback_query(F.data.startswith("order_approve_"))
async def order_approve(callback: CallbackQuery, bot: Bot):
    if not await check_admin(callback.from_user.id):
        return
    order_id = int(callback.data.split("_")[2])
    order = await get_order(order_id)
    if not order:
        return

    await update_order_status(order_id, "approved")
    await log_admin_action(callback.from_user.id, "APPROVE_ORDER", f"#{order_id}")

    user = await get_user(order["user_id"])
    if user:
        lang = user["language"]
        try:
            await bot.send_message(
                order["user_id"],
                t(lang, "order_approved",
                  name=order["gift_name"],
                  recipient=order["recipient"]),
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"User xabar xatosi: {e}")

    try:
        await callback.message.edit_caption(
            caption=callback.message.caption + "\n\n✅ <b>TASDIQLANDI</b>",
            parse_mode="HTML"
        )
    except Exception:
        try:
            await callback.message.edit_text(
                callback.message.text + "\n\n✅ <b>TASDIQLANDI</b>",
                parse_mode="HTML"
            )
        except Exception:
            pass
    await callback.answer("✅ Tasdiqlandi")


@router.callback_query(F.data.startswith("order_reject_"))
async def order_reject(callback: CallbackQuery, state: FSMContext):
    if not await check_admin(callback.from_user.id):
        return
    order_id = int(callback.data.split("_")[2])
    await state.update_data(reject_order_id=order_id)
    await callback.message.answer("❌ Rad etish sababini yozing:")
    await state.set_state(AdminState.waiting_reject_reason)


@router.message(AdminState.waiting_reject_reason)
async def process_reject(message: Message, state: FSMContext, bot: Bot):
    if not await check_admin(message.from_user.id):
        return
    data = await state.get_data()
    order_id = data.get("reject_order_id")
    reason = message.text

    order = await get_order(order_id)
    await update_order_status(order_id, "rejected")
    await log_admin_action(message.from_user.id, "REJECT_ORDER", f"#{order_id}: {reason}")

    if order:
        user = await get_user(order["user_id"])
        if user:
            lang = user["language"]
            try:
                await bot.send_message(
                    order["user_id"],
                    t(lang, "order_rejected", reason=reason),
                    parse_mode="HTML"
                )
            except Exception as e:
                print(f"User xabar xatosi: {e}")

    await message.answer(f"✅ Buyurtma #{order_id} rad etildi")
    await state.clear()


@router.callback_query(F.data == "admin_gifts")
async def admin_gifts(callback: CallbackQuery):
    if not await check_admin(callback.from_user.id):
        return

    gifts = await get_all_gifts()

    if not gifts:
        text = "🎁 <b>Giftlar</b>\n\n❌ Hozircha giftlar yo'q\n\n➕ Qo'shish uchun tugmani bosing:"
    else:
        text = f"🎁 <b>Giftlar</b> ({len(gifts)})\n\n"
        text += "✅ — faol\n❌ — o'chirilgan\n\n"
        text += "Tahrirlash uchun giftni tanlang:"

    await callback.message.edit_text(
        text,
        reply_markup=admin_gifts_keyboard(gifts),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "agift_add")
async def admin_gift_add(callback: CallbackQuery, state: FSMContext):
    if not await check_admin(callback.from_user.id):
        return

    await callback.message.edit_text(
        "➕ <b>Yangi gift qo'shish</b>\n\n"
        "📝 Gift nomini yuboring:\n\n"
        "<i>Misol: 50 talik</i>",
        reply_markup=cancel_admin_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(GiftManageState.waiting_name)


@router.message(GiftManageState.waiting_name)
async def gift_add_name(message: Message, state: FSMContext):
    if not await check_admin(message.from_user.id):
        return

    name = message.text.strip()
    if len(name) < 2 or len(name) > 50:
        await message.answer("❌ Nom 2-50 belgi orasida bo'lishi kerak")
        return

    await state.update_data(name=name)

    await message.answer(
        f"💰 <b>Narxni kiriting</b>\n\n"
        f"Gift: {name}\n\n"
        f"<i>Misol: 5000</i>\n"
        f"<i>Faqat raqam, so'mda</i>",
        reply_markup=cancel_admin_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(GiftManageState.waiting_price)


@router.message(GiftManageState.waiting_price)
async def gift_add_price(message: Message, state: FSMContext):
    if not await check_admin(message.from_user.id):
        return

    try:
        price = int(message.text.replace(" ", "").replace(",", ""))
        if price < 100:
            raise ValueError
    except ValueError:
        await message.answer("❌ Noto'g'ri narx. Kamida 100 so'm")
        return

    await state.update_data(price=price)

    await message.answer(
        f"🎨 <b>Emojini kiriting</b>\n\n"
        f"<i>Misol: 💝 🧸 🎁 🌹 🎂 🚀 🏆 💍</i>\n"
        f"<i>Yoki o'tkazib yuborish uchun \"skip\" yuboring</i>",
        reply_markup=cancel_admin_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(GiftManageState.waiting_emoji)


@router.message(GiftManageState.waiting_emoji)
async def gift_add_emoji(message: Message, state: FSMContext):
    if not await check_admin(message.from_user.id):
        return

    emoji = message.text.strip()
    if emoji.lower() == "skip" or not emoji:
        emoji = "🎁"

    if len(emoji) > 10:
        await message.answer("❌ Emoji juda uzun")
        return

    await state.update_data(emoji=emoji)

    await message.answer(
        f"🖌 <b>Rangni tanlang</b>\n\n"
        f"Quyidagi ranglardan birini tanlang:",
        reply_markup=color_choice_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(GiftManageState.waiting_color)


@router.callback_query(F.data.startswith("color_"), GiftManageState.waiting_color)
async def gift_add_color_callback(callback: CallbackQuery, state: FSMContext):
    if not await check_admin(callback.from_user.id):
        return

    color = callback.data.split("_", 1)[1]
    valid_colors = ["primary", "success", "danger", "warning", "info"]
    if color not in valid_colors:
        color = "primary"

    data = await state.get_data()
    name = data.get("name", "Gift")
    price = data.get("price", 0)
    emoji = data.get("emoji", "🎁")

    gift_id = await add_gift(name, price, emoji, color)
    await log_admin_action(callback.from_user.id, "ADD_GIFT", f"#{gift_id} {name}")

    await callback.message.edit_text(
        f"✅ <b>Gift qo'shildi!</b>\n\n"
        f"🆔 #{gift_id}\n"
        f"{emoji} {name}\n"
        f"💰 {price:,} so'm\n"
        f"🖌 {color}",
        parse_mode="HTML"
    )
    await state.clear()

    gifts = await get_all_gifts()
    await callback.message.answer(
        f"🎁 <b>Giftlar</b> ({len(gifts)})",
        reply_markup=admin_gifts_keyboard(gifts),
        parse_mode="HTML"
    )


@router.message(GiftManageState.waiting_color)
async def gift_add_color_text(message: Message, state: FSMContext):
    if not await check_admin(message.from_user.id):
        return

    color = message.text.strip().lower()
    if color == "skip" or not color:
        color = "primary"

    valid_colors = ["primary", "success", "danger", "warning", "info"]
    if color not in valid_colors:
        color = "primary"

    data = await state.get_data()
    name = data.get("name", "Gift")
    price = data.get("price", 0)
    emoji = data.get("emoji", "🎁")

    gift_id = await add_gift(name, price, emoji, color)
    await log_admin_action(message.from_user.id, "ADD_GIFT", f"#{gift_id} {name}")

    await message.answer(
        f"✅ <b>Gift qo'shildi!</b>\n\n"
        f"🆔 #{gift_id}\n"
        f"{emoji} {name}\n"
        f"💰 {price:,} so'm\n"
        f"🖌 {color}",
        parse_mode="HTML"
    )
    await state.clear()

    gifts = await get_all_gifts()
    await message.answer(
        f"🎁 <b>Giftlar</b> ({len(gifts)})",
        reply_markup=admin_gifts_keyboard(gifts),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("agift_"))
async def admin_gift_view(callback: CallbackQuery):
    if not await check_admin(callback.from_user.id):
        return

    parts = callback.data.split("_")
    if len(parts) < 2:
        return

    if parts[1] == "add":
        return

    try:
        gift_id = int(parts[1])
    except ValueError:
        return

    gift = await get_gift(gift_id)
    if not gift:
        await callback.answer("❌ Gift topilmadi", show_alert=True)
        return

    status = "✅ Faol" if gift["is_active"] else "❌ O'chirilgan"

    text = (
        f"🎁 <b>Gift #{gift_id}</b>\n\n"
        f"📝 Nomi: <b>{gift['name']}</b>\n"
        f"💰 Narxi: <b>{gift['price']:,} so'm</b>\n"
        f"🎨 Emoji: <b>{gift['emoji']}</b>\n"
        f"🖌 Rang: <b>{gift['color']}</b>\n"
        f"📊 Holat: {status}\n\n"
        f"<b>Nimani o'zgartirmoqchisiz?</b>"
    )

    await callback.message.edit_text(
        text,
        reply_markup=admin_gift_edit_keyboard(gift_id, gift["is_active"]),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("gedit_name_"))
async def gift_edit_name(callback: CallbackQuery, state: FSMContext):
    if not await check_admin(callback.from_user.id):
        return

    gift_id = int(callback.data.split("_")[2])
    gift = await get_gift(gift_id)
    if not gift:
        await callback.answer("❌ Gift topilmadi", show_alert=True)
        return

    await state.update_data(gift_id=gift_id)

    await callback.message.edit_text(
        f"✏️ <b>Nomini o'zgartirish</b>\n\n"
        f"Eski: <b>{gift['name']}</b>\n\n"
        f"Yangi nomni yuboring:",
        reply_markup=cancel_admin_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(GiftManageState.waiting_new_name)


@router.message(GiftManageState.waiting_new_name)
async def gift_edit_name_save(message: Message, state: FSMContext):
    if not await check_admin(message.from_user.id):
        return

    name = message.text.strip()
    if len(name) < 2 or len(name) > 50:
        await message.answer("❌ Nom 2-50 belgi orasida")
        return

    data = await state.get_data()
    gift_id = data.get("gift_id")
    if not gift_id:
        await message.answer("❌ Xato. Qayta urinib ko'ring")
        await state.clear()
        return

    await update_gift(gift_id, name=name)
    await log_admin_action(message.from_user.id, "EDIT_GIFT_NAME", f"#{gift_id}: {name}")

    await message.answer(f"✅ Nom o'zgartirildi: <b>{name}</b>", parse_mode="HTML")
    await state.clear()

    gift = await get_gift(gift_id)
    await message.answer(
        f"🎁 <b>Gift #{gift_id}</b>\n\n"
        f"📝 {gift['name']}\n"
        f"💰 {gift['price']:,} so'm\n"
        f"🎨 {gift['emoji']}",
        reply_markup=admin_gift_edit_keyboard(gift_id, gift["is_active"]),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("gedit_price_"))
async def gift_edit_price(callback: CallbackQuery, state: FSMContext):
    if not await check_admin(callback.from_user.id):
        return

    gift_id = int(callback.data.split("_")[2])
    gift = await get_gift(gift_id)
    if not gift:
        await callback.answer("❌ Gift topilmadi", show_alert=True)
        return

    await state.update_data(gift_id=gift_id)

    await callback.message.edit_text(
        f"💰 <b>Narxni o'zgartirish</b>\n\n"
        f"Eski: <b>{gift['price']:,} so'm</b>\n\n"
        f"Yangi narxni yuboring:",
        reply_markup=cancel_admin_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(GiftManageState.waiting_new_price)


@router.message(GiftManageState.waiting_new_price)
async def gift_edit_price_save(message: Message, state: FSMContext):
    if not await check_admin(message.from_user.id):
        return

    try:
        price = int(message.text.replace(" ", "").replace(",", ""))
        if price < 100:
            raise ValueError
    except ValueError:
        await message.answer("❌ Noto'g'ri narx")
        return

    data = await state.get_data()
    gift_id = data.get("gift_id")
    if not gift_id:
        await message.answer("❌ Xato. Qayta urinib ko'ring")
        await state.clear()
        return

    await update_gift(gift_id, price=price)
    await log_admin_action(message.from_user.id, "EDIT_GIFT_PRICE", f"#{gift_id}: {price}")

    await message.answer(f"✅ Narx o'zgartirildi: <b>{price:,} so'm</b>", parse_mode="HTML")
    await state.clear()

    gift = await get_gift(gift_id)
    await message.answer(
        f"🎁 <b>Gift #{gift_id}</b>\n\n"
        f"📝 {gift['name']}\n"
        f"💰 {gift['price']:,} so'm\n"
        f"🎨 {gift['emoji']}",
        reply_markup=admin_gift_edit_keyboard(gift_id, gift["is_active"]),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("gedit_emoji_"))
async def gift_edit_emoji(callback: CallbackQuery, state: FSMContext):
    if not await check_admin(callback.from_user.id):
        return

    gift_id = int(callback.data.split("_")[2])
    gift = await get_gift(gift_id)
    if not gift:
        await callback.answer("❌ Gift topilmadi", show_alert=True)
        return

    await state.update_data(gift_id=gift_id)

    await callback.message.edit_text(
        f"🎨 <b>Emojini o'zgartirish</b>\n\n"
        f"Eski: <b>{gift['emoji']}</b>\n\n"
        f"Yangi emojini yuboring:\n\n"
        f"<i>Misol: 💝 🧸 🎁 🌹 🎂 🚀 🏆 💍</i>",
        reply_markup=cancel_admin_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(GiftManageState.waiting_new_emoji)


@router.message(GiftManageState.waiting_new_emoji)
async def gift_edit_emoji_save(message: Message, state: FSMContext):
    if not await check_admin(message.from_user.id):
        return

    emoji = message.text.strip()
    if len(emoji) > 10:
        await message.answer("❌ Emoji juda uzun")
        return

    data = await state.get_data()
    gift_id = data.get("gift_id")
    if not gift_id:
        await message.answer("❌ Xato. Qayta urinib ko'ring")
        await state.clear()
        return

    await update_gift(gift_id, emoji=emoji)
    await log_admin_action(message.from_user.id, "EDIT_GIFT_EMOJI", f"#{gift_id}: {emoji}")

    await message.answer(f"✅ Emoji o'zgartirildi: <b>{emoji}</b>", parse_mode="HTML")
    await state.clear()

    gift = await get_gift(gift_id)
    await message.answer(
        f"🎁 <b>Gift #{gift_id}</b>\n\n"
        f"📝 {gift['name']}\n"
        f"💰 {gift['price']:,} so'm\n"
        f"🎨 {gift['emoji']}",
        reply_markup=admin_gift_edit_keyboard(gift_id, gift["is_active"]),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("gedit_color_"))
async def gift_edit_color(callback: CallbackQuery, state: FSMContext):
    if not await check_admin(callback.from_user.id):
        return

    gift_id = int(callback.data.split("_")[2])
    gift = await get_gift(gift_id)
    if not gift:
        await callback.answer("❌ Gift topilmadi", show_alert=True)
        return

    await state.update_data(gift_id=gift_id)

    await callback.message.edit_text(
        f"🖌 <b>Rangni o'zgartirish</b>\n\n"
        f"Eski: <b>{gift['color']}</b>\n\n"
        f"Yangi rangni tanlang:",
        reply_markup=color_choice_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(GiftManageState.waiting_new_color)


@router.callback_query(F.data.startswith("color_"), GiftManageState.waiting_new_color)
async def gift_edit_color_callback(callback: CallbackQuery, state: FSMContext):
    if not await check_admin(callback.from_user.id):
        return

    color = callback.data.split("_", 1)[1]
    valid_colors = ["primary", "success", "danger", "warning", "info"]
    if color not in valid_colors:
        color = "primary"

    data = await state.get_data()
    gift_id = data.get("gift_id")
    if not gift_id:
        await callback.answer("❌ Xato", show_alert=True)
        await state.clear()
        return

    await update_gift(gift_id, color=color)
    await log_admin_action(callback.from_user.id, "EDIT_GIFT_COLOR", f"#{gift_id}: {color}")

    await callback.message.edit_text(
        f"✅ Rang o'zgartirildi: <b>{color}</b>",
        parse_mode="HTML"
    )
    await state.clear()

    gift = await get_gift(gift_id)
    await callback.message.answer(
        f"🎁 <b>Gift #{gift_id}</b>\n\n"
        f"📝 {gift['name']}\n"
        f"💰 {gift['price']:,} so'm\n"
        f"🎨 {gift['emoji']}\n"
        f"🖌 {gift['color']}",
        reply_markup=admin_gift_edit_keyboard(gift_id, gift["is_active"]),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("gtoggle_"))
async def gift_toggle(callback: CallbackQuery):
    if not await check_admin(callback.from_user.id):
        return

    gift_id = int(callback.data.split("_")[1])
    gift = await get_gift(gift_id)
    if not gift:
        await callback.answer("❌ Gift topilmadi", show_alert=True)
        return

    await toggle_gift(gift_id)
    await log_admin_action(callback.from_user.id, "TOGGLE_GIFT", f"#{gift_id}")

    gift = await get_gift(gift_id)
    status = "✅ Faol" if gift["is_active"] else "❌ O'chirilgan"

    await callback.answer(f"Holat: {status}", show_alert=True)

    await callback.message.edit_text(
        f"🎁 <b>Gift #{gift_id}</b>\n\n"
        f"📝 {gift['name']}\n"
        f"💰 {gift['price']:,} so'm\n"
        f"🎨 {gift['emoji']}\n"
        f"📊 {status}",
        reply_markup=admin_gift_edit_keyboard(gift_id, gift["is_active"]),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("gdelete_yes_"))
async def gift_delete_yes(callback: CallbackQuery):
    if not await check_admin(callback.from_user.id):
        return

    gift_id = int(callback.data.split("_")[2])
    gift = await get_gift(gift_id)
    if not gift:
        await callback.answer("❌ Gift topilmadi", show_alert=True)
        return

    await delete_gift(gift_id)
    await log_admin_action(callback.from_user.id, "DELETE_GIFT", f"#{gift_id} {gift['name']}")

    await callback.answer("✅ O'chirildi")

    gifts = await get_all_gifts()
    text = f"🎁 <b>Giftlar</b> ({len(gifts)})\n\nTahrirlash uchun giftni tanlang:"

    await callback.message.edit_text(
        text,
        reply_markup=admin_gifts_keyboard(gifts),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("gdelete_"))
async def gift_delete(callback: CallbackQuery):
    if not await check_admin(callback.from_user.id):
        return

    parts = callback.data.split("_")
    if len(parts) < 2:
        return

    if parts[1] == "yes":
        return

    try:
        gift_id = int(parts[1])
    except ValueError:
        return

    gift = await get_gift(gift_id)
    if not gift:
        await callback.answer("❌ Gift topilmadi", show_alert=True)
        return

    await callback.message.edit_text(
        f"⚠️ <b>Tasdiqlaysizmi?</b>\n\n"
        f"🎁 {gift['emoji']} {gift['name']}\n"
        f"💰 {gift['price']:,} so'm\n\n"
        f"<b>Bu amalni bekor qilib bo'lmaydi!</b>",
        reply_markup=confirm_delete_gift_keyboard(gift_id),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin_channels")
async def admin_channels(callback: CallbackQuery):
    if not await check_admin(callback.from_user.id):
        return
    channels = await get_channels()
    text = "📢 <b>Majburiy obuna kanallari</b>\n\n"
    if not channels:
        text += "❌ Kanallar yo'q\n\n"
    else:
        for i, ch in enumerate(channels, 1):
            text += f"{i}. @{ch['channel_username']}\n"
    text += "\n➕ Kanal qo'shish: /addchannel"
    text += "\n🗑 Kanal o'chirish: /removechannel"
    await callback.message.edit_text(text, reply_markup=admin_back(), parse_mode="HTML")


@router.message(Command("addchannel"))
async def add_channel_cmd(message: Message, state: FSMContext):
    if not await check_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer(
        "📢 Kanal username yuboring:\n\n"
        "<i>Misol: @mychannel</i>\n\n"
        "⚠️ <b>Diqqat:</b> Bot kanalga <b>admin</b> bo'lishi kerak!",
        parse_mode="HTML"
    )
    await state.set_state(AdminState.waiting_channel)


@router.message(AdminState.waiting_channel)
async def process_add_channel(message: Message, state: FSMContext):
    if not await check_admin(message.from_user.id):
        return

    text = message.text.strip()

    if text.startswith("https://t.me/"):
        text = text.replace("https://t.me/", "@")
    elif text.startswith("t.me/"):
        text = text.replace("t.me/", "@")
    elif not text.startswith("@") and not text.startswith("-"):
        text = "@" + text

    if text.startswith("-"):
        username = text
        channel_id = text
    else:
        username = text.lstrip("@")
        channel_id = text

    if len(username) < 4:
        await message.answer("❌ Username juda qisqa. Qayta kiriting:")
        return

    await add_channel(channel_id, username, username)
    await log_admin_action(message.from_user.id, "ADD_CHANNEL", channel_id)

    await message.answer(
        f"✅ <b>Kanal qo'shildi!</b>\n\n"
        f"🔗 Username: @{username}\n"
        f"🆔 ID: <code>{channel_id}</code>\n\n"
        f"⚠️ Botni kanalga <b>admin</b> qilishni unutmang!",
        parse_mode="HTML"
    )
    await state.clear()


@router.message(Command("removechannel"))
async def remove_channel_cmd(message: Message):
    if not await check_admin(message.from_user.id):
        return
    channels = await get_channels()
    if not channels:
        await message.answer("❌ Kanallar yo'q")
        return

    await message.answer(
        "🗑 <b>Qaysi kanalni o'chirish?</b>\n\n"
        "Quyidagi tugmalardan birini tanlang:",
        reply_markup=channels_delete_keyboard(channels),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("delchannel_"))
async def del_channel_callback(callback: CallbackQuery):
    if not await check_admin(callback.from_user.id):
        return

    try:
        channel_id = int(callback.data.split("_")[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Xato", show_alert=True)
        return

    await remove_channel(channel_id)
    await log_admin_action(callback.from_user.id, "REMOVE_CHANNEL", f"ID: {channel_id}")

    await callback.answer("✅ Kanal o'chirildi", show_alert=True)

    channels = await get_channels()
    if not channels:
        text = "📢 <b>Majburiy obuna kanallari</b>\n\n❌ Kanallar yo'q"
    else:
        text = "📢 <b>Majburiy obuna kanallari</b>\n\n"
        for i, ch in enumerate(channels, 1):
            text += f"{i}. @{ch['channel_username']}\n"

    await callback.message.edit_text(
        text,
        reply_markup=admin_back(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin_settings")
async def admin_settings(callback: CallbackQuery):
    if not await check_admin(callback.from_user.id):
        return
    card = await get_setting("card_number") or "0000 0000 0000 0000"
    owner = await get_setting("card_owner") or "Admin"
    bonus = int(await get_setting("referal_bonus") or 1000)
    text = (
        f"⚙️ <b>Sozlamalar</b>\n\n"
        f"💳 Karta: <code>{card}</code>\n"
        f"👤 Egasi: {owner}\n"
        f"🎁 Referal bonusi: {bonus:,} so'm\n\n"
        f"<b>O'zgartirish:</b>\n"
        f"/setcard — karta raqami\n"
        f"/setowner — karta egasi\n"
        f"/setbonus — referal bonusi"
    )
    await callback.message.edit_text(text, reply_markup=admin_back(), parse_mode="HTML")


@router.message(Command("setcard"))
async def set_card_cmd(message: Message, state: FSMContext):
    if not await check_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer(
        "💳 Yangi karta raqamini yuboring:\n\n<i>Misol: 8600 1234 5678 9012</i>",
        parse_mode="HTML"
    )
    await state.set_state(AdminState.waiting_card)


@router.message(AdminState.waiting_card)
async def process_set_card(message: Message, state: FSMContext):
    if not await check_admin(message.from_user.id):
        return
    await set_setting("card_number", message.text.strip())
    await log_admin_action(message.from_user.id, "SET_CARD", message.text.strip())
    await message.answer("✅ Karta raqami yangilandi")
    await state.clear()


@router.message(Command("setowner"))
async def set_owner_cmd(message: Message, state: FSMContext):
    if not await check_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer("👤 Yangi karta egasini yuboring:")
    await state.set_state(AdminState.waiting_card_owner)


@router.message(AdminState.waiting_card_owner)
async def process_set_owner(message: Message, state: FSMContext):
    if not await check_admin(message.from_user.id):
        return
    await set_setting("card_owner", message.text.strip())
    await log_admin_action(message.from_user.id, "SET_CARD_OWNER", message.text.strip())
    await message.answer("✅ Karta egasi yangilandi")
    await state.clear()


@router.message(Command("setbonus"))
async def set_bonus_cmd(message: Message, state: FSMContext):
    if not await check_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer("🎁 Yangi referal bonusini kiriting (so'mda):")
    await state.set_state(AdminState.waiting_referal_bonus)


@router.message(AdminState.waiting_referal_bonus)
async def process_set_bonus(message: Message, state: FSMContext):
    if not await check_admin(message.from_user.id):
        return
    try:
        bonus = int(message.text.strip())
        await set_setting("referal_bonus", str(bonus))
        await log_admin_action(message.from_user.id, "SET_BONUS", str(bonus))
        await message.answer(f"✅ Referal bonusi: {bonus:,} so'm")
        await state.clear()
    except ValueError:
        await message.answer("❌ Noto'g'ri raqam")


@router.callback_query(F.data == "admin_users")
async def admin_users(callback: CallbackQuery):
    if not await check_admin(callback.from_user.id):
        return
    users = await get_all_users()
    text = f"👥 <b>Foydalanuvchilar</b> ({len(users)})\n\n"
    for u in users[:20]:
        text += f"• {u['full_name']} — <code>{u['user_id']}</code>\n"
    if len(users) > 20:
        text += f"\n... va yana {len(users) - 20} ta"
    await callback.message.edit_text(text, reply_markup=admin_back(), parse_mode="HTML")


@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(callback: CallbackQuery, state: FSMContext):
    if not await check_admin(callback.from_user.id):
        return
    await callback.message.answer("📤 Yuboriladigan xabarni kiriting:")
    await state.set_state(AdminState.waiting_broadcast)


@router.message(AdminState.waiting_broadcast)
async def process_broadcast(message: Message, state: FSMContext, bot: Bot):
    if not await check_admin(message.from_user.id):
        return
    users = await get_all_users()
    sent = 0
    failed = 0
    for u in users:
        try:
            if message.photo:
                await bot.send_photo(u["user_id"], photo=message.photo[-1].file_id,
                                     caption=message.caption or "")
            elif message.video:
                await bot.send_video(u["user_id"], video=message.video.file_id,
                                     caption=message.caption or "")
            else:
                await bot.send_message(u["user_id"], message.text)
            sent += 1
        except Exception:
            failed += 1
    await log_admin_action(message.from_user.id, "BROADCAST", f"sent={sent}, failed={failed}")
    await message.answer(f"✅ Yuborildi: {sent}\n❌ Xatolik: {failed}")
    await state.clear()


@router.callback_query(F.data == "admin_manage")
async def admin_manage(callback: CallbackQuery):
    if not await check_admin(callback.from_user.id):
        return

    owner = await get_owner()
    is_owner = owner and owner["user_id"] == callback.from_user.id

    owner_name = owner['full_name'] if owner and owner['full_name'] else 'Noma lum'
    owner_id = owner['user_id'] if owner else '—'
    role_text = "👑 Egasi" if is_owner else "👤 Admin"

    text = (
        f"👑 <b>Adminlar boshqaruvi</b>\n\n"
        f"👤 Egasi: {owner_name}\n"
        f"🆔 <code>{owner_id}</code>\n\n"
        f"<b>Sizning huquqingiz:</b> {role_text}\n\n"
        f"Quyidagilardan birini tanlang:"
    )

    await callback.message.edit_text(
        text,
        reply_markup=admin_manage_keyboard(is_owner=is_owner),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin_list")
async def admin_list(callback: CallbackQuery):
    if not await check_admin(callback.from_user.id):
        return

    admins = await get_admins()

    text = f"👑 <b>Adminlar ro'yxati</b> ({len(admins)})\n\n"

    for a in admins:
        emoji = "👑" if a["role"] == "owner" else "👤"
        uname = a["username"] if a["username"] else "yoq"
        full_name = a["full_name"] if a["full_name"] else "Noma lum"
        text += (
            f"{emoji} <b>{full_name}</b>\n"
            f"   🆔 <code>{a['user_id']}</code>\n"
            f"   📱 @{uname}\n"
            f"   🎭 {a['role']}\n\n"
        )

    await callback.message.edit_text(
        text,
        reply_markup=admin_back(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin_add")
async def admin_add_start(callback: CallbackQuery, state: FSMContext):
    if not await check_admin(callback.from_user.id):
        return

    await callback.message.edit_text(
        f"➕ <b>Admin qo'shish</b>\n\n"
        f"Yangi adminning <b>Telegram ID</b> sini yuboring.\n\n"
        f"<i>ID olish: @userinfobot ga o'ting va /start bosing</i>",
        reply_markup=admin_back(),
        parse_mode="HTML"
    )
    await state.set_state(AdminState.waiting_admin_id)


@router.message(AdminState.waiting_admin_id)
async def admin_add_process(message: Message, state: FSMContext, bot: Bot):
    if not await check_admin(message.from_user.id):
        return

    try:
        new_admin_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Noto'g'ri ID. Faqat raqam yuboring.")
        return

    if new_admin_id == message.from_user.id:
        await message.answer("❌ Siz o'zingizni admin qila olmaysiz.")
        return

    existing = await is_admin_user(new_admin_id)
    if existing:
        await message.answer("❌ Bu foydalanuvchi allaqachon admin.")
        return

    try:
        chat = await bot.get_chat(new_admin_id)
        username = chat.username or ""
        full_name = chat.full_name or chat.first_name or "Noma lum"
    except Exception:
        await message.answer(
            f"❌ Foydalanuvchi topilmadi.\n\n"
            f"Sabab: u botga <b>/start</b> bosmagan bo'lishi mumkin.\n\n"
            f"Avval u botga kirishi kerak.",
            parse_mode="HTML"
        )
        await state.clear()
        return

    await add_admin(new_admin_id, username, full_name, message.from_user.id)
    await log_admin_action(message.from_user.id, "ADD_ADMIN", f"{new_admin_id}")

    await message.answer(
        f"✅ <b>Admin qo'shildi!</b>\n\n"
        f"👤 {full_name}\n"
        f"🆔 <code>{new_admin_id}</code>\n"
        f"📱 @{username or 'yoq'}",
        parse_mode="HTML"
    )

    try:
        await bot.send_message(
            new_admin_id,
            f"🎉 Siz <b>admin</b> etib tayinlandingiz!\n\n"
            f"Admin panel: /admin",
            parse_mode="HTML"
        )
    except Exception:
        pass

    await state.clear()


@router.callback_query(F.data == "admin_remove")
async def admin_remove_start(callback: CallbackQuery, state: FSMContext):
    if not await check_admin(callback.from_user.id):
        return

    admins = await get_admins()
    if len(admins) <= 1:
        await callback.answer("❌ Faqat bitta admin qolgan", show_alert=True)
        return

    text = "➖ <b>Admin o'chirish</b>\n\nQaysi adminni o'chirish?\n\n"
    for a in admins:
        if a["role"] != "owner":
            full_name = a["full_name"] if a["full_name"] else "Noma lum"
            text += f"🆔 <code>{a['user_id']}</code> — {full_name}\n"

    text += "\n<i>ID ni yuboring</i>"

    await callback.message.edit_text(
        text,
        reply_markup=admin_back(),
        parse_mode="HTML"
    )
    await state.set_state(AdminState.waiting_remove_id)


@router.message(AdminState.waiting_remove_id)
async def admin_remove_process(message: Message, state: FSMContext, bot: Bot):
    if not await check_admin(message.from_user.id):
        return

    try:
        remove_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Noto'g'ri ID")
        return

    owner = await get_owner()
    if owner and owner["user_id"] == remove_id:
        await message.answer("❌ Egani o'chirib bo'lmaydi!")
        return

    result = await remove_admin(remove_id)
    if result:
        await log_admin_action(message.from_user.id, "REMOVE_ADMIN", f"{remove_id}")
        await message.answer(f"✅ Admin o'chirildi (ID: {remove_id})")

        try:
            await bot.send_message(
                remove_id,
                "⚠️ Siz adminlikdan chiqarildingiz."
            )
        except Exception:
            pass
    else:
        await message.answer("❌ Admin topilmadi yoki o'chirib bo'lmaydi")

    await state.clear()


@router.callback_query(F.data == "admin_transfer")
async def admin_transfer_start(callback: CallbackQuery, state: FSMContext):
    if not await check_admin(callback.from_user.id):
        return

    owner = await get_owner()
    if not owner or owner["user_id"] != callback.from_user.id:
        await callback.answer("❌ Faqat egasi o'tkazishi mumkin!", show_alert=True)
        return

    await callback.message.edit_text(
        f"🔄 <b>Egalikni o'tkazish</b>\n\n"
        f"⚠️ <b>Diqqat!</b> Bu amalni <b>bekor qilib bo'lmaydi</b>!\n\n"
        f"Yangi egasining <b>Telegram ID</b> sini yuboring:",
        reply_markup=admin_back(),
        parse_mode="HTML"
    )
    await state.set_state(AdminState.waiting_transfer_id)


@router.message(AdminState.waiting_transfer_id)
async def admin_transfer_process(message: Message, state: FSMContext, bot: Bot):
    if not await check_admin(message.from_user.id):
        return

    try:
        new_owner_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Noto'g'ri ID")
        return

    if new_owner_id == message.from_user.id:
        await message.answer("❌ Siz allaqachon egasiz")
        return

    try:
        chat = await bot.get_chat(new_owner_id)
        username = chat.username or ""
        full_name = chat.full_name or chat.first_name or "Noma lum"
    except Exception:
        await message.answer("❌ Foydalanuvchi topilmadi")
        await state.clear()
        return

    await state.update_data(
        new_owner_id=new_owner_id,
        new_owner_username=username,
        new_owner_name=full_name
    )

    await message.answer(
        f"⚠️ <b>Tasdiqlaysizmi?</b>\n\n"
        f"Yangi egasi:\n"
        f"👤 {full_name}\n"
        f"🆔 <code>{new_owner_id}</code>\n"
        f"📱 @{username or 'yoq'}\n\n"
        f"<b>Bu amalni bekor qilib bo'lmaydi!</b>",
        reply_markup=confirm_transfer_keyboard(new_owner_id),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("transfer_yes_"))
async def admin_transfer_confirm(callback: CallbackQuery, state: FSMContext, bot: Bot):
    if not await check_admin(callback.from_user.id):
        return

    data = await state.get_data()
    new_owner_id = data.get("new_owner_id")
    new_owner_username = data.get("new_owner_username", "")
    new_owner_name = data.get("new_owner_name", "")

    if not new_owner_id:
        await callback.answer("❌ Xato", show_alert=True)
        return

    await transfer_ownership(new_owner_id, new_owner_username, new_owner_name)
    await log_admin_action(callback.from_user.id, "TRANSFER_OWNERSHIP", f"to {new_owner_id}")

    await callback.message.edit_text(
        f"✅ <b>Egalik o'tkazildi!</b>\n\n"
        f"Yangi egasi: {new_owner_name}\n"
        f"🆔 <code>{new_owner_id}</code>",
        parse_mode="HTML"
    )

    try:
        await bot.send_message(
            new_owner_id,
            f"👑 <b>Tabriklaymiz!</b>\n\n"
            f"Siz endi botning <b>egasi</b>siz!\n\n"
            f"Admin panel: /admin",
            parse_mode="HTML"
        )
    except Exception:
        pass

    await state.clear()


@router.callback_query(F.data == "admin_log")
async def admin_log_view(callback: CallbackQuery):
    if not await check_admin(callback.from_user.id):
        return

    logs = await get_admin_log(30)

    if not logs:
        await callback.message.edit_text(
            "📜 Admin log bo'sh",
            reply_markup=admin_back()
        )
        return

    text = "📜 <b>Admin log</b> (so'nggi 30)\n\n"
    for log in logs:
        time_str = str(log["created_at"])[:16]
        text += f"🕐 {time_str}\n"
        text += f"👤 <code>{log['admin_id']}</code>\n"
        text += f"🔧 {log['action']}\n"
        if log["details"]:
            text += f"📝 {log['details'][:50]}\n"
        text += "\n"

    if len(text) > 4000:
        text = text[:4000] + "\n\n..."

    await callback.message.edit_text(
        text,
        reply_markup=admin_back(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("topup_approve_"))
async def topup_approve(callback: CallbackQuery, bot: Bot):
    if not await check_admin(callback.from_user.id):
        return
    parts = callback.data.split("_")
    user_id = int(parts[2])
    amount = int(parts[3])

    await update_balance(user_id, amount)
    await log_admin_action(callback.from_user.id, "APPROVE_TOPUP", f"{user_id}: +{amount}")

    user = await get_user(user_id)
    if user:
        lang = user["language"]
        try:
            await bot.send_message(
                user_id,
                t(lang, "balance_topped", balance=user["balance"] + amount),
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"User xabar xatosi: {e}")

    try:
        await callback.message.edit_caption(
            caption=callback.message.caption + f"\n\n✅ <b>TASDIQLANDI (+{amount:,})</b>",
            parse_mode="HTML"
        )
    except Exception:
        pass
    await callback.answer("✅ Balans to'ldirildi")


@router.callback_query(F.data.startswith("topup_reject_"))
async def topup_reject(callback: CallbackQuery, bot: Bot):
    if not await check_admin(callback.from_user.id):
        return
    parts = callback.data.split("_")
    user_id = int(parts[2])

    await log_admin_action(callback.from_user.id, "REJECT_TOPUP", f"{user_id}")

    user = await get_user(user_id)
    if user:
        lang = user["language"]
        try:
            await bot.send_message(
                user_id,
                "❌ Balans to'ldirish rad etildi",
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"User xabar xatosi: {e}")

    try:
        await callback.message.edit_caption(
            caption=callback.message.caption + "\n\n❌ <b>RAD ETILDI</b>",
            parse_mode="HTML"
        )
    except Exception:
        pass
    await callback.answer("❌ Rad etildi")
