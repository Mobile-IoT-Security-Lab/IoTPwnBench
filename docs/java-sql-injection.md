# Vulnerable Java JARs — SQL Injection (CWE-89)

> INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT

Each existing device profile has a separate `<device>-cwe089-java-sql-injection`
image. Its sole vulnerability package is `cwe089-java-sql-injection`. The common
image, device profile, native services, simulated peripherals, build selector,
export layout and QEMU launcher retain their existing roles.

The **Configuration Lookup** dashboard panel models a public configuration
search backed by a Java firmware service. The same operation remains available
as a local Java command. Normal searches enforce `visibility = 'public'`, so
even a direct search for `internal` returns no rows. SQL injection bypasses
that visibility predicate and exposes the synthetic internal row. This is an
application filtering boundary, not an OS permission or account-authentication
scenario. All records are fake; no vendor firmware or CVE is claimed.

The deployment model is a Linux management stack, matching IoTBench's QEMU
firmware architecture. For small-device profiles this represents the simulated
Linux management/controller variant; it does not reproduce an MCU-only bulb,
sensor or lock running a vendor's native software. The realistic element is
the HTTP-to-Java/JDBC input flow and the actual SQL visibility-filter bypass.

| Device | Firmware id |
| --- | --- |
| doorlock | `doorlock-cwe089-java-sql-injection` |
| envsensor | `envsensor-cwe089-java-sql-injection` |
| healthmonitor | `healthmonitor-cwe089-java-sql-injection` |
| ipcamera | `ipcamera-cwe089-java-sql-injection` |
| plc | `plc-cwe089-java-sql-injection` |
| router | `router-cwe089-java-sql-injection` |
| smartbulb | `smartbulb-cwe089-java-sql-injection` |
| smarthub | `smarthub-cwe089-java-sql-injection` |
| smartplug | `smartplug-cwe089-java-sql-injection` |
| smartspeaker | `smartspeaker-cwe089-java-sql-injection` |
| thermostat | `thermostat-cwe089-java-sql-injection` |

## Source-to-sink ground truth

The implementation is
[`FixtureDbQuery.java`](../meta-iotbench/recipes-vulns/cwe089-java-sql-injection/files/FixtureDbQuery.java),
compiled with debug information and packaged as a Java 17 executable JAR.

1. CLI `main()` validates the argument count before reading `args[0]`.
   The web backend accepts a UTF-8 POST body at its fixed `/lookup` endpoint.
   Both paths enforce one string of 1–240 Java characters.
2. CLI `String input = args[0]` or the HTTP body reaches the shared
   `FixtureDbQuery.lookup(input)` operation.
3. Direct string concatenation constructs
   `SELECT record_name, record_value FROM fixture_records WHERE visibility = 'public' AND record_name = '`
   plus `input` plus `' ORDER BY id;`.
4. `DriverManager.getConnection()` opens the fixed packaged SQLite database
   through JDBC, with URI `mode=ro&immutable=1` and `open_mode=1`
   (`SQLITE_OPEN_READONLY`). It verifies `connection.isReadOnly()` before
   executing the query. Extension loading is disabled.
5. `Statement.executeQuery(query)` executes that constructed SQL. There is no
   parameter binding, quote escaping or filtering of SQL syntax in the input.
6. `ResultSet.getString()` returns the matched synthetic names and values.

The complete expected finding is **Java JAR + user-controlled input + SQL
string concatenation + missing parameter binding + JDBC query execution +
SQL Injection**, **CWE-89**. The concatenation and JDBC execution both exist in
the installed `org/iotbench/fixture/FixtureDbQuery.class` bytecode. Java may
compile string concatenation to `invokedynamic` / `StringConcatFactory`.
The installed matching source and `ground-truth.json` aid source/bytecode tools.

Normal `public` selects only row 1, and `internal` selects no rows because of
the public-visibility filter. Input `public' OR '1'='1` makes the predicate
`visibility = 'public' AND record_name = 'public' OR '1'='1'`, selecting both
rows. SQL's AND/OR precedence makes the injected OR bypass both conditions.
The shipped query deliberately retains string concatenation. Shell and Python files
are test infrastructure; the ordinary JNI driver is the database dependency.

The CLI has no network interface. The Java web backend uses the JDK's
[`jdk.httpserver`](https://docs.oracle.com/en/java/javase/17/docs/api/jdk.httpserver/module-summary.html)
module inside the same application JAR. The dashboard forwards raw input over
a fixed guest-loopback URL; it never constructs SQL or runs a shell/process.
Both interfaces avoid elevated permissions, runtime database creation and
input-controlled database paths. Query results
are capped at sixteen rows and the JDBC query timeout is two seconds.
In the CLI, successful queries, including no matches, exit 0; SQL/configuration failures
exit 1; invalid argument counts or lengths exit 2. The warning goes to stderr
on every invocation; record results go to stdout.

## Filesystem and database

| Firmware path | Role / permissions |
| --- | --- |
| `/usr/share/iotbench/java-sql-injection/fixture-db-query.jar` | Executable application JAR, root:root `0644` |
| `/usr/share/iotbench/java-sql-injection/fixture.db` | Synthetic SQLite database, root:root `0444` |
| `/usr/share/iotbench/java-sql-injection/FixtureDbQuery.java` | Matching Java source, root:root `0644` |
| Same directory: `schema.sql`, `ground-truth.json`, `NOTICE`, `LICENSE`, `test-guest.sh` | Supporting assets, root:root `0644` |
| `/usr/share/java/iotbench-sqlite-jdbc.jar` | Pinned JDBC classes; manifest Class-Path resolves here |
| `/usr/lib/libsqlitejdbc.so` | Yocto cross-built Xerial JNI library linked to target SQLite |
| `/usr/lib/jvm/` and `/usr/bin/java` | OpenJDK runtime and its launcher link |
| Same application JAR: `org.iotbench.fixture.FixtureWebService` | Loopback HTTP entry point sharing `FixtureDbQuery.lookup()` |
| `/usr/share/iotbench/java-sql-injection/FixtureWebService.java` | Matching backend source |
| `/usr/share/router-dashboard/modules/java-configuration-lookup/module.php` | Thin dashboard adapter, no SQL or process execution |
| `/usr/lib/systemd/system/iotbench-java-sql.service` | Automatically enabled backend service, UID/GID 990 (`javafixture`) |

Paths above use the repository's default `datadir` and `libdir`. Recipes render
these variables into the packaged configuration and test assets. The database
URL and native-library path come only from `fixture.properties` inside the JAR.

`sqlite3-native` creates the database at build time from the ordered schema.
Its only table is `fixture_records(id INTEGER PRIMARY KEY, record_name TEXT
NOT NULL UNIQUE, record_value TEXT NOT NULL, visibility TEXT NOT NULL)` with a
visibility CHECK constraint. Exact rows:

| id | record_name | record_value | visibility |
| --- | --- | --- | --- |
| 1 | public | SYNTHETIC_PUBLIC_FIXTURE_DATA | public |
| 2 | internal | SYNTHETIC_INTERNAL_FIXTURE_DATA | internal |

No credentials or production information are used. Read-only JDBC flags apply
even when the caller is root; database file permissions additionally permit
ordinary unprivileged reads. No journal or persistent state is needed.

The Java service listens only on guest `127.0.0.1:18089`, with bounded request
bodies, connections, workers and request/response timeouts. Its systemd unit
uses a locked account, `NoNewPrivileges`, an empty capability set, a read-only
system view, protected homes and private temporary/device namespaces. The JVM
runs in this separate service because it requires executable memory; Lighttpd's
existing `MemoryDenyWriteExecute` and other hardening are retained. There is
no new host port forward. The backend is an internal application endpoint;
the public HTTP entry is the existing management dashboard with its existing
request-token checks. No extra authentication vulnerability is introduced.

## Java dependencies and reproducibility

The repository previously had no Java runtime, JAR recipes, Maven/Gradle project
layout or JDBC package. The fixture follows its existing local-source recipe
pattern under `recipes-vulns/`; no standalone project is introduced.

`Dockerfile` pins the wrynose
[`meta-openjdk`](https://github.com/amarula/meta-openjdk/tree/0fefb16cf99e687a53ae5e36a163af962dd64e9f)
layer to commit `0fefb16cf99e687a53ae5e36a163af962dd64e9f`, and Compose enables it.
The IoTBench layer selects OpenJDK 17 for both the target runtime and native
compiler. Small bbappends select the server JVM (Zero on MIPS), support the
aarch64 bootstrap archive alongside upstream x86_64, and correct upstream's
SQLite license-expression separator. The JDK is cross-built by Yocto, rather
than copying a host runtime into firmware. The first Java image therefore
requires substantial extra downloads and compilation; later devices reuse it.

The platform recipe `iotbench-sqlite-jdbc_3.53.4.0.bb` fetches the official
[Xerial release](https://github.com/xerial/sqlite-jdbc/tree/3.53.4.0) source and
published Maven JAR, pinning source commit
`cab7981c19ce04d691f0675f0b2586afc2bbf803` and the JAR's SHA-256. It removes all bundled foreign
native binaries from the JAR, generates matching JNI headers with the native
JDK, and compiles upstream `NativeDB.c` using `${CC}`, target flags and the
existing target `sqlite3`. The driver requires no Maven execution or downloaded
runtime dependencies. Its optional SLF4J integration falls back to JDK logging.
The firmware installs the dependency's Apache/BSD licenses separately.

The application uses plain `javac --release 17 -g -Xlint:all -Werror`.
Both packaged JARs have fixed ZIP timestamps and sorted entries. The database
is recreated from scratch for each build. No compiler/build tool is required
in the guest; all dependencies are available offline after building.

## Build and manual verification

Rebuild an existing export to add the web panel and backend service. After
booting, open `http://127.0.0.1:8080` (or the port set by `QEMU_HTTP_PORT`) in
the host browser. In **Configuration Lookup**, submit `public`, then `internal`,
then `public' OR '1'='1` using **Search configuration**. Expected results are
respectively the public row, no records, and both public/internal rows. Do not
add surrounding shell double quotes in the form field. See the root README's
**Manual browser test** for the Apple Silicon boot command and output table.

From the host repository root, rebuild the builder once to add the pinned layer:

```bash
docker compose build yocto
docker compose run --rm yocto bash -lc \
  'source /opt/yocto/yocto-env.sh && bitbake -p && bitbake -n iotbench-router-cwe089-java-sql-injection'
FIRMWARE=router-cwe089-java-sql-injection docker compose run --rm yocto
FIRMWARE=router-cwe089-java-sql-injection ./scripts/run-qemu.sh
```

Log into the guest serial console with the existing lab `root` / `routeradmin`
credentials. Run inside the guest:

```sh
java -Xmx32m -jar /usr/share/iotbench/java-sql-injection/fixture-db-query.jar public
java -Xmx32m -jar /usr/share/iotbench/java-sql-injection/fixture-db-query.jar "public' OR '1'='1"
```

The first command prints only `public|SYNTHETIC_PUBLIC_FIXTURE_DATA`. The second
prints that line followed by `internal|SYNTHETIC_INTERNAL_FIXTURE_DATA`.
Both return 0 and print the fixture warning on stderr. Ordinary missing-record
input prints no records. The same commands work without root privileges:

```sh
setpriv --reuid=65534 --regid=65534 --clear-groups \
  java -Xmx32m -jar /usr/share/iotbench/java-sql-injection/fixture-db-query.jar "public' OR '1'='1"
sh /usr/share/iotbench/java-sql-injection/test-guest.sh router
```

The regression prints five `PASS` lines, including exact normal/injected
results, bad argument counts, empty/oversized input, malformed SQL, unchanged
database bytes and absent journal sidecars. Every Java invocation runs as UID
65534. Close disposable QEMU with Ctrl-A, then X.

Build every device through the existing export procedure:

```bash
for recipe in meta-iotbench/recipes-images/iotbench-*-cwe089-java-sql-injection.bb; do
    firmware=$(basename "$recipe" .bb)
    FIRMWARE="${firmware#iotbench-}" docker compose run --rm yocto || exit 1
done
```

Exports land in `deploy-images/<device>-cwe089-java-sql-injection/<machine>/`.
The default is `qemuarm64`. `scripts/build-all.sh` discovers these images
automatically. `YOCTO_MACHINE` continues to select the toolchain and runtime;
only machines actually built and booted are claimed as validated below.

## Automated checks

Run separately from a manually running QEMU guest:

```bash
python3 scripts/test-java-sql-injection.py --device router
python3 scripts/test-java-sql-injection.py --all
# Optional Apple Silicon acceleration and alternative existing service ports:
QEMU_ACCEL=hvf QEMU_CPU=host QEMU_HTTP_PORT=18080 \
  QEMU_MQTT_PORT=21883 QEMU_MODBUS_PORT=11502 \
  python3 scripts/test-java-sql-injection.py --all
```

The host runner boots disposable snapshots through the existing launcher,
checks all five guest groups, closes QEMU and saves `validation-console.log`
beside each export. It also exercises the actual dashboard HTTP action and
loopback Java backend: normal lookup, direct `internal` denial, injected
visibility bypass, malformed inputs, CSRF rejection, private-asset denial,
service UID, loopback binding, unchanged database and Lighttpd sandbox.
The runner decompresses its disk into a temporary directory to avoid touching
disks used by manual guests. It requires host QEMU and `zstd`.

Offline firmware inspection uses `debugfs` without mounting or running firmware:

```bash
docker compose run --rm yocto python3 /scripts/test-java-sql-injection.py \
  --debugfs /workdir/build/tmp/sysroots-components/aarch64/e2fsprogs-native/sbin/debugfs \
  --image /export/router-cwe089-java-sql-injection/qemuarm64/iotbench-router-cwe089-java-sql-injection-qemuarm64.rootfs.ext4.zst
```

Use `x86_64` instead of `aarch64` in the debugfs path on an x86_64 builder host.
The checker verifies the application class format and JDBC/query references,
manifest, fixed read-only configuration, matching source/assets, dependency
classes, target JNI/runtime ELF files, database contents, modes and warning.
This is structural ground-truth validation, not an external analyzer verdict.

A host-only functional check requires Java 17 or newer, `javac`, and an explicit
copy of the official pinned JDBC JAR (its SHA-256 is checked):

```bash
python3 scripts/test-java-sql-injection.py --local --jdbc-jar /path/to/sqlite-jdbc-3.53.4.0.jar
```

It compiles an executable JAR in a temporary directory, exercises the actual
Java/JDBC path, and builds a temporary parameterized control. Normal input
works in both; injected input returns the internal row only in the vulnerable
JAR. The database stays unchanged. This host test supplements guest validation.

## Remediation

In a separate corrected variant, use a constant query ending in
`WHERE visibility = 'public' AND record_name = ? ORDER BY id`, call `connection.prepareStatement(query)`,
bind `stmt.setString(1, input)`, then call `stmt.executeQuery()` with no SQL
argument. The crafted string becomes a value and returns no rows; ordinary
`public` still returns only the public row. Preserve read-only mode and ordinary
permissions. The actual fixture intentionally retains the vulnerable query.

## Validation artifacts

The offline checker verifies both Java classes, exact installed Java/PHP sources,
service definition, fixed database configuration, dependency JAR/JNI/runtime,
synthetic database contents, file modes and warning. Runtime testing uses
isolated temporary disks and existing dashboard HTTP forwarding; it records
`validation-console.log` and the actual API requests/responses in
`validation-web.json` beside each device export.

The web revision is validated independently of the earlier CLI-only revision.
Current aggregate evidence is stored under `deploy-images/java-sql-injection-web-*`.
Only architectures actually built and booted are claimed as validated.
