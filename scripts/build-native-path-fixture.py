#!/usr/bin/env python3
"""Build one explicitly enabled native C path-handling artifact offline."""
from pathlib import Path
import runpy

if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    runpy.run_path(str(root / 'meta-iotbench/recipes-vulns/native-path-fixture/files/fixture-build.py'),
                   run_name='__main__')
