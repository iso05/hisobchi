"""State duty for one inheritance object and one documented beneficiary share."""
from fractions import Fraction

from fastapi import HTTPException

from .catalog import BY_ID


def calculate_inheritance(answers, parameters, bhm, result):
    definitions = BY_ID['notary_inheritance']['sources']
    refs = [definitions[0], definitions[7]]
    notes = []
    documents = ['Merosxo‘r ulushini ko‘rsatuvchi hujjatni notariusga taqdim eting.']
    result = {**result, 'next_steps': documents}

    def add_ref(index):
        if definitions[index] not in refs:
            refs.append(definitions[index])

    def finish_sources():
        extras = [s for s in result['legal_basis'] if s.get('title') in {'Admin tasdiqlagan stavka manbasi','BHM manbasi'}]
        return refs + extras

    def unknown(message):
        return {**result, 'explanation':message, 'formula_steps':notes, 'legal_basis':finish_sources()}

    def share(numerator, denominator, label):
        if numerator > denominator:
            raise HTTPException(422, f'{label} 1 dan katta bo‘lishi mumkin emas.')
        return Fraction(numerator, denominator)

    heir_share = share(answers['share_numerator'], answers['share_denominator'], 'Merosxo‘r ulushi')
    estate_share = Fraction(1)
    if answers['joint_property'] == 'yes':
        estate_share = share(answers['estate_numerator'], answers['estate_denominator'], 'Merosga kiradigan qism')
        add_ref(11)
        notes.append(f'Er-xotin umumiy mulkining faqat {estate_share} qismi merosga kiradi; tirik turmush o‘rtog‘ining o‘z mulki qo‘shilmadi.')

    kind = answers['property_type']
    rate_key = 'real_vehicle_bhm' if kind in {'home','real_estate','vehicle'} else 'other_bhm'
    rate = Fraction(parameters[rate_key])
    location = Fraction(parameters['outside_multiplier']) if answers['location'] == 'outside' else Fraction(1)
    if answers['location'] != 'office':
        add_ref(13)
        notes.append('Idoradan tashqarida boj oshirildi.' if answers['location']=='outside' else 'Mahalla organi binosidagi sayyor qabul: boj oshirilmadi.')
    baseline = Fraction(bhm) * rate * estate_share * heir_share * location
    notes.append(f'{bhm} so‘m BHM × {rate} stavka × {estate_share} merosga kiradigan qism × {heir_share} merosxo‘r ulushi × {location} joy koeffitsiyenti.')

    exemption = None
    if answers.get('minor')=='yes':
        exemption = 'Merosxo‘r voyaga yetmagan — ushbu ulush uchun davlat boji olinmaydi.'
        add_ref(8)
        documents.append('Merosxo‘rning yoshini tasdiqlovchi hujjat kerak.')
    special = answers['special_status']
    special_rules = {
        'duty_death':(1, '11-modda 5-band: xizmat yoki fuqarolik burchini bajarishda halok bo‘lgan shaxs mol-mulki.'),
        'guardianship':(4, '11-modda 11-band: surunkali ruhiy kasallik va qonuniy vasiylik shartlari.'),
        'farmer':(6, '11-modda 15-band: fermer xo‘jaligi mulki va faoliyatni davom ettirish.'),
        'dehkan':(6, '11-modda 16-band: dehqon xo‘jaligi mulki va faoliyatni davom ettirish.'),
        'state_authority':(2, '11-modda 3-band: davlat merosi uchun soliq yoki moliya organi.'),
        'disability_organization':(2, '11-modda 4-band: nogironligi bo‘lgan shaxslar jamoat birlashmasi va qonunda sanalgan tashkilotlari.'),
    }
    if special in special_rules:
        index, reason = special_rules[special]
        add_ref(index)
        exemption = reason
        documents.append('Tanlangan imtiyozning barcha shartlarini tasdiqlovchi hujjatlar kerak.')

    asset_exemptions = {
        'deposit':'Bank omonati', 'salary':'Ish haqi', 'pension':'Shaxsiy jamg‘arib boriladigan pensiya hisobi',
        'government_bond':'Davlat zayom obligatsiyasi', 'insurance':'Shaxsiy yoki mulkiy sug‘urta summasi',
        'copyright':'Muallif yoki ijrochining qonunda sanalgan mulkiy huquqi',
        'royalty':'Asar, ixtiro yoki ijroni yaratish va undan foydalanish haqi',
    }
    if kind in asset_exemptions:
        add_ref(1)
        exemption = f'11-modda 5-band: {asset_exemptions[kind]} bo‘yicha meros guvohnomasi davlat bojidan ozod.'
        documents.append('Mablag‘ yoki huquq aynan tanlangan toifaga kirishini tasdiqlang.')
    if kind=='passenger_insurance':
        add_ref(5)
        exemption = '11-modda 14-band: yo‘lovchi yoki fuqaroga tegishli mol-mulkning majburiy sug‘urtasi to‘lovi.'
    if kind=='work_insurance':
        add_ref(3)
        if answers['work_policy']=='yes':
            exemption = '11-modda 10-band: ishdagi baxtsiz hodisadan vafot etish uchun korxona hisobidan sug‘urta.'
        elif exemption is None:
            return unknown('Korxona hisobidan sug‘urta sharti tasdiqlanmagan. Sug‘urta hujjatlarini tekshiring; shaxsiy yoki mulkiy sug‘urta bo‘lsa, mos mulk turini tanlang.')
    if kind in {'home','housing_coop'} and answers.get('minor')=='no' and special=='none':
        conditions = ['lived_before','registered','lives_after']
        if all(answers.get(key)=='yes' for key in conditions):
            add_ref(1)
            exemption = '11-modda 5-band: vafotgacha birga yashash, doimiy ro‘yxat va vafotdan keyin yashash — uchala shart bajarilgan.'
            documents.append('Birga yashash va doimiy ro‘yxat shartlarini tasdiqlovchi ma’lumotlar kerak.')
        else:
            notes.append('Uy-joy imtiyozi qo‘llanmadi: uchta yashash/ro‘yxat shartining hammasi bajarilmagan.')
    if kind=='credit_certificate':
        add_ref(12)
        notes.append('Kredit tashkiloti sertifikati va akkreditivga bank omonati imtiyozi qo‘llanmadi; umumiy tartib.')

    certificate = answers['certificate_kind']
    prior = 0
    if certificate in {'partial','remaining'}:
        add_ref(9)
        notes.append('Faqat guvohnomada ko‘rsatiladigan qism hisoblanadi.' if certificate=='partial' else 'Hisob oldingi va yangi guvohnomalardagi jami qamraladigan ulush uchun; oldingi tasdiqlangan to‘lov keyin ayriladi.')
    if certificate=='court_reissue':
        add_ref(10)
        notes.append('Sud eski guvohnomani haqiqiy emas deb topganidan keyingi guvohnoma umumiy tartibda hisoblanadi.')
    if certificate in {'remaining','court_reissue'}:
        if answers['credit_confirmed']!='yes' and exemption is None:
            return unknown('Oldingi to‘lovni hisobga olish miqdori va hujjatlari hali tekshirilmagan. Yakuniy to‘lov taxmin qilinmadi.')
        prior = answers.get('previous_payment',0)
        documents.append('Oldingi guvohnoma va davlat boji kvitansiyasini ko‘rsating. Suddan keyingi holatda sud qarori, hisobga olish arizasi va da’vo muddati sharti ham tekshiriladi.')

    duty = Fraction(0) if exemption else baseline
    if not exemption and Fraction(prior) > duty:
        raise HTTPException(422, 'Oldingi to‘lov hisoblangan jami bojdan katta. Ulush va hisobga olinadigan summani notarius bilan tekshiring.')
    credit = Fraction(0) if exemption else Fraction(prior)
    payable = duty - credit
    if exemption:
        notes.append(exemption)
        if prior:
            notes.append('Oldingi to‘lovni qaytarish masalasi alohida ko‘riladi; avtomatik qaytarish hisoblanmadi.')
    if credit:
        notes.append(f'{prior} so‘m oldingi to‘lov hisobga olindi. Bu imtiyoz yoki tejalgan pul emas.')
    result['arithmetic'] = [f'{bhm} × {rate} × {estate_share} × {heir_share} × {location} = {baseline}']
    if exemption:
        result['arithmetic'].append(f'{baseline} × 0% = 0')
    elif credit:
        result['arithmetic'].append(f'{baseline} − {credit} = {payable}')
    if payable.denominator != 1:
        return {**unknown('Kasr so‘m hosil bo‘ldi. Yaxlitlash tartibi tasdiqlanmaguncha yakuniy summa berilmaydi.'), 'unrounded_payable':str(payable)}
    baseline_amount = int(baseline) if baseline.denominator==1 else None
    return {**result, 'status':'exempt' if exemption else 'credit_applied' if credit else 'standard',
            'standard_amount':baseline_amount, 'payable_amount':int(payable),
            'saving_amount':baseline_amount if exemption else 0,
            'total_duty_amount':int(duty) if duty.denominator==1 else None,
            'previous_payment_credit':int(credit),
            'benefit_title':'Davlat bojidan ozod' if exemption else 'Oldingi to‘lov hisobga olindi' if credit else 'Umumiy stavka qo‘llandi',
            'explanation':' '.join(notes), 'formula_steps':notes, 'legal_basis':finish_sources()}
