# Hisobchi

Hisobchi O‘zbekistondagi davlat bojini foydalanuvchining holatiga qarab hisoblaydi. Natijada summa, qo‘llangan stavka va Lex.uz manbasi chiqadi. Admin yangi kalkulyatorni kod yozmasdan yaratadi, sinaydi va e’lon qiladi.

[Checkpoint taqdimoti (PDF)](output/pdf/Hisobchi-checkpoint.pdf) · [Texnik qo‘llanma (PDF)](output/pdf/Hisobchi-texnik-qollanma.pdf) · [SQLite sxemasi](docs/SQLITE-SXEMA.svg)

## Ishga tushirish

Windows uchun Python 3.12, Node.js 22 va npm kerak. PowerShell oynasida quyidagilarni bajaring.

```powershell
git clone https://github.com/iso05/hisobchi.git
cd hisobchi
py -3.12 -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.lock.txt
backend/.venv/Scripts/python.exe backend/bootstrap.py
npm.cmd --prefix frontend ci
npm.cmd --prefix frontend run build
backend/.venv/Scripts/python.exe -m uvicorn app.web:app --app-dir backend --host 127.0.0.1 --port 8000
```

Brauzerda [Hisobchini oching](http://127.0.0.1:8000/). Shu jarayon tayyor frontend fayllari va API’ni bitta manzildan uzatadi. Birinchi ishga tushirishda bootstrap admin parolini backend/.env fayliga yozadi va namuna kalkulyatorlarini e’lon qiladi. Admin panel manzili /admin.

## Jonli demo

| Kalkulyator | Bitta o‘zgarish | 2026-11-21 uchun natija |
| --- | --- | --- |
| Avtomobil oldi-sotdisi | Oddiy avtomobil, bank kreditisiz, notarius idorasida. Xaridor boshqa shaxsdan ota yoki onaga almashadi. | 1 320 000 so‘mdan 66 000 so‘mga |
| Qarz shartnomasi | Tasdiqlash o‘rniga bekor qilish tanlanadi. | 110 000 so‘mdan 55 000 so‘mga |
| Tezlikni oshirish jarimasi | Cheklov 60 km/soat. Radar tezligi 85 dan 86 km/soatga o‘zgaradi. | 440 000 so‘mdan 2 200 000 so‘mga |

Ariza sahifasida fuqaro ortiqcha to‘langan bojni qaytarish uchun o‘zbekcha yoki ruscha ariza tayyorlaydi va PDF yoki DOCX yuklaydi. Shaxsiy rekvizitlar brauzerda ishlanadi.

## LexAI

Chatni yoqish uchun backend/.env fayliga LEXAI_URL qiymati sifatida jamoaning faol Gradio HTTPS manzilini kiriting va backendni qayta ishga tushiring. /ai-yordamchi sahifasi joriy savolni backend orqali /ask_json xizmatiga yuboradi. Gradio manzili vaqtinchalik bo‘lishi mumkin. Modelning xulosasi va arifmetikasi xato chiqishi mumkin. Yakuniy summa uchun tegishli kalkulyatordan foydalaning. Kalkulyator va ariza LexAI xizmatidan mustaqil ishlaydi.

## Serverga joylash

Frontendni yig‘ib, yuqoridagi app.web:app jarayonini HTTPS teskari proksi ortida ishga tushiring. HISOBCHI_PUBLIC_ORIGIN qiymatini saytning aniq HTTPS manziliga sozlang. Mijoz IP va HTTPS sarlavhalari uchun faqat o‘z proksingiz manziliga ishoning. ADMIN_PASSWORD va LEXAI_URL server muhitida yoki himoyalangan backend/.env faylida saqlanadi. SQLite uchun HISOBCHI_DB orqali doimiy diskdagi faylni belgilang. Zaxira olish va tiklash tartibi [texnik qo‘llanmada](output/pdf/Hisobchi-texnik-qollanma.pdf) keltirilgan.

## Dasturlash va sinov

Frontend bilan ishlashda alohida terminalda npm.cmd --prefix frontend run dev buyrug‘i Vite’ni 5173-portda ishga tushiradi. Mahalliy API uchun odatiy port 8000.

```powershell
Push-Location backend
.venv/Scripts/python.exe -m pytest -q
Pop-Location
npm.cmd --prefix frontend test
npm.cmd --prefix frontend run build
```

[Backend va ma’lumotlar modeli](docs/MVP-TEXNIK.md) · [Kalkulyator manbalari](docs/KALKULYATOR_MANBALARI.md) · [Qo‘lda sinash misollari](docs/MANUAL_QABUL.md)
