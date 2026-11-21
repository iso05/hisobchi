CREATE TABLE calculators (
    id INTEGER PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    deleted_at DATE CHECK (deleted_at IS NULL OR (date(deleted_at,'+0 days') IS deleted_at))
);
CREATE TABLE custom_categories (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
    icon TEXT NOT NULL
);
CREATE TABLE custom_calculators (
    id INTEGER PRIMARY KEY REFERENCES calculators(id),
    category_id INTEGER NOT NULL REFERENCES custom_categories(id),
    definition TEXT NOT NULL CHECK (json_valid(definition)),
    revision INTEGER NOT NULL DEFAULT 1 CHECK (revision > 0),
    tested_hash TEXT,
    created_at DATE NOT NULL DEFAULT CURRENT_DATE CHECK (date(created_at,'+0 days') IS created_at)
);
CREATE TABLE rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_id INTEGER NOT NULL REFERENCES calculators(id),
    status TEXT NOT NULL CHECK(status IN ('draft','published')),
    effective_from DATE NOT NULL CHECK (date(effective_from,'+0 days') IS effective_from),
    config TEXT NOT NULL CHECK (json_valid(config)),
    created_at DATE NOT NULL DEFAULT CURRENT_DATE CHECK (date(created_at,'+0 days') IS created_at),
    published_at DATE CHECK (published_at IS NULL OR date(published_at,'+0 days') IS published_at)
);
CREATE INDEX rules_by_service ON rules(service_id,id DESC);
CREATE INDEX published_rules_by_date ON rules(service_id,effective_from DESC,id DESC) WHERE status='published';
CREATE TRIGGER immutable_published_rules BEFORE UPDATE ON rules WHEN OLD.status='published'
BEGIN SELECT RAISE(ABORT, 'Published rules are immutable'); END;
CREATE TRIGGER retain_published_rules BEFORE DELETE ON rules WHEN OLD.status='published'
BEGIN SELECT RAISE(ABORT, 'Published rules are retained'); END;
CREATE TABLE audit (
    id INTEGER PRIMARY KEY,
    rule_id INTEGER NOT NULL REFERENCES rules(id),
    action TEXT NOT NULL,
    created_at DATE NOT NULL DEFAULT CURRENT_DATE CHECK (date(created_at,'+0 days') IS created_at)
);
CREATE TABLE calculations (
    id INTEGER PRIMARY KEY,
    public_id TEXT NOT NULL UNIQUE,
    service_id INTEGER NOT NULL REFERENCES calculators(id),
    rule_id INTEGER REFERENCES rules(id),
    owner TEXT NOT NULL,
    answers TEXT NOT NULL CHECK(json_valid(answers)),
    result TEXT NOT NULL CHECK(json_valid(result)),
    created_at DATE NOT NULL DEFAULT CURRENT_DATE CHECK (date(created_at,'+0 days') IS created_at)
);
CREATE TABLE reports (
    id INTEGER PRIMARY KEY,
    public_id TEXT NOT NULL UNIQUE,
    calculation_id INTEGER NOT NULL UNIQUE REFERENCES calculations(id),
    standard_amount INTEGER,
    paid_amount INTEGER,
    saving_amount INTEGER,
    created_at DATE NOT NULL DEFAULT CURRENT_DATE CHECK (date(created_at,'+0 days') IS created_at)
);
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY,
    token_hash TEXT NOT NULL UNIQUE,
    expires_at REAL NOT NULL
);
CREATE INDEX sessions_by_expiry ON sessions(expires_at);
CREATE TABLE login_attempts (
    id INTEGER PRIMARY KEY,
    client_hash TEXT NOT NULL,
    attempted_at INTEGER NOT NULL
);
CREATE INDEX attempts_by_client ON login_attempts(client_hash,attempted_at);
CREATE INDEX attempts_by_time ON login_attempts(attempted_at);
