"""Tenants, API keys and interview sessions. SQLite: one file, no extra service.

ponytail: single-node SQLite with JSON blobs; move to Postgres when running more than one API replica.
"""
import hashlib
import json
import secrets
import sqlite3
import threading
import time

DB = 'data/t10.db'
_lock = threading.Lock()
_conn = None


def _db():
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(DB, check_same_thread=False)
        _conn.executescript("""
            CREATE TABLE IF NOT EXISTS tenants (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, key_hash TEXT UNIQUE NOT NULL,
                webhook_url TEXT, webhook_secret TEXT NOT NULL, share_training INTEGER NOT NULL DEFAULT 0,
                created REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL REFERENCES tenants(id), token TEXT UNIQUE NOT NULL,
                data TEXT NOT NULL, created REAL NOT NULL, expires REAL NOT NULL);
            CREATE INDEX IF NOT EXISTS sessions_tenant ON sessions(tenant_id);
        """)
    return _conn


def _hash(key):
    return hashlib.sha256(key.encode()).hexdigest()


def create_tenant(name, webhook_url=None, share_training=False):
    """Returns (tenant_id, api_key). The key is shown once; only its hash is stored."""
    tid, key = 'tn_' + secrets.token_hex(8), 't10_' + secrets.token_urlsafe(32)
    with _lock:
        _db().execute('INSERT INTO tenants VALUES (?,?,?,?,?,?,?)',
                      (tid, name, _hash(key), webhook_url, secrets.token_urlsafe(32), int(share_training), time.time()))
        _db().commit()
    return tid, key


def tenant_by_key(key):
    row = _db().execute('SELECT id, name, webhook_url, webhook_secret, share_training FROM tenants WHERE key_hash=?',
                        (_hash(key),)).fetchone()
    return row and dict(zip(('id', 'name', 'webhook_url', 'webhook_secret', 'share_training'), row))


def tenant(tid):
    row = _db().execute('SELECT id, name, webhook_url, webhook_secret, share_training FROM tenants WHERE id=?',
                        (tid,)).fetchone()
    return row and dict(zip(('id', 'name', 'webhook_url', 'webhook_secret', 'share_training'), row))


def update_tenant(tid, **vals):
    allowed = {k: v for k, v in vals.items() if k in ('webhook_url', 'share_training')}
    if allowed:
        with _lock:
            _db().execute(f"UPDATE tenants SET {', '.join(f'{k}=?' for k in allowed)} WHERE id=?",
                          (*allowed.values(), tid))
            _db().commit()


def create_session(tenant_id, context, ttl_hours):
    sid, token, now = 'is_' + secrets.token_hex(10), secrets.token_urlsafe(32), time.time()
    data = {'id': sid, 'tenant_id': tenant_id, 'status': 'created', 'context': context, 'transcript': [],
            'flags': [], 'proctor_events': [], 'snapshots': [], 'models': {}, 'consent': None, 'report': None,
            'decision': None, 'created': now}
    with _lock:
        _db().execute('INSERT INTO sessions VALUES (?,?,?,?,?,?)',
                      (sid, tenant_id, token, json.dumps(data, ensure_ascii=False), now, now + ttl_hours * 3600))
        _db().commit()
    return data, token


def get_session(sid, tenant_id):
    row = _db().execute('SELECT data FROM sessions WHERE id=? AND tenant_id=?', (sid, tenant_id)).fetchone()
    return row and json.loads(row[0])


def session_by_token(token):
    """Candidate-side lookup. Expired links behave like unknown ones."""
    if not token or len(token) < 32:
        return None
    row = _db().execute('SELECT data, expires FROM sessions WHERE token=?', (token,)).fetchone()
    return row and row[1] > time.time() and json.loads(row[0]) or None


def save_session(data):
    with _lock:
        _db().execute('UPDATE sessions SET data=? WHERE id=?', (json.dumps(data, ensure_ascii=False), data['id']))
        _db().commit()


def close_token(sid):
    """Candidate link stops working once the interview is over."""
    with _lock:
        _db().execute('UPDATE sessions SET expires=0 WHERE id=?', (sid,))
        _db().commit()


def list_sessions(tenant_id, limit=50):
    rows = _db().execute('SELECT data FROM sessions WHERE tenant_id=? ORDER BY created DESC LIMIT ?',
                         (tenant_id, limit)).fetchall()
    return [json.loads(r[0]) for r in rows]
