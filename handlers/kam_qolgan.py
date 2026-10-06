from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import database as db

router = Router()

@router.message(F.text.in_(["⚠️ Kam qolgan dorilar", "⚠️ Kam qolgan mollar"]))
async def show_low_stock(message: Message):
    low_medicines = await db.get_low_stock_medicines()

    if not low_medicines:
        await message.answer(
            "🎉 <b>Ajoyib! Omborda barcha tovar va dorilar yetarli miqdorda!</b>\n\n"
            "Minimal me'yordan kam qolgan tovarlar mavjud emas.",
            parse_mode="HTML"
        )
        return

    # Qoldig'i 0 bo'lganlar va kam qolganlarga ajratamiz
    zero_stock = [m for m in low_medicines if m["quantity"] <= 0]
    low_stock = [m for m in low_medicines if m["quantity"] > 0]

    text = (
        f"🚨 <b>KAM QOLGAN DORILAR RO'YXATI (Jami: {len(low_medicines)} xil):</b>\n"
        f"<i>Dorilar nomi va hozirgi qoldiq (soni) ko'rsatilgan:</i>\n\n"
    )

    item_idx = 1
    if zero_stock:
        text += f"❌ <b>MUTLAQO TUGAGAN DORILAR (0 QOLDIQ):</b>\n"
        for med in zero_stock:
            text += (
                f"<b>{item_idx}. {med['name']}</b>\n"
                f"   👉 <b>Qoldiq: 0 {med['unit']}</b> (Min. norma: {med['min_quantity']:g} {med['unit']})\n\n"
            )
            item_idx += 1

    if low_stock:
        text += f"⚠️ <b>ZAXIRASI KAM QOLGAN DORILAR:</b>\n"
        for med in low_stock:
            deficiency = max(0, med["min_quantity"] - med["quantity"])
            def_text = f", yetishmaydi: {deficiency:g}" if deficiency > 0 else ""
            text += (
                f"<b>{item_idx}. {med['name']}</b>\n"
                f"   👉 <b>Qoldiq: {med['quantity']:g} {med['unit']}</b> (Min. norma: {med['min_quantity']:g} {med['unit']}{def_text})\n\n"
            )
            item_idx += 1

    text += "<i>Doriga tezkor kirim qilish uchun quyidagi tugmalardan birini bosing 👇</i>"

    # Tugmalar: har bir tugmada dori nomi va qoldiq soni aniq ko'rinsin
    buttons = []
    # 2 tadan qilib joylashtiramiz
    row = []
    for med in low_medicines:
        btn_text = f"📥 {med['name'][:18]} ({med['quantity']:g} {med['unit']})"
        row.append(InlineKeyboardButton(text=btn_text, callback_data=f"med_in:{med['id']}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    # Agar xabar 4096 belgidan uzun bo'lsa, xatolik bermasligi uchun qismlarga bo'lamiz
    if len(text) > 4000:
        parts = []
        lines = text.split("\n\n")
        curr_part = ""
        for line in lines:
            if len(curr_part) + len(line) + 2 > 3800:
                parts.append(curr_part)
                curr_part = line + "\n\n"
            else:
                curr_part += line + "\n\n"
        if curr_part:
            parts.append(curr_part)

        for i, part in enumerate(parts):
            if i == len(parts) - 1:
                await message.answer(part, reply_markup=kb, parse_mode="HTML")
            else:
                await message.answer(part, parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=kb, parse_mode="HTML")
