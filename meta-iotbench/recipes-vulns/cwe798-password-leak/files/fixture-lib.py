"""Local CWE-798 fixture parsing and policy. Never executes payload source."""

import base64
import configparser
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

MACHINES = ('qemuarm64', 'qemuarm', 'qemux86-64', 'qemux86', 'qemumips')
VARIANTS = ('conf-password', 'cfg-admin', 'ini-root', 'env-db', 'json-token',
            'xml-api', 'shell-password', 'c-password', 'header-password',
            'app-password', 'init-password', 'log-password', 'kv-password',
            'json-base64', 'env-base64')
SECRET = re.compile(r'FIXTURE_[A-Z0-9_]+\Z')
KEY = re.compile(r'(?:password|admin_password|root_password|auth_token|api_key|'
                 r'db_password|service\.auth\.password|password_b64|auth_token_b64)\Z', re.I)
ASSIGNMENT = re.compile(
    r'^\s*(?:export\s+)?(?P<key>[A-Za-z_][\w.]*)\s*[:=]\s*'
    r'(?P<value>"[^"\n]*"|\x27[^\x27\n]*\x27|[^#\n]+?)\s*(?:#.*)?$')
C_LITERAL = re.compile(r'\bfixture_secret\[\]\s*=\s*"([^"\n]+)"')


def validate_build(mode, enabled, machine, variant):
    if (mode != 'fixture' or enabled != '1' or machine not in MACHINES
            or variant not in VARIANTS):
        raise ValueError('Password leak requires mode=fixture, explicit enable=1, '
                         'a supported QEMU machine and one known variant')


def credential(text, kind, field):
    """Parse the documented synthetic auth configuration; no eval or shell."""
    if kind == 'json':
        return json.loads(text)[field]
    if kind == 'xml':
        return ET.fromstring(text).find(field).text
    if kind == 'ini':
        config = configparser.ConfigParser(interpolation=None)
        config.read_string(text)
        section, key = field.split('.')
        return config[section][key]
    if kind == 'c':
        return C_LITERAL.search(text).group(1)
    values = {}
    for line in text.splitlines():
        match = ASSIGNMENT.fullmatch(line)
        if match:
            value = match['value'].strip()
            if value[:1] in ('"', "'"):
                value = value[1:-1]
            values[match['key']] = value
    return values[field]


def decode(value, encoding):
    if encoding == 'base64':
        return base64.b64decode(value, validate=True).decode('ascii')
    if encoding != 'plaintext':
        raise ValueError('Unknown encoding')
    return value


def scan(root, decode_base64=True):
    """Small deterministic reference scanner, independent of finding manifests.

    Uses file syntax and credential keys. It reports unexpected credential-like
    values too, so inventory validation cannot silently ignore an extra secret.
    Documentation/comments and explicit provisioning placeholders are controls.
    """
    findings = []
    placeholders = {'', 'CHANGEME', '<set-at-runtime>', '${RUNTIME_SECRET}', 'example-only'}

    def record(path, line, field, value):
        if not isinstance(value, str) or value in placeholders:
            return
        encoded = field.lower().endswith('_b64')
        if encoded and not decode_base64:
            return
        decoded = decode(value, 'base64' if encoded else 'plaintext')
        findings.append({'path': path.relative_to(root).as_posix(), 'line': line,
                         'field': field, 'value': decoded,
                         'encoding': 'base64' if encoded else 'plaintext'})

    for path in sorted(Path(root).rglob('*')):
        if path.is_symlink():
            raise ValueError('Symlinks are not fixture data')
        if not path.is_file() or path.suffix not in (
                '.conf', '.cfg', '.ini', '.env', '.json', '.xml', '.sh',
                '.c', '.h', '.properties', '.log', '.txt'):
            continue
        text = path.read_text()
        if path.suffix == '.json':
            data = json.loads(text)
            if not isinstance(data, dict):
                continue
            # Fixture JSON configs are deliberately flat; manifests have no keys
            # from the credential-key allowlist.
            for field, value in data.items():
                if KEY.fullmatch(field):
                    line = next(i for i, s in enumerate(text.splitlines(), 1)
                                if re.search(r'"' + re.escape(field) + r'"\s*:', s))
                    record(path, line, field, value)
        elif path.suffix == '.xml':
            for element in ET.fromstring(text):
                if KEY.fullmatch(element.tag):
                    line = next(i for i, s in enumerate(text.splitlines(), 1)
                                if '<' + element.tag + '>' in s)
                    record(path, line, element.tag, element.text)
        elif path.suffix in ('.c', '.h'):
            for number, line in enumerate(text.splitlines(), 1):
                match = C_LITERAL.search(line)
                if match and not line.lstrip().startswith(('//', '/*', '*')):
                    record(path, number, 'fixture_secret', match.group(1))
        else:
            for number, line in enumerate(text.splitlines(), 1):
                match = ASSIGNMENT.fullmatch(line)
                if match and KEY.fullmatch(match['key']):
                    value = match['value'].strip()
                    if value[:1] in ('"', "'"):
                        value = value[1:-1]
                    record(path, number, match['key'], value)
    return findings
