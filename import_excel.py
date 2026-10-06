import asyncio
import os
import openpyxl
import aiosqlite
from datetime import datetime
from config import DB_NAME
import database as db

EXCEL_PATH = os.path.join(os.path.dirname(__file__), "initial_medicines.xlsx")
if not os.path.exists(EXCEL_PATH):
    EXCEL_PATH = r"c:\Users\Predator\Downloads\Telegram Desktop\Дорилар рўйхати 2026 й октябр.xlsx"


def determine_unit(name: str) -> str:
    n = name.lower()
    if "амп" in n:
        return "ampula"
    elif "таб" in n:
        return "tabletka"
    elif "флакон" in n:
        return "flakon"
    elif "кап" in n:
        return "kapsula"
    elif "светча" in n or "свитча" in n:
        return "shamcha"
    elif "маз" in n:
        return "tubik"
    elif "капли" in n or "сусп" in n or "масло" in n or "р-р" in n:
        return "flakon"
    elif "шприц" in n:
        return "dona"
    elif "перчатк" in n:
        return "juft"
    elif "бинт" in n or "дока" in n or "пластырь" in n:
        return "dona"
    elif "пачк" in n:
        return "pachka"
    else:
        return "dona"

def determine_min_qty(qty: float) -> float:
    if qty >= 500:
        return 50
    elif qty >= 100:
        return 20
    elif qty >= 20:
        return 10
    else:
        return 3

async def import_medicines():
    await db.init_db()

    if not os.path.exists(EXCEL_PATH):
        print(f"Xatolik: Fayl topilmadi: {EXCEL_PATH}")
        return

    wb = openpyxl.load_workbook(EXCEL_PATH)
    ws = wb.active

    imported = 0
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    async with aiosqlite.connect(DB_NAME) as conn:
        for row_idx, row in enumerate(ws.iter_rows(values_only=True), 1):
            if row_idx == 1:
                continue
            
            raw_name = row[0]
            raw_qty = row[1]

            if not raw_name or not str(raw_name).strip():
                continue

            name = " ".join(str(raw_name).split()).strip()
            
            qty = 0.0
            if raw_qty is not None and str(raw_qty).strip():
                try:
                    qty = float(str(raw_qty).replace(",", ".").strip())
                except ValueError:
                    qty = 0.0

            unit = determine_unit(name)
            min_qty = determine_min_qty(qty)

            # Agar baza oldin mavjud bo'lsa, yangilaymiz yoki kiritamiz
            cursor = await conn.execute(
                "SELECT id, quantity FROM medicines WHERE LOWER(name) = LOWER(?)",
                (name,)
            )
            existing = await cursor.fetchone()

            if existing:
                med_id = existing[0]
                await conn.execute(
                    "UPDATE medicines SET quantity = ?, unit = ?, min_quantity = ?, updated_at = ? WHERE id = ?",
                    (qty, unit, min_qty, now, med_id)
                )
            else:
                cursor = await conn.execute(
                    """
                    INSERT INTO medicines (name, unit, quantity, min_quantity, location, expiry_date, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (name, unit, qty, min_qty, "Asosiy omborxona", "", now, now)
                )
                med_id = cursor.lastrowid

            # Boshlang'ich kirim tranzaksiyasi
            if qty > 0:
                await conn.execute(
                    """
                    INSERT INTO transactions (medicine_id, type, quantity, comment, user_id, user_name, created_at)
                    VALUES (?, 'kirim', ?, ?, ?, ?, ?)
                    """,
                    (med_id, qty, "2026-yil oktyabr oyi boshlang'ich qoldig'i (Excel)", 475334833, "Ombor mudiri", now)
                )

            imported += 1

        await conn.commit()

    print(f"Muvaffaqiyatli yakunlandi! Jami {imported} ta dori bazaga kiritildi.")

if __name__ == "__main__":
    asyncio.run(import_medicines())
