import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.db import Database
from app.main import create_app


def test_legacy_rows_keep_public_references_and_backup(tmp_path):
    path = tmp_path / 'old.sqlite3'
    with sqlite3.connect(path) as db:
        db.executescript("""
            CREATE TABLE rules(id INTEGER PRIMARY KEY, status TEXT, effective_from TEXT, config TEXT, created_at TEXT, published_at TEXT);
            INSERT INTO rules VALUES(42,'published','2026-09-01','{}','2026-11-18 16:54:32','2026-11-19 03:11:02');
            CREATE TABLE calculations(id TEXT PRIMARY KEY, owner TEXT, rule_id INTEGER, answers TEXT, result TEXT, created_at TEXT);
            INSERT INTO calculations VALUES('old-reference','owner',42,'{}','{"service_id":"notary_car"}','2026-11-20 01:04:05');
            CREATE TABLE reports(id TEXT PRIMARY KEY, calculation_id TEXT, standard_amount INTEGER, paid_amount INTEGER, saving_amount INTEGER, created_at TEXT);
            INSERT INTO reports VALUES('old-report','old-reference',100,20,80,'2026-11-20 01:05:00');
        """)
    model = Database(path)
    model.initialize()
    model.initialize()
    backups = list((tmp_path/'backups').glob('*.sqlite3'))
    assert len(backups) == 1
    with sqlite3.connect(backups[0]) as original:
        assert original.execute('SELECT created_at FROM rules').fetchone()[0].endswith('16:54:32')
    with model.connect() as db:
        result = db.execute("""SELECT c.slug,r.published_at,a.public_id,p.public_id,p.saving_amount,typeof(r.service_id)
            FROM reports p JOIN calculations a ON a.id=p.calculation_id JOIN rules r ON r.id=a.rule_id
            JOIN calculators c ON c.id=r.service_id""").fetchone()
        assert tuple(result) == ('notary_car','2026-11-19','old-reference','old-report',80,'integer')
        assert not db.execute('PRAGMA foreign_key_check').fetchall()
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("UPDATE calculators SET deleted_at='2026-02-30' WHERE slug='notary_car'")


def test_dangling_legacy_row_rolls_back_all_ddl(tmp_path):
    path = tmp_path / 'invalid.sqlite3'
    with sqlite3.connect(path) as db:
        db.executescript("""CREATE TABLE audit(id INTEGER PRIMARY KEY,rule_id INTEGER,action TEXT,created_at TEXT);
            INSERT INTO audit VALUES(8,123,'legacy','2026-11-20');""")
    with pytest.raises(sqlite3.IntegrityError):
        Database(path).initialize()
    with sqlite3.connect(path) as db:
        assert db.execute('PRAGMA user_version').fetchone()[0] == 0
        assert db.execute('SELECT id,rule_id FROM audit').fetchone() == (8,123)
        assert db.execute("SELECT count(*) FROM sqlite_master WHERE name LIKE 'legacy_%'").fetchone()[0] == 0


def test_cookie_security_and_shared_login_limit(tmp_path, monkeypatch):
    origin = 'https://hisobchi.example'
    monkeypatch.setenv('HISOBCHI_PUBLIC_ORIGIN',origin)
    path = tmp_path/'two-workers.sqlite3'
    password = 'test-only-strong-password'
    with TestClient(create_app(path,password),base_url=origin) as a, TestClient(create_app(path,password),base_url=origin) as b:
        good = a.post('/api/v1/admin/login',json={'password':password},headers={'Origin':origin})
        assert good.status_code == 200
        assert all(s in good.headers['set-cookie'].lower() for s in ('httponly','secure','samesite=strict'))
        assert good.headers['cache-control'] == 'no-store'
        assert a.get('/api/v1/admin/me').status_code == 200
        for client in (a,b,a,b,a):
            assert client.post('/api/v1/admin/login',json={'password':'wrong'}).status_code == 401
        assert b.post('/api/v1/admin/login',json={'password':password}).status_code == 429
        assert a.post('/api/v1/admin/logout',headers={'Origin':'http://localhost:5173'}).status_code == 403
        assert a.post('/api/v1/admin/logout',headers={'Origin':origin}).status_code == 200
        assert a.get('/api/v1/admin/me').status_code == 401
