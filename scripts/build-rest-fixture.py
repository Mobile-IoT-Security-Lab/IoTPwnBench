#!/usr/bin/env python3
"""Build the native REST fixture in a disposable staging directory."""
from pathlib import Path
import runpy

if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    runpy.run_path(str(root / 'meta-iotbench/recipes-vulns/'
                      'cwe022-rest-internal-files/files/fixture-build.py'),
                   run_name='__main__')
