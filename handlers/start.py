import random
import string
from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from database import (
    get_user, create_user, set_language, get_channels,
    update_balance, get_setting, is_admin_user, update_admin_info
)
from keyboards import (
    lang_keyboard, main_menu, subscribe_keyboard, get_bot_commands
)
from locales import t

router = Router()


def generate_referal_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))


@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot, command: Command, state: FSMContext):
    await state.clear()

    user_id = message.from_user.id
    args = command.args

    user = await get_user(user_id)
    refered_by = None

    if not user and args:
        try:
            ref_id = int(args)
            if ref_id != user_id:
                ref_user = await get_user(ref_id)
                if ref_user:
                    refered_by = ref_id
        except ValueError:
            pass

    if not user:
        code = generate_referal_code()
        await create_user(
            user_id=user_id,
            username=message.from_user.username or "",
            full_name=message.from_user.full_name,
            referal_code=code,
            refered_by=refered_by
        )
        if refered_by:
            bonus = int(await get_setting("referal_bonus") or 1000)
            await update_balance(refered_by, bonus)
            try:
                await bot.send_message(
                    refered_by,
                    f"🎉 Yangi referal!\n\n"
                    f"👤 {message.from_user.full_name}\n"
                    f"💰 +{bonus:,} so'm"
                )
            except Exception as e:
                print(f"Referal xabar xatosi: {e}")

    user = await get_user(user_id)
    lang = user["language"] if user else "uz"

    is_admin = await is_admin_user(user_id)

    if is_admin:
        await update_admin_info(
            user_id,
            message.from_user.username or "",
            message.from_user.full_name or ""
        )

    try:
        await bot.set_my_commands(get_bot_commands(lang, is_admin=is_admin))
    except Exception as e:
        print(f"set_my_commands xatosi: {e}")

    await message.answer(
        t(lang, "welcome", name=message.from_user.first_name),
        reply_markup=main_menu(lang, is_admin=is_admin),
        parse_mode="HTML"
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    user = await get_user(message.from_user.id)
    lang = user["language"] if user else "uz"

    is_admin = await is_admin_user(message.from_user.id)

    text = (
        f"❓ <b>Yordam</b>\n\n"
        f"<b>Buyruqlar:</b>\n"
        f"/start — Asosiy menyu\n"
        f"/help — Yordam\n"
        f"/cancel — Bekor qilish\n"
    )

    if is_admin:
        text += f"\n<b>Admin buyruqlar:</b>\n/admin — Admin panel\n"

    text += (
        f"\n<b>Asosiy menyu:</b>\n"
        f"🎁 Giftlar — Gift sotib olish\n"
        f"💰 Balans — Balansni ko'rish\n"
        f"👥 Referal — Referal tizimi\n"
        f"📞 Support — Qo'llab-quvvatlash\n"
        f"🌐 Til — Tilni o'zgartirish\n"
    )

    if is_admin:
        text += f"⚙️ Admin Panel — Boshqaruv paneli\n"

    await message.answer(text, parse_mode="HTML")


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()

    user = await get_user(message.from_user.id)
    lang = user["language"] if user else "uz"
    is_admin = await is_admin_user(message.from_user.id)
    await message.answer(
        t(lang, "cancelled"),
        reply_markup=main_menu(lang, is_admin=is_admin)
    )


@router.callback_query(F.data == "check_sub")
async def check_sub_callback(callback: CallbackQuery, bot: Bot):
    user = await get_user(callback.from_user.id)
    lang = user["language"] if user else "uz"
    is_admin = await is_admin_user(callback.from_user.id)

    channels = await get_channels()
    not_subscribed = []
    for ch in channels:
        try:
            member = await bot.get_chat_member(chat_id=ch["channel_id"], user_id=callback.from_user.id)
            if member.status in ("left", "kicked"):
                not_subscribed.append(ch)
        except Exception:
            continue

    if not not_subscribed:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(
            t(lang, "subscribe_ok"),
            reply_markup=main_menu(lang, is_admin=is_admin)
        )
    else:
        await callback.answer(t(lang, "subscribe_fail"), show_alert=True)


@router.message(F.text.in_(["🌐 Til", "🌐 Язык", "🌐 Language"]))
async def change_lang(message: Message):
    await message.answer(
        t("uz", "choose_lang"),
        reply_markup=lang_keyboard()
    )


@router.callback_query(F.data.startswith("lang_"))
async def set_lang_callback(callback: CallbackQuery, bot: Bot):
    lang = callback.data.split("_")[1]
    await set_language(callback.from_user.id, lang)

    is_admin = await is_admin_user(callback.from_user.id)
    try:
        await bot.set_my_commands(get_bot_commands(lang, is_admin=is_admin))
    except Exception as e:
        print(f"set_my_commands xatosi: {e}")

    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer(
        t(lang, "lang_set"),
        reply_markup=main_menu(lang, is_admin=is_admin)
    )


@router.callback_query(F.data == "back_main")
async def back_to_main(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    lang = user["language"] if user else "uz"
    is_admin = await is_admin_user(callback.from_user.id)
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer(
        t(lang, "main_menu"),
        reply_markup=main_menu(lang, is_admin=is_admin)
    )


@router.callback_query(F.data == "back_gifts")
async def back_to_gifts(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    lang = user["language"] if user else "uz"
    from database import get_gifts
    from keyboards import gifts_keyboard
    gifts = await get_gifts()
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer(
        t(lang, "gifts_menu"),
        reply_markup=gifts_keyboard(gifts, lang),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "back_balance")
async def back_to_balance(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    lang = user["language"] if user else "uz"
    from keyboards import balance_keyboard
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer(
        t(lang, "balance_menu", balance=user["balance"]),
        reply_markup=balance_keyboard(lang),
        parse_mode="HTML"
    )