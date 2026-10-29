#!/usr/bin/env python3
"""Build the native cron wildcard fixture into a disposable staging directory."""
from pathlib import Path
import runpy

if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    runpy.run_path(str(root / 'meta-iotbench/recipes-vulns/'
                      'cwe088-cronjob-wildcard-injection/files/fixture-build.py'),
                   run_name='__main__')
