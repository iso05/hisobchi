# Hisobchi Python backend

Python 3.12, FastAPI, Pydantic va SQLite. SQLite fayli `data/hisobchi.sqlite3`da, qoidalar va hisoblar diskda saqlanadi. Demo uchun alohida PostgreSQL o‘rnatish shart emas.

## Ishga tushirish

```powershell
cd D:\LEXH\backend
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe bootstrap.py
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Muhit va paketlar dastlabki ishda o‘rnatilgan. Keyingi safar oxirgi buyruq yetadi.

Frontend: `D:\LEXH\frontend`da `npm.cmd run dev`. Vite `/api`ni Python serveriga uzatadi. Kalkulyator http://127.0.0.1:5173/, admin http://127.0.0.1:5173/admin, API hujjatlari http://127.0.0.1:8000/docs.

## Admin kirishi

Mahalliy admin paroli `backend/.env`dagi `ADMIN_PASSWORD` qiymati. Fayl Gitga kiritilmaydi. `bootstrap.py` kuchli tasodifiy parol yaratadi va mavjud parolni almashtirmaydi. Admin cookie 4 soat amal qiladi, HttpOnly va SameSite=Strict. Server faqat ushbu kompyuterda ochilgan. Internetga chiqarishdan oldin HTTPS, production cookie, foydalanuvchi rollari va deployment sozlamalari kerak.

## Qoida yangilash

Admin jadvali: **Tahrirlash** → qiymatlar, Lex.uz manbalari, modda, kuchga kirish sanasi va izoh → tekshirilganini belgilash → **O‘zgarishlarni saqlash**. Saqlash bitta tranzaksiyada yangi, e’lon qilingan versiya yaratadi. Eski qoralama API endpointlari orqaga moslik uchun saqlangan.

Kalkulyator qatoridagi **O‘chirish** xizmatni faol ro‘yxatdan chiqaradi. Qoidalar va hisoblar saqlanadi. O‘chirilganlarni ko‘rsatib **Qayta tiklash** mumkin. Server hisoblash so‘rovlarini ham faol holat bo‘yicha tekshiradi.

Qoralama hisobga ta’sir qilmaydi. E’lon qilingan, tegishli sanada kuchga kirgan eng yangi versiya qo‘llanadi. Oldingi versiyalarni o‘chirish yoki ustidan yozish bazada ham taqiqlangan. Har bir hisob qoida raqami va natijaning o‘sha paytdagi nusxasini saqlaydi. Kelajak qoida sanasidan oldin ishlamaydi. Noto‘g‘ri o‘zgarishni to‘g‘rilash uchun tuzatilgan yangi versiya yarating. Qoidalar avtomatik Lex.uz’dan yangilanmaydi; admin tekshiradi va e’lon qiladi.

Foizlar **to‘lanadigan ulush**: qarindoshga 5% to‘lash = 95% kamayish. Bu BHMning 5%i emas, avval hisoblangan bojning 5%i.

## Hozirgi qamrov

2026-11-20 yangilanishi: **10 kalkulyator**. `app/catalog.py` savollar, parametrlar, shartlar va manbalarni; `app/engine.py` deterministik hisoblarni boshqaradi. Avtomobil uchun oldingi `calculator.py` saqlangan. `rules.service_id` migratsiyasi oldingi qoidalar, hisoblar va hisobotlarni saqlagan holda bajariladi.

Yangi kalkulyatorlarning stavkalari `CatalogRuleConfig.parameters` ichida Decimal qiymatlar. Faqat katalogda ruxsat etilgan kalitlar va chegaralar qabul qilinadi. Admin tahriri bitta kalkulyatorga ta’sir qiladi; boshqa xizmat tarifi o‘zgarmaydi. Numeric savollarga faqat butun son qabul qilinadi, shartli savollar `when` bilan boshqariladi.

Har bir xizmatning aniq qamrovi, manbalari va qo‘lda tekshirish holati API’dan qaytadi. `../docs/KALKULYATOR_MANBALARI.md` hamda `../docs/MANUAL_QABUL.md` jamoaning huquqiy qabul hujjatlari.

Quyidagi eski qayd birinchi kalkulyatorga tegishli:

Avtomobil va mototransport oldi-sotdisining notarial **davlat boji**: umumiy stavka; qonundagi aniq qarindoshlik turlari; bank krediti; notarial idoradan tashqarida rasmiylashtirish koeffitsiyenti. Manbalar `../docs/LEGAL_SOURCES.md`da.

YTHda shikastlangan transport, bank krediti va qarindoshlik imtiyozi birga kelishi, boshqa shaxsiy imtiyozlar yoki yaxlitlash qoidasini talab qiladigan kasr natijada avtomatik yakuniy summa berilmaydi. Faqat tekshirilgan asoslar qo‘llanadi.

Gerb yig‘imi, huquqiy-texnik xizmatlar, sug‘urta va YHXX xarajatlari umumiy davlat boji natijasiga qo‘shilmaydi; ularni nol deb ko‘rsatmaymiz. Ularning miqdori hali ushbu kalkulyatorda yo‘q.


## Statistika

`/benefit-reports` hisobning ayni brauzerga tegishli ekanini cookie orqali tekshiradi, bitta hisobni qayta sanamaydi va foydalanuvchi tasdiqlagan summalarni yig‘adi. Bu to‘lov provayderi tasdiqlagan pul yoki noyob odamlar soni emas. Mahalliy frontendning eski demo statistikasi haqiqiy server bazasiga ko‘chirilmaydi.

## Testlar

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Testlarda alohida vaqtinchalik baza ishlatiladi; sun’iy stavkalar real demo bazasiga yozilmaydi.
