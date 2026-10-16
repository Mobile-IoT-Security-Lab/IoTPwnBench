# Developing a firmware for IoTBench

This guide explains how to add a firmware to the platform. A firmware is one
bootable image built from a **device profile** plus **one** vulnerability
implementing a single CWE. The catalog is a matrix of device types × CWEs.

> These images are intentionally vulnerable. Everything here is for isolated lab
> and research use only.

## Mental model

Four pieces with different lifecycles:

- **Common image** (`recipes-images/iotbench-image.inc`) — boot, users, rootfs
  sizing, and the shared peripheral simulator. Device-agnostic.
- **Device profile** (`recipes-devices/<device>/`) — the skeleton app for a
  device class (router dashboard, camera CGI, MQTT client, Modbus server...) plus
  its peripheral spec. Provides `IOTBENCH_DEVICE_INSTALL`.
- **Vulnerability package** (`recipes-vulns/<cwe>/`) — one package implementing
  one CWE: the vulnerable code, and for a web bug a dashboard module.
- **Firmware image recipe** (`recipes-images/iotbench-<device>-<cwe>-<slug>.bb`)
  — a thin recipe combining a device profile with a vulnerability.

The builder image and cache are generic; a new firmware is just a new BitBake
target reusing the shared `sstate-cache`.

## Peripheral simulation

Peripheral values are not static. A shared daemon, **`iotbench-sim`**
(`recipes-platform/iotbench-sim/`), reads a device's
`/etc/iotbench/peripherals.conf` and writes live values every few seconds to
`/run/iotbench/state.json` (for the web admin) and `/run/iotbench/state.env`
(flat `NAME=value` lines, for shell/C native services). The models are standard
stochastic processes for synthetic telemetry (see the file header for the
references).

Each line of `peripherals.conf` is `<name> <type> key=value...`. Types:

| Type | Behaviour | Keys |
| --- | --- | --- |
| `walk` | Ornstein–Uhlenbeck mean-reverting process, clamped | `min max mu theta step init unit` |
| `walkint` | integer OU process | `min max mu theta step init unit` |
| `diurnal` | `base + amp*sin(2π t/period) + noise` | `base amp noise period unit` |
| `binary` | two-state (telegraph) Markov process | `p01 p10 init` |
| `enum` | finite-state Markov jumps | `states=a,b,c p init` |
| `counter` | monotonic accumulator (e.g. kWh) | `rate init unit` |

For `walk`/`walkint`, `mu` is the long-run mean (defaults to `init` or the
midpoint), `theta` the reversion rate, `step` the volatility (sigma).

Example (router):

```text
wan_rx_rate  walk     unit=Mbps min=0   max=940  init=120 step=30
cpu_temp     diurnal  unit=C    base=54 amp=6    noise=1.5 period=3600
uplink       binary   p01=0.6   p10=0.01 init=1
```

Reading the state from PHP is one call (`dashboard_sim()` in the router). Other
skeletons parse `/run/iotbench/state.json` themselves.

## Conventions

- **Firmware id:** `<device>-cwe<NNN>-<slug>`, CWE number zero-padded to 3
  digits, e.g. `router-cwe078-os-command-injection`. It is the image recipe
  suffix and the `FIRMWARE` value.
- **Package names:** device package `device-<device>`; vulnerability package
  `cwe<NNN>-<slug>`.
- **One CWE per firmware.** No runtime switches; each image is deterministic.
- **English only** in all repo files, including UI strings.
- **LF line endings** (enforced by `.gitattributes`).
- **Determinism:** pin external sources (git `SRCREV`, release tag).

## Adding a vulnerability to an existing device (most common)

For a device with a web UI (router, and future camera/NAS), a vulnerability plugs
in as a dashboard *module*: the core discovers modules at runtime under
`/usr/share/router-dashboard/modules/*/module.php` — you never edit the device or
platform recipes.

### 1. Create the vulnerability package

```text
meta-iotbench/recipes-vulns/cwe<NNN>-<slug>/
├── cwe<NNN>-<slug>_1.0.bb
└── files/
    ├── LICENSE           (MIT, md5 2ac030fbcf0423505c28549799c198f7)
    ├── module.php        (web module; see below)
    └── ...               (vulnerable binary source, configs, etc.)
```

Template: `recipes-vulns/cwe078-os-command-injection/`. A typical recipe:

```bitbake
SUMMARY = "IoTBench vulnerability module - CWE-<NNN> <name>"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=2ac030fbcf0423505c28549799c198f7"
SRC_URI = "file://LICENSE file://module.php"
S = "${UNPACKDIR}"
RDEPENDS:${PN} = "router-dashboard"

do_install() {
    install -d ${D}${datadir}/router-dashboard/modules/<id>
    install -m 0644 ${S}/module.php ${D}${datadir}/router-dashboard/modules/<id>/module.php
}
FILES:${PN} = "${datadir}/router-dashboard/modules/<id>"
```

Native helper? Compile from local C source (see the CWE-78 recipe:
`DEPENDS += "virtual/libc"`, a `do_compile()` calling
`${CC} ${CFLAGS} ${LDFLAGS} ... -o ${B}/<bin>`, then `install -d ${D}${bindir}`
and `install -m 0755` into `${bindir}`).

### 2. Write the dashboard module

`module.php` registers a panel and API actions. It is trusted code (ships in the
image), so its rendered HTML is emitted verbatim.

```php
<?php
declare(strict_types=1);

dashboard_register_module([
    'id'    => '<id>',
    'title' => 'Human title',
    'tag'   => 'CATEGORY',
    'render' => static function (): string {
        return <<<'HTML'
<form class="module-form" data-action="<action-name>">
    <label>Target <input name="target" maxlength="240" required></label>
    <button class="button primary" type="submit">Run</button>
    <pre class="module-output" aria-live="polite">No run yet.</pre>
</form>
HTML;
    },
    'actions' => [
        '<action-name>' => static function (array $input): array {
            $value = trim((string)($input['target'] ?? ''));
            if ($value === '') {
                return ['ok' => false, 'error' => 'Invalid input', 'status' => 422];
            }
            // ... the intentionally vulnerable behaviour ...
            return ['ok' => true, 'message' => 'Done', 'output' => $result];
        },
    ],
]);
```

### 3. Add the firmware image recipe

`recipes-images/iotbench-<device>-cwe<NNN>-<slug>.bb`:

```bitbake
require recipes-images/iotbench-image.inc
require recipes-devices/<device>/device-<device>.inc

SUMMARY = "IoTBench target - <device>, CWE-<NNN> <name>"
IOTBENCH_CWE = "CWE-<NNN>"
IOTBENCH_VULN_INSTALL = "cwe<NNN>-<slug>"
```

### 4. Register in the catalog

Add a row to the "Firmware catalog" table in the top-level `README.md`.

## Adding a new device type

Create `recipes-devices/<device>/`, using `router` as the template:

```text
recipes-devices/<device>/
├── device-<device>.inc          # sets IOTBENCH_DEVICE + IOTBENCH_DEVICE_INSTALL
├── device-<device>_1.0.bb       # installs /etc/iotbench/peripherals.conf; RDEPENDS the app
├── files/peripherals.conf       # the device's simulated peripherals
└── <app>/                       # the skeleton app recipe + files (like router-dashboard/)
```

- `device-<device>.inc`:

  ```bitbake
  IOTBENCH_DEVICE = "<device>"
  IOTBENCH_DEVICE_INSTALL = "device-<device>"
  ```

- `device-<device>_1.0.bb` installs `peripherals.conf` into `/etc/iotbench/` and
  `RDEPENDS` on the skeleton app package.
- The **skeleton app** is the device's primary service. For a web device reuse
  lighttpd + php and the dashboard module system; for others ship the native
  service (see below).

> Recipes may nest up to `recipes-<x>/<a>/<b>/<recipe>.bb` (the skeleton app in a
> subdirectory of the device); `conf/layer.conf` globs that depth.

## The non-web path

Not every device or CWE is web-based. A device/vulnerability package may instead
ship:

- a **network daemon** with its own systemd unit and listening port (e.g. an
  MQTT client, a Modbus/TCP server), or
- a **setuid binary** (e.g. a second-stage privilege-escalation target).

The image recipe still just lists the packages via `IOTBENCH_DEVICE_INSTALL` and
`IOTBENCH_VULN_INSTALL`; no dashboard module is required. The service reads
`/run/iotbench/state.env` (or `state.json`) to expose simulated peripheral
values. Implemented templates to copy:

- **MQTT** (`recipes-platform/iotbench-mqtt/`) — a publisher against a local
  mosquitto broker; used by every MQTT-class device profile.
- **Modbus/TCP** (`recipes-devices/plc/iotbench-modbusd_1.0.bb`) — a libmodbus
  server mapping peripherals to registers.
- **HTTP snapshot + MJPEG** (`recipes-devices/ipcamera/ipcamera-stream_1.0.bb`) —
  served through the shared lighttpd.

`mosquitto` needs the `meta-networking` layer (with `meta-python`), already in
`YOCTO_LAYERS`; `libmodbus` is in `meta-oe`.

## Java fixtures

Java utilities follow the same local-source vulnerability-package pattern;
keep Java sources in the package's `files/` directory. The pinned
`meta-openjdk` layer is included by the builder and Compose. IoTBench selects
OpenJDK 17, with `openjdk-bin-native` supplying build-time `javac` and `openjdk`
supplying the cross-built target runtime. Rebuild the builder after pulling
changes to its layer pins: `docker compose build yocto`.

Use `${STAGING_LIBDIR_NATIVE}/jvm/bin/javac --release 17` in `do_compile()` and
package an executable JAR with explicit Main-Class and Class-Path. Install
fixture JARs and matching source/assets under `${datadir}/iotbench/<scenario>/`;
shared dependency JARs belong in `${datadir}/java/`. Fixed ZIP timestamps and
entry ordering avoid timestamp-dependent artifacts. No Maven/Gradle application
project or target compiler is needed for a small utility.

For SQLite JDBC, reuse the pinned `iotbench-sqlite-jdbc` platform package: its
Java classes use a Yocto-built JNI library linked to target SQLite. Do not copy
host native libraries into firmware. Render `datadir`/`libdir` into packaged
configuration rather than accepting user-selected database paths. See
[Java SQL injection](java-sql-injection.md) for the complete reference recipe,
offline image checks, host JVM regression and disposable guest tests.

## Dashboard module API reference

Provided by `router.php` (router device):

- `dashboard_register_module(array $module): void` — call once from
  `module.php`. Fields: `id` (required), `title`, `tag`, `render` (callable
  returning HTML), `actions` (map of action name → `callable(array): array`).
- **Action handler:** receives the decoded JSON body; returns an array sent as
  JSON. Success: `['ok' => true]` plus `message` (toast) and `output`
  (`.module-output`). Failure: `['ok' => false, 'error' => '...', 'status' =>
  <http code>]`. CSRF and method checks are done by the core; reserved core
  actions are `save_wifi`, `save_network`, `client_access`, `restart`.
- **Front-end contract** (`app.js`): `<form class="module-form"
  data-action="...">` — every named input is sent in the payload; an optional
  `<pre class="module-output">` receives `result.output`; `result.message` is a
  toast.

## Service hardening

lighttpd runs as the unprivileged `routerweb` user and its upstream systemd unit
is sandboxed (`ProtectSystem`, `ProtectHome`, `MemoryDenyWriteExecute`, ...). If a
web vulnerability must write to the filesystem like a real RCE, ship a systemd
drop-in that relaxes the sandbox — see
`recipes-vulns/cwe078-os-command-injection/files/lighttpd-writable.conf` and the
"Runtime model" section of `README.md`. Writes still obey `routerweb`'s Unix
permissions.

## Build and test loop

Select the firmware with `FIRMWARE` (default
`router-cwe078-os-command-injection`).

```bash
# One-off: warm the shared cache (only needed once)
docker compose --profile warm run --rm warm-cache

# Validate the layer without building (fast): parse + dependency graph
docker compose run --rm yocto bash -lc \
  'source /opt/yocto/yocto-env.sh && bitbake -p && bitbake -n iotbench-<device>-cwe<NNN>-<slug>'

# Build and export the firmware
FIRMWARE=<device>-cwe<NNN>-<slug> docker compose up --build yocto   # -> deploy-images/<firmware>/qemuarm64/

# Boot it (writable rootfs via -snapshot by default)
FIRMWARE=<device>-cwe<NNN>-<slug> ./scripts/run-qemu.sh             # dashboard on http://127.0.0.1:8080

# Build every firmware in the catalog, optionally across architectures
./scripts/build-all.sh
MACHINES="qemuarm64 qemuarm qemux86-64 qemux86 qemumips" ./scripts/build-all.sh
```

The architecture is a build-time selector (`YOCTO_MACHINE`), not a separate
recipe; keep device and vulnerability recipes architecture-agnostic (no
hardcoded arch, tune, or kernel assumptions). Artifacts land in
`deploy-images/<firmware>/<machine>/`.

`bitbake -p` catches recipe/layer syntax errors; `bitbake -n` resolves the
dependency graph without compiling. To inspect what landed in an image,
decompress the exported `.ext4.zst` and read it with `debugfs` (no root mount).

## Submission checklist

- [ ] Device profile exists (`recipes-devices/<device>/`) or you reuse one.
- [ ] `recipes-vulns/cwe<NNN>-<slug>/` with recipe, `LICENSE`, and code/module.
- [ ] `recipes-images/iotbench-<device>-cwe<NNN>-<slug>.bb` requiring the common
      image and the device profile.
- [ ] Catalog row added to `README.md`.
- [ ] `bitbake -p` clean; `FIRMWARE=<id> docker compose up yocto` succeeds.
- [ ] Booted in QEMU; the vulnerability is reachable and behaves as intended.
- [ ] English strings only; external sources pinned; one CWE per firmware.
