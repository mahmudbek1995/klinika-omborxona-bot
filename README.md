# 🏥 Klinika Omborxonasi Telegram Boti

Ushbu Telegram bot klinika omborxonasidagi barcha dorilar hisob-kitobini yuritish, kirim va chiqimlarni nazorat qilish, ombordagi aniq qoldiqni real vaqtda ko'rsatish va kam qolgan dorilar haqida ogohlantirish uchun mo'ljallangan.

---

## 🚀 Asosiy Imkoniyatlar

1. **📥 Dori Kirim qilish:**
   - Yangi dori qo'shish (nomi, o'lchov birligi, miqdori, minimal me'yor, joylashuvi, yaroqlilik muddati).
   - Mavjud dorilarning qoldig'ini oshirish.
   - Yetkazib beruvchi yoki partiya izohlarini qayd qilish.

2. **📤 Dori Chiqim qilish:**
   - Dorini tezkor qidirish yoki tanlash.
   - Mavjud qoldiqni avtomatik tekshirish (omborda boridan ortiqcha chiqim qilishga ruxsat bermaydi).
   - Qaysi bo'limga (jarrohlik, terapiya va h.k.) yoki kimga berilganini yozish.
   - **🚨 Avtomatik ogohlantirish:** Chiqim qilingach, agar dori belgilangan minimal me'yordan kam qolsa, bot darhol qizil ogohlantirish xabarini chiqaradi!

3. **📦 Barcha dorilar va Aniq Qoldiq:**
   - Ombordagi barcha dorilar ro'yxatini qulay sahifalab (pagination) ko'rsatish.
   - Har bir dorining to'liq kartochkasi (nomi, qoldig'i, joylashuvi, yaroqlilik muddati, holati).

4. **⚠️ Kam qolgan dorilar bo'limi:**
   - Zaxirasi tugayotgan (qoldig'i minimal normadan kam yoki 0 bo'lib qolgan) dorilarni bitta tugma bilan ko'rish.
   - Har bir kam qolgan dori uchun yetishmayotgan miqdorni ko'rsatish va shu yerdan turib tezkor kirim qilish imkoniyati.

5. **🔍 Qidiruv tizimi:**
   - Dori nomining bir qismini yozish orqali tez topish.

6. **📊 Excel hisobot:**
   - Barcha dorilar qoldig'i va to'liq kirim-chiqimlar jurnalini chiroyli formatlangan `.xlsx` fayl ko'rinishida yuklab olish.

7. **📈 Statistika:**
   - Jami dorilar turi, umumiy qoldiq soni, kam qolganlar va bugungi harakatlar statistikasi.

---

## 🛠 O'rnatish va Ishga tushirish

### 1. Bot tokenini olish
1. Telegramda [@BotFather](https://t.me/BotFather) ga kiring.
2. `/newbot` buyrug'ini yuboring va ko'rsatmalarga amal qilib yangi bot yarating.
3. BotFather bergan **Token**ni nusxalab oling.

### 2. Tokenni sozlash
Loyiha papkasidagi `.env` faylini oching va tokenni yozing:
```env
BOT_TOKEN=1234567890:ABCdefGhIJKlmNoPQRsTUVwxyZ
ADMINS=
```

### 3. Ishga tushirish
Windows tizimida:
- Loyiha papkasidagi **`ishga_tushirish.bat`** faylini ikki marta bosing.
- Yoki terminalda:
  ```bash
  python bot.py
  ```

Telegramda botingizga kiring va **/start** tugmasini bosing!
