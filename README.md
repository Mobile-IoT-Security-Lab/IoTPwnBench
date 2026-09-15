# Yocto Docker Builder

Questo progetto crea un container Docker con Yocto/OpenEmbedded gia configurato
per generare una immagine firmware di esempio.

Importante: `docker build` crea solo l'immagine Docker del builder. Il firmware
vero e proprio viene creato dopo, entrando nel container e lanciando `bitbake`.

## Requisiti

- Docker installato e avviato
- Connessione internet per scaricare i sorgenti durante la build Yocto
- Molto spazio libero su disco. Una build Yocto puo usare decine di GB.

## 1. Costruire l'immagine Docker

Dalla cartella di questo progetto:

```bash
docker build -t yocto-builder:6.0.3 .
```

Il nome dell'immagine Docker creata sara:

```text
yocto-builder:6.0.3
```

## 2. Entrare nel container

Creare un container con nome fisso, cosi poi e facile copiare fuori i file
generati:

```bash
docker run -it --name yocto-build yocto-builder:6.0.3
```

Se il container `yocto-build` esiste gia, rimuoverlo prima:

```bash
docker rm yocto-build
```

Poi rilanciare il comando `docker run`.

## 3. Generare il firmware

Dentro al container:

```bash
cd /workdir/yocto-firmware
source layers/openembedded-core/oe-init-build-env build
bitbake core-image-minimal
```

La build puo richiedere parecchio tempo.

## 4. Dove si trova il firmware

Dopo una build riuscita, i file generati sono qui, dentro al container:

```text
/workdir/yocto-firmware/build/tmp/deploy/images/qemux86-64/
```

Con la configurazione attuale:

- target Yocto: `core-image-minimal`
- macchina Yocto: `qemux86-64`
- formati prodotti: `tar.zst` ed `ext4.zst`

Il file principale del firmware si chiama:

```text
core-image-minimal-qemux86-64.rootfs.ext4.zst
```

Yocto crea anche un file con timestamp, per esempio:

```text
core-image-minimal-qemux86-64.rootfs-YYYYMMDDHHMMSS.ext4.zst
```

Il file senza timestamp e normalmente un link al file piu recente.

Viene generato anche l'archivio della root filesystem:

```text
core-image-minimal-qemux86-64.rootfs.tar.zst
```

Nota: con questa configurazione il firmware non si chiama `.img`. Il formato
principale e una root filesystem `ext4` compressa con `zstd`, quindi finisce in
`.ext4.zst`.

Per ottenere il file `.ext4` non compresso:

```bash
cd /workdir/yocto-firmware/build/tmp/deploy/images/qemux86-64
zstd -d core-image-minimal-qemux86-64.rootfs.ext4.zst
```

Il risultato sara:

```text
core-image-minimal-qemux86-64.rootfs.ext4
```

## 5. Copiare il firmware sul computer host

Uscire dal container:

```bash
exit
```

Poi, dalla cartella del progetto sul computer host:

```bash
mkdir -p deploy-images
docker cp yocto-build:/workdir/yocto-firmware/build/tmp/deploy/images/qemux86-64 ./deploy-images
```

A questo punto i file saranno disponibili in:

```text
./deploy-images/qemux86-64/
```

## 6. Riprendere una build gia iniziata

Se il container esiste ancora:

```bash
docker start -ai yocto-build
```

Poi dentro al container:

```bash
cd /workdir/yocto-firmware
source layers/openembedded-core/oe-init-build-env build
bitbake core-image-minimal
```

## 7. Pulizia

Per eliminare il container:

```bash
docker rm yocto-build
```

Per eliminare anche l'immagine Docker:

```bash
docker rmi yocto-builder:6.0.3
```
