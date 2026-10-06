from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from keyboards import get_main_menu, get_web_inline_keyboard
from config import ADMIN_IDS, WEB_PORT
import database as db
from notifier import notify_admin

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    
    user_id = message.from_user.id
    full_name = message.from_user.full_name or "Noma'lum"
    username = message.from_user.username or ""

    user, is_new_request = await db.register_or_get_user(user_id, full_name, username)

    # 1. Agar foydalanuvchi Admin bo'lsa yoki tasdiqlangan bo'lsa
    if user["status"] == "approved" or user_id in ADMIN_IDS:
        admin_badge = " (👑 Glavniy Admin)" if user_id in ADMIN_IDS else ""
        text = (
            f"🏥 <b>Assalomu alaykum, {full_name}!{admin_badge}</b>\n\n"
            f"<b>Klinika omborxonasi tizimiga xush kelibsiz!</b>\n\n"
            f"Sizga tizimdan foydalanish uchun to'liq ruxsat berilgan.\n"
            f"🔑 Sizning Veb PIN-kodingiz: <code>{user.get('web_password', 'admin123')}</code>\n\n"
            f"🔹 <b>📥 Kirim qilish</b> — yangi partiya dorilarni qabul qilish\n"
            f"🔹 <b>📤 Chiqim qilish</b> — bo'limlarga dori chiqarish\n"
            f"🔹 <b>📦 Barcha dorilar</b> — qoldiqni real vaqtda ko'rish\n"
            f"🔹 <b>⚠️ Kam qolgan dorilar</b> — tugab borayotgan dorilar ogohlantirishi\n"
            f"🔹 <b>🏢 Bo'limlar hisoboti</b> — dori sarfi statistikasi\n"
            f"🔹 <b>🌐 Web Dashboard</b> — veb-sahifa orqali boshqarish\n"
            f"🔹 <b>📊 Excel hisobot</b> — hisobotni yuklab olish\n\n"
            f"<i>Kerakli amalni pastdagi menyudan tanlang 👇</i>"
        )
        await message.answer(text, reply_markup=get_main_menu(), parse_mode="HTML")
        return

    # 2. Agar foydalanuvchi rad etilgan bo'lsa
    if user["status"] == "rejected":
        await message.answer(
            f"⛔️ <b>Kirish rad etilgan!</b>\n\n"
            f"Hurmatli {full_name}, sizga ushbu tizimdan foydalanish uchun bosh admin tomonidan ruxsat berilmagan.",
            parse_mode="HTML"
        )
        return

    # 3. Kutilayotgan (pending) foydalanuvchi
    await message.answer(
        f"⏳ <b>Hurmatli {full_name}!</b>\n\n"
        f"Sizning Telegram ID: <code>{user_id}</code>\n"
        f"Xavfsizlik talablariga muvofiq, tizimdan foydalanish uchun <b>Bosh Admindan ruxsat (do'psuk)</b> olishingiz kerak.\n\n"
        f"✅ <i>Bosh adminga sizning nomingizdan so'rov yuborildi. Admin tasdiqlashi bilan sizga xabar beriladi.</i>",
        parse_mode="HTML"
    )

    # Glavniy adminga ruxsat so'rovini yuborish
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Ruxsat berish", callback_data=f"user_appr:{user_id}"),
            InlineKeyboardButton(text="❌ Rad etish", callback_data=f"user_rejc:{user_id}")
        ]
    ])

    admin_alert_text = (
        f"🔔 <b>YANGI XODIM KIRISH UCHUN RUXSAT (DO'PSUK) SO'RAMOQDA!</b>\n\n"
        f"👤 <b>F.I.Sh:</b> {full_name}\n"
        f"💬 <b>Username:</b> @{username or 'yo‘q'}\n"
        f"🆔 <b>Telegram ID:</b> <code>{user_id}</code>\n\n"
        f"<i>Ushbu xodimga tizimdan foydalanishga ruxsat berasizmi?</i>"
    )
    await notify_admin(admin_alert_text, reply_markup=kb)

# Admin tomonidan ruxsat berish
@router.callback_query(F.data.startswith("user_appr:"))
async def approve_user_callback(callback: CallbackQuery, bot: Bot):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Faqat Glavniy Admin tasdiqlashi mumkin!", show_alert=True)
        return

    target_id = int(callback.data.split(":")[1])
    target_user = await db.get_user_by_id(target_id)
    if not target_user:
        await callback.answer("Foydalanuvchi topilmadi!", show_alert=True)
        return

    pin = await db.approve_user(target_id)
    await callback.message.edit_text(
        f"✅ <b>XODIMGA RUXSAT BERILDI!</b>\n\n"
        f"👤 Xodim: <b>{target_user['full_name']}</b> (ID: <code>{target_id}</code>)\n"
        f"🔑 Berilgan Veb PIN-kod: <code>{pin}</code>\n"
        f"Holat: <b>Faol (Approved)</b>",
        parse_mode="HTML"
    )
    await callback.answer("Ruxsat berildi!", show_alert=True)

    # Xodimning o'ziga bildirishnoma jo'natish
    try:
        user_msg = (
            f"🎉 <b>XUSHXABAR!</b>\n\n"
            f"Bosh admin sizga <b>Klinika Omborxonasi</b> tizimidan foydalanish uchun ruxsat berdi!\n\n"
            f"🔑 <b>Veb-saytga kirish PIN-kodingiz:</b> <code>{pin}</code>\n\n"
            f"<i>Endi pastdagi menyu orqali botdan foydalanishingiz mumkin 👇</i>"
        )
        await bot.send_message(chat_id=target_id, text=user_msg, reply_markup=get_main_menu(), parse_mode="HTML")
    except Exception as e:
        pass

# Admin tomonidan rad etish
@router.callback_query(F.data.startswith("user_rejc:"))
async def reject_user_callback(callback: CallbackQuery, bot: Bot):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Faqat Glavniy Admin bajara oladi!", show_alert=True)
        return

    target_id = int(callback.data.split(":")[1])
    target_user = await db.get_user_by_id(target_id)
    await db.reject_user(target_id)

    name = target_user['full_name'] if target_user else str(target_id)
    await callback.message.edit_text(
        f"❌ <b>Xodim so'rovi rad etildi:</b> {name}",
        parse_mode="HTML"
    )
    await callback.answer("Rad etildi!")

    try:
        await bot.send_message(
            chat_id=target_id,
            text="⛔️ Sizning tizimga kirish so'rovingiz bosh admin tomonidan rad etildi."
        )
    except Exception:
        pass

@router.message(F.text == "🌐 Web Havola")
async def show_web_link(message: Message):
    if not await db.is_user_approved(message.from_user.id):
        await message.answer("⛔️ Sizga ruxsat berilmagan!")
        return

    user = await db.get_user_by_id(message.from_user.id)
    pin = user.get("web_password", "admin123") if user else "admin123"

    text = (
        f"🌐 <b>Klinika Omborxonasi Web Dashboard:</b>\n\n"
        f"🔗 <b>Brauzer orqali kirish manzili:</b>\n"
        f"👉 <code>http://localhost:{WEB_PORT}</code>\n\n"
        f"🔐 <b>Vebga kirish ma'lumotlaringiz:</b>\n"
        f"👤 Login (ID): <code>{message.from_user.id}</code>\n"
        f"🔑 Parol (PIN): <code>{pin}</code>\n\n"
        f"💡 <i>Ushbu havolani brauzerda ochib, yuqoridagi login va parolingiz bilan tizimga kiring!</i>"
    )
    inline_kb = get_web_inline_keyboard()
    await message.answer(text, reply_markup=inline_kb, parse_mode="HTML")

@router.message(F.text == "❌ Bekor qilish")
async def cancel_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Amal bekor qilindi. Asosiy menyudasiz.",
        reply_markup=get_main_menu()
    )

@router.message(F.text == "🏢 Bo'limlar hisoboti")
async def show_department_reports(message: Message):
    if not await db.is_user_approved(message.from_user.id):
        await message.answer("⛔️ Sizga ruxsat berilmagan!")
        return

    dept_stats = await db.get_department_stats()
    if not dept_stats:
        await message.answer(
            "🏢 Hozircha bo'limlarga dori chiqimi qilinmagan.",
            reply_markup=get_main_menu()
        )
        return

    text = "🏢 <b>Bo'limlar bo'yicha berilgan dorilar hisoboti:</b>\n\n"
    total_all_qty = 0
    for idx, row in enumerate(dept_stats, 1):
        dept_name = row["department"]
        tx_count = row["tx_count"]
        total_qty = row["total_qty"] or 0
        total_all_qty += total_qty
        text += (
            f"<b>{idx}. {dept_name}</b>\n"
            f"   🔹 Chiqimlar soni: <b>{tx_count} marta</b>\n"
            f"   📦 Jami olingan miqdor: <b>{total_qty:g} ta</b>\n\n"
        )

    text += f"━━━━━━━━━━━━━━━━━━━━\n"
    text += f"📊 <b>Jami barcha bo'limlarga berilgan:</b> <b>{total_all_qty:g} ta</b>"

    await message.answer(text, reply_markup=get_main_menu(), parse_mode="HTML")

@router.message(F.text == "📈 Statistika")
async def show_statistics(message: Message):
    if not await db.is_user_approved(message.from_user.id):
        await message.answer("⛔️ Sizga ruxsat berilmagan!")
        return

    stats = await db.get_statistics()
    text = (
        f"📊 <b>Klinika omborxonasi statistikasi:</b>\n\n"
        f"📦 Jami dori turlari: <b>{stats['total_items']} xil</b>\n"
        f"🔢 Ombordagi umumiy qoldiq: <b>{stats['total_qty']:g} ta</b>\n"
        f"⚠️ Kam qolgan dorilar: <b>{stats['low_count']} xil</b>\n"
        f"👥 Tasdiqlangan xodimlar: <b>{stats['total_users']} nafar</b>\n\n"
        f"📅 <b>Bugungi harakatlar:</b>\n"
        f"📥 Bugungi kirimlar: <b>{stats['today_kirim']} marta</b>\n"
        f"📤 Bugungi chiqimlar: <b>{stats['today_chiqim']} marta</b>\n"
    )
    await message.answer(text, parse_mode="HTML")

@router.message(F.text == "ℹ️ Qo'llanma")
async def show_help(message: Message):
    text = (
        f"📖 <b>Bot va Web Dashboard bo'yicha qo'llanma:</b>\n\n"
        f"1️⃣ <b>📥 Kirim qilish:</b>\n"
        f"Yangi dorini qo'shish yoki mavjud dorining sonini ko'paytirish.\n\n"
        f"2️⃣ <b>📤 Chiqim qilish:</b>\n"
        f"Bo'limlarga dori berish (Xudud, LOR, Ortopediya, Muolajaxonasi, Laboratoriya, Operatsion).\n\n"
        f"3️⃣ <b>📦 Barcha dorilar:</b>\n"
        f"Ombordagi barcha dorilar va ularning aniq qoldig'i.\n\n"
        f"4️⃣ <b>⚠️ Kam qolgan dorilar:</b>\n"
        f"Tugab qolayotgan dorilar ro'yxati va ularning yonida aniq qoldiq soni.\n\n"
        f"5️⃣ <b>🏢 Bo'limlar hisoboti:</b>\n"
        f"Har bir bo'limning dori iste'moli statistikasi.\n\n"
        f"6️⃣ <b>🌐 Web Dashboard:</b>\n"
        f"Brauzerda ochib, login va PIN bilan kirish.\n\n"
        f"7️⃣ <b>📊 Excel hisobot:</b>\n"
        f"To'liq hisobotni Excel formatida bitta tugma bilan yuklab olish."
    )
    await message.answer(text, parse_mode="HTML")
