#!/usr/bin/env python3
"""Dedicated, explicitly enabled host build of one Password Leak variant."""

from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[1]
if __name__ == '__main__':
    runpy.run_path(str(ROOT / 'meta-iotbench/recipes-vulns/cwe798-password-leak/files/fixture-build.py'),
                   run_name='__main__')
