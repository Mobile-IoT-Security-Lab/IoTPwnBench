#!/usr/bin/env python3
"""Build the explicitly enabled synthetic Java deserialization fixture offline."""
from pathlib import Path
import runpy

if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    runpy.run_path(str(root / "meta-iotbench/recipes-vulns/cwe502-java-deserialization/files/fixture-build.py"),
                   run_name="__main__")
