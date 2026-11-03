"""Specs for the scenarios that exist on every device, keyed by the scenario slug.

Each entry is a function that takes the device class and returns the same tuple
as SCENARIOS (kind, payload, signal regex, normal payload, normal signal).
Kinds
  host      the signal must appear on a vulnerable image and must not on a corrected twin
  selftest  the module's own installed regression must pass on both, as the twin has its own corrected one
"""
import base64
import json
import re
from pathlib import Path

from scenarios import dashboard_action, guest_steps, guest_python

ROOT = Path(__file__).resolve().parents[2]
VULNS = ROOT / "meta-iotbench/recipes-vulns"


def probe(command, signal):
    return lambda device: ("host", guest_steps(command), signal, None, None)


def selftest(extension="sh"):
    runner = "sh" if extension == "sh" else "python3"
    command = (f"n=0; for t in /usr/share/iotbench/*/test-guest.{extension}; do [ -e \"$t\" ] || continue; n=1; "
               f"{runner} \"$t\" DEVICE >/tmp/st.out 2>&1 && echo SELFTEST_OK || {{ echo SELFTEST_FAIL; tail -4 /tmp/st.out; }}; done; "
               "[ $n = 1 ] || echo SELFTEST_NONE")
    return lambda device: ("selftest", guest_steps(command.replace("DEVICE", device)), r"SELFTEST_OK", None, None)


SHARED = {
    "cwe276-allow-anonymous-login": probe("grep -h '^anonymous_enable' /etc/iotbench/vsftpd-anonymous.conf", r"anonymous_enable=YES"),
    "cwe276-permit-root-login": probe("cat /etc/ssh/sshd_config.d/00-iotbench-permit-root-login.conf", r"PermitRootLogin\s+yes"),
    "cwe521-permit-empty-passwords": probe("grep -i '^PermitEmptyPasswords' /etc/ssh/sshd_config", r"PermitEmptyPasswords\s+yes"),
    "cwe250-dangerous-suid-rights": probe("stat -c 'MODE=%a' /usr/bin/iotbench-suid-fixture", r"MODE=4755"),
    "cwe276-bad-write-rights": probe("stat -c 'MODE=%a' /srv/iotbench-ftp/bad", r"MODE=775"),
    "cwe327-weak-cipher": probe("echo hello | /usr/bin/iotbench-weak-cipher encrypt 2>&1", r"3DES-CBC:"),
    "cwe798-hardcoded-credentials": probe(
        "grep -c 'iotbench-support-2026' /usr/share/router-dashboard/modules/hardcoded-credentials/module.php",
        r"\b[1-9]\d*\s*$"),
    "cwe798-hardcoded-user-passwords": probe("cat /etc/iotbench/hardcoded-user-passwords/accounts.conf", r"fixtureuser:fixture-password-123"),
    "cwe862-mqtt-internal-files": probe(
        "out=$(mosquitto_sub -h 127.0.0.1 -t device/config -C 1 -W 10 2>/dev/null); [ -n \"$out\" ] && echo LEAKED", r"LEAKED"),
    "cwe476-null-pointer-dereference": selftest(),
    "cwe190-integer-overflow": selftest(),
    "cwe787-native-buffer-overflow": selftest(),
    "cwe089-c-sql-injection": selftest(),
    "cwe089-java-sql-injection": selftest(),
    "cwe022-bad-sudo-rights": selftest(),
    "cwe022-bash-path-traversal": selftest(),
    "cwe020-native-connection-string": selftest(),
}

# Root is deliberately locked on the embedded-auth family (see
# iotbench-embedded-auth.inc), so no guest-login entry is defined here; run.py's
# check() special-cases the "cwe798-embedded-auth-*" slug and inspects the
# exported rootfs offline (debugfs + scripts/test-embedded-auth-fixture.py)
# instead of booting it, per docs/marco-payloads.md's documented procedure.

# One leaked line per password-leak variant, read from the source of the fixture.
_findings = json.loads((VULNS / "cwe798-password-leak/files/expected-findings.json").read_text())
for _variant, _finding in _findings.items():
    _source = ROOT / _finding["source_path"]
    _line = _source.read_text().splitlines()[_finding["line"] - 1].strip()
    # The corrected twin keeps the file but defers the secret to runtime provisioning, so the
    # file still names RUNTIME_SECRET (the placeholder, or the environment variable in C sources).
    SHARED[f"cwe798-password-leak-{_variant}"] = (lambda path, number, text: lambda device: (
        "host", guest_steps(f"sed -n '{number}p' /{path}"), re.escape(text),
        guest_steps(f"grep -h RUNTIME_SECRET /{path}"), r"RUNTIME_SECRET"))(
            _finding["path"], _finding["line"], _line)


def selftest_command(command_template, signal=r"EXIT=0"):
    def run(device):
        command = command_template.format(device=device)
        target = command.split()[1] if command.startswith(("python3 ", "sh ")) else command.split()[0]
        full = (f"[ -e '{target}' ] || echo SELFTEST_NONE; "
               f"[ -e '{target}' ] && {{ {command} >/tmp/st.out 2>&1; echo EXIT=$?; tail -c 2000 /tmp/st.out; }}")
        return ("selftest", guest_steps(full), signal, None, None)
    return run




def _service_buffer_overflow(device):
    # The ASAN binary needs more than the 5 CPU seconds the shipped test allows on the emulated guest,
    # and test-guest.sh has its directory hardcoded, so run a patched copy of both.
    prepare = ("rm -rf /tmp/sbo; cp -r /usr/share/iotbench/service-buffer-overflow /tmp/sbo 2>/dev/null && "
               "sed -i 's/RLIMIT_CPU, (5, 5)/RLIMIT_CPU, (600, 600)/' /tmp/sbo/test-service.py && "
               "sed 's#^data=.*#data=/tmp/sbo#; s/RuntimeMaxSec=60/RuntimeMaxSec=1800/' /usr/share/iotbench/service-buffer-overflow/test-guest.sh "
               "> /tmp/sbo/test-guest.sh")
    run = (f"[ -e /tmp/sbo/test-guest.sh ] || echo SELFTEST_NONE; "
           f"[ -e /tmp/sbo/test-guest.sh ] && {{ sh /tmp/sbo/test-guest.sh {device} >/tmp/st.out 2>&1; "
           "echo EXIT=$?; tail -c 2000 /tmp/st.out; }")
    return ("selftest", guest_steps(prepare, run, timeout=900), r"EXIT=0", None, None)


SHARED["cwe120-service-buffer-overflow"] = _service_buffer_overflow
def _unpriv_runner(path):
    script = ("import os, subprocess, sys\n"
             "os.setgroups([])\n"
             "os.setgid(1000)\n"
             "os.setuid(1000)\n"
             f"result = subprocess.run(['python3', '{path}/fixture-runner.py', '--isolated-fixture'],\n"
             "                        capture_output=True, text=True)\n"
             "print(result.stdout, result.stderr)\n"
             "print('EXIT=' + str(result.returncode))\n")
    code = ("echo 1 > /proc/sys/net/core/fb_tunnels_only_for_init_net",) + guest_python(script)[1]

    def run(device):
        return ("selftest", ("guest", code, 0), r"EXIT=0", None, None)
    return run


SHARED["cwe061-native-symlink-following"] = _unpriv_runner("/usr/share/iotbench/native-symlink")
SHARED["cwe022-native-path-traversal"] = _unpriv_runner("/usr/share/iotbench/native-path")
SHARED["cwe020-native-filename-validation"] = _unpriv_runner("/usr/share/iotbench/native-path")
# The vulnerable policy keeps POSIXLY_CORRECT through sudo, which changes the units of du; the twin resets it.
SHARED["cwe798-sudo-environment"] = probe(
    "grep -h env_keep /etc/sudoers.d/iotbench-sudo-environment", r'env_keep\s*=\s*"POSIXLY_CORRECT"')

_JAVA_DESERIALIZE = """
import os, subprocess
root = "/usr/share/iotbench/java-deserialization-fixture"
cp = root + "/fixture-deserialization.jar:" + root + "/fixture-deserialization-tests.jar"
env = dict(os.environ, IOTBENCH_ENABLE_JAVA_DESERIALIZATION_FIXTURE="1")
vector = subprocess.run(["java", "-cp", cp, "org.iotbench.fixture.deserialization.FixtureHarness",
                         "generate", "marker"], capture_output=True, env=env).stdout
result = subprocess.run(["java", "-cp", cp, "org.iotbench.fixture.deserialization.FixtureDeserialize",
                         "--fixture-test"], input=vector, capture_output=True, env=env)
print(result.stdout.decode("utf-8", "replace"), result.stderr.decode("utf-8", "replace"))
"""


def _java_command(jar, payload, marker_file, marker_text):
    code = f"""
import os, subprocess
os.makedirs("/work", exist_ok=True)
env = dict(os.environ, IOTBENCH_ENABLE_JAVA_COMMAND_FIXTURE="1")
try:
    subprocess.run(["java", "-jar", "/usr/share/iotbench/java-command-fixture/{jar}", "--fixture-test"],
                   input={payload!r}, env=env, cwd="/work", timeout=40, capture_output=True)
except subprocess.TimeoutExpired:
    print("HARNESS_TIMEOUT")
    raise SystemExit(0)
path = "/work/{marker_file}"
print(open(path).read() if os.path.exists(path) else "NO_MARKER")
"""
    return lambda device: ("host", guest_python(code), marker_text, None, None)


SHARED["cwe502-java-deserialization"] = lambda device: (
    "host", guest_python(_JAVA_DESERIALIZE), r"UNEXPECTED_TYPE", None, None)
SHARED["cwe078-java-os-command-injection"] = _java_command(
    "fixture-os-command.jar", b"label=sensor' > normal.txt; printf 'JAVA_OS_MARKER\\n' > os-marker.txt; #\n",
    "os-marker.txt", "JAVA_OS_MARKER")
SHARED["cwe077-java-app-command-injection"] = _java_command(
    "fixture-app-command.jar", b"label=sensor;mark\n", "app-marker.txt", "JAVA_APP_MARKER")
