"""Minimal local Chrome DevTools client using only the Python standard library."""
import base64
import hashlib
import http.client
import json
import os
from pathlib import Path
import socket
import struct
import subprocess
import tempfile
import time


class Browser:
    def __enter__(self):
        self.log = open('/state/browser.log', 'wb')
        self.profile = tempfile.TemporaryDirectory(prefix='chrome-profile-', dir='/tmp')
        self.process = subprocess.Popen([
            '/browser/chrome', '--headless=new', '--remote-debugging-address=127.0.0.1',
            '--remote-debugging-port=19222', '--user-data-dir=' + self.profile.name,
            '--no-first-run', '--no-default-browser-check', '--disable-background-networking',
            '--disable-component-update', '--disable-sync', 'about:blank'],
            stdout=self.log, stderr=self.log)
        try:
            deadline = time.monotonic() + 15
            while True:
                try:
                    connection = http.client.HTTPConnection('127.0.0.1', 19222, timeout=1)
                    connection.request('GET', '/json/version')
                    info = json.loads(connection.getresponse().read())
                    connection.close()
                    break
                except (OSError, ValueError):
                    if self.process.poll() is not None or time.monotonic() > deadline:
                        raise RuntimeError('Chrome startup failed: ' + Path('/state/browser.log').read_text())
                    time.sleep(.05)
            path = info['webSocketDebuggerUrl'].split('19222', 1)[1]
            self.socket = socket.create_connection(('127.0.0.1', 19222), timeout=10)
            key = base64.b64encode(os.urandom(16)).decode()
            self.socket.sendall(('GET ' + path + ' HTTP/1.1\r\nHost: 127.0.0.1:19222\r\n'
                                 'Upgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: ' + key +
                                 '\r\nSec-WebSocket-Version: 13\r\n\r\n').encode())
            headers = b''
            while not headers.endswith(b'\r\n\r\n'):
                headers += self.socket.recv(1)
            accept = base64.b64encode(hashlib.sha1((key + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest())
            if headers.split(b'\r\n', 1)[0].split()[1] != b'101' or accept not in headers:
                raise RuntimeError('Invalid local DevTools websocket handshake')
            self.sequence = 0
            self.session = None
            target = self.call('Target.createTarget', {'url': 'about:blank'})['targetId']
            self.session = self.call('Target.attachToTarget', {'targetId': target, 'flatten': True})['sessionId']
            self.call('Page.enable')
            self.call('Runtime.enable')
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def read(self, count):
        data = b''
        while len(data) < count:
            chunk = self.socket.recv(count - len(data))
            if not chunk:
                raise RuntimeError('DevTools disconnected')
            data += chunk
        return data

    def receive(self):
        parts = b''
        while True:
            first, second = self.read(2)
            size = second & 127
            if size == 126:
                size = struct.unpack('!H', self.read(2))[0]
            elif size == 127:
                size = struct.unpack('!Q', self.read(8))[0]
            mask = self.read(4) if second & 128 else None
            payload = self.read(size)
            if mask:
                payload = bytes(v ^ mask[i % 4] for i, v in enumerate(payload))
            opcode = first & 15
            if opcode == 8:
                raise RuntimeError('DevTools closed')
            if opcode in (0, 1):
                parts += payload
                if first & 128:
                    return json.loads(parts)

    def call(self, method, params=None):
        self.sequence += 1
        message = {'id': self.sequence, 'method': method, 'params': params or {}}
        if self.session:
            message['sessionId'] = self.session
        payload = json.dumps(message).encode()
        mask = os.urandom(4)
        header = bytes([0x81, 0x80 | len(payload)]) if len(payload) < 126 else bytes([0x81, 0xfe]) + struct.pack('!H', len(payload))
        self.socket.sendall(header + mask + bytes(v ^ mask[i % 4] for i, v in enumerate(payload)))
        while True:
            try:
                response = self.receive()
            except OSError:
                print('BROWSER LOG:', Path('/state/browser.log').read_text()[-4000:], flush=True)
                print('APACHE LOG:', Path('/state/error.log').read_text()[-2000:], flush=True)
                print('WAITING FOR:', message, flush=True)
                raise
            if response.get('id') == self.sequence:
                if 'error' in response:
                    raise RuntimeError(str(response['error']))
                return response.get('result', {})

    def evaluate(self, expression):
        result = self.call('Runtime.evaluate', {'expression': expression, 'returnByValue': True, 'awaitPromise': True})
        if 'exceptionDetails' in result:
            raise RuntimeError(str(result['exceptionDetails']))
        return result['result'].get('value')

    def wait(self, expression):
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            try:
                if self.evaluate(expression):
                    return
            except RuntimeError:
                pass  # Navigation destroys the previous execution context.
            time.sleep(.05)
        raise AssertionError('Browser condition timed out: ' + expression)

    def navigate(self, url):
        self.call('Page.navigate', {'url': url})
        self.wait('location.href === ' + json.dumps(url) + ' && document.readyState === "complete"')

    def __exit__(self, *unused):
        if hasattr(self, 'socket'):
            self.socket.close()
        self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()
        self.log.close()
        self.profile.cleanup()
