import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.db import SEED
from app.main import create_app

PASSWORD = 'test-only-admin-password-12345'
ANSWERS = {'vehicle_type': 'car', 'relative_type': 'other', 'bank_credit': 'no', 'damaged': 'no', 'location': 'office', 'special_status': 'none'}


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setattr('app.main.today', lambda: date(2026, 11, 20))
    return create_app(tmp_path / 'test.sqlite3', PASSWORD)


@pytest.fixture
def client(app):
    with TestClient(app) as client:
        yield client


def calc(client, **changes):
    return client.post('/api/v1/calculate', json={'answers': {**ANSWERS, **changes}, 'as_of_date': '2026-11-20'}).json()['result']


def login(client):
    assert client.post('/api/v1/admin/login', json={'password': PASSWORD}).status_code == 200


def draft(client, **changes):
    response = client.post('/api/v1/admin/rules', json={**SEED, **changes})
    assert response.status_code == 200, response.text
    return response.json()['rule']


def test_standard_and_relative_payments(client):
    standard = calc(client)
    relative = calc(client, relative_type='parent')
    assert standard['payable_amount'] == 1_320_000
    assert relative['payable_amount'] == 66_000
    assert relative['saving_amount'] == 1_254_000
    assert relative['formula']['pay_percent'] == '5'
    assert relative['legal_basis'][0]['url'].startswith('https://lex.uz/')
    assert relative['components'][0]['amount'] is None


def test_bank_motorcycle_outside_and_outreach(client):
    assert calc(client, bank_credit='yes')['payable_amount'] == 132_000
    assert calc(client, vehicle_type='motorcycle')['payable_amount'] == 110_000
    assert calc(client, location='outside')['payable_amount'] == 2_640_000
    assert calc(client, location='outreach')['payable_amount'] == 1_320_000


@pytest.mark.parametrize('changes', [{'damaged': 'yes', 'damage_assessed': 'no'}, {'special_status': 'needs_review'}])
def test_unsupported_legal_cases_never_guess(client, changes):
    result = calc(client, **changes)
    assert result['status'] == 'needs_verification'
    assert result['payable_amount'] is None


def test_missing_and_invalid_inputs(client):
    assert client.post('/api/v1/calculate', json={'answers': {}}).json()['question']['key'] == 'vehicle_type'
    assert client.post('/api/v1/calculate', json={'answers': {**ANSWERS, 'relative_type': 'cousin'}}).status_code == 422
    assert client.post('/api/v1/calculate', json={'answers': {**ANSWERS, 'bhm_amount': 1}}).status_code == 422
    old = client.post('/api/v1/calculate', json={'answers': ANSWERS, 'as_of_date': '2020-01-01'}).json()['result']
    assert old['payable_amount'] is None


def test_admin_authentication_and_logout(client):
    assert client.get('/api/v1/admin/rules').status_code == 401
    assert client.post('/api/v1/admin/login', json={'password': 'wrong'}).status_code == 401
    login(client)
    assert client.get('/api/v1/admin/me').status_code == 200
    assert client.post('/api/v1/admin/logout').status_code == 200
    assert client.get('/api/v1/admin/me').status_code == 401


def test_draft_publish_updates_calculation_but_retains_snapshot(client, app):
    old = calc(client, relative_type='parent')
    login(client)
    new = draft(client, relative_pay_percent='6', effective_from='2026-11-20', change_note='Test qoida: faqat test bazasida yangi foiz.')
    assert calc(client, relative_type='parent')['payable_amount'] == 66_000
    assert client.post(f"/api/v1/admin/rules/{new['id']}/publish", json={'reviewed': False}).status_code == 422
    assert client.post(f"/api/v1/admin/rules/{new['id']}/publish", json={'reviewed': True}).status_code == 200
    assert calc(client, relative_type='parent')['payable_amount'] == 79_200
    with app.state.database.connect() as db:
        original = json.loads(db.execute('SELECT result FROM calculations WHERE public_id=?', (old['calculation_id'],)).fetchone()['result'])
        assert original['payable_amount'] == 66_000
        assert db.execute("SELECT COUNT(*) FROM rules WHERE status='published' AND service_id=(SELECT id FROM calculators WHERE slug='notary_car')").fetchone()[0] == 2
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("UPDATE rules SET config='{}' WHERE id=1")


def test_future_rule_does_not_apply_early(client):
    login(client)
    new = draft(client, bhm_amount=500000, effective_from='2027-01-01')
    assert client.post(f"/api/v1/admin/rules/{new['id']}/publish", json={'reviewed': True}).status_code == 200
    assert calc(client)['payable_amount'] == 1_320_000


def test_sources_and_percentages_validated(client):
    login(client)
    assert client.post('/api/v1/admin/rules', json={**SEED, 'law_url': 'https://lex.uz.evil.com/fake'}).status_code == 422
    assert client.post('/api/v1/admin/rules', json={**SEED, 'relative_pay_percent': 105}).status_code == 422
    assert client.post('/api/v1/admin/rules', json={**SEED, 'verified_at': '2027-01-01'}).status_code == 422


def test_cross_site_writes_are_rejected(client):
    assert client.post('/api/v1/admin/login', json={'password': PASSWORD}, headers={'Origin': 'https://other.example'}).status_code == 403


def test_report_ownership_and_idempotency(client, app):
    result = calc(client, relative_type='parent')
    body = {'calculation_id': result['calculation_id'], 'service_id': 'notary_car', 'standard_amount': 1320000, 'paid_amount': 66000}
    with TestClient(app) as stranger:
        assert stranger.post('/api/v1/benefit-reports', json=body).status_code == 404
    first = client.post('/api/v1/benefit-reports', json=body)
    assert first.status_code == 200, first.text
    second = client.post('/api/v1/benefit-reports', json=body)
    assert first.json()['report']['id'] == second.json()['report']['id']
    assert second.json()['impact']['confirmed_reports'] == 1
    assert second.json()['impact']['reported_saving_amount'] == 1254000




def test_table_edit_updates_duty_and_percent_atomically(client, app):
    before = calc(client, relative_type='parent')
    login(client)
    payload = {**SEED, 'car_bhm_multiplier': '4', 'relative_pay_percent': '6', 'effective_from': '2026-11-20', 'reviewed': True, 'change_note': 'Faqat test bazasida boj va foiz tahriri.'}
    response = client.put('/api/v1/admin/calculators/notary_car', json=payload)
    assert response.status_code == 200, response.text
    after = calc(client, relative_type='parent')
    assert after['standard_amount'] == 1760000
    assert after['payable_amount'] == 105600
    with app.state.database.connect() as db:
        assert json.loads(db.execute('SELECT result FROM calculations WHERE public_id=?', (before['calculation_id'],)).fetchone()['result'])['payable_amount'] == 66000
    assert len(client.get('/api/v1/admin/rules').json()['rules']) == 2


def test_table_edit_requires_review_and_admin(client):
    body = {**SEED, 'reviewed': True}
    assert client.put('/api/v1/admin/calculators/notary_car', json=body).status_code == 401
    assert client.delete('/api/v1/admin/calculators/notary_car').status_code == 401
    login(client)
    assert client.put('/api/v1/admin/calculators/notary_car', json={**body, 'reviewed': False}).status_code == 422
    assert len(client.get('/api/v1/admin/rules').json()['rules']) == 1


def test_delete_removes_public_calculator_and_restore_preserves_history(client, app):
    old = calc(client)
    login(client)
    assert client.delete('/api/v1/admin/calculators/notary_car').status_code == 200
    assert 'notary_car' not in {s['id'] for s in client.get('/api/v1/services').json()['services']}
    assert client.get('/api/v1/calculator/schema').status_code == 404
    assert client.post('/api/v1/calculate', json={'answers': ANSWERS}).status_code == 404
    assert client.post('/api/v1/chat', json={'message': 'Avtomobilni sotmoqchiman'}).status_code == 404
    assert client.get('/api/v1/admin/calculators').json()['calculators'][0]['active'] is False
    app.state.database.initialize()
    assert app.state.database.calculator_active() is False
    with app.state.database.connect() as db:
        assert db.execute('SELECT id FROM calculations WHERE public_id=?', (old['calculation_id'],)).fetchone()
        assert db.execute("SELECT COUNT(*) FROM rules WHERE service_id=(SELECT id FROM calculators WHERE slug='notary_car')").fetchone()[0] == 1
    assert client.post('/api/v1/admin/calculators/notary_car/restore').status_code == 200
    assert len(client.get('/api/v1/services').json()['services']) == 15
    assert calc(client)['payable_amount'] == 1320000


def test_deleted_calculator_cannot_be_edited_until_restored(client):
    login(client)
    client.delete('/api/v1/admin/calculators/notary_car')
    assert client.put('/api/v1/admin/calculators/notary_car', json={**SEED, 'reviewed': True}).status_code == 409
