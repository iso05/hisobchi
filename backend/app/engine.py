from datetime import date
from decimal import Decimal, InvalidOperation

from fastapi import HTTPException
from pydantic import ValidationError

from .catalog import BY_ID, applies
from .calculator import calculate as calculate_car, missing_question as car_missing, QUESTIONS, today
from .models import Answers, RuleConfig, RELATIVES
from .inheritance import calculate_inheritance
from .notarial import apply_notarial_exemption, normalize_notarial_answers


def prepare_answers(service_id, raw):
    if service_id not in BY_ID:
        raise HTTPException(404, 'Kalkulyator topilmadi.')
    raw = normalize_notarial_answers(service_id, raw)
    if service_id == 'notary_car':
        try:
            return Answers.model_validate(raw).model_dump(exclude_none=True, mode='json')
        except ValidationError:
            raise HTTPException(422,'Avtomobil kalkulyatori javoblari noto‘g‘ri.')
    questions = BY_ID[service_id]['questions']
    if not isinstance(raw, dict) or set(raw) - {q['key'] for q in questions}:
        raise HTTPException(422, 'Javob maydonlari ushbu kalkulyatorga mos emas.')
    clean = {}
    for q in questions:
        value = raw.get(q['key'])
        if value is None or value == '':
            continue
        if q['type'] == 'choice':
            if not isinstance(value,str) or value not in {o['value'] for o in q['options']}:
                raise HTTPException(422, f"{q['label']} — variant noto‘g‘ri.")
        elif isinstance(value, bool) or not isinstance(value, int) or not q['min'] <= value <= q['max']:
            raise HTTPException(422, f"{q['label']} — {q['min']} dan {q['max']} gacha butun son kiriting.")
        clean[q['key']] = value
    return clean


def get_questions(service_id):
    return QUESTIONS if service_id == 'notary_car' else BY_ID[service_id]['questions']


def missing_question(service_id, answers):
    if service_id == 'notary_car':
        return car_missing(Answers.model_validate(answers))
    return next((q for q in get_questions(service_id) if applies(q,answers) and q['key'] not in answers),None)


def validate_parameters(service_id, values):
    expected = {p['key']: p for p in BY_ID[service_id]['parameters']}
    if set(values) != set(expected):
        raise HTTPException(422, 'Stavka maydonlari kalkulyatorga mos emas.')
    for key,value in values.items():
        field = expected[key]
        try:
            number = Decimal(str(value))
        except InvalidOperation:
            raise HTTPException(422, f"{field['label']}: son kiriting.")
        if not number.is_finite() or not Decimal(field['min']) <= number <= Decimal(field['max']):
            raise HTTPException(422, f"{field['label']}: qiymat chegaradan tashqarida.")
        if field['unit'] == 'son' and number != number.to_integral_value():
            raise HTTPException(422, f"{field['label']}: butun son bo‘lishi kerak.")


def calculate(service_id, answers, rule, as_of: date):
    unknown_benefit = answers.get('special_status') == 'unsure'
    if unknown_benefit:
        answers = {**answers, 'special_status':'none'}
    result = calculate_fee(service_id, answers, rule, as_of)
    if unknown_benefit:
        result['benefit_unspecified'] = True
    return result


def calculate_fee(service_id, answers, rule, as_of):
    definition = BY_ID[service_id]
    if service_id == 'notary_car':
        result = calculate_car(Answers.model_validate(answers),rule,as_of)
        sources = [s for s in result['legal_basis'] if s['url'].split('#')[0] != 'https://lex.uz/docs/-5109530']
        result = {**result,'legal_basis': sources + definition['sources'] if rule else definition['sources'],'review_note':definition['review_note'],'review_status':'source_compared'}
        return apply_notarial_exemption(result,answers,service_id) if rule else result
    cfg = rule['config'] if rule else {}
    params = {key:Decimal(str(value)) for key,value in cfg.get('parameters',{}).items()}
    notary = definition['category'] == 'Notarial'
    result = {
        'service_id': service_id,'title':definition['name'],'status':'needs_verification','payable_amount':None,'standard_amount':None,'saving_amount':None,'currency':'UZS',
        'benefit_title':'Alohida tekshiruv kerak','explanation':'','legal_basis':definition['sources'] + ([{'title':'Admin tasdiqlagan stavka manbasi','article':cfg['law_article'],'url':cfg['law_url']},{'title':'BHM manbasi','article':'BHM miqdori va kuchga kirish sanasi','url':cfg['bhm_source_url']}] if rule else []),
        'next_steps':['Natija bilan birga ko‘rsatilgan qonun bandlarini tekshiring.','Imtiyoz asosini tasdiqlovchi ma’lumotlarni tegishli organga taqdim eting.'],
        'other_costs_note': 'Faqat davlat boji. Gerb yig‘imi va huquqiy-texnik xizmatlar alohida.' if notary else 'Faqat davlat boji. Pochta va boshqa sud xarajatlari alohida.' if definition['category']=='Sud' else 'Faqat tanlangan bosqich davlat boji; boshqa bosqichlar xarajatlari kiritilmagan.',
        'components':[{'name':'Gerb yig‘imi' if notary else 'Boshqa xarajatlar','amount':None,'note':'Alohida aniqlanadi; nol deb olinmagan.'}],
        'is_demo':False,'verified_at':cfg.get('verified_at'),'as_of_date':str(as_of),'rule_version':rule['id'] if rule else None,
        'review_note':definition['review_note'],'review_status':'source_compared' if notary else 'awaiting_legal_review','formula_steps':[],
    }
    def unknown(text):
        return {**result,'explanation':text}
    if not rule:
        return unknown('Tanlangan sanaga tegishli qoida kiritilmagan. Summa taxmin qilinmadi.')
    validate_parameters(service_id, params)
    bhm = Decimal(cfg['bhm_amount'])
    p = lambda key: params[key]
    if answers.get('special_status') == 'needs_review':
        return unknown('Boshqa shaxsiy yoki tashkilot imtiyozi ko‘rsatilgan. Uni qonun bandi va tasdiqlovchi ma’lumot bilan alohida tekshirish kerak.')
    location = p('outside_multiplier') if notary and answers.get('location') == 'outside' else Decimal(1)
    relative = answers.get('relative_type') in RELATIVES
    standard = payable = Decimal(0)
    notes = []
    arithmetic = []
    if service_id == 'notary_property':
        multiplier = p('center_bhm') if answers['region'] in {'tashkent','nukus','capital'} else p('other_bhm')
        standard = bhm * multiplier * location
        if answers['transaction'] == 'foreign_new':
            if relative:
                return unknown('Maxsus xorijiy xarid va qarindoshlik birga ko‘rsatilgan. Ikki asosni birlashtirish tartibi tekshirilishi kerak.')
            area = answers.get('special_area')
            if area not in {'tashkent_city','tashkent_region'} or answers['region']=='nukus' or (answers['region']=='tashkent') != (area=='tashkent_city') or Decimal(answers['contract_amount']) < bhm*p('foreign_threshold_bhm'):
                return unknown('4-band “b”dagi maxsus hudud/narx shartlari to‘liq bajarilmadi. Ushbu bitimni umumiy stavkaga avtomatik o‘tkazmaymiz.')
            if answers.get('special_status') in {'disability_organization','state_orphan_home','islamic_finance'}:
                return unknown('Maxsus xorijiy xaridor maqomi va tanlangan ozodlik asosi bir-biriga mosligi tekshirilishi kerak. Avtomatik summa berilmadi.')
            standard = Decimal(answers['contract_amount'])*p('foreign_price_percent')/100*location
            payable = standard
            notes.append(f"Maxsus bitim: shartnoma narxi × {p('foreign_price_percent')}% × joy koeffitsiyenti {location}.")
        elif answers['transaction'] == 'resale_special' and answers['resale_period'] == 'within':
            if relative:
                return unknown('Maxsus qayta sotuv va qarindoshlik imtiyozi birga. Alohida huquqiy tekshiruv kerak.')
            standard = payable = bhm*p('resale_bhm')*location
            notes.append(f"4-band “v”: {p('resale_bhm')} BHM × joy koeffitsiyenti {location}.")
        else:
            payable = standard * (p('relative_pay_percent')/100 if relative else 1)
            arithmetic.append(f"{bhm} × {multiplier} × {location} × {p('relative_pay_percent') if relative else 100}% = {payable}")
            notes.append(f"BHM × hudud stavkasi {multiplier} × joy koeffitsiyenti {location}; qarindoshlik bo‘lsa {p('relative_pay_percent')}%i to‘lanadi.")
        exemption = answers.get('special_status')
        property_exemptions = {'disability_organization':'11-modda 4-band', 'state_orphan_home':'11-modda 19-band', 'islamic_finance':'11-modda 20-band'}
        if exemption in property_exemptions:
            if exemption == 'state_orphan_home' and answers['transaction'] != 'ordinary':
                return unknown('19-banddagi davlat ikkilamchi bozordan olgan uy-joy sharti tanlangan maxsus bitim turiga mos emas. Holatni tekshiring.')
            notes.append(f"{property_exemptions[exemption]}: ozodlik bitim taraflari bo‘yicha alohida tekshiriladi.")
    elif service_id in {'notary_vehicle_power','notary_property_power'}:
        eligible = relative or service_id == 'notary_vehicle_power' and answers['relative_type']=='nephew_niece'
        standard = bhm*p('other_bhm')*location
        payable = bhm*(p('relative_bhm') if eligible else p('other_bhm'))*location
        arithmetic.append(f"{bhm} × {p('relative_bhm') if eligible else p('other_bhm')} × {location} = {payable}")
        notes.append(f"BHM × {'qarindosh' if eligible else 'umumiy'} stavka {p('relative_bhm') if eligible else p('other_bhm')} × joy koeffitsiyenti {location}.")
    elif service_id == 'notary_lease':
        base_rate = p('legal_bhm') if answers['party_type']=='legal' else p('individual_bhm')
        cancel = p('cancel_pay_percent')/100 if answers['operation']=='cancel' else Decimal(1)
        standard = bhm*base_rate*location*cancel
        payable = bhm*(p('relative_bhm') if relative and answers['party_type']=='individual' else base_rate)*location*cancel
        arithmetic.append(f"{bhm} × {p('relative_bhm') if relative and answers['party_type']=='individual' else base_rate} × {location} × {cancel} = {payable}")
        notes.append(f"BHM × tarafga tegishli stavka × joy koeffitsiyenti {location} × harakat ulushi {cancel}.")
        if relative:
            notes.append(f"Qonundagi qarindoshlar uchun stavka {p('relative_bhm')} BHM.")
    elif service_id == 'notary_inheritance':
        return calculate_inheritance(answers, params, bhm, result)
    elif service_id in {'court_civil','court_economic'}:
        if answers['mixed_claims']=='yes':
            return unknown('Aralash / xorijiy valyutadagi talablar har bir qismi bo‘yicha alohida baholanadi. Bitta summadan yakuniy hisob berilmadi.')
        if service_id=='court_civil' and answers['claim_type']!='debt':
            if answers['stage']!='first':
                return unknown('Imtiyozli talabning shikoyat bosqichidagi qo‘llanishi alohida tekshiriladi.')
            result.update(status='exempt',payable_amount=0,benefit_title='Davlat bojidan ozod qilish',explanation='Tanlangan talab uchun 8-moddadagi tegishli ozodlik asosi ko‘rsatiladi. Talab aynan shu turga kirishini tasdiqlash kerak.')
            result['formula_steps']=['8-modda: tanlangan talab bo‘yicha da’vogardan davlat boji undirilmaydi.']
            return result
        standard = max(Decimal(answers['claim_amount'])*p('claim_percent')/100,bhm*p('minimum_bhm'))
        if service_id=='court_economic' and answers['small_business']=='yes' and answers['stage']=='appeal':
            return unknown('Kichik biznes va shikoyatning ikki 50% ulushini avtomatik ko‘paytirmaymiz. Birgalikda qo‘llanishi tekshirilishi kerak.')
        stage_factor = p('appeal_pay_percent')/100 if answers['stage']=='appeal' else Decimal(1)
        standard *= stage_factor
        payable = standard*(p('small_business_pay_percent')/100 if service_id=='court_economic' and answers['small_business']=='yes' else 1)
        arithmetic.append(f"max({answers['claim_amount']} × {p('claim_percent')}%, {bhm * p('minimum_bhm')}) × {stage_factor} × {p('small_business_pay_percent') if service_id == 'court_economic' and answers['small_business'] == 'yes' else 100}% = {payable}")
        notes.append(f"max(da’vo summasi × {p('claim_percent')}%, BHM × {p('minimum_bhm')}) × bosqich ulushi {stage_factor}.")
        if service_id=='court_economic' and answers['small_business']=='yes':
            notes.append(f"Kichik biznes uchun {p('small_business_pay_percent')}%i to‘lanadi.")
    elif service_id == 'court_divorce':
        arithmetic = notes
        standard = bhm * p(answers['marriage'])
        notes.append(f"{bhm} × {p(answers['marriage'])} = {standard}")
        if answers['division'] == 'yes':
            amount = Decimal(answers['claim_amount'])
            property_fee = max(amount * p('claim_percent') / 100, bhm * p('minimum_bhm'))
            notes.append(f"max({amount} × {p('claim_percent')}%, {bhm} × {p('minimum_bhm')}) = {property_fee}")
            notes.append(f"{standard} + {property_fee} = {standard + property_fee}")
            standard += property_fee
        payable = standard
    elif service_id in {'court_copies', 'court_economic_filing', 'court_nonproperty', 'court_special_proceeding'}:
        arithmetic = notes
        if service_id == 'court_copies':
            units = p('page_bhm') * answers['pages']
            notes.append(f"{p('page_bhm')} × {answers['pages']} = {units}")
        elif service_id == 'court_economic_filing':
            units = p(answers['filing'])
        else:
            units = p('base')
        standard = bhm * units
        percent = p('business_percent') if answers.get('business_relief') == 'yes' else Decimal(100)
        if service_id == 'court_special_proceeding' and answers['fact'] != 'ordinary':
            percent = Decimal(0)
        payable = standard * percent / 100
        notes.append(f"{bhm} × {units} × {percent}% = {payable}")
    elif service_id=='vehicle_power_electronic':
        if answers['recipient']=='relative':
            return unknown('Qarindosh/jiyan uchun notarial tarif va elektron xizmat bazasining munosabati qo‘lda tekshirilishi kerak. Qarindoshlikni inkor qilib umumiy summa berilmadi.')
        if answers['benefit_category'] in {'registry','multiple'}:
            return unknown('Reyestr yoki bir nechta imtiyoz asosining elektron xizmatda qo‘llanishi tekshirilishi kerak. Qo‘shimcha portal chegirmasi avtomatik qo‘shilmadi.')
        duration_rate = p({'one_month':'one_month_percent','six_months':'six_months_percent','three_years':'three_years_percent'}[answers['duration']])
        standard = bhm*p('base_bhm')*duration_rate/100
        payable = standard*(p('disability_pay_percent')/100 if answers['benefit_category']=='disability' else 1)
        arithmetic.append(f"{bhm} × {p('base_bhm')} × {duration_rate}% × {p('disability_pay_percent') if answers['benefit_category']=='disability' else 100}% = {payable}")
        notes.append(f"BHM × notarial baza {p('base_bhm')} × muddat ulushi {duration_rate}%.")
        if answers['benefit_category']=='disability':
            notes.append(f"Reglamentdagi I–II guruh imtiyozi: {p('disability_pay_percent')}%i to‘lanadi.")
    elif service_id=='patent_application':
        individual = answers['applicant_type']=='individual'
        prefix = 'individual' if individual else 'legal'
        benefit = answers.get('individual_benefit') if individual else answers.get('legal_benefit')
        if benefit=='multiple':
            return unknown('Bir nechta talabgor yoki imtiyoz asosini birgalikda qo‘llash tartibi tekshirilishi kerak.')
        units = p(f'{prefix}_base_bhm') + (Decimal(answers['object_count'])-1)*p(f'{prefix}_extra_bhm')
        pages = max(0,Decimal(answers.get('description_pages',0))-p('page_limit')) if answers['object_type']=='invention' else Decimal(0)
        units += pages*p(f'{prefix}_page_bhm')
        standard = bhm*units
        pay = p('disability_pay_percent') if benefit=='disability2' else p('education_pay_percent') if benefit=='education' else p('organization_pay_percent') if benefit=='small_or_education' else Decimal(100)
        payable = standard*pay/100
        arithmetic.append(f"{p(f'{prefix}_base_bhm')} + ({answers['object_count']} − 1) × {p(f'{prefix}_extra_bhm')} + {pages} × {p(f'{prefix}_page_bhm')} = {units}")
        arithmetic.append(f"{bhm} × {units} × {pay}% = {payable}")
        notes.append(f"Birinchi obyekt + qo‘shimcha obyektlar + {pages} ortiqcha ixtiro varag‘i = {units} BHM.")
        notes.append(f"23-modda bo‘yicha hisoblangan bojning {pay}%i to‘lanadi. Faqat talabnoma bosqichi.")
    result['arithmetic'] = arithmetic
    if standard > 10**15 or payable > 10**15:
        return unknown('Hisoblangan summa kalkulyatorning ishchi chegarasidan oshdi. Uni alohida tekshirish kerak.')
    if payable == 0 and standard != standard.to_integral_value():
        return {**result,'status':'exempt','payable_amount':0,'benefit_title':'Davlat bojidan ozod qilish','explanation':' '.join(notes),'formula_steps':notes}
    if standard != standard.to_integral_value() or payable != payable.to_integral_value():
        return {**unknown('Kasr so‘m hosil bo‘ldi. Qonuniy yaxlitlash tartibi jamoa tomonidan tekshirilmaguncha yakuniy butun summa berilmaydi.'),'formula_steps':notes,'unrounded_payable':str(payable)}
    standard,payable = int(standard),int(payable)
    output = {**result,'status':'exempt' if payable==0 else 'discounted' if payable<standard else 'standard','standard_amount':standard,'payable_amount':payable,'saving_amount':standard-payable,
            'benefit_title':'Davlat bojidan ozod qilish' if payable==0 else 'Imtiyoz qo‘llandi' if payable<standard else 'Umumiy stavka qo‘llandi','explanation':' '.join(notes),'formula_steps':notes}
    return apply_notarial_exemption(output, answers, service_id) if notary else output
