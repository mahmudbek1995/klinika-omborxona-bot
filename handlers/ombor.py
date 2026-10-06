from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from keyboards import (
    get_main_menu, 
    get_cancel_menu, 
    get_medicine_action_keyboard, 
    get_delete_confirm_keyboard,
    get_pagination_keyboard
)
from states import SearchStates, EditStates
from config import ADMIN_IDS
from notifier import notify_admin
from datetime import datetime
import database as db

router = Router()

ITEMS_PER_PAGE = 8

async def build_medicine_card_text(med) -> str:
    is_low = med["quantity"] <= med["min_quantity"]
    status = "🚨 <b>Zaxira kam qolgan!</b>" if is_low else "✅ <b>Yetarli miqdorda</b>"

    text = (
        f"💊 <b>Dori ma'lumotlari:</b>\n\n"
        f"🏷 <b>Nomi:</b> {med['name']}\n"
        f"📦 <b>Mavjud qoldiq:</b> {med['quantity']:g} {med['unit']}\n"
        f"⚠️ <b>Minimal me'yor:</b> {med['min_quantity']:g} {med['unit']}\n"
        f"📍 <b>Joylashuvi:</b> {med['location'] or 'Ko‘rsatilmagan'}\n"
        f"⏳ <b>Yaroqlilik muddati:</b> {med['expiry_date'] or 'Ko‘rsatilmagan'}\n"
        f"📊 <b>Holati:</b> {status}\n"
        f"🕒 <b>Oxirgi o'zgarish:</b> {med['updated_at']}"
    )
    return text

@router.message(F.text == "📦 Barcha dorilar")
async def show_all_medicines(message: Message):
    if not await db.is_user_approved(message.from_user.id):
        await message.answer("⛔️ Sizga ruxsat berilmagan!")
        return

    medicines = await db.get_all_medicines()
    if not medicines:
        await message.answer(
            "📦 Omborda hozircha hech qanday dori yo'q.\n"
            "Yangi dori qo'shish uchun <b>📥 Kirim qilish</b> tugmasini bosing.",
            reply_markup=get_main_menu(),
            parse_mode="HTML"
        )
        return


    await render_medicines_page(message, medicines, page=1)

async def render_medicines_page(message_or_query, medicines, page: int = 1):
    total_items = len(medicines)
    total_pages = (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    if page < 1:
        page = 1
    if page > total_pages:
        page = total_pages

    start_idx = (page - 1) * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    page_items = medicines[start_idx:end_idx]

    buttons = []
    for med in page_items:
        is_low = med["quantity"] <= med["min_quantity"]
        icon = "⚠️" if is_low else "💊"
        buttons.append([
            InlineKeyboardButton(
                text=f"{icon} {med['name']} — {med['quantity']:g} {med['unit']}",
                callback_data=f"med_view:{med['id']}"
            )
        ])

    # Sahifalash tugmalari
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"page:{page - 1}"))
    nav_buttons.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"page:{page + 1}"))

    if nav_buttons:
        buttons.append(nav_buttons)

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    text = (
        f"📦 <b>Ombordagi dorilar ro'yxati (Jami: {total_items} xil):</b>\n"
        f"<i>Batafsil ma'lumot va amallar uchun dorini bosing 👇</i>"
    )

    if isinstance(message_or_query, Message):
        await message_or_query.answer(text, reply_markup=kb, parse_mode="HTML")
    else:
        await message_or_query.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data.startswith("page:"))
async def pagination_callback(callback: CallbackQuery):
    page = int(callback.data.split(":")[1])
    medicines = await db.get_all_medicines()
    await render_medicines_page(callback, medicines, page=page)
    await callback.answer()

@router.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery):
    await callback.answer()

@router.callback_query(F.data.startswith("med_view:"))
async def view_medicine_callback(callback: CallbackQuery):
    med_id = int(callback.data.split(":")[1])
    med = await db.get_medicine_by_id(med_id)
    if not med:
        await callback.answer("Dori topilmadi!", show_alert=True)
        return

    text = await build_medicine_card_text(med)
    kb = get_medicine_action_keyboard(med["id"])
    await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

# Qidiruv bo'limi
@router.message(F.text == "🔍 Dori qidirish")
async def search_command(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(SearchStates.query)
    await message.answer(
        "🔍 <b>Dori qidirish:</b>\n\n"
        "Qidirmoqchi bo'lgan dori nomini yoki uning bir qismini kiriting:\n"
        "<i>(Masalan: anal, para, sef, amp)</i>",
        reply_markup=get_cancel_menu(),
        parse_mode="HTML"
    )

@router.message(SearchStates.query)
async def process_search_query(message: Message, state: FSMContext):
    query = message.text.strip()
    results = await db.search_medicines(query)
    await state.clear()

    if not results:
        await message.answer(
            f"❌ <b>'{query}'</b> bo'yicha hech qanday dori topilmadi.",
            reply_markup=get_main_menu(),
            parse_mode="HTML"
        )
        return

    buttons = []
    for med in results:
        is_low = med["quantity"] <= med["min_quantity"]
        icon = "⚠️" if is_low else "💊"
        buttons.append([
            InlineKeyboardButton(
                text=f"{icon} {med['name']} — {med['quantity']:g} {med['unit']}",
                callback_data=f"med_view:{med['id']}"
            )
        ])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer(
        f"🔍 <b>Qidiruv natijalari ('{query}' bo'yicha {len(results)} ta dori topildi):</b>\n"
        f"<i>Batafsil ma'lumot olish uchun ustiga bosing:</i>",
        reply_markup=kb,
        parse_mode="HTML"
    )

# Minimal normani o'zgartirish
@router.callback_query(F.data.startswith("med_min:"))
async def edit_min_qty_callback(callback: CallbackQuery, state: FSMContext):
    med_id = int(callback.data.split(":")[1])
    med = await db.get_medicine_by_id(med_id)
    if not med:
        await callback.answer("Dori topilmadi!", show_alert=True)
        return

    await state.clear()
    await state.update_data(medicine_id=med["id"], medicine_name=med["name"], unit=med["unit"])
    await state.set_state(EditStates.new_min_quantity)

    await callback.message.answer(
        f"⚙️ <b>{med['name']}</b> uchun yangi minimal ogohlantirish me'yorini kiriting:\n"
        f"(Hozirgi me'yor: <b>{med['min_quantity']:g} {med['unit']}</b>)\n\n"
        f"Yangi sonni yozing:",
        reply_markup=get_cancel_menu(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(EditStates.new_min_quantity)
async def process_new_min_qty(message: Message, state: FSMContext):
    text = message.text.replace(",", ".").strip()
    try:
        val = float(text)
        if val < 0:
            val = 0
    except ValueError:
        await message.answer("Iltimos, musbat son kiriting:")
        return

    data = await state.get_data()
    await db.update_min_quantity(data["medicine_id"], val)
    await state.clear()

    await message.answer(
        f"✅ <b>{data['medicine_name']}</b> uchun minimal me'yor <b>{val:g} {data['unit']}</b> ga o'zgartirildi!",
        reply_markup=get_main_menu(),
        parse_mode="HTML"
    )

# Dori o'chirish (Faqat Glavniy Adminga ruxsat beriladi)
@router.callback_query(F.data.startswith("med_del:"))
async def delete_medicine_prompt(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔️ Dorini o'chirish faqat Glavniy Adminga ruxsat berilgan!", show_alert=True)
        return

    med_id = int(callback.data.split(":")[1])
    med = await db.get_medicine_by_id(med_id)
    if not med:
        await callback.answer("Dori topilmadi!", show_alert=True)
        return

    kb = get_delete_confirm_keyboard(med["id"])
    await callback.message.answer(
        f"⚠️ <b>Haqiqatan ham '{med['name']}' dorisini bazadan butunlay o'chirmoqchimisiz?</b>\n\n"
        f"<i>Ushbu amal unga tegishli barcha kirim-chiqimlar tarixini ham o'chiradi!</i>",
        reply_markup=kb,
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("confirm_del:"))
async def confirm_delete_medicine(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔️ Ruxsat berilmagan!", show_alert=True)
        return

    med_id = int(callback.data.split(":")[1])
    med = await db.get_medicine_by_id(med_id)
    med_name = med["name"] if med else "Noma'lum"

    await db.delete_medicine(med_id)
    await callback.message.edit_text(f"✅ '{med_name}' dorisi bazadan butunlay o'chirildi.")
    await callback.answer()

    # FAQAT GLAVNIY ADMINGA BILDIRISHNOMA
    await notify_admin(
        f"🚨 <b>DIQQAT: DORI BAZADAN O'CHIRILDI!</b>\n\n"
        f"💊 <b>Dori:</b> {med_name}\n"
        f"👤 <b>Kim o'chirdi:</b> {callback.from_user.full_name} (ID: <code>{callback.from_user.id}</code>)\n"
        f"🕒 <b>Vaqt:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    )

@router.callback_query(F.data == "cancel_del")
async def cancel_delete_medicine(callback: CallbackQuery):
    await callback.message.edit_text("O'chirish bekor qilindi.")
    await callback.answer()

