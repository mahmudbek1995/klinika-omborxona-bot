import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from typing import Optional
import database as db
from excel_export import generate_stock_excel
from notifier import notify_admin
from datetime import datetime

app = FastAPI(title="Klinika Omborxonasi Web API")

class LoginRequest(BaseModel):
    login: str
    password: str

class KirimRequest(BaseModel):
    name: str
    category: Optional[str] = "dori"
    unit: str = "dona"
    quantity: float
    min_quantity: float = 10.0
    location: Optional[str] = ""
    comment: Optional[str] = ""
    user_name: Optional[str] = "Web xodim"

class ChiqimRequest(BaseModel):
    medicine_id: int
    quantity: float
    department: str
    comment: Optional[str] = ""
    user_name: Optional[str] = "Web xodim"

@app.get("/", response_class=HTMLResponse)
async def get_index():
    template_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    if os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Index sahifasi topilmadi</h1>"

@app.post("/api/login")
async def api_login(req: LoginRequest):
    success, user, msg = await db.verify_web_login(req.login, req.password)
    if success and user:
        return {
            "success": True,
            "user": {
                "user_id": user["user_id"],
                "full_name": user["full_name"],
                "role": user["role"]
            }
        }
    return {"success": False, "message": msg}

@app.get("/api/medicines")
async def api_get_medicines(category: Optional[str] = None):
    meds = await db.get_all_medicines(category=category)
    return [dict(m) for m in meds]

@app.get("/api/stats")
async def api_get_stats():
    stats = await db.get_statistics()
    depts = await db.get_department_stats()
    stats["departments"] = [dict(d) for d in depts]
    return stats

@app.get("/api/transactions")
async def api_get_transactions(limit: int = 100):
    txs = await db.get_recent_transactions(limit=limit)
    return [dict(t) for t in txs]

@app.post("/api/kirim")
async def api_kirim(req: KirimRequest):
    if req.quantity <= 0:
        return {"success": False, "message": "Miqdor 0 dan katta bo'lishi kerak!"}

    existing = await db.get_medicine_by_name(req.name)
    now_str = datetime.now().strftime("%d.%m.%Y %H:%M")

    if existing:
        success, new_qty = await db.record_kirim(
            medicine_id=existing["id"],
            quantity=req.quantity,
            comment=req.comment or "",
            user_id=0,
            user_name=req.user_name or "Web xodim"
        )
        if success:
            # FAQAT GLAVNIY ADMINGA BILDIRISHNOMA
            await notify_admin(
                f"🌐 <b>WEB ORQALI OPERATSIYA: KIRIM</b>\n\n"
                f"🏷 <b>Nomi:</b> {existing['name']}\n"
                f"📥 <b>Kiritildi:</b> +{req.quantity:g} {existing['unit']}\n"
                f"📦 <b>Yangi qoldiq:</b> {new_qty:g} {existing['unit']}\n"
                f"👤 <b>Kim bajardi (Web):</b> {req.user_name}\n"
                f"📝 <b>Izoh:</b> {req.comment or 'Yo‘q'}\n"
                f"🕒 <b>Vaqt:</b> {now_str}"
            )
        return {"success": success, "new_quantity": new_qty, "is_new": False}
    else:
        cat_names = {"dori": "💊 Dori-darmon", "operatsion": "🩺 Operatsion rasxod", "xojalik": "🧹 Xo'jalik moli"}
        cat_str = cat_names.get(req.category, req.category)

        med_id = await db.add_new_medicine(
            name=req.name,
            unit=req.unit,
            initial_qty=req.quantity,
            min_qty=req.min_quantity,
            location=req.location or "",
            expiry_date="",
            category=req.category or "dori",
            user_id=0,
            user_name=req.user_name or "Web xodim"
        )
        # FAQAT GLAVNIY ADMINGA BILDIRISHNOMA
        await notify_admin(
            f"🆕 <b>WEB ORQALI OPERATSIYA: YANGI MAHSULOT QO'SHILDI!</b>\n\n"
            f"🏷 <b>Nomi:</b> {req.name}\n"
            f"📂 <b>Toifasi:</b> {cat_str}\n"
            f"📦 <b>Boshlang'ich qoldiq:</b> {req.quantity:g} {req.unit}\n"
            f"⚠️ <b>Min. norma:</b> {req.min_quantity:g} {req.unit}\n"
            f"📍 <b>Joylashuv:</b> {req.location or 'Ko‘rsatilmagan'}\n"
            f"👤 <b>Kim qo'shdi (Web):</b> {req.user_name}\n"
            f"📝 <b>Izoh:</b> {req.comment or 'Yo‘q'}\n"
            f"🕒 <b>Vaqt:</b> {now_str}"
        )
        return {"success": True, "medicine_id": med_id, "new_quantity": req.quantity, "is_new": True}

@app.post("/api/chiqim")
async def api_chiqim(req: ChiqimRequest):
    if req.quantity <= 0:
        return {"success": False, "message": "Miqdor 0 dan katta bo'lishi kerak!"}

    med = await db.get_medicine_by_id(req.medicine_id)
    if not med:
        return {"success": False, "message": "Dori topilmadi!"}

    success, new_qty, msg, is_low = await db.record_chiqim(
        medicine_id=req.medicine_id,
        quantity=req.quantity,
        department=req.department,
        comment=req.comment or "",
        user_id=0,
        user_name=req.user_name or "Web xodim"
    )

    if success:
        now_str = datetime.now().strftime("%d.%m.%Y %H:%M")
        # FAQAT GLAVNIY ADMINGA BILDIRISHNOMA
        await notify_admin(
            f"🌐 <b>WEB ORQALI OPERATSIYA: CHIQIM</b>\n\n"
            f"💊 <b>Dori:</b> {med['name']}\n"
            f"📤 <b>Chiqarildi:</b> -{req.quantity:g} {med['unit']}\n"
            f"🏢 <b>Bo'lim:</b> {req.department}\n"
            f"📦 <b>Yangi qoldiq:</b> {new_qty:g} {med['unit']}\n"
            f"👤 <b>Kim bajardi (Web):</b> {req.user_name}\n"
            f"📝 <b>Qabul qiluvchi / Izoh:</b> {req.comment or 'Yo‘q'}\n"
            f"🕒 <b>Vaqt:</b> {now_str}"
            + (f"\n\n🚨 <b>DIQQAT:</b> Ushbu dori omborda kam qoldi!" if is_low else "")
        )

    return {
        "success": success,
        "new_quantity": new_qty,
        "message": msg,
        "is_low": is_low
    }

@app.get("/api/export-excel")
async def api_export_excel():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ombor_hisoboti_{timestamp}.xlsx"
    filepath = await generate_stock_excel(output_filename=filename)
    return FileResponse(
        filepath,
        filename=f"Klinika_Ombor_{datetime.now().strftime('%d_%m_%Y')}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
