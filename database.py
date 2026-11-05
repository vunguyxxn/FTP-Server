"""SQLite persistence shared by the server and the local administration CLI."""
import hashlib
import hmac
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

BASE = Path(__file__).resolve().parent
DEFAULT_DATA = BASE / 'data'


@contextmanager
def connect(data):
    db = sqlite3.connect(Path(data) / 'ftp.sqlite3', timeout=10)
    db.row_factory = sqlite3.Row
    try:
        with db:
            yield db
    finally:
        db.close()


def initialize(data):
    Path(data).mkdir(parents=True, exist_ok=True)
    with connect(data) as db:
        db.execute('PRAGMA journal_mode=WAL')
        db.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY, salt TEXT NOT NULL, password_hash TEXT NOT NULL,
            home TEXT NOT NULL, permissions TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
        );
        CREATE TABLE IF NOT EXISTS audit (
            id INTEGER PRIMARY KEY, time TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
            username TEXT, ip TEXT, event TEXT NOT NULL, detail TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS transfers (
            id INTEGER PRIMARY KEY, time TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
            username TEXT, ip TEXT, direction TEXT NOT NULL, path TEXT NOT NULL,
            bytes INTEGER NOT NULL, status TEXT NOT NULL
        );
        ''')


def hash_password(password, salt):
    return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), bytes.fromhex(salt), 260_000).hex()


def add_user(data, username, password, readonly=False):
    import re
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,32}', username):
        raise ValueError('Username: 1–32 ký tự A–Z, a–z, 0–9, _ hoặc -.')
    if len(password) < 8:
        raise ValueError('Mật khẩu cần ít nhất 8 ký tự.')
    initialize(data)
    home = (Path(data) / 'homes' / username).resolve()
    home.mkdir(parents=True, exist_ok=True)
    salt = os.urandom(16).hex()
    with connect(data) as db:
        db.execute('INSERT INTO users(username,salt,password_hash,home,permissions) VALUES (?,?,?,?,?)',
                   (username, salt, hash_password(password, salt), str(home), 'elr' if readonly else 'elradfmwMT'))


def verify_user(data, username, password):
    with connect(data) as db:
        row = db.execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()
    # Do the expensive hash even for unknown users.
    salt = row['salt'] if row else '00' * 16
    digest = hash_password(password, salt)
    return row is not None and hmac.compare_digest(digest, row['password_hash'])


def audit(data, username, ip, event, detail=''):
    with connect(data) as db:
        db.execute('INSERT INTO audit(username,ip,event,detail) VALUES (?,?,?,?)',
                   (username, ip, event, str(detail)))


def transfer(data, username, ip, direction, path, status):
    size = Path(path).stat().st_size if Path(path).is_file() else 0
    with connect(data) as db:
        db.execute('INSERT INTO transfers(username,ip,direction,path,bytes,status) VALUES (?,?,?,?,?,?)',
                   (username, ip, direction, str(path), size, status))
