# Francesco Payloads

## How to use this guide

Start by choosing a scenario from the [manual test index](#manual-test-index)
below, then build and boot its firmware and run the manual test described in
that scenario's own section. All 23 scenarios in this document were
implemented by Francesco in the IoTBench repository. The corresponding catalog
rows use `OWNER = Francesco`, `Implemented = V`, and one implemented test per
firmware scenario. The complete 34-image benchmark index, including the shared
CWE-78 device scenarios, is in [device-payloads.md](device-payloads.md).

> **Warning:** these images are intentionally vulnerable. Run them only in an
> isolated, disposable QEMU lab. Never deploy them or expose them to untrusted
> networks.

### Common setup

- **Host**: the computer running Docker. Open a terminal at the root of this
  repository, where `compose.yaml` and `scripts/` are located.
- **Guest**: the Linux firmware running inside QEMU. For tests marked
  `[SERIAL]`, wait for `login:` in the QEMU terminal and sign in with username
  `root` and password `routeradmin`. The password is not displayed while you
  type.
- **Second host terminal**: use this for SSH, TCP, Modbus and MQTT requests;
  keep QEMU running in the first terminal. Run HTTP/dashboard tests in the
  host browser or with `curl`.
- **Always stop the previous guest before booting the next one.**
  `run-qemu-docker.sh` uses host networking, so a running guest keeps its
  forwarded ports (`8080`, `2222`, `9090`, `1883`, `1502`, `17754`, `18000`,
  `2575`, ...) and the next boot fails with
  `Could not set up host forwarding rule`. One-liner that stops any running
  IoTBench guest:

  ```bash
  docker ps -q --filter name=iotbench-qemu | xargs -r docker stop
  ```

This session's host has Docker but no host-installed QEMU, so every scenario
below boots through `scripts/run-qemu-docker.sh`, which reuses the
`qemu-system-aarch64` binary already built into the `yocto-build` Docker
volume and needs nothing installed on the host. If your host does have QEMU
and `zstd` installed, `scripts/run-qemu.sh` boots the same exported image
directly instead; the manual test for each scenario is identical either way.

For scripted dashboard calls, load `/`, read the `meta[name="dashboard-token"]`
value, then POST JSON to `/api.php` with header `X-Dashboard-Token: <token>`.
The dashboard forms already perform that step; a plain browser visit to
`http://127.0.0.1:8080` is enough for manual testing.

### Build and boot any device

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
protocol on `:2575`, for the images that need them. Stop the guest when done:

```bash
docker stop iotbench-qemu-"$TEST_FIRMWARE"-qemuarm64
```

### Manual test index

| Test | Firmware id | Where to run it | Evidence of the defect |
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

### Technical references

This guide documents the Francesco firmware scenarios: 13 router images that
each add one independent vulnerability package to the shared router dashboard,
and 10 device-specific images that each reproduce a CVE-inspired weakness on
one device's native protocol. Every scenario installs the device's normal
profile plus exactly one vulnerability package; no scenario in this document
is shared across multiple device profiles. The wire payloads and the CVE each
device scenario is inspired by are also indexed, together with the shared
CWE-78 per-device scenarios, in [device-payloads.md](device-payloads.md). All
23 scenarios were boot-tested end to end in this session; dates,
SHA-256 digests of the exported images and the one defect found and fixed
during testing are recorded in
[validation/francesco-manual-boot-validation-2026-10-30.md](validation/francesco-manual-boot-validation-2026-10-30.md).
That record is a manual boot-and-exploit log, not an automated regression
suite: none of these 23 scenarios currently has a `scripts/test-*.py` runner
of its own, unlike several of the scenarios documented in
[luca-payloads.md](luca-payloads.md).

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
run were both executed directly during this session, not only relayed from
Francesco). Exported rootfs SHA-256:
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
