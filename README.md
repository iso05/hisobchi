# Hisobchi | LexHackathon

Hozir **10 ta davlat boji kalkulyatori** mavjud. React frontend Python backendga ulangan. Har bir kalkulyatorning savollari, shartlari, imtiyozlari va admin orqali yangilanadigan stavkalari alohida.

Yo‘nalishlar: avtomobil oldi-sotdisi; ko‘chmas mulk oldi-sotdisi; notarial avtoishonchnoma; ko‘chmas mulk ishonchnomasi; notarial ijara; meros guvohnomasi; fuqarolik pul da’vosi; iqtisodiy pul da’vosi; elektron avtoishonchnoma; ixtiro/foydali model talabnomasi.

**Qo‘lda qonun bo‘yicha tekshirish:** `docs/KALKULYATOR_MANBALARI.md`da 10 kalkulyator uchun 29 ta aniq havola, modda/band va qidiruv iborasi bor. `docs/MANUAL_QABUL.md`da nazorat misollari va istisnolar berilgan. Boshlang‘ich qoidalar jamoa tekshiruvi kutilayotganini natija kartasi ochiq ko‘rsatadi.

## Ochish

### GitHub’dan birinchi marta olish

Yopiq repoga kirish uchun GitHub taklifini qabul qiling.

```powershell
git clone https://github.com/iso05/hisobchi.git
cd hisobchi
py -3.12 -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.lock.txt
backend/.venv/Scripts/python.exe backend/bootstrap.py
npm.cmd --prefix frontend ci
Set-Content frontend/.env.local 'VITE_API_BASE_URL=/api/v1'
```

Loyiha papkasidan backendni `backend/.venv/Scripts/python.exe -m uvicorn app.main:app --app-dir backend --port 8000` bilan, frontendni ikkinchi terminalda `npm.cmd --prefix frontend run dev` bilan ishga tushiring.

- Kalkulyator: http://127.0.0.1:5173/
- Admin panel: http://127.0.0.1:5173/admin
- AI yordamchi: http://127.0.0.1:5173/ai-yordamchi (yangi model ulanishini kutmoqda)
- API hujjatlari: http://127.0.0.1:8000/docs

Admin paroli `backend/.env`dagi `ADMIN_PASSWORD` qiymati. Parol Gitga kiritilmaydi.

## Qayta ishga tushirish

Backend uchun bir terminal:

```powershell
cd D:\LEXH\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Frontend uchun boshqa terminal:

```powershell
cd D:\LEXH\frontend
npm.cmd run dev
```

Python muhiti va paketlar o‘rnatilgan. `frontend/.env.local`da `VITE_API_BASE_URL=/api/v1` sozlangan. Vite `/api`ni 8000-portga uzatadi. Tizim shu kompyuterda ishlaydi; internetga e’lon qilinmagan.

## Adminning ish tartibi

Admin panelda har bir kalkulyator jadval qatorida turadi. **Tahrirlash** → BHM, davlat boji va foizlar → Lex.uz manbasi, sana va izoh → tekshirilganini belgilash → **O‘zgarishlarni saqlash**. Saqlash yangi qoida versiyasini yaratadi va belgilangan sanadan ishga tushiradi.

**O‘chirish** kalkulyatorni ommaviy ro‘yxatdan olib tashlaydi va yangi hisoblarni to‘xtatadi. Oldingi qoidalar va hisoblar saqlanadi. “O‘chirilganlarni ko‘rsatish” orqali **Qayta tiklash** mumkin.

Qoralama hisobga ta’sir qilmaydi. Oldingi e’lon qilingan qoidalar o‘zgarmaydi; har bir hisob qoidaning versiyasi va natijasini saqlaydi. Yangi qoida o‘z sanasidan ishlaydi. Admin qonunlarni o‘zi tekshiradi; avtomatik huquqiy yangilanish yo‘q.

## Hisoblash va suhbat

Chat oynasi keyingi AI integratsiyasi uchun ajratilgan.

Hisob faqat **davlat boji** uchun. Gerb yig‘imi, huquqiy-texnik xizmatlar va YHXX xarajatlari alohida; ularning miqdori hozir aniqlanmagan. YTH shikasti, kombinatsiyalangan imtiyoz yoki maxsus maqomda taxminiy natija chiqarilmaydi.

## Statistika

Foydalanuvchi imtiyozdan amalda foydalanganini o‘zi bildiradi. Har bir hisob faqat bir marta sanaladi. Noma’lum summa avtomatik tejashga aylantirilmaydi. Tasdiqlar SQLite bazasida saqlanadi; brauzerdagi eski demo raqamlaridan alohida. Bu to‘lov provayderi tasdiqlagan tranzaksiyalar emas.

## Tekshirish

```powershell
cd D:\LEXH\backend
.\.venv\Scripts\python.exe -m pytest -q
cd D:\LEXH\frontend
npm.cmd test
npm.cmd run build
```

## Fayllar

- `backend/README.md` - server va cheklovlar.
- `docs/KALKULYATOR_MANBALARI.md` - barcha kalkulyatorlar uchun aniq Lex.uz havolalari (CSV/JSON ham bor).
- `docs/MANUAL_QABUL.md` - qo‘lda tekshirish misollari va imtiyozlar.
- `docs/LEGAL_SOURCES.md` - birinchi avtomobil kalkulyatorining oldingi manba qaydlari.
- `docs/API_CONTRACT.md` - joriy API shartnomasi.
- `backend/requirements.lock.txt` - o‘rnatilgan paket versiyalari.
- `BACKEND_PROMPT.md` - oldingi reja; joriy kod uchun README va API hujjatlari ustuvor.

### Pastki menyu va notarial imtiyozlar (20.11.2026)

Ommaviy xizmatlar: `/` — kalkulyatorlar, `/ai-yordamchi` — suhbat oynasi, `/ai-xizmat` — ariza loyihasi demosidir. `/ai-ariza` eski manzili ham ishlaydi. Admin `/admin` manzilida saqlangan, ommaviy menyuda ko‘rsatilmaydi.

Har bir notarial kalkulyator shakli ostida 11-moddaning 20 bandi bor: avval tegishli bandlar, so‘ng “Barcha 20 holat” orqali to‘liq ma’lumotnoma ko‘rinadi. Ma’lumotnoma boshqa xizmatga oid bandni avtomatik ozodlikka aylantirmaydi. Manba iboralari `docs/NOTARIAL_IMTIYOZLAR.json` faylida saqlanadi va manbalar registrini yig‘uvchi skript bilan rasmiy HTML nusxasiga solishtiriladi.

Muhim hisob tuzatishi: oldi-sotdi va ijara bitimida faqat bir taraf davlat bojidan ozod bo‘lsa, 20-modda bo‘yicha boshqa taraf to‘liq to‘laydi. 11-modda maqomi tanlanganda taraflar haqida qo‘shimcha savol beriladi. Tashkilot imtiyozi bilan jismoniy taraf yoki qarindoshlik ma’lumotlari zid bo‘lsa avtomatik nol chiqarilmaydi. Ishonchnoma kabi bir tomonlama notarial harakat alohida tekshiriladi.

### Mahsulot yo‘nalishi va so‘nggi interfeys (20.11.2026)

Hisobchi — Calk.UZ singari qidiruv va xizmat kartalariga ega, davlat bojlariga ixtisoslashgan kalkulyatorlar katalogi. Asosiy oqim: xizmatni tanlash → kerakli ma’lumotlarni kiritish → boj, mos imtiyoz va Lex.uz asosini ko‘rish. AI suhbat yangi model ulanishini kutmoqda; ariza bo‘limi namuna sifatida ishlaydi.

Statistika va imtiyozdan foydalanganlikni bildirish ommaviy interfeysdan olib tashlangan. Oldingi saqlangan ma’lumotlar o‘chirilmagan. Bosh sahifada hech bir kalkulyator avtomatik tanlanmaydi. Pastki menyu o‘rniga “Nima qilmoqchisiz?” tugmasi orqali xizmat tanlash oynasi ochiladi.

AI xizmatda avval ariza turi tanlanadi: to‘lovni to‘liq qaytarish yoki ortiqcha qismini qaytarish. Ikkinchi holatda qaytarishni so‘raydigan summa = amalda to‘langan summa − to‘lash kerak bo‘lgan summa. Qaytarish huquqi avtomatik tasdiqlanmaydi; ariza loyiha sifatida tayyorlanadi va yuborilmaydi. Matnni tahrirlash, nusxalash va TXT yuklash mumkin. Namuna: 600 000 − 440 000 = 160 000 so‘m.
