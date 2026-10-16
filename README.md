# IoTBench

A benchmark of deliberately vulnerable Yocto firmwares for `qemuarm64`. Each
firmware is a **device profile** (a skeleton IoT app with simulated peripherals)
plus **one** vulnerability implementing a distinct CWE, so every image is a
clean, reproducible target for security tooling. The catalog is a matrix of
device types × CWEs.

> **Warning:** these images are intentionally vulnerable. Run them only in an
> isolated, disposable lab. Never deploy them or expose them to untrusted
> networks.

The first device is a **router**: a PHP management dashboard served by lighttpd,
showing real system metrics, simulated Wi-Fi/LAN/DHCP settings, client
management, and a live **Sensors** panel fed by the peripheral simulator. Actions
in the UI do not change the Linux network; demo state is stored in
`/var/lib/router-dashboard/settings.json`.

## Layout

```text
builder/                  generic Yocto builder, copied into the image
├── site.conf             cache locations (DL_DIR, SSTATE_DIR, hash equivalence)
├── yocto-env.sh          sets up /workdir/build for YOCTO_MACHINE and YOCTO_LAYERS
└── warm-cache.sh         fills the cache without exporting firmware
meta-iotbench/            OpenEmbedded layer
├── recipes-platform/     shared across devices: iotbench-sim, lighttpd, php
├── recipes-devices/      one directory per device profile (skeleton app + peripherals)
├── recipes-vulns/        one directory per CWE module (vulnerable code / module)
└── recipes-images/       iotbench-image.inc + one iotbench-<device>-<cwe>.bb per target
scripts/
├── container-build-and-export.sh   builds the selected firmware (run by Compose)
├── build-all.sh                    builds every firmware in turn
└── run-qemu.sh                     boots an exported firmware on the host
```

The build also uses `meta-openembedded/meta-oe`, pinned to a revision compatible
with the `wrynose` series, for the PHP recipe.

## Devices and peripherals

A firmware is a **device profile** plus **one vulnerability**. The device profile
(`recipes-devices/<device>/`) provides the skeleton app and a peripheral spec;
the vulnerability (`recipes-vulns/<cwe>/`) implements one CWE. The firmware id is
`<device>-<cwe>-<slug>`, so the catalog is a matrix of devices × CWEs.

Peripheral values are not static: a shared daemon, `iotbench-sim`, reads each
device's `/etc/iotbench/peripherals.conf` and writes live values every few
seconds to `/run/iotbench/state.json` and `/run/iotbench/state.env`. The models
are standard stochastic processes used for synthetic sensor/telemetry generation:

- **Ornstein–Uhlenbeck** mean-reverting process for continuous sensors
  (temperature, RSSI, power…) — bounded, realistic drift (Uhlenbeck & Ornstein,
  *Phys. Rev.* 36, 1930);
- **seasonal (diurnal) mean + Gaussian noise** for daily-cycle signals;
- **two-state (random telegraph) Markov process** for binary actuators;
- **finite-state Markov jump process** for enumerated states;
- **monotonic accumulators** for counters (e.g. energy).

Each device exposes those values over a native protocol, on top of the shared
web admin (which shows them in a **Sensors** panel):

| Device | Native service | Endpoint |
| --- | --- | --- |
| router | web admin | HTTP :80 |
| ipcamera | HTTP snapshot + MJPEG stream | `/snapshot.jpg`, `/stream.cgi` |
| smartplug, thermostat, smartbulb, smarthub, envsensor, smartspeaker, healthmonitor, doorlock | MQTT publisher + local broker | `iotbench/<class>/<peripheral>` on :1883 |
| plc | Modbus/TCP server | registers on :502 |

## Firmware catalog

All device profiles retain their CWE-78 scenario. The router uses a web-admin
ping diagnostic; every other device reaches the flaw through its native HTTP,
MQTT, or Modbus service. Firmware id is
`<device>-cwe078-os-command-injection`.

| Device | Category | Native service |
| --- | --- | --- |
| `router` | network gateway | web admin (HTTP) |
| `ipcamera` | surveillance camera | PTZ CGI command injection over HTTP |
| `smartplug` | energy management | MQTT relay-schedule command injection |
| `thermostat` | climate control | MQTT HVAC-profile command injection |
| `plc` | industrial gateway (OT) | Modbus/TCP project-apply command injection |
| `smartbulb` | lighting | MQTT scene command injection |
| `smarthub` | controller / hub | MQTT pairing-backup command injection |
| `envsensor` | environmental sensor | MQTT calibration command injection |
| `smartspeaker` | audio / voice assistant | MQTT media-source command injection |
| `healthmonitor` | health monitor | MQTT export-target command injection |
| `doorlock` | access control | MQTT firmware-update command injection |

The catalog also includes one CVE-inspired, device-specific scenario for every
non-router profile. These are functional reproductions of the weakness and
attack surface, not copies of vendor firmware:

| Firmware id | CWE | Device-specific scenario |
| --- | --- | --- |
| `ipcamera-cwe022-recording-path-traversal` | CWE-22 | Recording-export CGI path traversal |
| `smartplug-cwe862-missing-authorization` | CWE-862 | Cross-owner MQTT relay control |
| `thermostat-cwe294-command-replay` | CWE-294 | Replayable authenticated setpoint frame |
| `smartbulb-cwe122-zcl-heap-overflow` | CWE-122 | ZCL commissioning string heap overflow |
| `smarthub-cwe121-database-stack-overflow` | CWE-121 | Hub database bucket stack overflow |
| `envsensor-cwe306-unauthenticated-calibration` | CWE-306 | Calibration change without authentication |
| `smartspeaker-cwe122-id3-heap-overflow` | CWE-122 | ID3 metadata heap overflow |
| `healthmonitor-cwe200-memory-disclosure` | CWE-200 | Unauthenticated patient-memory read |
| `doorlock-cwe294-unlock-replay` | CWE-294 | Replayable authenticated unlock frame |
| `plc-cwe121-modbus-stack-overflow` | CWE-121 | Vendor Modbus project-chunk stack overflow |

Each firmware maps to `recipes-images/iotbench-<firmware id>.bb`. The catalog is
the set of those recipes; the table above is a convenience copy. Every device
carries a distinct simulated peripheral set (`recipes-devices/<device>/files/peripherals.conf`).
Native-service payloads, register maps and CVE analogues are documented in
[docs/device-payloads.md](docs/device-payloads.md).

Additional router scenarios from the Francesco catalog slice:

| Firmware id | CWE | Scenario |
| --- | --- | --- |
| `router-cwe276-leaked-private-key` | CWE-276 | Private key exposed under the web document root |
| `router-cwe276-bad-chown-rights` | CWE-276 | Privileged configuration file owned by the web user |
| `router-cwe798-ld-preload-sudo` | CWE-798 | Hardcoded support password reaches an LD_PRELOAD-capable maintenance command |
| `router-cwe798-vi-privilege-escalation` | CWE-798 | Hardcoded maintenance password reaches a privileged editor workflow |
| `router-cwe078-writable-root-cron` | CWE-78 | Root cron interpolates a web-user-controlled target into a shell command |
| `router-cwe287-ssh-hardcoded-backdoor` | CWE-287 | Hardcoded SSH support account |
| `router-cwe089-http-sqli-auth` | CWE-89 | HTTP login SQL injection |
| `router-cwe078-bash-command-injection` | CWE-78 | Bash diagnostic command injection |
| `router-cwe077-c-command-injection` | CWE-77 | C helper command injection |
| `router-cwe416-use-after-free` | CWE-416 | Freed authorization object reuse |
| `router-cwe400-diagnostic-dos` | CWE-400 | Diagnostic resource exhaustion |
| `router-cwe078-service-interface-injection` | CWE-78 | TCP service interface command injection |
| `router-cwe022-path-traversal` | CWE-22 | Global Lighttpd fallback path traversal |

Payloads and expected exploit signals for these scenarios are documented in
[docs/francesco-payloads.md](docs/francesco-payloads.md).
That guide also identifies the canonical attacker position for each image:
remote HTTP, remote network service, or a local `routerweb` foothold.

### Weak cipher: Triple DES (CWE-327)

Every device also has a separate firmware that encrypts and decrypts device
backup data with **3DES-CBC** through the shared web admin. The vulnerability
package lives in `meta-iotbench/recipes-vulns/weak-cipher/` and installs the
**Device Backup Encryption** panel plus the `iotbench-weak-cipher` CLI helper.
Each image retains its device's native services and simulated peripherals.
The 3DES key, IV and HMAC key are hardcoded and identical in all eleven images;
the same plaintext produces the same encrypted frame. Their public hex values
are documented in [docs/luca-payloads.md](docs/luca-payloads.md).

| Firmware id | CWE | Scenario |
| --- | --- | --- |
| `router-cwe327-weak-cipher` | CWE-327 | 3DES device backup encryption |
| `ipcamera-cwe327-weak-cipher` | CWE-327 | 3DES device backup encryption |
| `smartplug-cwe327-weak-cipher` | CWE-327 | 3DES device backup encryption |
| `thermostat-cwe327-weak-cipher` | CWE-327 | 3DES device backup encryption |
| `plc-cwe327-weak-cipher` | CWE-327 | 3DES device backup encryption |
| `smartbulb-cwe327-weak-cipher` | CWE-327 | 3DES device backup encryption |
| `smarthub-cwe327-weak-cipher` | CWE-327 | 3DES device backup encryption |
| `envsensor-cwe327-weak-cipher` | CWE-327 | 3DES device backup encryption |
| `smartspeaker-cwe327-weak-cipher` | CWE-327 | 3DES device backup encryption |
| `healthmonitor-cwe327-weak-cipher` | CWE-327 | 3DES device backup encryption |
| `doorlock-cwe327-weak-cipher` | CWE-327 | 3DES device backup encryption |

Build and boot one device:

```bash
FIRMWARE=router-cwe327-weak-cipher docker compose run --rm yocto
FIRMWARE=router-cwe327-weak-cipher ./scripts/run-qemu.sh
```

Build only the eleven weak-cipher images for the default `qemuarm64` machine
(set `YOCTO_MACHINE` to build another supported architecture):

```bash
for recipe in meta-iotbench/recipes-images/iotbench-*-cwe327-weak-cipher.bb; do
    firmware=$(basename "$recipe" .bb)
    FIRMWARE="${firmware#iotbench-}" docker compose run --rm yocto || exit 1
done
```

The catalog-wide `scripts/build-all.sh` discovers these images automatically.
Build artifacts are exported to `deploy-images/<firmware>/<machine>/`.
See [docs/luca-payloads.md](docs/luca-payloads.md) for the frame format, API/CLI
examples and verification procedure.

### Allow anonymous login (CWE-276)

All eleven devices have a separate FTP maintenance image with permissive
default access. `vsftpd` accepts `anonymous` (or `ftp`) without a password and
publishes a readable backup of the device identity, peripheral specification
and dashboard settings. This models **CWE-276: Incorrect Default Permissions**:
maintenance data that should be private is available to every network client.
Each image installs only `cwe276-allow-anonymous-login` as its vulnerability
package and retains the device's native services and simulated peripherals.

| Firmware id | CWE | Scenario |
| --- | --- | --- |
| `doorlock-cwe276-allow-anonymous-login` | CWE-276 | Anonymous FTP maintenance backup access |
| `envsensor-cwe276-allow-anonymous-login` | CWE-276 | Anonymous FTP maintenance backup access |
| `healthmonitor-cwe276-allow-anonymous-login` | CWE-276 | Anonymous FTP maintenance backup access |
| `ipcamera-cwe276-allow-anonymous-login` | CWE-276 | Anonymous FTP maintenance backup access |
| `plc-cwe276-allow-anonymous-login` | CWE-276 | Anonymous FTP maintenance backup access |
| `router-cwe276-allow-anonymous-login` | CWE-276 | Anonymous FTP maintenance backup access |
| `smartbulb-cwe276-allow-anonymous-login` | CWE-276 | Anonymous FTP maintenance backup access |
| `smarthub-cwe276-allow-anonymous-login` | CWE-276 | Anonymous FTP maintenance backup access |
| `smartplug-cwe276-allow-anonymous-login` | CWE-276 | Anonymous FTP maintenance backup access |
| `smartspeaker-cwe276-allow-anonymous-login` | CWE-276 | Anonymous FTP maintenance backup access |
| `thermostat-cwe276-allow-anonymous-login` | CWE-276 | Anonymous FTP maintenance backup access |

Build, boot and verify one device:

```bash
FIRMWARE=router-cwe276-allow-anonymous-login docker compose run --rm yocto
FIRMWARE=router-cwe276-allow-anonymous-login ./scripts/run-qemu.sh
# Run in a second terminal while QEMU is running:
python3 scripts/test-anonymous-login.py --device router
```

Build only the eleven anonymous-login images (default `qemuarm64`):

```bash
for recipe in meta-iotbench/recipes-images/iotbench-*-cwe276-allow-anonymous-login.bb; do
    firmware=$(basename "$recipe" .bb)
    FIRMWARE="${firmware#iotbench-}" docker compose run --rm yocto || exit 1
done
```

`YOCTO_MACHINE` selects another supported architecture. Artifacts land in
`deploy-images/<device>-cwe276-allow-anonymous-login/<machine>/`; the existing
`scripts/build-all.sh` discovers these recipes automatically. QEMU forwards
FTP control to `127.0.0.1:2121` (`QEMU_FTP_PORT` overrides it) and passive data
to `127.0.0.1:30000-30009`. Use passive FTP; all forwarded ports bind to
loopback. See [docs/luca-payloads.md](docs/luca-payloads.md#allow-anonymous-login-cwe-276)
for configuration, payloads, expected results, verification and remediation.

### Hardcoded credentials (CWE-798)

Every device has a separate firmware with a **Vendor Support Backup** panel.
Its HTTP action authenticates against username `support` and password
`iotbench-support-2026`, embedded as plaintext PHP constants and identical in
all eleven images. The accepted credential exports a maintenance-only backup
stored outside the web document root, plus device identity, settings and live
peripherals. Incorrect or missing credentials are rejected. This reproduces
inbound authentication with a shared, unchangeable firmware credential.

Each image installs only `cwe798-hardcoded-credentials` as its vulnerability
package and retains its device's native services and simulated peripherals.

| Firmware id | CWE | Scenario |
| --- | --- | --- |
| `doorlock-cwe798-hardcoded-credentials` | CWE-798 | Shared vendor support credential |
| `envsensor-cwe798-hardcoded-credentials` | CWE-798 | Shared vendor support credential |
| `healthmonitor-cwe798-hardcoded-credentials` | CWE-798 | Shared vendor support credential |
| `ipcamera-cwe798-hardcoded-credentials` | CWE-798 | Shared vendor support credential |
| `plc-cwe798-hardcoded-credentials` | CWE-798 | Shared vendor support credential |
| `router-cwe798-hardcoded-credentials` | CWE-798 | Shared vendor support credential |
| `smartbulb-cwe798-hardcoded-credentials` | CWE-798 | Shared vendor support credential |
| `smarthub-cwe798-hardcoded-credentials` | CWE-798 | Shared vendor support credential |
| `smartplug-cwe798-hardcoded-credentials` | CWE-798 | Shared vendor support credential |
| `smartspeaker-cwe798-hardcoded-credentials` | CWE-798 | Shared vendor support credential |
| `thermostat-cwe798-hardcoded-credentials` | CWE-798 | Shared vendor support credential |

Build, boot and verify one device:

```bash
FIRMWARE=router-cwe798-hardcoded-credentials docker compose run --rm yocto
FIRMWARE=router-cwe798-hardcoded-credentials ./scripts/run-qemu.sh
# Run in a second terminal while QEMU is running:
python3 scripts/test-hardcoded-credentials.py --device router
```

Build only the eleven hardcoded-credential images (default `qemuarm64`):

```bash
for recipe in meta-iotbench/recipes-images/iotbench-*-cwe798-hardcoded-credentials.bb; do
    firmware=$(basename "$recipe" .bb)
    FIRMWARE="${firmware#iotbench-}" docker compose run --rm yocto || exit 1
done
```

`YOCTO_MACHINE` selects another supported architecture; the recipes are
architecture-independent. Artifacts land in
`deploy-images/<device>-cwe798-hardcoded-credentials/<machine>/` and
`scripts/build-all.sh` discovers these images automatically. The HTTP endpoint
is `http://127.0.0.1:8080` (`QEMU_HTTP_PORT` overrides it). This scenario uses
the web support account; the router's two existing CWE-798 sudo scenarios have
their own SSH entry points. See
[docs/luca-payloads.md](docs/luca-payloads.md#hardcoded-credentials-cwe-798)
for credentials, extraction, API payloads, expected signals and verification.

### Hardcoded Credentials — Hardcoding User Passwords (CWE-798)

> INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT

These separate local fixtures install the synthetic application account
`fixtureuser` with the fixed fake password `fixture-password-123` in
`/etc/iotbench/hardcoded-user-passwords/accounts.conf`. The local
`/usr/bin/iotbench-fixture-auth` helper consumes this account record, checks the
supplied username and stdin password, and prints a harmless marker only on
success. The account database is copied verbatim at build time, so every image
contains the same recoverable credential. Root-only file permissions do not
prevent offline firmware extraction.

| Firmware id | CWE | Scenario |
| --- | --- | --- |
| `doorlock-cwe798-hardcoded-user-passwords` | CWE-798 | Fixed synthetic local account password |
| `envsensor-cwe798-hardcoded-user-passwords` | CWE-798 | Fixed synthetic local account password |
| `healthmonitor-cwe798-hardcoded-user-passwords` | CWE-798 | Fixed synthetic local account password |
| `ipcamera-cwe798-hardcoded-user-passwords` | CWE-798 | Fixed synthetic local account password |
| `plc-cwe798-hardcoded-user-passwords` | CWE-798 | Fixed synthetic local account password |
| `router-cwe798-hardcoded-user-passwords` | CWE-798 | Fixed synthetic local account password |
| `smartbulb-cwe798-hardcoded-user-passwords` | CWE-798 | Fixed synthetic local account password |
| `smarthub-cwe798-hardcoded-user-passwords` | CWE-798 | Fixed synthetic local account password |
| `smartplug-cwe798-hardcoded-user-passwords` | CWE-798 | Fixed synthetic local account password |
| `smartspeaker-cwe798-hardcoded-user-passwords` | CWE-798 | Fixed synthetic local account password |
| `thermostat-cwe798-hardcoded-user-passwords` | CWE-798 | Fixed synthetic local account password |

Build and boot from the host repository root:

~~~bash
FIRMWARE=router-cwe798-hardcoded-user-passwords docker compose run --rm yocto
FIRMWARE=router-cwe798-hardcoded-user-passwords ./scripts/run-qemu.sh
~~~

From the guest root serial console (the existing `root` / `routeradmin` lab
login), run:

~~~bash
printf '%s\n' 'fixture-password-123' | iotbench-fixture-auth fixtureuser
sh /usr/share/iotbench/hardcoded-user-passwords/test-guest.sh router
~~~

Expected: `HARDCODED_USER_PASSWORD_ACCEPTED`, `AUTHENTICATED_AS=fixtureuser`
and exit zero for the first command; four `PASS` lines for the regression.
Wrong username/password combinations fail with status 1. The account is an
application identity with no OS login, shell or privilege grant. The fixture
uses no networking; device-native services come from the existing profiles.
It installs only `cwe798-hardcoded-user-passwords` as its vulnerability package.

Offline verification uses the builder's existing tools:

~~~bash
docker compose run --rm yocto python3 /scripts/test-hardcoded-user-passwords.py \
  --image /export/router-cwe798-hardcoded-user-passwords/qemuarm64/iotbench-router-cwe798-hardcoded-user-passwords-qemuarm64.rootfs.ext4.zst
# Automated serial testing; run separately from a manually running guest:
python3 scripts/test-hardcoded-user-passwords.py --device router
python3 scripts/test-hardcoded-user-passwords.py --all
~~~

Replace `router` with any listed device. Build all eleven using:

~~~bash
for recipe in meta-iotbench/recipes-images/iotbench-*-cwe798-hardcoded-user-passwords.bb; do
    firmware=$(basename "$recipe" .bb)
    FIRMWARE="${firmware#iotbench-}" docker compose run --rm yocto || exit 1
done
~~~

The existing `YOCTO_MACHINE` selector and `scripts/build-all.sh` apply; exports
go to `deploy-images/<device>-cwe798-hardcoded-user-passwords/<machine>/`.
Detection requires the installed account credential and its authentication
consumer, rather than a password-looking string alone. The exact ground-truth
label is **Hardcoded credentials — Hardcoding the user passwords**,
**CWE-798 — Use of Hard-coded Credentials**. See
[docs/luca-payloads.md](docs/luca-payloads.md#hardcoded-credentials--hardcoding-user-passwords-cwe-798)
for per-device files, build/test instructions and remediation.

### Bad SUDO Rights — Path Traversal (CWE-22)

> INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT

These fixtures show how an unsafe sudo rule lets a non-root user read a fake
root-only file. The same local test works on all eleven device profiles below.

There are two directories under `/usr/share/iotbench/bad-sudo-rights/`:

- `data/`: the directory the reader is supposed to allow.
- `private/`: a root-owned directory with mode `0700`, containing the fake
  `root-only.conf` file with mode `0600`. Only root can read it.

The synthetic user `fixturetest` has no root privileges. Its sudo rule permits
one specific reader to run as root with paths starting with `data/`:

```sudoers
fixturetest ALL=(root) NOPASSWD: /usr/bin/iotbench-maintenance-read /usr/share/iotbench/bad-sudo-rights/data/*
```

The mistake is that `*` also matches `../`, and the reader only checks the
start of the path. It does not check where the path actually leads. The reader
confines every read to the synthetic fixture tree, which contains both
directories; it cannot read other guest or host files.

| Firmware id | CWE | Scenario |
| --- | --- | --- |
| `doorlock-cwe022-bad-sudo-rights` | CWE-22 | Privileged sudo-helper path traversal |
| `envsensor-cwe022-bad-sudo-rights` | CWE-22 | Privileged sudo-helper path traversal |
| `healthmonitor-cwe022-bad-sudo-rights` | CWE-22 | Privileged sudo-helper path traversal |
| `ipcamera-cwe022-bad-sudo-rights` | CWE-22 | Privileged sudo-helper path traversal |
| `plc-cwe022-bad-sudo-rights` | CWE-22 | Privileged sudo-helper path traversal |
| `router-cwe022-bad-sudo-rights` | CWE-22 | Privileged sudo-helper path traversal |
| `smartbulb-cwe022-bad-sudo-rights` | CWE-22 | Privileged sudo-helper path traversal |
| `smarthub-cwe022-bad-sudo-rights` | CWE-22 | Privileged sudo-helper path traversal |
| `smartplug-cwe022-bad-sudo-rights` | CWE-22 | Privileged sudo-helper path traversal |
| `smartspeaker-cwe022-bad-sudo-rights` | CWE-22 | Privileged sudo-helper path traversal |
| `thermostat-cwe022-bad-sudo-rights` | CWE-22 | Privileged sudo-helper path traversal |

**Build and boot from the host**, in the repository root:

```bash
FIRMWARE=router-cwe022-bad-sudo-rights docker compose run --rm yocto
FIRMWARE=router-cwe022-bad-sudo-rights ./scripts/run-qemu.sh
```

Skip the build command if the image is already exported. On Apple Silicon,
prefix the boot command with `QEMU_ACCEL=hvf QEMU_CPU=host` for acceleration.
Log into the QEMU serial console with `root` / `routeradmin`.

**Example 1: direct read is denied.** Run this inside the guest:

```bash
sudo -n -u fixturetest -- cat \
  /usr/share/iotbench/bad-sudo-rights/private/root-only.conf
```

Expected: `Permission denied` and a nonzero exit status.

Here `-u fixturetest` tells sudo to run `cat` as the non-root user. It does
not give `cat` root privileges. That user cannot enter the private directory
or read the file. The normal filesystem permissions work correctly.

**Example 2: sudo plus traversal reads the same file.** Inside the guest:

```bash
sudo -n -u fixturetest -- sudo -n /usr/bin/iotbench-maintenance-read \
  /usr/share/iotbench/bad-sudo-rights/data/../private/root-only.conf
```

Expected output includes:

```text
READER_EUID=0
IOTBENCH_ROOT_ONLY_MAINTENANCE=ROOT_ONLY_PATH_TRAVERSAL_CONFIRMED
```

The first sudo switches from the root test console to `fixturetest`. The
second sudo uses that user's rule to run the reader as root. The rule accepts
the argument because it starts with `data/`, and its `*` matches the rest.
The reader also accepts that prefix without resolving the path first.

`../` means "go up one directory", so `data/../private/root-only.conf` leads
to `private/root-only.conf`. When the reader opens it, the filesystem resolves
`../` and checks the reader's privileges: it is now root (`READER_EUID=0`),
so the read succeeds. Both examples target the same file; they use different
execution privileges and the second bypasses the intended `data/` boundary.

The vulnerability is **Path Traversal reachable through an overly permissive
sudo rule / privileged sudo helper (CWE-22)**. Fix it by removing the wildcard
grant or allowing only an exact filename, and checking inside the helper that
the resolved file stays within `data/`, including protection against symlinks
and races. All fixture data is synthetic; the reader only reads files.

**Automatic testing:** from the guest root console, run:

```bash
sh /usr/share/iotbench/bad-sudo-rights/test-guest.sh router
```

Alternatively, after building, use the host runner. It boots and closes QEMU
itself; use it separately from a manually running guest:

```bash
python3 scripts/test-bad-sudo-rights.py --device router
# Test all eleven exported images:
python3 scripts/test-bad-sudo-rights.py --all
```

Replace `router` with another device from the table. Every image keeps its
existing device profile and installs only `cwe022-bad-sudo-rights` as its
vulnerability package. Exports go to
`deploy-images/<device>-cwe022-bad-sudo-rights/<machine>/`; `YOCTO_MACHINE`
selects the architecture and `scripts/build-all.sh` includes these fixtures.
See [docs/luca-payloads.md](docs/luca-payloads.md#bad-sudo-rights--path-traversal-cwe-22)
for per-device details and completed validation.

### Privilege Escalation Risk — Dangerous SUID Rights (CWE-250)

> INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT

Each device has a permissions-focused fixture containing
`/usr/bin/iotbench-suid-fixture`, a dedicated synthetic ELF helper owned by
`root:root` with mode **4755 (`-rwsr-xr-x`)**. The unprivileged `suidfixture`
user (UID/GID 993) can execute it, and SUID gives the helper effective UID 0.
The helper only prints a static marker and its execution identities; it
accepts no arguments and opens no files. Root privilege is unnecessary for
that behavior, so the expected finding is dangerous SUID rights / CWE-250.
This is a known-positive permissions sample without an exploitation chain.

| Firmware id | CWE | Scenario |
| --- | --- | --- |
| `doorlock-cwe250-dangerous-suid-rights` | CWE-250 | Unnecessary root-owned SUID helper |
| `envsensor-cwe250-dangerous-suid-rights` | CWE-250 | Unnecessary root-owned SUID helper |
| `healthmonitor-cwe250-dangerous-suid-rights` | CWE-250 | Unnecessary root-owned SUID helper |
| `ipcamera-cwe250-dangerous-suid-rights` | CWE-250 | Unnecessary root-owned SUID helper |
| `plc-cwe250-dangerous-suid-rights` | CWE-250 | Unnecessary root-owned SUID helper |
| `router-cwe250-dangerous-suid-rights` | CWE-250 | Unnecessary root-owned SUID helper |
| `smartbulb-cwe250-dangerous-suid-rights` | CWE-250 | Unnecessary root-owned SUID helper |
| `smarthub-cwe250-dangerous-suid-rights` | CWE-250 | Unnecessary root-owned SUID helper |
| `smartplug-cwe250-dangerous-suid-rights` | CWE-250 | Unnecessary root-owned SUID helper |
| `smartspeaker-cwe250-dangerous-suid-rights` | CWE-250 | Unnecessary root-owned SUID helper |
| `thermostat-cwe250-dangerous-suid-rights` | CWE-250 | Unnecessary root-owned SUID helper |

**Build if needed (host).** Run from the repository root. Skip this command
if the selected image has already been exported:

```bash
FIRMWARE=router-cwe250-dangerous-suid-rights docker compose run --rm yocto
```

**Static test (host, no QEMU needed).** Read the exported image's ownership
and permissions using the tools already available in the builder:

```bash
docker compose run --rm yocto python3 /scripts/test-dangerous-suid-rights.py \
  --image /export/router-cwe250-dangerous-suid-rights/qemuarm64/iotbench-router-cwe250-dangerous-suid-rights-qemuarm64.rootfs.ext4.zst
```

Expected: two `PASS` lines and exit status zero. The test checks that the
synthetic helper is owned by `root:root`, has mode `4755`, and is accessible
to the non-root user. It also checks the fixture account, metadata and warning.

**Automatic runtime test (host).** QEMU and `zstd` must be installed on the
host. The runner boots a disposable guest, executes the benign identity
checks, and closes QEMU itself:

```bash
QEMU_HTTP_PORT=18080 \
  python3 scripts/test-dangerous-suid-rights.py --device router
```

Expected: `PASS router-cwe250-dangerous-suid-rights: ...` and exit status
zero. The console log path is printed in the result. To test all eleven
images after building them:

```bash
QEMU_HTTP_PORT=18080 QEMU_MQTT_PORT=21883 QEMU_MODBUS_PORT=11502 \
  python3 scripts/test-dangerous-suid-rights.py --all
```

On Apple Silicon, enable acceleration by adding `QEMU_ACCEL=hvf QEMU_CPU=host`
before the host runtime command, for example:

```bash
QEMU_ACCEL=hvf QEMU_CPU=host QEMU_HTTP_PORT=18080 \
  python3 scripts/test-dangerous-suid-rights.py --device router
```

**Manual test, step 1: boot on the host.** Run from the repository root:

```bash
QEMU_HTTP_PORT=18080 FIRMWARE=router-cwe250-dangerous-suid-rights \
  ./scripts/run-qemu.sh
```

On an Apple Silicon Mac, use this command instead:

```bash
QEMU_ACCEL=hvf QEMU_CPU=host QEMU_HTTP_PORT=18080 \
  FIRMWARE=router-cwe250-dangerous-suid-rights ./scripts/run-qemu.sh
```

Log into the QEMU serial console:

```text
login: root
password: routeradmin
```

Run the remaining commands **inside the guest**, separately from the
automatic host runner.

**Step 2: inspect ownership and permissions (guest).**

```bash
stat -c '%U:%G %a %A' /usr/bin/iotbench-suid-fixture
```

Expected:

```text
root:root 4755 -rwsr-xr-x
```

The leading `4` in `4755` enables SUID. The `s` in `-rwsr-xr-x` shows that
bit together with the owner's execute permission. The other-user `r-x`
permissions let the synthetic non-root user read and execute the helper.

**Step 3: run the helper as the unprivileged caller (guest).**

```bash
setpriv --reuid=993 --regid=993 --clear-groups \
  /usr/bin/iotbench-suid-fixture
```

Expected output includes:

```text
SUID_FIXTURE_ONLY=BENIGN_IDENTITY_REPORT
REAL_UID=993
EFFECTIVE_UID=0
REAL_GID=993
EFFECTIVE_GID=993
```

`setpriv` switches the caller to the unprivileged user before executing the
helper. `REAL_UID=993` proves that caller identity; `EFFECTIVE_UID=0` shows
that SUID makes the helper run with its root owner's effective UID. The
ordinary non-SUID `setpriv` utility is only the test harness. The group stays
993 because this helper has no SGID bit. Running the helper directly from
the root console would not demonstrate the non-root-to-root transition.

The helper only prints these values and exits. This test demonstrates the
unsafe permission configuration without supplying a shell or an exploitation
chain.

**Step 4 (optional): remove SUID and compare (guest).** From the guest root
console:

```bash
chmod 0755 /usr/bin/iotbench-suid-fixture

setpriv --reuid=993 --regid=993 --clear-groups \
  /usr/bin/iotbench-suid-fixture
```

Expected output now includes:

```text
REAL_UID=993
EFFECTIVE_UID=993
```

The same benign marker still prints. This shows that the helper does not
need root privileges. Quit QEMU with **Ctrl-A**, then **X**; the default
snapshot discards the permission change on exit. For a lasting fix, install
the helper with mode `0755` in its recipe and update the intentionally
vulnerable image's permission assertion before rebuilding.

Replace `router` in the build, static-test and runtime-test commands with
another device from the table. Use the same `YOCTO_MACHINE` for build and
boot when selecting another architecture. `qemuarm64` is the default.

All images reuse their normal device profile, install only
`cwe250-dangerous-suid-rights` as the vulnerability package, and export to
`deploy-images/<device>-cwe250-dangerous-suid-rights/<machine>/`.
`YOCTO_MACHINE` selects the architecture; `scripts/build-all.sh` discovers
these recipes. See [docs/luca-payloads.md](docs/luca-payloads.md#privilege-escalation-risk--dangerous-suid-rights-cwe-250)
for every device's paths, metadata, build instructions and verification.

### CoAP Server Communicating with Vulnerable Internal Files (CWE-862)

> INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT

All eleven device profiles have a separate read-only CoAP fixture. Its systemd
service listens on guest UDP port `5683` and exposes two fixed resources:

| CoAP resource | Predefined internal firmware file | Synthetic information |
| --- | --- | --- |
| `/device/config` | `/usr/share/iotbench/coap-internal-files/internal/device.conf` | Device class, fake asset reference, calibration and diagnostic configuration |
| `/maintenance/info` | `/usr/share/iotbench/coap-internal-files/internal/maintenance.dat` | Fake maintenance reference, service window and self-test state |

The handler opens the corresponding file and returns its exact bytes in a
`2.05 Content` response **without checking authorization**. These files are
marked internal-maintenance-only and have restrictive Unix permissions; their
contents should not be available to arbitrary CoAP clients. The missing
resource authorization is **CWE-862 — Missing Authorization**. No client input
is used as a filename, and requests cannot modify files or execute commands.
The daemon uses the existing pinned `libcoap` recipe and runs as a locked,
unprivileged `coapfixture` service account.

| Firmware id | CWE | Scenario |
| --- | --- | --- |
| `doorlock-cwe862-coap-internal-files` | CWE-862 | Unrestricted CoAP exposure of internal synthetic files |
| `envsensor-cwe862-coap-internal-files` | CWE-862 | Unrestricted CoAP exposure of internal synthetic files |
| `healthmonitor-cwe862-coap-internal-files` | CWE-862 | Unrestricted CoAP exposure of internal synthetic files |
| `ipcamera-cwe862-coap-internal-files` | CWE-862 | Unrestricted CoAP exposure of internal synthetic files |
| `plc-cwe862-coap-internal-files` | CWE-862 | Unrestricted CoAP exposure of internal synthetic files |
| `router-cwe862-coap-internal-files` | CWE-862 | Unrestricted CoAP exposure of internal synthetic files |
| `smartbulb-cwe862-coap-internal-files` | CWE-862 | Unrestricted CoAP exposure of internal synthetic files |
| `smarthub-cwe862-coap-internal-files` | CWE-862 | Unrestricted CoAP exposure of internal synthetic files |
| `smartplug-cwe862-coap-internal-files` | CWE-862 | Unrestricted CoAP exposure of internal synthetic files |
| `smartspeaker-cwe862-coap-internal-files` | CWE-862 | Unrestricted CoAP exposure of internal synthetic files |
| `thermostat-cwe862-coap-internal-files` | CWE-862 | Unrestricted CoAP exposure of internal synthetic files |

Build and boot from the host repository root:

~~~bash
FIRMWARE=router-cwe862-coap-internal-files docker compose run --rm yocto
FIRMWARE=router-cwe862-coap-internal-files ./scripts/run-qemu.sh
~~~

In a second host terminal, retrieve the files manually:

~~~bash
python3 scripts/test-coap-internal-files.py --port 5683 --get /device/config
python3 scripts/test-coap-internal-files.py --port 5683 --get /maintenance/info
~~~

Expected: `CoAP 2.05` followed by the internal file content, including
`COAP_INTERNAL_CONFIG_EXPOSED` or `COAP_INTERNAL_MAINTENANCE_EXPOSED`.
No credential is supplied. `QEMU_COAP_PORT` changes the loopback-only host UDP
port; pass the same value with the client's `--port` option. These resources
use CoAP/UDP and cannot be tested by opening an HTTP URL in a browser.

For protocol regression against that running image:

~~~bash
python3 scripts/test-coap-internal-files.py --device router
~~~

For an automatic disposable QEMU boot/test, run separately from manual QEMU:

~~~bash
python3 scripts/test-coap-internal-files.py --boot router
python3 scripts/test-coap-internal-files.py --all
~~~

Offline inspection uses the existing builder tools:

~~~bash
docker compose run --rm yocto python3 /scripts/test-coap-internal-files.py \
  --image /export/router-cwe862-coap-internal-files/qemuarm64/iotbench-router-cwe862-coap-internal-files-qemuarm64.rootfs.ext4.zst
~~~

Replace `router` with any device in the table. The existing architecture
selector, export paths and `scripts/build-all.sh` apply. Safe remediation is
to remove internal-file resources from the public interface, or authenticate
clients and authorize maintenance access before opening the files. See
[docs/luca-payloads.md](docs/luca-payloads.md#coap-server-communicating-with-vulnerable-internal-files-cwe-862)
for the source-to-response data flow and per-device procedures.

### MQTT Server Communicating with Vulnerable Internal Files (CWE-862)

> INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT

All eleven device profiles have separate firmware images that expose two
private synthetic files through a local Mosquitto broker. A small publisher
reads only the fixed files below and publishes their exact bytes as retained
MQTT messages. The public ACL intentionally grants anonymous read access to
both topics without maintenance authorization: **CWE-862 — Missing
Authorization**, with internal-information disclosure as the consequence.
Public writes are denied; no MQTT message can select a filesystem path.

| MQTT topic | Fixed internal firmware file | Synthetic information |
| --- | --- | --- |
| `device/config` | `/usr/share/iotbench/mqtt-internal-files/internal/device.conf` | Device class, fake asset reference, calibration profile and diagnostic mode |
| `maintenance/info` | `/usr/share/iotbench/mqtt-internal-files/internal/maintenance.dat` | Fake maintenance reference, service window and self-test state |

The vulnerable flow is **internal synthetic file → bounded file read →
`mosquitto_publish` → insufficiently restricted MQTT topic → anonymous
subscriber**. Files are root:mqttfixture `0640` inside `0750`, marked
internal-maintenance-only, and contain fixture data only. The unprivileged
publisher connects to guest-loopback TCP 1884; anonymous subscribers use guest
TCP 1883, forwarded only to host loopback. No external broker, MQTT credential,
command execution or arbitrary file read is introduced. Existing device
services remain available, and each image installs only
`cwe862-mqtt-internal-files` as its vulnerability package.

| Firmware id | CWE | Scenario |
| --- | --- | --- |
| `doorlock-cwe862-mqtt-internal-files` | CWE-862 | Anonymous MQTT exposure of internal synthetic files |
| `envsensor-cwe862-mqtt-internal-files` | CWE-862 | Anonymous MQTT exposure of internal synthetic files |
| `healthmonitor-cwe862-mqtt-internal-files` | CWE-862 | Anonymous MQTT exposure of internal synthetic files |
| `ipcamera-cwe862-mqtt-internal-files` | CWE-862 | Anonymous MQTT exposure of internal synthetic files |
| `plc-cwe862-mqtt-internal-files` | CWE-862 | Anonymous MQTT exposure of internal synthetic files |
| `router-cwe862-mqtt-internal-files` | CWE-862 | Anonymous MQTT exposure of internal synthetic files |
| `smartbulb-cwe862-mqtt-internal-files` | CWE-862 | Anonymous MQTT exposure of internal synthetic files |
| `smarthub-cwe862-mqtt-internal-files` | CWE-862 | Anonymous MQTT exposure of internal synthetic files |
| `smartplug-cwe862-mqtt-internal-files` | CWE-862 | Anonymous MQTT exposure of internal synthetic files |
| `smartspeaker-cwe862-mqtt-internal-files` | CWE-862 | Anonymous MQTT exposure of internal synthetic files |
| `thermostat-cwe862-mqtt-internal-files` | CWE-862 | Anonymous MQTT exposure of internal synthetic files |

Build and boot from the host repository root:

~~~bash
FIRMWARE=router-cwe862-mqtt-internal-files docker compose run --rm yocto
FIRMWARE=router-cwe862-mqtt-internal-files ./scripts/run-qemu.sh
~~~

In a second host terminal, fetch the predefined topics anonymously:

~~~bash
python3 scripts/test-mqtt-internal-files.py --get device/config
python3 scripts/test-mqtt-internal-files.py --get maintenance/info
python3 scripts/test-mqtt-internal-files.py --device router
~~~

Expected: exact internal config and maintenance content, including
`MQTT_INTERNAL_CONFIG_EXPOSED`, `device_class=router` and
`MQTT_INTERNAL_MAINTENANCE_EXPOSED`. `QEMU_MQTT_PORT` changes the host-loopback
TCP port; pass the matching client `--port`. Substitute any listed device.
For automated disposable QEMU checks, separately from manual QEMU:

~~~bash
python3 scripts/test-mqtt-internal-files.py --boot router
python3 scripts/test-mqtt-internal-files.py --all
~~~

Offline inspection uses the existing builder tools:

~~~bash
docker compose run --rm yocto python3 /scripts/test-mqtt-internal-files.py \
  --image /export/router-cwe862-mqtt-internal-files/qemuarm64/iotbench-router-cwe862-mqtt-internal-files-qemuarm64.rootfs.ext4.zst
~~~

Build all eleven by iterating `iotbench-*-cwe862-mqtt-internal-files.bb` as
shown in [docs/luca-payloads.md](docs/luca-payloads.md#mqtt-server-communicating-with-vulnerable-internal-files-cwe-862).
The existing architecture selector, export paths and `scripts/build-all.sh`
apply. Safe remediation removes the anonymous internal-topic grants or limits
access to authenticated, authorized maintenance subscribers. The payload guide
contains broker/ACL/service paths, concrete file-to-publish flow, expected
static findings and a section for each firmware.

### Vulnerable Bash Files — Path Traversal (CWE-22)

> INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT

All eleven device profiles have a separate local Bash path-traversal fixture.
The installed `/usr/bin/iotbench-bash-read` expects a filename relative to
`/usr/share/iotbench/bash-path-traversal/data/`, concatenates `$1` with that fixed directory,
and reads the result using Bash's `read` builtin and a quoted redirection.
It intentionally performs no path normalization or boundary validation.
`../internal/private-fixture.txt` therefore reads the synthetic internal marker
`SYNTHETIC_INTERNAL_FIXTURE_DATA` outside the intended `data/` directory.

A fixed Bash loadable builtin first confines the process to a synthetic-only
jail and drops privileges. It receives no path input and does not enforce the
`data/` boundary. No external or host file is reachable, even through deep
traversal. The vulnerability is in the Bash helper; the small C shared object
only implements process containment and has no standalone executable entry.
The fixture adds no network service, sudo rule, SUID, credentials or command
execution. Existing device services and peripherals come from their profiles.

| Firmware id | CWE | Scenario |
| --- | --- | --- |
| `doorlock-cwe022-bash-path-traversal` | CWE-22 | Local Bash helper path traversal |
| `envsensor-cwe022-bash-path-traversal` | CWE-22 | Local Bash helper path traversal |
| `healthmonitor-cwe022-bash-path-traversal` | CWE-22 | Local Bash helper path traversal |
| `ipcamera-cwe022-bash-path-traversal` | CWE-22 | Local Bash helper path traversal |
| `plc-cwe022-bash-path-traversal` | CWE-22 | Local Bash helper path traversal |
| `router-cwe022-bash-path-traversal` | CWE-22 | Local Bash helper path traversal |
| `smartbulb-cwe022-bash-path-traversal` | CWE-22 | Local Bash helper path traversal |
| `smarthub-cwe022-bash-path-traversal` | CWE-22 | Local Bash helper path traversal |
| `smartplug-cwe022-bash-path-traversal` | CWE-22 | Local Bash helper path traversal |
| `smartspeaker-cwe022-bash-path-traversal` | CWE-22 | Local Bash helper path traversal |
| `thermostat-cwe022-bash-path-traversal` | CWE-22 | Local Bash helper path traversal |

Build and boot from the host repository root:

~~~bash
FIRMWARE=router-cwe022-bash-path-traversal docker compose run --rm yocto
FIRMWARE=router-cwe022-bash-path-traversal ./scripts/run-qemu.sh
~~~

Log into the guest serial console with the existing `root` / `routeradmin`
lab login, then run **inside the guest**:

~~~bash
iotbench-bash-read public.txt
iotbench-bash-read '../internal/private-fixture.txt'
sh /usr/share/iotbench/bash-path-traversal/test-guest.sh router
~~~

Expected: public marker, then `SYNTHETIC_INTERNAL_FIXTURE_DATA`, then five
regression `PASS` lines, each with status zero. Only the helper's own process
is confined; it starts from the guest root test console and drops to UID/GID
990 before reading. There is no privilege grant to unprivileged callers.

Automatic disposable QEMU testing (separate from manually running QEMU):

~~~bash
python3 scripts/test-bash-path-traversal.py --device router
python3 scripts/test-bash-path-traversal.py --all
~~~

Offline verification with the existing builder tools:

~~~bash
docker compose run --rm yocto python3 /scripts/test-bash-path-traversal.py \
  --image /export/router-cwe022-bash-path-traversal/qemuarm64/iotbench-router-cwe022-bash-path-traversal-qemuarm64.rootfs.ext4.zst
~~~

Build all eleven (default `qemuarm64`):

~~~bash
for recipe in meta-iotbench/recipes-images/iotbench-*-cwe022-bash-path-traversal.bb; do
    firmware=$(basename "$recipe" .bb)
    FIRMWARE="${firmware#iotbench-}" docker compose run --rm yocto || exit 1
done
~~~

`YOCTO_MACHINE` selects the existing supported architectures;
`scripts/build-all.sh` discovers these recipes automatically. Exports go to
`deploy-images/<device>-cwe022-bash-path-traversal/<machine>/`. Each image
installs only `cwe022-bash-path-traversal` as its vulnerability package.
The exact ground-truth label is **Vulnerable Bash files — Path Traversal**.
See [docs/luca-payloads.md](docs/luca-payloads.md#vulnerable-bash-files--path-traversal-cwe-22)
for filesystem mappings, per-device data flows, remediation and local tests.

### Vulnerable Java JARs — SQL Injection (CWE-89)

> INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT

All eleven profiles have a separate Java firmware fixture. Its executable JAR
accepts one local record name, directly concatenates it into a SELECT without
parameter binding or escaping, and executes it with JDBC `Statement.executeQuery()`.
The fixed SQLite database opens in read-only mode and contains only synthetic
public/internal records. A public-visibility filter makes input `internal`
return no rows; `public` returns only the public row. Input
`public' OR '1'='1` bypasses the filter and returns both rows. The same Java
lookup serves the CLI and the dashboard's **Configuration Lookup** panel.
The vulnerable flow is compiled into the JAR.

| Firmware id | CWE | Scenario |
| --- | --- | --- |
| `doorlock-cwe089-java-sql-injection` | CWE-89 | Java JAR synthetic SQLite JDBC lookup SQL injection |
| `envsensor-cwe089-java-sql-injection` | CWE-89 | Java JAR synthetic SQLite JDBC lookup SQL injection |
| `healthmonitor-cwe089-java-sql-injection` | CWE-89 | Java JAR synthetic SQLite JDBC lookup SQL injection |
| `ipcamera-cwe089-java-sql-injection` | CWE-89 | Java JAR synthetic SQLite JDBC lookup SQL injection |
| `plc-cwe089-java-sql-injection` | CWE-89 | Java JAR synthetic SQLite JDBC lookup SQL injection |
| `router-cwe089-java-sql-injection` | CWE-89 | Java JAR synthetic SQLite JDBC lookup SQL injection |
| `smartbulb-cwe089-java-sql-injection` | CWE-89 | Java JAR synthetic SQLite JDBC lookup SQL injection |
| `smarthub-cwe089-java-sql-injection` | CWE-89 | Java JAR synthetic SQLite JDBC lookup SQL injection |
| `smartplug-cwe089-java-sql-injection` | CWE-89 | Java JAR synthetic SQLite JDBC lookup SQL injection |
| `smartspeaker-cwe089-java-sql-injection` | CWE-89 | Java JAR synthetic SQLite JDBC lookup SQL injection |
| `thermostat-cwe089-java-sql-injection` | CWE-89 | Java JAR synthetic SQLite JDBC lookup SQL injection |

#### Manual browser test

This models a public configuration-search function backed by a Java firmware
service. Internal records should not be returned by the search. A separate
unprivileged Java process in the same JAR handles requests on guest loopback;
the existing dashboard forwards the input to it. PHP performs no SQL or shell
execution, and Lighttpd retains its sandbox.

Build the updated firmware and boot it from the host repository root:

```bash
FIRMWARE=router-cwe089-java-sql-injection docker compose run --rm yocto
QEMU_ACCEL=hvf QEMU_CPU=host QEMU_HTTP_PORT=18080 \
  FIRMWARE=router-cwe089-java-sql-injection ./scripts/run-qemu.sh
```

The boot command above uses Apple Silicon acceleration. On other hosts, omit
`QEMU_ACCEL=hvf QEMU_CPU=host`. Existing older exports must be rebuilt to include
the web panel and service. On a fresh builder, first run `docker compose build yocto`.

Open **http://127.0.0.1:18080** in the host browser and find **Configuration Lookup**.
Enter each value in **Record name**, then click **Search configuration**:

| Input | Expected result |
| --- | --- |
| `public` | `public\|SYNTHETIC_PUBLIC_FIXTURE_DATA` |
| `internal` | No public configuration found; no records |
| `public' OR '1'='1` | Both `public\|SYNTHETIC_PUBLIC_FIXTURE_DATA` and `internal\|SYNTHETIC_INTERNAL_FIXTURE_DATA` |

Enter the injection exactly as shown, without surrounding double quotes: those
quotes are needed only for shell commands. The internal row appearing only
after SQL injection demonstrates a bypass of the Java query's visibility
filter. These remain synthetic records in a read-only database.

The browser uses the existing dashboard request-token checks. Results are
rendered as text by the existing UI. The Java backend binds only to guest
`127.0.0.1:18089`, runs as `javafixture`, and has no separate host port forward.

#### Manual Java CLI test

**1. Build on the host, if needed.** Run from the repository root. Skip this
step if the selected firmware has already been exported. Rebuild the builder
once to add the pinned `meta-openjdk` layer, then build the firmware:

```bash
docker compose build yocto
FIRMWARE=router-cwe089-java-sql-injection docker compose run --rm yocto
```

**2. Boot on the host.** QEMU and `zstd` must be installed on the host:

```bash
FIRMWARE=router-cwe089-java-sql-injection ./scripts/run-qemu.sh
```

On an Apple Silicon Mac, use this accelerated command instead:

```bash
QEMU_ACCEL=hvf QEMU_CPU=host QEMU_HTTP_PORT=18080 \
  FIRMWARE=router-cwe089-java-sql-injection ./scripts/run-qemu.sh
```

**3. Log into the guest serial console.** In the same terminal, wait for
`qemuarm64 login:` and enter:

```text
login: root
password: routeradmin
```

Run the remaining commands **inside the guest**, at `root@qemuarm64:~#`.
These CLI checks exercise the same Java lookup operation used by the web panel.

**4. Run the normal lookup (guest):**

```sh
java -Xmx32m -jar /usr/share/iotbench/java-sql-injection/fixture-db-query.jar public
echo "exit=$?"
```

Expected stdout:

```text
public|SYNTHETIC_PUBLIC_FIXTURE_DATA
exit=0
```

Only the public record must appear. Each invocation also prints the fixture
warning to stderr, so this line appears above the result in the console:

```text
INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT
```

Also verify that a direct internal-record lookup returns no rows:

```sh
java -Xmx32m -jar /usr/share/iotbench/java-sql-injection/fixture-db-query.jar internal
echo "exit=$?"
```

Expected: only the warning on stderr, no record output, and `exit=0`.

**5. Run the SQL injection lookup (guest).** Keep the double quotes around
the entire argument so its spaces and single quotes reach Java intact:

```sh
java -Xmx32m -jar /usr/share/iotbench/java-sql-injection/fixture-db-query.jar "public' OR '1'='1"
echo "exit=$?"
```

Expected stdout, in this order:

```text
public|SYNTHETIC_PUBLIC_FIXTURE_DATA
internal|SYNTHETIC_INTERNAL_FIXTURE_DATA
exit=0
```

The extra internal record demonstrates the vulnerability: concatenation
changes the SQL predicate to
`visibility = 'public' AND record_name = 'public' OR '1'='1'`, matching both
synthetic rows and bypassing the public-record filter. The database remains read-only.

**6. Verify execution without root privileges (optional, guest):**

```sh
setpriv --reuid=65534 --regid=65534 --clear-groups \
  java -Xmx32m -jar /usr/share/iotbench/java-sql-injection/fixture-db-query.jar "public' OR '1'='1"
echo "exit=$?"
```

Expected: the same two record lines and `exit=0`, plus the fixture warning.

**7. Run the full guest regression (optional):**

```sh
sh /usr/share/iotbench/java-sql-injection/test-guest.sh router
echo "exit=$?"
```

Expected: five `PASS` lines and `exit=0`. The regression runs Java as UID/GID
65534 and checks normal/injected output, argument handling, unchanged database
bytes and absence of journal sidecars. Warnings and lookup errors from deliberate
negative cases are expected.

**8. Close QEMU.** Press **Ctrl-A**, release the keys, then press **X**.
The default disposable snapshot discards guest writes on exit.

For another device, replace `router` in the firmware ID and regression argument
with any device from the table above. The JAR path, payloads and expected
records are identical. Use the same `YOCTO_MACHINE` when building and booting
another architecture; the default is `qemuarm64`.

For automatic disposable boots, run
`python3 scripts/test-java-sql-injection.py --all` on the host separately from
manual QEMU. It checks both CLI and dashboard HTTP behavior, including direct
internal-record denial, SQL injection, CSRF, the Java service identity and
Lighttpd's retained sandbox.

Each image installs only `cwe089-java-sql-injection` as its vulnerability
package, plus the cross-built OpenJDK runtime and pinned SQLite JDBC dependency.
The initial Java build requires extra downloads and compilation. Existing
`YOCTO_MACHINE`, export paths and catalog-wide build discovery apply.
See [docs/java-sql-injection.md](docs/java-sql-injection.md) for the exact Java
source/sink, dependency pins, filesystem layout, schema, batch builds, offline
and local tests, validation status and remediation.

### Vulnerable C Binaries — SQL injection (CWE-89)

> INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT

All eleven profiles have a separate `<device>-cwe089-c-sql-injection` image.
The native `/usr/bin/fixture-db-query` executable interpolates its first argument
into a SELECT query with `snprintf()`, without SQL parameter binding or escaping,
then calls `sqlite3_prepare_v2()` and `sqlite3_step()`. The fixed SQLite database
contains only two synthetic records and is opened with `SQLITE_OPEN_READONLY`.
Normal input `public` returns only the public marker; `public' OR '1'='1`
returns both public and internal markers. The vulnerability is entirely in C.

| Firmware id | CWE | Scenario |
| --- | --- | --- |
| `doorlock-cwe089-c-sql-injection` | CWE-89 | Native C synthetic SQLite lookup SQL injection |
| `envsensor-cwe089-c-sql-injection` | CWE-89 | Native C synthetic SQLite lookup SQL injection |
| `healthmonitor-cwe089-c-sql-injection` | CWE-89 | Native C synthetic SQLite lookup SQL injection |
| `ipcamera-cwe089-c-sql-injection` | CWE-89 | Native C synthetic SQLite lookup SQL injection |
| `plc-cwe089-c-sql-injection` | CWE-89 | Native C synthetic SQLite lookup SQL injection |
| `router-cwe089-c-sql-injection` | CWE-89 | Native C synthetic SQLite lookup SQL injection |
| `smartbulb-cwe089-c-sql-injection` | CWE-89 | Native C synthetic SQLite lookup SQL injection |
| `smarthub-cwe089-c-sql-injection` | CWE-89 | Native C synthetic SQLite lookup SQL injection |
| `smartplug-cwe089-c-sql-injection` | CWE-89 | Native C synthetic SQLite lookup SQL injection |
| `smartspeaker-cwe089-c-sql-injection` | CWE-89 | Native C synthetic SQLite lookup SQL injection |
| `thermostat-cwe089-c-sql-injection` | CWE-89 | Native C synthetic SQLite lookup SQL injection |

#### Manual SQL injection test

**1. Build on the host.** Run from the repository root. If this image has
already been exported, continue with step 2. The default target is `qemuarm64`.

~~~bash
FIRMWARE=router-cwe089-c-sql-injection docker compose run --rm yocto
~~~

**2. Boot on the host.** QEMU and `zstd` must be installed on the host:

~~~bash
FIRMWARE=router-cwe089-c-sql-injection ./scripts/run-qemu.sh
~~~

On an Apple Silicon Mac, use this accelerated command instead. Port `18080`
is the host port for the existing dashboard:

~~~bash
QEMU_ACCEL=hvf QEMU_CPU=host QEMU_HTTP_PORT=18080 \
  FIRMWARE=router-cwe089-c-sql-injection ./scripts/run-qemu.sh
~~~

**3. Log into the guest serial console.** Wait for `qemuarm64 login:` in the
same terminal and enter the existing lab credentials:

~~~text
login: root
password: routeradmin
~~~

Run the following steps at the guest prompt, `root@qemuarm64:~#`.
The SQL lookup is a local firmware CLI test; no browser or HTTP request is needed.

**4. Check the installed executable and database (guest):**

~~~sh
stat -c '%u:%g:%a' /usr/bin/fixture-db-query
stat -c '%u:%g:%a' /usr/share/iotbench/c-sql-injection/fixture.db
~~~

Expected output, respectively:

~~~text
0:0:755
0:0:444
~~~

**5. Run the normal lookup (guest):**

~~~sh
fixture-db-query public
echo "exit=$?"
~~~

Expected stdout:

~~~text
public|SYNTHETIC_PUBLIC_FIXTURE_DATA
exit=0
~~~

The internal record must not appear. Each helper invocation also prints the
fixture warning to stderr, so it appears above the result in the console:

~~~text
INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT
~~~

**6. Run the SQL injection lookup (guest).** Keep the double quotes around
the entire argument so its spaces and single quotes reach the C binary intact:

~~~sh
fixture-db-query "public' OR '1'='1"
echo "exit=$?"
~~~

Expected stdout, in this order:

~~~text
public|SYNTHETIC_PUBLIC_FIXTURE_DATA
internal|SYNTHETIC_INTERNAL_FIXTURE_DATA
exit=0
~~~

The extra internal marker demonstrates the vulnerability: the argument changes
the WHERE condition to `record_name = 'public' OR '1'='1'`, matching both
synthetic rows. The database remains read-only.

**7. Verify the same behavior without root privileges (guest):**

~~~sh
setpriv --reuid=65534 --regid=65534 --clear-groups \
  /usr/bin/fixture-db-query "public' OR '1'='1"
echo "exit=$?"
~~~

Expected: the same two record lines and `exit=0`, plus the fixture warning.
The helper has ordinary permissions and needs no SUID or sudo grant.

**8. Run the full guest regression (optional):**

~~~sh
sh /usr/share/iotbench/c-sql-injection/test-guest.sh router
echo "exit=$?"
~~~

Expected: six `PASS` lines and `exit=0`. The regression runs all lookups as
UID/GID 65534, compares exact normal/injection results, checks malformed and
oversized inputs, and verifies unchanged database contents with no journal
sidecars. Warning lines and lookup-failure messages for deliberate negative
cases are expected; the six `PASS` lines and final exit status determine success.

**9. Close QEMU.** Press **Ctrl-A**, release the keys, then press **X**.
The default disposable snapshot discards guest writes on exit.

For another device, replace `router` in the firmware ID and the regression's
device argument with any device from the table above. The lookup executable,
payloads, database path and expected record output are identical. Use the same
`YOCTO_MACHINE` when building and booting a different target architecture.

#### Automated SQL injection tests and batch builds

For automated disposable boots, separately from manual QEMU:

~~~bash
python3 scripts/test-c-sql-injection.py --device router
python3 scripts/test-c-sql-injection.py --all
# Apple Silicon acceleration and alternative existing service ports:
QEMU_ACCEL=hvf QEMU_CPU=host QEMU_HTTP_PORT=18080 \
  QEMU_MQTT_PORT=21883 QEMU_MODBUS_PORT=11502 \
  python3 scripts/test-c-sql-injection.py --all
~~~

Build all eleven with the existing builder and export convention:

~~~bash
for recipe in meta-iotbench/recipes-images/iotbench-*-cwe089-c-sql-injection.bb; do
    firmware=$(basename "$recipe" .bb)
    FIRMWARE="${firmware#iotbench-}" docker compose run --rm yocto || exit 1
done
~~~

`YOCTO_MACHINE` selects the existing architecture/toolchain; default `qemuarm64`.
Exports are under `deploy-images/<device>-cwe089-c-sql-injection/<machine>/`;
`scripts/build-all.sh` discovers the recipes automatically. Each image installs
only `cwe089-c-sql-injection` as its vulnerability package and retains the
existing device profile and peripherals. SQLite is supplied by the pinned
OpenEmbedded core layer; no additional layer or target SQLite CLI is needed.
See [docs/luca-payloads.md](docs/luca-payloads.md#vulnerable-c-binaries--sql-injection-cwe-89)
for per-device sources, schema, exact flow, offline tests and remediation.

### Vulnerable C Binaries — Null Pointer Dereference (CWE-476)

> INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT

Every device has a separate local native C fixture. `/usr/bin/fixture-device-info`
looks up `argv[1]` in two compiled synthetic records. `public` and `status` return
valid pointers; `missing-record` returns `NULL`. The caller deliberately omits
NULL validation before accessing `record->id`. This input-dependent lookup and
unchecked member load are the sole intended weakness. The helper reads no files,
executes no commands, uses no network and needs no privileges.

| Firmware id | CWE | Scenario |
| --- | --- | --- |
| `doorlock-cwe476-null-pointer-dereference` | CWE-476 | Native C nullable record lookup and unchecked dereference |
| `envsensor-cwe476-null-pointer-dereference` | CWE-476 | Native C nullable record lookup and unchecked dereference |
| `healthmonitor-cwe476-null-pointer-dereference` | CWE-476 | Native C nullable record lookup and unchecked dereference |
| `ipcamera-cwe476-null-pointer-dereference` | CWE-476 | Native C nullable record lookup and unchecked dereference |
| `plc-cwe476-null-pointer-dereference` | CWE-476 | Native C nullable record lookup and unchecked dereference |
| `router-cwe476-null-pointer-dereference` | CWE-476 | Native C nullable record lookup and unchecked dereference |
| `smartbulb-cwe476-null-pointer-dereference` | CWE-476 | Native C nullable record lookup and unchecked dereference |
| `smarthub-cwe476-null-pointer-dereference` | CWE-476 | Native C nullable record lookup and unchecked dereference |
| `smartplug-cwe476-null-pointer-dereference` | CWE-476 | Native C nullable record lookup and unchecked dereference |
| `smartspeaker-cwe476-null-pointer-dereference` | CWE-476 | Native C nullable record lookup and unchecked dereference |
| `thermostat-cwe476-null-pointer-dereference` | CWE-476 | Native C nullable record lookup and unchecked dereference |

Build and run static verification from the repository root:

~~~bash
docker compose run --rm yocto python3 /scripts/test-null-pointer-dereference.py --static
FIRMWARE=router-cwe476-null-pointer-dereference docker compose run --rm yocto
~~~

The static check requires GCC's interprocedural analyzer to report CWE-476 on
the exact input → lookup → NULL return → unchecked `record->id` path. A temporary
corrected control must have no CWE-476 diagnostic. The firmware remains vulnerable.

Inspect an exported image without executing it:

~~~bash
docker compose run --rm yocto python3 /scripts/test-null-pointer-dereference.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/router-cwe476-null-pointer-dereference/qemuarm64/iotbench-router-cwe476-null-pointer-dereference-qemuarm64.rootfs.ext4.zst
~~~

The `debugfs` path is for an aarch64 builder host; use its `x86_64` counterpart
on an x86_64 builder. `--machine` selects the expected ELF target;
`--objdump` accepts the corresponding cross-objdump for other targets.
Optional isolated runtime validation, separately from a manually running guest:

~~~bash
python3 scripts/test-null-pointer-dereference.py --device router
python3 scripts/test-null-pointer-dereference.py --all
~~~

The runner uses disposable QEMU snapshots and stores each console log beside
the image. Guest tests run the helper without privileges, verify valid output
and argument handling, then use a separate Linux diagnostic supervisor to
confirm the kernel's SIGSEGV fault address is zero and the child terminates by
SIGSEGV. Core dumps are disabled and each subprocess has a timeout. Source
analysis and ELF inspection provide independent evidence beyond the crash.

All images retain their existing device profile and install only
`cwe476-null-pointer-dereference` as the vulnerability package. Exports go to
`deploy-images/<device>-cwe476-null-pointer-dereference/<machine>/`.
`YOCTO_MACHINE` selects the architecture and `scripts/build-all.sh` discovers
the recipes. See [docs/luca-payloads.md](docs/luca-payloads.md#vulnerable-c-binaries--null-pointer-dereference-cwe-476)
for each device, exact source locations, remediation and validation results.

### Vulnerable C Binaries — Integer Overflow (CWE-190)

> INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT

Each device has a separate `<device>-cwe190-integer-overflow` image containing
`/usr/bin/fixture-batch-size`, compiled from its matching C source with the
existing Yocto target toolchain. The utility parses one decimal record count
as `uint32_t`, multiplies by a fixed 1024-byte record size without checking
arithmetic bounds, and compares the wrapped total with a synthetic 4096-byte
capacity. Input `2` yields 2048 and is accepted; `4194304` has mathematical
total 4294967296, wraps to 0, and is incorrectly accepted. The wrapped value
is used only for reporting and this simulated decision.

| Firmware id | CWE | Scenario |
| --- | --- | --- |
| `doorlock-cwe190-integer-overflow` | CWE-190 | Native C unchecked uint32_t batch-size multiplication |
| `envsensor-cwe190-integer-overflow` | CWE-190 | Native C unchecked uint32_t batch-size multiplication |
| `healthmonitor-cwe190-integer-overflow` | CWE-190 | Native C unchecked uint32_t batch-size multiplication |
| `ipcamera-cwe190-integer-overflow` | CWE-190 | Native C unchecked uint32_t batch-size multiplication |
| `plc-cwe190-integer-overflow` | CWE-190 | Native C unchecked uint32_t batch-size multiplication |
| `router-cwe190-integer-overflow` | CWE-190 | Native C unchecked uint32_t batch-size multiplication |
| `smartbulb-cwe190-integer-overflow` | CWE-190 | Native C unchecked uint32_t batch-size multiplication |
| `smarthub-cwe190-integer-overflow` | CWE-190 | Native C unchecked uint32_t batch-size multiplication |
| `smartplug-cwe190-integer-overflow` | CWE-190 | Native C unchecked uint32_t batch-size multiplication |
| `smartspeaker-cwe190-integer-overflow` | CWE-190 | Native C unchecked uint32_t batch-size multiplication |
| `thermostat-cwe190-integer-overflow` | CWE-190 | Native C unchecked uint32_t batch-size multiplication |

#### Manual integer-overflow test

This fixture is tested in the **QEMU guest serial console**. The web dashboard
shown at the forwarded HTTP address has no panel for this local C utility.

**1. Build on the host, if needed.** Run from the repository root. Skip this
command if the firmware has already been exported:

~~~bash
FIRMWARE=router-cwe190-integer-overflow docker compose run --rm yocto
~~~

**2. Boot on the host.** QEMU and `zstd` must be installed:

~~~bash
FIRMWARE=router-cwe190-integer-overflow ./scripts/run-qemu.sh
~~~

On an Apple Silicon Mac, use this accelerated command instead:

~~~bash
QEMU_ACCEL=hvf QEMU_CPU=host QEMU_HTTP_PORT=18080 \
FIRMWARE=router-cwe190-integer-overflow ./scripts/run-qemu.sh
~~~

**3. Log into the guest.** In the same terminal, wait for `qemuarm64 login:`
and enter the existing lab credentials:

~~~text
login: root
password: routeradmin
~~~

Run the remaining commands **inside the guest**, at `root@qemuarm64:~#`.

**4. Test normal arithmetic:**

~~~sh
fixture-batch-size 2
echo "exit=$?"
~~~

Expected stdout:

~~~text
record_count = 2
record_size = 1024
total_size = 2048
max_capacity = 4096
Synthetic batch accepted
exit=0
~~~

Every invocation also prints the intentional-fixture warning to stderr.

**5. Trigger integer overflow:**

~~~sh
fixture-batch-size 4194304
echo "exit=$?"
~~~

Expected stdout:

~~~text
record_count = 4194304
record_size = 1024
total_size = 0
max_capacity = 4096
Synthetic batch accepted
exit=0
~~~

The correct mathematical total is `4194304 * 1024 = 4294967296`, which exceeds
`UINT32_MAX` (`4294967295`). Unchecked unsigned multiplication wraps to zero,
so the simulated capacity decision incorrectly accepts the batch. The exact
wrong total and decision demonstrate CWE-190; the program terminates normally.

**6. Check ordinary capacity rejection and malformed input:**

~~~sh
fixture-batch-size 5
echo "exit=$?"
fixture-batch-size abc
echo "exit=$?"
~~~

Input `5` prints `total_size = 5120`, `Synthetic batch exceeds capacity` and
`exit=0`: capacity rejection is a valid calculation. Input `abc` prints usage
to stderr, no numerical result, and `exit=2`. A value outside the input type's
range, such as `4294967296`, also returns 2. The valid overflow witness
`4194304` passes input conversion and reaches the unchecked multiplication.

**7. Run the complete guest regression (optional):**

~~~sh
sh /usr/share/iotbench/integer-overflow/test-guest.sh router
echo "exit=$?"
~~~

The regression checks exact numerical results and decisions, parsing and range
errors, arithmetic boundaries and execution as UID/GID 65534 with cleared
groups. Expected: six `PASS` lines and `exit=0`.

**8. Close QEMU.** Press **Ctrl-A**, release the keys, then press **X**.
The default disposable snapshot discards guest writes on exit.

For another device, replace `router` in the firmware ID and the regression's
device argument with a device from the table above. The executable, inputs
and expected numerical output are identical. Use the same `YOCTO_MACHINE`
when building and booting another target architecture.

#### Automated integer-overflow checks

Run these commands on the host, separately from a manually running QEMU guest:

~~~bash
python3 scripts/test-integer-overflow.py --device router
python3 scripts/test-integer-overflow.py --all
python3 scripts/test-integer-overflow.py --local --sanitize
~~~

The last command builds a separate host test executable and requires Clang's
unsigned-overflow diagnostic at the exact multiplication plus a clean corrected
temporary control. The installed firmware remains vulnerable and uninstrumented.
Every image installs only `cwe190-integer-overflow` as its vulnerability package,
retaining the existing device profile, native services and simulator.
`YOCTO_MACHINE` selects the existing architecture; exports land under
`deploy-images/<device>-cwe190-integer-overflow/<machine>/`.
`scripts/build-all.sh` discovers all eleven recipes automatically.
See [docs/luca-payloads.md](docs/luca-payloads.md#vulnerable-c-binaries--integer-overflow-cwe-190)
for per-device sources, exact flow, batch builds, offline ELF checks, remediation
and completed verification results.

### Device taxonomy

The five categories are chosen to span the device classes and protocols found in
published IoT device datasets and taxonomies, across consumer and industrial
(OT) domains: network gateway (HTTP), surveillance camera (MJPEG/RTSP), energy
management / smart plug (MQTT), climate control / thermostat (MQTT), and
industrial PLC gateway (Modbus). Reference taxonomies/datasets:

- Sivanathan et al., "Classifying IoT Devices in Smart Environments Using
  Network Traffic Characteristics", *IEEE TMC* 2019 (UNSW IoT dataset, ~28
  devices: cameras, hubs, energy, appliances, sensors, bulbs…).
- Alrawi et al., "SoK: Security Evaluation of Home-Based IoT Deployments",
  *IEEE S&P* 2019 (YourThings, 45 devices).
- Ren et al., "Information Exposure From Consumer IoT Devices", *IMC* 2019
  (Mon(IoT)r, 81 devices).

The roster spans the main consumer classes of those datasets — camera, hub,
energy/plug, lighting, environmental sensor, audio/speaker, health monitor,
access/lock, climate — plus network infrastructure and an industrial (OT)
gateway, giving cross-domain coverage with protocol diversity (HTTP, MJPEG,
MQTT, Modbus).

## Architectures

Any firmware builds for several architectures; the architecture is a build-time
selector (`YOCTO_MACHINE`), not a separate recipe. Supported machines:

| `YOCTO_MACHINE` | Arch | QEMU |
| --- | --- | --- |
| `qemuarm64` (default) | aarch64 | `qemu-system-aarch64` |
| `qemuarm` | ARM 32-bit | `qemu-system-arm` |
| `qemux86-64` | x86-64 | `qemu-system-x86_64` |
| `qemux86` | x86 32-bit | `qemu-system-i386` |
| `qemumips` | MIPS (BE) | `qemu-system-mips` |

Build for an architecture with `YOCTO_MACHINE=<machine>`; artifacts land in
`deploy-images/<firmware>/<machine>/`. `run-qemu.sh` reads the same
`YOCTO_MACHINE` and picks the right QEMU binary, machine and console. Only
`qemuarm64` sstate is cached initially, so the first build of another arch is
slow (fresh toolchain); later builds reuse that arch's sstate.

## Adding a firmware

See [docs/adding-a-firmware.md](docs/adding-a-firmware.md) for the full developer
guide (module API, non-web vulnerabilities, build/test loop, checklist). In
short:

1. Create the vulnerability module under
   `meta-iotbench/recipes-vulns/cwe<NNN>-<slug>/`:
   - `cwe<NNN>-<slug>_1.0.bb` builds/installs the vulnerable code and, for a web
     vulnerability, installs a dashboard module to
     `${datadir}/router-dashboard/modules/<id>/module.php`;
   - a web module calls `dashboard_register_module()` with a `render` panel and
     named `actions`. The core dashboard discovers it automatically — no change
     to the platform recipes. Panels use `<form class="module-form"
     data-action="...">` with an optional `<pre class="module-output">`; the core
     `app.js` posts the form and shows the result.
2. Add `recipes-images/iotbench-<device>-cwe<NNN>-<slug>.bb`, combining a device
   profile with the vulnerability:

   ```bitbake
   require recipes-images/iotbench-image.inc
   require recipes-devices/<device>/device-<device>.inc
   SUMMARY = "IoTBench target - <device>, CWE-<NNN> ..."
   IOTBENCH_CWE = "CWE-<NNN>"
   IOTBENCH_VULN_INSTALL = "cwe<NNN>-<slug>"
   ```

A new device type adds `recipes-devices/<device>/` (skeleton app +
`peripherals.conf` + `device-<device>.inc`); see the `router` device as the
template. Not every CWE is web-based: a module may instead ship a network daemon
or a setuid binary. The image recipe only decides which packages are installed.

## Builder and cache

| Part | Location | Contents |
| --- | --- | --- |
| image `yocto-builder:6.0.3` | `/opt/yocto` | tools, BitBake and pinned layers |
| volume `yocto-cache` | `/cache` | `downloads/`, `sstate-cache/`, `hashserv/` |
| volume `yocto-build` | `/workdir` | build directory, safe to delete |

The image contains no firmware layer and no build output, so it can be pushed to
a registry. The IoTBench layer is mounted at runtime and enabled via
`YOCTO_LAYERS`. Because all firmwares share the base, the `sstate-cache` makes
every firmware after the first build quickly.

What the cache can reuse:

- `downloads/`: sources, valid for any machine, image and host;
- `sstate-cache/`: task outputs, reused by every image sharing those tasks.
  `-native` tools depend on the host architecture (arm64 on Apple Silicon,
  amd64 on most Windows PCs), target packages on the target CPU; only the kernel
  and the image are machine specific.

Fill the cache once with a common base (`core-image-minimal`) plus the sources
of a firmware image:

```bash
docker compose --profile warm run --rm warm-cache
```

`WARM_MACHINES`, `WARM_TARGETS` and `WARM_FETCH_TARGETS` change what is
prepared, e.g. `WARM_MACHINES="qemuarm64 qemux86-64"`.

## Build a firmware

Select the firmware with `FIRMWARE` (default `router-cwe078-os-command-injection`):

```bash
FIRMWARE=router-cwe078-os-command-injection docker compose up --build yocto
```

The container builds `iotbench-<firmware>`, reusing the cache, and copies the
root filesystem and kernel to `deploy-images/<firmware>/<machine>/`. Run the same
command again after changing the layer. Build for another architecture with
`YOCTO_MACHINE` (see [Architectures](#architectures)):

```bash
YOCTO_MACHINE=qemux86-64 FIRMWARE=router-cwe078-os-command-injection docker compose up yocto
```

Build every firmware in the catalog, optionally across architectures:

```bash
./scripts/build-all.sh
MACHINES="qemuarm64 qemuarm qemux86-64 qemux86 qemumips" ./scripts/build-all.sh
```

### Windows with WSL 2

The supported Windows setup uses an Ubuntu WSL 2 distribution together with
Docker Desktop. The Yocto build itself runs in Docker; WSL provides the Linux
shell used to run the repository scripts.

Install WSL 2 from an elevated PowerShell terminal, then restart Windows if
requested:

```powershell
wsl --install -d Ubuntu
```

Install [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)
and configure it as follows:

1. In **Settings > General**, enable **Use the WSL 2 based engine**.
2. In **Settings > Resources > WSL Integration**, enable integration for the
   Ubuntu distribution installed above.
3. Allocate at least 16 GB of RAM and 150 GB of virtual disk space for Docker.

Use Docker Desktop's engine; do not install a second Docker daemon inside the
WSL distribution. Open Ubuntu and install the tools needed to clone and run the
scripts:

```bash
sudo apt update
sudo apt install -y git
docker info
docker compose version
```

For the best filesystem performance, clone the repository into the WSL Linux
filesystem rather than under `/mnt/c`:

```bash
mkdir -p ~/src
cd ~/src
git clone <repository-url> IoTBench
cd IoTBench
chmod +x scripts/*.sh
./scripts/build-all.sh
```

To build all supported architectures instead of the default `qemuarm64`:

```bash
MACHINES="qemuarm64 qemuarm qemux86-64 qemux86 qemumips" ./scripts/build-all.sh
```

Artifacts are written to `deploy-images/<firmware>/<machine>/`. If WSL reports
`Cannot connect to the Docker daemon at unix:///var/run/docker.sock`, confirm
that Docker Desktop is running and that WSL integration is enabled for the
distribution. Then run the following in PowerShell and reopen Ubuntu:

```powershell
wsl --shutdown
```

QEMU is not required to build the images. Install it separately inside WSL only
when you want to boot them; see [Run QEMU on the host](#run-qemu-on-the-host).

To start from a clean build directory while keeping the cache:

```bash
docker compose down
docker volume rm yocto-build
```

## Publish the builder image

```bash
docker buildx build --platform linux/amd64,linux/arm64 \
    -t <user>/yocto-builder:6.0.3 --push .
YOCTO_BUILDER_IMAGE=<user>/yocto-builder docker compose up yocto
```

Keep the cache out of the image: it is many GB, partly host-architecture
specific and would be duplicated on disk when copied into the volume.

## Performance notes

- Docker Desktop: give it as many CPUs as possible, at least 16 GB of RAM and
  150 GB of virtual disk.
- Apple Silicon: use the native `linux/arm64` image, never
  `--platform linux/amd64`.
- Windows: use the WSL2 backend. `.gitattributes` enforces LF line endings,
  required for scripts and recipes mounted into the container.
- Keep the cache and build directory on Docker volumes, not on bind mounts.

## Run QEMU on the host

QEMU is not part of the container. Install `qemu-system-aarch64` and `zstd`;
on macOS with Homebrew:

```bash
brew install qemu zstd
```

Boot a firmware (same `FIRMWARE` and `YOCTO_MACHINE` selectors as the build;
defaults `router-cwe078-os-command-injection` / `qemuarm64`):

```bash
FIRMWARE=ipcamera-cwe078-os-command-injection ./scripts/run-qemu.sh
YOCTO_MACHINE=qemux86-64 FIRMWARE=router-cwe078-os-command-injection ./scripts/run-qemu.sh
```

The dashboard is available at <http://127.0.0.1:8080>. The firmware always
listens on guest port 80; the host port can be changed:

```bash
QEMU_HTTP_PORT=80 ./scripts/run-qemu.sh
```

`run-qemu.sh` exposes additional ports only when the selected firmware needs
them:

| Scenario | Host endpoint | Override |
| --- | --- | --- |
| SSH hardcoded backdoor | `127.0.0.1:2222` -> guest `:22` | `QEMU_SSH_PORT` |
| Anonymous FTP login | `127.0.0.1:2121` -> guest `:21`; passive `30000-30009` unchanged | `QEMU_FTP_PORT` (control only) |
| TCP service injection | `127.0.0.1:9090` -> guest `:9090` | `QEMU_SERVICE_PORT` |
| CoAP internal-file exposure | `127.0.0.1:5683` -> guest `:5683` (UDP) | `QEMU_COAP_PORT` |
| MQTT device profiles and MQTT internal-file fixtures | `127.0.0.1:1883` -> guest `:1883` | `QEMU_MQTT_PORT` |
| PLC profile | `127.0.0.1:1502` -> guest `:502` | `QEMU_MODBUS_PORT` |
| Smart bulb ZCL parser | `127.0.0.1:17754` -> guest `:17754` | `QEMU_ZCL_PORT` |
| Smart speaker media parser | `127.0.0.1:18000` -> guest `:18000` | `QEMU_MEDIA_PORT` |
| Health monitor protocol | `127.0.0.1:2575` -> guest `:2575` | `QEMU_HEALTH_PORT` |

For example, start the firmware in one terminal and run the matching client
command from a second terminal:

```bash
FIRMWARE=router-cwe287-ssh-hardcoded-backdoor ./scripts/run-qemu.sh
ssh -p 2222 support@127.0.0.1

FIRMWARE=router-cwe078-service-interface-injection ./scripts/run-qemu.sh
printf 'status; id\n' | nc 127.0.0.1 9090
```

On Apple Silicon, hardware acceleration can be enabled:

```bash
QEMU_ACCEL=hvf QEMU_CPU=host ./scripts/run-qemu.sh
```

By default QEMU boots with `-snapshot`: the rootfs is always writable, guest
writes go to a throwaway overlay, and the golden `.ext4` never corrupts, so
every boot starts clean. This suits a target that is re-exploited each run. To
keep guest writes across reboots instead:

```bash
QEMU_PERSIST=1 ./scripts/run-qemu.sh
```

In persistent mode, power off from inside the guest with `poweroff` rather than
`Ctrl-A X`; a hard kill leaves the ext4 journal dirty and ext4 eventually
remounts the rootfs read-only (`errors=remount-ro`).

To quit QEMU from the serial console: `Ctrl-A`, then `X`.

### Reaching the dashboard from Windows (WSL2)

When QEMU runs inside WSL2, the host-forwarded port is bound to `127.0.0.1`
inside the distro. If `http://localhost:8080` does not open from the Windows
browser, enable mirrored networking in `C:\Users\<user>\.wslconfig`:

```ini
[wsl2]
networkingMode=mirrored
```

Then `wsl --shutdown` from PowerShell and restart WSL. A leftover
`netsh interface portproxy` rule on the same port also blocks the bind; remove
it from an elevated PowerShell with
`netsh interface portproxy delete v4tov4 listenaddress=0.0.0.0 listenport=8080`.

## Firmware shell access

The QEMU serial console uses these development credentials:

```text
login: root
password: routeradmin
```

`routerweb` is normally only the dashboard service account and cannot log in.
The two CWE-798 images intentionally enable SSH login for it with the shared
password `iotbench`. The `yocto` user belongs to the builder container and does
not exist in the firmware.
Change the password before using the image outside a local development setup.

## Firmware: router, CWE-78 OS command injection

Firmware id `router-cwe078-os-command-injection`. The dashboard shows a **Ping**
diagnostic module (`recipes-vulns/cwe078-os-command-injection/files/module.php`).
Its `ping` action invokes `/usr/bin/router-ping`, compiled from `router-ping.c`,
which builds a shell command from the submitted target without sanitization.

The flaw is **CWE-78** (OS Command Injection): unsanitized input is concatenated
into a shell command and executed. The remediation is to validate the target as
an IPv4 address and invoke `ping` with a direct argument vector (without a
shell), e.g. `execve()`/`posix_spawn()`.

### Runtime model

The injected command runs in the context of `php-cgi`, spawned by lighttpd, so
two layers shape what it can do:

- **systemd sandbox.** The upstream `lighttpd.service` hardens the daemon with
  `ProtectHome`, `ProtectSystem`, `PrivateTmp` and `MemoryDenyWriteExecute`,
  which make the filesystem read-only for the service and cause writes to fail
  with `Read-only file system`. This firmware's vulnerability package ships a
  drop-in (`lighttpd-writable.conf` →
  `/lib/systemd/system/lighttpd.service.d/`) that disables the sandbox so the
  vulnerability behaves like a real RCE.
- **Privilege drop.** lighttpd runs as the unprivileged `routerweb` user
  (`server.username` in `lighttpd.conf`), so even with the sandbox off, writes
  obey normal Unix permissions.

Directories `routerweb` (uid/gid 995) can write to, once the sandbox is removed:

| Path | Mode | Persists | Notes |
| --- | --- | --- | --- |
| `/tmp` | `1777` | yes (rootfs) | General scratch space. |
| `/var/tmp` → `/var/volatile/tmp` | `1777` | no (tmpfs) | Lost on reboot. |
| `/dev/shm` | `1777` | no (tmpfs) | Lost on reboot. |
| `/var/lib/router-dashboard` | `0750`, `995:995` | yes (rootfs) | The service account's home; the realistic foothold. |
| `/home`, `/etc`, `/usr`, `/www/pages` | root-owned | — | Not writable: permission denied. |

The docroot and system paths staying read-only is realistic: an unprivileged web
RCE is confined, and reaching further would need a separate privilege-escalation
bug.
