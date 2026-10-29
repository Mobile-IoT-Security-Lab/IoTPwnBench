#!/usr/bin/python3
"""Synthetic CGI boundary. Each image supplies exactly one scenario module."""
import hmac
import json
import os
from pathlib import Path
import secrets
import sqlite3
import sys
from http.cookies import SimpleCookie
from urllib.parse import parse_qs

sys.path.insert(0, str(Path(__file__).parent))
import scenario

STATE = Path('/state')
ORIGIN = 'http://127.0.0.1:18080'
USERS = {'admin': ('fixture-admin-proof', 'admin'),
         'reader': ('fixture-reader-proof', 'reader')}


class Rejected(Exception):
    def __init__(self, status=400):
        self.status = status


def respond(body, status=200, content_type='application/json', cookie=None):
    if content_type == 'application/json':
        body = json.dumps(body, sort_keys=True)
    headers = ['Status: ' + str(status), 'Content-Type: ' + content_type + '; charset=utf-8',
               'Cache-Control: no-store', 'X-Content-Type-Options: nosniff',
               "Content-Security-Policy: default-src 'none'; script-src 'unsafe-inline'; "
               "form-action 'self'; frame-ancestors 'none'; base-uri 'none'"]
    if cookie:
        headers.append('Set-Cookie: ' + cookie)
    sys.stdout.write('\r\n'.join(headers) + '\r\n\r\n' + body)


def parameters():
    method = os.environ['REQUEST_METHOD']
    if method == 'GET':
        raw = os.environ.get('QUERY_STRING', '')
    elif method == 'POST':
        if os.environ.get('CONTENT_TYPE', '').split(';')[0] != 'application/x-www-form-urlencoded':
            raise Rejected(415)
        n = int(os.environ.get('CONTENT_LENGTH', '0'))
        if n < 0 or n > 4096:
            raise Rejected(413)
        raw = sys.stdin.read(n)
    else:
        raise Rejected(405)
    if len(raw) > 4096:
        raise Rejected(413)
    if not raw:
        return {}
    values = parse_qs(raw, keep_blank_values=True, strict_parsing=True,
                      encoding='utf-8', errors='strict', max_num_fields=8)
    if any(len(v) != 1 or len(v[0]) > 512 or '\x00' in v[0] for v in values.values()):
        raise Rejected()
    return {k: v[0] for k, v in values.items()}


def fields(p, names):
    if set(p) != set(names):
        raise Rejected()


def authenticate():
    cookie = SimpleCookie(os.environ.get('HTTP_COOKIE', ''))
    sid = cookie['fixture_session'].value if 'fixture_session' in cookie else ''
    if len(sid) != 64 or any(c not in '0123456789abcdef' for c in sid):
        raise Rejected(401)
    with sqlite3.connect(str(STATE / 'sessions.db')) as db:
        row = db.execute('SELECT identity, role, csrf FROM sessions WHERE sid=?', (sid,)).fetchone()
    if not row:
        raise Rejected(401)
    return row


def csrf(p, session):
    if os.environ.get('HTTP_ORIGIN') != ORIGIN or not hmac.compare_digest(p.get('csrf', ''), session[2]):
        raise Rejected(403)


def change(value):
    with sqlite3.connect(str(STATE / 'settings.db')) as db:
        db.execute('UPDATE settings SET value=? WHERE name=?', (str(value), 'benchmark'))


def main():
    if os.geteuid() == 0 or Path('/run/iotbench-apache-isolated').read_text() != 'fixture-v1\n':
        raise Rejected(503)
    p = parameters()
    route = os.environ.get('PATH_INFO', '')
    method = os.environ['REQUEST_METHOD']
    if route == '/login' and method == 'POST':
        fields(p, ('identity', 'proof'))
        if os.environ.get('HTTP_ORIGIN') != ORIGIN:
            raise Rejected(403)
        expected, role = USERS.get(p['identity'], ('', ''))
        verify = getattr(scenario, 'verify', hmac.compare_digest)
        if not expected or not verify(p['proof'], expected):
            raise Rejected(401)
        sid, token = secrets.token_hex(32), secrets.token_hex(32)
        with sqlite3.connect(str(STATE / 'sessions.db')) as db:
            db.execute('INSERT INTO sessions VALUES (?,?,?,?)', (sid, p['identity'], role, token))
        respond({'identity': p['identity'], 'csrf': token}, cookie=
                'fixture_session=' + sid + '; Path=/app; HttpOnly; SameSite=Lax')
        return
    if route == '/session' and method == 'GET':
        fields(p, ())
        session = authenticate()
        respond({'identity': session[0], 'role': session[1], 'csrf': session[2]})
        return
    if route != scenario.ROUTE or method != scenario.METHOD:
        raise Rejected(404)
    fields(p, scenario.FIELDS)
    session = None
    if not getattr(scenario, 'MISSING_AUTH', False):
        session = authenticate()
        if session[1] != 'admin' and not getattr(scenario, 'MISSING_AUTHZ', False):
            raise Rejected(403)
    if method == 'POST' and session and not getattr(scenario, 'MISSING_CSRF', False):
        csrf(p, session)
    body, kind = scenario.handle(p, STATE, change, Rejected)
    respond(body, content_type=kind)


if __name__ == '__main__':
    try:
        main()
    except Rejected as error:
        respond({'error': 'rejected'}, error.status)
    except (ValueError, TypeError, KeyError, OSError, sqlite3.Error, sqlite3.Warning) as error:
        print(type(error).__name__, file=sys.stderr)
        respond({'error': 'invalid request'}, 400)
