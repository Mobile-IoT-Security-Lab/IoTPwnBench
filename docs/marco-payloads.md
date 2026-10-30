# Marco Payloads

Operational guide to **14 catalog tests**, plus the embedded-credentials extra.
Start with local checks, then build and verify a router image before repeating
the procedure for other devices. Numbering follows Marco's catalog assignments.

<a id="how-to-use-this-guide"></a>
<a id="common-setup"></a>

## SETUP

### Environment and prerequisites

Run host commands from the repository root, beside `compose.yaml` and `scripts/`,
as an ordinary Linux user. **Guest** commands run in QEMU's serial console.

`python3` must resolve to **Python 3.9+**. If necessary, replace it in host
commands with the absolute path of a compatible interpreter.

```bash
python3 --version
```

| Checks | Additional requirements |
| --- | --- |
| SSH parser | Native OpenSSH `sshd` and `ssh-keygen` |
| Native C fixtures | C compiler, Make, binutils; matching ASan/UBSan runtimes for diagnostics |
| Connection string | SQLite development headers/library |
| REST and C path | Linux 5.6+ with `openat2`; Unix sockets allowed |
| Isolated runners | util-linux, working user/mount/PID/network namespaces; `ldd` for copied runtimes |
| Telnet packet capture | `ip` from iproute2; packet capture allowed inside the test namespace |
| Apache | Apache 2.4 with CGI modules; native Chrome/Chromium and fonts for XSS/CSRF |
| Java | Local JDK 17+ with `java` and `javac` |
| Firmware builds | Docker daemon access and Docker Compose |
| Automated FTP/QEMU console | Python `pexpect` and a native or Docker QEMU backend |
| Filesystem inspection | `zstd` and `debugfs` from e2fsprogs |

For namespace-based runners, check support before testing:

```bash
unshare --user --map-root-user --mount --pid --fork --net /bin/true
echo "exit=$?"
```

An error requires a suitable Linux environment; running the host suite as root
is not a substitute. This probe does not cover every operation used by a runner.

For Java tests, set the installed JDK directory:

```bash
IOTBENCH_JDK=/path/to/jdk-17
"$IOTBENCH_JDK/bin/java" -version
"$IOTBENCH_JDK/bin/javac" -version
```

### Results and scope

Run one block at a time and check `echo "exit=$?"` immediately after each test.
**PASS/OK + exit 0** confirms the checks that ran; **SKIP** is incomplete coverage;
**FAIL/ERROR** requires investigation. Expected failures inside a runner are
assessed by its final result.

Record local tests, firmware builds and firmware verification separately, per
device and variant. A passing fixture test confirms the intended weakness and
its controls. Dashboard availability alone does not verify the weakness.
Keep logs, artifact hashes and skipped checks with the validation record.
This guide describes procedures, not a claim that every image was tested.

<a id="device-keywords"></a>

### Devices

All tests support these eleven keywords:

`router`, `ipcamera`, `smartplug`, `thermostat`, `plc`, `smartbulb`, `smarthub`,
`envsensor`, `smartspeaker`, `healthmonitor`, `doorlock`.

<a id="build-and-boot-any-device"></a>

### Build and boot

For the firmware phase, prepare the builder once and keep the same machine for
build and boot. Examples reuse these variables in the same shell:

```bash
TEST_DEVICE=router
export YOCTO_MACHINE=qemuarm64
docker compose build yocto
echo "builder_exit=$?"
```

Each test sets `TEST_FIRMWARE=<device>-<scenario>` and supplies its required
opt-in. Do not enable several fixture families together. Exports are under
`deploy-images/<firmware>/<machine>/`.

After a successful build, choose **one** manual boot method:

```bash
# Docker: reuse QEMU from the yocto-build volume populated by the build.
FIRMWARE="$TEST_FIRMWARE" QEMU_HTTP_PORT=18080 ./scripts/run-qemu-docker.sh
```

```bash
# Native: matching QEMU and zstd must be installed on the host.
FIRMWARE="$TEST_FIRMWARE" QEMU_HTTP_PORT=18080 ./scripts/run-qemu.sh
```

Run one firmware at a time. The standard serial-console login is `root` /
`routeradmin`; embedded-auth images lock root and use offline inspection instead.
Exit QEMU with **Ctrl-A**, release, then **X**. Default guest writes are disposable.

When the image exposes its device dashboard, open `http://127.0.0.1:18080/`.
For a remote host, forward that port to your workstation first. Apache, native
path/buffer/connection/symlink and Java fixtures are serial-only and have no
dashboard or forwarded network port.

<a id="inspect-the-generated-firmware"></a>

### Inspect an exported filesystem

For tests using `--rootfs`, extract the selected `TEST_FIRMWARE` without booting:

```bash
TEST_INSPECT=$(mktemp -d /tmp/iotbench-inspect.XXXXXX) &&
mkdir "$TEST_INSPECT/rootfs" &&
zstd -dc "deploy-images/$TEST_FIRMWARE/$YOCTO_MACHINE/iotbench-$TEST_FIRMWARE-$YOCTO_MACHINE.rootfs.ext4.zst" \
  > "$TEST_INSPECT/image.ext4" &&
LC_ALL=C debugfs -R "rdump / $TEST_INSPECT/rootfs" "$TEST_INSPECT/image.ext4" \
  > "$TEST_INSPECT/extraction.log" 2>&1
echo "extract_exit=$?"

grep -vE '^(debugfs [0-9]|(dump_file|rdump): Operation not permitted while changing ownership of )' \
  "$TEST_INSPECT/extraction.log"
```

If `debugfs` is outside `PATH`, use its installed path, commonly
`/usr/sbin/debugfs`. Expect exit 0 and no remaining diagnostics. Ownership-only
warnings are possible as a normal user; original ownership is not verified by
that extracted copy. Other errors must be resolved before testing the rootfs.
Use only this temporary tree for `--rootfs`, never the host's `/`.

<a id="manual-test-index"></a>

### Test index

Variants are separate scenarios per device, not additional devices.

| Test | Catalog no. | Variants | Subject |
| --- | --- | --- | --- |
| [Test 1](#test-1) | 2 | 1 | SSH empty-password policy |
| [Test 2](#test-2) | 6 | 1 | FTP write permissions |
| [Test 3](#test-3) | 9 | 1 | Telnet plaintext traffic |
| [Test 4](#test-4) | 12 | 1 | Sudo environment |
| [Test 5](#test-5) | 15 | 1 | Cron wildcard injection |
| [Test 6](#test-6) | 18 | 15 | Password leak |
| [Test 7](#test-7) | 21 | 1 | REST internal files |
| [Test 8](#test-8) | 24 | 10 | Apache web applications |
| [Test 9](#test-9) | 28 | 2 | C path and filename validation |
| [Test 10](#test-10) | 30 | 1 | C buffer overflow |
| [Test 11](#test-11) | 33 | 1 | C connection string injection |
| [Test 12](#test-12) | 36 | 1 | C symbolic links |
| [Test 13](#test-13) | 39 | 2 | Java command injection |
| [Test 14](#test-14) | 42 | 1 | Java deserialization |
| [Extra](#extra-embedded) | — | 8 | Embedded credential pairs |

<a id="technical-references"></a>

The catalog is [Catalogo_Test_Sicurezza_Firmware_IoT.xlsm](../Catalogo_Test_Sicurezza_Firmware_IoT.xlsm).
Execution evidence belongs in [validation records](validation/).

<a id="weakly-configured-ssh--empty-password-authentication-permitted-cwe-521"></a>
<a id="test-1"></a>

## Test 1: SSH empty-password policy — CWE-521

**Purpose:** detect a weak SSH configuration and distinguish its corrected copy.
The installed `/etc/ssh/sshd_config` contains:

```text
PermitEmptyPasswords yes
PasswordAuthentication yes
PermitRootLogin no
```

**Host test:**

```bash
python3 scripts/test-ssh-empty-passwords.py
echo "exit=$?"
```

Expected: policy/isolation and eleven-device source checks pass; OpenSSH
`-t/-T` accepts both configurations and reports `permitemptypasswords yes` for
the positive case and `no` for the control. The other two directives stay
unchanged. Duplicate directives, `Include`, `Match` and unrelated policy changes
are rejected by the fixture validator.

Use `--sshd /path/to/sshd` to select the native parser. `--skip-openssh` runs
only portable checks and must be recorded as skipping parser validation.

**Firmware build:**

```bash
TEST_FIRMWARE="$TEST_DEVICE-cwe521-permit-empty-passwords"
FIRMWARE="$TEST_FIRMWARE" docker compose run --rm yocto
echo "build_exit=$?"
```

Extract it using the setup procedure, then run on the host:

```bash
python3 scripts/test-ssh-empty-passwords.py --rootfs "$TEST_INSPECT/rootfs"
echo "exit=$?"
```

Expected: installed policy and native parser checks pass; the rootfs validator
finds no known SSH server/startup entries or empty password fields.
**No SSH server or empty-password account is installed. A successful SSH login
is neither expected nor required.** Boot is optional for this policy test.

Source: [cwe521-permit-empty-passwords](../meta-iotbench/recipes-vulns/cwe521-permit-empty-passwords/).
References: [OpenSSH option](https://man.openbsd.org/sshd_config#PermitEmptyPasswords),
[CWE-521](https://cwe.mitre.org/data/definitions/521.html).

<a id="weakly-configured-vsftpd-bad-write-rights"></a>
<a id="test-2"></a>

## Test 2: FTP write permissions — CWE-276

**Purpose:** an authenticated maintenance user can upload where policy permits
only listing/download. Account: `ftpfixture` / `Fixture-FTP-Only-42`, synthetic
test credentials. Both directories are owned by `root:ftpfixture`:

| Operation | Expected result |
| --- | --- |
| `STOR bad/probe.txt`, directory mode `0775` | Upload succeeds: intended defect |
| Same upload in `control`, mode `0755` | Rejected |
| Upload after temporarily correcting `bad` to `0755` | Rejected |
| Anonymous, root or wrong-password login | Rejected |

**Host checks and build:**

```bash
python3 scripts/check-ftp-write-rights.py
echo "exit=$?"

TEST_FIRMWARE="$TEST_DEVICE-cwe276-bad-write-rights"
FIRMWARE="$TEST_FIRMWARE" docker compose run --rm \
  -e IOTBENCH_ENABLE_FTP_WRITE_FIXTURE=1 yocto
echo "build_exit=$?"
```

After a successful build:

```bash
python3 scripts/test-ftp-write-rights.py --device "$TEST_DEVICE"
echo "exit=$?"
```

The runner manages QEMU and saves `/tmp/iotbench-ftp-<device>-qemu.log`.
It selects native QEMU or Docker automatically; `--qemu-backend native|docker`
overrides selection. `--all --build` builds and tests all eleven devices.

For an already booted image, the equivalent **guest** command is:

```bash
python3 /usr/share/iotbench/bad-write-rights/test-guest.py --isolated-fixture
echo "exit=$?"
```

Expected: five PASS groups covering authentication, reads, uploads, boundaries
and permissions. FTP runs only during the test in a private network namespace;
its ports are not forwarded. vsftpd retains its privileged authentication/chroot
broker, while uploaded files belong to the unprivileged account. This test does
not demonstrate anonymous upload, root FTP access or command execution.

Source: [cwe276-bad-write-rights](../meta-iotbench/recipes-vulns/cwe276-bad-write-rights/).

<a id="weakly-configured-telnet--unencrypted-traffic-cwe-798287276"></a>
<a id="test-3"></a>

## Test 3: Telnet plaintext traffic — CWE-798/287/276

**Purpose:** observe a synthetic plaintext session with fixed credentials and
weak authentication policy. The expected pair is `telnet-fixture` /
`Fixture-Telnet-Only-42`. The weak policy also accepts another nonempty username
with that password; the strict username/password control rejects it.
The policy file is mode `0666`; the permission control changes it to `0644`.

**Host tests:**

```bash
python3 scripts/test-telnet-unencrypted-traffic.py --static
echo "exit=$?"
python3 scripts/test-telnet-unencrypted-traffic.py --local --isolated-fixture \
  --transcript /tmp/iotbench-telnet-wire.json
echo "exit=$?"
```

The JSON transcript is not a packet capture. For actual PCAP evidence:

```bash
unshare --user --map-root-user --net /bin/bash -c '
  ip link set lo up &&
  exec python3 scripts/test-telnet-unencrypted-traffic.py \
    --local --isolated-fixture --require-pcap \
    --pcap /tmp/iotbench-telnet-isolated.pcap \
    --transcript /tmp/iotbench-telnet-isolated-wire.json
'
echo "exit=$?"
```

Expected: synthetic credentials and commands are readable without decryption;
normal behavior and strict controls pass. The loopback-only run skips the
non-loopback interface check, which the ordinary local run covers.

**Firmware build:**

```bash
TEST_FIRMWARE="$TEST_DEVICE-cwe798-unencrypted-traffic"
FIRMWARE="$TEST_FIRMWARE" docker compose run --rm \
  -e IOTBENCH_ENABLE_TELNET_FIXTURE=1 yocto
echo "build_exit=$?"
```

Boot using setup, then run in the **guest**:

```bash
python3 /usr/share/iotbench/unencrypted-traffic/test-session.py \
  --installed --isolated-fixture --require-pcap \
  --pcap /tmp/iotbench-telnet.pcap --transcript /tmp/iotbench-telnet-wire.json
echo "exit=$?"
```

`STATUS`, `HELP` and `QUIT` return fixed responses. This is a synthetic service,
not an OS login daemon: other inputs cannot execute commands or start a shell.
No Telnet port is forwarded to the host.

Source: [cwe798-unencrypted-traffic](../meta-iotbench/recipes-vulns/cwe798-unencrypted-traffic/).

<a id="bad-sudo-rights--allow-changes-to-environment-variables-cwe-798"></a>
<a id="test-4"></a>

## Test 4: Sudo environment — CWE-798

**Purpose:** caller-controlled variables preserved by sudo change a privileged
diagnostic helper's behavior. The policy permits only
`sudo -n /usr/bin/fixture-sudo-env --fixture-test` for the locked `fixtureenv`
account; `env_keep` preserves these three inputs:

| Variable | Normal value | Diagnostic value |
| --- | --- | --- |
| `FIXTURE_MODE` | `status` | `diagnostic` |
| `FIXTURE_CONFIG` | `public` | `Fixture-Sudo-Only-42` |
| `TEST_PROFILE` | `baseline` | `boundary` |

**Host tests:**

```bash
python3 scripts/test-sudo-env-fixture.py --static
echo "exit=$?"
python3 scripts/test-sudo-env-fixture.py --local --isolated-fixture
echo "exit=$?"
```

Expected: normal output is `RESULT=nominal`; diagnostic inputs yield
`RESULT=synthetic-diagnostic`. Wrong credentials and invalid modes/profiles are
rejected. The local test exercises the helper; it does not prove real sudo
policy behavior or root execution.

**Firmware build:**

```bash
TEST_FIRMWARE="$TEST_DEVICE-cwe798-sudo-environment"
FIRMWARE="$TEST_FIRMWARE" docker compose run --rm \
  -e IOTBENCH_ENABLE_SUDO_ENV_FIXTURE=1 yocto
echo "build_exit=$?"
```

Boot, then test the actual sudo rule in the **guest**:

```bash
python3 /usr/share/iotbench/sudo-environment/test-session.py \
  --installed --isolated-fixture
echo "exit=$?"
```

Expected: the permitted diagnostic runs with `FIXTURE_EUID=0`, while unlisted
caller variables remain absent or are rejected. The synthetic credential is
hardcoded for CWE-798 analysis. `FIXTURE_CONFIG` is a fixed value, not a path;
the helper does not execute user commands, load libraries or read arbitrary files.

Source: [cwe798-sudo-environment](../meta-iotbench/recipes-vulns/cwe798-sudo-environment/).

<a id="cronjob-wildcard-injection-cwe-8878269"></a>
<a id="test-5"></a>

## Test 5: Cron wildcard injection — CWE-88/78/269

**Purpose:** a file named `--fixture-diagnostic` is interpreted as an option
when a maintenance command expands bare `*`. The corrected command uses
`--fixture-test -- *`, so the same filename remains an operand.

**Host test:**

```bash
python3 scripts/test-cron-wildcard-fixture.py --isolated-fixture
echo "exit=$?"
```

Expected: nominal input stays `nominal`; the option-like filename selects
`synthetic-diagnostic`; the corrected control stays `nominal`.

**Firmware build:**

```bash
TEST_FIRMWARE="$TEST_DEVICE-cwe088-cronjob-wildcard-injection"
FIRMWARE="$TEST_FIRMWARE" docker compose run --rm \
  -e IOTBENCH_BUILD_MODE=fixture \
  -e IOTBENCH_ENABLE_CRON_WILDCARD_FIXTURE=1 yocto
echo "build_exit=$?"
```

Boot a fresh snapshot, then run in the **guest**:

```bash
CRON_ROOT=/usr/share/iotbench/cronjob-wildcard-injection
python3 "$CRON_ROOT/fixture-runner.py" --isolated-fixture
echo "exit=$?"

touch "$CRON_ROOT/inbox/--fixture-diagnostic"
rm "$CRON_ROOT/logs/vulnerable.jsonl"
python3 "$CRON_ROOT/fixture-runner.py" --isolated-fixture
echo "exit=$?"
python3 "$CRON_ROOT/fixture-runner.py" --isolated-fixture --secure
echo "exit=$?"
```

The three runs should show nominal, diagnostic, then nominal behavior. Logs
must be fresh: the runner refuses to overwrite them. Reboot the disposable
snapshot before repeating. The schedule and privileged role are simulated;
nothing is installed in system cron and no privilege escalation is performed.

Source: [cwe088-cronjob-wildcard-injection](../meta-iotbench/recipes-vulns/cwe088-cronjob-wildcard-injection/).

<a id="password-leak--different-file-types-and-patterns-cwe-798"></a>
<a id="test-6"></a>

## Test 6: Password leak — CWE-798

**Purpose:** recover a synthetic credential from a file and verify that it is
used by the local authentication helper. Each image contains one variant.

| Variant | File | Field / representation |
| --- | --- | --- |
| `conf-password` | `auth.conf` | `password` |
| `cfg-admin` | `admin.cfg` | `admin_password` |
| `ini-root` | `account.ini` | `[auth] root_password` |
| `env-db` | `database.env` | `DB_PASSWORD` |
| `json-token` | `service.json` | `auth_token` |
| `xml-api` | `service.xml` | `api_key` |
| `shell-password` | `credentials.sh` | `PaSsWoRd` |
| `c-password` | `credential.c` | C `fixture_secret[]` |
| `header-password` | `credential.h` | C `fixture_secret[]` |
| `app-password` | `application.properties` | `service.auth.password` |
| `init-password` | `init-auth.sh` | `PASSWORD`; inert script |
| `log-password` | `authentication.log` | `password` |
| `kv-password` | `credentials.txt` | `Password` |
| `json-base64` | `encoded.json` | `auth_token_b64` |
| `env-base64` | `encoded.env` | `PASSWORD_B64` |

Exact synthetic values are in the
[inventory](../meta-iotbench/recipes-vulns/cwe798-password-leak/files/synthetic-inventory.json);
[expected findings](../meta-iotbench/recipes-vulns/cwe798-password-leak/files/expected-findings.json)
map source and installed locations. Base64 is encoding, not encryption.

**Host test — all 15 variants:**

```bash
python3 scripts/test-password-leak-fixture.py --isolated-fixture
echo "exit=$?"
```

Expected: all nine test groups pass, including credential recovery, accepted
correct values and rejected controls. Scripts are parsed as data, not executed.
C/header authentication is compiled in local tests; those firmware variants
ship source plus the Python authentication helper, not an extra credential ELF.

**Firmware build — example variant:**

```bash
TEST_FIRMWARE="$TEST_DEVICE-cwe798-password-leak-conf-password"
FIRMWARE="$TEST_FIRMWARE" docker compose run --rm \
  -e IOTBENCH_BUILD_MODE=fixture -e IOTBENCH_ENABLE_PASSWORD_LEAK_FIXTURE=1 yocto
echo "build_exit=$?"
```

Extract it using setup, then verify on the **host**:

```bash
python3 scripts/test-password-leak-fixture.py --isolated-fixture \
  --rootfs "$TEST_INSPECT/rootfs" --variant conf-password
echo "exit=$?"
```

To observe authentication in the booted **guest**:

```bash
AUTH_ROOT=/usr/share/iotbench/password-leak/conf-password
sed -n 's/^password=//p' "$AUTH_ROOT/auth.conf" | \
  python3 "$AUTH_ROOT/fixture-auth.py" --isolated-fixture
echo "correct_exit=$?"
printf '%s\n' wrong | python3 "$AUTH_ROOT/fixture-auth.py" --isolated-fixture
echo "wrong_exit=$?"
```

Expected: `accepted`/0, then `rejected`/1. That manual negative exit 1 is expected.
Repeat build and image verification for each selected variant; a local suite
covering all variants does not verify all generated images.

Source: [cwe798-password-leak](../meta-iotbench/recipes-vulns/cwe798-password-leak/).

<a id="exploitable-rest-interface--internal-files-cwe-22cwe-73"></a>
<a id="test-7"></a>

## Test 7: REST internal files — CWE-22/CWE-73

**Purpose:** the config route reads beyond its intended `fs/api` directory,
while remaining inside a dedicated synthetic filesystem. The interface is
HTTP over a private Unix socket, not a browser-accessible TCP service.

| Request | Vulnerable result | Corrected result |
| --- | --- | --- |
| `GET /api/config?file=config.cfg` | 200, synthetic config | Same |
| `GET /api/config?file=../restricted/marker.txt` | 200, `IOTBENCH_SYNTHETIC_REST_BOUNDARY_MARKER` | 403 |
| Same traversal, percent-encoded once | 200, same marker | 403 |
| `GET /api/status?file=status.cfg` | 200, status; traversal rejected | Same |
| `POST /api/config/read`, body `file=config.cfg` | 200, config; traversal rejected | Same |
| Escape beyond the synthetic root or follow a symlink | 403 | 403 |

**Host tests:**

```bash
python3 scripts/test-rest-fixture.py --isolated-fixture
echo "exit=$?"
python3 scripts/test-rest-fixture.py --isolated-fixture --sanitize
echo "exit=$?"
```

Expected: eight test groups pass, including normal requests, traversal and
corrected controls. Linux `openat2` enforces the outer boundary; it does not
correct the narrower API-directory policy.

**Firmware build:**

```bash
TEST_FIRMWARE="$TEST_DEVICE-cwe022-rest-internal-files"
FIRMWARE="$TEST_FIRMWARE" docker compose run --rm \
  -e IOTBENCH_BUILD_MODE=fixture -e IOTBENCH_ENABLE_REST_FIXTURE=1 yocto
echo "build_exit=$?"
```

Boot a fresh snapshot. The full host suite is not installed; test the native
service manually in the **guest**:

```bash
REST_ROOT=/usr/share/iotbench/rest-internal-files
"$REST_ROOT/bin/fixture-rest" --isolated-fixture &
REST_PID=$!
```

Wait for `fixture-ready unix-only`, then send normal and traversal requests:

```bash
python3 - <<'PY'
import socket
for name in ('config.cfg', '../restricted/marker.txt'):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.connect('/usr/share/iotbench/rest-internal-files/run/rest.sock')
        request = ('GET /api/config?file=' + name +
                   ' HTTP/1.1\r\nHost: fixture\r\nConnection: close\r\n\r\n')
        client.sendall(request.encode('ascii'))
        client.shutdown(socket.SHUT_WR)
        response = b''
        while True:
            chunk = client.recv(4096)
            if not chunk:
                break
            response += chunk
        print(name, response.decode('ascii', errors='replace'))
PY
```

Switch to the corrected binary and repeat the same request block:

```bash
kill "$REST_PID"
wait "$REST_PID" || true
rm -f "$REST_ROOT/run/rest.sock"
"$REST_ROOT/bin/fixture-rest-secure" --isolated-fixture &
REST_PID=$!
```

After its ready message, normal config must remain readable and traversal must
be denied. Finish with `kill "$REST_PID"` and `wait "$REST_PID" || true`.
The fixture has no upload, write or command-execution API.

Source: [cwe022-rest-internal-files](../meta-iotbench/recipes-vulns/cwe022-rest-internal-files/).

<a id="apache-application-fixtures-ten-cwes-eleven-devices"></a>
<a id="test-8"></a>

## Test 8: Apache web applications — ten CWE variants

**Purpose:** one application defect per image, with ordinary inputs and negative
controls. Apache and synthetic resources run in disposable Linux namespaces.
Accounts are `admin` / `fixture-admin-proof` and `reader` /
`fixture-reader-proof`. The runner manages sessions, Origin and CSRF tokens.

| CWE | Endpoint and witness | Expected signal |
| --- | --- | --- |
| 89 | `GET /app/query`, `name=' OR designated=1 --` | Admin retrieves `synthetic-sql-sentinel` |
| 79 | `GET /app/reflect`, `message=<script>document.body.dataset.fixture="xss-marker"</script>` | Browser DOM marker appears |
| 20 | `POST /app/level`, `level=101` | Persists 101 despite the allowed range 0–100 |
| 352 | Form from loopback port 18081 posts `value=csrf-marker` to `/app/setting` on 18080 | Authenticated browser changes state without CSRF verification |
| 78 | `POST /app/diagnostic`, `label=ordinary; printf shell-marker > shell.marker; #` | Creates the synthetic shell marker |
| 22 | `GET /app/file`, `file=../sentinel.txt` | Reads `synthetic-traversal-sentinel` |
| 77 | `POST /app/command`, `label=ordinary; MARK` | Application interpreter writes its marker; no OS shell |
| 306 | `POST /app/critical`, `value=unauthenticated-marker` | Changes state without a session |
| 862 | `POST /app/admin-setting` as `reader`, `value=reader-marker` | Authenticated non-admin changes the admin setting |
| 287 | `POST /app/login`, `identity=admin&proof=fixture-INVALID` | Partial proof comparison incorrectly creates an admin session |

All other protected routes require the intended session/role checks; protected
writes also require Origin/CSRF unless that check is the selected defect.
The CSRF fixture uses different origins on the same site, not a cross-site POST.

**Host tests:** set the native Chrome/Chromium executable, not a launcher script.

```bash
python3 scripts/test-apache-integration.py
echo "exit=$?"
IOTBENCH_BROWSER=/path/to/chrome
python3 scripts/test-apache-fixtures.py \
  --mode fixture --enable 1 --browser "$IOTBENCH_BROWSER"
echo "exit=$?"
```

Expected: normal behavior, witness and controls pass for all ten variants.
Use `--cwe 089` to select one. `--apache` and `--modules` override discovery.
`--http-only` permits a **partial** run without a browser: XSS and CSRF remain
unverified. The suite does not download browsers or dependencies.

**Firmware build — SQL injection example:**

```bash
TEST_FIRMWARE="$TEST_DEVICE-cwe089-apache-web"
FIRMWARE="$TEST_FIRMWARE" docker compose run --rm \
  -e IOTBENCH_BUILD_MODE=fixture -e IOTBENCH_ENABLE_APACHE_FIXTURE=1 yocto
echo "build_exit=$?"
```

Replace `089` with the three-digit CWE for another variant. Boot using setup,
then run in the **guest**:

```bash
su -s /bin/sh -c 'python3 /usr/share/iotbench/apache-fixture/fixture-build.py --mode fixture --enable 1 --cwe 089 --apache /usr/sbin/httpd --modules /usr/libexec/apache2/modules' iotapache
echo "exit=$?"
```

Only the selected variant is installed. QEMU has no network device for these
images; the host browser cannot open the guest application. Browser binaries
are not bundled, so guest XSS/CSRF checks need a matching browser separately.

Source: [apache-web-fixture](../meta-iotbench/recipes-vulns/apache-web-fixture/).

<a id="native-c-path-fixtures-cwe-22-and-cwe-20"></a>
<a id="test-9"></a>

## Test 9: C path and filename validation — CWE-22/CWE-20

**Purpose:** test two distinct file-access policies on a private Unix socket.
A request is a two-byte big-endian length, the ASCII pathname, then EOF.

| Scenario suffix | Witness | Expected vulnerable result |
| --- | --- | --- |
| `cwe022-native-path-traversal` | `../sentinel.txt` | Reads `SYNTHETIC_CWE22_SENTINEL_ONLY` outside `allowed/` |
| `cwe020-native-filename-validation` | `private.cfg.bak` | Reads `SYNTHETIC_CWE20_DISALLOWED_BACKUP` despite the required final `.cfg` extension |

`public.cfg` succeeds normally. Corrected controls reject the witnesses;
malformed frames, absolute paths and escapes beyond the synthetic root fail.
The CWE-20 variant rejects slashes and stays inside `allowed/`.

**Host tests — both variants:**

```bash
python3 scripts/test-native-path-fixtures.py --isolated-fixture
echo "exit=$?"
python3 scripts/test-native-path-fixtures.py --isolated-fixture --sanitize
echo "exit=$?"
```

**Firmware build:** repeat for each scenario suffix above.

```bash
TEST_SCENARIO=cwe022-native-path-traversal
TEST_FIRMWARE="$TEST_DEVICE-$TEST_SCENARIO"
FIRMWARE="$TEST_FIRMWARE" docker compose run --rm \
  -e IOTBENCH_BUILD_MODE=fixture -e IOTBENCH_ENABLE_NATIVE_PATH_FIXTURE=1 yocto
echo "build_exit=$?"
```

Boot, then run in the **guest**:

```bash
su -s /bin/sh -c 'python3 /usr/share/iotbench/native-path/fixture-runner.py --isolated-fixture' iotpath
echo "exit=$?"
```

The fixture uses Linux namespaces and `openat2`, with no older-kernel fallback.
Reads remain confined to synthetic data; no dashboard, upload or shell exists.
Optional target sanitizer binaries require `-e IOTBENCH_NATIVE_PATH_ASAN=1`
at build time and a compatible target toolchain.

Source: [native-path-fixture](../meta-iotbench/recipes-vulns/native-path-fixture/).

<a id="native-c-buffer-overflow-cwe-787-cwe-20-cwe-119"></a>
<a id="test-10"></a>

## Test 10: C buffer overflow — CWE-787

**Purpose:** a framed stdin length controls writes into a 64-byte global buffer
without a destination-capacity check. CWE-20 and CWE-119 describe the same defect.
The frame is a two-byte big-endian length, payload bytes, then EOF.

| Input | Expected result |
| --- | --- |
| Header `00 01` + `A` | `OK 1 65` |
| Header `00 40` + 64 `A` bytes | `OK 64 4160` |
| Header `00 41` + 65 `A` bytes, ASan binary | `global-buffer-overflow`, `WRITE of size 1`, diagnostic exit 86 |
| Same oversized input, corrected control | `ERR CAPACITY`, no ASan error |
| Malformed or truncated frame | Rejected |

**Host tests:**

```bash
python3 scripts/test-native-buffer-overflow.py --static
echo "exit=$?"
python3 scripts/test-native-buffer-overflow.py --local
echo "exit=$?"
```

Expected: the runner recognizes the intentional ASan failure and passes the
corrected control, finishing with exit 0. Use an ordinary user and matching
compiler/sanitizer runtimes. This runner uses temporary directories and process
limits, not a filesystem namespace jail.

**Firmware build:**

```bash
TEST_FIRMWARE="$TEST_DEVICE-cwe787-native-buffer-overflow"
FIRMWARE="$TEST_FIRMWARE" docker compose run --rm \
  -e IOTBENCH_BUILD_MODE=fixture -e IOTBENCH_ENABLE_NATIVE_BUFFER_FIXTURE=1 yocto
echo "build_exit=$?"
```

Boot, then run in the **guest**, replacing `router` with the built device:

```bash
sh /usr/share/iotbench/native-buffer-overflow/test-guest.sh router
echo "exit=$?"
```

**The default guest checks do not exercise the overflow.** To verify that
diagnostic on the target, rebuild with `-e IOTBENCH_NATIVE_BUFFER_ASAN=1`
added to the build command, then run:

```bash
sh /usr/share/iotbench/native-buffer-overflow/test-guest.sh router --asan
echo "exit=$?"
```

Target ASan support is required. Normal firmware binaries retain compiler
hardening; the corrected control is a temporary test build, not another image.

Source: [cwe787-native-buffer-overflow](../meta-iotbench/recipes-vulns/cwe787-native-buffer-overflow/).

<a id="native-connection-string-injection-cwe-20"></a>
<a id="test-11"></a>

## Test 11: C connection string injection — CWE-20

**Purpose:** a caller-controlled cache field changes SQLite connection options.
The program constructs `file:<temporary-db>?cache=<field>&mode=ro` and passes it
to `sqlite3_open_v2`. Input is a two-byte big-endian length, ASCII field, then EOF.

| Field | Expected result |
| --- | --- |
| `private` or `shared` | `readonly=1`; reads `SYNTHETIC_CONNECTION_RESOURCE` |
| `private&mode=rw#` | `readonly=0`; `#` hides the fixed read-only suffix |
| Same witness in corrected control | Rejected by exact-value validation |
| Ordinary input after the witness | Read-only behavior restored in a fresh database |

**Host tests:**

```bash
python3 scripts/test-native-connection-string.py --static
echo "exit=$?"
python3 scripts/test-native-connection-string.py --local
echo "exit=$?"
```

Expected: normal, injected and corrected cases pass, including sanitizer checks
without memory errors. The runner uses the real linked SQLite library and
checks its URI parsing behavior; it requires SQLite development files.

**Firmware build:**

```bash
TEST_FIRMWARE="$TEST_DEVICE-cwe020-native-connection-string"
FIRMWARE="$TEST_FIRMWARE" docker compose run --rm \
  -e IOTBENCH_BUILD_MODE=fixture -e IOTBENCH_ENABLE_CONNECTION_FIXTURE=1 yocto
echo "build_exit=$?"
```

Boot, then run in the **guest**, using the built device keyword:

```bash
sh /usr/share/iotbench/native-connection-string/test-guest.sh router
echo "exit=$?"
```

The witness changes connection mode; SQL statements remain constant and no
database write is performed. Each request uses a disposable local database.
There are no remote credentials, network database connections or shell commands;
process/seccomp restrictions are not a complete filesystem namespace jail.

Source: [cwe020-native-connection-string](../meta-iotbench/recipes-vulns/cwe020-native-connection-string/).

<a id="native-c-symbolic-link-following-cwe-61-and-cwe-59"></a>
<a id="test-12"></a>

## Test 12: C symbolic-link following — CWE-61/CWE-59

**Purpose:** opening the fixed `allowed/public.cfg` follows a pre-existing
symlink because the final `openat()` lacks `O_NOFOLLOW`.
The private socket accepts only the framed command `READ`:
`00 04 52 45 41 44`, followed by EOF. No pathname comes from the request.

| Filesystem state | Expected result |
| --- | --- |
| Ordinary `public.cfg` | `SYNTHETIC_CWE61_ORDINARY_CONFIGURATION` |
| `public.cfg -> ../sentinel.txt` | `SYNTHETIC_CWE61_SENTINEL_ONLY`: intended defect |
| Same symlink with corrected final open | Rejected |
| Malformed command or request-supplied path | `ERR INVALID` |

**Host test:**

```bash
python3 scripts/test-native-symlink-fixture.py --isolated-fixture
echo "exit=$?"
```

The runner creates the link only in its disposable fixture filesystem.
This tests link following, not a check/use race or request-path traversal.

**Firmware build:**

```bash
TEST_FIRMWARE="$TEST_DEVICE-cwe061-native-symlink-following"
FIRMWARE="$TEST_FIRMWARE" docker compose run --rm \
  -e IOTBENCH_BUILD_MODE=fixture -e IOTBENCH_ENABLE_NATIVE_SYMLINK_FIXTURE=1 yocto
echo "build_exit=$?"
```

Boot, then run in the **guest**:

```bash
su -s /bin/sh -c 'python3 /usr/share/iotbench/native-symlink/fixture-runner.py --isolated-fixture' iotsymlink
echo "exit=$?"
```

Expected: ordinary-file, symlink, malformed-request and corrected-control
checks pass. Both source and sentinel remain within the synthetic filesystem;
no real system file is targeted.

Source: [cwe061-native-symlink-following](../meta-iotbench/recipes-vulns/cwe061-native-symlink-following/).

<a id="java-jar-command-injection-cwe-78--cwe-77-contributing-cwe-20"></a>
<a id="test-13"></a>

## Test 13: Java command injection — CWE-78/CWE-77

**Purpose:** incomplete label validation lets input cross either an OS-shell
boundary (`os`) or an application-interpreter boundary (`app`). Each request
is ASCII `label=<value>` followed by LF and EOF. The intended label alphabet
is `[A-Za-z0-9_-]{1,128}`.

| Variant | Firmware suffix | Witness |
| --- | --- | --- |
| `os` | `cwe078-java-os-command-injection` | Label below breaks out of the shell's quoted argument |
| `app` | `cwe077-java-app-command-injection` | `label=sensor;mark` adds an application command |

OS-variant label, with `\n` as literal backslash-n inside the shell command:

```text
sensor' > normal.txt; printf 'JAVA_OS_MARKER\n' > os-marker.txt; #
```

Expected: normal `label=sensor_01` creates only `normal.txt`; the witnesses
add `os-marker.txt` containing `JAVA_OS_MARKER` or `app-marker.txt` containing
`JAVA_APP_MARKER`. Corrected controls reject both. The `app` JAR has no OS
process execution; `sensor;mark` stays literal in the quoted `os` command.

**Host tests — both variants, using the JDK selected in setup:**

```bash
python3 scripts/test-java-command-fixture.py --static
echo "exit=$?"
python3 scripts/test-java-command-fixture.py --jdk "$IOTBENCH_JDK"
echo "exit=$?"
```

The runner builds the JARs and corrected controls, checks byte-for-byte repeated
builds, then executes in disposable namespaces. A missing isolation capability
fails the test; it does not fall back to running directly on the host JVM.

**Firmware build — repeat with the other suffix for `app`:**

```bash
TEST_FIRMWARE="$TEST_DEVICE-cwe078-java-os-command-injection"
FIRMWARE="$TEST_FIRMWARE" docker compose run --rm \
  -e IOTBENCH_BUILD_MODE=fixture -e IOTBENCH_ENABLE_JAVA_COMMAND_FIXTURE=1 yocto
echo "build_exit=$?"
```

Boot, then run in the **guest**; use `--variant app` for that image:

```bash
FIXTURE_DATA=/usr/share/iotbench/java-command-fixture
FIXTURE_JDK=$(dirname "$(dirname "$(readlink -f /usr/bin/java)")")
setpriv --reuid=991 --regid=991 --clear-groups \
  python3 "$FIXTURE_DATA/test-java-command-fixture.py" \
  --jdk "$FIXTURE_JDK" --jar-dir "$FIXTURE_DATA" --variant os
echo "exit=$?"
```

`--jar-dir` tests the packaged artifacts without rebuilding corrected controls.
The local full suite covers those controls separately. Canonical requests are
in [requests.json](../meta-iotbench/recipes-vulns/java-command-fixture/files/requests.json).

Source: [java-command-fixture](../meta-iotbench/recipes-vulns/java-command-fixture/).

<a id="java-deserialization-cwe-502-with-cwe-20-contributing"></a>
<a id="test-14"></a>

## Test 14: Java deserialization — CWE-502

**Purpose:** an unexpected serialized class executes its reconstruction callback
before a late type check rejects it. Input is one Java serialization stream
on stdin, header `AC ED 00 05`, at most 4096 bytes, followed by EOF.
Resource limits remain enabled; the missing control is a type allowlist.

| Input / control | Expected observation |
| --- | --- |
| `FixtureData("sensor_01", 23)` | `OK sensor=sensor_01 reading=23`, exit 0 |
| Unexpected `FixtureMarker` | `UNEXPECTED_TYPE`, exit 2, **one callback event** |
| Marker with the harness's corrected allowlist | Rejected before reconstruction, **zero events** |
| Normal data with the allowlist | Accepted, zero events |
| Input over 4096 bytes | `INPUT_TOO_LARGE`, zero callback events |
| Depth over 8, references over 32 or array length over 16 | `FILTER_REJECTED` |

**Host tests:**

```bash
python3 scripts/test-java-deserialization-fixture.py --static
echo "exit=$?"
python3 scripts/test-java-deserialization-fixture.py --jdk "$IOTBENCH_JDK"
echo "exit=$?"
```

Expected: all 16 input cases and additional controls pass. JARs and inputs are
generated automatically; add `--output deploy-images/java-deserialization-fixture`
to retain them. Canonical inputs are defined in
[vectors.json](../meta-iotbench/recipes-vulns/cwe502-java-deserialization/files/vectors.json).

**`UNEXPECTED_TYPE` alone is not proof of the defect.** The separate harness
measures the in-memory callback counter and compares it with the allowlist
control. This fixture does not demonstrate arbitrary code execution or an
external gadget chain; CWE-20 is a contributing classification of the same flaw.

**Firmware build:**

```bash
TEST_FIRMWARE="$TEST_DEVICE-cwe502-java-deserialization"
FIRMWARE="$TEST_FIRMWARE" docker compose run --rm \
  -e IOTBENCH_BUILD_MODE=fixture -e IOTBENCH_ENABLE_JAVA_DESERIALIZATION_FIXTURE=1 yocto
echo "build_exit=$?"
```

Boot, then run in the **guest**:

```bash
FIXTURE_DATA=/usr/share/iotbench/java-deserialization-fixture
FIXTURE_JDK=$(dirname "$(dirname "$(readlink -f /usr/bin/java)")")
setpriv --reuid=992 --regid=992 --clear-groups \
  python3 "$FIXTURE_DATA/test-java-deserialization-fixture.py" \
  --jdk "$FIXTURE_JDK" --jar-dir "$FIXTURE_DATA"
echo "exit=$?"
```

The packaged runtime uses the same isolated harness. Root must drop to the
fixture identity before running it. There is no network listener or dashboard.

Source: [cwe502-java-deserialization](../meta-iotbench/recipes-vulns/cwe502-java-deserialization/).

<a id="embedded-credential-pairs-over-a-unix-socket-cwe-798"></a>
<a id="extra-embedded"></a>

## Extra: Embedded credential pairs — CWE-798

This family is additional to the 14 catalog assignments. Each image contains
one active synthetic username/password pair, consumed by a private Unix-socket
authentication service.

| Variant | Artifact |
| --- | --- |
| `native` | `credential.c` and active `credential.so` |
| `shell` | `credentials.sh` |
| `ini` | `auth.ini` |
| `json` | `auth.json` |
| `xml` | `auth.xml` |
| `yaml` | `auth.yaml` |
| `connection-string` | `connection.conf` |
| `base64` | `encoded.json` |

Exact pairs are in the
[inventory](../meta-iotbench/recipes-vulns/cwe798-embedded-auth/files/inventory.json).
For example, the JSON variant accepts this line, terminated by LF:

```json
{"username":"fixture798_json","password":"SYNTH_ONLY_798_json_P9!"}
```

Expected: `OK` when both fields match; `DENIED` for a wrong field or malformed
request. Base64 must be decoded before comparison. Shell/YAML files are parsed
as data, not executed; the connection-string variant makes no remote connection.

**Host test — all eight variants:**

```bash
python3 -B scripts/test-embedded-auth-fixture.py --isolated-fixture
echo "exit=$?"
```

Add `--filesystem-roundtrip` to build/extract ext4 test artifacts with
`mke2fs` and `debugfs`. This remains a host fixture check, not a Yocto boot test.

**Firmware build — native example:**

```bash
TEST_FIRMWARE="$TEST_DEVICE-cwe798-embedded-auth-native"
FIRMWARE="$TEST_FIRMWARE" docker compose run --rm \
  -e IOTBENCH_BUILD_MODE=fixture -e IOTBENCH_ENABLE_EMBEDDED_AUTH_FIXTURE=1 yocto
echo "build_exit=$?"
```

Root is deliberately locked in these images. Extract the image using setup,
then inspect it on the **host**:

```bash
python3 scripts/test-embedded-auth-fixture.py --isolated-fixture \
  --rootfs "$TEST_INSPECT/rootfs" --variant native
echo "exit=$?"
```

Expected: the selected pair and its artifact are present, with no other
variant's credentials installed. Rootfs inspection does not execute an ARM
ELF on an x86 host and must be recorded separately from target execution.

Source: [cwe798-embedded-auth](../meta-iotbench/recipes-vulns/cwe798-embedded-auth/).
