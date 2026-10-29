#!/usr/bin/env python3
"""Offline JDK-17 compilation and deterministic executable JAR packaging."""
import argparse
from pathlib import Path
import subprocess
import tempfile
import zipfile

VARIANTS = {"os": "FixtureOsCommand", "app": "FixtureAppCommand"}


def package(classes, output, main):
    manifest = f"Manifest-Version: 1.0\r\nMain-Class: org.iotbench.fixture.{main}\r\n\r\n"
    entries = [("META-INF/MANIFEST.MF", manifest.encode("ascii"))]
    entries += [(p.relative_to(classes).as_posix(), p.read_bytes())
                for p in sorted(classes.rglob("*.class"))]
    # ZIP_STORED avoids zlib-version differences. No timestamps or host paths.
    with zipfile.ZipFile(output, "w") as jar:
        for name, data in entries:
            info = zipfile.ZipInfo(name, (2020, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            jar.writestr(info, data)


def build(source, output, javac, variant):
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="java-command-classes-") as temporary:
        classes = Path(temporary)
        main = VARIANTS[variant]
        subprocess.run([str(javac), "--release", "17", "-encoding", "UTF-8", "-g",
                        "-Xlint:all", "-Werror", "-d", str(classes),
                        str(source / "FixtureRequest.java"), str(source / (main + ".java"))],
                       check=True, timeout=60)
        destination = output / f"fixture-{variant}-command.jar"
        package(classes, destination, main)
        return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture-build", action="store_true", required=True)
    parser.add_argument("--variant", choices=VARIANTS, required=True)
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--javac", type=Path, default=Path("javac"))
    args = parser.parse_args()
    print(build(args.source, args.output, args.javac, args.variant))


if __name__ == "__main__":
    main()
