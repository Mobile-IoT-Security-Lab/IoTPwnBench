#!/usr/bin/env python3
"""Offline packaged-JAR tests. Namespace isolation is mandatory; no host-JVM fallback.

Requires Python >=3.8, JDK >=17, ldd, util-linux unshare/setpriv, and user namespaces.
--static executes build gates and launcher command doubles without running Java.
"""
import argparse
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "meta-iotbench/recipes-vulns/cwe502-java-deserialization/files"
SLUG = "cwe502-java-deserialization"
ENABLE = "IOTBENCH_ENABLE_JAVA_DESERIALIZATION_FIXTURE"
PACKAGE = "org.iotbench.fixture.deserialization."
JAR = "fixture-deserialization.jar"
TEST_JAR = "fixture-deserialization-tests.jar"

if sys.version_info < (3, 8):
    raise SystemExit("Python >=3.8 is required; select a compatible interpreter (e.g. /usr/bin/python3).")


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def static_checks():
    class Rejected(Exception):
        pass

    class BB:
        class parse:
            SkipRecipe = Rejected

        @staticmethod
        def fatal(message):
            raise Rejected(message)

    class Data:
        def __init__(self, values):
            self.values = values

        def getVar(self, key):
            return self.values.get(key)

    recipe = SOURCE.parent / f"{SLUG}_1.0.bb"
    image = ROOT / "meta-iotbench/recipes-images/iotbench-java-deserialization-fixture.inc"
    for path, function in ((recipe, "__anonymous"), (image, "iotbench_java_deserialization_guard")):
        match = re.search(r"python " + function + r"\(\) \{\n(.*?)\n\}", path.read_text(), re.S)
        require(match is not None, "missing build gate")
        gate = compile(textwrap.dedent(match.group(1)), function, "exec")
        for mode, enabled, accepted in ((None, None, False), ("production", "1", False),
                                         ("fixture", "0", False), ("fixture", "1", True)):
            values = {"IOTBENCH_BUILD_MODE": mode, ENABLE: enabled,
                      "IOTBENCH_VULN_INSTALL": SLUG, "IMAGE_INSTALL": "packagegroup-core-boot " + SLUG}
            try:
                exec(gate, {"bb": BB, "d": Data(values)})
                require(accepted, "production/default mode admitted fixture and marker")
            except Rejected:
                require(not accepted, "explicit fixture mode rejected")
        if path == image:
            for extra in (" device-router", " cwe077-java-app-command-injection"):
                values["IMAGE_INSTALL"] = "packagegroup-core-boot " + SLUG + extra
                try:
                    exec(gate, {"bb": BB, "d": Data(values)})
                    raise AssertionError("additional applications accepted")
                except Rejected:
                    pass
    profiles = sorted((ROOT / "meta-iotbench/recipes-devices").glob("*/device-*.inc"))
    images = sorted((ROOT / "meta-iotbench/recipes-images").glob(f"iotbench-*-{SLUG}.bb"))
    require(len(profiles) == len(images) == 11, "incomplete Java device coverage")
    for profile in profiles:
        content = (image.parent / f"iotbench-{profile.parent.name}-{SLUG}.bb").read_text()
        require(f"require recipes-devices/{profile.parent.name}/{profile.name}" in content
                and 'require recipes-images/iotbench-java-deserialization-fixture.inc' in content
                and f'IOTBENCH_VULN_INSTALL = "{SLUG}"' in content, "invalid device integration")
    # There must be no other recipe that installs the marker/application sources.
    for other in (ROOT / "meta-iotbench").rglob("*.bb"):
        if other != recipe:
            require("FixtureMarker.java" not in other.read_text(), "marker included in unrelated recipe")
    with tempfile.TemporaryDirectory(prefix="java-deserialization-build-guard-") as temporary:
        output = Path(temporary) / "not-built"
        result = subprocess.run([sys.executable, str(SOURCE / "fixture-build.py"), "--output", str(output)],
                                capture_output=True, timeout=10)
        require(result.returncode == 2 and not output.exists(), "local build accepted missing fixture opt-in")
    print("PASS default/production exclusion gates; single fixture package; all 11 device recipes")
    launcher_checks(images)


def launcher_checks(catalog):
    with tempfile.TemporaryDirectory(prefix="java-deserialization-dispatch-") as temporary:
        base = Path(temporary)
        scripts = base / "scripts"
        scripts.mkdir()
        images = base / "meta-iotbench/recipes-images"
        images.mkdir(parents=True)
        binaries = base / "bin"
        binaries.mkdir()
        log = base / "calls"

        def executable(name, content):
            path = binaries / name
            path.write_text("#!/bin/sh\nset -eu\n" + content)
            path.chmod(0o755)

        executable("docker", 'printf "%s %s\\n" "$FIRMWARE" "$*" >> "$CALL_LOG"\n')
        executable("bitbake", 'printf "%s\\n" "$*" >> "$CALL_LOG"\n'
                   'if [ "$1" = -r ]; then cat "$2" >> "$CALL_LOG"; fi\nexit 70\n')
        executable("zstd", 'while [ "$#" -gt 0 ]; do if [ "$1" = -o ]; then shift; : > "$1"; fi; shift; done\n')
        executable("qemu-system-aarch64", 'printf "%s\\n" "$*" >> "$CALL_LOG"\n')
        environment = {"PATH": str(binaries) + ":/usr/bin:/bin", "CALL_LOG": str(log),
                       "HOME": str(base), "MACHINES": "qemuarm64"}
        for recipe in catalog:
            shutil.copy2(recipe, images / recipe.name)
        (images / "iotbench-ordinary.bb").touch()
        shutil.copy2(ROOT / "scripts/build-all.sh", scripts / "build-all.sh")
        for enabled in (False, True):
            log.unlink(missing_ok=True)
            env = dict(environment, **({ENABLE: "1", "IOTBENCH_BUILD_MODE": "fixture"} if enabled else {}))
            subprocess.run(["sh", str(scripts / "build-all.sh")], env=env, check=True,
                           stdout=subprocess.DEVNULL, timeout=10)
            calls = log.read_text().splitlines()
            require(len(calls) == (12 if enabled else 1), "catalog opt-in/exclusion failed")
            require(all(f"-e {ENABLE}=1" in call and "-e IOTBENCH_BUILD_MODE=fixture" in call
                        for call in calls if SLUG in call), "fixture configuration not forwarded")
        setup = base / "setup.sh"
        setup.write_text(":\n")
        wrapper = scripts / "container-build-and-export.sh"
        wrapper.write_text((ROOT / "scripts/container-build-and-export.sh").read_text().replace(
            "source /opt/yocto/yocto-env.sh", 'source "' + str(setup) + '"'))
        for config, expected in (({}, 1), ({ENABLE: "1", "IOTBENCH_BUILD_MODE": "production"}, 1),
                                 ({ENABLE: "1", "IOTBENCH_ENABLE_JAVA_COMMAND_FIXTURE": "1"}, 1),
                                 ({ENABLE: "1", "IOTBENCH_BUILD_MODE": "fixture"}, 70)):
            log.unlink(missing_ok=True)
            result = subprocess.run(["bash", str(wrapper)], env=dict(environment,
                                    FIRMWARE="router-" + SLUG, **config), capture_output=True, timeout=10)
            require(result.returncode == expected, "wrapper opt-in guard failed: " + repr(result.stderr))
            if expected == 70:
                require(f'{ENABLE} = "1"' in log.read_text()
                        and 'IOTBENCH_BUILD_MODE = "fixture"' in log.read_text(), "missing BitBake opt-in")
            else:
                require(not log.exists(), "disabled fixture reached BitBake")
        shutil.copy2(ROOT / "scripts/run-qemu.sh", scripts / "run-qemu.sh")
        for recipe in catalog:
            firmware = recipe.stem[len("iotbench-"):]
            deployment = base / "deploy-images" / firmware / "qemuarm64"
            deployment.mkdir(parents=True)
            (deployment / f"iotbench-{firmware}-qemuarm64.rootfs.ext4.zst").touch()
            (deployment / "Image").touch()
            log.unlink(missing_ok=True)
            subprocess.run(["sh", str(scripts / "run-qemu.sh")], env=dict(environment, FIRMWARE=firmware),
                           check=True, stdout=subprocess.DEVNULL, timeout=10)
            args = log.read_text()
            require("-nic none" in args and "-m 1024" in args and "-snapshot" in args
                    and all(option not in args for option in ("-netdev", "hostfwd", "ip=dhcp", "virtfs", "9p")),
                    "QEMU isolation flags failed")
    print("PASS catalog opt-in, build-wrapper guards and 11 serial-only QEMU commands (command doubles)")


def check_jars(directory):
    for filename, expected in ((JAR, {"FixtureData", "FixtureMarker", "FixtureDeserialize"}),
                               (TEST_JAR, {"FixtureHarness"})):
        with zipfile.ZipFile(directory / filename) as jar:
            classes = [name for name in jar.namelist() if name.endswith(".class")]
            require({Path(name).stem for name in classes} == expected, "unrelated classes in JAR")
            require(all(jar.read(name)[6:8] == b"\x00=" for name in classes), "expected Java-17 bytecode")
            require(b"Main-Class: org.iotbench.fixture.deserialization." in jar.read("META-INF/MANIFEST.MF"),
                    "missing executable manifest")
            if filename == JAR:
                bytecode = b"".join(jar.read(name) for name in classes)
                for forbidden in (b"java/lang/ProcessBuilder", b"java/lang/Runtime", b"java/net/",
                                  b"java/io/File", b"java/nio/file", b"java/net/URLClassLoader"):
                    require(forbidden not in bytecode, "unexpected side-effect API in application")


def runtime_checks(jdk, artifacts, root, vectors):
    shared = module("java_fixture_sandbox", Path(__file__).with_name("test-java-command-fixture.py"))
    sandbox = shared.Sandbox(root, jdk, enable_variable=ENABLE)
    for name in (JAR, TEST_JAR):
        shutil.copy2(artifacts / name, root / "fixtures" / name)
    sandbox.verify_isolation()
    java = ["/jdk/bin/java", "-Xmx32m", "-Xss512k", "-XX:-UsePerfData"]
    harness = ["-cp", f"/fixtures/{JAR}:/fixtures/{TEST_JAR}", PACKAGE + "FixtureHarness"]
    inputs = {}
    for name in vectors["generated"]:
        code, data, err = sandbox.run(java + harness + ["generate", name])
        require(code == 0 and not err, f"input generation failed: {name}: {err!r}")
        second = sandbox.run(java + harness + ["generate", name])
        require(second == (0, data, b""), "non-deterministic synthetic serialized input")
        inputs[name] = data
    for name, encoded in vectors["samples_base64"].items():
        require(inputs[name] == base64.b64decode(encoded, validate=True), "serialized sample drift: " + name)
    print("PASS locally generated normal/marker bytes match committed synthetic samples")
    inputs.update({"empty": b"", "truncated-header": b"\xac\xed",
                   "truncated-object": inputs["normal"][:-1], "invalid-header": b"NOPE",
                   "oversized-garbage": b"x" * 4097})
    output = artifacts / "inputs"
    output.mkdir(exist_ok=True)
    hashes = {}
    for name, data in inputs.items():
        (output / (name + ".ser")).write_bytes(data)
        hashes[name] = hashlib.sha256(data).hexdigest()
    (output / "sha256.json").write_text(json.dumps(hashes, indent=2, sort_keys=True) + "\n")
    for name, response in {**vectors["generated"], **vectors["controls"]}.items():
        code, out, err = sandbox.run(java + ["-jar", "/fixtures/" + JAR, "--fixture-test"], inputs[name])
        require((code, out, err) == (0 if response.startswith("OK ") else 2, (response + "\n").encode(), b""),
                f"{name}: unexpected result {code}, {out!r}, {err!r}")
        print("PASS packaged JAR / " + name + " -> " + response)
    for enabled, args in ((False, ["--fixture-test"]), (True, []), (True, ["--wrong"])):
        actual = sandbox.run(java + ["-jar", "/fixtures/" + JAR] + args, inputs["marker"], enabled=enabled)
        require(actual == (64, b"", b"FIXTURE_DISABLED\n"), "runtime opt-in guard failed")
    code, out, err = sandbox.run(java + harness + ["observe"])
    require(code == 0 and out == b"OBSERVED marker_events=1 rejected_after_callback=true allowlist_events=0 reset=true oversized_events=0\n"
            and not err, f"independent callback/allowlist observations failed: {code}, {out!r}, {err!r}")
    print("PASS independent in-memory callback observation, late rejection, allowlist, reset and oversized prefix")
    global_filter = ["-Djdk.serialFilter=!" + PACKAGE + "FixtureMarker"]
    code, out, err = sandbox.run(java + global_filter + harness + ["observe-global"])
    require((code, out, err) == (0, b"OBSERVED global_filter_events=0\n", b""), "existing JVM filter bypassed")
    result = sandbox.run(java + ["-Djdk.serialFilter=maxdepth=2", "-jar", "/fixtures/" + JAR, "--fixture-test"],
                         inputs["depth-at-limit"])
    require(result == (2, b"FILTER_REJECTED\n", b""), "stricter JVM resource filter bypassed")
    require(not list((root / "work").iterdir()) and not list((root / "tmp").iterdir()),
            "unexpected runtime filesystem side effect")
    print("PASS runtime opt-in, existing JVM type/depth filters and no work/tmp filesystem side effects")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--static", action="store_true")
    parser.add_argument("--jdk", type=Path)
    parser.add_argument("--jar-dir", type=Path, help="test prebuilt application/test JARs alongside vectors.json")
    parser.add_argument("--output", type=Path, help="retain JARs, generated synthetic .ser inputs and hashes")
    args = parser.parse_args()
    if args.jar_dir is None:
        static_checks()
    if args.static:
        require(args.jar_dir is None, "--static requires repository sources")
        return
    require(args.jdk is not None and (args.jdk / "bin/java").is_file(), "--jdk must identify a local JDK/JRE")
    require(os.geteuid() != 0, "run the harness as an unprivileged host/guest user")
    with tempfile.TemporaryDirectory(prefix="iotbench-java-deserialization-") as temporary:
        base = Path(temporary)
        artifacts = args.output.resolve() if args.output else base / "artifacts"
        artifacts.mkdir(parents=True, exist_ok=True)
        if args.jar_dir is None:
            builder = module("deserialization_build", SOURCE / "fixture-build.py")
            for directory in (artifacts, base / "rebuild"):
                builder.build(SOURCE, directory, args.jdk.resolve() / "bin/javac", with_tests=True)
            for name in (JAR, TEST_JAR):
                require((artifacts / name).read_bytes() == (base / "rebuild" / name).read_bytes(),
                        "non-reproducible JAR: " + name)
                print("PASS reproducible " + name + " sha256=" + hashlib.sha256((artifacts / name).read_bytes()).hexdigest())
            shutil.copy2(SOURCE / "vectors.json", artifacts / "vectors.json")
        else:
            for name in (JAR, TEST_JAR, "vectors.json"):
                if (args.jar_dir / name).resolve() != (artifacts / name).resolve():
                    shutil.copy2(args.jar_dir / name, artifacts / name)
        check_jars(artifacts)
        runtime_checks(args.jdk.resolve(), artifacts, base / "root", json.loads((artifacts / "vectors.json").read_text()))
        if args.output:
            print("Artifacts: " + str(artifacts))


if __name__ == "__main__":
    main()
