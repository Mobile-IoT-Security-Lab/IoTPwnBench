# Vulnerable Java JARs — SQL Injection (CWE-89)

> INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT

Each existing device profile has a separate `<device>-cwe089-java-sql-injection`
image. Its sole vulnerability package is `cwe089-java-sql-injection`. The common
image, device profile, native services, simulated peripherals, build selector,
export layout and QEMU launcher retain their existing roles.

The canonical entry point is a local Java command in the guest serial console.
All database records are fake. The `internal` row is simply the extra record
outside the ordinary named lookup, not a separate authentication scenario.

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

1. `main()` validates the argument count before reading `args[0]`, and accepts
   one string of 1–240 Java characters.
2. `String input = args[0]` receives user-controlled input.
3. Direct string concatenation constructs
   `SELECT record_name, record_value FROM fixture_records WHERE record_name = '`
   plus `input` plus `' ORDER BY id;`.
4. `DriverManager.getConnection()` opens the fixed packaged SQLite database
   through JDBC, with URI `mode=ro&immutable=1` and `open_mode=1`
   (`SQLITE_OPEN_READONLY`). It verifies `connection.isReadOnly()` before
   executing the query. Extension loading is disabled.
5. `Statement.executeQuery(query)` executes that constructed SQL. There is no
   parameter binding, quote escaping or predicate filtering.
6. `ResultSet.getString()` returns the matched synthetic names and values.

The complete expected finding is **Java JAR + user-controlled input + SQL
string concatenation + missing parameter binding + JDBC query execution +
SQL Injection**, **CWE-89**. The concatenation and JDBC execution both exist in
the installed `org/iotbench/fixture/FixtureDbQuery.class` bytecode. Java may
compile string concatenation to `invokedynamic` / `StringConcatFactory`.
The installed matching source and `ground-truth.json` aid source/bytecode tools.

Normal `public` makes the predicate `record_name = 'public'`, selecting only row
1. Input `public' OR '1'='1` makes it
`record_name = 'public' OR '1'='1'`, selecting both rows. The intentionally
vulnerable query remains unchanged in the firmware. Shell and Python files
are test infrastructure; the ordinary JNI driver is the database dependency.

The utility has no network interface, shell invocation, elevated permissions,
runtime database creation or input-controlled database path. Query results
are capped at sixteen rows and the JDBC query timeout is two seconds.
Successful queries, including no matches, exit 0; SQL/configuration failures
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
beside each export. It requires host QEMU and `zstd`.

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
`WHERE record_name = ? ORDER BY id`, call `connection.prepareStatement(query)`,
bind `stmt.setString(1, input)`, then call `stmt.executeQuery()` with no SQL
argument. The crafted string becomes a value and returns no rows; ordinary
`public` still returns only the public row. Preserve read-only mode and ordinary
permissions. The actual fixture intentionally retains the vulnerable query.

## Completed validation

On 2026-10-16, all eleven `qemuarm64` images built and exported successfully
after a clean layer parse and dependency dry run. Each exported manifest
contains exactly one vulnerability package, `cwe089-java-sql-injection`, plus
OpenJDK 17, the pinned JDBC package and target SQLite library.

Offline checks passed for all eleven compressed ext4 images: actual Java 17
bytecode and JDBC/query references, executable manifest, fixed read-only
configuration, target runtime/JNI, exact matching source/assets, file modes,
synthetic database integrity/records and login warning. Every image contains
the same JAR (SHA-256
`5050383bf66dea9760abe3bf7b706edf3121e7237e3592e4f5e5265294e63817`)
and database (SHA-256
`4b3f4330fe7cae2725831a28873be7377cb44b5a9fa3c6b96603667a444af66a`).
Disassembly of the extracted application confirms argument-array access,
string concatenation, JDBC connection/read-only verification and
`Statement.executeQuery(String)` in the actual firmware bytecode.

All eleven devices booted in disposable QEMU snapshots with HVF/host CPU and
passed all five guest groups each, **55 groups total**. Every application
invocation ran as UID/GID 65534. Ordinary `public` returned only the public
record; the injected condition returned both synthetic records. Invalid
argument counts, empty/oversized input, malformed SQL and literal shell-shaped
input behaved as specified. Database bytes stayed unchanged, with no journal
sidecars. Existing device-service host-loopback ports were HTTP `18080`, MQTT
`21883` and Modbus `11502`; the Java fixture itself uses no network.

The host JVM regression also passed, including a temporary corrected
`PreparedStatement` control that preserved ordinary lookup and returned no
rows for the injected string. The actual firmware remains vulnerable.

The [local validation report](../deploy-images/java-sql-injection-qemuarm64-validation.txt)
records artifact/source hashes and the per-device guest groups. Aggregate
logs and extracted bytecode disassembly are under
`deploy-images/java-sql-injection-*`; each device export contains
`rootfs.manifest` and `validation-console.log`. Other architectures were not
built or boot-tested. No external static-analysis engine was run; CWE-89 is
the expected ground truth supported by the source, bytecode and reproduced
Java/JDBC behavior.
