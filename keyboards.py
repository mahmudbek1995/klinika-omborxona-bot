from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo
)
from config import WEB_APP_URL

CLINIC_DEPARTMENTS = [
    ("🏘 Xudud bo'limi", "Xudud bo'limi"),
    ("👂 LOR bo'limi", "LOR bo'limi"),
    ("🦴 Ortopediya bo'limi", "Ortopediya bo'limi"),
    ("💉 Muolajaxonasi", "Muolajaxonasi"),
    ("🔬 Laboratoriya", "Laboratoriya"),
    ("🔪 Operatsion bo'lim", "Operatsion bo'lim"),
]

def get_main_menu() -> ReplyKeyboardMarkup:
    """Asosiy menyu tugmalari"""
    web_button = (
        KeyboardButton(text="🌐 Web Dastur (Mini App)", web_app=WebAppInfo(url=WEB_APP_URL))
        if WEB_APP_URL.startswith("https://")
        else KeyboardButton(text="🌐 Web Havola")
    )

    keyboard = [
        [
            KeyboardButton(text="📥 Kirim qilish"),
            KeyboardButton(text="📤 Chiqim qilish")
        ],
        [
            KeyboardButton(text="💊 Dori-darmonlar"),
            KeyboardButton(text="🩺 Operatsion rasxodnik")
        ],
        [
            KeyboardButton(text="🧹 Xo'jalik xarajatlari"),
            KeyboardButton(text="⚠️ Kam qolgan mollar")
        ],
        [
            KeyboardButton(text="🏢 Bo'limlar hisoboti"),
            KeyboardButton(text="🔍 Qidirish")
        ],
        [
            web_button,
            KeyboardButton(text="📊 Excel hisobot")
        ],
        [
            KeyboardButton(text="📈 Statistika"),
            KeyboardButton(text="ℹ️ Qo'llanma")
        ]
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        persistent=True
    )

def get_category_selection_keyboard(prefix: str = "cat") -> InlineKeyboardMarkup:
    """Kategoriya tanlash tugmalari"""
    keyboard = [
        [
            InlineKeyboardButton(text="💊 Dori-darmon", callback_data=f"{prefix}:dori"),
            InlineKeyboardButton(text="🩺 Operatsion rasxod", callback_data=f"{prefix}:operatsion")
        ],
        [
            InlineKeyboardButton(text="🧹 Xo'jalik moli", callback_data=f"{prefix}:xojalik")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_web_inline_keyboard() -> InlineKeyboardMarkup | None:
    """Web-ilovani ochish uchun inline tugma (faqat https bo'lganda)"""
    if WEB_APP_URL.startswith("https://"):
        btn = InlineKeyboardButton(text="🌐 Web Omborxonani ochish", web_app=WebAppInfo(url=WEB_APP_URL))
        return InlineKeyboardMarkup(inline_keyboard=[[btn]])
    return None


def get_cancel_menu() -> ReplyKeyboardMarkup:
    """Jarayonni bekor qilish tugmasi"""
    keyboard = [
        [KeyboardButton(text="❌ Bekor qilish")]
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True
    )

def get_departments_keyboard() -> InlineKeyboardMarkup:
    """Chiqim paytida bo'limni tanlash uchun inline tugmalar"""
    keyboard = []
    for label, dept_name in CLINIC_DEPARTMENTS:
        keyboard.append([
            InlineKeyboardButton(text=label, callback_data=f"dept:{dept_name}")
        ])
    
    keyboard.append([
        InlineKeyboardButton(text="✍️ Boshqa bo'lim (qo'lda yozish)", callback_data="dept:other")
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_units_keyboard() -> InlineKeyboardMarkup:
    """O'lchov birliklarini tez tanlash uchun inline tugmalar"""
    keyboard = [
        [
            InlineKeyboardButton(text="dona", callback_data="unit:dona"),
            InlineKeyboardButton(text="ampula", callback_data="unit:ampula"),
            InlineKeyboardButton(text="flakon", callback_data="unit:flakon")
        ],
        [
            InlineKeyboardButton(text="quti", callback_data="unit:quti"),
            InlineKeyboardButton(text="tabletka", callback_data="unit:tabletka"),
            InlineKeyboardButton(text="kapsula", callback_data="unit:kapsula")
        ],
        [
            InlineKeyboardButton(text="pachka", callback_data="unit:pachka"),
            InlineKeyboardButton(text="juft", callback_data="unit:juft"),
            InlineKeyboardButton(text="boshqa", callback_data="unit:boshqa")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_medicine_action_keyboard(medicine_id: int) -> InlineKeyboardMarkup:
    """Bitta dori bo'yicha tezkor amallar tugmalari"""
    keyboard = [
        [
            InlineKeyboardButton(text="📥 Kirim qilish", callback_data=f"med_in:{medicine_id}"),
            InlineKeyboardButton(text="📤 Chiqim qilish", callback_data=f"med_out:{medicine_id}")
        ],
        [
            InlineKeyboardButton(text="⚙️ Min. normani o'zgartirish", callback_data=f"med_min:{medicine_id}"),
            InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"med_del:{medicine_id}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_delete_confirm_keyboard(medicine_id: int) -> InlineKeyboardMarkup:
    """O'chirishni tasdiqlash inline klaviaturasi"""
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Ha, o'chirilsin", callback_data=f"confirm_del:{medicine_id}"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_del")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_pagination_keyboard(current_page: int, total_pages: int, prefix: str = "page") -> InlineKeyboardMarkup:
    """Dorilar ro'yxatini sahifalash tugmalari"""
    buttons = []
    if current_page > 1:
        buttons.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"{prefix}:{current_page - 1}"))
    
    buttons.append(InlineKeyboardButton(text=f"{current_page}/{total_pages}", callback_data="noop"))
    
    if current_page < total_pages:
        buttons.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"{prefix}:{current_page + 1}"))

    return InlineKeyboardMarkup(inline_keyboard=[buttons])

