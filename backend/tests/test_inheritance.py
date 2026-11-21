from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr('app.main.today', lambda:date(2026,11,20))
    with TestClient(create_app(tmp_path/'inheritance.sqlite3', 'test-admin-password-123456')) as instance:
        yield instance


BASE = {'property_type':'home', 'certificate_kind':'first', 'minor':'no', 'special_status':'none',
        'lived_before':'no', 'registered':'no', 'lives_after':'no', 'joint_property':'no',
        'share_numerator':1, 'share_denominator':2, 'location':'office'}


def calculate(client, **changes):
    return client.post('/api/v1/calculate', json={'service_id':'notary_inheritance','answers':{**BASE, **changes}})


@pytest.mark.parametrize('kind', ['deposit','salary','pension','government_bond','insurance','copyright','royalty','passenger_insurance'])
def test_statutory_money_and_rights_exemptions(client,kind):
    result = calculate(client,property_type=kind).json()['result']
    assert result['payable_amount']==0
    assert result['status']=='exempt'
    assert any('11-modda' in s['article'] for s in result['legal_basis'])


@pytest.mark.parametrize('special', ['duty_death','guardianship','farmer','dehkan','state_authority','disability_organization'])
def test_individual_and_organization_grounds(client,special):
    result=calculate(client,special_status=special).json()['result']
    assert result['payable_amount']==0
    assert result['saving_amount']==110000
    assert result['next_steps']


@pytest.mark.parametrize('missing', ['lived_before','registered','lives_after'])
def test_all_three_housing_conditions_are_required(client,missing):
    conditions={'lived_before':'yes','registered':'yes','lives_after':'yes',missing:'no'}
    assert calculate(client,**conditions).json()['result']['payable_amount']==110000


def test_housing_and_cooperative_housing_eligibility(client):
    conditions={'lived_before':'yes','registered':'yes','lives_after':'yes'}
    assert calculate(client,**conditions).json()['result']['payable_amount']==0
    assert calculate(client,property_type='housing_coop',**conditions).json()['result']['payable_amount']==0
    # Residence exemption must not leak into a vehicle when hidden form values remain.
    assert calculate(client,property_type='vehicle',**conditions).json()['result']['payable_amount']==110000


def test_minor_does_not_need_residence_proof_and_fraction_is_not_rounded(client):
    answers={**BASE,'minor':'yes','share_denominator':3}
    for key in ['lived_before','registered','lives_after']:
        answers.pop(key)
    result=client.post('/api/v1/calculate',json={'service_id':'notary_inheritance','answers':answers}).json()['result']
    assert result['payable_amount']==0
    assert result['standard_amount'] is None
    assert calculate(client,share_denominator=3).json()['result']['status']=='needs_verification'


def test_ordinary_tariffs_and_location(client):
    assert calculate(client,property_type='other',share_denominator=1).json()['result']['payable_amount']==132000
    assert calculate(client,location='outside').json()['result']['payable_amount']==220000
    assert calculate(client,location='outreach').json()['result']['payable_amount']==110000
    assert calculate(client,property_type='credit_certificate',share_denominator=1).json()['result']['payable_amount']==132000


def test_spouses_own_property_is_excluded(client):
    result=calculate(client,joint_property='yes',estate_numerator=1,estate_denominator=2).json()['result']
    assert result['payable_amount']==55000
    assert calculate(client,joint_property='yes',estate_numerator=3,estate_denominator=2).status_code==422
    assert calculate(client,share_numerator=3).status_code==422


def test_remaining_certificate_credit_is_not_saving(client):
    result=calculate(client,certificate_kind='remaining',share_denominator=1,
                     credit_confirmed='yes',previous_payment=110000).json()['result']
    assert result['total_duty_amount']==220000
    assert result['payable_amount']==110000
    assert result['previous_payment_credit']==110000
    assert result['saving_amount']==0
    assert result['status']=='credit_applied'
    assert calculate(client,certificate_kind='remaining',credit_confirmed='no').json()['result']['payable_amount'] is None
    assert calculate(client,certificate_kind='remaining',credit_confirmed='yes',previous_payment=999999).status_code==422


def test_partial_and_court_reissued_certificate(client):
    assert calculate(client,certificate_kind='partial').json()['result']['payable_amount']==110000
    assert calculate(client,certificate_kind='court_reissue',credit_confirmed='no').json()['result']['status']=='needs_verification'
    result=calculate(client,certificate_kind='court_reissue',credit_confirmed='yes',previous_payment=110000).json()['result']
    assert result['payable_amount']==0
    assert result['status']=='credit_applied'
    assert result['saving_amount']==0


def test_work_insurance_needs_the_employer_policy_condition(client):
    assert calculate(client,property_type='work_insurance',work_policy='yes').json()['result']['payable_amount']==0
    assert calculate(client,property_type='work_insurance',work_policy='no').json()['result']['status']=='needs_verification'


def test_schema_removes_vague_exemption_and_splits_residence_conditions(client):
    schema=client.get('/api/v1/calculator/schema?service_id=notary_inheritance').json()
    questions={q['key']:q for q in schema['questions']}
    assert {'lived_before','registered','lives_after'} <= questions.keys()
    assert all(o['value']!='needs_review' for o in questions['special_status']['options'])
    assert len(schema['sources'])==14
