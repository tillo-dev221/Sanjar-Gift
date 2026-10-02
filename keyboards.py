from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
    BotCommand
)
from locales import t


def get_bot_commands(lang='uz', is_admin=False):
    commands = {
        'uz': [
            BotCommand(command="start", description="🏠 Asosiy menyu"),
            BotCommand(command="help", description="❓ Yordam"),
            BotCommand(command="cancel", description="❌ Bekor qilish"),
        ],
        'ru': [
            BotCommand(command="start", description="🏠 Главное меню"),
            BotCommand(command="help", description="❓ Помощь"),
            BotCommand(command="cancel", description="❌ Отмена"),
        ],
        'en': [
            BotCommand(command="start", description="🏠 Main menu"),
            BotCommand(command="help", description="❓ Help"),
            BotCommand(command="cancel", description="❌ Cancel"),
        ]
    }

    admin_commands = {
        'uz': [BotCommand(command="admin", description="🔧 Admin panel")],
        'ru': [BotCommand(command="admin", description="🔧 Админ панель")],
        'en': [BotCommand(command="admin", description="🔧 Admin panel")],
    }

    base = list(commands.get(lang, commands['uz']))
    if is_admin:
        base.extend(admin_commands.get(lang, admin_commands['uz']))
    return base


def lang_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇺🇿 O'zbek", callback_data="lang_uz")],
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")],
        [InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")],
    ])


def main_menu(lang, is_admin=False):
    keyboard = [
        [KeyboardButton(text="🎁 Giftlar"), KeyboardButton(text="💰 Balans")],
        [KeyboardButton(text="👥 Referal"), KeyboardButton(text="📞 Support")],
    ]

    if is_admin:
        keyboard.append([KeyboardButton(text="⚙️ Admin Panel")])

    keyboard.append([KeyboardButton(text="🌐 Til")])

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True
    )


def gifts_keyboard(gifts, lang):
    buttons = []
    for g in gifts:
        emoji = g['emoji'] if g['emoji'] else '🎁'
        buttons.append([InlineKeyboardButton(
            text=f"{emoji} {g['name']} — {g['price']:,} so'm",
            callback_data=f"ugift_{g['id']}"
        )])
    buttons.append([InlineKeyboardButton(
        text=t(lang, "back"),
        callback_data="back_main"
    )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def confirm_keyboard(gift_id, lang):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "yes"), callback_data=f"uconfirm_{gift_id}")],
        [InlineKeyboardButton(text=t(lang, "no"), callback_data="back_gifts")],
    ])


def payment_keyboard(gift_id, lang):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "card_pay"), callback_data=f"upay_card_{gift_id}")],
        [InlineKeyboardButton(text=t(lang, "balance_pay"), callback_data=f"upay_balance_{gift_id}")],
        [InlineKeyboardButton(text=t(lang, "cancel"), callback_data="back_gifts")],
    ])


def back_keyboard(lang, action="back_main"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "back"), callback_data=action)]
    ])


def subscribe_keyboard(channels, lang):
    buttons = []
    for ch in channels:
        username = ch['channel_username'].lstrip('@')
        buttons.append([InlineKeyboardButton(
            text=f"📢 {username}",
            url=f"https://t.me/{username}"
        )])
    buttons.append([InlineKeyboardButton(
        text=t(lang, "subscribe_check"),
        callback_data="check_sub"
    )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def balance_keyboard(lang):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Balans to'ldirish", callback_data="topup")],
        [InlineKeyboardButton(text=t(lang, "back"), callback_data="back_main")],
    ])


def confirm_topup_keyboard(lang):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "cancel"), callback_data="back_balance")],
    ])


def admin_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats")],
        [InlineKeyboardButton(text="🎁 Giftlar", callback_data="admin_gifts")],
        [InlineKeyboardButton(text="📦 Buyurtmalar", callback_data="admin_orders")],
        [InlineKeyboardButton(text="👥 Foydalanuvchilar", callback_data="admin_users")],
        [InlineKeyboardButton(text="📢 Kanallar", callback_data="admin_channels")],
        [InlineKeyboardButton(text="⚙️ Sozlamalar", callback_data="admin_settings")],
        [InlineKeyboardButton(text="👑 Adminlar", callback_data="admin_manage")],
        [InlineKeyboardButton(text="📤 Xabar yuborish", callback_data="admin_broadcast")],
    ])


def admin_manage_keyboard(is_owner=False):
    buttons = [
        [InlineKeyboardButton(text="➕ Admin qo'shish", callback_data="admin_add")],
        [InlineKeyboardButton(text="➖ Admin o'chirish", callback_data="admin_remove")],
        [InlineKeyboardButton(text="👑 Adminlar ro'yxati", callback_data="admin_list")],
    ]
    if is_owner:
        buttons.append([InlineKeyboardButton(text="🔄 Egalikni o'tkazish", callback_data="admin_transfer")])
    buttons.append([InlineKeyboardButton(text="📜 Admin log", callback_data="admin_log")])
    buttons.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def confirm_transfer_keyboard(user_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Ha, o'tkazish", callback_data=f"transfer_yes_{user_id}")],
        [InlineKeyboardButton(text="❌ Yo'q", callback_data="admin_manage")],
    ])


def confirm_remove_admin_keyboard(user_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Ha, o'chirish", callback_data=f"remove_admin_yes_{user_id}")],
        [InlineKeyboardButton(text="❌ Yo'q", callback_data="admin_manage")],
    ])


def admin_order_keyboard(order_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Qabul qilish", callback_data=f"order_approve_{order_id}")],
        [InlineKeyboardButton(text="❌ Rad etish", callback_data=f"order_reject_{order_id}")],
    ])


def admin_back():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_menu")]
    ])


def admin_gifts_keyboard(gifts):
    buttons = []
    for g in gifts:
        status = "✅" if g["is_active"] else "❌"
        emoji = g['emoji'] if g['emoji'] else '🎁'
        buttons.append([InlineKeyboardButton(
            text=f"{status} {emoji} {g['name']} — {g['price']:,}",
            callback_data=f"agift_{g['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="➕ Yangi gift qo'shish", callback_data="agift_add")])
    buttons.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_gift_edit_keyboard(gift_id, is_active):
    toggle_text = "❌ O'chirish" if is_active else "✅ Yoqish"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Nomini o'zgartirish", callback_data=f"gedit_name_{gift_id}")],
        [InlineKeyboardButton(text="💰 Narxini o'zgartirish", callback_data=f"gedit_price_{gift_id}")],
        [InlineKeyboardButton(text="🎨 Emojini o'zgartirish", callback_data=f"gedit_emoji_{gift_id}")],
        [InlineKeyboardButton(text="🖌 Rangni o'zgartirish", callback_data=f"gedit_color_{gift_id}")],
        [InlineKeyboardButton(text=toggle_text, callback_data=f"gtoggle_{gift_id}")],
        [InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"gdelete_{gift_id}")],
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_gifts")],
    ])


def confirm_delete_gift_keyboard(gift_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Ha, o'chirish", callback_data=f"gdelete_yes_{gift_id}")],
        [InlineKeyboardButton(text="❌ Yo'q", callback_data=f"agift_{gift_id}")],
    ])


def cancel_admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin_gifts")]
    ])


def color_choice_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Yashil", callback_data="color_success")],
        [InlineKeyboardButton(text="🔵 Ko'k", callback_data="color_primary")],
        [InlineKeyboardButton(text="🔴 Qizil", callback_data="color_danger")],
        [InlineKeyboardButton(text="🟡 Sariq", callback_data="color_warning")],
        [InlineKeyboardButton(text="⚪ Kulrang", callback_data="color_info")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin_gifts")],
    ])


def channels_delete_keyboard(channels):
    buttons = []
    for ch in channels:
        buttons.append([InlineKeyboardButton(
            text=f"🗑 @{ch['channel_username']}",
            callback_data=f"delchannel_{ch['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)