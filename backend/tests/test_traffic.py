from fastapi.testclient import TestClient

from app.main import create_app
from traffic_presets import install_traffic, presets


def test_published_admin_fines_and_boundary_amounts(tmp_path):
    password = 'test-admin-traffic-2048'
    app = create_app(tmp_path / 'test.db', password)
    install_traffic(app, password)
    install_traffic(app, password)
    with TestClient(app) as client:
        available = client.get('/api/v1/services').json()['services']
        for slug, template, examples in presets():
            key = 'custom_' + slug
            assert sum(x['id'] == key and x['charge_type'] == 'fine' for x in available) == 1
            assert len(app.state.database.all_rules(key)) == 1
            for answers, expected in examples:
                result = client.post('/api/v1/calculate', json={'service_id':key, 'as_of_date':'2026-11-21','answers':answers}).raise_for_status().json()['result']
                assert result['payable_amount'] == expected
                assert result['status'] == 'standard'
                assert result['legal_basis'][0]['url'] == template['sources'][0]['url']
        client.post('/api/v1/admin/login',json={'password':password}).raise_for_status()
        client.delete('/api/v1/admin/builder/custom_traffic_speed').raise_for_status()
    install_traffic(app, password)
    assert not app.state.database.calculator_active('custom_traffic_speed')
