"""Article 11 reference and service-specific exemptions; Article 20 party rule."""
from urllib.parse import quote

LAW = 'https://lex.uz/docs/-4680944'
NOTARIAL_IDS = ['notary_car','notary_property','notary_vehicle_power','notary_property_power','notary_lease','notary_inheritance']


def rule(number, title, description, phrase, services=()):
    return {'number':number, 'title':title, 'description':description,
            'url':LAW+'#-4682691:~:text='+quote(phrase,safe=''), 'find_text':phrase, 'services':list(services)}


ARTICLE_11 = [
    rule(1,'Pensiya, nafaqa va oilaga oid hujjat nusxalari','Pensiya yoki nafaqa olish, vasiylik yoki farzandlikka olish ishi uchun hujjat nusxasini tasdiqlash.','1) shaxslar — davlat pensiyalari va nafaqalarini'),
    rule(2,'Davlat yoki tashkilotga hadya','Davlat yoki yuridik shaxs foydasiga hadya va vasiyatnomani tasdiqlash. Oddiy oldi-sotdiga tegishli emas.','2) shaxslar — mol-mulkini davlat foydasiga'),
    rule(3,'Davlatga o‘tadigan meros','Soliq yoki moliya organiga davlatning meros huquqi guvohnomasi, uning dublikati va kerakli hujjatlar.','3) davlat soliq xizmati organlari va moliya organlari',['notary_inheritance']),
    rule(4,'Nogironligi bo‘lgan shaxslar tashkilotlari','Jamoat birlashmalari va ularning muassasalari, o‘quv-ishlab chiqarish korxonalari hamda birlashmalari uchun. Shaxsning nogironligi o‘zi bu asosga teng emas.','4) nogironligi boʻlgan shaxslarning jamoat birlashmalari',NOTARIAL_IDS),
    rule(5,'Merosga oid imtiyozlar','Xizmat yoki fuqarolik burchida halok bo‘lgan shaxs merosi; shartlari bajarilgan uy-joy; qonundagi omonat, sug‘urta, ish haqi, pensiya mablag‘i, mualliflik huquqi va haq.','5) shaxslar — ularga quyidagilar uchun merosga boʻlgan huquqi',['notary_inheritance']),
    rule(6,'Pensiya yoki nafaqa olish ishonchnomasi','Faqat pensiya va nafaqa olish uchun ishonchnoma. Avtomobil yoki uy-joyni tasarruf qilish ishonchnomasi emas.','6) shaxslar — pensiyalar va nafaqalar olish uchun'),
    rule(7,'Ko‘p bolali onaning mukofot hujjatlari','Ko‘p bolalik uchun orden yoki medal berish ishidagi hujjat nusxalarini tasdiqlash.','7) onalar — koʻp bolalik uchun'),
    rule(8,'Maktab-internatning ijro yozuvi','Bolaning internatdagi ta’minoti uchun ota-onadan qarz undirishga oid ijro yozuvi.','8) maktab-internatlar — farzandlarining'),
    rule(9,'Ixtisoslashtirilgan maktab ta’minoti','Moliya organining tegishli ixtisoslashtirilgan maktab ta’minoti qarzini undirish ijro yozuvi.','9) moliya organlari — farzandlarining'),
    rule(10,'Ishdagi baxtsiz hodisa sug‘urtasi','Ishdagi baxtsiz hodisadan vafot etish uchun korxona hisobidan sug‘urtalangan shaxsning sug‘urta puliga meros guvohnomasi.','10) ishlab chiqarishdagi baxtsiz hodisa',['notary_inheritance']),
    rule(11,'Vasiylik belgilangan merosxo‘r','Surunkali ruhiy kasallik va qonuniy belgilangan vasiylik birga mavjud bo‘lsa — meros guvohnomasi.','11) surunkali ruhiy kasallikka chalingan',['notary_inheritance']),
    rule(12,'Davlat organi orqali ishga yuborish','Bandlik organlari orqali tashkiliy ishga qabul qilishda tuzilgan mehnat shartnomasini tasdiqlash.','12) Oʻzbekiston Respublikasi Kambagʻallikni qisqartirish'),
    rule(13,'Imtiyoz olish uchun hujjat nusxalari','Qonunda sanalgan urush, xizmat va Chernobil bilan bog‘liq toifalarga imtiyoz olish uchun zarur nusxalarni tasdiqlash. Barcha notarial harakatlarga umumiy ozodlik emas.','13) 1941 — 1945-yillardagi urush nogironlari'),
    rule(14,'Majburiy sug‘urta pulini meros olish','Yo‘lovchilar yoki fuqaroga tegishli mol-mulk majburiy sug‘urtasi bo‘yicha meros guvohnomasi.','14) shaxslar — ularga yoʻlovchilarning majburiy sugʻurtasi',['notary_inheritance']),
    rule(15,'Fermer faoliyatini davom ettirish','Merosxo‘r fermer xo‘jaligi faoliyatini davom ettirsa — shu xo‘jalik mulkiga meros guvohnomasi.','15) fermer xoʻjaligida faoliyatni davom ettirayotgan merosxoʻrlar',['notary_inheritance']),
    rule(16,'Dehqon faoliyatini davom ettirish','Merosxo‘r dehqon xo‘jaligi faoliyatini davom ettirsa — shu xo‘jalik mulkiga meros guvohnomasi.','16) yuridik shaxs tashkil etgan va tashkil etmagan',['notary_inheritance']),
    rule(17,'Kommunal qarzning ijro yozuvi','Uy-joy mulkdorlari shirkati yoki kommunal tashkilotning badal va xizmat haqi qarzi uchun ijro yozuvi.','17) xususiy uy-joy mulkdorlarining shirkatlari'),
    rule(18,'Ofatdan keyingi hujjatlarni tiklash','Tabiiy yoki texnogen ofat jabrlanuvchisiga hujjat dublikati, nusxasi va notarial reyestrdan ko‘chirma berish.','18) Oʻzbekiston Respublikasi yoki chet davlatlar hududida'),
    rule(19,'Bolaga davlat sotib olgan uy-joy','Yetim yoki ota-ona qaramog‘isiz bola uchun davlat ikkilamchi bozordan olgan uy-joyni bolaning nomiga rasmiylashtirish.','19) yetim bolalar va ota-onasining qaramogʻidan mahrum',['notary_property']),
    rule(20,'Islomiy moliyalashtirishdagi mulk xaridi','Islomiy bank yoki tegishli mikromoliya tashkiloti mulkni keyin mijozga islomiy moliya asosida sotish uchun o‘z nomiga olishi.','20) shaxslar — islomiy bank faoliyatini',['notary_car','notary_property']),
]


def configure_notarial_questions(questions):
    for q in questions:
        if q['key'] == 'relative_type':
            for option in q['options']:
                if option['value'] == 'other':
                    option['label'] = 'Boshqa shaxs (shu jumladan, yuqorida ko‘rsatilmagan qarindoshlar)'
        if q['key'] == 'special_status':
            q['label'] = 'Mavjud imtiyozlar'
            q['options'].append({'value':'unsure', 'label':'Bilmayman'})
        statuses = q.get('when', {}).get('special_status', [])
        if 'none' in statuses:
            q['when'] = {**q['when'], 'special_status':[*statuses, 'unsure']}


def reference_for(service_id):
    return [{**item, 'applicable':service_id in item['services']} for item in ARTICLE_11] if service_id in NOTARIAL_IDS else []


def normalize_notarial_answers(service_id, answers):
    answers = dict(answers)
    if service_id == 'notary_car' and answers.get('transaction_kind') == 'exchange':
        answers['bank_credit'] = 'no'
    if service_id in NOTARIAL_IDS and service_id != 'notary_inheritance' and answers.get('special_status') in {'disability_organization','islamic_finance'}:
        # Kinship is between natural persons, not a legal entity and its counterparty.
        # Discard an old hidden kinship answer when switching to an organization.
        answers['relative_type'] = 'other'
    return answers


def party_question(statuses):
    return {'key':'exemption_parties','label':'Bitimda kim davlat bojidan ozod?', 'type':'choice',
            'options':[{'value':'one','label':'Faqat bir taraf'}, {'value':'both','label':'Ikkala taraf ham — asoslari tasdiqlangan'}],
            'when':{'special_status':statuses},
            'help':'20-modda: faqat bir taraf ozod bo‘lsa, davlat bojini ikkinchi taraf to‘liq to‘laydi. Ikkala tarafning ozodlik asosini hujjatlar bilan tekshiring.',
            'source_url':LAW+'#-4683028:~:text='+quote('Davlat boji toʻlashdan bir taraf ozod',safe='')}


def apply_notarial_exemption(result, answers, service_id):
    status = answers.get('special_status')
    grounds = {'disability_organization':4,'state_orphan_home':19,'islamic_finance':20}
    if status not in grounds:
        return result
    # A selected exemption cannot turn an unresolved calculation into a final zero.
    if result.get('payable_amount') is None:
        return result
    transactional = service_id in {'notary_car','notary_property','notary_lease'}
    number = grounds[status]
    entry = ARTICLE_11[number-1]
    legal_source = {'title':'Davlat boji to‘g‘risidagi qonun', 'article':f'11-modda, {number}-band — {entry["title"]}', 'url':entry['url'], 'find_text':entry['find_text']}
    sources = result.get('legal_basis',[]) + [legal_source]
    if service_id=='notary_lease' and answers.get('party_type')!='legal':
        return {**result,'status':'needs_verification','payable_amount':None,'saving_amount':None,'benefit_title':'Taraflar ma’lumotini tekshiring','explanation':'Tashkilot imtiyozi tanlangan, lekin ikkala taraf jismoniy shaxs deb ko‘rsatilgan. Taraflar turini aniqlashtiring.','legal_basis':sources}
    if transactional and answers.get('exemption_parties') != 'both':
        sources += [{'title':'Davlat boji to‘g‘risidagi qonun','article':'20-modda — faqat bir taraf ozod bo‘lgan bitim','url':party_question([])['source_url'],'find_text':'Davlat boji toʻlashdan bir taraf ozod'}]
        if result['standard_amount'] is None:
            return {**result,'legal_basis':sources}
        return {**result, 'payable_amount':result['standard_amount'], 'saving_amount':0, 'status':'standard',
                 'arithmetic':[f"{result['standard_amount']} × 100% = {result['standard_amount']}"], 'benefit_title':'Bojni ikkinchi taraf to‘laydi' ,
                'explanation':f'11-modda {number}-band bo‘yicha faqat bir taraf davlat bojidan ozod. 20-modda bo‘yicha boshqa taraf ushbu bitim uchun belgilangan bojni to‘liq to‘laydi: {result["standard_amount"]:,} so‘m. Bir tarafning ozodligi butun bitimni bojdan ozod qilmaydi.', 'legal_basis':sources,
                'formula_steps':[f'20-modda: boshqa taraf belgilangan bojni to‘liq to‘laydi — {result["standard_amount"]:,} so‘m.']}
    return {**result,'status':'exempt','payable_amount':0,'saving_amount':result.get('standard_amount'),
            "arithmetic":[f"{result['standard_amount']} × 0% = 0"] if result.get('standard_amount') is not None else [], 'benefit_title':entry['title']+' — davlat bojidan ozod',
            'explanation':f'11-modda {number}-band. {entry["description"]} '+('Ikkala tarafning ozodlik asosi tasdiqlangan deb ko‘rsatildi. ' if transactional else '')+'Mos hujjatlar notarius tomonidan tekshiriladi.',
            'legal_basis':sources, 'next_steps':result.get('next_steps',[])+['Imtiyozga tegishli maqom va ushbu harakatning shartlarini tasdiqlovchi hujjatlarni notariusga ko‘rsating.']}
