from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from states import KirimStates
from keyboards import get_main_menu, get_cancel_menu, get_units_keyboard, get_category_selection_keyboard
import database as db

from notifier import notify_admin
from datetime import datetime

router = Router()

@router.message(F.text == "📥 Kirim qilish")
async def start_kirim(message: Message, state: FSMContext):
    if not await db.is_user_approved(message.from_user.id):
        await message.answer("⛔️ Sizga tizimdan foydalanish uchun hali ruxsat berilmagan!")
        return

    await state.clear()
    await state.set_state(KirimStates.search_or_new)
    await message.answer(
        "📥 <b>Omborga kirim qilish:</b>\n\n"
        "Mahsulot, dori yoki sarf materiali nomini kiriting (masalan: <i>Analgin, Spirt, Shprits, Qo'lqop</i>):\n\n"
        "<i>(Agar tovar bazada mavjud bo'lsa qoldiq oshiriladi, bo'lmasa yangi sifatida ro'yxatga olinadi)</i>",
        reply_markup=get_cancel_menu(),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("med_in:"))
async def quick_kirim_callback(callback: CallbackQuery, state: FSMContext):
    if not await db.is_user_approved(callback.from_user.id):
        await callback.answer("⛔️ Sizga ruxsat berilmagan!", show_alert=True)
        return

    med_id = int(callback.data.split(":")[1])
    med = await db.get_medicine_by_id(med_id)
    if not med:
        await callback.answer("Dori topilmadi!", show_alert=True)
        return

    await state.clear()
    await state.update_data(
        medicine_id=med["id"],
        medicine_name=med["name"],
        unit=med["unit"],
        is_existing=True
    )
    await state.set_state(KirimStates.quantity)

    await callback.message.answer(
        f"📥 <b>{med['name']}</b> uchun kirim:\n\n"
        f"📦 Hozirgi qoldiq: <b>{med['quantity']:g} {med['unit']}</b>\n\n"
        f"Qancha miqdorda kirim qilinmoqda? (Raqam yozing, masalan: 50 yoki 100):",
        reply_markup=get_cancel_menu(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(KirimStates.search_or_new)
async def process_medicine_name(message: Message, state: FSMContext):
    med_name = message.text.strip()
    if not med_name:
        await message.answer("Iltimos, to'g'ri dori nomini yozing:")
        return

    # Bazada bormi tekshiramiz
    existing = await db.get_medicine_by_name(med_name)
    if existing:
        await state.update_data(
            medicine_id=existing["id"],
            medicine_name=existing["name"],
            unit=existing["unit"],
            is_existing=True
        )
        await state.set_state(KirimStates.quantity)
        await message.answer(
            f"✅ <b>Dori bazada mavjud:</b> {existing['name']}\n\n"
            f"📦 Hozirgi qoldiq: <b>{existing['quantity']:g} {existing['unit']}</b>\n"
            f"📍 Joylashuvi: {existing['location'] or 'Ko‘rsatilmagan'}\n\n"
            f"Qancha miqdor kirim qilmoqchisiz? (Raqam kiriting):",
            reply_markup=get_cancel_menu(),
            parse_mode="HTML"
        )
    else:
        # Yangi tovar kiritish
        await state.update_data(
            medicine_name=med_name,
            is_existing=False
        )
        await state.set_state(KirimStates.category)
        await message.answer(
            f"🆕 <b>Yangi mahsulot qo'shilmoqda:</b> {med_name}\n\n"
            f"Ushbu mahsulot qaysi toifaga (bo'limga) tegishli?",
            reply_markup=get_category_selection_keyboard(prefix="kirim_cat"),
            parse_mode="HTML"
        )

@router.callback_query(KirimStates.category, F.data.startswith("kirim_cat:"))
async def process_kirim_category_cb(callback: CallbackQuery, state: FSMContext):
    cat = callback.data.split(":")[1]
    cat_names = {"dori": "💊 Dori-darmon", "operatsion": "🩺 Operatsion rasxod", "xojalik": "🧹 Xo'jalik moli"}
    await state.update_data(category=cat)
    await state.set_state(KirimStates.unit)
    await callback.message.answer(
        f"Toifa: <b>{cat_names.get(cat, cat)}</b>\n\n"
        f"O'lchov birligini tanlang yoki qo'lda yozing:",
        reply_markup=get_units_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(KirimStates.unit, F.data.startswith("unit:"))
async def process_unit_callback(callback: CallbackQuery, state: FSMContext):
    unit = callback.data.split(":")[1]
    if unit == "boshqa":
        await callback.message.answer(
            "Iltimos, o'lchov birligini yozma ravishda kiriting (masalan: flakon, tyubik, upakovka):",
            reply_markup=get_cancel_menu()
        )
        await callback.answer()
        return

    await state.update_data(unit=unit)
    await state.set_state(KirimStates.quantity)
    data = await state.get_data()
    await callback.message.answer(
        f"Tanlangan birlik: <b>{unit}</b>\n\n"
        f"Kirim miqdorini kiriting (masalan: 100):",
        reply_markup=get_cancel_menu(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(KirimStates.unit)
async def process_unit_text(message: Message, state: FSMContext):
    unit = message.text.strip().lower()
    await state.update_data(unit=unit)
    await state.set_state(KirimStates.quantity)
    await message.answer(
        f"Tanlangan birlik: <b>{unit}</b>\n\n"
        f"Kirim miqdorini kiriting (masalan: 100):",
        reply_markup=get_cancel_menu(),
        parse_mode="HTML"
    )

@router.message(KirimStates.quantity)
async def process_kirim_quantity(message: Message, state: FSMContext):
    text = message.text.replace(",", ".").strip()
    try:
        qty = float(text)
        if qty <= 0:
            await message.answer("Miqdor 0 dan katta bo'lishi kerak! Qaytadan kiriting:")
            return
    except ValueError:
        await message.answer("Iltimos, faqat raqam kiriting (masalan: 20 yoki 50.5):")
        return

    await state.update_data(quantity=qty)
    data = await state.get_data()

    if data.get("is_existing"):
        # Mavjud dori bo'lsa to'g'ridan-to'g'ri izoh so'raymiz
        await state.set_state(KirimStates.comment)
        await message.answer(
            f"Kirim miqdori: <b>{qty:g} {data['unit']}</b>\n\n"
            f"Yetkazib beruvchi yoki izohni kiriting (yoki 'yo'q' deb yozing):",
            reply_markup=get_cancel_menu(),
            parse_mode="HTML"
        )
    else:
        # Yangi dori bo'lsa minimal normani so'raymiz
        await state.set_state(KirimStates.min_quantity)
        skip_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Standart (10 dona)", callback_data="min_def:10")]
        ])
        await message.answer(
            f"Ushbu dori omborda qanchadan kam qolsa bot ogohlantirishi kerak?\n"
            f"(Minimal me'yorni kiriting, masalan: 10 yoki 20):",
            reply_markup=skip_kb
        )

@router.callback_query(KirimStates.min_quantity, F.data.startswith("min_def:"))
async def process_default_min_qty(callback: CallbackQuery, state: FSMContext):
    val = float(callback.data.split(":")[1])
    await state.update_data(min_quantity=val)
    await state.set_state(KirimStates.location)
    skip_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="O'tkazib yuborish ➡️", callback_data="skip:location")]
    ])
    await callback.message.answer(
        f"Minimal me'yor: <b>{val:g}</b> deb belgilandi.\n\n"
        f"Dorining ombordagi joylashuvi (shkaf, polka, xona)ni kiriting (ixtiyoriy):",
        reply_markup=skip_kb,
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(KirimStates.min_quantity)
async def process_min_quantity(message: Message, state: FSMContext):
    text = message.text.replace(",", ".").strip()
    try:
        min_qty = float(text)
        if min_qty < 0:
            min_qty = 0
    except ValueError:
        await message.answer("Iltimos, son kiriting (masalan: 10):")
        return

    await state.update_data(min_quantity=min_qty)
    await state.set_state(KirimStates.location)
    skip_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="O'tkazib yuborish ➡️", callback_data="skip:location")]
    ])
    await message.answer(
        f"Minimal me'yor: <b>{min_qty:g}</b> deb belgilandi.\n\n"
        f"Dorining ombordagi joylashuvi (shkaf, polka, xona)ni kiriting (ixtiyoriy):",
        reply_markup=skip_kb,
        parse_mode="HTML"
    )

@router.callback_query(KirimStates.location, F.data == "skip:location")
async def skip_location_cb(callback: CallbackQuery, state: FSMContext):
    await state.update_data(location="")
    await state.set_state(KirimStates.expiry)
    skip_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="O'tkazib yuborish ➡️", callback_data="skip:expiry")]
    ])
    await callback.message.answer(
        "Yaroqlilik muddatini kiriting (masalan: <i>12.2026</i> yoki <i>2026-12</i>) (ixtiyoriy):",
        reply_markup=skip_kb,
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(KirimStates.location)
async def process_location(message: Message, state: FSMContext):
    loc = message.text.strip()
    await state.update_data(location=loc)
    await state.set_state(KirimStates.expiry)
    skip_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="O'tkazib yuborish ➡️", callback_data="skip:expiry")]
    ])
    await message.answer(
        "Yaroqlilik muddatini kiriting (masalan: <i>12.2026</i>) (ixtiyoriy):",
        reply_markup=skip_kb,
        parse_mode="HTML"
    )

@router.callback_query(KirimStates.expiry, F.data == "skip:expiry")
async def skip_expiry_cb(callback: CallbackQuery, state: FSMContext):
    await state.update_data(expiry="")
    await state.set_state(KirimStates.comment)
    await callback.message.answer(
        "Yetkazib beruvchi / Fatura / Izohni kiriting (yoki 'yo'q' deb yozing):",
        reply_markup=get_cancel_menu()
    )
    await callback.answer()

@router.message(KirimStates.expiry)
async def process_expiry(message: Message, state: FSMContext):
    exp = message.text.strip()
    await state.update_data(expiry=exp)
    await state.set_state(KirimStates.comment)
    await message.answer(
        "Yetkazib beruvchi / Fatura / Izohni kiriting (yoki 'yo'q' deb yozing):",
        reply_markup=get_cancel_menu()
    )

@router.message(KirimStates.comment)
async def process_kirim_finish(message: Message, state: FSMContext):
    comment = message.text.strip()
    if comment.lower() in ("yo'q", "yoq", "none", "-"):
        comment = ""

    data = await state.get_data()
    user_id = message.from_user.id
    user_name = message.from_user.full_name or message.from_user.username or "Noma'lum"

    if data.get("is_existing"):
        # Mavjud dori qoldig'ini oshirish
        success, new_qty = await db.record_kirim(
            medicine_id=data["medicine_id"],
            quantity=data["quantity"],
            comment=comment,
            user_id=user_id,
            user_name=user_name
        )
        await state.clear()
        if success:
            await message.answer(
                f"✅ <b>Kirim muvaffaqiyatli qabul qilindi!</b>\n\n"
                f"💊 Dori: <b>{data['medicine_name']}</b>\n"
                f"📥 Qo'shildi: <b>+{data['quantity']:g} {data['unit']}</b>\n"
                f"📦 Yangi umumiy qoldiq: <b>{new_qty:g} {data['unit']}</b>\n"
                f"📝 Izoh: {comment or 'Kiritilmagan'}",
                reply_markup=get_main_menu(),
                parse_mode="HTML"
            )

            # FAQAT GLAVNIY ADMINGA SHAXSIY BILDIRISHNOMA
            await notify_admin(
                f"🔔 <b>OMBORDAGI OPERATSIYA: KIRIM</b>\n\n"
                f"💊 <b>Dori:</b> {data['medicine_name']}\n"
                f"📥 <b>Kiritildi:</b> +{data['quantity']:g} {data['unit']}\n"
                f"📦 <b>Yangi qoldiq:</b> {new_qty:g} {data['unit']}\n"
                f"👤 <b>Kim bajardi:</b> {user_name} (ID: <code>{user_id}</code>)\n"
                f"📝 <b>Izoh / Yetkazib beruvchi:</b> {comment or 'Yo‘q'}\n"
                f"🕒 <b>Vaqt:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            )
        else:
            await message.answer(
                "❌ Xatolik yuz berdi. Dori bazada topilmadi.",
                reply_markup=get_main_menu()
            )
    else:
        # Yangi tovar yaratish
        category = data.get("category", "dori")
        med_id = await db.add_new_medicine(
            name=data["medicine_name"],
            unit=data["unit"],
            initial_qty=data["quantity"],
            min_qty=data.get("min_quantity", 10),
            location=data.get("location", ""),
            expiry_date=data.get("expiry", ""),
            category=category,
            user_id=user_id,
            user_name=user_name
        )
        await state.clear()
        cat_names = {"dori": "💊 Dori-darmon", "operatsion": "🩺 Operatsion rasxod", "xojalik": "🧹 Xo'jalik moli"}
        cat_str = cat_names.get(category, category)

        await message.answer(
            f"🎉 <b>Yangi mahsulot muvaffaqiyatli ro'yxatdan o'tkazildi!</b>\n\n"
            f"🏷 Mahsulot nomi: <b>{data['medicine_name']}</b>\n"
            f"📂 Bo'lim / toifa: <b>{cat_str}</b>\n"
            f"📦 Boshlang'ich qoldiq: <b>{data['quantity']:g} {data['unit']}</b>\n"
            f"⚠️ Minimal me'yor: <b>{data.get('min_quantity', 10):g} {data['unit']}</b>\n"
            f"📍 Joylashuv: {data.get('location') or 'Ko‘rsatilmagan'}\n"
            f"⏳ Yaroqlilik: {data.get('expiry') or 'Ko‘rsatilmagan'}\n"
            f"📝 Izoh: {comment or 'Kiritilmagan'}",
            reply_markup=get_main_menu(),
            parse_mode="HTML"
        )

        # FAQAT GLAVNIY ADMINGA SHAXSIY BILDIRISHNOMA
        await notify_admin(
            f"🆕 <b>OMBORDAGI OPERATSIYA: YANGI MAHSULOT QO'SHILDI!</b>\n\n"
            f"🏷 <b>Nomi:</b> {data['medicine_name']}\n"
            f"📂 <b>Toifasi:</b> {cat_str}\n"
            f"📦 <b>Boshlang'ich qoldiq:</b> {data['quantity']:g} {data['unit']}\n"
            f"⚠️ <b>Min. norma:</b> {data.get('min_quantity', 10):g} {data['unit']}\n"
            f"📍 <b>Joylashuv:</b> {data.get('location') or 'Ko‘rsatilmagan'}\n"
            f"👤 <b>Kim qo'shdi:</b> {user_name} (ID: <code>{user_id}</code>)\n"
            f"📝 <b>Izoh:</b> {comment or 'Yo‘q'}\n"
            f"🕒 <b>Vaqt:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )

