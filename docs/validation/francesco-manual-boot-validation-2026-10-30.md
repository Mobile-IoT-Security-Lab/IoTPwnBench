# Francesco — validazione manuale boot + exploit

**Esito: 23/23 PASS al 30 ottobre 2026.** Validazione completa di tutti gli
scenari con `OWNER = Francesco`. Build ed export eseguiti e verificati in questa sessione (`0 ERROR`
in ogni build BitBake); gli exploit sono stati eseguiti **a mano da Francesco**
sulla sua macchina locale e l'esito PASS è stato riferito durante la sessione,
non da un log di esecuzione automatica.

## Identificazione e perimetro

- Catalogo: `Catalogo_Test_Sicurezza_Firmware_IoT.xlsm`, foglio
  `Comparison Previous Work`, righe con `OWNER = Francesco`, `Implemented = V`,
  `Number of test implemented = 1`. Il catalogo marca l'implementazione, non il
  boot-test runtime: quest'ultimo è ciò che registra il presente documento.
- Assegnatario: Francesco. Totale assegnazioni: 23 (13 scenari router + 10
  scenari device CVE-inspired).
- Macchina: `qemuarm64`. Build: `FIRMWARE=<id> docker compose up --build
  --force-recreate yocto`. Avvio: `scripts/run-qemu-docker.sh` (QEMU nativo dal
  volume `yocto-build`, nessun QEMU host).
- A differenza di una validazione su artefatto pre-esistente, **ogni immagine è
  stata ricostruita in questa sessione** dai sorgenti del repository, quindi la
  riproducibilità della build è stata esercitata.
- Payload per-firmware, interfaccia e segnale di successo atteso: in
  [../francesco-payloads.md](../francesco-payloads.md). Credenziali console/SSH:
  `root` / `routeradmin`; backdoor e sudo: `iotbench`.

## Esiti osservati

| # | Firmware | CWE | Interfaccia | Esito |
| --- | --- | --- | --- | --- |
| 1 | `router-cwe276-leaked-private-key` | CWE-276 | HTTP | PASS |
| 2 | `router-cwe276-bad-chown-rights` | CWE-276 | console seriale | PASS |
| 3 | `router-cwe798-ld-preload-sudo` | CWE-798 | SSH | PASS |
| 4 | `router-cwe798-vi-privilege-escalation` | CWE-798 | SSH | PASS |
| 5 | `router-cwe078-writable-root-cron` | CWE-78 | console seriale + cron | PASS |
| 6 | `router-cwe287-ssh-hardcoded-backdoor` | CWE-287 | SSH | PASS |
| 7 | `router-cwe089-http-sqli-auth` | CWE-89 | dashboard HTTP | PASS |
| 8 | `router-cwe078-bash-command-injection` | CWE-78 | dashboard HTTP | PASS |
| 9 | `router-cwe077-c-command-injection` | CWE-77 | dashboard HTTP | PASS |
| 10 | `router-cwe416-use-after-free` | CWE-416 | dashboard HTTP | PASS |
| 11 | `router-cwe400-diagnostic-dos` | CWE-400 | dashboard HTTP | PASS |
| 12 | `router-cwe078-service-interface-injection` | CWE-78 | TCP :9090 | PASS |
| 13 | `router-cwe022-path-traversal` | CWE-22 | HTTP | PASS |
| 14 | `ipcamera-cwe022-recording-path-traversal` | CWE-22 | HTTP CGI | PASS |
| 15 | `smartplug-cwe862-missing-authorization` | CWE-862 | MQTT :1883 | PASS |
| 16 | `thermostat-cwe294-command-replay` | CWE-294 | MQTT :1883 | PASS |
| 17 | `smartbulb-cwe122-zcl-heap-overflow` | CWE-122 | TCP ZCL :17754 | PASS |
| 18 | `smarthub-cwe121-database-stack-overflow` | CWE-121 | HTTP CGI :8080 | PASS (dopo fix, vedi sotto) |
| 19 | `envsensor-cwe306-unauthenticated-calibration` | CWE-306 | MQTT :1883 | PASS |
| 20 | `smartspeaker-cwe122-id3-heap-overflow` | CWE-122 | TCP media :18000 | PASS |
| 21 | `healthmonitor-cwe200-memory-disclosure` | CWE-200 | TCP :2575 | PASS |
| 22 | `doorlock-cwe294-unlock-replay` | CWE-294 | MQTT :1883 | PASS |
| 23 | `plc-cwe121-modbus-stack-overflow` | CWE-121 | Modbus/TCP :1502 | PASS |

## Nota di correzione

Per lo scenario #13 (`router-cwe022-path-traversal`) il payload documentato
usava quattro segmenti `..`, insufficienti a risalire da
`/var/lib/router-dashboard/reports/` fino alla radice: con il prefisso
`/missing/` servono **cinque** `%252e%252e`. Il firmware è corretto; è stato
aggiornato il payload in [../francesco-payloads.md](../francesco-payloads.md).

Per lo scenario #18 (`smarthub-cwe121-database-stack-overflow`) l'exploit
restituiva HTTP 500 invece del segnale `STACK_OVERFLOW`: il modulo era compilato
con `${CFLAGS}` di Yocto (`-D_FORTIFY_SOURCE=2`), che trasforma `strcpy` in
`__strcpy_chk` e fa abortire il processo (SIGABRT) prima di produrre l'output.
Fix: `-U_FORTIFY_SOURCE -D_FORTIFY_SOURCE=0` nel `do_compile` del recipe
`cwe121-smarthub-stack-overflow_1.0.bb`, più un campo `guard[32]` nella struct
`request_frame` perché il terminatore NUL della copia non raggiunga i registri
salvati. Verificato end-to-end: HTTP 200 con `STACK_OVERFLOW authorization=admin`.
Il modulo gemello `cwe121-plc-modbus-stack-overflow` (#23) usa lo stesso schema
di compilazione ma **non** presenta il difetto: l'exploit ha restituito
`STACK_OVERFLOW` senza fix. La differenza è che il suo overflow usa `memcpy` con
un object-size che copre l'intera struct (`data[32]` + `safety_state[4]` = 36) e
la copia resta entro quei 36 byte, quindi `__memcpy_chk` non aborta; lo smarthub
invece usava `strcpy` oltre la dimensione del singolo membro `bucket[64]`.

## Identità degli artefatti

SHA-256 calcolati alla registrazione sul file rootfs esportato
(`deploy-images/<id>/qemuarm64/iotbench-<id>-qemuarm64.rootfs.ext4.zst`).
Baseline Git della sessione: `2431fef326da640ce7bf3d60d11fcb83f3210447`
(con modifiche locali e artefatti non tracciati; non è un attestato di build
riproducibile bit-per-bit).

| Firmware | SHA-256 (rootfs.ext4.zst) |
| --- | --- |
| `router-cwe276-leaked-private-key` | `ca010f28d168dba8c5abf0830506889e32b34ddb2b7134628c4492eb4c1eeefe` |
| `router-cwe276-bad-chown-rights` | `c78a2e15589205da0cdee59b4453e6c6ef48542550eb6e897444300957080b7a` |
| `router-cwe798-ld-preload-sudo` | `41a438731f9d696b0099fc6727d19ddda77abde60e62d3116fe1d01334a2d006` |
| `router-cwe798-vi-privilege-escalation` | `10fcc58f7e70acedfb8c7c54cb1afc1c95a121951a5875b04403a56065fb6d75` |
| `router-cwe078-writable-root-cron` | `a1dc81b06f8699a252137959ac3c0cfb11edd9bd1dddcfdf9a1a0927a3013e47` |
| `router-cwe287-ssh-hardcoded-backdoor` | `63a37ba1344606820188c03ef5ee03d644687e8dd75d582409d6e55261c06b42` |
| `router-cwe089-http-sqli-auth` | `5af020aba79bacf717c99c2c8382ec9fc3a3eac5653111cca52f5f1bbf691c20` |
| `router-cwe078-bash-command-injection` | `b10a75c3599946c4e43e3dd168143e2f1c421f733ea5bc496f590a886961f75f` |
| `router-cwe077-c-command-injection` | `176707ab7ee4d14646cddb06367d306710c98c65357a00139086848a8536c457` |
| `router-cwe416-use-after-free` | `b74ac59a05a820365f5a2b1fd306d4b3e4d228332b2f91dafe1817c9291d636a` |
| `router-cwe400-diagnostic-dos` | `e7fdd5f781835c77fa8feb7c03418272c35206daaf37fc5972bae772620d3a89` |
| `router-cwe078-service-interface-injection` | `2d71647458bf571ec77ba010bb8a272fdf68b5ec05fe87390ce4c0711330bcc7` |
| `router-cwe022-path-traversal` | `e817fa2b728d71c2b53b61cd592d4e1694459deb148dbbbc8aa9e4ee85fcf5d1` |
| `ipcamera-cwe022-recording-path-traversal` | `2d3f8c843c18ba94ccabafd9e9e4a07df7b8dda4a7a2411eb852641f55e255ef` |
| `smartplug-cwe862-missing-authorization` | `75816a1dbc5aa33b26756a2dcc5fe118bfc5b30450056c54931faeda1288eb2a` |
| `thermostat-cwe294-command-replay` | `e49eed14cd40baaa8d4249e8ed6a08ba5b2acc9480fee173feec1e47c4d89e86` |
| `smartbulb-cwe122-zcl-heap-overflow` | `c5384e7b792c52491db667d7aaf117912a1902c742fce7beed63ecfca10b4fb5` |
| `smarthub-cwe121-database-stack-overflow` (post-fix) | `8bf938dd0e00b19c080dfb1f63c000f77c4a2580bbc460797b6703edff28ee08` |
| `envsensor-cwe306-unauthenticated-calibration` | `7f49ad02c6eb84fc6d48b51e1e67a6969a53f85689237a25af676752c1a8fccb` |
| `smartspeaker-cwe122-id3-heap-overflow` | `27e8e3499870fcb9c0f6d36c22da7e9a8e13d8d89c9a921e4671426dacc2f141` |
| `healthmonitor-cwe200-memory-disclosure` | `423c97e3411a2e0f185f2f7d39b6167407f2c7357ae51e9f704c53ab2e597fa4` |
| `doorlock-cwe294-unlock-replay` | `7e951c9d128134815356c4c9a4a0ac2c924466a34ee805db587623b4402dbc0f` |
| `plc-cwe121-modbus-stack-overflow` | `934ff9502422feced7848598255a92abdc2095726f4513c64b40624895e1adf8` |

Questo documento viene aggiornato a ogni firmware validato in sessione.
