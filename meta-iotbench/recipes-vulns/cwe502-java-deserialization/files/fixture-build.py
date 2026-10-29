#!/usr/bin/env python3
"""Offline Java-17 compilation; deterministic executable fixture and test JARs."""
import argparse
from pathlib import Path
import subprocess
import tempfile
import zipfile

PACKAGE = "org.iotbench.fixture.deserialization."
JAR = "fixture-deserialization.jar"
TEST_JAR = "fixture-deserialization-tests.jar"


def package(classes, output, main):
    entries = [("META-INF/MANIFEST.MF",
                f"Manifest-Version: 1.0\r\nMain-Class: {PACKAGE}{main}\r\n\r\n".encode("ascii"))]
    entries += [(p.relative_to(classes).as_posix(), p.read_bytes())
                for p in sorted(classes.rglob("*.class"))]
    with zipfile.ZipFile(output, "w") as archive:
        for name, data in entries:
            info = zipfile.ZipInfo(name, (2020, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)


def build(source, output, javac, with_tests=False):
    output.mkdir(parents=True, exist_ok=True)
    flags = [str(javac), "--release", "17", "-encoding", "UTF-8", "-g", "-Xlint:all", "-Werror"]
    with tempfile.TemporaryDirectory(prefix="java-deserialization-classes-") as temporary:
        classes = Path(temporary) / "app"
        classes.mkdir()
        subprocess.run(flags + ["-d", str(classes)] +
                       [str(source / (name + ".java")) for name in
                        ("FixtureData", "FixtureMarker", "FixtureDeserialize")], check=True, timeout=60)
        result = output / JAR
        package(classes, result, "FixtureDeserialize")
        if with_tests:
            test_classes = Path(temporary) / "tests"
            test_classes.mkdir()
            # Compile against the packaged artifact, not a second copy of its classes.
            subprocess.run(flags + ["-cp", str(result), "-d", str(test_classes),
                                    str(source / "FixtureHarness.java")], check=True, timeout=60)
            package(test_classes, output / TEST_JAR, "FixtureHarness")
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture-build", action="store_true", required=True)
    parser.add_argument("--with-tests", action="store_true")
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--javac", type=Path, default=Path("javac"))
    args = parser.parse_args()
    print(build(args.source, args.output, args.javac, args.with_tests))


if __name__ == "__main__":
    main()
