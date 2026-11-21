from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

from .models import RELATIVES, Answers, RuleConfig
from .notarial import party_question, configure_notarial_questions

LAW = 'https://lex.uz/docs/-4680944'
REGULATION = 'https://lex.uz/docs/-5109530'


def today():
    return datetime.now(timezone(timedelta(hours=5))).date()


def question(key, label, options):
    return {'key': key, 'label': label, 'type': 'choice', 'options': [{'value': v, 'label': l} for v, l in options]}


QUESTIONS = [
    question('vehicle_type', 'Qaysi transport vositasi sotilmoqda?', [('car', 'Avtomobil'), ('motorcycle', 'Mototsikl / motoaravacha / motoqayiq')]),
    {**question('transaction_kind','Transport sotilyaptimi yoki ayirboshlanyaptimi?', [('sale','Oldi-sotdi'),('exchange','Ayirboshlash')]), 'help':'Ayirboshlashda boj faqat bitta transport uchun olinadi. Transportlar turi farq qilsa, qiymati yuqori bo‘lgan transport turini tanlang. Asos: 4-band “o” izohi va 20-modda.'},
    question('relative_type', 'Xaridor mulkdorga kim bo‘ladi?', [('spouse', 'Er yoki xotin'), ('parent', 'Ota yoki ona'), ('child', 'Farzand'), ('spouse_parent', 'Turmush o‘rtog‘ining ota-onasi'), ('child_spouse', 'Farzandning eri yoki xotini'), ('grandchild', 'Nabira'), ('grandparent', 'Buvi yoki buva'), ('sibling', 'Aka-uka yoki opa-singil'), ('other', 'Boshqa shaxs / boshqa qarindosh')]),
    {**question('bank_credit', 'Avtomobil bank krediti hisobidan sotib olinadimi?', [('no', 'Yo‘q'), ('yes', 'Ha, bank krediti bilan')]), 'when':{'transaction_kind':['sale']}},
    question('damaged', 'Transport yo‘l-transport hodisasida shikastlanganmi?', [('no', 'Yo‘q'), ('yes', 'Ha, shikastlangan')]),
    {**question('damage_assessed', 'Ekspert yaroqlilik foizini belgilaganmi?', [('yes', 'Ha, ekspert xulosasi bor'), ('no', 'Yo‘q, hali belgilanmagan')]), 'when':{'damaged':['yes']}, 'help':'Foizni o‘zingiz taxmin qilmang. Notarius topshirig‘i bo‘yicha ekspert belgilagan qoldiq yaroqlilik foizi kerak.'},
    {'key':'residual_percent','label':'Ekspert belgilagan qoldiq yaroqlilik foizi','type':'number','min':0,'max':100,'step':0.0001,'when':{'damaged':['yes'],'damage_assessed':['yes']},'help':'Masalan, xulosada 60% bo‘lsa, 60 kiriting. Bu shikastlanish foizi emas, qolgan yaroqlilik foizi.','source_url':LAW+'#-8113528'},
    question('location', 'Bitim qayerda tasdiqlanadi?', [('office', 'Notarial idorada'), ('outside', 'Idoradan tashqarida'), ('outreach', 'Mahalladagi sayyor qabulda')]),
    question('special_status', '11-modda bo‘yicha imtiyozni tanlang', [('none', 'Bu imtiyozlar menga tegishli emas'), ('disability_organization', 'Nogironligi bo‘lgan shaxslar tashkiloti'), ('islamic_finance', 'Islomiy bank yoki mikromoliya tashkiloti mulk olyapti')]),
    party_question(['disability_organization','islamic_finance']),
]

# Ask legal capacity before kinship so incompatible branches cannot be combined.
status_question = next(q for q in QUESTIONS if q['key'] == 'special_status')
QUESTIONS.remove(status_question)
QUESTIONS.insert(1, status_question)
next(q for q in QUESTIONS if q['key'] == 'relative_type')['when'] = {'special_status':['none']}


configure_notarial_questions(QUESTIONS)


def missing_question(answers: Answers):
    return next((q for q in QUESTIONS if all(getattr(answers,key) in values for key,values in q.get('when',{}).items()) and getattr(answers, q['key']) is None), None)


def calculate(answers: Answers, rule, as_of: date):
    sources = [{'title': 'Davlat boji to‘g‘risidagi qonun', 'article': 'Ilova, 4-band “o” kichik bandi; 20-modda', 'url': LAW}, {'title': 'Notarial harakatlar reglamenti', 'article': '726-son qaror, 2-ilova', 'url': REGULATION}]
    base = {
        'service_id': 'notary_car', 'title': 'Avtomobil oldi-sotdisi', 'status': 'needs_verification',
        'payable_amount': None, 'standard_amount': None, 'saving_amount': None, 'currency': 'UZS',
        'benefit_title': 'Alohida tekshiruv kerak', 'legal_basis': sources,
        'next_steps': ['Notariusga bitim holati va imtiyozni tasdiqlovchi ma’lumotlarni taqdim eting.'],
        'other_costs_note': 'Faqat davlat boji hisoblanadi. Gerb yig‘imi, huquqiy-texnik xizmatlar va YHXX xarajatlari kiritilmagan.',
        'is_demo': False, 'verified_at': None, 'as_of_date': str(as_of), 'rule_version': None,
        'components': [{'name': 'Gerb yig‘imi', 'amount': None, 'note': 'Gerbli blankada chop etilganda; alohida aniqlanadi.'}, {'name': 'Huquqiy va texnik xizmatlar', 'amount': None, 'note': 'Bajarilgan harakatlar bo‘yicha alohida aniqlanadi.'}],
    }
    if not rule:
        return {**base, 'explanation': 'Tanlangan sana uchun e’lon qilingan qoida yo‘q. Summa taxmin qilinmadi.'}
    config = RuleConfig.model_validate(rule['config'])
    base.update(rule_version=rule['id'], verified_at=str(config.verified_at))
    sources[0].update(article=config.law_article, url=config.law_url)
    sources.append({'title': 'BHM manbasi', 'article': 'BHM miqdori va amal qilish sanasi', 'url': config.bhm_source_url})
    if answers.damaged == 'yes' and (answers.damage_assessed != 'yes' or answers.residual_percent is None):
        return {**base, 'explanation': 'YTHda shikastlangan transport uchun notarius topshirig‘i bo‘yicha ekspert belgilagan qoldiq yaroqlilik foizi kerak. Foiz taxmin qilinmadi.'}
    if answers.special_status == 'needs_review':
        return {**base, 'explanation': 'Qo‘shimcha shaxsiy imtiyoz maqomingiz notarius tomonidan tekshirilishi kerak. Uni avtomatik rad etmaymiz yoki tasdiqlamaymiz.'}
    relative = answers.relative_type in RELATIVES
    combined = relative and answers.bank_credit == 'yes'
    if answers.damaged == 'yes' and (relative or answers.bank_credit == 'yes'):
        return {**base, 'explanation':'YTH bo‘yicha ekspert foizi bilan qarindoshlik yoki bank krediti birga tanlangan. Qonunda bu asoslarni birlashtirish ketma-ketligi aniq belgilanmagan; ular ko‘paytirilmadi.'}
    multiplier = config.car_bhm_multiplier if answers.vehicle_type == 'car' else config.motorcycle_bhm_multiplier
    location_multiplier = config.outside_multiplier if answers.location == 'outside' else Decimal(1)
    standard = Decimal(config.bhm_amount) * multiplier * location_multiplier
    percent = config.relative_pay_percent + config.bank_pay_percent if combined else config.relative_pay_percent if relative else config.bank_pay_percent if answers.bank_credit == 'yes' else Decimal(100)
    if percent > 100:
        return {**base, 'explanation':'Admin kiritgan ikki to‘lov ulushining yig‘indisi 100%dan oshdi. Stavka sozlamalarini to‘g‘rilash kerak.'}
    residual = Decimal(answers.residual_percent) / 100 if answers.damaged == 'yes' else Decimal(1)
    payable = standard * percent / 100 * residual
    # Keep explicit precision; never silently label a fractional amount as an exact integer fee.
    if payable != payable.to_integral_value() or standard != standard.to_integral_value():
        return {**base, 'explanation': 'Stavka natijasida kasr so‘m hosil bo‘ldi. Yaxlitlash tartibi tasdiqlanmaguncha aniq summa chiqarilmaydi.'}
    standard, payable = int(standard), int(payable)
    benefit = relative or answers.bank_credit == 'yes' or residual < 1
    reason = 'Qonunda sanalgan qarindoshga o‘tkazish' if relative else 'Bank krediti hisobidan sotib olish' if answers.bank_credit == 'yes' else 'Umumiy stavka'
    explanation = f'BHM {config.bhm_amount:,} so‘m × {multiplier} × joy koeffitsiyenti {location_multiplier}. {reason}: belgilangan bojning {percent}%i to‘lanadi.'
    parts = []
    if combined:
        for label, rate in [('Qarindoshlik bo‘yicha',config.relative_pay_percent),('Bank krediti bo‘yicha',config.bank_pay_percent)]:
            amount = Decimal(standard) * rate / 100
            if amount != amount.to_integral_value():
                return {**base,'explanation':'Alohida boj qismida kasr so‘m hosil bo‘ldi. Qismlar yashirin yaxlitlanmadi.'}
            parts.append({'name':label,'pay_percent':str(rate),'amount':int(amount)})
        explanation = f'Qarindoshlik bo‘yicha: {standard:,} × {config.relative_pay_percent}% = {parts[0]["amount"]:,} so‘m. Bank krediti bo‘yicha: {standard:,} × {config.bank_pay_percent}% = {parts[1]["amount"]:,} so‘m. Jami: {parts[0]["amount"]:,} + {parts[1]["amount"]:,} = {payable:,} so‘m.'
    if answers.transaction_kind == 'exchange':
        explanation += ' Ayirboshlashda davlat boji faqat bitta transport vositasi uchun hisoblandi; ikki transport uchun qo‘shilmadi. Turli mulk almashilsa, qiymati yuqori bo‘lgan mulk hisobga olinadi (20-modda).'
    if answers.damaged == 'yes':
        explanation += f' Ekspert xulosasidagi qoldiq yaroqlilik {answers.residual_percent}%: hisoblangan boj shu ulushga ko‘paytirildi.'
    return {**base, 'status': 'discounted' if benefit else 'standard', 'payable_amount': payable, 'standard_amount': standard, 'saving_amount': standard-payable,
            'arithmetic':[f'{config.bhm_amount} × {multiplier} × {location_multiplier} = {standard}',
                          *([f"{standard} × {part['pay_percent']}% = {part['amount']}" for part in parts] + [f"{parts[0]['amount']} + {parts[1]['amount']} = {payable}"] if combined else [f'{standard} × {percent}% × {residual} = {payable}'])],
            'duty_breakdown':parts, 'interpretation_note':'Ikki asosni qo‘shib hisoblash: hakatondagi notarius mentor izohi asosida.' if combined else None,
            'benefit_title': f'Qoldiq yaroqlilik: {answers.residual_percent}%' if answers.damaged == 'yes' else f'Belgilangan bojning {percent}%i to‘lanadi' if benefit else 'Umumiy stavka qo‘llanildi', 'explanation': explanation,
            'formula': {'bhm_amount': config.bhm_amount, 'bhm_multiplier': str(multiplier), 'location_multiplier': str(location_multiplier), 'pay_percent': str(percent),'transaction_kind':answers.transaction_kind,'charged_vehicle_count':1,'residual_percent':str(answers.residual_percent) if answers.damaged=='yes' else None},
            'next_steps': ['Shaxs va transportga oid hujjatlarni tayyorlang.', 'Qarindoshlik yoki bank krediti asosini tasdiqlovchi ma’lumotlarni notariusga ko‘rsating.' if benefit else 'Bitimni rasmiylashtirish uchun notariusga murojaat qiling.', 'Davlat bojidan tashqari gerb yig‘imi va huquqiy-texnik xizmatlar hisobini alohida so‘rang.']}
