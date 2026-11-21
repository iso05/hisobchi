"""Install the two checkpoint fines through the same authenticated API as the admin UI."""
from fastapi.testclient import TestClient

CATEGORY = 'Yo‘l harakati jarimalari'
CODE = 'https://lex.uz/uz/acts/-97664#'
BHM = {'title': 'PF-115, 3-band (b)(ii) · BHM', 'url': 'https://lex.uz/docs/-8283656#-8283949'}


def rate(multiplier):
    return {'operation': 'replace', 'unit': 'bhm', 'value': str(multiplier)}


def presets():
    common = {'category': CATEGORY, 'effective_from': '2026-09-01', 'bhm_amount': 440000, 'base': rate(0)}
    rules = []
    for low, high, multiplier in [(5,25,1), (25,45,5), (45,65,9), (65,None,15)]:
        condition = {'field': 'radar_speed', 'minus_field': 'speed_limit'}
        conditions = [{**condition, 'op': 'gt', 'value': str(low)}]
        if high is not None:
            conditions.append({**condition, 'op': 'lte', 'value': str(high)})
        rules.append({'label': f'5 km/soat chegirilgach · {multiplier} BHM', 'conditions': conditions, 'effect': rate(multiplier)})
    speed = {**common, 'name': 'Tezlikni oshirish jarimasi', 'icon': 'car',
             'description': 'Radar qayd etgan tezlikdan 5 km/soat avtomatik ayiriladi. To‘liq jarima hisoblanadi.',
             'factors': [{'key':'speed_limit','label':'Yo‘ldagi tezlik cheklovi (km/soat)','type':'number','minimum':1},
                         {'key':'radar_speed','label':'Radar ko‘rsatgan tezlik (5 km/soat ayirilmasdan)','type':'number'}],
             'rules': rules, 'sources':[{'title':'MJtK 128³-modda · tezlik stavkalari','url':CODE+'-7400359'},
                                        {'title':'MJtK 128³-modda · 5 km/soat chegirma','url':CODE+'-7400397'},BHM]}
    signal = {**common, 'name':'Svetofor va to‘xtash chizig‘i jarimasi', 'icon':'shield',
              'description':'Taqiqlovchi signal yoki tartibga soluvchining taqiqlovchi ishorasida sodir etilgan bitta holat uchun.',
              'factors':[{'key':'signal_action','label':'Taqiqlovchi signal yoki ishorada nima sodir bo‘ldi?',
                          'options':[{'value':'stop_line','label':'Faqat to‘xtash chizig‘ini bosib kirdim','effect':rate('0.5')},
                                     {'value':'passed_signal','label':'Taqiqlovchi signal yoki ishorada o‘tdim','effect':rate(3)}]}],
              'sources':[{'title':'MJtK 128⁴-modda, 1-qism · chiziqni bosish','url':CODE+'-4659123'},
                         {'title':'MJtK 128⁴-modda, 2-qism · taqiqlovchi ishorada o‘tish','url':CODE+'-7400413'},BHM]}
    return [('traffic_speed',speed,[({'speed_limit':60,'radar_speed':60+x},m*440000) for x,m in
                                    [(0,0),(5,0),(6,1),(25,1),(26,5),(45,5),(46,9),(65,9),(66,15)]]),
            ('traffic_signal',signal,[({'signal_action':'stop_line'},220000),({'signal_action':'passed_signal'},1320000)])]


def loan_preset():
    field = 'f_b45a642cd6c5'
    half = {'operation':'multiply', 'unit':'percent', 'value':'50', 'basis':'initial'}
    choices = [('o_91acfc5d95cd','Shartnomani tasdiqlash',{},110000),
               ('o_c209c845036c','Shartnomani o‘zgartirish',half,55000),
               ('o_c4d15080f5c1','Shartnomani bekor qilish',half,55000)]
    definition = {
        'name':'Qarz shartnomasi', 'category':'Notarial', 'icon':'file',
        'description':'Qarz shartnomasini notariusda tasdiqlash, o‘zgartirish yoki bekor qilish.',
        'effective_from':'2026-11-20', 'bhm_amount':440000,
        'base':{'operation':'replace','unit':'percent','value':'25','basis':'bhm'},
        'factors':[{'key':field,'label':'Qanday xizmat kerak?', 'options':[
            {'value':value,'label':label,'effect':effect} for value,label,effect,_ in choices]}],
        'sources':[{'title':'Ilova, 4-band “z” va izohi','section':'notarial',
                    'url':'https://lex.uz/docs/-4680944#-8113528',
                    'find_text':'qarz shartnomalarini tasdiqlaganlik uchun'}],
    }
    return ('loan_contract', definition, [({field:value}, amount) for value,_,_,amount in choices])


def install_traffic(app, password, extra=()):
    from app.builder import Definition
    with TestClient(app, base_url='https://testserver') as client:
        def post(path, body):
            response = client.post('/api/v1/admin/'+path,json=body)
            response.raise_for_status()
            return response.json()
        post('login', {'password':password})
        try:
            existing = {v['id']:v for v in client.get('/api/v1/admin/builder').raise_for_status().json()['calculators']}
            for slug, definition, trials in [*presets(), *extra]:
                key = 'custom_'+slug
                if slug == 'loan_contract' and 'custom_46d0f29997774413' in existing:
                    continue  # Keep the original admin-created checkpoint calculator.
                item = existing.get(key)
                if item is None:
                    item = post('builder', {'slug':slug,'definition':definition})['calculator']
                if item['published'] or not item['active'] or item['definition'] != Definition.model_validate(definition).model_dump(mode='json'):
                    continue
                path = 'builder/'+key
                for answers, expected in trials:
                    result = post(path+'/preview', {'revision':item['revision'],'answers':answers})['result']
                    if result is None or result['payable_amount'] != expected:
                        raise ValueError(f'{key}: expected {expected}')
                post(path+'/publish', {'revision':item['revision']})
        finally:
            post('logout', {})


if __name__ == '__main__':
    import os
    from app.main import app
    install_traffic(app, os.environ['ADMIN_PASSWORD'])
