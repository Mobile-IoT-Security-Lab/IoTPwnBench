#!/usr/bin/env python3
"""Dedicated host test build; production/default configurations are rejected."""

from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / 'meta-iotbench/recipes-vulns/cwe798-unencrypted-traffic/files/fixture-build.py'

if __name__ == '__main__':
    runpy.run_path(str(BUILDER), run_name='__main__')
