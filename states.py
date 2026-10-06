from aiogram.fsm.state import State, StatesGroup

class KirimStates(StatesGroup):
    search_or_new = State()      # Dori nomini qidirish yoki yangi dori kiritish
    choose_existing = State()    # Topilgan ro'yxatdan mavjud dorini tanlash
    unit = State()               # Yangi dori uchun o'lchov birligi
    quantity = State()           # Kirim miqdori
    min_quantity = State()       # Yangi dori uchun minimal zaxira normasi
    location = State()           # Joylashuvi (polka/shkaf)
    expiry = State()             # Yaroqlilik muddati
    comment = State()            # Yetkazib beruvchi / izoh

class ChiqimStates(StatesGroup):
    search_or_select = State()   # Dorini qidirish yoki tanlash
    quantity = State()           # Chiqim miqdori
    choose_department = State()  # Bo'limni tugmalar orqali tanlash
    custom_department = State()  # Boshqa bo'lim nomini qo'lda kiritish
    comment = State()            # Kim qabul qildi / shifokor F.I.Sh / izoh

class SearchStates(StatesGroup):
    query = State()              # Qidiruv so'zi

class EditStates(StatesGroup):
    new_min_quantity = State()   # Yangi minimal me'yorni kiritish
