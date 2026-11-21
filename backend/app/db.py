import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from .migration import upgrade
from .catalog import CATALOG, seed_config, working_source_url

SEED = {
    'effective_from': '2026-09-01', 'bhm_amount': 440000,
    'car_bhm_multiplier': '3', 'motorcycle_bhm_multiplier': '0.25',
    'relative_pay_percent': '5', 'bank_pay_percent': '10', 'outside_multiplier': '2',
    'law_url': 'https://lex.uz/docs/-4680944',
    'law_article': 'Ilova, 4-band “o” kichik bandi va izohi; 20-modda',
    'bhm_source_url': 'https://lex.uz/docs/-8283656', 'verified_at': '2026-11-20',
    'change_note': 'Boshlang‘ich qoida: O‘RQ-600 va PF-115 (3-band b(ii)); rasmiy Lex.uz matni tekshirildi.',
}


class Database:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path, timeout=15)
        connection.row_factory = sqlite3.Row
        connection.execute('PRAGMA foreign_keys=ON')
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self):
        with self.connect() as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.execute('BEGIN IMMEDIATE')
            upgrade(db, self.path)
            for definition in CATALOG:
                slug = definition['id']
                db.execute('INSERT OR IGNORE INTO calculators(slug) VALUES(?)', (slug,))
                service_pk = db.execute('SELECT id FROM calculators WHERE slug=?',(slug,)).fetchone()[0]
                if db.execute('SELECT 1 FROM rules WHERE service_id=? LIMIT 1',(service_pk,)).fetchone():
                    continue
                config = SEED if slug == 'notary_car' else seed_config(definition)
                cursor = db.execute("INSERT INTO rules(service_id,status,effective_from,config,published_at) VALUES(?,'published',?,?,CURRENT_DATE)",
                                    (service_pk,config['effective_from'],json.dumps(config,ensure_ascii=False)))
                db.execute('INSERT INTO audit(rule_id,action) VALUES(?,?)',(cursor.lastrowid,definition['name']+' — boshlang‘ich qoida'))

    @staticmethod
    def rule(row):
        if not row:
            return None
        config = json.loads(row['config'])
        for key in ('law_url', 'bhm_source_url'):
            if key in config:
                config[key] = working_source_url(config[key])
        record = dict(row)
        record['service_id'] = record.pop('slug')
        return {**record, 'config': config}

    def current_rule(self, as_of, service_id='notary_car'):
        with self.connect() as db:
            return self.rule(db.execute("SELECT r.*, c.slug FROM rules r JOIN calculators c ON c.id=r.service_id WHERE c.slug=? AND status='published' AND effective_from<=? ORDER BY effective_from DESC,r.id DESC LIMIT 1", (service_id,as_of)).fetchone())

    def all_rules(self, service_id='notary_car'):
        with self.connect() as db:
            rows = db.execute('SELECT r.*,c.slug FROM rules r JOIN calculators c ON c.id=r.service_id ORDER BY r.id DESC').fetchall() if service_id is None else db.execute('SELECT r.*,c.slug FROM rules r JOIN calculators c ON c.id=r.service_id WHERE c.slug=? ORDER BY r.id DESC',(service_id,)).fetchall()
            return [self.rule(r) for r in rows]

    def calculator_active(self,service_id='notary_car'):
        with self.connect() as db:
            row = db.execute('SELECT deleted_at FROM calculators WHERE slug=?',(service_id,)).fetchone()
            return bool(row is not None and row['deleted_at'] is None)
