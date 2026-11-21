# Admin kalkulyator konstruktori

Manzil: http://127.0.0.1:5173/admin

## Ishlatish

1. Admin panelga kiring va “Yangi kalkulyator”ni bosing.
2. Nom, xizmat turi va ikonka tanlang. Kerak bo‘lsa yangi xizmat turi qo‘shing.
3. BHM va boshlang‘ich bojni kiriting. Masalan, 3 BHM.
4. “Omil qo‘shish” orqali savollarni yarating. Tanlash ro‘yxatiga variantlar, raqamli maydonga chegaralar, matnga kerakli nom qo‘ying.
5. Har bir variantning ta’sirini tanlang: hisobga ta’sir qilmaydi, bojni almashtiradi, jamiga qo‘shiladi, ko‘paytiradi yoki bojdan ozod qiladi. Qiymat BHM, foiz yoki so‘m bilan kiritiladi. Ko‘paytirish uchun oddiy son ham bor.
6. Manba nomi va Lex.uz havolasini qo‘shing.
7. “Sinab ko‘rish”ni bosing. Qoralama saqlanadi, pastda sinov formasi ochiladi. Javoblarni kiriting va “Natijani ko‘rish”ni bosing.
8. Hisob to‘g‘ri bo‘lsa “E’lon qilish”ni bosing. Karta saytga o‘z xizmat turida chiqadi. Kelajak sana tanlangan bo‘lsa o‘sha sanadan ko‘rinadi.

## Foiz va hisoblash asosi

“Foiz” tanlanganda 3 qiymati 3/100 degani. Foiz nimadan olinishini ham tanlang: boshlang‘ich boj, hozirgi jami, BHM yoki raqamli maydon.

Misol: boshlang‘ich boj 3 BHM, BHM 440 000. “Ota-ona” varianti “almashtirish / foiz / 5 / boshlang‘ich boj” bo‘lsa natija 66 000 so‘m. Bu arifmetik sozlash namunasi; yangi xizmat stavkasini admin o‘z manbasiga ko‘ra kiritadi.

Da’vo summasidan 4% va kamida 1 BHM hisoblash uchun “Da’vo summasi” raqamli omili qo‘shiladi. Boshlang‘ich boj turi “foiz”, qiymati 4, asosi shu raqamli maydon qilinadi. Eng kam boj 1 BHM qilib belgilanadi.

“Ketma-ket” tartibida hisob boshlang‘ich bojdan boshlanadi va omillar yuqoridan pastga bajariladi. “Qismlarni yig‘ish” tartibida hisob 0 dan boshlanadi. Har bir qism uchun “qo‘shish” amali qo‘yiladi. Birorta ta’sirli shart bajarilmasa boshlang‘ich boj olinadi. Shartli qoidalar omillardan keyin, tartib bilan bajariladi.

“Bojdan ozod qilish” yakuniy 0 beradi; eng kam boj uni oshirmaydi. Matn maydoni bevosita arifmetikaga kirmaydi, ammo shartli qoida uchun ishlatiladi. Savolni faqat oldingi tanlash omilining ma’lum variantidan keyin ko‘rsatish ham mumkin.

## Saqlash va versiyalar

Qoralama foydalanuvchiga ko‘rinmaydi. E’lon qilingan kalkulyatorni tahrirlash ham dastlab qoralamada qoladi. O‘zgargan qoralamani qayta sinash kerak; keyin yangi versiya chiqariladi. Eski hisoblar va e’lon qilingan qoidalar saqlanadi. O‘chirish kalkulyatorni yashiradi; jadvaldagi “O‘chirilganlarni ko‘rsatish” orqali tiklash mumkin.

Sinov va foydalanuvchi hisobi bitta Python hisoblash tizimidan foydalanadi. Qoralama muvaffaqiyatli hisoblanganligi uning huquqiy mazmunini avtomatik tasdiqlamaydi. Manba va stavkani admin kiritadi. Kasr so‘m hosil bo‘lsa summa yashirin yaxlitlanmaydi va bunday sinov e’lon qilish uchun yetarli deb olinmaydi.

Avvalgi 10 kalkulyator saqlangan; ular jadvalda “Mavjud kalkulyator” deb ko‘rsatiladi va stavkalari oldingi shaklda tahrirlanadi. Yangi kalkulyatorlar to‘liq konstruktorda yaratiladi. AI chatbot integratsiyasi ushbu o‘zgarishga kiritilmagan.

## Tuzilma

- `backend/app/builder.py`: ta’riflarni tekshirish, umumiy hisoblash, qoralama/sinov/e’lon qilish API.
- `custom_calculators`: qoralama, tahrir raqami, sinovdan o‘tgan ta’rif xeshi, yashirish belgisi.
- `custom_categories`: admin qo‘shgan xizmat turlari.
- `rules`: e’lon qilingan o‘zgarmas versiyalar. Natijalar shu versiyaga bog‘lanadi.
- `frontend/src/components/BuilderEditor.jsx`: sodda sozlash va sinov formasi.
- `frontend/src/components/CalculatorTable.jsx`: har bir amal alohida ustunda; muharrir qator tagida.

## Tekshirilgan oqim

Admin orqali namuna yaratildi, yangi toifa va ikonka tanlandi, 3 BHM va 5% varianti qo‘shildi. Admin va public hisob ikkalasida 66 000 so‘m chiqdi. Qoralama 4 BHMga o‘zgarganda public hisob 66 000 bo‘lib qoldi, admin sinovi 88 000 berdi. Keyin yangi versiya e’lon qilindi. Sinov yozuvi tekshiruvdan keyin yashirildi; asosiy 10 xizmat saqlangan.
