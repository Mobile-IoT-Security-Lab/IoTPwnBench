#!/usr/bin/python3
"""Integration tests; refuse execution outside the disposable namespace runner."""
import http.client
import json
import errno
import os
from pathlib import Path
import sqlite3
import subprocess
import time
import unittest
from urllib.parse import urlencode

BASE = 'http://127.0.0.1:18080'
STATE = Path('/state')
CWE = json.loads(Path('/fixture/variant.json').read_text())['cwe']
import scenario
from browser import Browser


def reset():
    for path in STATE.iterdir():
        if path.is_file() and path.name not in ('httpd.pid', 'error.log', 'browser.log'):
            path.unlink()
    (STATE / 'allowed').mkdir(exist_ok=True)
    (STATE / 'allowed/public.txt').write_text('synthetic-public\n')
    (STATE / 'sentinel.txt').write_text('synthetic-traversal-sentinel\n')
    with sqlite3.connect(str(STATE / 'settings.db')) as db:
        db.execute('CREATE TABLE settings (name TEXT PRIMARY KEY, value TEXT)')
        db.execute("INSERT INTO settings VALUES ('benchmark','initial')")
    with sqlite3.connect(str(STATE / 'sessions.db')) as db:
        db.execute('CREATE TABLE sessions (sid TEXT PRIMARY KEY, identity TEXT, role TEXT, csrf TEXT)')
    with sqlite3.connect(str(STATE / 'records.db')) as db:
        db.execute('CREATE TABLE records (name TEXT, label TEXT, designated INTEGER)')
        db.executemany('INSERT INTO records VALUES (?,?,?)',
                       [('public', 'synthetic-public-record', 0), ('sentinel', 'synthetic-sql-sentinel', 1)])


def setting():
    with sqlite3.connect(str(STATE / 'settings.db')) as db:
        return db.execute("SELECT value FROM settings WHERE name='benchmark'").fetchone()[0]


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if (os.getuid() != 1000 or os.geteuid() != 1000 or
                Path('/run/iotbench-apache-isolated').read_text() != 'fixture-v1\n'):
            raise RuntimeError('Tests require the isolated fixture runner')
        status = Path('/proc/self/status').read_text()
        if 'CapEff:\t0000000000000000' not in status or 'NoNewPrivs:\t1' not in status:
            raise RuntimeError('Tests require dropped capabilities and no new privileges')
        # Private network namespace contains only the enabled loopback interface.
        interfaces = Path('/proc/net/dev').read_text().splitlines()[2:]
        if len(interfaces) != 1 or interfaces[0].split(':')[0].strip() != 'lo':
            raise RuntimeError('Unexpected network interface')
        if list(Path('/oldroot').iterdir()):
            raise RuntimeError('Host root must be detached')
        try:
            Path('/fixture/write-probe').touch()
        except OSError as error:
            if error.errno != errno.EROFS:
                raise
        else:
            raise RuntimeError('Fixture source filesystem must be read-only')
        if 'Synthetic fixture' not in Path('/etc/passwd').read_text():
            raise RuntimeError('Unexpected account database')
        cls.log = open('/state/apache-start.log', 'wb')
        cls.apache = subprocess.Popen(['/usr/sbin/httpd', '-f', '/fixture/httpd.conf.in', '-DFOREGROUND'],
                                      stdout=cls.log, stderr=cls.log, start_new_session=True)
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            try:
                cls.request('/app/session')
                return
            except OSError:
                if cls.apache.poll() is not None:
                    break
                time.sleep(.02)
        cls.apache.terminate()
        cls.apache.wait(timeout=30)
        cls.log.close()
        raise RuntimeError('Apache failed: ' + Path('/state/apache-start.log').read_text() +
                           (Path('/state/error.log').read_text() if Path('/state/error.log').exists() else ''))

    @classmethod
    def tearDownClass(cls):
        cls.apache.terminate()
        cls.apache.wait(timeout=30)
        cls.log.close()

    def setUp(self):
        reset()

    @staticmethod
    def request(route, params=None, method='GET', cookie=None, origin=BASE, port=18080, raw=None):
        data = urlencode(params or {})
        headers = {}
        body = None
        if method == 'GET' and data:
            route += '?' + data
        elif method == 'POST':
            body = data if raw is None else raw
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
        if cookie:
            headers['Cookie'] = cookie
        if origin:
            headers['Origin'] = origin
        connection = http.client.HTTPConnection('127.0.0.1', port, timeout=90)
        try:
            connection.request(method, route, body=body, headers=headers)
            response = connection.getresponse()
            result = response.status, response.read().decode(), dict(response.getheaders())
            return result
        finally:
            connection.close()

    def login(self, identity='admin', proof=None):
        proof = proof or ('fixture-' + identity + '-proof')
        code, text, headers = self.request('/app/login', {'identity': identity, 'proof': proof}, 'POST')
        self.assertEqual(code, 200, text)
        return headers['Set-Cookie'].split(';')[0], json.loads(text)['csrf']

    def sample(self):
        return {'089': {'name': 'public'}, '079': {'message': 'ordinary'},
                '020': {'level': '50'}, '352': {'value': 'ordinary'},
                '078': {'label': 'ordinary'}, '022': {'file': 'public.txt'},
                '077': {'label': 'ordinary'}, '306': {'value': 'ordinary'},
                '862': {'value': 'ordinary'}, '287': {}}[CWE]

    def invoke(self, params=None, cookie=None, token=None, origin=BASE, raw=None):
        values = self.sample() if params is None else dict(params)
        if 'csrf' in scenario.FIELDS:
            values['csrf'] = token or ''
        return self.request('/app' + scenario.ROUTE, values, scenario.METHOD, cookie, origin, raw=raw)

    def test_ordinary_behavior(self):
        cookie, token = self.login()
        code, body, _ = self.invoke(cookie=cookie, token=token)
        self.assertEqual(code, 200, body)
        if CWE == '089':
            self.assertEqual(json.loads(body)['records'], ['synthetic-public-record'])
        elif CWE == '022':
            self.assertEqual(json.loads(body)['content'], 'synthetic-public\n')
        elif CWE in ('020', '352', '306', '862'):
            self.assertEqual(setting(), '50' if CWE == '020' else 'ordinary')
        elif CWE == '078':
            self.assertEqual((STATE / 'diagnostic.txt').read_text(), 'ordinary')
            self.assertFalse((STATE / 'shell.marker').exists())
        elif CWE == '077':
            self.assertEqual(json.loads(body)['shown'], ['ordinary'])
            self.assertFalse((STATE / 'interpreter.marker').exists())
        elif CWE == '287':
            code, session, _ = self.request('/app/session', cookie=cookie)
            self.assertEqual(json.loads(session)['identity'], 'admin')
        elif CWE == '079' and Path('/fixture/browser-enabled').exists():
            with Browser() as browser:
                self.browser_session(browser, cookie)
                browser.navigate(BASE + '/app/reflect?' + urlencode({'message': 'ordinary'}))
                self.assertEqual(browser.evaluate('document.querySelector("main").textContent'), 'ordinary')
                self.assertIsNone(browser.evaluate('document.body.dataset.fixture'))

    def test_controls(self):
        cookie, token = self.login()
        # Unauthenticated and forged sessions cannot access unrelated protected routes.
        self.assertEqual(self.request('/app/session')[0], 401)
        self.assertEqual(self.request('/app/session', cookie='fixture_session=' + 'a' * 64)[0], 401)
        self.assertEqual(self.request('/app/login', {'identity': 'admin', 'proof': 'wrong'}, 'POST')[0], 401)
        self.assertEqual(self.request('/app/login', {'identity': 'unknown', 'proof': 'fixture-admin-proof'}, 'POST')[0], 401)
        self.assertEqual(self.request('/app/login', {'identity': 'admin', 'proof': 'fixture-admin-proof'}, 'POST', origin='http://127.0.0.1:18081')[0], 403)
        if CWE != '306':
            self.assertEqual(self.invoke(token=token)[0], 401)
        reader, reader_token = self.login('reader')
        if CWE not in ('306', '862'):
            self.assertEqual(self.invoke(cookie=reader, token=reader_token)[0], 403)
        if 'csrf' in scenario.FIELDS:
            self.assertEqual(self.invoke(cookie=cookie, token='bad')[0], 403)
            self.assertEqual(self.invoke(cookie=cookie, token=token, origin='http://127.0.0.1:18081')[0], 403)
        self.assertEqual(setting(), 'initial')
        self.assertFalse((STATE / 'shell.marker').exists())
        self.assertFalse((STATE / 'interpreter.marker').exists())
        self.assertEqual(self.request('/app/unknown', cookie=cookie)[0], 404)
        self.assertEqual(self.request('/scenario.py')[0], 403)
        self.assertEqual(self.request('/app.cgi')[0], 403)
        # Distinct routes from other variants are absent from this image.
        for route in ('/query', '/reflect', '/level', '/setting', '/diagnostic', '/file', '/command', '/critical', '/admin-setting', '/identity'):
            if route != scenario.ROUTE:
                self.assertEqual(self.request('/app' + route, cookie=cookie)[0], 404)
        params = self.sample()
        params['unexpected'] = 'x'
        self.assertEqual(self.invoke(params, cookie, token)[0], 400)
        self.assertEqual(self.request('/app' + scenario.ROUTE, method='PUT', cookie=cookie)[0], 405)
        self.assertEqual(self.request('/app/login', method='POST', raw='identity=admin&identity=reader&proof=x')[0], 400)
        self.assertEqual(self.request('/app/login', method='POST', raw='identity=admin&proof=%00')[0], 400)
        self.assertEqual(self.request('/app/login', method='POST', raw='proof=' + 'x' * 5000)[0], 413)
        if CWE == '020':
            for value in ('-1', '1.5', 'abc', '1000'):
                self.assertEqual(self.invoke({'level': value}, cookie, token)[0], 400)
            for value in ('0', '100'):
                self.assertEqual(self.invoke({'level': value}, cookie, token)[0], 200)
                self.assertEqual(setting(), value)
        if CWE in ('352', '306', '862'):
            self.assertEqual(self.invoke({'value': 'invalid'}, cookie, token)[0], 400)
        if CWE == '022':
            self.assertEqual(self.invoke({'file': '/etc/passwd'}, cookie, token)[0], 400)
        if CWE == '077':
            self.assertEqual(self.invoke({'label': 'ordinary && MARK'}, cookie, token)[0], 400)
            self.assertFalse((STATE / 'interpreter.marker').exists())

    @staticmethod
    def browser_session(browser, cookie):
        name, value = cookie.split('=', 1)
        result = browser.call('Network.setCookie', {'name': name, 'value': value, 'url': BASE + '/app',
                                                  'path': '/app', 'httpOnly': True, 'sameSite': 'Lax'})
        if not result.get('success'):
            raise AssertionError('Browser refused synthetic session cookie')

    def test_intended_weakness(self):
        cookie, token = self.login()
        if CWE == '089':
            code, body, _ = self.invoke({'name': "' OR designated=1 --"}, cookie, token)
            self.assertEqual(code, 200, body)
            self.assertIn('synthetic-sql-sentinel', json.loads(body)['records'])
            with sqlite3.connect(str(STATE / 'records.db')) as db:
                self.assertEqual(db.execute('SELECT COUNT(*) FROM records').fetchone()[0], 2)
            self.assertEqual(self.invoke({'name': "'; DELETE FROM records; --"}, cookie, token)[0], 400)
        elif CWE == '079':
            if not Path('/fixture/browser-enabled').exists():
                self.skipTest('Explicit HTTP-only run: browser evidence missing')
            with Browser() as browser:
                self.browser_session(browser, cookie)
                payload = '<script>document.body.dataset.fixture="xss-marker"</script>'
                browser.navigate(BASE + '/app/reflect?' + urlencode({'message': payload}))
                browser.wait('document.body.dataset.fixture === "xss-marker"')
                self.assertEqual(browser.evaluate('document.body.dataset.fixture'), 'xss-marker')
        elif CWE == '020':
            self.assertEqual(self.invoke({'level': '101'}, cookie, token)[0], 200)
            self.assertEqual(setting(), '101')
        elif CWE == '352':
            if not Path('/fixture/browser-enabled').exists():
                self.skipTest('Explicit HTTP-only run: browser evidence missing')
            with Browser() as browser:
                # Before authentication, a real browser form submission cannot change state.
                browser.navigate('http://127.0.0.1:18081/index.html')
                browser.evaluate('document.getElementById("attack").submit()')
                browser.wait('location.origin === ' + json.dumps(BASE) + ' && document.body.textContent.includes("rejected")')
                self.assertEqual(setting(), 'initial')
                self.browser_session(browser, cookie)
                browser.navigate('http://127.0.0.1:18081/index.html')
                cookies = browser.call('Network.getCookies', {'urls': [BASE + '/app/setting']})['cookies']
                self.assertEqual(cookies[0]['sameSite'], 'Lax')
                browser.evaluate('document.getElementById("attack").submit()')
                browser.wait('location.origin === ' + json.dumps(BASE) + ' && document.body.textContent.includes("csrf-marker")')
                self.assertEqual(setting(), 'csrf-marker')
        elif CWE == '078':
            payload = 'ordinary; printf shell-marker > shell.marker; #'
            self.assertEqual(self.invoke({'label': payload}, cookie, token)[0], 200)
            self.assertEqual((STATE / 'shell.marker').read_text(), 'shell-marker')
        elif CWE == '022':
            code, body, _ = self.invoke({'file': '../sentinel.txt'}, cookie, token)
            self.assertEqual(code, 200, body)
            self.assertEqual(json.loads(body)['content'], 'synthetic-traversal-sentinel\n')
        elif CWE == '077':
            self.assertEqual(self.invoke({'label': 'ordinary; MARK'}, cookie, token)[0], 200)
            self.assertEqual((STATE / 'interpreter.marker').read_text(), 'application-command-marker\n')
            self.assertFalse((STATE / 'shell.marker').exists())
        elif CWE == '306':
            self.assertEqual(self.invoke({'value': 'unauthenticated-marker'})[0], 200)
            self.assertEqual(setting(), 'unauthenticated-marker')
        elif CWE == '862':
            reader, reader_token = self.login('reader')
            self.assertEqual(self.invoke({'value': 'reader-marker'}, reader, reader_token)[0], 200)
            self.assertEqual(setting(), 'reader-marker')
        elif CWE == '287':
            forged, _ = self.login(proof='fixture-INVALID')
            code, body, _ = self.request('/app/session', cookie=forged)
            self.assertEqual(code, 200)
            self.assertEqual(json.loads(body)['identity'], 'admin')
            self.assertEqual(self.invoke(cookie=forged)[0], 200)


if __name__ == '__main__':
    print(subprocess.check_output(['/usr/sbin/httpd', '-v'], universal_newlines=True).strip(), flush=True)
    print('variant=CWE-' + CWE + '; uid=' + str(os.getuid()) + '; runtime=' + os.sys.version.split()[0], flush=True)
    unittest.main(verbosity=2)
