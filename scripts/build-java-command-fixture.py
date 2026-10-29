#!/usr/bin/env python3
"""Build explicitly enabled Java command fixtures without downloading dependencies."""
from pathlib import Path
import runpy

if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    runpy.run_path(str(root / "meta-iotbench/recipes-vulns/java-command-fixture/files/fixture-build.py"),
                   run_name="__main__")
