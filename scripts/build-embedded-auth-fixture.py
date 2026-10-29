#!/usr/bin/env python3
"""Stage one opt-in embedded authentication fixture (native ELF built separately)."""
from pathlib import Path
import runpy

if __name__ == '__main__':
    runpy.run_path(str(Path(__file__).resolve().parents[1] /
                      'meta-iotbench/recipes-vulns/cwe798-embedded-auth/files/fixture-build.py'),
                   run_name='__main__')
