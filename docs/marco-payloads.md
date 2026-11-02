# Marco Payloads

## How to use this guide

Start by choosing a device keyword and a scenario keyword below, then build and
boot the selected firmware. Each scenario explains its manual test, inputs and
expected results. For `permit-empty-passwords`, one shared policy check covers every device.
Execution evidence is stated separately from the test procedures.

### Common setup

- **Host**: the computer running Docker and QEMU. Open a terminal at the root
  of this repository, where `compose.yaml` and `scripts/` are located.
- **Guest**: the Linux firmware running inside QEMU. For tests marked as guest,
  wait for `login:` in the QEMU terminal and sign in with username `root` and
  password `routeradmin`. The password is not displayed while you type.
- **Second host terminal**: use this for host checks and firmware inspection;
  keep QEMU running in the first terminal during manual guest tests.

You need Docker Compose, plus QEMU and `zstd` on the host. The Python clients
shown here require Python 3.9+; additional tools depend on the selected test.
The manual SSH policy test uses the device dashboard. On macOS, install
QEMU and zstd with `brew install qemu zstd`. Before the first build, or if your builder predates
the Java layer, run on the host:

```bash
docker compose build yocto
```

### Device keywords

Use the exact keyword from this table when selecting a firmware:

| Device type | Keyword |
| --- | --- |
| Router | `router` |
| IP camera | `ipcamera` |
| Smart plug | `smartplug` |
| Thermostat | `thermostat` |
| Programmable logic controller | `plc` |
| Smart bulb | `smartbulb` |
| Smart home hub | `smarthub` |
| Environmental sensor | `envsensor` |
| Smart speaker | `smartspeaker` |
| Health monitor | `healthmonitor` |
| Door lock | `doorlock` |

The firmware ID is `<device-keyword>-<scenario-keyword>`, for example
`router-cwe521-permit-empty-passwords` or `doorlock-cwe521-permit-empty-passwords`.
Choose the scenario keyword from the [manual test index](#manual-test-index).
All scenarios listed there have a firmware recipe for each of these eleven
devices. For a given scenario, the fixture's payloads and expected vulnerability
signals are shared across devices; device identity, peripheral data and native
service ports can differ. In particular, every `permit-empty-passwords` image
uses the same SSH policy and dashboard procedure.

### Build and boot any device

Run the following commands in the same host terminal at the repository root.
Change only `TEST_DEVICE` and `TEST_SCENARIO` to select a different firmware,
then rerun the block. The default architecture is `qemuarm64`; for another
supported architecture, set `YOCTO_MACHINE` consistently for build and boot.

On **Apple Silicon**, you can accelerate `qemuarm64` boots by running these
commands in the host terminal before the boot commands:

```bash
export QEMU_ACCEL=hvf
export QEMU_CPU=host
```

```bash
TEST_DEVICE=router
TEST_SCENARIO=cwe521-permit-empty-passwords
TEST_FIRMWARE="${TEST_DEVICE}-${TEST_SCENARIO}"

FIRMWARE="$TEST_FIRMWARE" docker compose run --rm yocto
QEMU_HTTP_PORT=18080 FIRMWARE="$TEST_FIRMWARE" ./scripts/run-qemu.sh
```

The build exports its kernel and root filesystem to
`deploy-images/<device-keyword>-<scenario-keyword>/<machine>/`.
If you already have an up-to-date export, skip the Docker command and run the
QEMU command after setting the three variables. After boot, use the selected
scenario's test below. For `permit-empty-passwords`, go directly to
[Test 1](#test-1) and run the manual check in the browser.

This command and the manual guides set HTTP to **18080**.
When the selected image exposes its device dashboard, open
<http://127.0.0.1:18080>; always use the port printed by the launcher.
Apache, native path/buffer/connection/symlink and Java fixtures use the serial
console and have no dashboard or forwarded network port. The embedded-auth
extra locks root and is inspected offline as described in its test.
Run one firmware at a time to avoid port conflicts.

Follow the selected scenario's test procedure. For example,
`cwe276-bad-write-rights` uses the guest runner in [Test 2](#test-2): its FTP
service runs in a private network namespace, with no ports forwarded to the host.
Before guest tests, wait for `login:` and sign into the serial console.
To quit QEMU, press **Ctrl-A**, release the keys, then press **X**.
The launcher normally uses a disposable snapshot.

For CLI tests, run `echo "exit=$?"` **immediately after** the command you want to
check. A status of `0` means success, but the specific output described in each
guide confirms the defect. `INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE`
messages are expected notices. Scripts that boot QEMU themselves must run after
you close the manual instance.

### Manual test index

| Test | Scenario keyword | Where to run it | Evidence of the defect |
| --- | --- | --- | --- |
| [Test 1: SSH empty passwords](#test-1) | `cwe521-permit-empty-passwords` | Browser / guest inspection | Synthetic policy diagnostic permits an empty candidate; corrected control rejects it |
| [Test 2: FTP write permissions](#test-2) | `cwe276-bad-write-rights` | Guest / host VM runner | Upload succeeds in the writable directory and fails in the control |
| [Test 3: Telnet plaintext](#test-3) | `cwe798-unencrypted-traffic` | Guest / isolated host | Synthetic credentials and commands appear in plaintext |
| [Test 4: Sudo environment](#test-4) | `cwe798-sudo-environment` | Guest | Preserved variables select the diagnostic behavior with EUID 0 |
| [Test 5: Cron wildcard](#test-5) | `cwe088-cronjob-wildcard-injection` | Guest | Option-like filename selects the diagnostic; corrected control stays nominal |
| [Test 6: Password leak](#test-6) | `cwe798-password-leak-<variant>` | Guest / extracted firmware | Recovered synthetic credential is accepted; wrong value is rejected |
| [Test 7: REST internal files](#test-7) | `cwe022-rest-internal-files` | Guest / isolated host | Config route returns the restricted synthetic marker; control denies it |
| [Test 8: Apache applications](#test-8) | `cwe<CWE>-apache-web` | Guest / isolated host; browser for XSS and CSRF | Selected defect produces its marker or unauthorized state change |
| [Test 9: C path and filename](#test-9) | `cwe022-native-path-traversal`, `cwe020-native-filename-validation` | Guest / isolated host | Disallowed synthetic file is read; corrected control rejects it |
| [Test 10: C buffer overflow](#test-10) | `cwe787-native-buffer-overflow` | Host / guest with ASan | ASan identifies the out-of-bounds write; corrected control rejects the input |
| [Test 11: C connection string](#test-11) | `cwe020-native-connection-string` | Guest / host | Injected field changes SQLite from read-only to writable capability |
| [Test 12: C symbolic links](#test-12) | `cwe061-native-symlink-following` | Guest / isolated host | Fixed file follows the synthetic symlink; corrected control denies it |
| [Test 13: Java commands](#test-13) | `cwe078-java-os-command-injection`, `cwe077-java-app-command-injection` | Guest / isolated host | Selected interpreter creates its extra synthetic marker |
| [Test 14: Java deserialization](#test-14) | `cwe502-java-deserialization` | Guest / isolated host | Unexpected class triggers one callback; allowlist control triggers zero |
| [Extra: Embedded pairs](#extra-embedded) | `cwe798-embedded-auth-<variant>` | Host / extracted firmware | Matching synthetic pair is accepted; incorrect fields are denied |

The 14 tests cover 39 variants per device; the extra family adds eight.
Choose one concrete variant wherever the index uses a placeholder.

### Technical references

The catalog is [Catalogo_Test_Sicurezza_Firmware_IoT.xlsm](../Catalogo_Test_Sicurezza_Firmware_IoT.xlsm).
Execution evidence belongs in [validation records](validation/). Catalog numbers
and variant counts appear in each test's scope section.


<a id="weakly-configured-ssh--empty-password-authentication-permitted-cwe-521"></a>
<a id="test-1"></a>

## Test 1: SSH empty-password policy — CWE-521

### Build, boot and manual testing

**What this tests.** A dashboard diagnostic evaluates a candidate password
against the installed SSH policy. An empty candidate is permitted by the weak
policy and rejected by a corrected control. This is a synthetic policy check,
not an SSH authentication service.

**Build — host:**

Run from the repository root, where `compose.yaml` and `scripts/` are located:

```bash
TEST_DEVICE=router
TEST_SCENARIO=cwe521-permit-empty-passwords
TEST_FIRMWARE="${TEST_DEVICE}-${TEST_SCENARIO}"

FIRMWARE="$TEST_FIRMWARE" docker compose run --rm yocto
```

Wait for the build to finish successfully. With the default `qemuarm64`
architecture, the final export message is:

```text
Firmware exported to deploy-images/router-cwe521-permit-empty-passwords/qemuarm64
```

**Boot — host:**

After the build succeeds, run in the same host terminal:

```bash
QEMU_HTTP_PORT=18080 FIRMWARE="$TEST_FIRMWARE" ./scripts/run-qemu.sh
```

Wait for the guest to show `login:` and for its web service to respond. Keep QEMU running; the browser test does not require a serial-console login.

**Manual test — browser:**

Open <http://127.0.0.1:18080> and find the **SSH Password Policy** panel.

1. Select **Installed firmware**, leave **Candidate password** empty and click
   **Check password policy**. The output must contain:

   ```text
   diagnostic=synthetic
   policy=firmware
   PermitEmptyPasswords=yes
   PasswordAuthentication=yes
   PermitRootLogin=no
   password_empty=yes
   decision=POLICY_PERMITS_EMPTY_PASSWORD
   ```

2. Select **Corrected control**, keep the candidate empty and submit again.
   Expect `PermitEmptyPasswords=no` and
   `decision=POLICY_REJECTS_EMPTY_PASSWORD`.
3. Enter `manual-policy-check` and submit once with each policy. Both must
   return `password_empty=no` and
   `decision=POLICY_PERMITS_NONEMPTY_PASSWORD`.
4. Return to **Installed firmware**, clear the password and submit again.
   Expect `POLICY_PERMITS_EMPTY_PASSWORD` again: the corrected control must
   not change the installed configuration.

**Expected behaviour:**

| Candidate | Installed firmware | Corrected control |
| --- | --- | --- |
| Empty | `POLICY_PERMITS_EMPTY_PASSWORD` | `POLICY_REJECTS_EMPTY_PASSWORD` |
| `manual-policy-check` | `POLICY_PERMITS_NONEMPTY_PASSWORD` | `POLICY_PERMITS_NONEMPTY_PASSWORD` |

The empty-input difference is the observable policy defect. A permitted candidate has passed only this password-policy diagnostic; no credential is checked and no user is signed in. Submitted passwords are not echoed or saved. The corrected control changes only an in-memory copy of `PermitEmptyPasswords`.

**Optional inspection — guest:** log into the QEMU serial console as `root` with password `routeradmin`, then read the backing configuration:

```sh
cat /etc/ssh/sshd_config
```

It still contains `PermitEmptyPasswords yes`, `PasswordAuthentication yes` and `PermitRootLogin no`, including after the corrected-control requests.

### Scenario and scope

The diagnostic reads only `/etc/ssh/sshd_config` and recognizes the fixture's closed directive set. It is not a general OpenSSH configuration parser. Malformed or unexpected policy content is rejected. The selected mode and candidate cannot select a file path or change the installed policy. The fixture installs no SSH server, accounts with empty passwords or SSH startup hooks. It creates no authenticated session and adds no SSH port forwarding. Its policy result is not evidence of a successful SSH login.


Source: [cwe521-permit-empty-passwords](../meta-iotbench/recipes-vulns/cwe521-permit-empty-passwords/).
References: [OpenSSH option](https://man.openbsd.org/sshd_config#PermitEmptyPasswords),
[CWE-521](https://cwe.mitre.org/data/definitions/521.html).

<a id="weakly-configured-vsftpd-bad-write-rights"></a>
<a id="test-2"></a>

## Test 2: FTP write permissions — CWE-276

### Build, boot and manual testing

**What this tests.** An authenticated maintenance user can upload where policy permits
only listing/download.

**Build and boot — host:**

```bash
TEST_DEVICE=router
TEST_SCENARIO=cwe276-bad-write-rights
TEST_FIRMWARE="${TEST_DEVICE}-${TEST_SCENARIO}"

FIRMWARE="$TEST_FIRMWARE" docker compose run --rm yocto
QEMU_HTTP_PORT=18080 FIRMWARE="$TEST_FIRMWARE" ./scripts/run-qemu.sh
```

**Test — guest:**

```sh
python3 /usr/share/iotbench/bad-write-rights/test-guest.py --isolated-fixture
echo "exit=$?"
```

Expected: five PASS groups covering authentication, reads, uploads, boundaries
and permissions. FTP runs only during the test in a private network namespace;
its ports are not forwarded. vsftpd retains its privileged authentication/chroot
broker, while uploaded files belong to the unprivileged account. This test does
not demonstrate anonymous upload, root FTP access or command execution.

### Scenario and scope

Catalog no. **6**; **1 variant** per device.

Account: `ftpfixture` / `Fixture-FTP-Only-42`, synthetic
test credentials. Both directories are owned by `root:ftpfixture`:

| Operation | Expected result |
| --- | --- |
| `STOR bad/probe.txt`, directory mode `0775` | Upload succeeds: intended defect |
| Same upload in `control`, mode `0755` | Rejected |
| Upload after temporarily correcting `bad` to `0755` | Rejected |
| Anonymous, root or wrong-password login | Rejected |

### Regression verification

**Test — host:**

```bash
python3 scripts/check-ftp-write-rights.py
echo "exit=$?"
```

After closing any manually booted VM, run the automated firmware check:

```bash
python3 scripts/test-ftp-write-rights.py --device "$TEST_DEVICE"
echo "exit=$?"
```

The runner manages QEMU and saves `/tmp/iotbench-ftp-<device>-qemu.log`.
It uses the same `scripts/run-qemu.sh` launcher as the manual procedure.
`--all --build` repeats the same build and test for all eleven devices.

Source: [cwe276-bad-write-rights](../meta-iotbench/recipes-vulns/cwe276-bad-write-rights/).

<a id="weakly-configured-telnet--unencrypted-traffic-cwe-798287276"></a>
<a id="test-3"></a>

## Test 3: Telnet plaintext traffic — CWE-798/287/276

### Build, boot and manual testing

**What this tests.** A synthetic Telnet session exposes fixed credentials and commands
in plaintext.

**Build and boot — host:**

```bash
TEST_DEVICE=router
TEST_SCENARIO=cwe798-unencrypted-traffic
TEST_FIRMWARE="${TEST_DEVICE}-${TEST_SCENARIO}"

FIRMWARE="$TEST_FIRMWARE" docker compose run --rm yocto
QEMU_HTTP_PORT=18080 FIRMWARE="$TEST_FIRMWARE" ./scripts/run-qemu.sh
```

**Test — guest:**

```sh
python3 /usr/share/iotbench/unencrypted-traffic/test-session.py \
  --installed --isolated-fixture --require-pcap \
  --pcap /tmp/iotbench-telnet.pcap --transcript /tmp/iotbench-telnet-wire.json
echo "exit=$?"
```

`STATUS`, `HELP` and `QUIT` return fixed responses. This is a synthetic service,
not an OS login daemon: other inputs cannot execute commands or start a shell.
No Telnet port is forwarded to the host.

### Scenario and scope

Catalog no. **9**; **1 variant** per device.

The expected pair is `telnet-fixture` /
`Fixture-Telnet-Only-42`. The weak policy also accepts another nonempty username
with that password; the strict username/password control rejects it.
The policy file is mode `0666`; the permission control changes it to `0644`.

### Regression verification

**Test — host:**

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

Source: [cwe798-unencrypted-traffic](../meta-iotbench/recipes-vulns/cwe798-unencrypted-traffic/).

<a id="bad-sudo-rights--allow-changes-to-environment-variables-cwe-798"></a>
<a id="test-4"></a>

## Test 4: Sudo environment — CWE-798

### Build, boot and manual testing

**What this tests.** Caller-controlled variables preserved by sudo change a privileged
diagnostic helper's behavior.

**Build and boot — host:**

```bash
TEST_DEVICE=router
TEST_SCENARIO=cwe798-sudo-environment
TEST_FIRMWARE="${TEST_DEVICE}-${TEST_SCENARIO}"

FIRMWARE="$TEST_FIRMWARE" docker compose run --rm yocto
QEMU_HTTP_PORT=18080 FIRMWARE="$TEST_FIRMWARE" ./scripts/run-qemu.sh
```

**Test — guest:**

```sh
python3 /usr/share/iotbench/sudo-environment/test-session.py \
  --installed --isolated-fixture
echo "exit=$?"
```

Expected: the permitted diagnostic runs with `FIXTURE_EUID=0`, while unlisted
caller variables remain absent or are rejected. The synthetic credential is
hardcoded for CWE-798 analysis. `FIXTURE_CONFIG` is a fixed value, not a path;
the helper does not execute user commands, load libraries or read arbitrary files.

### Scenario and scope

Catalog no. **12**; **1 variant** per device.

The policy permits only
`sudo -n /usr/bin/fixture-sudo-env --fixture-test` for the locked `fixtureenv`
account; `env_keep` preserves these three inputs:

| Variable | Normal value | Diagnostic value |
| --- | --- | --- |
| `FIXTURE_MODE` | `status` | `diagnostic` |
| `FIXTURE_CONFIG` | `public` | `Fixture-Sudo-Only-42` |
| `TEST_PROFILE` | `baseline` | `boundary` |

### Regression verification

**Test — host:**

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

Source: [cwe798-sudo-environment](../meta-iotbench/recipes-vulns/cwe798-sudo-environment/).

<a id="cronjob-wildcard-injection-cwe-8878269"></a>
<a id="test-5"></a>

## Test 5: Cron wildcard injection — CWE-88/78/269

### Build, boot and manual testing

**What this tests.** A file named `--fixture-diagnostic` is interpreted as an option
when a maintenance command expands bare `*`.

**Build and boot — host:**

```bash
TEST_DEVICE=router
TEST_SCENARIO=cwe088-cronjob-wildcard-injection
TEST_FIRMWARE="${TEST_DEVICE}-${TEST_SCENARIO}"

FIRMWARE="$TEST_FIRMWARE" docker compose run --rm yocto
QEMU_HTTP_PORT=18080 FIRMWARE="$TEST_FIRMWARE" ./scripts/run-qemu.sh
```

**Test — guest:**

Use a fresh disposable snapshot.

```sh
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

### Scenario and scope

Catalog no. **15**; **1 variant** per device.

The corrected command uses
`--fixture-test -- *`, so the same filename remains an operand.

### Regression verification

**Test — host:**

```bash
python3 scripts/test-cron-wildcard-fixture.py --isolated-fixture
echo "exit=$?"
```

Expected: nominal input stays `nominal`; the option-like filename selects
`synthetic-diagnostic`; the corrected control stays `nominal`.

Source: [cwe088-cronjob-wildcard-injection](../meta-iotbench/recipes-vulns/cwe088-cronjob-wildcard-injection/).

<a id="password-leak--different-file-types-and-patterns-cwe-798"></a>
<a id="test-6"></a>

## Test 6: Password leak — CWE-798

### Build, boot and manual testing

**What this tests.** A synthetic credential stored in a file is accepted by the local
authentication helper.

**Build and boot — host:**

The example selects `conf-password`; repeat it for each required variant below.

```bash
TEST_DEVICE=router
TEST_SCENARIO=cwe798-password-leak-conf-password
TEST_FIRMWARE="${TEST_DEVICE}-${TEST_SCENARIO}"

FIRMWARE="$TEST_FIRMWARE" docker compose run --rm yocto
QEMU_HTTP_PORT=18080 FIRMWARE="$TEST_FIRMWARE" ./scripts/run-qemu.sh
```

**Test — guest:**

```sh
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

**Firmware extraction — host:**

Extract the selected `TEST_FIRMWARE` on the host without booting it:

```bash
TEST_MACHINE="${YOCTO_MACHINE:-qemuarm64}"
TEST_INSPECT=$(mktemp -d /tmp/iotbench-inspect.XXXXXX) &&
mkdir "$TEST_INSPECT/rootfs" &&
zstd -dc "deploy-images/$TEST_FIRMWARE/$TEST_MACHINE/iotbench-$TEST_FIRMWARE-$TEST_MACHINE.rootfs.ext4.zst" \
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

**Check — host:** verify the extracted filesystem:

```bash
python3 scripts/test-password-leak-fixture.py --isolated-fixture \
  --rootfs "$TEST_INSPECT/rootfs" --variant conf-password
echo "exit=$?"
```

### Scenario and scope

Catalog no. **18**; **15 variants** per device.

Each image contains one variant.

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

### Regression verification

**Test — host:**

All 15 variants.

```bash
python3 scripts/test-password-leak-fixture.py --isolated-fixture
echo "exit=$?"
```

Expected: all nine test groups pass, including credential recovery, accepted
correct values and rejected controls. Scripts are parsed as data, not executed.
C/header authentication is compiled in local tests; those firmware variants
ship source plus the Python authentication helper, not an extra credential ELF.

Source: [cwe798-password-leak](../meta-iotbench/recipes-vulns/cwe798-password-leak/).

<a id="exploitable-rest-interface--internal-files-cwe-22cwe-73"></a>
<a id="test-7"></a>

## Test 7: REST internal files — CWE-22/CWE-73

### Build, boot and manual testing

**What this tests.** The config route reads beyond its intended `fs/api` directory,
while remaining inside a dedicated synthetic filesystem.

**Build and boot — host:**

```bash
TEST_DEVICE=router
TEST_SCENARIO=cwe022-rest-internal-files
TEST_FIRMWARE="${TEST_DEVICE}-${TEST_SCENARIO}"

FIRMWARE="$TEST_FIRMWARE" docker compose run --rm yocto
QEMU_HTTP_PORT=18080 FIRMWARE="$TEST_FIRMWARE" ./scripts/run-qemu.sh
```

**Test — guest:**

Use a fresh disposable snapshot. The full host suite is not installed;
the following procedure checks the native service.

```sh
REST_ROOT=/usr/share/iotbench/rest-internal-files
"$REST_ROOT/bin/fixture-rest" --isolated-fixture &
REST_PID=$!
```

Wait for `fixture-ready unix-only`, then send normal and traversal requests:

```sh
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

```sh
kill "$REST_PID"
wait "$REST_PID" || true
rm -f "$REST_ROOT/run/rest.sock"
"$REST_ROOT/bin/fixture-rest-secure" --isolated-fixture &
REST_PID=$!
```

After its ready message, normal config must remain readable and traversal must
be denied. Finish with `kill "$REST_PID"` and `wait "$REST_PID" || true`.
The fixture has no upload, write or command-execution API.

### Scenario and scope

Catalog no. **21**; **1 variant** per device.

The interface is
HTTP over a private Unix socket, not a browser-accessible TCP service.

| Request | Vulnerable result | Corrected result |
| --- | --- | --- |
| `GET /api/config?file=config.cfg` | 200, synthetic config | Same |
| `GET /api/config?file=../restricted/marker.txt` | 200, `IOTBENCH_SYNTHETIC_REST_BOUNDARY_MARKER` | 403 |
| Same traversal, percent-encoded once | 200, same marker | 403 |
| `GET /api/status?file=status.cfg` | 200, status; traversal rejected | Same |
| `POST /api/config/read`, body `file=config.cfg` | 200, config; traversal rejected | Same |
| Escape beyond the synthetic root or follow a symlink | 403 | 403 |

### Regression verification

**Test — host:**

```bash
python3 scripts/test-rest-fixture.py --isolated-fixture
echo "exit=$?"
python3 scripts/test-rest-fixture.py --isolated-fixture --sanitize
echo "exit=$?"
```

Expected: eight test groups pass, including normal requests, traversal and
corrected controls. Linux `openat2` enforces the outer boundary; it does not
correct the narrower API-directory policy.

Source: [cwe022-rest-internal-files](../meta-iotbench/recipes-vulns/cwe022-rest-internal-files/).

<a id="apache-application-fixtures-ten-cwes-eleven-devices"></a>
<a id="test-8"></a>

## Test 8: Apache web applications — ten CWE variants

### Build, boot and manual testing

**What this tests.** One application defect per image, with ordinary inputs and negative
controls.

**Build and boot — host:**

The example selects CWE-089; use the three-digit CWE of the selected variant below.

```bash
TEST_DEVICE=router
TEST_SCENARIO=cwe089-apache-web
TEST_FIRMWARE="${TEST_DEVICE}-${TEST_SCENARIO}"

FIRMWARE="$TEST_FIRMWARE" docker compose run --rm yocto
QEMU_HTTP_PORT=18080 FIRMWARE="$TEST_FIRMWARE" ./scripts/run-qemu.sh
```

**Test — guest:**

```sh
su -s /bin/sh -c 'python3 /usr/share/iotbench/apache-fixture/fixture-build.py --mode fixture --enable 1 --cwe 089 --apache /usr/sbin/httpd --modules /usr/libexec/apache2/modules' iotapache
echo "exit=$?"
```

Only the selected variant is installed. QEMU has no network device for these
images; the host browser cannot open the guest application. Browser binaries
are not bundled, so guest XSS/CSRF checks need a matching browser separately.

### Scenario and scope

Catalog no. **24**; **10 variants** per device.

Apache and synthetic resources run in disposable Linux namespaces.
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

### Regression verification

**Test — host:**

Set the native Chrome/Chromium executable, not a launcher script.

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

Source: [apache-web-fixture](../meta-iotbench/recipes-vulns/apache-web-fixture/).

<a id="native-c-path-fixtures-cwe-22-and-cwe-20"></a>
<a id="test-9"></a>

## Test 9: C path and filename validation — CWE-22/CWE-20

### Build, boot and manual testing

**What this tests.** Two native fixtures test distinct file-access policies on a private
Unix socket.

**Build and boot — host:**

Repeat the procedure for each scenario suffix listed below.

```bash
TEST_DEVICE=router
TEST_SCENARIO=cwe022-native-path-traversal
TEST_FIRMWARE="${TEST_DEVICE}-${TEST_SCENARIO}"

FIRMWARE="$TEST_FIRMWARE" docker compose run --rm yocto
QEMU_HTTP_PORT=18080 FIRMWARE="$TEST_FIRMWARE" ./scripts/run-qemu.sh
```

**Test — guest:**

```sh
su -s /bin/sh -c 'python3 /usr/share/iotbench/native-path/fixture-runner.py --isolated-fixture' iotpath
echo "exit=$?"
```

The fixture uses Linux namespaces and `openat2`, with no older-kernel fallback.
Reads remain confined to synthetic data; no dashboard, upload or shell exists.
Optional target sanitizer binaries require `-e IOTBENCH_NATIVE_PATH_ASAN=1`
at build time and a compatible target toolchain.

### Scenario and scope

Catalog no. **28**; **2 variants** per device.

A request is a two-byte big-endian length, the ASCII pathname, then EOF.

| Scenario suffix | Witness | Expected vulnerable result |
| --- | --- | --- |
| `cwe022-native-path-traversal` | `../sentinel.txt` | Reads `SYNTHETIC_CWE22_SENTINEL_ONLY` outside `allowed/` |
| `cwe020-native-filename-validation` | `private.cfg.bak` | Reads `SYNTHETIC_CWE20_DISALLOWED_BACKUP` despite the required final `.cfg` extension |

`public.cfg` succeeds normally. Corrected controls reject the witnesses;
malformed frames, absolute paths and escapes beyond the synthetic root fail.
The CWE-20 variant rejects slashes and stays inside `allowed/`.

### Regression verification

**Test — host:**

Both variants.

```bash
python3 scripts/test-native-path-fixtures.py --isolated-fixture
echo "exit=$?"
python3 scripts/test-native-path-fixtures.py --isolated-fixture --sanitize
echo "exit=$?"
```

Source: [native-path-fixture](../meta-iotbench/recipes-vulns/native-path-fixture/).

<a id="native-c-buffer-overflow-cwe-787-cwe-20-cwe-119"></a>
<a id="test-10"></a>

## Test 10: C buffer overflow — CWE-787

### Build, boot and manual testing

**What this tests.** A framed stdin length controls writes into a 64-byte global buffer
without a destination-capacity check.

**Build and boot — host:**

```bash
TEST_DEVICE=router
TEST_SCENARIO=cwe787-native-buffer-overflow
TEST_FIRMWARE="${TEST_DEVICE}-${TEST_SCENARIO}"

FIRMWARE="$TEST_FIRMWARE" docker compose run --rm yocto
QEMU_HTTP_PORT=18080 FIRMWARE="$TEST_FIRMWARE" ./scripts/run-qemu.sh
```

**Test — guest:**

Replace `router` with the built device keyword.

```sh
sh /usr/share/iotbench/native-buffer-overflow/test-guest.sh router
echo "exit=$?"
```

**The default guest checks do not exercise the overflow.** To verify that
diagnostic on the target, rebuild with `-e IOTBENCH_NATIVE_BUFFER_ASAN=1`
added to the build command, then run:

```sh
sh /usr/share/iotbench/native-buffer-overflow/test-guest.sh router --asan
echo "exit=$?"
```

Target ASan support is required. Normal firmware binaries retain compiler
hardening; the corrected control is a temporary test build, not another image.

### Scenario and scope

Catalog no. **30**; **1 variant** per device.

CWE-20 and CWE-119 describe the same defect.
The frame is a two-byte big-endian length, payload bytes, then EOF.

| Input | Expected result |
| --- | --- |
| Header `00 01` + `A` | `OK 1 65` |
| Header `00 40` + 64 `A` bytes | `OK 64 4160` |
| Header `00 41` + 65 `A` bytes, ASan binary | `global-buffer-overflow`, `WRITE of size 1`, diagnostic exit 86 |
| Same oversized input, corrected control | `ERR CAPACITY`, no ASan error |
| Malformed or truncated frame | Rejected |

### Regression verification

**Test — host:**

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

Source: [cwe787-native-buffer-overflow](../meta-iotbench/recipes-vulns/cwe787-native-buffer-overflow/).

<a id="native-connection-string-injection-cwe-20"></a>
<a id="test-11"></a>

## Test 11: C connection string injection — CWE-20

### Build, boot and manual testing

**What this tests.** A caller-controlled cache field changes SQLite connection options.

**Build and boot — host:**

```bash
TEST_DEVICE=router
TEST_SCENARIO=cwe020-native-connection-string
TEST_FIRMWARE="${TEST_DEVICE}-${TEST_SCENARIO}"

FIRMWARE="$TEST_FIRMWARE" docker compose run --rm yocto
QEMU_HTTP_PORT=18080 FIRMWARE="$TEST_FIRMWARE" ./scripts/run-qemu.sh
```

**Test — guest:**

Replace `router` with the built device keyword.

```sh
sh /usr/share/iotbench/native-connection-string/test-guest.sh router
echo "exit=$?"
```

The witness changes connection mode; SQL statements remain constant and no
database write is performed. Each request uses a disposable local database.
There are no remote credentials, network database connections or shell commands;
process/seccomp restrictions are not a complete filesystem namespace jail.

### Scenario and scope

Catalog no. **33**; **1 variant** per device.

The program constructs `file:<temporary-db>?cache=<field>&mode=ro` and passes it
to `sqlite3_open_v2`. Input is a two-byte big-endian length, ASCII field, then EOF.

| Field | Expected result |
| --- | --- |
| `private` or `shared` | `readonly=1`; reads `SYNTHETIC_CONNECTION_RESOURCE` |
| `private&mode=rw#` | `readonly=0`; `#` hides the fixed read-only suffix |
| Same witness in corrected control | Rejected by exact-value validation |
| Ordinary input after the witness | Read-only behavior restored in a fresh database |

### Regression verification

**Test — host:**

```bash
python3 scripts/test-native-connection-string.py --static
echo "exit=$?"
python3 scripts/test-native-connection-string.py --local
echo "exit=$?"
```

Expected: normal, injected and corrected cases pass, including sanitizer checks
without memory errors. The runner uses the real linked SQLite library and
checks its URI parsing behavior; it requires SQLite development files.

Source: [cwe020-native-connection-string](../meta-iotbench/recipes-vulns/cwe020-native-connection-string/).

<a id="native-c-symbolic-link-following-cwe-61-and-cwe-59"></a>
<a id="test-12"></a>

## Test 12: C symbolic-link following — CWE-61/CWE-59

### Build, boot and manual testing

**What this tests.** Opening the fixed `allowed/public.cfg` follows a pre-existing
symlink because the final `openat()` lacks `O_NOFOLLOW`.

**Build and boot — host:**

```bash
TEST_DEVICE=router
TEST_SCENARIO=cwe061-native-symlink-following
TEST_FIRMWARE="${TEST_DEVICE}-${TEST_SCENARIO}"

FIRMWARE="$TEST_FIRMWARE" docker compose run --rm yocto
QEMU_HTTP_PORT=18080 FIRMWARE="$TEST_FIRMWARE" ./scripts/run-qemu.sh
```

**Test — guest:**

```sh
su -s /bin/sh -c 'python3 /usr/share/iotbench/native-symlink/fixture-runner.py --isolated-fixture' iotsymlink
echo "exit=$?"
```

Expected: ordinary-file, symlink, malformed-request and corrected-control
checks pass. Both source and sentinel remain within the synthetic filesystem;
no real system file is targeted.

### Scenario and scope

Catalog no. **36**; **1 variant** per device.

The private socket accepts only the framed command `READ`:
`00 04 52 45 41 44`, followed by EOF. No pathname comes from the request.

| Filesystem state | Expected result |
| --- | --- |
| Ordinary `public.cfg` | `SYNTHETIC_CWE61_ORDINARY_CONFIGURATION` |
| `public.cfg -> ../sentinel.txt` | `SYNTHETIC_CWE61_SENTINEL_ONLY`: intended defect |
| Same symlink with corrected final open | Rejected |
| Malformed command or request-supplied path | `ERR INVALID` |

### Regression verification

**Test — host:**

```bash
python3 scripts/test-native-symlink-fixture.py --isolated-fixture
echo "exit=$?"
```

The runner creates the link only in its disposable fixture filesystem.
This tests link following, not a check/use race or request-path traversal.

Source: [cwe061-native-symlink-following](../meta-iotbench/recipes-vulns/cwe061-native-symlink-following/).

<a id="java-jar-command-injection-cwe-78--cwe-77-contributing-cwe-20"></a>
<a id="test-13"></a>

## Test 13: Java command injection — CWE-78/CWE-77

### Build, boot and manual testing

**What this tests.** Incomplete label validation lets input cross either an OS-shell
boundary (`os`) or an application-interpreter boundary (`app`).

**Build and boot — host:**

The example selects `os`; use the other suffix and `--variant app` for `app`.

```bash
TEST_DEVICE=router
TEST_SCENARIO=cwe078-java-os-command-injection
TEST_FIRMWARE="${TEST_DEVICE}-${TEST_SCENARIO}"

FIRMWARE="$TEST_FIRMWARE" docker compose run --rm yocto
QEMU_HTTP_PORT=18080 FIRMWARE="$TEST_FIRMWARE" ./scripts/run-qemu.sh
```

**Test — guest:**

Use `--variant app` for the application-command image.

```sh
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

### Scenario and scope

Catalog no. **39**; **2 variants** per device.

Each request
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

### Regression verification

**Test — host:**

Both variants, using the JDK selected in setup.

```bash
python3 scripts/test-java-command-fixture.py --static
echo "exit=$?"
python3 scripts/test-java-command-fixture.py --jdk "$IOTBENCH_JDK"
echo "exit=$?"
```

The runner builds the JARs and corrected controls, checks byte-for-byte repeated
builds, then executes in disposable namespaces. A missing isolation capability
fails the test; it does not fall back to running directly on the host JVM.

Source: [java-command-fixture](../meta-iotbench/recipes-vulns/java-command-fixture/).

<a id="java-deserialization-cwe-502-with-cwe-20-contributing"></a>
<a id="test-14"></a>

## Test 14: Java deserialization — CWE-502

### Build, boot and manual testing

**What this tests.** An unexpected serialized class executes its reconstruction callback
before a late type check rejects it.

**Build and boot — host:**

```bash
TEST_DEVICE=router
TEST_SCENARIO=cwe502-java-deserialization
TEST_FIRMWARE="${TEST_DEVICE}-${TEST_SCENARIO}"

FIRMWARE="$TEST_FIRMWARE" docker compose run --rm yocto
QEMU_HTTP_PORT=18080 FIRMWARE="$TEST_FIRMWARE" ./scripts/run-qemu.sh
```

**Test — guest:**

```sh
FIXTURE_DATA=/usr/share/iotbench/java-deserialization-fixture
FIXTURE_JDK=$(dirname "$(dirname "$(readlink -f /usr/bin/java)")")
setpriv --reuid=992 --regid=992 --clear-groups \
  python3 "$FIXTURE_DATA/test-java-deserialization-fixture.py" \
  --jdk "$FIXTURE_JDK" --jar-dir "$FIXTURE_DATA"
echo "exit=$?"
```

The packaged runtime uses the same isolated harness. Root must drop to the
fixture identity before running it. There is no network listener or dashboard.

### Scenario and scope

Catalog no. **42**; **1 variant** per device.

Input is one Java serialization stream
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

### Regression verification

**Test — host:**

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

Source: [cwe502-java-deserialization](../meta-iotbench/recipes-vulns/cwe502-java-deserialization/).

<a id="embedded-credential-pairs-over-a-unix-socket-cwe-798"></a>
<a id="extra-embedded"></a>

## Extra: Embedded credential pairs — CWE-798

### Build, boot and manual testing

**What this tests.** Each image contains
one active synthetic username/password pair, consumed by a private Unix-socket
authentication service.

**Build — host:**

The example selects `native`; use the selected variant consistently for inspection.

```bash
TEST_DEVICE=router
TEST_SCENARIO=cwe798-embedded-auth-native
TEST_FIRMWARE="${TEST_DEVICE}-${TEST_SCENARIO}"

FIRMWARE="$TEST_FIRMWARE" docker compose run --rm yocto
```

Root is deliberately locked in these images; inspect the exported firmware offline.

**Firmware extraction — host:**

Extract the selected `TEST_FIRMWARE` on the host without booting it:

```bash
TEST_MACHINE="${YOCTO_MACHINE:-qemuarm64}"
TEST_INSPECT=$(mktemp -d /tmp/iotbench-inspect.XXXXXX) &&
mkdir "$TEST_INSPECT/rootfs" &&
zstd -dc "deploy-images/$TEST_FIRMWARE/$TEST_MACHINE/iotbench-$TEST_FIRMWARE-$TEST_MACHINE.rootfs.ext4.zst" \
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

**Test — host:** inspect the extracted filesystem:

```bash
python3 scripts/test-embedded-auth-fixture.py --isolated-fixture \
  --rootfs "$TEST_INSPECT/rootfs" --variant native
echo "exit=$?"
```

Expected: the selected pair and its artifact are present, with no other
variant's credentials installed. Rootfs inspection does not execute an ARM
ELF on an x86 host and must be recorded separately from target execution.

### Scenario and scope

Additional family outside the 14 catalog assignments; **8 variants** per device.

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

Inspect the exported image offline; the root account is locked.

### Regression verification

**Test — host:**

All eight variants.

```bash
python3 -B scripts/test-embedded-auth-fixture.py --isolated-fixture
echo "exit=$?"
```

Add `--filesystem-roundtrip` to build/extract ext4 test artifacts with
`mke2fs` and `debugfs`. This remains a host fixture check, not a Yocto boot test.

Source: [cwe798-embedded-auth](../meta-iotbench/recipes-vulns/cwe798-embedded-auth/).
