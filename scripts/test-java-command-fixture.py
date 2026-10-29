#!/usr/bin/env python3
"""Offline packaged-JAR tests; Linux namespaces are mandatory, with no unsafe fallback.

Requires Python >=3.8, a JDK >=17, ldd and util-linux unshare/setpriv.
All runtime files are copies. The only new mount is namespace-local procfs.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import resource
import shutil
import signal
import subprocess
import tempfile
import textwrap
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "meta-iotbench/recipes-vulns/java-command-fixture/files"
VARIANTS = {"os": "FixtureOsCommand", "app": "FixtureAppCommand"}


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def build_guards():
    """Execute the actual BitBake Python gates with a minimal datastore."""
    recipe = (SOURCE.parent / "java-command-fixture.inc").read_text()
    image = (ROOT / "meta-iotbench/recipes-images/iotbench-java-command-fixture.inc").read_text()

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

        def getVar(self, name):
            return self.values.get(name)

    gates = []
    for source, name in ((recipe, "__anonymous"), (image, "iotbench_java_command_guard")):
        match = re.search(r"python " + name + r"\(\) \{\n(.*?)\n\}", source, re.S)
        require(match is not None, "missing build gate")
        gates.append(compile(textwrap.dedent(match.group(1)), name, "exec"))
    for variant, package in (("os", "cwe078-java-os-command-injection"),
                             ("app", "cwe077-java-app-command-injection")):
        enabled = {"IOTBENCH_BUILD_MODE": "fixture", "IOTBENCH_ENABLE_JAVA_COMMAND_FIXTURE": "1",
                   "IOTBENCH_VULN_INSTALL": package,
                   "IMAGE_INSTALL": "packagegroup-core-boot " + package}
        for gate in gates:
            for mode, optin, accept in ((None, None, False), ("production", "1", False),
                                        ("fixture", "0", False), ("fixture", "1", True)):
                values = dict(enabled, IOTBENCH_BUILD_MODE=mode,
                              IOTBENCH_ENABLE_JAVA_COMMAND_FIXTURE=optin)
                try:
                    exec(gate, {"bb": BB, "d": Data(values)})
                    require(accept, "production/default build accepted fixture")
                except Rejected:
                    require(not accept, "explicit fixture build rejected")
        try:
            exec(gates[1], {"bb": BB, "d": Data(dict(enabled, IMAGE_INSTALL=enabled["IMAGE_INSTALL"] + " device-router"))})
            raise AssertionError("unrelated device services accepted")
        except Rejected:
            pass
        images = sorted((ROOT / "meta-iotbench/recipes-images").glob(f"iotbench-*-{package}.bb"))
        devices = sorted(p.name for p in (ROOT / "meta-iotbench/recipes-devices").iterdir()
                         if (p / f"device-{p.name}.inc").exists())
        require(len(images) == len(devices) == 11, "device fixture coverage incomplete")
        for device in devices:
            content = (ROOT / f"meta-iotbench/recipes-images/iotbench-{device}-{package}.bb").read_text()
            require(f'require recipes-devices/{device}/device-{device}.inc' in content
                    and f'IOTBENCH_VULN_INSTALL = "{package}"' in content,
                    "device integration mismatch")
    print("PASS production/default exclusion gates and 22 device recipes")


def limits():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_CPU, (5, 5))
    resource.setrlimit(resource.RLIMIT_FSIZE, (4096, 4096))


def launcher_checks():
    """Run repository shell dispatch with command doubles, never Docker/QEMU."""
    with tempfile.TemporaryDirectory(prefix="java-command-dispatch-") as temporary:
        base = Path(temporary)
        scripts = base / "scripts"
        scripts.mkdir()
        images = base / "meta-iotbench/recipes-images"
        images.mkdir(parents=True)
        bin_dir = base / "bin"
        bin_dir.mkdir()
        log = base / "calls"

        def executable(name, content):
            path = bin_dir / name
            path.write_text("#!/bin/sh\nset -eu\n" + content)
            path.chmod(0o755)

        executable("docker", 'printf "%s %s\\n" "$FIRMWARE" "$*" >> "$CALL_LOG"\n')
        executable("bitbake", 'printf "%s\\n" "$*" >> "$CALL_LOG"\n'
                   'if [ "$1" = -r ]; then cat "$2" >> "$CALL_LOG"; fi\nexit 70\n')
        executable("zstd", 'while [ "$#" -gt 0 ]; do if [ "$1" = -o ]; then shift; : > "$1"; fi; shift; done\n')
        executable("qemu-system-aarch64", 'printf "%s\\n" "$*" >> "$CALL_LOG"\n')
        environment = {"PATH": str(bin_dir) + ":/usr/bin:/bin", "CALL_LOG": str(log),
                       "HOME": str(base), "MACHINES": "qemuarm64"}
        catalog = sorted((ROOT / "meta-iotbench/recipes-images").glob("iotbench-*-java-*-command-injection.bb"))
        for recipe in catalog:
            shutil.copy2(recipe, images / recipe.name)
        (images / "iotbench-ordinary.bb").touch()
        shutil.copy2(ROOT / "scripts/build-all.sh", scripts / "build-all.sh")
        subprocess.run(["sh", str(scripts / "build-all.sh")], env=environment,
                       check=True, stdout=subprocess.DEVNULL, timeout=10)
        require(log.read_text().splitlines() == ["ordinary compose run --rm yocto"],
                "catalog includes Java fixtures without opt-in")
        log.unlink()
        enabled = dict(environment, IOTBENCH_ENABLE_JAVA_COMMAND_FIXTURE="1", IOTBENCH_BUILD_MODE="fixture")
        subprocess.run(["sh", str(scripts / "build-all.sh")], env=enabled,
                       check=True, stdout=subprocess.DEVNULL, timeout=10)
        calls = log.read_text().splitlines()
        require(len(calls) == 23 and all("-e IOTBENCH_ENABLE_JAVA_COMMAND_FIXTURE=1" in line
                and "-e IOTBENCH_BUILD_MODE=fixture" in line for line in calls if "java-" in line),
                "catalog fixture configuration not forwarded")
        # Substitute just the environment setup path. A sentinel BitBake exits
        # before image export; no real /opt, /workdir or /export is accessed.
        setup = base / "setup.sh"
        setup.write_text(":\n")
        wrapper = scripts / "container-build-and-export.sh"
        wrapper.write_text((ROOT / "scripts/container-build-and-export.sh").read_text().replace(
            "source /opt/yocto/yocto-env.sh", 'source "' + str(setup) + '"'))
        for firmware in ("router-cwe078-java-os-command-injection", "router-cwe077-java-app-command-injection"):
            for options, expected in (({}, 1),
                                      ({"IOTBENCH_ENABLE_JAVA_COMMAND_FIXTURE": "1", "IOTBENCH_BUILD_MODE": "production"}, 1),
                                      ({"IOTBENCH_ENABLE_JAVA_COMMAND_FIXTURE": "1", "IOTBENCH_ENABLE_APACHE_FIXTURE": "1"}, 1),
                                      ({"IOTBENCH_ENABLE_JAVA_COMMAND_FIXTURE": "1", "IOTBENCH_BUILD_MODE": "fixture"}, 70)):
                log.unlink(missing_ok=True)
                result = subprocess.run(["bash", str(wrapper)], env=dict(environment, FIRMWARE=firmware, **options),
                                        capture_output=True, text=True, timeout=10)
                require(result.returncode == expected, "build wrapper configuration guard failed: " + result.stderr)
                if expected == 70:
                    require('IOTBENCH_BUILD_MODE = "fixture"' in log.read_text()
                            and 'IOTBENCH_ENABLE_JAVA_COMMAND_FIXTURE = "1"' in log.read_text(),
                            "wrapper failed to create explicit BitBake configuration")
                else:
                    require(not log.exists(), "rejected build reached BitBake")
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
            arguments = log.read_text()
            require("-nic none" in arguments and "-m 1024" in arguments
                    and "-netdev" not in arguments and "hostfwd" not in arguments and "ip=dhcp" not in arguments,
                    "Java guest launcher exposes networking or lacks staging memory")
    print("PASS catalog defaults/opt-in, build-wrapper guards, and all 22 serial-only QEMU commands (command doubles)")


class Sandbox:
    def __init__(self, root, jdk, enable_variable="IOTBENCH_ENABLE_JAVA_COMMAND_FIXTURE"):
        self.root = root
        self.enable_variable = enable_variable
        def missing_links(directory, names):
            # Distribution JREs can contain a dangling optional src.zip link.
            return [name for name in names if (Path(directory) / name).is_symlink()
                    and not (Path(directory) / name).exists()]
        shutil.copytree(jdk, root / "jdk", symlinks=False, ignore=missing_links)
        binaries = [(Path("/bin/sh").resolve(), "bin/sh"),
                    (Path(shutil.which("setpriv")), "usr/bin/setpriv")]
        # Copy ELF dependencies, including the JDK's native libraries. No binds.
        for path in list((root / "jdk").rglob("*")) + [p for p, _ in binaries]:
            if not path.is_file():
                continue
            with path.open("rb") as stream:
                if stream.read(4) != b"\x7fELF":
                    continue
            linked = subprocess.run(["ldd", str(path)], capture_output=True, text=True, timeout=10)
            for library in re.findall(r"(/[^\s()]+)", linked.stdout):
                source = Path(library)
                if root in source.parents:
                    continue  # JDK libraries already live at /jdk in the copy.
                destination = root / source.relative_to("/")
                destination.parent.mkdir(parents=True, exist_ok=True)
                if not destination.exists():
                    shutil.copy2(source, destination)
        for source, destination in binaries:
            path = root / destination
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, path)
        for directory in ("work", "tmp", "dev", "proc", "fixtures"):
            (root / directory).mkdir(exist_ok=True)
        # A disposable regular sink suffices; no host device nodes are exposed.
        (root / "dev/null").touch()

    def run(self, command, request=b"", enabled=True):
        environment = {"PATH": "/usr/bin:/bin", "LC_ALL": "C"}
        if enabled:
            environment[self.enable_variable] = "1"
        argv = ["unshare", "--user", "--map-user=65534", "--map-group=65534", "--keep-caps",
                "--net", "--mount", "--pid", "--fork", "--kill-child",
                "--root=" + str(self.root), "--wd=/work", "--mount-proc=/proc",
                "/usr/bin/setpriv", "--bounding-set=-all", "--inh-caps=-all",
                "--ambient-caps=-all", "--no-new-privs"] + command
        process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, env=environment,
                                   start_new_session=True, preexec_fn=limits)
        try:
            stdout, stderr = process.communicate(request, timeout=10)
            return process.returncode, stdout, stderr
        finally:
            # --kill-child also destroys the namespace's init and descendants.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=5)

    def verify_isolation(self):
        probe = ('while IFS= read -r line; do case "$line" in '
                 'Uid:*|Gid:*|CapEff:*|CapPrm:*|CapInh:*|CapAmb:*|CapBnd:*|NoNewPrivs:*|NSpid:*) '
                 'printf "%s\\n" "$line";; esac; done < /proc/self/status; '
                 'test ! -e /home; test ! -e /sys; '
                 'while IFS= read -r line; do printf "ROUTE:%s\\n" "$line"; done < /proc/net/route; '
                 'while IFS= read -r line; do printf "DEV:%s\\n" "$line"; done < /proc/net/dev')
        code, out, err = self.run(["/bin/sh", "-c", probe])
        require(code == 0, "namespace isolation unavailable: " + err.decode())
        status = out.decode()
        for key in ("CapEff", "CapPrm", "CapInh", "CapAmb", "CapBnd"):
            require(re.search(key + r":\s+0+\n", status), "capabilities retained: " + status)
        for key in ("Uid", "Gid"):
            require(re.search(key + r":\s+65534\s+65534\s+65534\s+65534\n", status), "privileged UID/GID")
        require("NoNewPrivs:\t1" in status and "NSpid:\t1" in status, "missing privilege or PID isolation")
        routes = [line for line in status.splitlines() if line.startswith("ROUTE:")]
        require(not routes or (len(routes) == 1 and routes[0].startswith("ROUTE:Iface")),
                "external network route present: " + status)
        require(status.count("DEV:") == 3 and re.search(r"DEV:\s+lo:", status),
                "network namespace exposes a non-loopback interface: " + status)
        print("PASS copied filesystem, UID/GID 65534, zero capabilities, no-new-privileges, isolated PID/network")

    def case(self, variant, name, request, expected_code, expected, enabled=True, arguments=None):
        work = self.root / "work"
        shutil.rmtree(work)
        work.mkdir()
        command = ["/jdk/bin/java", "-Xmx32m", "-XX:-UsePerfData", "-jar",
                   f"/fixtures/fixture-{variant}-command.jar"]
        command += ["--fixture-test"] if arguments is None else arguments
        code, out, err = self.run(command, request, enabled)
        require(code == expected_code, f"{variant}/{name}: exit {code}, {out!r}, {err!r}")
        actual = {p.name: p.read_bytes() for p in work.iterdir() if p.is_file()}
        require(actual == expected and len(list(work.iterdir())) == len(expected),
                f"{variant}/{name}: unexpected marker contents/location: {actual!r}")
        require(not list((self.root / "tmp").iterdir()),
                "unexpected files outside /work: " + str(list((self.root / "tmp").rglob("*"))))
        print(f"PASS {variant}/{name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--static", action="store_true", help="only execute build guards and inspect integration")
    parser.add_argument("--jdk", type=Path, help="local JDK home; all runtime files are copied")
    parser.add_argument("--jar-dir", type=Path, help="test already packaged JARs, e.g. extracted firmware files")
    parser.add_argument("--variant", choices=("os", "app", "all"), default="all")
    args = parser.parse_args()
    if args.jar_dir is None:
        build_guards()
        launcher_checks()
    if args.static:
        require(args.jar_dir is None, "--static requires repository sources")
        return
    require(args.jdk is not None, "--jdk is required for isolated execution")
    require(os.geteuid() != 0, "run the harness as an unprivileged host/guest user")
    jdk = args.jdk.resolve()
    selected = list(VARIANTS) if args.variant == "all" else [args.variant]
    builder = None
    if args.jar_dir is None:
        spec = importlib.util.spec_from_file_location("fixture_build", SOURCE / "fixture-build.py")
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
    with tempfile.TemporaryDirectory(prefix="iotbench-java-command-") as temporary:
        base = Path(temporary)
        artifacts = base / "artifacts"
        jars = {}
        for variant in selected:
            if builder:
                first = builder.build(SOURCE, artifacts, jdk / "bin/javac", variant)
                second = builder.build(SOURCE, base / "rebuild", jdk / "bin/javac", variant)
                require(first.read_bytes() == second.read_bytes(), "non-reproducible JAR")
                jars[variant] = first
                print(f"PASS {variant} reproducible JAR: {hashlib.sha256(first.read_bytes()).hexdigest()}")
            else:
                jars[variant] = args.jar_dir / f"fixture-{variant}-command.jar"
            with zipfile.ZipFile(jars[variant]) as jar:
                classes = [name for name in jar.namelist() if name.endswith(".class")]
                require(len(classes) == 2, "fixture contains unrelated classes")
                require(all(jar.read(name)[6:8] == b"\x00=" for name in classes), "not Java-17 bytecode")
                main = jar.read("META-INF/MANIFEST.MF")
                require(VARIANTS[variant].encode() in main, "incorrect executable manifest")
                class_bytes = b"".join(jar.read(name) for name in classes)
                require((b"java/lang/ProcessBuilder" in class_bytes) == (variant == "os"),
                        "OS execution must be confined to the CWE-78 fixture")
        sandbox = Sandbox(base / "root", jdk)
        for jar in jars.values():
            shutil.copy2(jar, sandbox.root / "fixtures" / jar.name)
        sandbox.verify_isolation()
        vectors = json.loads(((args.jar_dir or SOURCE) / "requests.json").read_text())
        for variant in selected:
            sandbox.case(variant, "normal", vectors["normal"].encode(), 0, {"normal.txt": b"sensor_01\n"})
            sandbox.case(variant, "boundary-1", b"label=a\n", 0, {"normal.txt": b"a\n"})
            sandbox.case(variant, "boundary-128", b"label=" + b"a" * 128 + b"\n", 0,
                         {"normal.txt": b"a" * 128 + b"\n"})
            sandbox.case(variant, "injection", vectors[variant].encode(), 0,
                         {name: value.encode() for name, value in vectors[variant + "_expected"].items()})
            for name, value in vectors["invalid"].items():
                sandbox.case(variant, name, value.encode(), 2, {})
            sandbox.case(variant, "boundary-129", b"label=" + b"a" * 129 + b"\n", 2, {})
            sandbox.case(variant, "huge", b"label=" + b"a" * 10000, 2, {})
            sandbox.case(variant, "non-ascii", b"label=\xff\n", 2, {})
            sandbox.case(variant, "disabled-env", vectors["normal"].encode(), 2, {}, enabled=False)
            sandbox.case(variant, "disabled-arg", vectors["normal"].encode(), 2, {}, arguments=[])
        if "os" in selected:
            sandbox.case("os", "quoted-metacharacters", b"label=sensor;mark\n", 0,
                         {"normal.txt": b"sensor;mark\n"})
            sandbox.case("os", "malformed-shell", b"label='\n", 3, {})
        if "app" in selected:
            sandbox.case("app", "unknown-command", b"label=sensor;unknown\n", 3, {})
            sandbox.case("app", "duplicate-command", b"label=sensor;mark;mark\n", 3, {})
        if builder:
            # A temporary corrected JAR verifies that restoring the documented
            # alphabet removes both demonstrations without changing either sink.
            control = base / "control-source"
            shutil.copytree(SOURCE, control)
            request_source = control / "FixtureRequest.java"
            original = request_source.read_text()
            corrected = original.replace('if (label.isEmpty() || label.length() > 128)',
                                         'if (!label.matches("[A-Za-z0-9_-]{1,128}"))')
            require(corrected != original, "corrected validation control was not applied")
            request_source.write_text(corrected)
            for variant in selected:
                jar = builder.build(control, base / "control-jars", jdk / "bin/javac", variant)
                shutil.copy2(jar, sandbox.root / "fixtures" / jar.name)
                sandbox.case(variant, "corrected-normal", vectors["normal"].encode(), 0,
                             {"normal.txt": b"sensor_01\n"})
                sandbox.case(variant, "corrected-injection-rejected", vectors[variant].encode(), 2, {})
    print("PASS packaged JAR validation; temporary files and child processes cleaned")


if __name__ == "__main__":
    main()
