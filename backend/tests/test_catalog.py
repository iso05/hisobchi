from datetime import date
import pytest
from fastapi.testclient import TestClient
from app.catalog import BY_ID, CATALOG, applies
from app.main import create_app


@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr('app.main.today',lambda:date(2026,11,20))
    with TestClient(create_app(tmp_path/'catalog.sqlite3','test-admin-password-123456')) as instance:
        yield instance


BASE = {'location':'office','special_status':'none'}
PROPERTY = {**BASE,'region':'capital','transaction':'ordinary','relative_type':'other'}
POWER = {**BASE,'relative_type':'other'}
LEASE = {**BASE,'party_type':'individual','relative_type':'other','operation':'certify'}
HERITAGE = {**BASE,'property_type':'home','minor':'no','lived_before':'no','registered':'no','lives_after':'no','certificate_kind':'first','joint_property':'no','share_numerator':1,'share_denominator':2}
CIVIL = {'claim_type':'debt','stage':'first','claim_amount':20000000,'mixed_claims':'no','special_status':'none'}
ECON = {'claim_amount':40000000,'stage':'first','small_business':'no','mixed_claims':'no','special_status':'none'}
EPOWER = {'duration':'one_month','recipient':'other','benefit_category':'none'}
PATENT = {'object_type':'invention','applicant_type':'individual','object_count':1,'description_pages':35,'individual_benefit':'none'}

# Expected amounts are independent worked examples from the cited legal tariffs.
CASES = [
    ('notary_property',PROPERTY,440000),
    ('notary_property',{**PROPERTY,'region':'other'},220000),
    ('notary_property',{**PROPERTY,'region':'nukus'},440000),
    ('notary_property',{**PROPERTY,'location':'outside'},880000),
    ('notary_property',{**PROPERTY,'location':'outreach'},440000),
    ('notary_property',{**PROPERTY,'special_status':'disability_organization','exemption_parties':'both'},0),
    ('notary_property',{**PROPERTY,'special_status':'state_orphan_home','exemption_parties':'both'},0),
    ('notary_property',{**PROPERTY,'special_status':'islamic_finance','exemption_parties':'both'},0),
    ('notary_property',{**PROPERTY,'relative_type':'parent'},220000),
    ('notary_property',{**PROPERTY,'region':'other','relative_type':'parent'},110000),
    ('notary_property',{**PROPERTY,'region':'tashkent','transaction':'foreign_new','special_area':'tashkent_city','contract_amount':2000000000},200000000),
    ('notary_property',{**PROPERTY,'region':'other','transaction':'foreign_new','special_area':'tashkent_region','contract_amount':1452000000},145200000),
    ('notary_property',{**PROPERTY,'transaction':'resale_special','resale_period':'within'},176000000),
    ('notary_vehicle_power',POWER,880000),
    ('notary_vehicle_power',{**POWER,'relative_type':'nephew_niece'},220000),
    ('notary_vehicle_power',{**POWER,'location':'outside'},1760000),
    ('notary_vehicle_power',{**POWER,'location':'detention'},880000),
    ('notary_property_power',POWER,220000),
    ('notary_property_power',{**POWER,'relative_type':'spouse'},110000),
    ('notary_lease',LEASE,110000),
    ('notary_lease',{**LEASE,'relative_type':'parent'},44000),
    ('notary_lease',{**LEASE,'party_type':'legal'},220000),
    ('notary_lease',{**LEASE,'operation':'cancel'},55000),
    ('notary_lease',{**LEASE,'operation':'cancel','relative_type':'parent'},22000),
    ('notary_inheritance',HERITAGE,110000),
    ('notary_inheritance',{**HERITAGE,'lived_before':'yes','registered':'yes','lives_after':'yes'},0),
    ('notary_inheritance',{**HERITAGE,'minor':'yes','share_denominator':3},0),
    ('notary_inheritance',{**HERITAGE,'property_type':'deposit'},0),
    ('court_civil',CIVIL,800000),
    ('court_civil',{**CIVIL,'claim_amount':1000000},440000),
    ('court_civil',{**CIVIL,'stage':'appeal'},400000),
    ('court_civil',{k:v for k,v in {**CIVIL,'claim_type':'salary'}.items() if k!='claim_amount'},0),
    ('court_civil',{**CIVIL,'claim_type':'alimony'},0),
    ('court_civil',{**CIVIL,'claim_type':'consumer'},0),
    ('court_economic',ECON,800000),
    ('court_economic',{**ECON,'claim_amount':1000000},440000),
    ('court_economic',{**ECON,'small_business':'yes'},400000),
    ('court_economic',{**ECON,'stage':'appeal'},400000),
    ('vehicle_power_electronic',EPOWER,88000),
    ('vehicle_power_electronic',{**EPOWER,'duration':'six_months'},440000),
    ('vehicle_power_electronic',{**EPOWER,'duration':'three_years'},880000),
    ('vehicle_power_electronic',{**EPOWER,'benefit_category':'disability'},44000),
    ('patent_application',PATENT,880000),
    ('patent_application',{**PATENT,'object_count':3,'description_pages':40},1782000),
    ('patent_application',{**PATENT,'object_count':3,'description_pages':40,'individual_benefit':'disability2'},178200),
    ('patent_application',{**PATENT,'object_count':3,'description_pages':40,'individual_benefit':'education'},1247400),
    ('patent_application',{'object_type':'invention','applicant_type':'legal','object_count':2,'description_pages':36,'legal_benefit':'small_or_education'},1986600),
    ('patent_application',{'object_type':'utility','applicant_type':'individual','object_count':2,'individual_benefit':'none'},1320000),
]


@pytest.mark.parametrize('service_id,answers,expected',CASES)
def test_worked_legal_examples(client,service_id,answers,expected):
    response = client.post('/api/v1/calculate',json={'service_id':service_id,'answers':answers})
    assert response.status_code==200,response.text
    result = response.json()['result']
    assert result is not None,response.json()
    assert result['payable_amount']==expected,result
    assert result['rule_version']
    assert all(source['url'].startswith('https://lex.uz/') for source in result['legal_basis'])
    assert result['review_status']==('source_compared' if service_id.startswith('notary_') else 'awaiting_legal_review')


@pytest.mark.parametrize('service_id,answers',[
    ('notary_property',{**PROPERTY,'region':'other','transaction':'foreign_new','special_area':'tashkent_city','contract_amount':1000000}),
    ('notary_property',{**PROPERTY,'region':'other','transaction':'foreign_new','special_area':'tashkent_region','contract_amount':1451999999}),
    ('notary_property',{**PROPERTY,'region':'nukus','transaction':'foreign_new','special_area':'tashkent_region','contract_amount':2000000000}),
    ('notary_property',{**PROPERTY,'transaction':'resale_special','resale_period':'within','special_status':'state_orphan_home','exemption_parties':'both'}),
    ('notary_inheritance',{**HERITAGE,'certificate_kind':'remaining','credit_confirmed':'no'}),
    ('notary_inheritance',{**HERITAGE,'share_denominator':3}),
    ('court_civil',{**CIVIL,'mixed_claims':'yes'}),
    ('court_civil',{**CIVIL,'claim_type':'salary','stage':'appeal'}),
    ('court_economic',{**ECON,'small_business':'yes','stage':'appeal'}),
    ('vehicle_power_electronic',{**EPOWER,'recipient':'relative'}),
    ('vehicle_power_electronic',{**EPOWER,'benefit_category':'registry'}),
    ('patent_application',{**PATENT,'individual_benefit':'multiple'}),
])
def test_uncertain_cases_are_explicit(client,service_id,answers):
    result = client.post('/api/v1/calculate',json={'service_id':service_id,'answers':answers}).json()['result']
    assert result['status']=='needs_verification'
    assert result['payable_amount'] is None
    assert result['explanation']


def test_catalog_has_fifteen_real_schemas_and_sources(client):
    services = client.get('/api/v1/services').json()['services']
    assert len(services)==15
    for item in services:
        schema = client.get('/api/v1/calculator/schema',params={'service_id':item['id']}).json()
        assert schema['questions'] and schema['sources']
        assert client.get('/api/v1/rules/current',params={'service_id':item['id']}).json()['rule']['service_id']==item['id']


def test_conditional_fields_are_not_demanded(client):
    # Utility-model filing does not inherit the invention-only page surcharge.
    body = {'service_id':'patent_application','answers':{'object_type':'utility','applicant_type':'individual','object_count':1,'individual_benefit':'education'}}
    assert client.post('/api/v1/calculate',json=body).json()['result']['payable_amount']==616000
    assert client.post('/api/v1/calculate',json={'service_id':'court_civil','answers':{'claim_type':'salary','stage':'first','mixed_claims':'no','special_status':'none'}}).json()['result']['payable_amount']==0


def test_invalid_numeric_values_and_inheritance_share(client):
    for amount in [-1,0,1.5,True,'20000000']:
        response = client.post('/api/v1/calculate',json={'service_id':'court_civil','answers':{**CIVIL,'claim_amount':amount}})
        assert response.status_code==422,response.text
    assert client.post('/api/v1/calculate',json={'service_id':'notary_inheritance','answers':{**HERITAGE,'share_numerator':3,'share_denominator':2}}).status_code==422
    assert client.post('/api/v1/calculate',json={'service_id':'court_civil','answers':{**CIVIL,'claim_type':{'invalid':'object'}}}).status_code==422


def test_editing_one_calculator_does_not_change_another(client):
    assert client.post('/api/v1/admin/login',json={'password':'test-admin-password-123456'}).status_code==200
    catalog = client.get('/api/v1/admin/calculators').json()['calculators']
    target = next(c for c in catalog if c['id']=='court_civil')
    rule = target['rule']['config']
    rule['parameters']['claim_percent']='5'
    rule.update(reviewed=True,change_note='Test: faqat fuqarolik sudining foizi o‘zgartirildi.')
    response = client.put('/api/v1/admin/calculators/court_civil',json=rule)
    assert response.status_code==200,response.text
    civil = client.post('/api/v1/calculate',json={'service_id':'court_civil','answers':CIVIL}).json()['result']
    econ = client.post('/api/v1/calculate',json={'service_id':'court_economic','answers':ECON}).json()['result']
    assert civil['payable_amount']==1000000
    assert econ['payable_amount']==800000
    rule['parameters']['malicious_formula']='1'
    assert client.put('/api/v1/admin/calculators/court_civil',json=rule).status_code==422


def test_archive_is_scoped_to_one_service(client):
    client.post('/api/v1/admin/login',json={'password':'test-admin-password-123456'})
    assert client.delete('/api/v1/admin/calculators/patent_application').status_code==200
    assert len(client.get('/api/v1/services').json()['services'])==14
    assert client.post('/api/v1/calculate',json={'service_id':'court_civil','answers':CIVIL}).json()['result']['payable_amount']==800000
    assert client.post('/api/v1/calculate',json={'service_id':'patent_application','answers':PATENT}).status_code==404
    assert client.post('/api/v1/admin/calculators/patent_application/restore').status_code==200




@pytest.mark.parametrize('service,answers,fee', [
    ('court_divorce', {'marriage':'repeat','division':'yes','claim_amount':20_000_000}, 2_560_000),
    ('court_divorce', {'marriage':'first','division':'yes','claim_amount':500_000}, 1_320_000),
    ('court_divorce', {'marriage':'statutory','division':'no'}, 8_800),
    ('court_copies', {'court_kind':'economic','pages':5,'business_relief':'yes'}, 22_000),
    ('court_copies', {'court_kind':'civil','pages':5,'business_relief':'no'}, 44_000),
    ('court_economic_filing', {'filing':'insolvency','business_relief':'yes'}, 660_000),
    ('court_economic_filing', {'filing':'contract','business_relief':'no'}, 4_400_000),
    ('court_special_proceeding', {'fact':'paternity'}, 0),
    ('court_special_proceeding', {'fact':'ordinary'}, 440_000),
    ('court_nonproperty', {'subject':'lease','business_relief':'yes'}, 440_000),
])
def test_court_filing_fees(client, service, answers, fee):
    result = client.post('/api/v1/calculate', json={'service_id':service,'answers':answers}).json()['result']
    assert result['payable_amount'] == fee
    assert result['arithmetic'] and result['legal_basis']


@pytest.mark.parametrize('service,answers', [
    ('notary_car', {**POWER,'vehicle_type':'car','transaction_kind':'sale','bank_credit':'no','damaged':'no'}),
    ('notary_vehicle_power', POWER), ('notary_property_power', POWER),
    ('notary_property', PROPERTY), ('notary_lease', {**LEASE,'party_type':'legal'}),
    ('notary_inheritance', HERITAGE),
])
def test_unsure_benefit_preserves_other_answers(client, service, answers):
    schema = client.get('/api/v1/calculator/schema',params={'service_id':service}).json()
    benefit = next(q for q in schema['questions'] if q['key'] == 'special_status')
    assert benefit['label'] == 'Mavjud imtiyozlar'
    assert {'value':'unsure','label':'Bilmayman'} in benefit['options']
    def get(status):
        return client.post('/api/v1/calculate',json={'service_id':service,'answers':{**answers,'special_status':status}}).json()['result']
    result = get('unsure')
    assert result['benefit_unspecified']
    assert result['payable_amount'] is not None and result['payable_amount'] == get('none')['payable_amount']
