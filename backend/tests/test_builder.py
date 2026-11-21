from copy import deepcopy
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


def effect(operation='none',unit='bhm',value='0',basis='initial',field='',times_input=False):
    return dict(operation=operation,unit=unit,value=value,basis=basis,field=field,times_input=times_input)


def definition():
    return {'name':'Sinov kalkulyatori','category':'Yangi xizmat','icon':'car','description':'Admin yaratgan hisob',
            'bhm_amount':440000,'effective_from':'2026-11-20','base':effect('replace','bhm','3'),
            'factors':[{'key':'relative','label':'Xaridor kim?','type':'choice','options':[
                {'value':'parent','label':'Ota-ona','effect':effect('replace','percent','5')},
                {'value':'other','label':'Boshqa shaxs','effect':effect()}]}],
            'sources':[{'title':'4-band o','url':'https://lex.uz/docs/-4680944#-8113528'}]}


@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr('app.main.today',lambda:date(2026,11,20))
    app=create_app(tmp_path/'builder.sqlite3','test-admin-password-123456')
    with TestClient(app) as c:
        c.post('/api/v1/admin/login',json={'password':'test-admin-password-123456'})
        yield c


def create(c,d=None):
    r=c.post('/api/v1/admin/builder',json={'definition':d or definition()})
    assert r.status_code==200,r.text
    return r.json()['calculator']


def preview(c,entry,answers):
    return c.post(f'/api/v1/admin/builder/{entry["id"]}/preview',json={'revision':entry['revision'],'answers':answers})


def publish(c,entry):
    return c.post(f'/api/v1/admin/builder/{entry["id"]}/publish',json={'revision':entry['revision']})


def test_draft_preview_publish_public_schema_and_same_engine(client):
    e=create(client)
    assert e['id'] not in {s['id'] for s in client.get('/api/v1/services').json()['services']}
    assert client.get('/api/v1/calculator/schema',params={'service_id':e['id']}).status_code==404
    assert publish(client,e).status_code==422
    assert preview(client,e,{}).json()['question']['key']=='relative'
    trial=preview(client,e,{'relative':'parent'}).json()['result']
    assert trial['payable_amount']==66000
    p=publish(client,e);assert p.status_code==200,p.text
    version=p.json()['rule_id']
    assert publish(client,e).json()['rule_id']==version
    s=next(s for s in client.get('/api/v1/services').json()['services'] if s['id']==e['id'])
    assert s['category']=='Yangi xizmat' and s['icon']=='car'
    schema=client.get('/api/v1/calculator/schema',params={'service_id':e['id']}).json()
    assert schema['questions'][0]['options'][0]['label']=='Ota-ona'
    live=client.post('/api/v1/calculate',json={'service_id':e['id'],'answers':{'relative':'parent'}}).json()['result']
    assert live['payable_amount']==trial['payable_amount']
    assert live['calculation_id'] and live['rule_version']==version
    assert live['legal_basis'][0]['url'].startswith('https://lex.uz/')


def test_edits_stay_draft_require_retest_and_keep_old_calculations(client):
    e=create(client);preview(client,e,{'relative':'parent'});publish(client,e)
    old=client.post('/api/v1/calculate',json={'service_id':e['id'],'answers':{'relative':'parent'}}).json()['result']
    d=deepcopy(e['definition']);d['base']['value']='4';d['name']='Yangi nom'
    update=client.put(f'/api/v1/admin/builder/{e["id"]}',json={'definition':d,'revision':e['revision']})
    e2=update.json()['calculator'];assert e2['revision']==2 and e2['tested'] is False
    assert publish(client,e2).status_code==422
    live=client.post('/api/v1/calculate',json={'service_id':e['id'],'answers':{'relative':'parent'}}).json()['result']
    assert live['payable_amount']==66000 and live['title']=='Sinov kalkulyatori'
    assert preview(client,e2,{'relative':'parent'}).json()['result']['payable_amount']==88000
    publish(client,e2)
    newer=client.post('/api/v1/calculate',json={'service_id':e['id'],'answers':{'relative':'parent'}}).json()['result']
    assert newer['payable_amount']==88000 and newer['title']=='Yangi nom'
    with client.app.state.database.connect() as db:
        stored=db.execute('SELECT result FROM calculations WHERE public_id=?',(old['calculation_id'],)).fetchone()['result']
        assert '66000' in stored
        assert db.execute("SELECT COUNT(*) FROM rules WHERE service_id=(SELECT id FROM calculators WHERE slug=?) AND status='published'",(e['id'],)).fetchone()[0]==2


def test_stale_update_and_publish_are_rejected(client):
    e=create(client);d=deepcopy(e['definition']);d['description']='O‘zgardi'
    assert client.put(f'/api/v1/admin/builder/{e["id"]}',json={'definition':d,'revision':e['revision']}).status_code==200
    assert client.put(f'/api/v1/admin/builder/{e["id"]}',json={'definition':d,'revision':e['revision']}).status_code==409
    assert preview(client,e,{'relative':'parent'}).status_code==409
    assert publish(client,e).status_code==409


def test_archive_restore_hides_service_but_preserves_history(client):
    e=create(client);preview(client,e,{'relative':'parent'});publish(client,e)
    assert client.delete(f'/api/v1/admin/builder/{e["id"]}').status_code==200
    assert e['id'] not in {s['id'] for s in client.get('/api/v1/services').json()['services']}
    assert client.post('/api/v1/calculate',json={'service_id':e['id'],'answers':{'relative':'parent'}}).status_code==404
    assert client.post(f'/api/v1/admin/builder/{e["id"]}/restore').status_code==200
    assert e['id'] in {s['id'] for s in client.get('/api/v1/services').json()['services']}


def test_source_required_to_publish_and_url_must_be_official(client):
    d=definition();d['sources']=[];e=create(client,d);preview(client,e,{'relative':'parent'})
    assert publish(client,e).status_code==422
    for url in ['javascript:alert(1)','https://lex.uz.evil.test/docs/x','https://user:secret@lex.uz/docs/x','http://lex.uz/docs/x']:
        d=definition();d['sources'][0]['url']=url
        assert client.post('/api/v1/admin/builder',json={'definition':d}).status_code==422


def test_authentication_and_origin_protect_builder(client):
    assert client.post('/api/v1/admin/builder',json={'definition':definition()},headers={'origin':'https://evil.test'}).status_code==403
    client.post('/api/v1/admin/logout')
    for path in ['/api/v1/admin/builder','/api/v1/admin/categories']:
        assert client.get(path).status_code==401
    assert client.post('/api/v1/admin/builder',json={'definition':definition()}).status_code==401


def test_categories_persist_and_future_rules_are_not_public(client):
    assert client.post('/api/v1/admin/categories',json={'name':'Davlat ro‘yxati','icon':'building'}).status_code==200
    assert any(x['name']=='Davlat ro‘yxati' for x in client.get('/api/v1/admin/categories').json()['categories'])
    d=definition();d['effective_from']='2026-12-01';e=create(client,d);preview(client,e,{'relative':'parent'});assert publish(client,e).status_code==200
    assert e['id'] not in {x['id'] for x in client.get('/api/v1/services').json()['services']}


def test_number_input_percentage_minimum_and_invalid_answers(client):
    d=definition();d['factors']=[{'key':'claim','label':'Da’vo summasi','type':'number','maximum':'1000000000000'}]
    d['base']=effect('replace','percent','4','field','claim');d['minimum']='1';d['minimum_unit']='bhm'
    e=create(client,d)
    assert preview(client,e,{'claim':1000000}).json()['result']['payable_amount']==440000
    assert preview(client,e,{'claim':20000000}).json()['result']['payable_amount']==800000
    for a in [{'claim':-1},{'claim':True},{'claim':'NaN'},{'claim':'1e999999'},{'claim':'1e-999999'},{'claim':10**14},{'alien':'x'}]:
        assert preview(client,e,a).status_code==422


def test_sequential_effects_conditions_and_exemption_override_minimum(client):
    d=definition();d['minimum']='1';d['factors'].append({'key':'outside','label':'Idoradan tashqaridami?','type':'choice','options':[{'value':'yes','label':'Ha','effect':effect('multiply','number','2')},{'value':'no','label':'Yo‘q'}]})
    d['rules']=[{'label':'Ikkala shart bajarildi','conditions':[{'field':'relative','value':'parent'},{'field':'outside','value':'yes'}],'effect':effect('exempt')}]
    e=create(client,d)
    assert preview(client,e,{'relative':'parent','outside':'yes'}).json()['result']['payable_amount']==0
    assert preview(client,e,{'relative':'other','outside':'yes'}).json()['result']['payable_amount']==2640000


def test_sum_mode_uses_initial_base_for_each_part(client):
    d=definition();d['combine']='sum';d['factors'][0]['options'][0]['effect']=effect('add','percent','5')
    d['factors'].append({'key':'credit','label':'Kredit','type':'choice','options':[{'value':'yes','label':'Ha','effect':effect('add','percent','10')},{'value':'no','label':'Yo‘q'}]})
    e=create(client,d)
    assert preview(client,e,{'relative':'parent','credit':'yes'}).json()['result']['payable_amount']==198000


def test_sum_rule_without_option_effect_starts_from_zero(client):
    d=definition();d['combine']='sum'
    for o in d['factors'][0]['options']:o['effect']=effect()
    d['rules']=[{'label':'Ota-ona bo‘lsa','conditions':[{'field':'relative','value':'parent'}],'effect':effect('add','percent','5')}]
    e=create(client,d)
    assert preview(client,e,{'relative':'parent'}).json()['result']['payable_amount']==66000


def test_optional_text_conditional_fields_and_numeric_rule(client):
    d=definition();d['factors']+=[{'key':'note','label':'Izoh','type':'text','required':False},
        {'key':'count','label':'Soni','type':'number','when':{'relative':['parent']},'effect':effect('add','bhm','0.1',times_input=True)}]
    e=create(client,d)
    assert preview(client,e,{'relative':'parent'}).json()['question']['key']=='count'
    assert preview(client,e,{'relative':'parent','count':2,'note':'Test'}).json()['result']['payable_amount']==154000
    assert preview(client,e,{'relative':'other','count':'bad hidden value'}).json()['result']['payable_amount']==1320000


@pytest.mark.parametrize('mutation',[
    lambda d:d['factors'].append(deepcopy(d['factors'][0])),
    lambda d:d['factors'][0].update(when={'relative':['parent']}),
    lambda d:d['base'].update(basis='field',field='not_existing',unit='percent'),
    lambda d:d['factors'][0]['options'][0]['effect'].update(operation='multiply',unit='bhm'),
    lambda d:d.update(icon='unknown'),
    lambda d:d.update(minimum='10',maximum='1'),
])
def test_invalid_definitions_are_rejected(client,mutation):
    d=definition();mutation(d)
    assert client.post('/api/v1/admin/builder',json={'definition':d}).status_code==422


def test_fractional_amount_is_not_silently_rounded_or_publish_tested(client):
    d=definition();d['base']=effect('replace','fixed','0.5');d['factors']=[];e=create(client,d)
    result=preview(client,e,{}).json()['result']
    assert result['payable_amount'] is None
    assert publish(client,e).status_code==422


def test_loan_cancellation_explains_percentage_and_keeps_preview_public_identical(client):
    d=definition();d['name']='Qarz shartnomasi';d['base']=effect('replace','percent','25','bhm')
    d['factors']=[{'key':'action','label':'Qanday xizmat kerak?','type':'choice','options':[
        {'value':'certify','label':'Tasdiqlash'},
        {'value':'cancel','label':'Shartnomani bekor qilish','effect':effect('multiply','percent','50')},
    ]}]
    e=create(client,d)
    trial=preview(client,e,{'action':'cancel'}).json()['result']
    assert trial['payable_amount']==55000
    assert '440 000 × 25% = 110 000 so‘m' in trial['explanation']
    assert '110 000 × 50% = 55 000 so‘m' in trial['explanation']
    publish(client,e)
    live=client.post('/api/v1/calculate',json={'service_id':e['id'],'answers':{'action':'cancel'}}).json()['result']
    assert live['explanation']==trial['explanation']


def test_source_section_and_admin_keyword_survive_preview_and_publication(client):
    d=definition()
    d['sources'][0].update(find_text='qarz shartnomalarini tasdiqlaganlik uchun',section='notarial')
    e=create(client,d)
    trial=preview(client,e,{'relative':'parent'}).json()['result']
    assert trial['legal_basis'][0]['find_text']==d['sources'][0]['find_text']
    assert trial['legal_basis'][0]['section']=='notarial'
    publish(client,e)
    public=client.post('/api/v1/calculate',json={'service_id':e['id'],'answers':{'relative':'parent'}}).json()['result']
    assert public['legal_basis']==trial['legal_basis']
