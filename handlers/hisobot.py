import os
from aiogram import Router, F
from aiogram.types import Message, FSInputFile
from excel_export import generate_stock_excel
from datetime import datetime

router = Router()

@router.message(F.text == "📊 Excel hisobot")
async def send_excel_report(message: Message):
    wait_msg = await message.answer("⏳ Excel hisobot tayyorlanmoqda, iltimos kuting...")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ombor_hisoboti_{timestamp}.xlsx"

    try:
        filepath = await generate_stock_excel(output_filename=filename)
        file_to_send = FSInputFile(filepath, filename=f"Klinika_Ombor_Hisoboti_{datetime.now().strftime('%d_%m_%Y')}.xlsx")

        caption = (
            f"📊 <b>Klinika omborxonasi hisoboti tayyor!</b>\n\n"
            f"📅 Sana: <b>{datetime.now().strftime('%d.%m.%Y %H:%M')}</b>\n"
            f"Fayl ichida:\n"
            f"1️⃣ <b>Dorilar qoldig'i</b> (Mavjud soni, minimal me'yor, joylashuvi, holati)\n"
            f"2️⃣ <b>Harakatlar jurnali</b> (Oxirgi kirim va chiqimlar tarixi, mas'ul xodimlar)"
        )

        await message.answer_document(
            document=file_to_send,
            caption=caption,
            parse_mode="HTML"
        )
    except Exception as e:
        await message.answer(f"❌ Hisobot tayyorlashda xatolik yuz berdi: {str(e)}")
    finally:
        await wait_msg.delete()
        if os.path.exists(filename):
            try:
                os.remove(filename)
            except Exception:
                pass
