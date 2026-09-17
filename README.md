# Yocto Router Dashboard

Yocto 6.0.3 firmware for `qemuarm64` with a PHP dashboard that simulates router
management. Lighttpd listens on port 80 on every interface of the firmware and
runs PHP through CGI.

The dashboard includes:

- an overview with real metrics read from `/proc` and `/sys`;
- live interface traffic;
- simulated client management with pause/resume;
- simulated Wi-Fi, guest network, LAN and DHCP settings;
- kernel, architecture, PHP runtime and interface status;
- a responsive layout with no CDN or external browser dependencies.

Actions in the UI do not change the Linux network. The demo state is stored in
`/var/lib/router-dashboard/settings.json`.

## Layout

```text
builder/                  generic Yocto builder, copied into the image
├── site.conf             cache locations (DL_DIR, SSTATE_DIR, hash equivalence)
├── yocto-env.sh          sets up /workdir/build for YOCTO_MACHINE and YOCTO_LAYERS
└── warm-cache.sh         fills the cache without exporting firmware
meta-router-dashboard/    OpenEmbedded layer of the firmware
scripts/
├── container-build-and-export.sh   builds the image and exports it (run by Compose)
└── run-qemu.sh                     boots the exported firmware on the host
```

The build also uses `meta-openembedded/meta-oe`, pinned to a revision compatible
with the `wrynose` series, for the PHP recipe.

## Builder and cache

| Part | Location | Contents |
| --- | --- | --- |
| image `yocto-builder:6.0.3` | `/opt/yocto` | tools, BitBake and pinned layers |
| volume `yocto-cache` | `/cache` | `downloads/`, `sstate-cache/`, `hashserv/` |
| volume `yocto-build` | `/workdir` | build directory, safe to delete |

The image contains no firmware layer and no build output, so it can be pushed to
a registry. Project layers are mounted at runtime and enabled via `YOCTO_LAYERS`.

What the cache can reuse:

- `downloads/`: sources, valid for any machine, image and host;
- `sstate-cache/`: task outputs, reused by every image sharing those tasks.
  `-native` tools depend on the host architecture (arm64 on Apple Silicon,
  amd64 on most Windows PCs), target packages on the target CPU; only the kernel
  and the image are machine specific.

Fill the cache once with a common base (`core-image-minimal`) plus the sources
of the dashboard image:

```bash
docker compose --profile warm run --rm warm-cache
```

`WARM_MACHINES`, `WARM_TARGETS` and `WARM_FETCH_TARGETS` change what is
prepared, e.g. `WARM_MACHINES="qemuarm64 qemux86-64"`.

## Build the firmware

```bash
YOCTO_MACHINE=qemuarm64 docker compose up --build yocto
```

The container builds `router-dashboard-image`, reusing the cache, and copies the
root filesystem and kernel to `deploy-images/qemuarm64/`. Run the same command
again after changing the layer.

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

Boot the firmware:

```bash
./scripts/run-qemu.sh
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

The `.ext4.zst` image is decompressed on first boot and after each new export.
The `.ext4` file is not a snapshot, so dashboard settings survive reboots until
the next export.

To quit QEMU from the serial console: `Ctrl-A`, then `X`.

## Firmware shell access

The QEMU serial console uses these development credentials:

```text
login: root
password: routeradmin
```

`routerweb` is only the dashboard service account and cannot log in. The `yocto`
user belongs to the builder container and does not exist in the firmware.
Change the password before using the image outside a local development setup.
