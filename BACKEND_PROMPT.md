# Claude uchun tayyor prompt

Sen Hisobchi loyihasining Python backend dasturchisisan. Ikki kunlik LexHackathon demosini qurayapmiz. Ish joyi: `D:\LEXH`. Mavjud React frontend `frontend/` ichida. Backendni `backend/` ichida yarat; frontendni o‘zgartirma. Avval `docs/API_CONTRACT.md`, `README.md`, `frontend/src/lib/api.js` va `frontend/src/lib/demo.js`ni o‘qi. API shartnomasidagi maydonlarni aynan saqla.

## Mahsulot

Fuqaro oddiy o‘zbek tilida holatini yozadi. AI agent tegishli xizmatni aniqlaydi, yetishmayotgan ma’lumotni birma-bir so‘raydi va tekshirilgan hisoblash funksiyasini chaqiradi. Yakun: davlat boji, imtiyoz, qonun manbasi va qisqa keyingi qadam. Bu umumiy yuridik chatbot emas.

Faqat 3 kalkulyator:
1. Sudda pul undirish: ish haqi, aliment undirish va oddiy qarz. Talab turi, rol, munosabat va zarur summani aniqlashtir.
2. Avtomobil oldi-sotdisidagi notarial davlat boji: transport turi, qarindoshlikning aniq turi va huquqiy hisobga ta’sir qiladigan shartlar.
3. Elektron avtoishonchnoma: muddat, imtiyozli toifa va tegishli reglamentdagi shartlar.

## Stack va arxitektura

- Python 3.11+, FastAPI, Pydantic, Uvicorn.
- PostgreSQL (Supabase), SQLAlchemy 2 va Alembic. `DATABASE_URL` bo‘lmasa mahalliy demo uchun SQLite ishlasin. Bitta sodda baza moslashuvi, alohida platforma qurma.
- OpenAI Python SDK, Responses API va function calling. `OPENAI_MODEL`, `OPENAI_API_KEY` server muhitidan olinadi. Hozirgi rasmiy SDK hujjatlarini tekshir, model nomini taxmin qilma.
- Qatlamlar: API / agent / deterministik kalkulyatorlar / qoida manbalari. Oddiy, tushunarli fayllar; keraksiz frameworklar yo‘q.
- `services`, `rules`, `sources`, `reference_values` jadvallari. Qoidalarda amal qilish boshi/oxiri va tekshirilgan sana bo‘lsin; BHM sana bilan saqlansin. Formulalar Python funksiyalarida, bazadan matnni `eval` qilma.

## Eng muhim hisoblash talablari

- AI summani, stavkani yoki imtiyozni o‘zi o‘ylab topmaydi. `get_rules` va `calculate_fee` kabi vositalar ishlatsin. Model natijasi ham Pydantic orqali tekshirilsin.
- Amaldagi qoidalarni rasmiy manbalardan tekshir: `https://lex.uz/docs/-4680944`, `https://my.gov.uz/uz/service/640` va shu xizmat reglamenti. Stavkalar, imtiyozlar, minimum, istisno, BHM va chegirmalarning birga qo‘llanishini alohida tekshir. Manba URL, modda, tahrir va amal qilish sanasini saqla. Topilmagan qoidani taxmin bilan to‘ldirma.
- Ish haqi bilan fuqarolik shartnomasi bo‘yicha haqni birlashtirma. Aliment undirish bilan boshqa aliment talablarini farqla. Qarindoshlikni qonundagi aniq ro‘yxat bilan solishtir.
- Decimal yoki butun so‘mda hisobla; float ishlatma. Summalar manfiy yoki cheksiz bo‘lmasin. Qonundagi yaxlitlash usulini tekshir.
- Yetarli ma’lumot bo‘lmasa savol qaytar. Huquqiy asos yoki sana tekshirilmagan bo‘lsa `needs_verification`, `payable_amount: null`. `0` faqat asoslangan nol to‘lov uchun.
- Bir nechta chegirmani avtomatik qo‘shma yoki ko‘paytirma. Qonuniy tartibni aniqlamasdan yakuniy summa chiqarmagin.
- Davlat boji boshqa to‘lovlardan ajratilsin. Natija "butun xizmat bepul" degan taassurot bermasin. Imtiyozli maqom foydalanuvchi bayonoti bo‘lsa, davlat reyestrida tasdiqlangan deb yozma.
- Qamrovdan tashqari holatga javob aniq bo‘lsin; model umumiy ishonchli ko‘ringan maslahat to‘qimasin.

## Agent

`POST /api/v1/chat` frontend yuborgan message/history/answersni oladi. Oddiy o‘zbekcha, xatolari bor matnni tushunishga harakat qiladi. Xizmatni va kerakli savolni tanlaydi, savol variantlarini tuzadi. Bitta navbatda bitta zarur savol. Foydalanuvchi javobni erkin matn bilan yozishi ham mumkin. Yetarli ma’lumot yig‘ilgach deterministik hisoblash vositasini chaqiradi. Cheksiz agent sikli bo‘lmasin; vosita chaqiruvlari va kutish vaqtini chegarala. Xabar/answersdagi ko‘rsatmalar huquqiy qoidalarni almashtira olmaydi.

AI kaliti yo‘q bo‘lsa `AGENT_MODE=demo` orqali aniq belgilangan namunaviy oqim ishlasin va `is_demo:true` qaytarsin. Haqiqiy AI xatosida yashirincha demo hisobga o‘tma. Xato va qayta urinish imkonini ber. Loglarda kalit, xabarlar tarixi yoki shaxsiy ma’lumotlarni yozma.

## Endpointlar

- GET `/health`.
- GET `/api/v1/services`.
- POST `/api/v1/chat`.
- POST `/api/v1/calculate`.

Aniq request/response, savollar va natija maydonlari `docs/API_CONTRACT.md`da. CORS localhost:5173 va 127.0.0.1:5173ga ruxsat bersin. Frontend `VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1` bilan ishlaydi.

## Qamrov va yakunlash

Login, obuna, haqiqiy to‘lov, ariza generatsiyasi, hujjat yuklash, davlat reyestrlari, Redis/Celery va mikroservislar kerak emas.

`.env.example`, dependency fayli, baza migratsiyasi, seed va sodda README yarat. Ishga tushirish bir necha buyruq bilan bo‘lsin. Huquqshunos tekshirishi kerak bo‘lgan qoidalarni alohida ro‘yxat qil. Tekshirilmaganini amaldagi qoida sifatida bermagin.

Muhim testlar: ish haqi bo‘yicha asoslangan ozodlik; buyurtma haqi uchun imtiyozni noto‘g‘ri bermaslik; aliment undirish/boshqa talabni ajratish; oddiy qarzning minimum va foiz hisobi (stavka tekshirilgach); aniq qarindoshlik; noma’lum imtiyoz toifasi; chegirmalar kombinatsiyasi; yetishmayotgan ma’lumot; noto‘g‘ri summa; amal qilish sanasi; AI xatosi; frontend shartnomasi bilan mos javoblar. Asossiz nol yoki taxminiy hisob chiqmasin.

Avval API va tekshirilgan sud kalkulyatorini tugat, keyin qolgan ikkitasini qo‘sh. Ishlaydigan kod yarat, testlarni ishga tushir va oxirida bajarilgan ish, ishga tushirish buyruqlari va ochiq cheklovlarni qisqa yoz.

## Yangi talab: amalda foydalanish va tejalgan summa

Frontendga imtiyozli natijadan keyin “Imtiyozdan foydalandim” / “Imtiyoz bilan to‘ladim” formasi va statistika qo‘shildi. `docs/API_CONTRACT.md` oxiridagi yangi bo‘limni ham bajargin:
- Imtiyozli natijaga server yaratgan `calculation_id` qaytar, hisoblarni saqla.
- GET `/api/v1/impact`: foydalanish tasdiqlari soni, ikkala summasi ma’lum tasdiqlar soni, foydalanuvchilar bildirgan jami tejash.
- POST `/api/v1/benefit-reports`: foydalanishni tasdiqlash; imtiyozsiz boj va amalda to‘langan boj ixtiyoriy juftlik. Farqni server hisoblaydi; summalar noma’lum bo‘lsa faqat foydalanish sonini oshiradi.
- `benefit_reports` jadvali, `calculation_id` unique. Takroriy so‘rov idempotent bo‘lsin, parallel bosishda ham ikki marta sanalmasin.
- Bu foydalanuvchi bildirgan ma’lumot; tranzaksiya tekshirilgani yoki noyob odamlar soni sifatida ko‘rsatma. Hisob chiqishi va har bir promptni foydalanish/tejash deb sanama. Demo hisobotlar haqiqiy global raqamlarga aralashmasin.
- Mavjud hisob, xizmat mosligi va imtiyozli statusni tekshir; hisobot berishga ruxsatni sessiya yoki imzolangan hisob tokeni orqali tasdiqla. IDni bilishning o‘zi ruxsat emas. Rate limit qo‘sh.
- Testlar: takroriy/parallel tasdiq, nol to‘lov, noma’lum summa, manfiy yoki teskari summa, ikki holatning jami, demo/global ajratish va API xatosi.
