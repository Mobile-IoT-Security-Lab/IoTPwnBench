#!/usr/bin/env python3
"""One-shot synthetic authentication. The secret is provisioned at runtime, never stored."""

import argparse
import hmac
import json
import os
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
        expected = os.environ.get('IOTBENCH_RUNTIME_SECRET', '')
        if not lib['SECRET'].fullmatch(expected):
            raise ValueError('No synthetic secret was provisioned at runtime')
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
