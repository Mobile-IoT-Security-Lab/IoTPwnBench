#!/usr/bin/env python3
"""Offline integration checks and local, real SQLite connection-mode regression.

Run --static or --local as an ordinary Linux user. No external network or
services; each request creates and destroys its own private synthetic database.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
LAYER = ROOT / "meta-iotbench"
SLUG = "cwe020-native-connection-string"
SOURCE = LAYER / "recipes-vulns" / SLUG / "files"
DEVICES = sorted(p.parent.name for p in (LAYER / "recipes-devices").glob("*/device-*.inc"))
NOTICE = (SOURCE / "NOTICE").read_bytes()
MARKER = "SYNTHETIC_CONNECTION_RESOURCE"
ENABLE = "IOTBENCH_ENABLE_CONNECTION_FIXTURE"


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def command(argv, **kwargs):
    return subprocess.run([str(a) for a in argv], stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, timeout=30, **kwargs)


def frame(field):
    return len(field).to_bytes(2, "big") + field


def integration():
    truth = json.loads((SOURCE / "ground-truth.json").read_text())
    require(truth["primary_cwe"] == "CWE-20" and truth["intentional_defects"] == 1,
            "Wrong classification/defect count")
    require(truth["normal_input"] == "private" and
            truth["injection_input"] == "private&mode=rw#" and
            truth["normal_readonly"] == 1 and truth["injection_readonly"] == 0,
            "Stale witnesses")
    images = LAYER / "recipes-images"
    actual = sorted(p.name[len("iotbench-"):-len(f"-{SLUG}.bb")]
                    for p in images.glob(f"iotbench-*-{SLUG}.bb"))
    require(len(DEVICES) == 11 and actual == DEVICES, "Missing device integrations")
    for device in DEVICES:
        text = (images / f"iotbench-{device}-{SLUG}.bb").read_text()
        for expected in ("require recipes-images/iotbench-image.inc",
                         f"require recipes-devices/{device}/device-{device}.inc",
                         "require recipes-images/iotbench-native-connection-string.inc",
                         'IOTBENCH_CWE = "CWE-20"', f'IOTBENCH_VULN_INSTALL = "{SLUG}"'):
            require(expected in text, f"Missing {expected} for {device}")
    # Execute package/image policy using a minimal datastore, without pretending
    # this is a complete BitBake parse or an actual image-manifest check.
    class Data:
        def __init__(self, **overrides):
            self.values = dict(IOTBENCH_CWE="CWE-20", IOTBENCH_VULN_INSTALL=SLUG,
                               IMAGE_INSTALL=f"packagegroup-core-boot {SLUG}",
                               IOTBENCH_BUILD_MODE="fixture", **{ENABLE: "1"})
            self.values.update(overrides)

        def getVar(self, name):
            return self.values.get(name)

    class BB:
        class parse:
            SkipRecipe = ValueError

        @staticmethod
        def fatal(message):
            raise ValueError(message)

    include = (images / "iotbench-native-connection-string.inc").read_text()
    recipe = (SOURCE.parent / f"{SLUG}_1.0.bb").read_text()
    for text, declaration in ((include, "python iotbench_native_connection_guard() {\n"),
                              (recipe, "python __anonymous() {\n")):
        body = text.split(declaration, 1)[1].split("\n}", 1)[0]
        scope = {"bb": BB}
        exec(compile("def guard(d):\n" + body + "\n", "fixture-policy", "exec"), scope)
        for mode in (None, "production", "fixture"):
            for enable in (None, "0", "1"):
                try:
                    scope["guard"](Data(IOTBENCH_BUILD_MODE=mode, **{ENABLE: enable}))
                except ValueError:
                    require(mode != "fixture" or enable != "1", "Valid policy rejected")
                else:
                    require(mode == "fixture" and enable == "1", "Production policy accepted")
        if text == include:
            for overrides in (dict(IOTBENCH_CWE="CWE-89"),
                              dict(IOTBENCH_VULN_INSTALL=SLUG + " cwe089-c-sql-injection"),
                              dict(IMAGE_INSTALL=f"packagegroup-core-boot {SLUG} device-router")):
                try:
                    scope["guard"](Data(**overrides))
                except ValueError:
                    pass
                else:
                    raise AssertionError("Image guard accepted unrelated packages")
    # No other image or include may select this test-only package.
    for path in images.glob("*"):
        if path.is_file() and SLUG in path.read_text():
            require(path.name.endswith(f"-{SLUG}.bb") or
                    path.name == "iotbench-native-connection-string.inc", "Unexpected selection")
    for name, shell in (("build-all.sh", "sh"), ("run-qemu.sh", "sh"),
                        ("container-build-and-export.sh", "bash")):
        result = command([shell, "-n", ROOT / "scripts" / name])
        require(result.returncode == 0, result.stderr.decode())
    require(command(["sh", "-n", SOURCE / "test-guest.sh"]).returncode == 0, "Guest script syntax")
    qemu = (ROOT / "scripts/run-qemu.sh").read_text()
    branch = qemu.split(f"*-{SLUG})", 1)[1].split(";;", 1)[0]
    require('NETDEV=""' in branch and f"*-{SLUG}) ;;" in qemu, "QEMU must have no NIC")
    wrapper_checks()
    print("PASS eleven devices, isolated image policy, production exclusion, wrappers and QEMU selection")


def wrapper_checks():
    with tempfile.TemporaryDirectory(prefix="iotbench-connection-wrappers-") as temporary:
        work = Path(temporary)
        bindir = work / "bin"
        bindir.mkdir()
        # Command doubles exercise only build dispatch. No Docker or BitBake runs.
        fake = bindir / "bitbake"
        fake.write_text("#!/usr/bin/python3\nimport json,os,sys\nfrom pathlib import Path\n"
                        "a=sys.argv[1:]\n"
                        "Path(os.environ['CAPTURE']).write_text(json.dumps([a,Path(a[1]).read_text()]))\n"
                        "sys.exit(94)\n")
        fake.chmod(0o755)
        wrapper = work / "wrapper.sh"
        wrapper.write_text((ROOT / "scripts/container-build-and-export.sh").read_text().replace(
            "source /opt/yocto/yocto-env.sh", ": # offline environment already supplied"))
        env = dict(PATH=str(bindir) + ":/usr/bin:/bin", CAPTURE=str(work / "capture"))
        valid = dict(env, FIRMWARE=f"router-{SLUG}", IOTBENCH_BUILD_MODE="fixture", **{ENABLE: "1"})
        result = command(["bash", wrapper], env=valid)
        require(result.returncode == 94, "Enabled wrapper did not reach fake BitBake")
        args, conf = json.loads((work / "capture").read_text())
        require(args[0] == "-r" and args[2] == f"iotbench-router-{SLUG}" and
                f'{ENABLE} = "1"' in conf and 'IOTBENCH_BUILD_MODE = "fixture"' in conf,
                "Wrapper did not pass explicit test configuration")
        require(not Path(args[1]).exists(), "Wrapper leaked temporary configuration")
        for overrides in ({ENABLE: "0"}, {"IOTBENCH_BUILD_MODE": "production"},
                          {"FIRMWARE": "router-cwe078-os-command-injection"},
                          {"IOTBENCH_ENABLE_NATIVE_BUFFER_FIXTURE": "1"}):
            (work / "capture").unlink()
            result = command(["bash", wrapper], env=dict(valid, **overrides))
            require(result.returncode == 1 and not (work / "capture").exists(),
                    f"Wrapper accepted invalid opt-in {overrides}")
            # Restore the capture file for the next invalid-case cleanup.
            (work / "capture").touch()
        docker = bindir / "docker"
        docker.write_text("#!/usr/bin/python3\nimport json,os,sys\n"
                          f"if os.environ.get('FIRMWARE','').endswith('-{SLUG}'):\n"
                          " with open(os.environ['CAPTURE'],'a') as f: f.write(json.dumps(sys.argv[1:])+'\\n')\n")
        docker.chmod(0o755)
        (work / "capture").write_text("")
        result = command(["sh", ROOT / "scripts/build-all.sh"], env=env)
        require(result.returncode == 0 and not (work / "capture").read_text(),
                "Default catalog selected connection fixture")
        result = command(["sh", ROOT / "scripts/build-all.sh"], env=dict(env, **{ENABLE: "1"}))
        entries = [json.loads(line) for line in (work / "capture").read_text().splitlines()]
        require(result.returncode == 0 and len(entries) == 11 and
                all(f"{ENABLE}=1" in entry and "IOTBENCH_BUILD_MODE=fixture" in entry for entry in entries),
                "Catalog did not pass all eleven opt-ins")
        export = work / "export"
        export.mkdir()
        boot = work / "boot.sh"
        boot.write_text((ROOT / "scripts/run-qemu.sh").read_text().replace(
            'DEPLOY_DIR="$(dirname -- "$0")/../deploy-images/${FIRMWARE}/${MACHINE}"',
            f'DEPLOY_DIR="{export}"'))
        qemu_source = ("#!/usr/bin/python3\nimport json,os,sys\nfrom pathlib import Path\n"
                       "Path(os.environ['CAPTURE']).write_text(json.dumps(sys.argv[1:]))\n")
        targets = {"qemuarm64": "aarch64", "qemuarm": "arm", "qemux86-64": "x86_64",
                   "qemux86": "i386", "qemumips": "mips"}
        for suffix in targets.values():
            fake = bindir / f"qemu-system-{suffix}"
            fake.write_text(qemu_source)
            fake.chmod(0o755)
        zstd = bindir / "zstd"
        zstd.write_text("#!/bin/sh\nexit 0\n")
        zstd.chmod(0o755)
        for device in DEVICES:
            for machine in targets:
                firmware = f"{device}-{SLUG}"
                (export / f"iotbench-{firmware}-{machine}.rootfs.ext4.zst").touch()
                result = command(["sh", boot], env=dict(env, FIRMWARE=firmware, YOCTO_MACHINE=machine))
                require(result.returncode == 0, result.stderr.decode())
                args = json.loads((work / "capture").read_text())
                require(args[args.index("-nic") + 1] == "none" and "-netdev" not in args and
                        "hostfwd" not in " ".join(args) and "ip=dhcp" not in " ".join(args) and
                        "-snapshot" in args, "QEMU must use a disposable disk and no NIC")


def invoke(binary, work, payload, expected_status, expected_output=b"", error=b"", args=()):
    before = set(Path("/tmp").glob("iotbench-connection.*"))
    env = {"PATH": "/usr/bin:/bin", "LC_ALL": "C",
           "ASAN_OPTIONS": "detect_leaks=0:halt_on_error=1:abort_on_error=0:exitcode=86",
           "UBSAN_OPTIONS": "halt_on_error=1:print_stacktrace=1"}
    result = command([binary, *args], input=payload, cwd=work, env=env)
    require(result.returncode == expected_status and result.stdout == expected_output and
            result.stderr == NOTICE + error,
            f"{binary.name} input={payload!r}: {result.returncode}, {result.stdout!r}, {result.stderr!r}")
    require(set(Path("/tmp").glob("iotbench-connection.*")) == before, "Leaked temporary resource")
    require(not list(work.iterdir()), "Unexpected file in working directory")


def behavior(binary, work):
    def ok(field, readonly):
        invoke(binary, work, frame(field), 0, f"OK readonly={readonly} marker={MARKER}\n".encode())

    for field in (b"private", b"shared", b"pr%69vate", b"private&mode=rw",
                  b"private&padding=" + b"A" * 240, b"private&padding='quoted'",
                  b"private&padding=http://synthetic.invalid/"):
        ok(field, 1)
    for field in (b"private&mode=rw#", b"private#", b"private&mode=rw#mode=ro"):
        ok(field, 0)
        ok(b"private", 1)  # Prove reset after every successful injection.
    for field in (b"", b"bad", b"A" * 256, b"'private'", b'"private"',
                  b"private%23", b"private%26mode=rw", b"private;mode=rw#",
                  b"private&mode=bad#", b"private&mode=ro&mode=rw#",
                  b"private&vfs=unix-none#", b"private&vfs=missing#",
                  b"private&mode=memory#"):
        # mode=memory has no table: it is disposable memory, never an external DB.
        error = b"ERR RESOURCE\n" if field == b"private&mode=memory#" else b"ERR CONNECT\n"
        invoke(binary, work, frame(field), 3, error=error)
    invalid = [b"", b"\x00", b"\x00\x02A", frame(b"private") + b"X",
               b"\x01\x01", b"\xff\xff", frame(b"A" * 257)]
    invalid += [frame(x) for x in (b"\x00", b"\x1f", b"\x7f", b"\xff", b"%", b"%0", b"%GG",
                                  b"%00", b"%1f", b"%7f", b"%ff", b"%C3%A9")]
    for payload in invalid:
        invoke(binary, work, payload, 2, error=b"ERR INVALID\n")
    invoke(binary, work, frame(b"private"), 2, error=b"ERR INVALID\n", args=("extra",))
    rng = random.Random(20)
    for _ in range(30):
        field = bytes(rng.choice(b"abcdefghijklmnopqrstuvwxyz0123456789") for _ in range(rng.randrange(1, 257)))
        invoke(binary, work, frame(field), 3, error=b"ERR CONNECT\n")
    print(f"PASS {binary.name}: normal/injected effective modes, resource marker, boundaries, malformed inputs and reset")


def local():
    require(os.getuid() != 0 and os.getgid() != 0, "Run as an ordinary unprivileged user")
    with tempfile.TemporaryDirectory(prefix="iotbench-connection-tests-") as temporary:
        build = Path(temporary) / "build"
        work = Path(temporary) / "work"
        work.mkdir()
        base = ["make", "-C", SOURCE, f"BUILD_DIR={build}"]
        for settings in ([], ["IOTBENCH_BUILD_MODE=production", f"{ENABLE}=1"],
                         ["IOTBENCH_BUILD_MODE=fixture"]):
            result = command(base + settings + ["fixture"])
            require(result.returncode != 0 and not build.exists(), "Unguarded fixture build")
        result = command(base + ["production"])
        require(result.returncode == 0, result.stderr.decode())
        disabled = build / "fixture-connection-disabled"
        result = command([disabled], input=frame(b"private&mode=rw#"))
        require(result.returncode == 77 and not result.stdout and
                result.stderr == b"Native connection fixture disabled\n", "Production stub parsed input")
        symbols = command(["nm", "-a", disabled]).stdout
        require(all(name not in symbols for name in (b"read_cache", b"construct_connection", b"sqlite3_")),
                "Fixture symbols in production")
        require(b"libsqlite3" not in command(["readelf", "-d", disabled]).stdout,
                "Production links connector")
        optin = ["IOTBENCH_BUILD_MODE=fixture", f"{ENABLE}=1"]
        result = command(base + optin + ["fixture", "sanitize"])
        require(result.returncode == 0, result.stderr.decode())
        binary = build / "fixture-connection"
        for candidate in (binary, build / "fixture-connection-sanitize"):
            elf = command(["readelf", "-h", "-lW", "-d", "-sW", candidate]).stdout.decode()
            require("DYN (" in elf and "Flags: NOW PIE" in elf and "GNU_RELRO" in elf and
                    "BIND_NOW" in elf and "__stack_chk_fail" in elf and
                    any("GNU_STACK" in line and "RW " in line and "RWE" not in line for line in elf.splitlines()),
                    "Missing compiler hardening")
            behavior(candidate, work)
        digest = hashlib.sha256(binary.read_bytes()).hexdigest()
        require(command(base + optin + ["fixture"]).returncode == 0 and
                hashlib.sha256(binary.read_bytes()).hexdigest() == digest, "Nonreproducible native rebuild")
        # A temporary repaired control proves the witness depends on the one
        # missing whitelist. It is never included in a firmware package.
        repaired = Path(temporary) / "repaired"
        shutil.copytree(SOURCE, repaired)
        path = repaired / "fixture-connection.c"
        source = path.read_text()
        needle = "if (argc != 1 || !read_cache(field))"
        require(source.count(needle) == 1, "Repaired-control insertion ambiguous")
        path.write_text(source.replace(needle, "if (argc != 1 || !read_cache(field) || "
                                       '(strcmp(field, "private") != 0 && strcmp(field, "shared") != 0))'))
        repaired_build = Path(temporary) / "repaired-build"
        result = command(["make", "-C", repaired, f"BUILD_DIR={repaired_build}", *optin, "sanitize"])
        require(result.returncode == 0, result.stderr.decode())
        fixed = repaired_build / "fixture-connection-sanitize"
        for field in (b"private", b"shared"):
            invoke(fixed, work, frame(field), 0, f"OK readonly=1 marker={MARKER}\n".encode())
        for field in (b"private&mode=rw#", b"private#", b"", b"A" * 256):
            invoke(fixed, work, frame(field), 2, error=b"ERR INVALID\n")
        print("PASS ASan/UBSan, repaired control, production stub, hardening and reproducible native rebuild")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--static", action="store_true")
    selection.add_argument("--local", action="store_true")
    selection.add_argument("--binary", type=Path, help="exercise an existing matching-architecture ELF")
    args = parser.parse_args()
    if args.binary:
        with tempfile.TemporaryDirectory(prefix="iotbench-connection-existing-") as temporary:
            behavior(args.binary.resolve(), Path(temporary))
    else:
        integration()
        if args.local:
            local()


if __name__ == "__main__":
    main()
