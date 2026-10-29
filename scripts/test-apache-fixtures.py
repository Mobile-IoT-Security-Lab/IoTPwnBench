#!/usr/bin/env python3
"""Run one variant or the complete Apache fixture suite in private Linux namespaces."""
import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'meta-iotbench/recipes-vulns/apache-web-fixture/files/fixture-build.py'
CWES = ('089', '079', '020', '352', '078', '022', '077', '306', '862', '287')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cwe', choices=CWES + ('all',), default='all')
    args, rest = parser.parse_known_args()
    for cwe in CWES if args.cwe == 'all' else (args.cwe,):
        subprocess.run([sys.executable, str(FIXTURE), '--cwe', cwe] + rest, check=True)
