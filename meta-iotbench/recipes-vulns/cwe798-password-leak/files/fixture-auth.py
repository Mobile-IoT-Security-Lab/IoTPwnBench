#!/usr/bin/env python3
"""One-shot synthetic authentication: candidate on stdin, status on stdout."""

import argparse
import hmac
import json
from pathlib import Path
import runpy
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--isolated-fixture', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    lib = runpy.run_path(str(root / 'fixture-lib.py'))
    if not args.isolated_fixture:
        return 77
    try:
        build = json.loads((root / 'build-config.json').read_text())
        lib['validate_build'](build['mode'], build['enabled'], build['machine'], build['variant'])
        policy = json.loads((root / 'authentication.json').read_text())
        source = root / policy['source']
        if source.is_symlink() or source.resolve().parent != root:
            raise ValueError('Authentication source must remain inside its fixture')
        stored = lib['credential'](source.read_text(), policy['parser'], policy['field'])
        expected = lib['decode'](stored, policy['encoding'])
        if not lib['SECRET'].fullmatch(expected):
            raise ValueError('Only synthetic fixture credentials are accepted')
        candidate = sys.stdin.buffer.readline(4097)
        if len(candidate) > 4096:
            raise ValueError('Oversized candidate')
        accepted = hmac.compare_digest(candidate.rstrip(b'\r\n'), expected.encode('ascii'))
    except (OSError, ValueError, KeyError, AttributeError):
        return 77
    print('synthetic-auth: ' + ('accepted' if accepted else 'rejected'))
    return 0 if accepted else 1


if __name__ == '__main__':
    sys.exit(main())
