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
| smartplug, thermostat | MQTT publisher + local broker | `iotbench/<class>/<peripheral>` on :1883 |
| plc | Modbus/TCP server | registers on :502 |

## Firmware catalog

All firmwares carry CWE-78 (web-admin ping diagnostic → shell). Firmware id is
`<device>-cwe078-os-command-injection`.

| Device | Category | Native service |
| --- | --- | --- |
| `router` | network gateway | web admin (HTTP) |
| `ipcamera` | surveillance camera | HTTP snapshot + MJPEG |
| `smartplug` | energy management | MQTT |
| `thermostat` | climate control | MQTT |
| `plc` | industrial gateway (OT) | Modbus/TCP |
| `smartbulb` | lighting | MQTT |
| `smarthub` | controller / hub | MQTT |
| `envsensor` | environmental sensor | MQTT |
| `smartspeaker` | audio / voice assistant | MQTT |
| `healthmonitor` | health monitor | MQTT |
| `doorlock` | access control | MQTT |

Each firmware maps to `recipes-images/iotbench-<firmware id>.bb`. The catalog is
the set of those recipes; the table above is a convenience copy. Every device
carries a distinct simulated peripheral set (`recipes-devices/<device>/files/peripherals.conf`).

Additional router scenarios from the Francesco catalog slice:

| Firmware id | CWE | Scenario |
| --- | --- | --- |
| `router-cwe276-leaked-private-key` | CWE-276 | Private key exposed under the web document root |
| `router-cwe276-bad-chown-rights` | CWE-276 | Privileged configuration file owned by the web user |
| `router-cwe798-ld-preload-sudo` | CWE-798 | Sudo rule preserving `LD_PRELOAD` for a root command |
| `router-cwe798-vi-privilege-escalation` | CWE-798 | Passwordless sudo rule for a privileged editor |
| `router-cwe078-writable-root-cron` | CWE-78 | Root cron entry executes a web-user-writable script |
| `router-cwe287-ssh-hardcoded-backdoor` | CWE-287 | Hardcoded SSH support account |
| `router-cwe089-http-sqli-auth` | CWE-89 | HTTP login SQL injection |
| `router-cwe078-bash-command-injection` | CWE-78 | Bash diagnostic command injection |
| `router-cwe077-c-command-injection` | CWE-77 | C helper command injection |
| `router-cwe416-use-after-free` | CWE-416 | Freed authorization object reuse |
| `router-cwe400-diagnostic-dos` | CWE-400 | Diagnostic resource exhaustion |
| `router-cwe078-service-interface-injection` | CWE-78 | TCP service interface command injection |
| `router-cwe022-path-traversal` | CWE-22 | Report viewer path traversal |

Payloads and expected exploit signals for these scenarios are documented in
[docs/francesco-payloads.md](docs/francesco-payloads.md).

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

`routerweb` is only the dashboard service account and cannot log in. The `yocto`
user belongs to the builder container and does not exist in the firmware.
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
