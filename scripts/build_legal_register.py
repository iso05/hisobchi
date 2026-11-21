"""Generate the exact source register and verify every highlighted phrase exists."""
import csv
import hashlib
import json
import re
import sys
import urllib.request
from html import unescape
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
sys.stdout.reconfigure(encoding='utf-8')
from app.catalog import CATALOG, LAW, EPOWER_SOURCE, BHM_SOURCE
from app.notarial import ARTICLE_11

source_dir = ROOT/'docs/sources'
source_dir.mkdir(exist_ok=True)
snapshots = {}
for base, name in [(LAW,'davlat-boji'),(EPOWER_SOURCE,'elektron-ishonchnoma'),(BHM_SOURCE,'bhm')]:
    path = source_dir/(name+'.html')
    if not path.exists():
        path.write_bytes(urllib.request.urlopen(base,timeout=30).read())
    data = path.read_bytes()
    html = data.decode('utf-8')
    html = re.sub(r'<(script|style)\b[^>]*>.*?</\1>','',html,flags=re.S|re.I)
    clean = unescape(re.sub('<[^>]+>',' ',html))
    clean = re.sub(r'\s+',' ',clean)
    snapshots[base] = {'sha256':hashlib.sha256(data).hexdigest(),'text':clean,'local_file':str(path)}

for item in ARTICLE_11:
    if item['find_text'] not in snapshots[LAW]['text']:
        raise ValueError(f"Missing Article 11 phrase: {item['number']}")
(ROOT/'docs/NOTARIAL_IMTIYOZLAR.json').write_text(json.dumps({'checked_at':'2026-11-20','source':LAW,'cases':ARTICLE_11},ensure_ascii=False,indent=2),encoding='utf-8')

rows = []
for index, item in enumerate(CATALOG,1):
    for source in item['sources']:
        base = source['url'].split('?')[0].split('#')[0]
        if source['find_text'] not in snapshots[base]['text']:
            raise ValueError(f"Missing source phrase: {item['id']} / {source['find_text']}")
        rows.append({'number':index,'calculator':item['name'],'service_id':item['id'],'article':source['article'],'specific_url':source['url'],'find_text':source['find_text'],'retrieved_date':'2026-11-20','source_sha256':snapshots[base]['sha256']})

with (ROOT/'docs/KALKULYATOR_MANBALARI.csv').open('w',encoding='utf-8-sig',newline='') as stream:
    writer=csv.DictWriter(stream,fieldnames=list(rows[0]))
    writer.writeheader();writer.writerows(rows)
(ROOT/'docs/KALKULYATOR_MANBALARI.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
lines=['# 10 ta kalkulyatorning qonuniy manbalari','', 'Manba o‘qilgan sana: **2026-11-20**. Barcha 10 kalkulyator jamoaning qo‘lda qonun bo‘yicha tekshiruvi uchun tayyorlangan. Bu tekshiruvdan o‘tgan rasmiy davlat xizmati emas.','', 'Havolalar Lex.uz hujjatining amaldagi sahifasi va mavjud bo‘lim belgilariga yo‘naltirilgan. Manba matni 20.11.2026 kuni o‘qilgan; havola tahrirni muzlatmaydi. Havolaga aniq matnni ajratish belgisi qo‘shilgan. Bu imkonni qo‘llamaydigan brauzerda **Ctrl+F** orqali ko‘rsatilgan iborani toping.','',f'Umumiy BHM: [PF-115, 3-band b(ii)]({BHM_SOURCE}), 01.09.2026dan 440000 so‘m. Oldingi davrlar tarifi kiritilmagan.','', 'Har bir natija faqat nomlangan davlat boji/bosqich uchun. Gerb yig‘imi, huquqiy-texnik, pochta va keyingi patent bosqichlari xarajatlari hisobga olinmagan.','']
for index,item in enumerate(CATALOG,1):
    lines += [f"## {index}. {item['name']}",'',f"Qamrov: {item['scope']}",'']
    for source in item['sources']:
        lines += [f"- [{source['article']}]({source['url']})",f"  Qidiruv: `{source['find_text']}`"]
    lines += ['', 'Tekshiriladigan istisnolar: '+ '; '.join(item['exceptions'])+'.','']
    if item['parameters']:
        lines += ['Boshlang‘ich qiymatlar: '+ '; '.join(f"{p['label']}: {p['value']} {p['unit']}" for p in item['parameters'])+'.','']
    else:
        lines += ['Boshlang‘ich qiymatlar: avtomobil 3 BHM; mototransport 0.25 BHM; qarindoshga belgilangan bojning 5%i, bank kreditiga 10%i to‘lanadi.','']
lines += ['## Qo‘lda qabul qilish tartibi','','Har bir xizmat uchun: asosiy stavka, minimum, imtiyozning qo‘llanish sharti, to‘lanadigan ulush va chegirma farqi, istisnolar, manba tahriri va misol hisobni tekshiring. Xato topilsa admin jadvalidan aynan shu kalkulyator stavkasini yangi versiya bilan tahrirlang. Qoidalar o‘zgarishi avtomatik huquqiy tasdiqlash hisoblanmaydi.','', 'Noaniq kombinatsiyalar `needs_verification` qaytaradi. Kasr so‘m hosil bo‘lib, yaxlitlash qoidasi tasdiqlanmagan holatda ham yakuniy summa berilmaydi.']
(ROOT/'docs/KALKULYATOR_MANBALARI.md').write_text('\n'.join(lines),encoding='utf-8')
print(f'Checked {len(CATALOG)} calculators and {len(rows)} exact source phrases. Register files written.')
