# Yocto Router Dashboard

Firmware Yocto 6.0.3 per `qemuarm64` con una dashboard PHP che simula la
gestione di un router. Lighttpd ascolta su tutte le interfacce del firmware,
porta 80, e avvia PHP tramite CGI.

La dashboard include:

- panoramica con metriche reali lette da `/proc` e `/sys`;
- traffico delle interfacce aggiornato in tempo reale;
- gestione simulata dei client con pausa/ripristino;
- impostazioni simulate Wi-Fi, rete ospiti, LAN e DHCP;
- stato kernel, architettura, runtime PHP e interfacce;
- layout responsive, senza CDN o dipendenze browser esterne.

Le azioni effettuate dalla UI non cambiano la rete Linux. Lo stato dimostrativo
viene salvato in `/var/lib/router-dashboard/settings.json`.

## Struttura

Il codice versionato è un layer OpenEmbedded completo:

```text
meta-router-dashboard/
├── conf/layer.conf
├── recipes-core/images/router-dashboard-image.bb
├── recipes-connectivity/router-dashboard/
├── recipes-devtools/php/php_%.bbappend
└── recipes-extended/lighttpd/lighttpd_%.bbappend
```

La build usa inoltre `meta-openembedded/meta-oe`, fissato alla revisione
compatibile con la serie `wrynose`, per la ricetta PHP.

## Preparazione automatica nel Dockerfile

Durante `docker compose build`, il `Dockerfile` esegue automaticamente:

1. creazione di `/workdir/yocto-firmware/layers`;
2. clone di BitBake, OpenEmbedded Core e `meta-yocto` dalla branch
   `yocto-6.0.3`;
3. creazione della directory `build` tramite `oe-init-build-env`;
4. configurazione di `MACHINE` in `build/conf/local.conf` usando il build arg
   `YOCTO_MACHINE`;
5. build di `core-image-minimal`;
6. registrazione dei layer PHP e dashboard.

Lo script avviato da Compose verifica nuovamente `MACHINE` e lancia prima
`core-image-minimal`, poi `router-dashboard-image`. Questo secondo controllo è
necessario perché il volume persistente `yocto-volume` può contenere una build
creata da una versione precedente del builder.

## Build ed esportazione tramite Docker Compose

Il Compose usa tre mapping oltre al volume persistente di Yocto:

```text
./meta-router-dashboard -> /workdir/yocto-firmware/layers/meta-router-dashboard (sola lettura)
./deploy-images         -> /export
./scripts               -> /project-scripts (sola lettura)
```

L'architettura Yocto viene impostata da CLI tramite `YOCTO_MACHINE`. Compose
passa lo stesso valore sia al build arg del `Dockerfile`, sia allo script
eseguito dal container. `qemuarm64` rimane il valore predefinito:

```bash
YOCTO_MACHINE=qemuarm64 docker compose up -d --build
docker compose logs -f yocto
```

La forma esplicita per costruire soltanto l'immagine builder è:

```bash
docker compose build --build-arg YOCTO_MACHINE=qemuarm64 yocto
```

Il primo comando compila automaticamente il firmware e scrive gli artefatti
necessari a QEMU direttamente nella repository locale.

Quando nei log compare `Firmware pronto`, l'immagine si trova in
`deploy-images/qemuarm64/`. QEMU non è installato né eseguito nel container.
Per ripetere build ed esportazione dopo una modifica:

```bash
docker compose restart yocto
docker compose logs -f yocto
```

## Build manuale nel container esistente

Con il container `yocto` attivo e `yocto-volume` montato su `/workdir`:

```bash
./scripts/sync-and-build.sh
```

Lo script copia il layer in
`/workdir/yocto-firmware/layers/meta-router-dashboard`, registra i layer e
compila:

```text
router-dashboard-image
```

Gli output QEMU sono generati in:

```text
/workdir/yocto-firmware/build/tmp/deploy/images/qemuarm64/
```

I file principali sono l'immagine root filesystem `.ext4.zst`, il kernel
`Image` e il file `.qemuboot.conf`. Sono binari ARM64 avviabili con QEMU.

Al termine della build lo script li esporta automaticamente anche sull'host.
La stessa cartella viene popolata direttamente dal servizio Compose:

```text
deploy-images/qemuarm64/
├── Image
├── router-dashboard-image-qemuarm64.rootfs.ext4.zst
├── router-dashboard-image-qemuarm64.rootfs.qemuboot.conf
├── router-dashboard-image-qemuarm64.rootfs.manifest
└── SHA256SUMS
```

Per riesportare gli artefatti senza ricompilare:

```bash
./scripts/export-firmware.sh
```

## Avvio QEMU locale

QEMU non viene eseguito nel container. Il container serve esclusivamente per
la build Yocto; lo script seguente usa i file in `deploy-images/` e avvia
`qemu-system-aarch64` direttamente sul computer host.

Sono richiesti `qemu-system-aarch64` e `zstd`. Su macOS con Homebrew:

```bash
brew install qemu zstd
```

Avvio:

```bash
./scripts/run-qemu.sh
```

La dashboard sarà disponibile su:

```text
http://127.0.0.1:8080
```

Il firmware ascolta sempre sulla porta guest 80. La porta locale è configurata
da QEMU e può essere cambiata, per esempio:

```bash
QEMU_HTTP_PORT=80 ./scripts/run-qemu.sh
```

Su un Mac Apple Silicon si può richiedere l'accelerazione hardware:

```bash
QEMU_ACCEL=hvf QEMU_CPU=host ./scripts/run-qemu.sh
```

L'immagine `.ext4.zst` viene decompressa localmente al primo avvio. Il file
`.ext4` risultante non usa la modalità snapshot, quindi le impostazioni della
dashboard restano disponibili tra i successivi avvii locali. Una nuova
esportazione della build sostituisce il firmware locale.

Per chiudere QEMU nella console seriale: `Ctrl-A`, poi `X`.

## Accesso alla shell del firmware

La console seriale QEMU usa queste credenziali di sviluppo:

```text
login: root
password: routeradmin
```

`routerweb` è esclusivamente l'account di servizio della dashboard e non può
effettuare il login. L'utente `yocto` appartiene invece al container builder e
non esiste nel firmware. Cambiare la password prima di usare l'immagine fuori
da un ambiente locale di sviluppo.

## Container builder

Il container non pubblica porte e non esegue QEMU. Per avviarlo conservando il
volume nominato e facendo partire automaticamente build ed esportazione:

```bash
YOCTO_MACHINE=qemuarm64 docker compose up -d --build
```

Se esiste già un container `yocto` creato senza Compose, Docker richiede prima
che venga fermato e rimosso. La rimozione del container non elimina
`yocto-volume`; il volume è dichiarato `external` anche in Compose per evitare
che la build venga rimossa insieme al container.

## Build pulita del builder

Per creare l'immagine builder da questa repository e generare il firmware:

```bash
YOCTO_MACHINE=qemuarm64 docker compose up -d --build
docker compose logs -f yocto
```

Il volume nominato rende persistenti download, cache sstate e artefatti tra le
esecuzioni.
