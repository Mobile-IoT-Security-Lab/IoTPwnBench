#!/usr/bin/env python3
"""Check opt-in integration, native behavior, ASan witnesses and a repaired control.

--binary runs only safe smoke cases against an existing matching-architecture
ELF. --local additionally compiles diagnostic builds and exercises the defect.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import resource
import shlex
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
LAYER = ROOT / "meta-iotbench"
SLUG = "cwe787-native-buffer-overflow"
SOURCE = LAYER / "recipes-vulns" / SLUG / "files"
DEVICES = sorted(p.parent.name for p in (LAYER / "recipes-devices").glob("*/device-*.inc"))
WARNING = ("INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE - "
           "LOCAL SECURITY TESTING ONLY - NOT FOR DEPLOYMENT\n")
SINK = "        configuration[index] = payload[index];"
LOOP = "    for (index = 0; index < length; ++index) {"


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def integration():
    truth = json.loads((SOURCE / "ground-truth.json").read_text())
    source = (SOURCE / "fixture-buffer-write.c").read_text()
    require(truth["primary_cwe"] == "CWE-787" and truth["contributing_cwes"] == ["CWE-20"]
            and truth["broader_cwes"] == ["CWE-119"] and truth["intentional_defects"] == 1,
            "Incorrect CWE classification or defect count")
    for key, statement in (("sink_line", SINK), ("input_line", "    int high = getchar();"),
                           ("transport_check_line", "    if (*length > TRANSPORT_CAPACITY) {")):
        require(source.splitlines()[truth[key] - 1] == statement, f"Stale ground truth: {key}")
    require(source.count(SINK) == source.count(LOOP) == 1, "Expected one indexed-write sink")
    require(truth["destination_capacity"] == 64 and truth["transport_capacity"] == 256 and
            truth["first_invalid_index"] == 64 and truth["minimal_witness_length"] == 65 and
            bytes.fromhex(truth["minimal_witness_hex"]) == frame(b"A" * 65) and
            bytes.fromhex(truth["safe_boundary_hex"]) == frame(b"A" * 64), "Stale boundary/witness data")
    recipes = LAYER / "recipes-images"
    images = sorted(p.name[len("iotbench-"):-len(f"-{SLUG}.bb")]
                    for p in recipes.glob(f"iotbench-*-{SLUG}.bb"))
    require(len(DEVICES) == 11 and images == DEVICES, "Missing or duplicate device recipes")
    for device in DEVICES:
        text = (recipes / f"iotbench-{device}-{SLUG}.bb").read_text()
        for expected in ("require recipes-images/iotbench-image.inc",
                         f"require recipes-devices/{device}/device-{device}.inc",
                         "require recipes-images/iotbench-native-buffer-overflow.inc",
                         'IOTBENCH_CWE = "CWE-787"', f'IOTBENCH_VULN_INSTALL = "{SLUG}"'):
            require(expected in text, f"Incorrect {device} image: {expected}")
        require(f"`{device}-{SLUG}`" in (ROOT / "README.md").read_text(), "Missing catalog row")
    # Execute the actual image guard with a minimal BitBake datastore double.
    include = (recipes / "iotbench-native-buffer-overflow.inc").read_text()
    guard = include.split("python iotbench_native_buffer_guard() {\n", 1)[1].split("\n}", 1)[0]

    class Data:
        def __init__(self, **overrides):
            self.values = dict(IOTBENCH_CWE="CWE-787", IOTBENCH_VULN_INSTALL=SLUG,
                               IMAGE_INSTALL=f"packagegroup-core-boot {SLUG}",
                               IOTBENCH_BUILD_MODE="fixture", IOTBENCH_ENABLE_NATIVE_BUFFER_FIXTURE="1")
            self.values.update(overrides)

        def getVar(self, key):
            return self.values.get(key)

    class BB:
        class parse:
            SkipRecipe = ValueError

        @staticmethod
        def fatal(message):
            raise ValueError(message)

    compiled = compile("def guard(d):\n" + guard + "\n", "image-guard", "exec")
    scope = {"bb": BB}
    exec(compiled, scope)
    scope["guard"](Data())
    for key, value in (("IOTBENCH_CWE", "CWE-20"), ("IOTBENCH_VULN_INSTALL", SLUG + " cwe190-integer-overflow"),
                       ("IMAGE_INSTALL", f"packagegroup-core-boot {SLUG} device-router"),
                       ("IOTBENCH_BUILD_MODE", "production"), ("IOTBENCH_BUILD_MODE", None),
                       ("IOTBENCH_ENABLE_NATIVE_BUFFER_FIXTURE", "0"),
                       ("IOTBENCH_ENABLE_NATIVE_BUFFER_FIXTURE", None)):
        invalid = Data()
        invalid.values[key] = value
        try:
            scope["guard"](invalid)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Image guard accepted {key}={value}")
    recipe = (LAYER / "recipes-vulns" / SLUG / (SLUG + "_1.0.bb")).read_text()
    anonymous = recipe.split("python __anonymous() {\n", 1)[1].split("\n}", 1)[0]
    exec(compile("def package_guard(d):\n" + anonymous + "\n", "package-guard", "exec"), scope)
    for mode in (None, "production", "fixture"):
        for enable in (None, "0", "1"):
            allowed = mode == "fixture" and enable == "1"
            try:
                scope["package_guard"](Data(IOTBENCH_BUILD_MODE=mode,
                                           IOTBENCH_ENABLE_NATIVE_BUFFER_FIXTURE=enable))
            except ValueError:
                require(not allowed, "Package guard rejected test configuration")
            else:
                require(allowed, "Production/absent opt-in package must be skipped")
    for path in recipes.glob("*.bb"):
        if not path.name.endswith(f"-{SLUG}.bb"):
            require(SLUG not in path.read_text(), f"Fixture leaked into unrelated image {path}")
    require('IOTBENCH_BUFFER_FIXTURE_ENABLED=1' in recipe and 'PACKAGECONFIG[asan]' in recipe,
            "Missing package compile opt-in or ASan option")
    print(f"PASS ground truth, all {len(DEVICES)} images, production package exclusion and image guards", flush=True)
    wrappers()


def wrappers():
    """Exercise real wrapper branches with local docker/bitbake command doubles."""
    with tempfile.TemporaryDirectory(prefix="iotbench-buffer-policy-") as temporary:
        stage = Path(temporary)
        log = stage / "commands"
        docker = stage / "docker"
        docker.write_text('#!/bin/sh\nprintf "%s %s\\n" "$FIRMWARE" "$*" >> "$TEST_LOG"\n')
        docker.chmod(0o755)
        environment = {key: value for key, value in os.environ.items() if not key.startswith("IOTBENCH_")}
        environment.update(PATH=str(stage) + os.pathsep + os.environ["PATH"], TEST_LOG=str(log),
                           MACHINES="qemuarm64")
        for enabled in (False, True):
            log.write_text("")
            env = dict(environment)
            if enabled:
                env.update(IOTBENCH_ENABLE_NATIVE_BUFFER_FIXTURE="1", IOTBENCH_NATIVE_BUFFER_ASAN="1")
            subprocess.run(["sh", str(ROOT / "scripts/build-all.sh")], env=env,
                           check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
            rows = [row for row in log.read_text().splitlines() if SLUG in row]
            require(len(rows) == (11 if enabled else 0), "Catalog must exclude buffer fixtures by default")
            require(all("IOTBENCH_ENABLE_NATIVE_BUFFER_FIXTURE=1" in row and
                        "IOTBENCH_NATIVE_BUFFER_ASAN=1" in row for row in rows), "Lost fixture build arguments")
        wrapper = (ROOT / "scripts/container-build-and-export.sh").read_text()
        # Replace only the unavailable Yocto environment; retain actual branching.
        wrapper = wrapper.replace("source /opt/yocto/yocto-env.sh", ": # test environment", 1)
        script = stage / "build.sh"
        script.write_text(wrapper)
        bitbake = stage / "bitbake"
        bitbake.write_text('#!/bin/sh\ncat "$2" > "$TEST_LOG"\nexit 19\n')
        bitbake.chmod(0o755)
        for extra, expected in (({}, 19),
                                ({"IOTBENCH_ENABLE_NATIVE_BUFFER_FIXTURE": "0"}, 1),
                                ({"IOTBENCH_ENABLE_NATIVE_BUFFER_FIXTURE": "1"}, 19),
                                ({"IOTBENCH_ENABLE_NATIVE_BUFFER_FIXTURE": "1", "IOTBENCH_BUILD_MODE": "production"}, 1),
                                ({"IOTBENCH_ENABLE_NATIVE_BUFFER_FIXTURE": "1", "IOTBENCH_NATIVE_BUFFER_ASAN": "1"}, 19),
                                ({"IOTBENCH_ENABLE_NATIVE_BUFFER_FIXTURE": "1", "IOTBENCH_NATIVE_BUFFER_ASAN": "bad"}, 1),
                                ({"IOTBENCH_ENABLE_NATIVE_BUFFER_FIXTURE": "1", "IOTBENCH_ENABLE_NATIVE_PATH_FIXTURE": "1"}, 1)):
            log.write_text("")
            env = dict(environment, FIRMWARE="router-" + SLUG, **extra)
            result = subprocess.run(["bash", str(script)], env=env, capture_output=True, timeout=5)
            require(result.returncode == expected, f"Incorrect wrapper result: {extra}: {result}")
            if expected == 19:
                require('IOTBENCH_BUILD_MODE = "fixture"' in log.read_text() and
                        'IOTBENCH_ENABLE_NATIVE_BUFFER_FIXTURE = "1"' in log.read_text(), "Missing BitBake opt-in")
                require(('PACKAGECONFIG:append:pn-' + SLUG in log.read_text()) ==
                        (extra.get("IOTBENCH_NATIVE_BUFFER_ASAN") == "1"), "Incorrect ASan configuration")
            else:
                require(not log.read_text(), "Rejected configuration reached bitbake")
    print("PASS catalog default exclusion, explicit opt-in, wrapper mode/mixing guards and ASan forwarding", flush=True)


def frame(payload):
    return len(payload).to_bytes(2, "big") + payload


def no_core():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def run(binary, data, arguments=()):
    environment = dict(os.environ, ASAN_OPTIONS="detect_leaks=0:halt_on_error=1:abort_on_error=0:symbolize=1:exitcode=86",
                       LC_ALL="C")
    return subprocess.run([str(binary), *arguments], input=data, capture_output=True,
                          timeout=5, env=environment, preexec_fn=no_core, cwd=str(binary.parent))


def smoke(binary):
    rng = random.Random(787)
    payloads = [b"", b"A", b" " * 63, b"~" * 64, b"A" * 64]
    payloads += [bytes(rng.randrange(0x20, 0x7f) for _ in range(rng.randrange(65))) for _ in range(24)]
    for payload in payloads:
        result = run(binary, frame(payload))
        expected = f"OK {len(payload)} {sum(payload)}\n".encode()
        require(result.returncode == 0 and result.stdout == expected and result.stderr == WARNING.encode(),
                f"Safe input failed ({len(payload)} bytes): {result}")
    invalid = [b"", b"\x00", b"\x00\x02A", frame(b"A") + b"B", frame(b"") * 2,
               b"\x01\x01", b"\xff\xff", frame(b"A" * 65)[:-1], frame(b"A" * 256)[:-1]]
    invalid += [frame(bytes([byte])) for byte in (0, 9, 10, 13, 31, 127, 128, 255)]
    # Validate all bytes before the vulnerable operation, including after byte 64.
    invalid += [frame(b"A" * 65 + b"\x00"), frame(b"A" * 255 + b"\xff")]
    for data, arguments in [(data, ()) for data in invalid] + [(frame(b"A"), ("extra",))]:
        result = run(binary, data, arguments)
        require(result.returncode == 2 and not result.stdout and
                result.stderr == (WARNING + "ERR INVALID\n").encode(), f"Malformed input failed: {result}")
    print(f"PASS {len(payloads)} safe inputs and {len(invalid) + 1} malformed/transport cases: {binary.name}", flush=True)


def local(cc):
    require(os.getuid() != 0 and os.geteuid() == os.getuid() and os.getgid() != 0,
            "Run local tests as an ordinary unprivileged user")
    integration()
    source = SOURCE / "fixture-buffer-write.c"
    flags = ["-std=c99", "-O1", "-g", "-fno-inline", "-fno-lto", "-Wall", "-Wextra", "-Werror",
             "-D_FORTIFY_SOURCE=2", "-fstack-protector-strong", "-fPIE",
             f"-ffile-prefix-map={ROOT}=."]
    truth = json.loads((SOURCE / "ground-truth.json").read_text())
    with tempfile.TemporaryDirectory(prefix="iotbench-buffer-") as temporary:
        stage = Path(temporary)

        def build(name, source_path=source, instrumentation=()):
            binary = stage / name
            subprocess.run([*shlex.split(cc), *flags, '-DIOTBENCH_BUFFER_FIXTURE_ENABLED=1',
                            *instrumentation, str(source_path), "-pie", "-Wl,-z,relro,-z,now,-z,noexecstack",
                            "-o", str(binary)],
                           check=True, timeout=60)
            return binary

        def make(target, mode="fixture", enable="1", destination=stage):
            return subprocess.run(["make", "--no-print-directory", "-f", str(SOURCE / "Makefile"),
                                   "CC=" + cc, "CFLAGS=" + " ".join(flags), "BUILD_DIR=" + str(destination),
                                   "IOTBENCH_BUILD_MODE=" + mode, "IOTBENCH_ENABLE_NATIVE_BUFFER_FIXTURE=" + enable,
                                   target], capture_output=True, timeout=60)

        for target in ("fixture", "asan"):
            for mode, enable in (("production", "0"), ("production", "1"), ("fixture", "0")):
                refused = stage / "refused"
                result = make(target, mode, enable, refused)
                require(result.returncode != 0 and not refused.exists(), "Native build opt-in bypassed")
        result = make("all", "production", "0")
        require(result.returncode == 0, result.stderr.decode())
        disabled = stage / "fixture-buffer-write-disabled"
        result = run(disabled, frame(b"A" * 65))
        require(result.returncode == 77 and not result.stdout and
                result.stderr == b"Native buffer fixture disabled\n", "Production stub enabled fixture")
        symbols = subprocess.check_output(["nm", str(disabled)], text=True)
        require(not any(row.split()[-1] in ("configuration", "apply_configuration", "read_configuration")
                        for row in symbols.splitlines() if row.split()), "Production contains vulnerable code")
        print("PASS native opt-in guards and default production ELF excludes vulnerable functions/storage", flush=True)
        result = make("fixture")
        require(result.returncode == 0, result.stderr.decode())
        native = stage / "fixture-buffer-write"
        smoke(native)
        digest = hashlib.sha256(native.read_bytes()).hexdigest()
        require(make("fixture").returncode == 0, "Repeat build failed")
        require(hashlib.sha256(native.read_bytes()).hexdigest() == digest,
                "Same toolchain/source/flags must reproduce identical ELF bytes")
        print(f"PASS repeat-build ELF SHA-256 {digest}", flush=True)
        asan_flags = ["-fsanitize=address", "-fno-sanitize-recover=all", "-fno-omit-frame-pointer"]
        result = make("asan")
        require(result.returncode == 0, result.stderr.decode())
        diagnostic = stage / "fixture-buffer-write-asan"
        for binary in (native, diagnostic):
            hardening(binary)
        smoke(diagnostic)
        for length in (65, 66, 128, 256):
            result = run(diagnostic, frame(b"A" * length))
            error = result.stderr.decode(errors="replace")
            require(result.returncode == 86 and not result.stdout
                    and "ERROR: AddressSanitizer: global-buffer-overflow" in error
                    and "WRITE of size 1" in error and "configuration" in error
                    and "apply_configuration" in error
                    and f"fixture-buffer-write.c:{truth['sink_line']}" in error,
                    f"Missing exact indexed-write diagnostic at length {length}: {error}")
        print(f"PASS ASan: lengths 65, 66, 128, 256 write beyond configuration[64] at line {truth['sink_line']}", flush=True)
        # Repair only a temporary control; no alternate firmware variant is created.
        fixed_source = stage / "fixed-control.c"
        fixed_source.write_text(source.read_text().replace(LOOP,
            "    if (length > sizeof(configuration)) { return 0; }\n" + LOOP, 1))
        fixed = build("fixed-control", source_path=fixed_source, instrumentation=asan_flags)
        smoke(fixed)
        for length in (65, 66, 128, 255, 256):
            result = run(fixed, frame(b"A" * length))
            require(result.returncode == 2 and not result.stdout and
                    result.stderr == (WARNING + "ERR CAPACITY\n").encode(), "Fixed control failed")
        print("PASS temporary bounds-check control rejects oversized input without ASan errors", flush=True)


def hardening(binary):
    headers = subprocess.check_output(["readelf", "-W", "-h", "-l", "-d", str(binary)], text=True)
    require("DYN (" in headers and "GNU_RELRO" in headers and "BIND_NOW" in headers,
            "Expected PIE and full RELRO")
    stack = next(line for line in headers.splitlines() if "GNU_STACK" in line)
    require("RWE" not in stack and "RW " in stack, "Expected non-executable stack")
    symbols = subprocess.check_output(["nm", "-D", str(binary)], text=True)
    require("__stack_chk_fail" in symbols, "Expected stack protector")
    print(f"PASS PIE, full RELRO, non-executable stack and stack protector: {binary.name}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--static", action="store_true", help="source and recipe integration only")
    choice.add_argument("--local", action="store_true", help="host builds, ASan and fixed-control regression")
    choice.add_argument("--binary", type=Path, help="safe smoke checks on an existing matching-architecture ELF")
    parser.add_argument("--cc", default="cc")
    args = parser.parse_args()
    if args.static:
        integration()
    elif args.local:
        local(args.cc)
    else:
        smoke(args.binary.resolve())


if __name__ == "__main__":
    main()
