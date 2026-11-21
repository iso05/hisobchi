import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
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
            db.executescript('''
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    status TEXT NOT NULL CHECK(status IN ('draft','published')),
                    effective_from TEXT NOT NULL, config TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    published_at TEXT
                );
                CREATE TABLE IF NOT EXISTS audit (
                    id INTEGER PRIMARY KEY, rule_id INTEGER NOT NULL,
                    action TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS calculations (
                    id TEXT PRIMARY KEY, owner TEXT NOT NULL, rule_id INTEGER,
                    answers TEXT NOT NULL, result TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS reports (
                    id TEXT PRIMARY KEY, calculation_id TEXT UNIQUE NOT NULL REFERENCES calculations(id),
                    standard_amount INTEGER, paid_amount INTEGER, saving_amount INTEGER,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    token_hash TEXT PRIMARY KEY, expires_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS calculators (
                    id TEXT PRIMARY KEY, deleted_at TEXT
                );
                INSERT OR IGNORE INTO calculators(id) VALUES('notary_car');
                CREATE TRIGGER IF NOT EXISTS immutable_published_rules
                BEFORE UPDATE ON rules WHEN OLD.status='published'
                BEGIN SELECT RAISE(ABORT, 'Published rules are immutable'); END;
                CREATE TRIGGER IF NOT EXISTS retain_published_rules
                BEFORE DELETE ON rules WHEN OLD.status='published'
                BEGIN SELECT RAISE(ABORT, 'Published rules are retained'); END;
            ''')
            columns = {row['name'] for row in db.execute('PRAGMA table_info(rules)')}
            if 'service_id' not in columns:
                db.execute("ALTER TABLE rules ADD COLUMN service_id TEXT NOT NULL DEFAULT 'notary_car'")
            if not db.execute("SELECT id FROM rules WHERE service_id='notary_car' LIMIT 1").fetchone():
                cursor = db.execute("INSERT INTO rules(status,effective_from,config,published_at) VALUES('published',?,?,CURRENT_TIMESTAMP)", (SEED['effective_from'], json.dumps(SEED, ensure_ascii=False)))
                db.execute('INSERT INTO audit(rule_id,action) VALUES(?,?)', (cursor.lastrowid, 'Boshlang‘ich Lex.uz qoidasi kiritildi'))
            for definition in CATALOG:
                service_id = definition['id']
                db.execute('INSERT OR IGNORE INTO calculators(id) VALUES(?)',(service_id,))
                if service_id=='notary_car' or db.execute('SELECT id FROM rules WHERE service_id=? LIMIT 1',(service_id,)).fetchone():
                    continue
                config = seed_config(definition)
                cursor = db.execute("INSERT INTO rules(service_id,status,effective_from,config,published_at) VALUES(?,'published',?,?,CURRENT_TIMESTAMP)",(service_id,config['effective_from'],json.dumps(config,ensure_ascii=False)))
                db.execute('INSERT INTO audit(rule_id,action) VALUES(?,?)',(cursor.lastrowid,definition['name']+' — boshlang‘ich qoida, jamoa tekshiruvi uchun'))

    @staticmethod
    def rule(row):
        if not row:
            return None
        config = json.loads(row['config'])
        for key in ('law_url', 'bhm_source_url'):
            if key in config:
                config[key] = working_source_url(config[key])
        return {**dict(row), 'config': config}

    def current_rule(self, as_of, service_id='notary_car'):
        with self.connect() as db:
            return self.rule(db.execute("SELECT * FROM rules WHERE service_id=? AND status='published' AND effective_from<=? ORDER BY effective_from DESC,id DESC LIMIT 1", (service_id,as_of)).fetchone())

    def all_rules(self, service_id='notary_car'):
        with self.connect() as db:
            rows = db.execute('SELECT * FROM rules ORDER BY id DESC').fetchall() if service_id is None else db.execute('SELECT * FROM rules WHERE service_id=? ORDER BY id DESC',(service_id,)).fetchall()
            return [self.rule(r) for r in rows]

    def calculator_active(self,service_id='notary_car'):
        with self.connect() as db:
            row = db.execute('SELECT deleted_at FROM calculators WHERE id=?',(service_id,)).fetchone()
            return bool(row is not None and row['deleted_at'] is None)
