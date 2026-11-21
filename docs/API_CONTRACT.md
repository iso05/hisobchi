# Hisobchi API — 10 kalkulyator

Joriy xizmatlar: `notary_car`, `notary_property`, `notary_vehicle_power`, `notary_property_power`, `notary_lease`, `notary_inheritance`, `court_civil`, `court_economic`, `vehicle_power_electronic`, `patent_application`.

`GET /calculator/schema?service_id=...` va `GET /rules/current?service_id=...` tanlangan xizmatni qabul qiladi. `POST /calculate` va `/chat` so‘rovlarida service_id hamda shu xizmat sxemasiga mos answers yuboriladi. Savollar choice yoki number; `when` ko‘rsatilsa, faqat shart bajarilganda kerak.

`GET /legal-sources` barcha 10 xizmatning aniq qonun havolalari, bandlari va istisnolarini beradi. Har bir natija review_status/review_note orqali jamoaning qo‘lda tekshirishi kutilayotganini ko‘rsatadi.

Admin katalogi `/admin/calculators`: har bir xizmatda parameters metama’lumotlari bor. `notary_car` eski tekis konfiguratsiyani saqlaydi; qolgan 9 ta xizmatning sozlamalari `parameters` lug‘atida. `PUT /admin/calculators/{id}` faqat shu xizmatga tegishli qiymatlarni yangi versiya sifatida saqlaydi.

`GET /admin/rules` eski mijozlar uchun avtomobil qoidalarini qaytaradi; `?service_id=all` barcha tarixni, yoki aniq service_id bitta xizmat tarixini beradi.

Qolgan bo‘limlar asosiy kontrakt tuzilmasi va avtomobil misolini ko‘rsatadi:

Frontend base URL `/api/v1`; Vite proxy → `http://127.0.0.1:8000`. To‘liq sxemalar: http://127.0.0.1:8000/docs.

## Ochiq endpointlar

- GET /health - server holati.
- GET /api/v1/services - mavjud xizmat.
- GET /api/v1/calculator/schema - forma savollari va variantlari.
- GET /api/v1/rules/current - bugungi qoida va server sanasi.
- POST /api/v1/calculate - deterministik hisoblash.
- POST /api/v1/chat - yo‘naltiruvchi suhbat; agent_mode=guided, LLM emas.
- GET /api/v1/impact - tasdiqlar va bildirilgan tejash.
- POST /api/v1/benefit-reports - hisob egasi tasdiqlaydi, idempotent.

## Hisoblash

```json
{"service_id":"notary_car","as_of_date":"2026-11-20","answers":{"vehicle_type":"car","relative_type":"parent","bank_credit":"no","damaged":"no","location":"office","special_status":"none"}}
```

Variantlar /calculator/schema dan olinadi. Ma’lumot yetishmasa {question,result:null}; yetarli bo‘lsa {question:null,result}.

Natija: calculation_id, rule_version, as_of_date, verified_at, status, payable_amount, standard_amount, saving_amount, formula, legal_basis, next_steps, components, other_costs_note. Pul butun so‘mda, currency=UZS. Noma’lum miqdor null, nol emas. Gerb yig‘imi va texnik xizmatlar components ichida null. Davlat boji butun xizmatning jami narxi emas.

## Suhbat

```json
{"conversation_id":null,"message":"Avtomobilni otamga sotmoqchiman","service_id":"notary_car","answers":{},"history":[]}
```

Javob: conversation_id, service_id, answers, reply, question, result, agent_mode. Variant bosilganda answers[question.key]=option.value; qaytgan answers keyingi so‘rovda saqlanadi. History oldingi {role,content} xabarlar; joriy message alohida.

## Admin

- GET /api/v1/admin/calculators - kalkulyator qatorlari: id, name, description, active, rule.
- PUT /api/v1/admin/calculators/{id} - RuleConfig maydonlari + reviewed:true; tekshirilgan tahrirni yangi e’lon qilingan versiya sifatida atomik saqlaydi.
- DELETE /api/v1/admin/calculators/{id} - qayta tiklanadigan o‘chirish; ommaviy xizmatlar ro‘yxati va yangi hisoblar o‘chadi, tarix saqlanadi.
- POST /api/v1/admin/calculators/{id}/restore - qayta faollashtirish.

- POST /api/v1/admin/login body {password}; HttpOnly session cookie, 4 soat.
- GET /api/v1/admin/me, POST /api/v1/admin/logout.
- GET /api/v1/admin/rules, POST /api/v1/admin/rules (qoralama).
- POST /api/v1/admin/rules/{id}/publish body {reviewed:true}.
- GET /api/v1/admin/audit.

Qoida maydonlari: effective_from, bhm_amount, car_bhm_multiplier, motorcycle_bhm_multiplier, relative_pay_percent, bank_pay_percent, outside_multiplier, law_url, law_article, bhm_source_url, verified_at, change_note. Manbalar HTTPS Lex.uz; foiz [0,100]. Foiz - chegirma emas, belgilangan bojning to‘lanadigan ulushi.

E’lon qilingan qoidalar ustidan yozilmaydi va o‘chirilmaydi. Eng yangi, tegishli sanada amaldagi qoida ishlatiladi. Kelajak qoida oldin ishlamaydi. Oldingi hisobning natija nusxasi saqlanadi.

## Foydalanishni tasdiqlash

```json
{"calculation_id":"server-uuid","service_id":"notary_car","standard_amount":1320000,"paid_amount":66000}
```

Summalar ikkisi ham null yoki ikkisi manfiy bo‘lmagan butun son. Tejash=standard_amount-paid_amount. Bu foydalanuvchi bildirgan ma’lumot, to‘lov dalili emas. Server cookie orqali hisob egasini tekshiradi. Bir calculation_id takroran yuborilsa eski tasdiq qaytadi. Javob {report,impact}.

Impact: confirmed_reports, reports_with_amount, reported_saving_amount, currency, scope=global, is_demo=false. Bu foydalanishlar soni; noyob odamlar soni emas. Har xabar yoki hisob avtomatik tasdiq sanalmaydi.

## Xavfsizlik

Server localhostda. Admin paroli server .env faylida, frontendda yo‘q. Admin sessiyasi, cross-site yozishlarni tekshirish va login urinish limiti bor. SQL parametrlar bilan bajariladi, qoidalar kod sifatida bajarilmaydi. Internetga chiqarish production sozlamalarini talab qiladi.
