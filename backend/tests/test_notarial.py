from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.notarial import NOTARIAL_IDS


@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr('app.main.today',lambda:date(2026,11,20))
    with TestClient(create_app(tmp_path/'notarial.sqlite3','test-admin-password-123456')) as instance:
        yield instance


CAR={'vehicle_type':'car','relative_type':'other','bank_credit':'no','damaged':'no','location':'office','special_status':'disability_organization'}
PROPERTY={'region':'other','transaction':'ordinary','relative_type':'other','location':'office','special_status':'state_orphan_home'}
LEASE={'party_type':'legal','operation':'certify','location':'office','special_status':'disability_organization'}


@pytest.mark.parametrize('service_id',NOTARIAL_IDS)
def test_all_notarial_services_include_twenty_scoped_cases(client,service_id):
    cases=client.get('/api/v1/calculator/schema',params={'service_id':service_id}).json()['notarial_exemptions']
    assert [case['number'] for case in cases]==list(range(1,21))
    assert all(case['url'].startswith('https://lex.uz/docs/-4680944#') and case['find_text'] for case in cases)
    assert all(case['applicable']==(service_id in case['services']) for case in cases)
    assert cases[3]['applicable']
    assert not cases[5]['applicable'] # Pension receipt power is not a vehicle/property power.


@pytest.mark.parametrize('service_id,answers,total',[
    ('notary_car',CAR,1320000),('notary_property',PROPERTY,220000),('notary_lease',LEASE,220000),
])
def test_only_one_exempt_party_does_not_zero_transaction_fee(client,service_id,answers,total):
    result=client.post('/api/v1/calculate',json={'service_id':service_id,'answers':{**answers,'exemption_parties':'one'}}).json()['result']
    assert result['payable_amount']==total
    assert result['saving_amount']==0
    assert result['status']=='standard'
    assert any('faqat bir taraf' in source['article'] for source in result['legal_basis'])


@pytest.mark.parametrize('service_id,answers', [('notary_car',CAR),('notary_property',PROPERTY),('notary_lease',LEASE)])
def test_both_parties_with_documented_grounds_are_exempt(client,service_id,answers):
    result=client.post('/api/v1/calculate',json={'service_id':service_id,'answers':{**answers,'exemption_parties':'both'}}).json()['result']
    assert result['payable_amount']==0
    assert result['status']=='exempt'


def test_party_condition_is_required_and_not_assumed(client):
    response=client.post('/api/v1/calculate',json={'service_id':'notary_car','answers':CAR}).json()
    assert response['result'] is None
    assert response['question']['key']=='exemption_parties'


@pytest.mark.parametrize('service_id',['notary_vehicle_power','notary_property_power'])
def test_organization_power_is_a_unilateral_notarial_act(client,service_id):
    result=client.post('/api/v1/calculate',json={'service_id':service_id,'answers':{'relative_type':'other','location':'office','special_status':'disability_organization'}}).json()['result']
    assert result['status']=='exempt' and result['payable_amount']==0


def test_organization_and_individual_party_types_cannot_be_mixed(client):
    result=client.post('/api/v1/calculate',json={'service_id':'notary_lease','answers':{**LEASE,'party_type':'individual','relative_type':'other','exemption_parties':'both'}}).json()['result']
    assert result['payable_amount'] is None


def test_non_notarial_services_have_no_notarial_reference(client):
    assert client.get('/api/v1/calculator/schema?service_id=court_civil').json()['notarial_exemptions']==[]




@pytest.mark.parametrize('residual,expected',[(0,0),(60,792000),(100,1320000)])
def test_expert_residual_adjusts_damaged_car_duty(client,residual,expected):
    answers={**CAR,'special_status':'none','damaged':'yes','damage_assessed':'yes','residual_percent':residual}
    result=client.post('/api/v1/calculate',json={'answers':answers}).json()['result']
    assert result['payable_amount']==expected
    assert 'Ekspert' in result['explanation']


def test_unassessed_damage_cannot_be_zeroed_by_selected_exemption(client):
    answers={**CAR,'damaged':'yes','damage_assessed':'no','exemption_parties':'both'}
    result=client.post('/api/v1/calculate',json={'answers':answers}).json()['result']
    assert result['status']=='needs_verification'
    assert result['payable_amount'] is None


def test_expert_percentage_is_conditional_and_bounded(client):
    answers={**CAR,'special_status':'none','damaged':'yes','damage_assessed':'yes'}
    data=client.post('/api/v1/calculate',json={'answers':answers}).json()
    assert data['question']['key']=='residual_percent'
    for bad in [-1,101,True,60.12345]:
        assert client.post('/api/v1/calculate',json={'answers':{**answers,'residual_percent':bad}}).status_code==422


def test_damage_does_not_stack_with_relative_or_credit(client):
    answers={**CAR,'special_status':'none','damaged':'yes','damage_assessed':'yes','residual_percent':60,'bank_credit':'yes'}
    result=client.post('/api/v1/calculate',json={'answers':answers}).json()['result']
    assert result['payable_amount'] is None


@pytest.mark.parametrize('parties,expected',[('one',1320000),('both',0)])
def test_old_kinship_answer_does_not_block_organization_transaction(client,parties,expected):
    data=client.post('/api/v1/calculate',json={'answers':{**CAR,'relative_type':'parent','exemption_parties':parties}}).json()
    assert data['result']['payable_amount']==expected
    assert data['result']['status']!='needs_verification'
    assert 'Imtiyozlar birga tekshiriladi' not in data['result']['benefit_title']


@pytest.mark.parametrize('parties,expected',[('one',220000),('both',0)])
def test_orphan_home_and_related_seller_follow_article_twenty(client,parties,expected):
    data=client.post('/api/v1/calculate',json={'service_id':'notary_property','answers':{**PROPERTY,'relative_type':'parent','exemption_parties':parties}}).json()
    assert data['result']['payable_amount']==expected
    assert '50%i' not in data['result']['explanation']


@pytest.mark.parametrize('service_id',['notary_vehicle_power','notary_property_power'])
def test_hidden_kinship_does_not_block_exempt_organization_power(client,service_id):
    result=client.post('/api/v1/calculate',json={'service_id':service_id,'answers':{'special_status':'disability_organization','relative_type':'parent','location':'office'}}).json()['result']
    assert result['payable_amount']==0


def test_capacity_questions_exclude_incompatible_kinship(client):
    from app.catalog import applies
    for service_id in ['notary_car','notary_property','notary_vehicle_power','notary_property_power']:
        questions=client.get('/api/v1/calculator/schema',params={'service_id':service_id}).json()['questions']
        kinship=next(q for q in questions if q['key']=='relative_type')
        assert not applies(kinship,{'special_status':'disability_organization'})
        assert applies(kinship,{'special_status':'none'})


@pytest.mark.parametrize('changes,expected',[
    ({'transaction_kind':'exchange'},1320000),
    ({'transaction_kind':'exchange','relative_type':'parent'},66000),
    ({'transaction_kind':'exchange','vehicle_type':'motorcycle'},110000),
    ({'transaction_kind':'exchange','bank_credit':'yes'},1320000),
    ({'transaction_kind':'sale','bank_credit':'yes'},132000),
    ({'damaged':'yes','damage_assessed':'yes','residual_percent':60.5},798600),
])
def test_vehicle_tariff_note_cases(client,changes,expected):
    answers={**CAR,'special_status':'none',**changes}
    data=client.post('/api/v1/calculate',json={'answers':answers}).json()
    result=data['result']
    assert result['payable_amount']==expected
    assert result['formula']['charged_vehicle_count']==1
    if changes.get('transaction_kind')=='exchange':
        assert 'faqat bitta transport' in result['explanation']


@pytest.mark.parametrize('vehicle,location,expected,parts',[
    ('car','office',198000,[66000,132000]),
    ('car','outside',396000,[132000,264000]),
    ('motorcycle','office',16500,[5500,11000]),
])
def test_mentor_combined_kinship_credit_is_sum_of_two_parts(client,vehicle,location,expected,parts):
    data=client.post('/api/v1/calculate',json={'answers':{**CAR,'special_status':'none','vehicle_type':vehicle,'relative_type':'grandparent','bank_credit':'yes','location':location}}).json()['result']
    assert data['payable_amount']==expected
    assert [p['amount'] for p in data['duty_breakdown']]==parts
    assert sum(parts)==data['payable_amount']
    assert data['formula']['pay_percent']=='15'
    assert 'mentor' in data['interpretation_note']
