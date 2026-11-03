#!/usr/bin/env python3
"""Generate the corrected twin image recipes.

A corrected twin of an image is the same device with the same scenario module
replaced by its corrected variant. A module recipe named <module>-fixed in
meta-iotbench/recipes-vulns marks a module as having a corrected variant. For
every image recipe that installs such a module through IOTBENCH_VULN_INSTALL,
this script writes iotbench-<firmware>-fixed.bb next to it.

  scripts/gen-fixed-twins.py           write or refresh the twin recipes
  scripts/gen-fixed-twins.py --check   fail if a twin is missing or out of date
  scripts/gen-fixed-twins.py --report  list modules without a corrected variant
"""
import argparse
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
VULNS = ROOT / "meta-iotbench/recipes-vulns"
IMAGES = ROOT / "meta-iotbench/recipes-images"
INSTALL_RE = re.compile(r'^IOTBENCH_VULN_INSTALL\s*=\s*"([^"]+)"\s*$', re.M)


def fixed_modules():
    return {p.name.split("_")[0].removesuffix("-fixed") for p in VULNS.glob("*/*-fixed_*.bb")}


def originals():
    return sorted(p for p in IMAGES.glob("iotbench-*.bb") if not p.stem.endswith("-fixed"))


REQUIRE_RE = re.compile(r'^require\s+(recipes-images/\S+\.inc)\s*$', re.M)


def twin_inc(recipe):
    """The family include of an image that supports IOTBENCH_TWIN, or None."""
    for name in REQUIRE_RE.findall(recipe.read_text()):
        path = ROOT / "meta-iotbench" / name
        if path.is_file() and "IOTBENCH_TWIN" in path.read_text():
            return path
    return None


def assignment(name):
    """A quoted assignment, possibly continued over several lines with a backslash."""
    return re.compile(rf'^{name}\s*=\s*"(?:\\.|[^"\\])*"[ \t]*$', re.M | re.S)


def twin_text(recipe, module):
    text = recipe.read_text()
    firmware = recipe.stem[len("iotbench-"):]
    summary = re.search(r'^SUMMARY\s*=\s*"[^"]*? - ([^"\n]*)"', text, re.M)
    detail = summary.group(1) if summary else firmware
    text = assignment("SUMMARY").sub(lambda m: f'SUMMARY = "IoTBench corrected twin - {detail}"', text)
    description = (f'DESCRIPTION = "Corrected twin of iotbench-{firmware}. The same device and service, '
                   f'with the weakness removed. No weakness is injected."')
    if assignment("DESCRIPTION").search(text):
        text = assignment("DESCRIPTION").sub(lambda m: description, text)
    else:
        text = text.rstrip("\n") + "\n" + description + "\n"
    if module is None:
        # A family include selects the corrected module itself when IOTBENCH_TWIN is 1.
        text = text.rstrip("\n") + '\nIOTBENCH_TWIN = "1"\n'
    else:
        text = INSTALL_RE.sub(f'IOTBENCH_VULN_INSTALL = "{module}-fixed"', text)
    # The twin has no weakness. The CWE of the original is kept in its own variable.
    return text.rstrip("\n") + '\nIOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"\nIOTBENCH_CWE = "none"\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args()
    fixed = fixed_modules()
    if args.report:
        used = {m for p in originals() for m in INSTALL_RE.findall(p.read_text())}
        print("\n".join(sorted(used - fixed)))
        families = sorted({p.name for r in originals() if not INSTALL_RE.search(r.read_text()) and twin_inc(r) is None
                           for p in [ROOT / "meta-iotbench" / n for n in REQUIRE_RE.findall(r.read_text())]
                           if p.name != "iotbench-image.inc" and "IOTBENCH_VULN_INSTALL" in p.read_text()})
        if families:
            print("families without corrected twins (no IOTBENCH_TWIN support):")
            print("\n".join("  " + f for f in families))
        return 0
    stale = []
    count = 0
    for recipe in originals():
        modules = INSTALL_RE.findall(recipe.read_text())
        if len(modules) == 1 and modules[0] in fixed:
            module = modules[0]
        elif not modules and twin_inc(recipe):
            module = None
        else:
            continue
        twin = recipe.with_name(recipe.stem + "-fixed.bb")
        text = twin_text(recipe, module)
        count += 1
        if args.check:
            if not twin.exists() or twin.read_text() != text:
                stale.append(twin.name)
        else:
            twin.write_text(text)
    if args.check and stale:
        print("missing or outdated twins:\n" + "\n".join(stale), file=sys.stderr)
        return 1
    print(f"{count} corrected twins {'checked' if args.check else 'written'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
