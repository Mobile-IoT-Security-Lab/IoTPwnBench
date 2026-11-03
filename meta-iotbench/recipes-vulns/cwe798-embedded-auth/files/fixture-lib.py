"""Strict readers and shared policy for the synthetic CWE-798 pair fixtures."""

import base64
import configparser
import ctypes
import hmac
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

VARIANTS = ('c-source', 'shell', 'ini', 'json', 'xml', 'yaml', 'connection-string', 'base64')
MACHINES = ('qemuarm64', 'qemuarm', 'qemux86-64', 'qemux86', 'qemumips')
FILES = dict(zip(VARIANTS, ('credential.c', 'credentials.sh', 'auth.ini', 'auth.json',
                           'auth.xml', 'auth.yaml', 'connection.conf', 'encoded.json')))
ELF_TARGETS = {'qemuarm64': (2, 1, 183), 'qemuarm': (1, 1, 40),
               'qemux86-64': (2, 1, 62), 'qemux86': (1, 1, 3), 'qemumips': (1, 2, 8)}


def validate_elf(data, machine):
    if len(data) < 20 or data[:4] != b'\x7fELF' or data[5] not in (1, 2):
        raise ValueError('Expected a compiled ELF')
    target = (data[4], data[5], int.from_bytes(data[18:20], 'little' if data[5] == 1 else 'big'))
    if ELF_TARGETS.get(machine) != target:
        raise ValueError('Compiled ELF does not match the selected QEMU target')


def validate_build(mode, enabled, machine, variant):
    if (mode != 'fixture' or enabled != '1' or machine not in MACHINES
            or variant not in VARIANTS):
        raise ValueError('Embedded auth requires explicit fixture mode, enable=1, QEMU and one known variant')


def object_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate field')
        result[key] = value
    return result


def json_object(text):
    return json.loads(text, object_pairs_hook=object_pairs)


def pair(fields):
    if not isinstance(fields, dict) or set(fields) != {'username', 'password'}:
        raise ValueError('Exactly one username/password pair required')
    result = (fields['username'], fields['password'])
    if any(not isinstance(v, str) or not re.fullmatch(r'[A-Za-z0-9_!.-]{1,128}', v)
           for v in result):
        raise ValueError('Invalid fixture credential syntax')
    return result


def read_pair(path, variant):
    text = Path(path).read_text(encoding='ascii')
    if variant == 'c-source':
        matches = re.findall(r'static const char (username|password)\[\] = "([^"]+)";', text)
        if len(matches) != 2:
            raise ValueError('C source must define exactly one pair')
        return pair(object_pairs(matches))
    if variant == 'ini':
        parser = configparser.ConfigParser(interpolation=None)
        try:
            parser.read_string(text)
        except configparser.Error as error:
            raise ValueError('Invalid or duplicate INI credentials') from error
        if parser.sections() != ['authentication'] or parser.defaults():
            raise ValueError('Unexpected INI sections')
        return pair(dict(parser['authentication']))
    if variant == 'json':
        return pair(json_object(text))
    if variant == 'base64':
        data = json_object(text)
        if set(data) != {'credential_base64'}:
            raise ValueError('Expected one encoded pair')
        decoded = base64.b64decode(data['credential_base64'], validate=True).decode('ascii')
        username, password = decoded.split(':')
        return pair(dict(username=username, password=password))
    if variant == 'xml':
        if '<!' in text:
            raise ValueError('XML declarations/entities are not fixture data')
        try:
            root = ET.fromstring(text)
        except ET.ParseError as error:
            raise ValueError('Invalid XML credentials') from error
        if root.tag != 'authentication' or root.attrib or len(root) != 2:
            raise ValueError('Expected one XML pair')
        if any(child.attrib or len(child) for child in root):
            raise ValueError('Unexpected nested XML')
        return pair(object_pairs((child.tag, child.text) for child in root))
    if variant == 'connection-string':
        match = re.fullmatch(r'connection=fixture://([^:@/]+):([^:@/]+)@local/auth\n', text)
        if not match:
            raise ValueError('Invalid synthetic connection string')
        return pair(dict(zip(('username', 'password'), match.groups())))
    # Deliberately limited YAML mapping and shell assignment grammars. These are
    # data readers: no YAML constructors, shell evaluation, sourcing or execution.
    separator = ': ' if variant == 'yaml' else '='
    fields = []
    for line in text.splitlines():
        if not line or line.startswith('#'):
            continue
        key, value = line.split(separator)
        if variant == 'shell':
            if not (value.startswith("'") and value.endswith("'")):
                raise ValueError('Expected single quoted shell literal')
            value = value[1:-1]
        fields.append((key, value))
    return pair(object_pairs(fields))


def verifier(root, config):
    variant = config['variant']
    if variant == 'c-source':
        library = ctypes.CDLL(str(root / 'credential.so'))
        function = library.fixture_auth
        function.argtypes = (ctypes.c_char_p, ctypes.c_char_p)
        function.restype = ctypes.c_int
        return lambda u, p: bool(function(u.encode('ascii'), p.encode('ascii')))
    username, password = read_pair(root / FILES[variant], variant)

    def compare(u, p):
        # Evaluate both comparisons and expose only one generic result.
        return bool(hmac.compare_digest(u, username) & hmac.compare_digest(p, password))
    return compare
