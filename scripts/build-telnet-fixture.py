#!/usr/bin/env python3
"""Stage native Telnet unit/metadata only; this does not compile a host daemon."""

from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / 'meta-iotbench/recipes-vulns/cwe798-unencrypted-traffic/files/fixture-build.py'

if __name__ == '__main__':
    runpy.run_path(str(BUILDER), run_name='__main__')
