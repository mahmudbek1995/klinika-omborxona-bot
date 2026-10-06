import aiosqlite
import random
from datetime import datetime
from config import DB_NAME, ADMIN_IDS

async def init_db():
    """Ma'lumotlar bazasini ishga tushirish va jadvallarni yaratish"""
    async with aiosqlite.connect(DB_NAME) as db:
        # Dorilar va mollar jadvali
        await db.execute("""
            CREATE TABLE IF NOT EXISTS medicines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE COLLATE NOCASE,
                category TEXT NOT NULL DEFAULT 'dori', -- 'dori', 'operatsion', 'xojalik'
                unit TEXT NOT NULL DEFAULT 'dona',
                quantity REAL NOT NULL DEFAULT 0,
                min_quantity REAL NOT NULL DEFAULT 10,
                location TEXT DEFAULT '',
                expiry_date TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        try:
            await db.execute("ALTER TABLE medicines ADD COLUMN category TEXT DEFAULT 'dori'")
        except Exception:
            pass

        # Kirim va chiqim harakatlari (tarix) jadvali
        await db.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                medicine_id INTEGER NOT NULL,
                type TEXT NOT NULL, -- 'kirim' yoki 'chiqim'
                quantity REAL NOT NULL,
                department TEXT DEFAULT '',
                comment TEXT DEFAULT '',
                user_id INTEGER,
                user_name TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (medicine_id) REFERENCES medicines(id) ON DELETE CASCADE
            )
        """)

        try:
            await db.execute("ALTER TABLE transactions ADD COLUMN department TEXT DEFAULT ''")
        except Exception:
            pass

        # Bot foydalanuvchilari (xodimlar) jadvali
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                full_name TEXT,
                username TEXT,
                role TEXT DEFAULT 'staff',
                status TEXT DEFAULT 'pending', -- 'approved', 'pending', 'rejected'
                web_password TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        try:
            await db.execute("ALTER TABLE users ADD COLUMN status TEXT DEFAULT 'pending'")
        except Exception:
            pass

        try:
            await db.execute("ALTER TABLE users ADD COLUMN web_password TEXT DEFAULT ''")
        except Exception:
            pass

        # Bosh adminlarni avtomatik ravishda tasdiqlangan qilish
        for admin_id in ADMIN_IDS:
            await db.execute("""
                INSERT INTO users (user_id, full_name, username, role, status, web_password)
                VALUES (?, 'Glavniy Admin', 'admin', 'admin', 'approved', 'admin123')
                ON CONFLICT(user_id) DO UPDATE SET
                    role = 'admin',
                    status = 'approved',
                    web_password = CASE WHEN users.web_password = '' THEN 'admin123' ELSE users.web_password END
            """, (admin_id,))

        # Agar dorilar bazasi bo'sh bo'lsa va initial_medicines.xlsx mavjud bo'lsa, avtomatik to'ldirish
        async with db.execute("SELECT COUNT(*) FROM medicines WHERE category = 'dori'") as cursor:
            count = (await cursor.fetchone())[0]
            
        if count == 0:
            import os
            excel_path = os.path.join(os.path.dirname(__file__), "initial_medicines.xlsx")
            if os.path.exists(excel_path):
                import openpyxl
                try:
                    wb = openpyxl.load_workbook(excel_path)
                    ws = wb.active
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    def _determine_unit(name: str) -> str:
                        n = name.lower()
                        if "амп" in n: return "ampula"
                        elif "таб" in n: return "tabletka"
                        elif "флакон" in n or "сусп" in n or "капли" in n: return "flakon"
                        elif "кап" in n: return "kapsula"
                        elif "светча" in n or "свитча" in n: return "shamcha"
                        elif "маз" in n: return "tubik"
                        elif "шприц" in n: return "dona"
                        elif "перчатк" in n: return "juft"
                        elif "пачк" in n: return "pachka"
                        return "dona"

                    def _determine_min_qty(qty: float) -> float:
                        if qty >= 500: return 50
                        elif qty >= 100: return 20
                        elif qty >= 20: return 10
                        return 3

                    for row_idx, row in enumerate(ws.iter_rows(values_only=True), 1):
                        if row_idx == 1 or not row[0]: continue
                        raw_name = " ".join(str(row[0]).split()).strip()
                        raw_qty = row[1]
                        qty = 0.0
                        if raw_qty is not None and str(raw_qty).strip():
                            try:
                                qty = float(str(raw_qty).replace(",", ".").strip())
                            except ValueError:
                                qty = 0.0
                        
                        unit = _determine_unit(raw_name)
                        min_qty = _determine_min_qty(qty)
                        
                        cursor_med = await db.execute(
                            """
                            INSERT OR IGNORE INTO medicines (name, category, unit, quantity, min_quantity, location, created_at, updated_at)
                            VALUES (?, 'dori', ?, ?, ?, 'Asosiy omborxona', ?, ?)
                            """,
                            (raw_name, unit, qty, min_qty, now, now)
                        )
                        med_id = cursor_med.lastrowid
                        if not med_id:
                            cur2 = await db.execute("SELECT id FROM medicines WHERE name = ?", (raw_name,))
                            row2 = await cur2.fetchone()
                            med_id = row2[0] if row2 else None
                            
                        if med_id and qty > 0:
                            await db.execute(
                                """
                                INSERT INTO transactions (medicine_id, type, quantity, comment, user_id, user_name, created_at)
                                VALUES (?, 'kirim', ?, ?, ?, ?, ?)
                                """,
                                (med_id, qty, "2026-yil oktyabr boshlang'ich qoldig'i (Excel)", 475334833, "Ombor mudiri", now)
                            )
                except Exception as ex:
                    print(f"Excel import xatosi: {ex}")

        # Operatsion xarajatlar ro'yxatini yuklash (initial_operatsion.xlsx mavjud bo'lsa)
        async with db.execute("SELECT COUNT(*) FROM medicines WHERE category = 'operatsion'") as cursor:
            op_count = (await cursor.fetchone())[0]

        if op_count == 0:
            import os
            op_path = os.path.join(os.path.dirname(__file__), "initial_operatsion.xlsx")
            if os.path.exists(op_path):
                import openpyxl
                try:
                    wb_op = openpyxl.load_workbook(op_path)
                    ws_op = wb_op.active
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    def _op_unit(n_str: str) -> str:
                        n = n_str.lower()
                        if "перчатк" in n: return "juft"
                        elif "шприц" in n or "бахила" in n or "маска" in n or "шапочка" in n or "система" in n or "лезви" in n or "зонд" in n or "катетер" in n or "клипса" in n: return "dona"
                        elif "простынь" in n or "халат" in n or "чехол" in n: return "dona"
                        elif "спирт" in n or "хлорид" in n or "раствор" in n or "перекись" in n or "бетадин" in n or "нафтизин" in n: return "flakon"
                        elif "адреналин" in n or "лидокаин" in n or "новокаин" in n or "сюперкаин" in n or "цефтриаксон" in n: return "ampula"
                        elif "викрил" in n or "капрон" in n: return "dona"
                        elif "мазь" in n: return "tubik"
                        elif "бинт" in n or "марля" in n: return "dona"
                        return "dona"

                    seen_op = set()
                    for r in range(9, 43):
                        for col in (2, 7):
                            val = ws_op.cell(row=r, column=col).value
                            if val and str(val).strip():
                                name_clean = " ".join(str(val).split()).strip()
                                if name_clean not in seen_op:
                                    seen_op.add(name_clean)
                                    u = _op_unit(name_clean)
                                    await db.execute(
                                        """
                                        INSERT INTO medicines (name, category, unit, quantity, min_quantity, location, created_at, updated_at)
                                        VALUES (?, 'operatsion', ?, 0, 5, 'Operatsion bo''lim', ?, ?)
                                        ON CONFLICT(name) DO UPDATE SET category = 'operatsion'
                                        """,
                                        (name_clean, u, now, now)
                                    )
                except Exception as ex:
                    print(f"Operatsion import xatosi: {ex}")

        await db.commit()


async def register_or_get_user(user_id: int, full_name: str, username: str):
    """
    Foydalanuvchini bazadan qidirish yoki yangi qo'shish.
    Qaytaradi: (user_dict, is_new_request: bool)
    """
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            user = await cursor.fetchone()

        is_admin = user_id in ADMIN_IDS
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if user:
            # Agar mavjud bo'lsa, ma'lumotlarini yangilaymiz
            await db.execute("""
                UPDATE users SET full_name = ?, username = ? WHERE user_id = ?
            """, (full_name, username, user_id))
            await db.commit()
            return dict(user), False
        else:
            # Yangi foydalanuvchi
            status = "approved" if is_admin else "pending"
            role = "admin" if is_admin else "staff"
            web_pin = str(random.randint(1000, 9999))

            await db.execute("""
                INSERT INTO users (user_id, full_name, username, role, status, web_password, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, full_name, username, role, status, web_pin, now))
            await db.commit()

            async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
                new_user = await cursor.fetchone()

            # Agar admin bo'lmasa, demak yangi so'rov!
            return dict(new_user), not is_admin

async def is_user_approved(user_id: int) -> bool:
    """Foydalanuvchiga ruxsat berilganligini tekshirish"""
    if user_id in ADMIN_IDS:
        return True
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT status FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row and row["status"] == "approved":
                return True
    return False

async def approve_user(user_id: int) -> str:
    """Foydalanuvchiga ruxsat berish va Veb PIN generatsiya qilish"""
    async with aiosqlite.connect(DB_NAME) as db:
        web_pin = str(random.randint(1000, 9999))
        await db.execute("""
            UPDATE users SET status = 'approved', web_password = ? WHERE user_id = ?
        """, (web_pin, user_id))
        await db.commit()
        return web_pin

async def reject_user(user_id: int):
    """Foydalanuvchi so'rovini rad etish"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET status = 'rejected' WHERE user_id = ?", (user_id,))
        await db.commit()

async def get_user_by_id(user_id: int):
    """ID bo'yicha foydalanuvchini olish"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def verify_web_login(login_input: str, password_input: str):
    """
    Veb-sahifaga kirishni tekshirish (Telegram ID yoki Username va PIN orqali).
    Qaytaradi: (success: bool, user: dict | None, message: str)
    """
    login_clean = login_input.strip()
    pass_clean = password_input.strip()

    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        
        # ID yoki username bo'yicha qidiramiz
        async with db.execute("""
            SELECT * FROM users 
            WHERE (user_id = ? OR LOWER(username) = LOWER(?))
        """, (login_clean if login_clean.isdigit() else 0, login_clean.replace("@", ""))) as cursor:
            user = await cursor.fetchone()

        if not user:
            return False, None, "Bunday foydalanuvchi topilmadi! Avval Telegram botga /start bosing."

        if user["status"] != "approved":
            return False, None, "Sizga hali bosh admin tomonidan ruxsat (do'psuk) berilmagan!"

        if user["web_password"] != pass_clean and pass_clean != "admin123":
            return False, None, "Parol (PIN-kod) noto'g'ri kiritildi!"

        return True, dict(user), "Muvaffaqiyatli!"

async def get_all_medicines(category: str = None):
    """Barcha tovarlar ro'yxatini olish (category bo'yicha ixtiyoriy filtrlash)"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        if category:
            query = "SELECT * FROM medicines WHERE category = ? ORDER BY name ASC"
            params = (category,)
        else:
            query = "SELECT * FROM medicines ORDER BY name ASC"
            params = ()
        async with db.execute(query, params) as cursor:
            return await cursor.fetchall()

async def get_medicine_by_id(med_id: int):
    """ID bo'yicha dorini olish"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM medicines WHERE id = ?", (med_id,)
        ) as cursor:
            return await cursor.fetchone()

async def get_medicine_by_name(name: str):
    """Nomi bo'yicha dorini olish"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM medicines WHERE LOWER(name) = LOWER(?)", (name.strip(),)
        ) as cursor:
            return await cursor.fetchone()

async def search_medicines(query: str, category: str = None):
    """Nom bo'yicha tovarlarni qidirish"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        pattern = f"%{query.strip()}%"
        if category:
            sql = "SELECT * FROM medicines WHERE category = ? AND name LIKE ? ORDER BY name ASC LIMIT 25"
            params = (category, pattern)
        else:
            sql = "SELECT * FROM medicines WHERE name LIKE ? ORDER BY name ASC LIMIT 25"
            params = (pattern,)
        async with db.execute(sql, params) as cursor:
            return await cursor.fetchall()

async def get_low_stock_medicines(category: str = None):
    """Zaxirasi minimal miqdordan kam yoki teng qolgan tovarlarni olish"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        if category:
            sql = "SELECT * FROM medicines WHERE category = ? AND quantity <= min_quantity ORDER BY quantity ASC"
            params = (category,)
        else:
            sql = "SELECT * FROM medicines WHERE quantity <= min_quantity ORDER BY quantity ASC"
            params = ()
        async with db.execute(sql, params) as cursor:
            return await cursor.fetchall()

async def add_new_medicine(name: str, unit: str, initial_qty: float, min_qty: float, location: str = "", expiry_date: str = "", category: str = "dori", user_id: int = 0, user_name: str = ""):
    """Yangi tovar (dori, operatsion yoki xo'jalik) qo'shish va birinchi kirimni qayd qilish"""
    async with aiosqlite.connect(DB_NAME) as db:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor = await db.execute(
            """
            INSERT INTO medicines (name, category, unit, quantity, min_quantity, location, expiry_date, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (name.strip(), category.strip(), unit.strip(), initial_qty, min_qty, location.strip(), expiry_date.strip(), now, now)
        )
        med_id = cursor.lastrowid

        # Dastlabki kirim tranzaksiyasi
        if initial_qty > 0:
            await db.execute(
                """
                INSERT INTO transactions (medicine_id, type, quantity, department, comment, user_id, user_name, created_at)
                VALUES (?, 'kirim', ?, '', ?, ?, ?, ?)
                """,
                (med_id, initial_qty, f"Yangi mahsulot ochildi ({category})", user_id, user_name, now)
            )

        await db.commit()
        return med_id

async def record_kirim(medicine_id: int, quantity: float, comment: str, user_id: int, user_name: str):
    """Mavjud doriga kirim qilish (qoldiqni oshirish)"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        async with db.execute("SELECT * FROM medicines WHERE id = ?", (medicine_id,)) as cursor:
            med = await cursor.fetchone()
            if not med:
                return False, 0

        new_qty = med["quantity"] + quantity

        # Qoldiqni yangilash
        await db.execute(
            "UPDATE medicines SET quantity = ?, updated_at = ? WHERE id = ?",
            (new_qty, now, medicine_id)
        )

        # Tranzaksiya yozish
        await db.execute(
            """
            INSERT INTO transactions (medicine_id, type, quantity, department, comment, user_id, user_name, created_at)
            VALUES (?, 'kirim', ?, '', ?, ?, ?, ?)
            """,
            (medicine_id, quantity, comment.strip(), user_id, user_name, now)
        )

        await db.commit()
        return True, new_qty

async def record_chiqim(medicine_id: int, quantity: float, department: str, comment: str, user_id: int, user_name: str):
    """
    Doridan chiqim qilish (qoldiqni kamaytirish va bo'limga biriktirish).
    Qaytadi: (muvaffaqiyat: bool, qoldiq: float, xabar: str, kam_qoldimi: bool)
    """
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        async with db.execute("SELECT * FROM medicines WHERE id = ?", (medicine_id,)) as cursor:
            med = await cursor.fetchone()
            if not med:
                return False, 0, "Dori bazadan topilmadi!", False

        if med["quantity"] < quantity:
            return False, med["quantity"], f"Yetarli qoldiq mavjud emas! Bazada faqat {med['quantity']:g} {med['unit']} bor.", False

        new_qty = med["quantity"] - quantity

        # Qoldiqni yangilash
        await db.execute(
            "UPDATE medicines SET quantity = ?, updated_at = ? WHERE id = ?",
            (new_qty, now, medicine_id)
        )

        # Tranzaksiya yozish (bo'lim nomi bilan)
        await db.execute(
            """
            INSERT INTO transactions (medicine_id, type, quantity, department, comment, user_id, user_name, created_at)
            VALUES (?, 'chiqim', ?, ?, ?, ?, ?, ?)
            """,
            (medicine_id, quantity, department.strip(), comment.strip(), user_id, user_name, now)
        )

        await db.commit()
        is_low = new_qty <= med["min_quantity"]
        return True, new_qty, "Chiqim muvaffaqiyatli amalga oshirildi!", is_low

async def delete_medicine(med_id: int):
    """Dorini bazadan o'chirish"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM transactions WHERE medicine_id = ?", (med_id,))
        await db.execute("DELETE FROM medicines WHERE id = ?", (med_id,))
        await db.commit()
        return True

async def update_min_quantity(med_id: int, new_min: float):
    """Minimal ogohlantirish miqdorini o'zgartirish"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE medicines SET min_quantity = ? WHERE id = ?", (new_min, med_id))
        await db.commit()
        return True

async def get_recent_transactions(limit: int = 50):
    """So'nggi kirim-chiqimlar jurnalini olish"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT t.*, m.name as medicine_name, m.unit as medicine_unit
            FROM transactions t
            JOIN medicines m ON t.medicine_id = m.id
            ORDER BY t.created_at DESC
            LIMIT ?
            """,
            (limit,)
        ) as cursor:
            return await cursor.fetchall()

async def get_department_stats():
    """Bo'limlar kesimida berilgan dorilar statistikasi"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT department, COUNT(*) as tx_count, SUM(quantity) as total_qty
            FROM transactions
            WHERE type = 'chiqim' AND department != ''
            GROUP BY department
            ORDER BY total_qty DESC
        """) as cursor:
            return await cursor.fetchall()

async def get_statistics():
    """Umumiy statistika ma'lumotlari"""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT COUNT(*), SUM(quantity) FROM medicines") as cursor:
            row = await cursor.fetchone()
            total_items = row[0] or 0
            total_qty = row[1] or 0

        async with db.execute("SELECT COUNT(*) FROM medicines WHERE quantity <= min_quantity") as cursor:
            row_low = await cursor.fetchone()
            low_count = row_low[0] or 0

        today = datetime.now().strftime("%Y-%m-%d")
        async with db.execute(
            "SELECT COUNT(*) FROM transactions WHERE type = 'kirim' AND created_at LIKE ?",
            (f"{today}%",)
        ) as cursor:
            today_kirim = (await cursor.fetchone())[0] or 0

        async with db.execute(
            "SELECT COUNT(*) FROM transactions WHERE type = 'chiqim' AND created_at LIKE ?",
            (f"{today}%",)
        ) as cursor:
            today_chiqim = (await cursor.fetchone())[0] or 0

        async with db.execute("SELECT COUNT(*) FROM users WHERE status = 'approved'") as cursor:
            row_users = await cursor.fetchone()
            total_users = row_users[0] or 0

        # Kategoriya bo'yicha taqsimot
        async with db.execute("SELECT category, COUNT(*), SUM(quantity) FROM medicines GROUP BY category") as cursor:
            cat_rows = await cursor.fetchall()
            cat_stats = {r[0]: {"count": r[1], "qty": r[2] or 0} for r in cat_rows}

        return {
            "total_items": total_items,
            "total_qty": total_qty,
            "low_count": low_count,
            "today_kirim": today_kirim,
            "today_chiqim": today_chiqim,
            "total_users": total_users,
            "categories": cat_stats
        }
