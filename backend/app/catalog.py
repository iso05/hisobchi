"""Reviewed source locations, bounded service scopes and editable numeric parameters."""
from urllib.parse import urlsplit, unquote, quote

LAW = 'https://lex.uz/docs/-4680944'
BHM_SOURCE = 'https://lex.uz/docs/-8283656'
EPOWER_SOURCE = 'https://lex.uz/docs/-6672128'
REVIEW_NOTE = 'Jamoaning qonun matni bo‘yicha qo‘lda tekshiruvi kutilmoqda.'

# Native document element IDs from the official Lex.uz HTML, not browser text fragments.
SOURCE_ANCHORS = {
    'Nikohni bekor qilish bilan': '-4683015',
    'Ayirboshlash shartnomalari boʻyicha': '-4683327',
    '3) davlat soliq': '-4682487',
    '10) ishlab chiqarishdagi': '-8292760',
    '11) surunkali ruhiy': '-5590823',
    '14) shaxslar': '-4682738',
    '15) fermer': '-4682741',
    'Bir nechta merosxo': '-4683292',
    'Agar merosga': '-4828178',
    'Sudlarning ilgari': '-5590902',
    'Er-xotinning birgalikda': '-4683315',
    'Kredit tashkilotlari': '-4683313',
    'Notarial idora binosidan tashqarida': '-4828174',
    'Notarial harakatlar amalga oshirilganda': '-4682689',
    '5) shaxslar': '-4682702',
    'Voyaga yetmagan merosxo': '-4683295',
    'Fuqarolik ishlari boʻyicha sudlarda': '-4682417',
    'Iqtisodiy sudlarda davlat bojini': '-4682602',
    'Bir vaqtning oʻzida': '-4683011',
    'II guruh nogironligi boʻlgan shaxslarga 90': '-7685704',
    '15. Ishonchnomani': '-6673209',
    'I va II guruh nogironligi': '-6673220',
}


def source_anchor(text, base):
    return next((anchor for phrase, anchor in SOURCE_ANCHORS.items() if text.startswith(phrase)), '-8113528' if base == LAW else '')


def exact_source_url(base, text, anchor=None):
    anchor = source_anchor(text, base) if anchor is None else anchor
    return base + '#' + anchor + ':~:text=' + quote(text, safe='')


def working_source_url(url):
    """Resolve our old generated source URLs without rewriting stored rule versions."""
    if url == BHM_SOURCE:
        return exact_source_url(BHM_SOURCE, '(ii) bazaviy hisoblash miqdori', '-8283949')
    parts = urlsplit(url)
    if parts.hostname not in {'lex.uz', 'www.lex.uz'}:
        return url
    if parts.query not in {'', 'ONDATE=20.11.2026'} or not parts.fragment.startswith(':~:text='):
        return url
    base = f'{parts.scheme}://{parts.netloc}{parts.path}'
    text = unquote(parts.fragment.removeprefix(':~:text='))
    anchor = source_anchor(text, base)
    return exact_source_url(base, text, anchor)


def precise_result_sources(service_id, items):
    known = BY_ID[service_id]['sources']
    output, seen = [], set()
    for item in items:
        item = dict(item)
        parts = urlsplit(item['url'])
        base = f'{parts.scheme}://{parts.netloc}{parts.path}'
        match = next((s for s in known if s['article'] == item.get('article') and s['url'].split('#')[0] == base), None)
        # Old car rules combine the tariff and Article 20 in one label; Article 20
        # already has its own independent source in the catalog.
        if not match and base == LAW and not parts.query and item.get('article','').startswith('Ilova, 4-band “o”') and service_id == 'notary_car':
            match = known[0]
        if match:
            item = {**item, **match}
        else:
            item['url'] = working_source_url(item['url'])
        if base == BHM_SOURCE:
            item['find_text'] = '(ii) bazaviy hisoblash miqdori'
        if item['url'] not in seen:
            output.append(item)
            seen.add(item['url'])
    return output


def source(article, text, url=LAW):
    anchor = source_anchor(text, url)
    return {'title': 'Davlat boji to‘g‘risidagi qonun' if url == LAW else 'Elektron ishonchnoma reglamenti', 'article': article, 'url': exact_source_url(url,text,anchor), 'find_text': text}


def choice(key, label, options, when=None):
    return {'key': key, 'label': label, 'type': 'choice', 'options': [{'value': v, 'label': l} for v,l in options], **({'when': when} if when else {})}


def number(key, label, minimum=1, maximum=10**12, when=None):
    return {'key': key, 'label': label, 'type': 'number', 'min': minimum, 'max': maximum, **({'when': when} if when else {})}


def param(key, label, value, unit='BHM', minimum='0', maximum='10000'):
    return {'key': key, 'label': label, 'value': str(value), 'unit': unit, 'min': str(minimum), 'max': str(maximum)}


RELATIVES = [('spouse','Er yoki xotin'),('parent','Ota yoki ona'),('child','Farzand'),('spouse_parent','Turmush o‘rtog‘ining ota-onasi'),('child_spouse','Farzandning eri yoki xotini'),('grandchild','Nabira'),('grandparent','Buvi yoki buva'),('sibling','Aka-uka yoki opa-singil'),('other','Boshqa shaxs / boshqa qarindosh')]
LOCATION = choice('location','Notarial harakat qayerda bajariladi?', [('office','Notarial idorada'),('outside','Idoradan tashqarida'),('outreach','Mahalla binosidagi sayyor qabulda')])
SPECIAL = choice('special_status','Boshqa shaxsiy yoki tashkilot maqomi bo‘yicha imtiyoz bormi?', [('none','Boshqa imtiyoz haqida ma’lumotim yo‘q'),('needs_review','Ha yoki aniq bilmayman')])
OUTSIDE = param('outside_multiplier','Idoradan tashqaridagi koeffitsiyent',2,'koeffitsiyent',1,10)
S20 = source('20-modda, idoradan tashqaridagi harakatlar','Notarial idora binosidan tashqarida amalga oshiriladigan notarial harakatlar')
S11 = source('11-modda, notarial imtiyozlar','Notarial harakatlar amalga oshirilganda davlat bojini toʻlashdan quyidagilar ozod etiladi')
S8 = source('8-modda, da’vogarlar uchun ozodlik asoslari','Fuqarolik ishlari boʻyicha sudlarda davlat bojini toʻlashdan quyidagilar ozod qilinadi')
S9 = source('9-modda, iqtisodiy sud imtiyozlari','Iqtisodiy sudlarda davlat bojini toʻlashdan quyidagilar ozod qilinadi')
S23 = source('23-modda, ixtiro va foydali model imtiyozlari','II guruh nogironligi boʻlgan shaxslarga 90 foiz miqdorida')


def definition(id, name, category, description, sources, questions, parameters, scope, exceptions):
    note = 'Notarial stavka va shartlar Lex.uz matni bilan solishtirildi (20.11.2026). Hisob kiritilgan ma’lumotlarga asoslanadi.' if category == 'Notarial' else REVIEW_NOTE
    return {'id': id, 'name': name, 'category': category, 'description': description, 'icon': 'scale' if category == 'Sud' else 'car' if id in {'notary_car','vehicle_power_electronic'} else 'file', 'sources': sources, 'questions': questions, 'parameters': parameters, 'scope': scope, 'exceptions': exceptions, 'review_note': note}


CATALOG = [
    definition('notary_car','Avtomobil oldi-sotdisi','Notarial','Transport turi, qarindoshlik va bank krediti',
        [source('Ilova, 4-band “o” va izoh','o) avtomototransport vositalarini boshqa shaxsga oʻtkazish'), S20, S11, source('20-modda — ayirboshlashda qiymati yuqori mulk','Ayirboshlash shartnomalari boʻyicha davlat boji qiymati yuqori boʻlgan mol-mulkdan')], [], [],
        'Avtomobil va mototransportning notarial davlat boji.', ['YTH ekspert bahosi','Kredit va qarindoshlik birga bo‘lsa','Boshqa shaxsiy imtiyoz']),
    definition('notary_property','Ko‘chmas mulk oldi-sotdisi','Notarial','Hudud, qarindoshlik va maxsus bitimlar',
        [source('Ilova, 4-band “a”, “b”, “v” va izoh','a) koʻchmas mol-mulkni boshqa shaxsga oʻtkazish'), S20,S11],
        [choice('region','Mulk qayerda joylashgan?', [('tashkent','Toshkent shahri'),('nukus','Nukus shahri'),('capital','Viloyat markazi'),('other','Boshqa aholi punkti')]),
         {**choice('transaction','Qaysi bitim turi?', [('ordinary','Odatdagi oldi-sotdi'),('foreign_new','Chet eldan kelgan xaridor yangi qurilgan mulk olyapti'),('resale_special','Oldin 10% boj to‘lab olingan mulk qayta sotilyapti')]), 'help':'Chet eldan kelgan xaridor uchun: u chet el fuqarosi yoki fuqaroligi bo‘lmagan shaxs bo‘lishi va O‘zbekistonda yashash guvohnomasiga ega bo‘lishi kerak. Yangi qurilgan mulk Toshkent shahri yoki viloyatida joylashgan va narxi kamida 3 300 BHM bo‘lsa, boj narxning 10%i bo‘ladi.', 'source_url':LAW+'#-8113528'},
         choice('special_area','Maxsus xarid qilinayotgan yangi mulk hududi', [('tashkent_city','Toshkent shahri'),('tashkent_region','Toshkent viloyati'),('outside','Boshqa hudud')],when={'transaction':['foreign_new']}),
         number('contract_amount','Shartnoma summasi (so‘m)',when={'transaction':['foreign_new']}),
         choice('resale_period','Avvalgi xariddan 3 yil o‘tganmi?', [('within','Hali 3 yil o‘tmagan'),('after','3 yil o‘tgan')],when={'transaction':['resale_special']}),
         choice('relative_type','Xaridor mulkdorga kim bo‘ladi?',RELATIVES),
         {**LOCATION,'label':'Notarius xizmatni qayerda ko‘rsatadi?','help':'Notarius idoradan tashqariga chiqsa, boj 2 baravar bo‘ladi. Mahalla binosidagi sayyor qabulda esa oshirilmaydi.','source_url':LAW+'#-4828174'},
         {**choice('special_status','Davlat bojidan ozod qiluvchi imtiyozni tanlang', [('none','Bu imtiyozlar menga tegishli emas'),('disability_organization','Nogironligi bo‘lgan shaxslar tashkiloti imtiyozi'),('state_orphan_home','Yetim yoki ota-ona qaramog‘isiz bolaga davlat olgan uy-joy'),('islamic_finance','Islomiy bank yoki mikromoliya tashkiloti imtiyozi')]),'help':'Mos holatni tanlang. Qarindoshlar uchun chegirma yuqoridagi savol orqali hisoblanadi.','help_by_value':{'disability_organization':'Bu imtiyoz nogironligi bo‘lgan shaxslarning jamoat birlashmasi va uning muassasasi, o‘quv-ishlab chiqarish korxonasi yoki birlashmasi uchun. Shaxsning o‘zi nogironligi borligi bu band uchun yetarli emas. Asos: 11-modda, 4-band.','state_orphan_home':'Uy-joy yetim yoki ota-ona qaramog‘idan mahrum bola uchun davlat tomonidan ikkilamchi bozordan sotib olingan va bolaning nomiga rasmiylashtirilayotgan bo‘lishi kerak. Asos: 11-modda, 19-band.','islamic_finance':'Islomiy bank yoki islomiy moliyalashtirish xizmati ko‘rsatuvchi mikromoliya tashkiloti mulkni o‘z nomiga olmoqda. Maqsad — uni keyin mijozga islomiy moliya standartlari asosida sotish. Asos: 11-modda, 20-band.'},'source_url':LAW+'#-4682691'}],
        [param('center_bhm','Toshkent/Nukus/viloyat markazi',1),param('other_bhm','Boshqa aholi punktlari',.5),param('relative_pay_percent','Qarindoshga to‘lanadigan ulush',50,'%',0,100),param('foreign_threshold_bhm','Maxsus xaridning eng kam narxi',3300),param('foreign_price_percent','Maxsus xarid: narxdan foiz',10,'%',0,100),param('resale_bhm','3 yil ichidagi maxsus qayta sotuv',400),OUTSIDE],
        'Bitta mulk bo‘yicha notarial davlat boji; maxsus xorijiy xarid shartlari alohida.', ['Maxsus bitim va qarindoshlik birga','Chegaradan past xorijiy xarid','Turli qo‘shimcha imtiyozlar']),
    definition('notary_vehicle_power','Avtomobil uchun notarial ishonchnoma','Notarial','Qarindoshlar, jiyan va berish joyi',
        [source('Ilova, 4-band “p”','p) avtomototransport vositalarini boshqarishga va tasarruf qilishga oid ishonchnomalarni'),S20,S11],
        [choice('relative_type','Vakil transport egasiga kim bo‘ladi?',RELATIVES[:-1]+[('nephew_niece','Jiyan')]+RELATIVES[-1:]),
         choice('location','Ishonchnoma qayerda tasdiqlanadi?', [('office','Idorada'),('outside','Idoradan tashqarida'),('outreach','Mahalla binosidagi sayyor qabulda'),('detention','Qamoqda saqlanayotgan shaxsning ishonchnomasi')]),SPECIAL],
        [param('relative_bhm','Qonundagi qarindosh/jiyan uchun',.5),param('other_bhm','Boshqa shaxs uchun',2),OUTSIDE],
        'Notarial boshqarish/tasarruf ishonchnomasining davlat boji; elektron xizmat emas.', ['Sug‘urtaga kiritish notarial xizmatdan alohida','Boshqa maqom bo‘yicha imtiyoz']),
    definition('notary_property_power','Ko‘chmas mulk uchun ishonchnoma','Notarial','Tasarruf vakolati va qarindoshlik',
        [source('Ilova, 4-band “r”','r) koʻchmas mol-mulkni tasarruf etish huquqini beruvchi ishonchnomalarni'),S20,S11],
        [choice('relative_type','Vakil mulkdorga kim bo‘ladi?',RELATIVES),choice('location','Ishonchnoma qayerda tasdiqlanadi?', [('office','Idorada'),('outside','Idoradan tashqarida'),('outreach','Mahalladagi sayyor qabulda'),('detention','Qamoqda saqlanayotgan shaxsning ishonchnomasi')]),SPECIAL],
        [param('relative_bhm','Qonundagi qarindosh uchun',.25),param('other_bhm','Boshqa shaxs uchun',.5),OUTSIDE],
        'Ko‘chmas mulkni tasarruf qilish vakolatiga oid notarial boj.', ['Jiyan bu bandning qarindoshlik ro‘yxatiga avtomatik kirmaydi','Boshqa maqsaddagi ishonchnoma']),
    definition('notary_lease','Mol-mulk ijarasini notarial tasdiqlash','Notarial','Taraflar, qarindoshlik va bekor qilish',
        [source('Ilova, 4-band “g” va bekor qilish izohi','g) mol-mulkni ijaraga berish shartnomasini tasdiqlaganlik'),S20,S11],
        [choice('party_type','Taraflardan biri yuridik shaxsmi?', [('individual','Ikkala taraf ham jismoniy shaxs'),('legal','Kamida biri yuridik shaxs')]),
         choice('relative_type','Taraflar o‘rtasidagi qarindoshlik',RELATIVES,when={'party_type':['individual']}),
         choice('operation','Qanday harakat?', [('certify','Tasdiqlash / o‘zgartirish'),('cancel','Shartnomani bekor qilish')]),LOCATION,SPECIAL],
        [param('individual_bhm','Jismoniy shaxslar',.25),param('legal_bhm','Yuridik shaxs ishtirok etsa',.5),param('relative_bhm','Qonundagi qarindoshlar',.1),param('cancel_pay_percent','Bekor qilishda to‘lanadigan ulush',50,'%',0,100),OUTSIDE],
        'Faqat notarial tasdiqlash boji; soliq organidagi ijara ro‘yxati va ijara haqi emas.', ['Boshqa maxsus shaxsiy maqom','Bir necha harakat birlashtirilsa alohida hisob']),
    definition('notary_inheritance','Meros huquqi guvohnomasi','Notarial','Mulk turi, meros ulushi va qonundagi imtiyozlar',
        [source('Ilova, 4-band “m”','m) merosga boʻlgan xuquq toʻgʻrisida guvohnoma berganlik'),
         source('11-modda, 5-band — meros imtiyozlari','5) shaxslar — ularga quyidagilar uchun merosga boʻlgan huquqi'),
         source('11-modda, 3–4-band — tashkilotlar','3) davlat soliq xizmati organlari va moliya organlari'),
         source('11-modda, 10-band — ishdagi baxtsiz hodisa sug‘urtasi','10) ishlab chiqarishdagi baxtsiz hodisa'),
         source('11-modda, 11-band — vasiylik','11) surunkali ruhiy kasallikka chalingan'),
         source('11-modda, 14-band — majburiy sug‘urta','14) shaxslar — ularga yoʻlovchilarning majburiy sugʻurtasi'),
         source('11-modda, 15–16-band — fermer va dehqon xo‘jaligi','15) fermer xoʻjaligida faoliyatni davom ettirayotgan merosxoʻrlar'),
         source('20-modda — har bir merosxo‘r ulushi','Bir nechta merosxoʻr'),
         source('20-modda — voyaga yetmagan merosxo‘r','Voyaga yetmagan merosxoʻrlar'),
         source('20-modda — oldingi guvohnoma to‘lovi','Agar merosga boʻlgan huquq toʻgʻrisidagi guvohnoma merosxoʻrlarning arizasi'),
         source('20-modda — suddan keyingi takroriy guvohnoma','Sudlarning ilgari berilgan guvohnomalar haqiqiy emasligi'),
         source('20-modda — er-xotinning umumiy mulki','Er-xotinning birgalikda yashaganda olingan'),
         source('20-modda — sertifikat va akkreditiv','Kredit tashkilotlari tomonidan beriladigan sertifikatlar'), S20],
        [{**choice('property_type','Qanday meros olyapsiz?', [
            ('home','Uy yoki kvartira'),('real_estate','Boshqa ko‘chmas mulk'),('vehicle','Avtomobil yoki mototransport'),('housing_coop','Uy-joy kooperatividagi pay'),
            ('deposit','Bank omonati'),('salary','Marhumga tegishli ish haqi'),('pension','Shaxsiy pensiya hisobidagi mablag‘'),('government_bond','Davlat zayom obligatsiyasi'),
            ('insurance','Shaxsiy yoki mulkiy sug‘urta puli'),('passenger_insurance','Yo‘lovchi / mol-mulk majburiy sug‘urtasi puli'),('work_insurance','Ishdagi baxtsiz hodisa uchun sug‘urta puli'),
            ('copyright','Mualliflik yoki ijrochilik mulkiy huquqi'),('royalty','Asar, ixtiro yoki ijro uchun haq'),('credit_certificate','Kredit tashkiloti sertifikati yoki akkreditiv'),('other','Boshqa mol-mulk')]), 'help':'Mulk turini aniq tanlang. Bir hisobda bitta obyekt olinadi.',
          'help_by_value':{'copyright':'Ilm-fan, adabiyot, san’at asari, ixtiro, seleksiya yutug‘i, foydali model, sanoat namunasi yoki mikrosxema topologiyasi muallifining mulkiy huquqi; ijrochining ijroga doir mulkiy huquqi. Boshqa huquqlarni avtomatik shu toifaga kiritmang.',
          'royalty':'Qonunda sanalgan asar, ixtiro va boshqa ijodiy natijalarni yoki ijrolarni yaratish va ulardan foydalanish uchun marhumga tegishli haq. Asos: 11-modda, 5-band.',
          'passenger_insurance':'Yo‘lovchining majburiy sug‘urtasi yoki fuqaroga qarashli mol-mulkning majburiy sug‘urtasi bo‘yicha to‘lov. Asos: 11-modda, 14-band.',
          'credit_certificate':'Sertifikat va akkreditiv bank omonati bilan bir xil emas. 20-modda bo‘yicha umumiy boj hisoblanadi.',
          'home':'Merosga kirayotgan uy yoki kvartira. Qiymat foizi olinmaydi; boj BHM va hujjatdagi meros ulushidan hisoblanadi.'}},
         {**choice('certificate_kind','Qaysi guvohnomani olyapsiz?', [('first','Birinchi guvohnoma'),('partial','Merosning bir qismiga guvohnoma'),('remaining','Qolgan qismga keyingi guvohnoma'),('court_reissue','Sud eski guvohnomani bekor qilganidan keyingi yangi guvohnoma')]),'help':'Hisob bitta mulk va bitta merosxo‘r uchun. Boshqa mulk yoki merosxo‘r bo‘lsa, alohida hisoblang.'},
         choice('minor','Merosxo‘r 18 yoshga to‘lmaganmi?', [('no','Yo‘q, 18 yoshga to‘lgan'),('yes','Ha, 18 yoshga to‘lmagan')],when={'special_status':['none','duty_death','guardianship','farmer','dehkan']}),
         {**choice('special_status','Merosxo‘rga tegishli imtiyoz', [
             ('none','Quyidagi imtiyozlar tegishli emas'),('duty_death','Vatan, davlat yoki inson hayotini himoya qilib halok bo‘lgan shaxs merosi'),
             ('guardianship','Surunkali ruhiy kasallik sabab vasiylik belgilangan'),('farmer','Fermer xo‘jaligi mulki — faoliyatni davom ettiraman'),('dehkan','Dehqon xo‘jaligi mulki — faoliyatni davom ettiraman'),
             ('state_authority','Davlat merosi uchun soliq yoki moliya organi'),('disability_organization','Nogironligi bo‘lgan shaxslar jamoat birlashmasi')]),
          'help':'Faqat shu merosga mos asosni tanlang. Oddiy nogironlik maqomi bu ro‘yxatdagi tashkilot yoki vasiylik imtiyozi bilan bir xil emas.',
          'help_by_value':{'duty_death':'Marhum Vatanni himoya qilish, davlat yoki jamoat vazifasini bajarish, inson hayotini qutqarish, davlat mulki yoki huquq-tartibotni himoya qilish bilan bog‘liq fuqarolik burchini bajarishda halok bo‘lgan bo‘lishi kerak. 11-modda, 5-band.',
          'guardianship':'Ikkala shart kerak: surunkali ruhiy kasallik va qonuniy tartibda belgilangan vasiylik. 11-modda, 11-band.',
          'farmer':'Meros aynan fermer xo‘jaligining mulki bo‘lishi va merosxo‘r shu xo‘jalikda faoliyatni davom ettirishi kerak. 11-modda, 15-band.',
          'dehkan':'Meros aynan dehqon xo‘jaligi mulki bo‘lishi va merosxo‘r faoliyatni davom ettirishi kerak. Xo‘jalik yuridik shaxs bo‘lishi shart emas. 11-modda, 16-band.',
          'state_authority':'Soliq yoki moliya organi davlatning meros huquqini rasmiylashtirish uchun murojaat qilmoqda. 11-modda, 3-band.',
          'disability_organization':'Nogironligi bo‘lgan shaxslar jamoat birlashmasi, uning muassasasi, o‘quv-ishlab chiqarish korxonasi yoki birlashmasi nomidan murojaat. 11-modda, 4-band.'},'source_url':S11['url']},
         choice('lived_before','Marhum vafotigacha shu uyda birga yashaganmisiz?', [('yes','Ha'),('no','Yo‘q')],when={'property_type':['home','housing_coop'],'minor':['no'],'special_status':['none']}),
         choice('registered','Shu manzilda doimiy ro‘yxatda bo‘lganmisiz?', [('yes','Ha'),('no','Yo‘q')],when={'property_type':['home','housing_coop'],'minor':['no'],'special_status':['none']}),
         {**choice('lives_after','Marhum vafotidan keyin ham shu uyda yashayapsizmi?', [('yes','Ha'),('no','Yo‘q')],when={'property_type':['home','housing_coop'],'minor':['no'],'special_status':['none']}),'help':'Uy-joy imtiyozi uchun uchala javob ham “Ha” bo‘lishi kerak. Asos: 11-modda, 5-band.'},
         {**choice('work_policy','Marhumni ishdagi baxtsiz hodisa uchun korxona hisobidan sug‘urtalashganmi?', [('yes','Ha, korxona yoki tashkilot hisobidan'),('no','Yo‘q / bu shart tasdiqlanmagan')],when={'property_type':['work_insurance']}),'help':'Imtiyoz ishlab chiqarishdagi baxtsiz hodisa sabab vafot etish uchun korxona hisobidan tuzilgan sug‘urtaga tegishli. Asos: 11-modda, 10-band.'},
         {**choice('joint_property','Bu er-xotinning umumiy mulkimi?', [('no','Yo‘q / faqat marhumga tegishli qism kiritilmoqda'),('yes','Ha, umumiy mulkdan merosga o‘tadigan qismni kiritaman')]),'help':'Tirik qolgan turmush o‘rtog‘ining o‘z mulki merosga qo‘shilmaydi. Merosga kiradigan qismni hujjat yoki notarius asosida kiriting; dastur avtomatik yarmini olmaydi.'},
         number('estate_numerator','Umumiy mulkning merosga kiradigan qismi: surat',1,10000,when={'joint_property':['yes']}),
         number('estate_denominator','Umumiy mulkning merosga kiradigan qismi: maxraj',1,10000,when={'joint_property':['yes']}),
         {**number('share_numerator','Merosxo‘r ulushi: surat (1/2 uchun 1)',1,10000),'help':'Qolgan qismga keyingi guvohnomada — oldingi va yangi guvohnomalar bilan qamraladigan jami ulushni kiriting. Boshqa holatda — hozirgi guvohnomadagi ulush. Qonun, vasiyatnoma yoki majburiy ulush bo‘yicha hujjatda belgilangan ulushdan foydalaning.'},
         number('share_denominator','Merosxo‘r ulushi: maxraj (1/2 uchun 2)',1,10000),
         choice('credit_confirmed','Oldingi to‘lovni hisobga olish hujjatlar bilan tasdiqlanganmi?', [('yes','Ha, hisobga olinadigan summa tasdiqlangan'),('no','Yo‘q, hali tekshirilmagan')],when={'certificate_kind':['remaining','court_reissue']}),
         {**number('previous_payment','Hisobga olinadigan oldingi davlat boji (so‘m)',0,10**12,when={'certificate_kind':['remaining','court_reissue'],'credit_confirmed':['yes']}),'help':'Faqat shu mulk va shu merosxo‘r uchun tasdiqlangan summa. Suddan keyingi yangi guvohnomada to‘lovning budjetga tushgani, uni hisobga olish arizasi va da’vo muddati sharti ham tekshirilishi kerak.'},
         {**LOCATION,'help':'Idoradan tashqarida boj 2 baravar. Mahalla organi binosidagi sayyor qabulda oshirilmaydi.','source_url':S20['url']}],
        [param('real_vehicle_bhm','Ko‘chmas mulk / avtomototransport',.5),param('other_bhm','Boshqa mol-mulk',.3),OUTSIDE],
        'Bitta mulk va bitta merosxo‘rning hujjatda belgilangan ulushi uchun davlat boji.', ['Har bir ko‘chmas mulk yoki transport alohida hisoblanadi','Ulush va imtiyoz shartlari hujjatlar bilan tasdiqlanadi','Sertifikat va akkreditiv bank omonati imtiyoziga kirmaydi','Oldingi bojni hisobga olish tejash deb hisoblanmaydi','Oddiy dublikat va merosni muhofaza qilish boshqa notarial harakatlardir']),
    definition('court_civil','Fuqarolik sudidagi pul talabi','Sud','Foiz, eng kam boj, da’vo turi va shikoyat',
        [source('Ilova, 1-band “a”, “z”','1. Fuqarolik ishlari boʻyicha sudlarga beriladigan'),S8,source('19-modda, aralash talablar','Bir vaqtning oʻzida mulkiy va nomulkiy xususiyatga ega')],
        [choice('claim_type','Talab nimaga oid?', [('debt','Oddiy qarz / boshqa mulkiy pul talabi'),('salary','Mehnat munosabatidan ish haqini undirish'),('alimony','Aliment undirish'),('consumer','Iste’molchi huquqi buzilishi'),('health','Mehnatda mayiblik / sog‘liqqa zarar / boquvchi vafoti zarari'),('crime','Jinoyat tufayli moddiy zarar')]),
         choice('stage','Murojaat bosqichi', [('first','Birinchi instansiyaga da’vo'),('appeal','Apellyatsiya / kassatsiya / taftish')]),
         number('claim_amount','Da’vo yoki nizolashilayotgan summa (so‘m)',when={'claim_type':['debt']}),
         choice('mixed_claims','Pul talabiga qo‘shimcha nomulkiy talab ham bormi?', [('no','Yo‘q, bitta pul talabi'),('yes','Ha / bir nechta turdagi talab')]),SPECIAL],
        [param('claim_percent','Da’vo bahosidan foiz',4,'%',0,100),param('minimum_bhm','Eng kam boj',1),param('appeal_pay_percent','Shikoyatdagi to‘lanadigan ulush',50,'%',0,100)],
        'Da’vogar uchun bitta UZS pul talabi; nomulkiy va sud buyrug‘i hisoblari kiritilmagan.', ['Imtiyozli talabning shikoyat bosqichi','Aralash talablar','Ish haqi va buyurtma haqini farqlash']),
    definition('court_economic','Iqtisodiy suddagi pul talabi','Sud','Eng kam boj, kichik biznes va shikoyat',
        [source('Ilova, 2-band “a”, “d” va izoh','2. Iqtisodiy sudlarga beriladigan'),S9],
        [number('claim_amount','Da’vo yoki nizolashilayotgan summa (so‘m)'),choice('stage','Murojaat bosqichi', [('first','Birinchi instansiya'),('appeal','Apellyatsiya / kassatsiya / taftish')]),
         choice('small_business','Murojaat qiluvchi kichik tadbirkor va talab uning tadbirkorlik faoliyati doirasidami?', [('no','Yo‘q'),('yes','Ikkala shart ham bajarilgan')]),
         choice('mixed_claims','Nomulkiy talab yoki xorijiy valyutadagi talab ham bormi?', [('no','Yo‘q, bitta UZS pul talabi'),('yes','Ha / aralash')]),SPECIAL],
        [param('claim_percent','Da’vo bahosidan foiz',2,'%',0,100),param('minimum_bhm','Eng kam boj',1),param('small_business_pay_percent','Kichik biznes to‘laydigan ulush',50,'%',0,100),param('appeal_pay_percent','Shikoyatda to‘lanadigan ulush',50,'%',0,100)],
        'Bitta UZS pul talabi; birinchi instansiya yoki oddiy shikoyat.', ['Kichik biznes va shikoyat ulushlarini birlashtirish','Maxsus ozodlik maqomi','Aralash va xorijiy valyuta talablari']),
    definition('vehicle_power_electronic','Elektron avtoishonchnoma','Davlat xizmati','Muddat va I–II guruh nogironlik imtiyozi',
        [source('613-son qaror, reglament 15-band','15. Ishonchnomani elektron shaklda rasmiylashtirish',EPOWER_SOURCE),source('613-son qaror, I–II guruh imtiyozi','I va II guruh nogironligi boʻlgan shaxslarga',EPOWER_SOURCE),source('Ilova, 4-band “p”, notarial bazaviy stavka','p) avtomototransport vositalarini boshqarishga va tasarruf qilishga oid ishonchnomalarni')],
        [choice('duration','Amal qilish muddati', [('one_month','1 oygacha'),('six_months','1 oydan ortiq, 6 oygacha'),('three_years','6 oydan ortiq, 3 yilgacha')]),
         choice('recipient','Vakil qarindoshmi? (notarial tarif asosini aniqlash uchun)', [('other','Boshqa shaxs'),('relative','Qarindosh / jiyan')]),
         choice('benefit_category','To‘lovchi imtiyozli toifaga kiradimi?', [('none','Boshqa imtiyoz haqida ma’lumot yo‘q'),('disability','I yoki II guruh nogironligi'),('registry','Ijtimoiy reyestr / boshqa imtiyoz'),('multiple','Bir nechta asos / aniq emas')])],
        [param('base_bhm','Notarial bazaviy stavka',2),param('one_month_percent','1 oygacha: bazaviy boj ulushi',10,'%',0,100),param('six_months_percent','6 oygacha: bazaviy boj ulushi',50,'%',0,100),param('three_years_percent','3 yilgacha: bazaviy boj ulushi',100,'%',0,100),param('disability_pay_percent','I–II guruh to‘laydigan ulush',50,'%',0,100)],
        'Elektron boshqaruv ishonchnomasi; oddiy boshqa shaxs tarifi va reglamentdagi nogironlik imtiyozi.', ['Qarindosh tarifining elektron xizmatga qo‘llanishini tekshirish','Portalning qo‘shimcha chegirmasini avtomatik qo‘shmaslik','Reyestr va bir nechta asos kombinatsiyasi']),
    definition('patent_application','Ixtiro / foydali model talabnomasi','Patent','Guruh, ortiqcha sahifalar va talabgor imtiyozi',
        [source('Ilova, 10-band “a”','10. Ixtirolar, foydali modellar, sanoat namunalarini huquqiy muhofaza qilish'),S23],
        [choice('object_type','Huquqiy muhofaza obyekti', [('invention','Ixtiro'),('utility','Foydali model')]),choice('applicant_type','Talabgor turi', [('individual','Jismoniy shaxs'),('legal','Yuridik shaxs')]),
         number('object_count','Guruhdagi ixtirolar / foydali modellar soni',1,1000),
         number('description_pages','Ixtiro tavsifi varaqlari soni',1,10000,when={'object_type':['invention']}),
         choice('individual_benefit','Jismoniy shaxs uchun imtiyoz asosi', [('none','Boshqa asos yo‘q'),('disability2','II guruh nogironligi'),('education','Ta’lim oluvchi / ilmiy yoki ilmiy-pedagogik xodim'),('multiple','Bir nechta asos / boshqa holat')],when={'applicant_type':['individual']}),
         choice('legal_benefit','Yuridik shaxs uchun imtiyoz asosi', [('none','Boshqa asos yo‘q'),('small_or_education','Kichik tadbirkor / akkreditatsiyali ta’lim yoki ilmiy tashkilot'),('multiple','Bir nechta asos / boshqa holat')],when={'applicant_type':['legal']})],
        [param('individual_base_bhm','Jismoniy shaxs: birinchi obyekt',2),param('legal_base_bhm','Yuridik shaxs: birinchi obyekt',4),param('individual_extra_bhm','Jismoniy shaxs: qo‘shimcha obyekt',1),param('legal_extra_bhm','Yuridik shaxs: qo‘shimcha obyekt',2),param('individual_page_bhm','Jismoniy shaxs: ortiqcha varaq',.01),param('legal_page_bhm','Yuridik shaxs: ortiqcha varaq',.02),param('page_limit','Ixtiro tavsifining bazaviy varaqlari',35,'son',1,10000),param('disability_pay_percent','II guruh: to‘lanadigan ulush',10,'%',0,100),param('education_pay_percent','Ta’lim / ilmiy xodim: to‘lanadigan ulush',70,'%',0,100),param('organization_pay_percent','Yuridik imtiyoz: to‘lanadigan ulush',75,'%',0,100)],
        'Faqat talabnoma, rasmiy ekspertiza va tegishli e’lon bosqichi; patent olishning jami narxi emas.', ['Bir nechta talabgor / imtiyoz kombinatsiyasi','Sanoat namunasi alohida tarif','Keyingi ekspertiza va patentni saqlash to‘lovlari alohida']),
]

# Keep the 20 statutory cases visible as a reference, but expose only applicable
# grounds in each calculation. Article 20 also requires a separate party check.
from .notarial import party_question, configure_notarial_questions
for item in CATALOG:
    if item['id'] in {'notary_vehicle_power','notary_property_power','notary_lease'}:
        for index, field in enumerate(item['questions']):
            if field['key']=='special_status':
                item['questions'][index] = {
                    **choice('special_status','11-modda bo‘yicha imtiyoz', [('none','Bu imtiyoz menga tegishli emas'),('disability_organization','Nogironligi bo‘lgan shaxslar tashkiloti')]),
                    'help':'Jamoat birlashmasi, uning muassasasi, o‘quv-ishlab chiqarish korxonasi yoki birlashmasi uchun. Shaxsning nogironligi o‘zi yetarli emas. Asos: 11-modda, 4-band.', 'source_url':S11['url']}
        if item['id']=='notary_lease':
            item['questions'].append(party_question(['disability_organization']))
    if item['id']=='notary_property':
        for field in item['questions']:
            if field['key']=='special_status':
                field['options']=[o for o in field['options'] if o['value']!='needs_review']
        item['questions'].append(party_question(['disability_organization','state_orphan_home','islamic_finance']))

for item in CATALOG:
    if item['id'] not in {'notary_property','notary_vehicle_power','notary_property_power','notary_lease'}:
        continue
    for field in item['questions']:
        if field['key'] == 'relative_type':
            field['when'] = {**field.get('when',{}), 'special_status':['none','state_orphan_home']}
        if item['id'] == 'notary_lease' and field['key'] == 'special_status':
            field['when'] = {'party_type':['legal']}
    # Existing order is preserved apart from moving capacity before kinship.
    status_field = next(q for q in item['questions'] if q['key']=='special_status')
    item['questions'].remove(status_field)
    relative_index = next(i for i,q in enumerate(item['questions']) if q['key']=='relative_type')
    item['questions'].insert(relative_index,status_field)
    if item['id']=='notary_lease':
        next(q for q in item['questions'] if q['key']=='relative_type')['when'] = {'party_type':['individual']}

for item in CATALOG:
    if item['category'] == 'Notarial':
        configure_notarial_questions(item['questions'])

# Court fees below cover one first-instance filing or one request for copies.
BUSINESS = choice('business_relief', 'Kichik tadbirkor o‘z faoliyati bo‘yicha murojaat qilyaptimi?',
                  [('no','Yo‘q'), ('yes','Ha')])
HALF = param('business_percent','Kichik tadbirkor to‘laydigan ulush',50,'%',0,100)


def court_service(key, name, description, sources, questions, rates):
    return definition(key, name, 'Sud', description, sources, questions, rates, description, [])


CATALOG.extend([
    court_service('court_divorce', 'Sud orqali nikohni bekor qilish', 'Nikoh turi va birga berilgan mulkiy talab',
        [source('Ilova, 1-band “v”, “g”, “d”','v) nikohni bekor qilish haqidagi'),
         source('Ilova, 1-band “a”','a) mulkiy xususiyatga ega daʼvo arizalaridan'),
         source('19-modda','Nikohni bekor qilish bilan bir vaqtda mol-mulkni boʻlish')],
        [choice('marriage','Qaysi holat sizga mos?', [('first','Birinchi nikoh'),('repeat','Takroriy nikoh'),
         ('statutory','Turmush o‘rtog‘i bedarak yo‘qolgan yoki ruhiy kasallik sababli muomalaga layoqatsiz deb topilgan yoxud kamida 3 yilga qamalgan')]),
         choice('division','Mol-mulkni bo‘lish ham so‘ralganmi?', [('no','Yo‘q'),('yes','Ha')]),
         number('claim_amount','Mulk bo‘yicha da’vo summasi (so‘m)',when={'division':['yes']})],
        [param('first','Birinchi nikoh',2),param('repeat','Takroriy nikoh',4),param('statutory','Maxsus asos',0.02),
         param('claim_percent','Mulkiy talab ulushi',4,'%',0,100),param('minimum_bhm','Mulkiy talab uchun eng kam boj',1)]),
    court_service('court_copies','Sud hujjatlaridan nusxa olish','Fuqarolik yoki iqtisodiy sud, betlar soni va tadbirkor imtiyozi',
        [source('Ilova, 1-band “i”','i) qarorlar, ajrimlar, boshqa sud hujjatlarining dublikatlari'),
         source('Ilova, 2-band “e”','e) sud hujjatlarining dublikatlarini hamda taraflar')],
        [choice('court_kind','Hujjat qaysi suddan olinadi?', [('civil','Fuqarolik sudi'),('economic','Iqtisodiy sud')]),
         number('pages','Jami nechta bet kerak?',1,10000), BUSINESS],
        [param('page_bhm','Bir bet uchun',0.02), HALF]),
    court_service('court_economic_filing','Iqtisodiy sudga ariza berish','Nomulkiy talab, shartnoma nizosi yoki to‘lovga qobiliyatsizlik',
        [source('Ilova, 2-band “b”–“g” va izoh','2. Iqtisodiy sudlarga beriladigan')],
        [choice('filing','Nima bo‘yicha murojaat qilyapsiz?', [('nonproperty','Nomulkiy da’vo'),('insolvency','To‘lovga qobiliyatsizlik ishini boshlash'),
         ('contract','Xo‘jalik shartnomasini tuzish, o‘zgartirish yoki bekor qilish nizosi')]), BUSINESS],
        [param('nonproperty','Nomulkiy da’vo',10),param('insolvency','To‘lovga qobiliyatsizlik',3),param('contract','Shartnoma nizosi',10),HALF]),
    court_service('court_special_proceeding','Faktni sud orqali belgilash','Alohida tartibdagi ish va bojdan ozod qilingan arizalar',
        [source('Ilova, 1-band “j” va izoh','j) alohida koʻriladigan ishlarga doir arizalardan')],
        [choice('fact','Ariza nima haqida?', [('paternity','Otalikni belgilash yoki tan olish'),('birth','Bolaning qaysi onadan yoki qachon tug‘ilganini aniqlash'),
         ('gambling','Shaxsni qimorga qaram shaxslar ro‘yxatiga kiritish'),('ordinary','Alohida tartibdagi boshqa ish (umumiy stavka)')])],
        [param('base','Umumiy stavka',1)]),
    court_service('court_nonproperty','Fuqarolik sudiga nomulkiy da’vo','Ijara nizosi, mulkni xatlovdan chiqarish yoki boshqa nomulkiy talab',
        [source('Ilova, 1-band “e” va izoh','e) turar joylar ijarasiga doir shartnomani')],
        [choice('subject','Talab nimaga tegishli?', [('lease','Turar joy ijarasini o‘zgartirish yoki bekor qilish'),
         ('inventory','Mol-mulkni xatlovdan chiqarish'),('nonproperty','Boshqa nomulkiy yoki baholanmaydigan talab')]), BUSINESS],
        [param('base','Umumiy stavka',2),HALF]),
])

BY_ID = {item['id']: item for item in CATALOG}


def public_service(item):
    return {key: item[key] for key in ['id','name','category','description','icon','scope','review_note']}


def seed_config(item):
    return {'effective_from':'2026-09-01','bhm_amount':440000,'parameters':{p['key']:p['value'] for p in item['parameters']},'law_url':item['sources'][0]['url'],'law_article':item['sources'][0]['article'],'bhm_source_url':BHM_SOURCE,'verified_at':'2026-11-20','change_note':'Lex.uz manbalari asosidagi boshlang‘ich hisob. Jamoaning qo‘lda huquqiy tekshiruvi kutilmoqda.'}


def applies(question, answers):
    return all(answers.get(key) in values for key,values in question.get('when',{}).items())
