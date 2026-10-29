#!/usr/bin/env python3
"""Build a native, explicitly opted-in sudo environment fixture in a staging tree.

Never installs a policy into host /etc. The staged helper uses a fixed manifest
path inside the output tree. Use only disposable test output directories.
"""

from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[1]
if __name__ == '__main__':
    runpy.run_path(str(ROOT / 'meta-iotbench/recipes-vulns/cwe798-sudo-environment/'
                            'files/fixture-build.py'), run_name='__main__')
