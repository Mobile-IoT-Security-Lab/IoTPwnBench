#!/usr/bin/env python3
"""Verify scripts/build-all.sh without building anything.

Checks the shell syntax, the dry-run plan against the recipes in both modes,
the filters and the real execution path with a stub `docker` on PATH, so no
Yocto build runs. Requires only Python 3 and a POSIX sh.
"""
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build-all.sh"
IMAGES = ROOT / "meta-iotbench/recipes-images"
MACHINES = ["qemuarm64", "qemuarm", "qemux86-64", "qemux86", "qemumips"]
CWE120_FLAG = "IOTBENCH_ENABLE_CWE120_FIXTURE"
FLAG_RE = re.compile(r"IOTBENCH_ENABLE_[A-Z0-9_]+_FIXTURE")


def clean_env(**extra):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith("IOTBENCH_") and k not in ("MACHINES", "BUILD_ALL")}
    env.update(extra)
    return env


def run(args, cwd=ROOT, env=None, check=None):
    result = subprocess.run(["sh", str(SCRIPT)] + args, cwd=cwd,
                            env=clean_env() if env is None else env,
                            capture_output=True, text=True)
    if check is not None:
        assert result.returncode == check, (args, result.returncode, result.stderr)
    return result


def all_ids():
    return sorted(p.stem[len("iotbench-"):] for p in IMAGES.glob("iotbench-*.bb"))


def firmware_ids():
    """The vulnerable images. Corrected twins end in -fixed and are opt-in."""
    return [f for f in all_ids() if not f.endswith("-fixed")]


def twin_ids():
    return [f for f in all_ids() if f.endswith("-fixed")]


def image_flags(recipe, seen=None):
    """Opt-in flags named by a recipe and by the files it requires."""
    seen = set() if seen is None else seen
    text = recipe.read_text(errors="ignore")
    flags = set(FLAG_RE.findall(text))
    for name in re.findall(r"^\s*(?:require|include)\s+(\S+)", text, re.M):
        candidate = IMAGES / Path(name).name
        if candidate.is_file() and candidate not in seen:
            seen.add(candidate)
            flags |= image_flags(candidate, seen)
    return flags


def expected_flag(firmware):
    flags = image_flags(IMAGES / f"iotbench-{firmware}.bb")
    if firmware.removesuffix("-fixed").endswith("-cwe120-service-buffer-overflow"):
        # The guard lives in the vulnerability recipe, not in the image recipe.
        guard = ROOT / "meta-iotbench/recipes-vulns/cwe120-service-buffer-overflow"
        assert any(CWE120_FLAG in p.read_text() for p in guard.glob("*.bb"))
        flags.add(CWE120_FLAG)
    assert len(flags) <= 1, (firmware, flags)
    return next(iter(flags), None)


def parse_plan(stdout):
    plan = []
    for line in stdout.splitlines():
        match = re.match(r"YOCTO_MACHINE=(\S+) FIRMWARE=(\S+) "
                         r"IOTBENCH_ENABLE_CWE120_FIXTURE=([01]) docker compose run --rm(.*) yocto$", line)
        assert match, line
        env = dict(item.split("=", 1) for item in re.findall(r"-e (\S+)", match.group(4)))
        env[CWE120_FLAG] = match.group(3)
        plan.append((match.group(1), match.group(2), env))
    return plan


def test_syntax():
    checked = []
    for shell in (["sh", "-n"], ["dash", "-n"], ["bash", "--posix", "-n"]):
        if shutil.which(shell[0]):
            subprocess.run(shell + [str(SCRIPT)], check=True)
            checked.append(shell[0])
    assert checked, "no shell available"
    if shutil.which("shellcheck"):
        subprocess.run(["shellcheck", "-s", "sh", str(SCRIPT)], check=True)
        checked.append("shellcheck")
    else:
        print("NOTE shellcheck not installed, static analysis skipped")
    print("PASS syntax:", ", ".join(checked))


def test_all_plan():
    ids = firmware_ids()
    result = run(["--all", "--dry-run"], check=0)
    assert "WARNING" not in result.stderr, result.stderr
    plan = parse_plan(result.stdout)
    assert len(plan) == len(ids) * len(MACHINES), len(plan)
    assert len({(m, f) for m, f, _ in plan}) == len(plan), "duplicate build"
    assert {f for _, f, _ in plan} == set(ids), "a recipe is missing from the plan"
    assert {m for m, _, _ in plan} == set(MACHINES)
    used = set()
    for machine, firmware, env in plan:
        flag = expected_flag(firmware)
        enabled = {k for k, v in env.items() if k.startswith("IOTBENCH_ENABLE_") and v == "1"}
        assert enabled == ({flag} if flag else set()), (firmware, env)
        assert env.get(CWE120_FLAG) in ("0", "1"), (firmware, env)
        if flag and flag != CWE120_FLAG:
            assert env.get("IOTBENCH_BUILD_MODE") == "fixture", (firmware, env)
        else:
            assert "IOTBENCH_BUILD_MODE" not in env, (firmware, env)
        used |= enabled
    in_recipes = set()
    for path in (ROOT / "meta-iotbench").rglob("*"):
        if path.suffix in (".bb", ".inc") and path.is_file():
            in_recipes |= set(FLAG_RE.findall(path.read_text(errors="ignore")))
    assert in_recipes <= used, ("flags never enabled", in_recipes - used)
    opt_in = sum(1 for f in ids if expected_flag(f))
    print(f"PASS --all plan: {len(plan)} builds, {len(ids)} firmware, "
          f"{opt_in} opt-in, {len(used)} flag families")


def test_fixed_twins():
    """Corrected twins are built only on request and keep the family of their original."""
    twins = twin_ids()
    assert twins, "no corrected twin found"
    for twin in twins:
        assert twin.removesuffix("-fixed") in firmware_ids(), f"{twin} has no vulnerable original"
        assert expected_flag(twin) == expected_flag(twin.removesuffix("-fixed")), twin
    default = parse_plan(run(["--all", "--dry-run"], check=0).stdout)
    assert not any(f.endswith("-fixed") for _, f, _ in default), "twins must be opt-in"
    only = parse_plan(run(["--only-fixed", "--all", "-m", "qemuarm64", "--dry-run"], check=0).stdout)
    assert sorted(f for _, f, _ in only) == twins
    both = parse_plan(run(["--fixed", "--all", "-m", "qemuarm64", "--dry-run"], check=0).stdout)
    assert len(both) == len(firmware_ids()) + len(twins)
    print(f"PASS corrected twins: {len(twins)} twins, opt-in with --fixed or --only-fixed")


def test_default_mode():
    """Without arguments the script keeps its historical behavior."""
    def plan(extra=None):
        result = run(["--dry-run"], env=clean_env(**(extra or {})), check=0)
        assert "WARNING" not in result.stderr, result.stderr
        return parse_plan(result.stdout)

    ids = firmware_ids()
    default_ids = sorted(f for f in ids if not expected_flag(f))
    default = plan()
    assert {m for m, _, _ in default} == {"qemuarm64"}, "default machine changed"
    assert sorted(f for _, f, _ in default) == default_ids, "opt-in fixtures must be skipped by default"
    one = "IOTBENCH_ENABLE_APACHE_FIXTURE"
    enabled = plan({one: "1"})
    wanted = sorted(f for f in ids if expected_flag(f) in (None, one))
    assert sorted(f for _, f, _ in enabled) == wanted, "one exported flag must add only its own family"
    assert plan({one: "0"}) == default, "a flag set to 0 must not enable a family"
    assert len(plan({"MACHINES": "qemuarm qemux86"})) == 2 * len(default_ids)
    assert len(plan({"BUILD_ALL": "1"})) == len(ids) * len(MACHINES), "BUILD_ALL must act as --all"
    print(f"PASS default mode: {len(default_ids)} default builds, {len(wanted)} with {one}")


def test_list_and_filters():
    ids = firmware_ids()
    listing = run(["--list"], check=0)
    assert len(listing.stdout.splitlines()) == len(ids)
    one = run(["-n", "--all", "-m", "qemuarm64", "-d", "router", "-s", "cwe120-*"], check=0)
    assert [(m, f) for m, f, _ in parse_plan(one.stdout)] == [
        ("qemuarm64", "router-cwe120-service-buffer-overflow")]
    two = run(["-n", "-m", "qemuarm qemumips", "-f", "plc-cwe121-modbus-stack-overflow"], check=0)
    assert [m for m, _, _ in parse_plan(two.stdout)] == ["qemuarm", "qemumips"]
    assert run(["-n", "-m", "qemuriscv"]).returncode == 2
    assert run(["-n", "-s", "no-such-scenario*"]).returncode == 2
    assert run(["--bogus"]).returncode == 2
    print("PASS list and filters")


def test_execution():
    """Run the real path against a stub docker that records its calls."""
    with tempfile.TemporaryDirectory(prefix="build-all-") as tmp:
        work = Path(tmp)
        (work / "scripts").mkdir()
        shutil.copy(SCRIPT, work / "scripts/build-all.sh")
        (work / "meta-iotbench").symlink_to(ROOT / "meta-iotbench")
        bindir = work / "bin"
        bindir.mkdir()
        log = work / "docker.log"
        stub = bindir / "docker"
        stub.write_text('#!/bin/sh\necho "$YOCTO_MACHINE $FIRMWARE cwe120=${IOTBENCH_ENABLE_CWE120_FIXTURE-unset} $*" >> "$STUB_LOG"\n'
                        '[ -n "${FAIL_FIRMWARE:-}" ] && [ "$FIRMWARE" = "$FAIL_FIRMWARE" ] && exit 1\n'
                        'exit 0\n')
        stub.chmod(0o755)
        base = clean_env(PATH=f"{bindir}{os.pathsep}{os.environ['PATH']}", STUB_LOG=str(log),
                         FAILURES_FILE=str(work / "failures.txt"))
        names = ["router-cwe276-leaked-private-key", "plc-cwe120-service-buffer-overflow"]
        cwe120 = names[1]
        first, second = sorted(names)  # the script builds in sorted recipe order
        args = ["--all", "-m", "qemuarm64", "-f", f"{first} {second}"]
        script = ["sh", str(work / "scripts/build-all.sh")]

        def go(extra, **env):
            log.write_text("")
            return subprocess.run(script + args + extra, cwd=work, env={**base, **env},
                                  capture_output=True, text=True)

        done = go([])
        assert done.returncode == 0, done.stderr
        calls = log.read_text().splitlines()
        assert len(calls) == 2 and not any("compose build" in c for c in calls), calls
        assert f"qemuarm64 {first} " in calls[0] and f"qemuarm64 {second} " in calls[1], calls
        for call in calls:
            wanted = "cwe120=1" if cwe120 in call else "cwe120=0"
            assert wanted in call, call
        # An ordinary build must stay identical to a plain compose run.
        ordinary = next(c for c in calls if cwe120 not in c)
        assert ordinary == f"qemuarm64 {ordinary.split()[1]} cwe120=0 compose run --rm yocto", ordinary
        assert "Summary: planned=2 built=2 skipped=0 failed=0" in done.stdout, done.stdout

        builder = go(["--build-builder"])
        calls = log.read_text().splitlines()
        assert builder.returncode == 0 and len(calls) == 3 and calls[0].endswith("compose build yocto"), calls

        stop = go([], FAIL_FIRMWARE=first)
        assert stop.returncode == 1 and len(log.read_text().splitlines()) == 1, stop.stderr

        keep = go(["--keep-going"], FAIL_FIRMWARE=first)
        assert keep.returncode == 1 and len(log.read_text().splitlines()) == 2
        assert "failed=1" in keep.stdout
        assert (work / "failures.txt").read_text() == f"qemuarm64 {first}\n"

        fake = work / "deploy-images" / first / "qemuarm64"
        fake.mkdir(parents=True)
        (fake / f"iotbench-{first}-qemuarm64.rootfs.ext4.zst").write_text("x")
        skip = go(["--skip-existing"])
        assert skip.returncode == 0 and "skipped=1" in skip.stdout, skip.stdout
        assert len(log.read_text().splitlines()) == 1

        # Without --all an unexported opt-in family is skipped, with the flag it builds.
        log.write_text("")
        plain = subprocess.run(script + ["-m", "qemuarm64", "-f", cwe120], cwd=work, env=base,
                               capture_output=True, text=True)
        assert plain.returncode == 0 and "Skipping opt-in fixture" in plain.stdout, plain.stdout
        assert log.read_text() == ""
        subprocess.run(script + ["-m", "qemuarm64", "-f", cwe120], cwd=work,
                       env={**base, CWE120_FLAG: "1"}, check=True, capture_output=True, text=True)
        assert "cwe120=1" in log.read_text()
    print("PASS execution: build, builder image, stop on failure, keep-going, skip-existing, opt-in")


def main():
    assert SCRIPT.is_file() and os.access(SCRIPT, os.X_OK), "scripts/build-all.sh must be executable"
    test_syntax()
    test_all_plan()
    test_fixed_twins()
    test_default_mode()
    test_list_and_filters()
    test_execution()
    print("PASS all")


if __name__ == "__main__":
    main()
