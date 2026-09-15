# Yocto Docker Builder

This project creates a Docker container with Yocto/OpenEmbedded already
configured to generate a sample firmware image.

Important: `docker build` only creates the Docker builder image. The actual
firmware is created later, by entering the container and running `bitbake`.

## Requirements

- Docker installed and running
- Internet connection to download sources during the Yocto build
- Plenty of free disk space. A Yocto build can use tens of GB.

## 1. Build the Docker image

From this project directory:

```bash
docker build -t yocto-builder:6.0.3 .
```

The Docker image name will be:

```text
yocto-builder:6.0.3
```

## 2. Enter the container

Create a container with a fixed name, so it is easy to copy the generated files
out later:

```bash
docker run -it --name yocto-build yocto-builder:6.0.3
```

If the `yocto-build` container already exists, remove it first:

```bash
docker rm yocto-build
```

Then run the `docker run` command again.

## 3. Generate the firmware

Inside the container:

```bash
cd /workdir/yocto-firmware
source layers/openembedded-core/oe-init-build-env build
bitbake core-image-minimal
```

The build can take a long time.

## 4. Firmware output location

After a successful build, the generated files are here inside the container:

```text
/workdir/yocto-firmware/build/tmp/deploy/images/qemux86-64/
```

With the current configuration:

- Yocto target: `core-image-minimal`
- Yocto machine: `qemux86-64`
- Generated formats: `tar.zst` and `ext4.zst`

The main firmware file is named:

```text
core-image-minimal-qemux86-64.rootfs.ext4.zst
```

Yocto also creates a timestamped file, for example:

```text
core-image-minimal-qemux86-64.rootfs-YYYYMMDDHHMMSS.ext4.zst
```

The file without the timestamp is usually a symlink to the latest build.

The root filesystem archive is also generated:

```text
core-image-minimal-qemux86-64.rootfs.tar.zst
```

Note: with this configuration, the firmware is not named `.img`. The main
format is an `ext4` root filesystem compressed with `zstd`, so the file ends in
`.ext4.zst`.

To get the uncompressed `.ext4` file:

```bash
cd /workdir/yocto-firmware/build/tmp/deploy/images/qemux86-64
zstd -d core-image-minimal-qemux86-64.rootfs.ext4.zst
```

The result will be:

```text
core-image-minimal-qemux86-64.rootfs.ext4
```

## 5. Copy the firmware to the host machine

Exit the container:

```bash
exit
```

Then, from the project directory on the host machine:

```bash
mkdir -p deploy-images
docker cp yocto-build:/workdir/yocto-firmware/build/tmp/deploy/images/qemux86-64 ./deploy-images
```

The files will then be available at:

```text
./deploy-images/qemux86-64/
```

## 6. Resume an existing build

If the container still exists:

```bash
docker start -ai yocto-build
```

Then, inside the container:

```bash
cd /workdir/yocto-firmware
source layers/openembedded-core/oe-init-build-env build
bitbake core-image-minimal
```

## 7. Cleanup

To remove the container:

```bash
docker rm yocto-build
```

To also remove the Docker image:

```bash
docker rmi yocto-builder:6.0.3
```
