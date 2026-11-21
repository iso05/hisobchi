"""Transactional upgrade of the original Hisobchi SQLite database."""
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

TABLES = ('calculators', 'custom_categories', 'custom_calculators', 'rules', 'audit',
          'calculations', 'reports', 'sessions')


def backup(path):
    folder = Path(path).parent / 'backups'
    folder.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    dest = folder / f'{Path(path).stem}-pre-v2-{stamp}-{uuid4().hex[:8]}.sqlite3'
    source = sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro', uri=True)
    copy = sqlite3.connect(dest)
    try:
        source.backup(copy)
        if copy.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise RuntimeError('SQLite backup integrity check failed')
    finally:
        copy.close()
        source.close()
    return dest


def install_schema(db):
    # executescript would implicitly commit the migration before the data copy.
    statement = ''
    for line in Path(__file__).with_name('schema.sql').read_text(encoding='utf-8-sig').splitlines(True):
        statement += line
        if sqlite3.complete_statement(statement):
            db.execute(statement)
            statement = ''


def upgrade(db, path):
    """Caller owns the BEGIN IMMEDIATE transaction, including the seed writes."""
    version = db.execute('PRAGMA user_version').fetchone()[0]
    if version == 2:
        return
    if version != 0:
        raise RuntimeError(f'Unsupported database version: {version}')
    tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")} & set(TABLES)
    if tables:
        backup(path)
        for trigger in ('immutable_published_rules','retain_published_rules'):
            db.execute(f'DROP TRIGGER IF EXISTS {trigger}')
        for name in TABLES:
            if name in tables:
                db.execute(f'ALTER TABLE {name} RENAME TO legacy_{name}')
    install_schema(db)
    if 'calculators' in tables:
        db.execute('INSERT INTO calculators(slug,deleted_at) SELECT id,substr(deleted_at,1,10) FROM legacy_calculators ORDER BY rowid')
    if 'rules' in tables:
        columns = {r['name'] for r in db.execute('PRAGMA table_info(legacy_rules)')}
        slug = 'r.service_id' if 'service_id' in columns else "'notary_car'"
        db.execute(f'INSERT OR IGNORE INTO calculators(slug) SELECT DISTINCT {slug} FROM legacy_rules r')
        db.execute(f'''INSERT INTO rules(id,service_id,status,effective_from,config,created_at,published_at)
            SELECT r.id,c.id,r.status,r.effective_from,r.config,substr(r.created_at,1,10),substr(r.published_at,1,10)
            FROM legacy_rules r JOIN calculators c ON c.slug={slug}''')
    if 'custom_categories' in tables:
        db.execute('INSERT INTO custom_categories(name,icon) SELECT name,icon FROM legacy_custom_categories')
    if 'custom_calculators' in tables:
        db.execute('''INSERT OR IGNORE INTO custom_categories(name,icon)
            SELECT json_extract(definition,'$.category'),json_extract(definition,'$.icon') FROM legacy_custom_calculators''')
        db.execute('''INSERT INTO custom_calculators(id,category_id,definition,revision,tested_hash,created_at)
            SELECT c.id,k.id,d.definition,d.revision,d.tested_hash,substr(d.created_at,1,10)
            FROM legacy_custom_calculators d JOIN calculators c ON c.slug=d.id
            JOIN custom_categories k ON k.name=json_extract(d.definition,'$.category')''')
        db.execute('''UPDATE calculators SET deleted_at=(SELECT substr(d.deleted_at,1,10)
            FROM legacy_custom_calculators d WHERE d.id=calculators.slug)
            WHERE deleted_at IS NULL AND slug IN (SELECT id FROM legacy_custom_calculators WHERE deleted_at IS NOT NULL)''')
    if 'audit' in tables:
        db.execute('INSERT INTO audit SELECT id,rule_id,action,substr(created_at,1,10) FROM legacy_audit')
    if 'calculations' in tables:
        db.execute('''INSERT INTO calculations(public_id,service_id,rule_id,owner,answers,result,created_at)
            SELECT a.id,c.id,a.rule_id,a.owner,a.answers,a.result,substr(a.created_at,1,10)
            FROM legacy_calculations a JOIN calculators c ON c.slug=json_extract(a.result,'$.service_id') ORDER BY a.rowid''')
    if 'reports' in tables:
        db.execute('''INSERT INTO reports(public_id,calculation_id,standard_amount,paid_amount,saving_amount,created_at)
            SELECT r.id,a.id,r.standard_amount,r.paid_amount,r.saving_amount,substr(r.created_at,1,10)
            FROM legacy_reports r JOIN calculations a ON a.public_id=r.calculation_id ORDER BY r.rowid''')
    if 'sessions' in tables:
        db.execute('INSERT INTO sessions(token_hash,expires_at) SELECT token_hash,expires_at FROM legacy_sessions')
    for name in reversed(TABLES):
        if name in tables:
            before = db.execute(f'SELECT COUNT(*) FROM legacy_{name}').fetchone()[0]
            after = db.execute(f'SELECT COUNT(*) FROM {name}').fetchone()[0]
            if after < before or (after != before and name not in {'calculators','custom_categories'}):
                raise RuntimeError(f'Migration count mismatch for {name}')
            db.execute(f'DROP TABLE legacy_{name}')
    if db.execute('PRAGMA foreign_key_check').fetchone() or db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
        raise RuntimeError('Migrated database failed integrity checks')
    db.execute('PRAGMA user_version=2')
