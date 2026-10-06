from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from states import ChiqimStates
from keyboards import get_main_menu, get_cancel_menu, get_departments_keyboard
import database as db

from notifier import notify_admin
from datetime import datetime

router = Router()

@router.message(F.text == "📤 Chiqim qilish")
async def start_chiqim(message: Message, state: FSMContext):
    if not await db.is_user_approved(message.from_user.id):
        await message.answer("⛔️ Sizga tizimdan foydalanish uchun hali ruxsat berilmagan!")
        return

    await state.clear()
    await state.set_state(ChiqimStates.search_or_select)
    await message.answer(
        "📤 <b>Chiqim qilish:</b>\n\n"
        "Chiqim qilinadigan dori, operatsion rasxodnik yoki xo'jalik moli nomini yozing (masalan: <i>Димедрол, Шприц, Спирт, Перчатки</i>):",
        reply_markup=get_cancel_menu(),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("med_out:"))
async def quick_chiqim_callback(callback: CallbackQuery, state: FSMContext):
    if not await db.is_user_approved(callback.from_user.id):
        await callback.answer("⛔️ Sizga ruxsat berilmagan!", show_alert=True)
        return

    med_id = int(callback.data.split(":")[1])
    med = await db.get_medicine_by_id(med_id)
    if not med:
        await callback.answer("Dori topilmadi!", show_alert=True)
        return

    if med["quantity"] <= 0:
        await callback.answer("❌ Bu doridan omborda qolmagan (qoldiq: 0)!", show_alert=True)
        return

    await state.clear()
    await state.update_data(
        medicine_id=med["id"],
        medicine_name=med["name"],
        unit=med["unit"],
        current_quantity=med["quantity"],
        min_quantity=med["min_quantity"]
    )
    await state.set_state(ChiqimStates.quantity)

    await callback.message.answer(
        f"📤 <b>{med['name']}</b> uchun chiqim:\n\n"
        f"📦 Ombordagi mavjud qoldiq: <b>{med['quantity']:g} {med['unit']}</b>\n\n"
        f"Qancha miqdorda chiqarilmoqda? (Raqam kiriting):",
        reply_markup=get_cancel_menu(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(ChiqimStates.search_or_select)
async def process_chiqim_search(message: Message, state: FSMContext):
    query = message.text.strip()
    if not query:
        await message.answer("Iltimos, dori nomini yozing:")
        return

    results = await db.search_medicines(query)
    if not results:
        await message.answer(
            f"❌ <b>'{query}'</b> bo'yicha bazada hech qanday dori topilmadi.\n"
            f"Iltimos, nomini tekshirib qaytadan kiriting:",
            reply_markup=get_cancel_menu(),
            parse_mode="HTML"
        )
        return

    if len(results) == 1:
        med = results[0]
        if med["quantity"] <= 0:
            await message.answer(
                f"❌ <b>{med['name']}</b> dorisining qoldig'i 0 ga teng! Chiqim qilib bo'lmaydi.",
                reply_markup=get_main_menu(),
                parse_mode="HTML"
            )
            await state.clear()
            return

        await state.update_data(
            medicine_id=med["id"],
            medicine_name=med["name"],
            unit=med["unit"],
            current_quantity=med["quantity"],
            min_quantity=med["min_quantity"]
        )
        await state.set_state(ChiqimStates.quantity)
        await message.answer(
            f"💊 Dori: <b>{med['name']}</b>\n"
            f"📦 Mavjud qoldiq: <b>{med['quantity']:g} {med['unit']}</b>\n\n"
            f"Chiqim miqdorini kiriting (raqam yozing):",
            reply_markup=get_cancel_menu(),
            parse_mode="HTML"
        )
    else:
        buttons = []
        for m in results[:10]:
            buttons.append([
                InlineKeyboardButton(
                    text=f"💊 {m['name']} ({m['quantity']:g} {m['unit']})",
                    callback_data=f"select_out:{m['id']}"
                )
            ])
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        await message.answer(
            f"🔍 <b>'{query}'</b> bo'yicha topilgan dorilar:\n"
            f"Chiqim qilmoqchi bo'lgan dorini tanlang 👇",
            reply_markup=kb,
            parse_mode="HTML"
        )

@router.callback_query(F.data.startswith("select_out:"))
async def select_chiqim_medicine(callback: CallbackQuery, state: FSMContext):
    med_id = int(callback.data.split(":")[1])
    med = await db.get_medicine_by_id(med_id)
    if not med:
        await callback.answer("Dori topilmadi!", show_alert=True)
        return

    if med["quantity"] <= 0:
        await callback.answer("❌ Bu dori omborda qolmagan (0 dona)!", show_alert=True)
        return

    await state.update_data(
        medicine_id=med["id"],
        medicine_name=med["name"],
        unit=med["unit"],
        current_quantity=med["quantity"],
        min_quantity=med["min_quantity"]
    )
    await state.set_state(ChiqimStates.quantity)

    await callback.message.answer(
        f"💊 Tanlandi: <b>{med['name']}</b>\n"
        f"📦 Mavjud qoldiq: <b>{med['quantity']:g} {med['unit']}</b>\n\n"
        f"Chiqim miqdorini kiriting (raqam yozing):",
        reply_markup=get_cancel_menu(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(ChiqimStates.quantity)
async def process_chiqim_quantity(message: Message, state: FSMContext):
    text = message.text.replace(",", ".").strip()
    try:
        qty = float(text)
        if qty <= 0:
            await message.answer("Miqdor 0 dan katta bo'lishi kerak! Qaytadan kiriting:")
            return
    except ValueError:
        await message.answer("Iltimos, son kiriting (masalan: 10):")
        return

    data = await state.get_data()
    current_qty = data["current_quantity"]
    unit = data["unit"]

    if qty > current_qty:
        await message.answer(
            f"❌ <b>Yetarli qoldiq yo'q!</b>\n\n"
            f"Siz so'ragan miqdor: <b>{qty:g} {unit}</b>\n"
            f"Biroq omborda bor: <b>{current_qty:g} {unit}</b>\n\n"
            f"Iltimos, mavjud miqdordan oshmagan son kiriting:",
            parse_mode="HTML"
        )
        return

    await state.update_data(quantity=qty)
    await state.set_state(ChiqimStates.choose_department)

    await message.answer(
        f"💊 Dori: <b>{data['medicine_name']}</b>\n"
        f"📤 Chiqim miqdori: <b>{qty:g} {unit}</b>\n\n"
        f"🏢 <b>Ushbu dori qaysi bo'limga berilmoqda?</b>\n"
        f"<i>Kerakli bo'limni tanlang 👇</i>",
        reply_markup=get_departments_keyboard(),
        parse_mode="HTML"
    )

@router.callback_query(ChiqimStates.choose_department, F.data.startswith("dept:"))
async def process_department_choice(callback: CallbackQuery, state: FSMContext):
    dept = callback.data.split(":", 1)[1]
    
    if dept == "other":
        await state.set_state(ChiqimStates.custom_department)
        await callback.message.answer(
            "Iltimos, bo'lim nomini yozma ravishda kiriting:",
            reply_markup=get_cancel_menu()
        )
        await callback.answer()
        return

    await state.update_data(department=dept)
    await ask_for_comment_or_finish(callback.message, state, dept)
    await callback.answer()

@router.message(ChiqimStates.custom_department)
async def process_custom_department(message: Message, state: FSMContext):
    dept = message.text.strip()
    if not dept:
        await message.answer("Iltimos, bo'lim nomini kiriting:")
        return

    await state.update_data(department=dept)
    await ask_for_comment_or_finish(message, state, dept)

async def ask_for_comment_or_finish(message: Message, state: FSMContext, department: str):
    await state.set_state(ChiqimStates.comment)
    
    skip_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚡️ Tezkor yakunlash (izohsiz)", callback_data="finish_chiqim_no_comment")]
    ])

    await message.answer(
        f"🏢 Tanlangan bo'lim: <b>{department}</b>\n\n"
        f"Qabul qilib olgan xodim (shifokor/hamshira F.I.Sh) yoki qo'shimcha izohni yozing:\n"
        f"<i>(Agar izoh kerak bo'lmasa, pastdagi 'Tezkor yakunlash' tugmasini bosing)</i>",
        reply_markup=skip_kb,
        parse_mode="HTML"
    )

@router.callback_query(ChiqimStates.comment, F.data == "finish_chiqim_no_comment")
async def finish_chiqim_no_comment_cb(callback: CallbackQuery, state: FSMContext):
    await execute_chiqim(callback.message, state, comment="", from_user=callback.from_user)
    await callback.answer()

@router.message(ChiqimStates.comment)
async def finish_chiqim_with_comment(message: Message, state: FSMContext):
    comment = message.text.strip()
    if comment.lower() in ("yo'q", "yoq", "none", "-"):
        comment = ""
    await execute_chiqim(message, state, comment=comment, from_user=message.from_user)

async def execute_chiqim(message: Message, state: FSMContext, comment: str, from_user):
    data = await state.get_data()
    user_id = from_user.id
    user_name = from_user.full_name or from_user.username or "Xodim"
    department = data.get("department", "Ko'rsatilmagan")

    success, new_qty, msg, is_low = await db.record_chiqim(
        medicine_id=data["medicine_id"],
        quantity=data["quantity"],
        department=department,
        comment=comment,
        user_id=user_id,
        user_name=user_name
    )

    await state.clear()

    if not success:
        await message.answer(f"❌ Xatolik: {msg}", reply_markup=get_main_menu())
        return

    result_text = (
        f"✅ <b>Chiqim muvaffaqiyatli amalga oshirildi!</b>\n\n"
        f"💊 Dori nomi: <b>{data['medicine_name']}</b>\n"
        f"📤 Chiqarildi: <b>-{data['quantity']:g} {data['unit']}</b>\n"
        f"🏢 Bo'lim: <b>{department}</b>\n"
        f"👤 Mas'ul xodim: <b>{user_name}</b>\n"
    )

    if comment:
        result_text += f"📝 Qabul qiluvchi / Izoh: <b>{comment}</b>\n"

    result_text += f"📦 Ombordagi yangi qoldiq: <b>{new_qty:g} {data['unit']}</b>\n"

    # Kam qolgan dori haqida ogohlantirish
    if is_low:
        result_text += (
            f"\n🚨 <b>DIQQAT! DORI KAM QOLDI!</b>\n"
            f"⚠️ Ushbu dorining qoldig'i belgilangan minimal me'yordan ({data['min_quantity']:g} {data['unit']}) kamayib ketdi!\n"
            f"Iltimos, zaxirani to'ldirish uchun yangi partiya buyurtma qiling!"
        )

    await message.answer(result_text, reply_markup=get_main_menu(), parse_mode="HTML")

    # FAQAT VA FAQAT GLAVNIY ADMINGA SHAXSIY BILDIRISHNOMA
    await notify_admin(
        f"🔔 <b>OMBORDAGI OPERATSIYA: CHIQIM</b>\n\n"
        f"💊 <b>Dori:</b> {data['medicine_name']}\n"
        f"📤 <b>Chiqarildi:</b> -{data['quantity']:g} {data['unit']}\n"
        f"🏢 <b>Bo'lim:</b> {department}\n"
        f"📦 <b>Yangi qoldiq:</b> {new_qty:g} {data['unit']}\n"
        f"👤 <b>Kim chiqardi:</b> {user_name} (ID: <code>{user_id}</code>)\n"
        f"📝 <b>Qabul qiluvchi / Izoh:</b> {comment or 'Yo‘q'}\n"
        f"🕒 <b>Vaqt:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        + (f"\n\n🚨 <b>DIQQAT:</b> Ushbu dori omborda kam qoldi!" if is_low else "")
    )

