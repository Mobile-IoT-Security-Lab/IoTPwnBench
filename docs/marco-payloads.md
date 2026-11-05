# Marco Payloads 🧪

## How to use this guide

Start by choosing a device keyword and a scenario keyword below, then build and boot the selected firmware. Each scenario explains its manual test, inputs and expected results. For `permit-empty-passwords`, one shared policy check covers every device. Execution evidence is stated separately from the test procedures.

### Common setup

- **Host**: the computer running Docker and QEMU. Open a terminal at the root of this repository, where `compose.yaml` and `scripts/` are located.
- **Guest**: the Linux firmware running inside QEMU. For tests marked as guest, wait for `login:` in the QEMU terminal and sign in with username `root` and password `routeradmin`. The password is not displayed while you type.
- **Second host terminal**: use this for host checks and firmware inspection; keep QEMU running in the first terminal during manual guest tests.

You need Docker Compose, plus QEMU and `zstd` on the host. The Python clients shown here require Python 3.9+; additional tools depend on the selected test. The manual SSH policy test uses the device dashboard. On macOS, install QEMU and zstd with `brew install qemu zstd`. Before the first build, or if your builder predates the Java layer, run on the host:

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

The firmware ID is `<device-keyword>-<scenario-keyword>`, for example `router-cwe521-permit-empty-passwords` or `doorlock-cwe521-permit-empty-passwords`. Choose the scenario keyword from the [manual test index](#manual-test-index). All scenarios listed there have a firmware recipe for each of these eleven devices. For a given scenario, the fixture's payloads and expected vulnerability signals are shared across devices; device identity, peripheral data and native service ports can differ. In particular, every `permit-empty-passwords` image uses the same SSH policy and dashboard procedure.

### Build and boot any device

Run the following commands in the same host terminal at the repository root. Change only `TEST_DEVICE` and `TEST_SCENARIO` to select a different firmware, then rerun the block. The default architecture is `qemuarm64`; for another supported architecture, set `YOCTO_MACHINE` consistently for build and boot.

On **Apple Silicon**, you can accelerate `qemuarm64` boots by running these commands in the host terminal before the boot commands:

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

The build exports its kernel and root filesystem to `deploy-images/<device-keyword>-<scenario-keyword>/<machine>/`. If you already have an up-to-date export, skip the Docker command and run the QEMU command after setting the three variables. After boot, use the selected scenario's test below. For `permit-empty-passwords`, go directly to [Test 1](#test-1) and run the manual check in the browser.

This command and the manual guides set HTTP to **18080**. When the selected image exposes its device dashboard, open <http://127.0.0.1:18080>; always use the port printed by the launcher. Apache, native path/buffer/connection/symlink and Java fixtures use the serial console and have no dashboard or forwarded network port. The embedded-auth extra locks root and is inspected offline as described in its test. Run one firmware at a time to avoid port conflicts.

Follow the selected scenario's test procedure. For example, `cwe276-bad-write-rights` uses the manual guest commands in [Test 2](#test-2): its FTP service runs in a private network namespace, with no ports forwarded to the host. Before guest tests, wait for `login:` and sign into the serial console. To quit QEMU, press **Ctrl-A**, release the keys, then press **X**. The launcher normally uses a disposable snapshot.

For CLI tests, run `echo "exit=$?"` **immediately after** the command you want to check. A status of `0` means success, but the specific output described in each guide confirms the defect. `INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE` messages are expected notices. Scripts that boot QEMU themselves must run after you close the manual instance.

### Manual test index

| Test | Scenario keyword | Where to run it | Evidence of the defect |
| --- | --- | --- | --- |
| [Test 1: SSH empty passwords](#test-1) | `cwe521-permit-empty-passwords` | Browser / guest inspection | Synthetic policy diagnostic permits an empty candidate; corrected control rejects it |
| [Test 2: FTP write permissions](#test-2) | `cwe276-bad-write-rights` | Guest / native curl | Real FTP creates a file in `bad`; `control` and corrected permissions reject creation |
| [Test 3: Telnet plaintext](#test-3) | `cwe798-unencrypted-traffic` | Guest / native Telnet and tcpdump | System login succeeds; packet capture exposes the password and device settings |
| [Test 4: Sudo environment](#test-4) | `cwe798-sudo-environment` | Guest / native sudo and du | Preserved environment doubles the real disk-usage count; explicit -k restores it |
| [Test 5: Cron wildcard](#test-5) | `cwe088-cronjob-wildcard-injection` | Guest | Option-like filename selects the diagnostic; corrected control stays nominal |
| [Test 6: Password leak](#test-6) | `cwe798-password-leak-<variant>` | Guest / extracted firmware | Recovered synthetic credential is accepted; wrong value is rejected |
| [Test 7: REST internal files](#test-7) | `cwe022-rest-internal-files` | Guest / isolated host | Config route returns the restricted synthetic marker; control denies it |
| [Test 8: Apache applications](#test-8) | `cwe<CWE>-apache-web` | Guest / isolated host | Selected defect produces its marker or unauthorized state change |
| [Test 9: C path and filename](#test-9) | `cwe022-native-path-traversal`, `cwe020-native-filename-validation` | Guest / isolated namespace | Disallowed synthetic file is read; outer containment or a nonmatching filename is rejected |
| [Test 10: C buffer overflow](#test-10) | `cwe787-native-buffer-overflow` | Host / guest with ASan | ASan identifies the first out-of-bounds write from a valid 65-byte frame |
| [Test 11: C connection string](#test-11) | `cwe020-native-connection-string` | Guest / host | Injected field changes SQLite from read-only to writable capability |
| [Test 12: C symbolic links](#test-12) | `cwe061-native-symlink-following` | Guest / isolated host | Fixed file follows the synthetic symlink; corrected control denies it |
| [Test 13: Java commands](#test-13) | `cwe078-java-os-command-injection`, `cwe077-java-app-command-injection` | Guest / isolated host | Selected interpreter creates its extra synthetic marker |
| [Test 14: Java deserialization](#test-14) | `cwe502-java-deserialization` | Guest / isolated host | Unexpected class triggers one callback; allowlist control triggers zero |
| [Extra: Embedded pairs](#extra-embedded) | `cwe798-embedded-auth-<variant>` | Host / extracted firmware | Matching synthetic pair is accepted; incorrect fields are denied |

The 14 tests cover 39 variants per device; the extra family adds eight. Choose one concrete variant wherever the index uses a placeholder.

### Technical references

The catalog is [Catalogo_Test_Sicurezza_Firmware_IoT.xlsm](../Catalogo_Test_Sicurezza_Firmware_IoT.xlsm). Execution evidence belongs in [validation records](validation/). Catalog numbers and variant counts appear in each test's scope section.

<a id="weakly-configured-ssh--empty-password-authentication-permitted-cwe-521"></a>
<a id="test-1"></a>

## Test 1: SSH empty-password policy — CWE-521

### Build, boot and manual testing

### Scenario and scope


<a id="weakly-configured-vsftpd-bad-write-rights"></a>
<a id="test-2"></a>

## Test 2: FTP write permissions — CWE-276

### Build, boot and manual testing

**What this tests.** Native vsftpd publishes build-time copies of this device's maintenance settings to an authenticated user whose intended policy is read-only. The `bad` directory incorrectly permits creation of new files; `control` denies it. This test performs real FTP transfers with `curl` and checks the resulting files in the guest filesystem. It uses no test-runner script.

**Build — host:**

Run from the repository root:

```bash
TEST_DEVICE=router
TEST_SCENARIO=cwe276-bad-write-rights
TEST_FIRMWARE="${TEST_DEVICE}-${TEST_SCENARIO}"

FIRMWARE="$TEST_FIRMWARE" docker compose run --rm yocto
```

Wait for a successful export. The named scenario selects its fixture build configuration automatically. Rebuild older exports to include the maintenance snapshots described below.

**Boot — host:**

```bash
QEMU_HTTP_PORT=18080 FIRMWARE="$TEST_FIRMWARE" ./scripts/run-qemu.sh
```

**Mini test — guest, one download and two upload attempts:**

This uses direct `curl` commands against native vsftpd. Here the maintenance account must authenticate, and the defect is an upload that should be denied. Run this short test or the detailed procedure below; start a fresh snapshot before  switching procedures. No firmware extraction is needed.

1. Start the fixture in the guest:

   ```sh
   touch /run/iotbench-ftp-write-test
   systemctl start iotbench-ftp-write.service
   systemctl is-active iotbench-ftp-write.service
   FTP_FIXTURE_PID=$(systemctl show --property=MainPID --value iotbench-ftp-write.service)
   echo "FTP PID=$FTP_FIXTURE_PID"
   ```

   Expect `active` and a positive PID; stop if either check fails. The `nsenter` prefix runs the client in the server's private network, where `127.0.0.1:2121` is reachable. Luca's host endpoint is not used here.

2. Download the router identity with the maintenance account:

   ```sh
   nsenter -t "$FTP_FIXTURE_PID" -n curl --fail --noproxy '*' \
     --ftp-method nocwd --ignore-content-length --user 'ftpfixture:Fixture-FTP-Only-42' \
     ftp://127.0.0.1:2121/bad/device.conf
   ```

   **Normal result:** the download contains `DEVICE_CLASS="router"`. Listing and downloading are allowed by the maintenance policy. `nocwd` and `--ignore-content-length` avoid the unsupported FTP `CWD` and `SIZE` commands.

3. Create a harmless text file and try uploading it to `bad`:

   ```sh
   printf '%s\n' 'iotbench-mini-upload' > /tmp/iotbench-ftp-mini.txt
   nsenter -t "$FTP_FIXTURE_PID" -n curl --fail --verbose --noproxy '*' \
     --ftp-method nocwd --user 'ftpfixture:Fixture-FTP-Only-42' \
     --upload-file /tmp/iotbench-ftp-mini.txt ftp://127.0.0.1:2121/bad/mini-probe.txt
   echo "upload_exit=$?"
   cat /srv/iotbench-ftp/bad/mini-probe.txt
   stat -c '%U:%G %a' /srv/iotbench-ftp/bad/mini-probe.txt
   ```

   **Concrete defect:** FTP completes the transfer (`226`), `upload_exit=0`, and the stored file contains `iotbench-mini-upload`, owned by `ftpfixture:ftpfixture` with mode `600`. The account created a real file despite its intended read-only access.

4. Upload the same file with the same account to `control`:

   ```sh
   nsenter -t "$FTP_FIXTURE_PID" -n curl --fail --verbose --noproxy '*' \
     --ftp-method nocwd --user 'ftpfixture:Fixture-FTP-Only-42' \
     --upload-file /tmp/iotbench-ftp-mini.txt ftp://127.0.0.1:2121/control/mini-probe.txt
   echo "control_exit=$?"
   ```

   **Expected control:** authentication succeeds (`230`), but file creation is rejected (`550` or `553`) and `control_exit` is nonzero. No  `/srv/iotbench-ftp/control/mini-probe.txt` is created. A connection or login failure is not evidence of correct write permissions. Both directories belong to `root:ftpfixture`; `bad` has mode `0775`, while `control` has mode `0755`.

**Finish the mini test — guest:**

```sh
systemctl stop iotbench-ftp-write.service
rm -f /run/iotbench-ftp-write-test /tmp/iotbench-ftp-mini.txt
rm -f /srv/iotbench-ftp/bad/mini-probe.txt
```

### Scenario and scope

**⚙️ Implementation.** Native `vsftpd` authenticates `ftpfixture` through PAM. Both directories belong to `root:ftpfixture`: `bad` is `0775`, allowing file creation despite the intended read-only policy; `control` is `0755`. Exported device settings are build-time snapshots.

**✅ Verification.** The same `curl` upload succeeds in `bad` (`226`, exit `0`, stored marker) and fails in `control` (`550`/`553`, nonzero exit, no file). Authentication must succeed in both cases.

> ⚠️ **Disclaimer:** Intentionally insecure lab fixture; not for deployment. Demonstrates **CWE-276**, not uploaded-file execution or authentication bypass (catalog: CWE-434/287). Startup is explicit; FTP uses a private network, chroot and unprivileged file operations, with no QEMU FTP forwarding.

Source: [cwe276-bad-write-rights](../meta-iotbench/recipes-vulns/cwe276-bad-write-rights/).

<a id="weakly-configured-telnet--unencrypted-traffic-cwe-798287276"></a>
<a id="test-3"></a>

## Test 3: Telnet plaintext traffic — CWE-798/287/276

### Build, boot and manual testing

**What this tests.** A maintenance operator logs into the firmware through native BusyBox `telnetd` and `/bin/login`, then reads the device's actual configuration. `tcpdump` records the TCP session: the login password, shell commands and returned configuration travel without encryption. Authentication uses a real, unprivileged system account and `/etc/shadow`; no Python server or predefined command responses are used.

**Build — host:**

Run from the repository root, where `compose.yaml` and `scripts/` are located:

```bash
TEST_DEVICE=router
TEST_SCENARIO=cwe798-unencrypted-traffic
TEST_FIRMWARE="${TEST_DEVICE}-${TEST_SCENARIO}"

FIRMWARE="$TEST_FIRMWARE" docker compose run --rm yocto
```

Wait for a successful export. Rebuild older images: they contain the former simulated service. Selecting this scenario enables the native BusyBox daemon automatically; the native `telnet` client, `tcpdump` and `nsenter` are installed in the guest.

**Boot — host, in the same terminal:**

```bash
QEMU_HTTP_PORT=18080 FIRMWARE="$TEST_FIRMWARE" ./scripts/run-qemu.sh
```

Wait for `login:` in the QEMU serial console and sign in as `root` with password `routeradmin`. Keep QEMU running. The following steps all run in that **guest console**; no browser, host Telnet connection or firmware extraction is needed.

**Manual test — guest:**

1. Start the native daemon and obtain its PID:

   ```sh
   touch /run/iotbench-telnet-test
   systemctl start iotbench-telnet.service
   systemctl is-active iotbench-telnet.service
   TELNET_PID=$(systemctl show --property=MainPID --value iotbench-telnet.service)
   echo "Telnet PID=$TELNET_PID"
   ```

   Expect `active` and a positive PID. Stop if either check fails. The service has its own network namespace; `nsenter -t "$TELNET_PID" -n` places the capture tool and client in that same network, where `127.0.0.1:2323` is reachable.

2. Start the packet capture in the background, then open the Telnet connection:

   ```sh
   nsenter -t "$TELNET_PID" -n tcpdump -i lo -nn -s 0 -U -Z root \
     -w /tmp/iotbench-telnet.pcap 'tcp port 2323' &
   CAPTURE_PID=$!
   sleep 1
   nsenter -t "$TELNET_PID" -n telnet 127.0.0.1 2323
   ```

   Wait for `tcpdump` to report `listening on lo`. At the Telnet `login:` prompt, press **Ctrl-]**, release the keys, then press **l** (lowercase L) to select **go to line mode** from BusyBox's escape menu. This sends each entered line together, making the capture easier to read. Type `maintenance` and press Enter. At `Password:`, type `Maintenance-Telnet-42` and press Enter. Enter each value only after its prompt. Line mode may echo the password locally; the packet capture is the evidence of network disclosure.

3. In the **Telnet maintenance shell**, enter these real commands one at a time:

   ```sh
   id
   cat /etc/iotbench/device.conf
   exit
   ```

   Expect a nonzero UID belonging to `maintenance`. For this router image, the configuration contains `DEVICE_NAME="Edge One"` and `DEVICE_CLASS="router"`. `exit` closes the maintenance shell and returns to the guest root console.

4. Back in the **guest root console**, stop and inspect the capture:

   ```sh
   kill -INT "$CAPTURE_PID"
   wait "$CAPTURE_PID"
   tcpdump -nn -A -r /tmp/iotbench-telnet.pcap 'tcp dst port 2323'
   tcpdump -nn -A -r /tmp/iotbench-telnet.pcap 'tcp src port 2323'
   ```

   The first command shows **client-to-server** traffic: find `Maintenance-Telnet-42` and `cat /etc/iotbench/device.conf` in packets whose destination is `127.0.0.1.2323`. The second shows **server-to-client** traffic: find the returned device settings. The lab banner also contains the public password; that banner alone is not evidence that the submitted password was sent in cleartext. Telnet negotiation bytes and TCP headers can appear as unreadable characters. These are real packets, with no decryption or generated transcript.

5. Check normal authentication rejection, then stop the service:

   ```sh
   nsenter -t "$TELNET_PID" -n telnet 127.0.0.1 2323
   ```

   Enter `maintenance` at `login:` and `wrong-password` at `Password:`. Expect `Login incorrect` and no maintenance shell. In this second session, keep the client's default character mode. Press **Ctrl-]**, release the keys, then press **e** to leave the client and return to the guest root console:

   ```sh
   systemctl stop iotbench-telnet.service
   rm /run/iotbench-telnet-test
   ```

**Expected behaviour:**

| Check | Expected result |
| --- | --- |
| Correct maintenance credentials | A real shell running as `maintenance`, with a nonzero UID |
| Read device settings | Actual `/etc/iotbench/device.conf` content, matching the selected device |
| Wrong password | `Login incorrect`; no maintenance shell |
| Inspect captured TCP traffic | Submitted password and command readable toward port 2323; device settings readable in the reply |

Successful authentication and a configuration read establish normal operation. The concrete defect is the readable password and configuration in the packet capture. A successful login alone does not prove this transport defect.

### Scenario and scope

**⚙️ Implementation.** BusyBox `telnetd` invokes `/bin/login` for unprivileged `maintenance`, whose fixed lab password is hashed in `/etc/shadow`. Telnet sends the password, commands and device settings without encryption.

**✅ Verification.** `tcpdump` must show the submitted password and command toward port `2323`, and device settings in replies. Wrong credentials must yield `Login incorrect`. The server banner alone is insufficient evidence.

> ⚠️ **Disclaimer:** Intentionally insecure lab fixture; not for deployment. Demonstrates **CWE-319/798**, not catalog mappings CWE-287/276. Explicit startup, guest loopback, a private network and read-only firmware filesystem contain the service; QEMU forwards no Telnet port.

Source: [cwe798-unencrypted-traffic](../meta-iotbench/recipes-vulns/cwe798-unencrypted-traffic/).

<a id="bad-sudo-rights--allow-changes-to-environment-variables-cwe-798"></a>
<a id="test-4"></a>

## Test 4: Bad SUDO Rights — allow changes to environment variables — CWE-798

### Build, boot and manual testing

**What this tests.** The locked `fixtureenv` account may run an exact native
maintenance report through `sudo`. Its policy resets the environment but
explicitly keeps `POSIXLY_CORRECT`. The real BusyBox `du` then changes the
implicit report unit from 1024 to 512 bytes when that preserved variable is
set. The report reads the selected firmware's installed `/etc/iotbench`
directory; no helper, fixed response, or file mutation is involved.

**Build — host:**

Run from the repository root:

```bash
TEST_DEVICE=router
TEST_SCENARIO=cwe798-sudo-environment
TEST_FIRMWARE="${TEST_DEVICE}-${TEST_SCENARIO}"

FIRMWARE="$TEST_FIRMWARE" docker compose run --rm yocto
```

Wait for a successful export. Selecting this scenario activates its required
fixture build mode and opt-in through the existing builder. Rebuild an older
export before testing it.

**Boot — host:**

```bash
QEMU_HTTP_PORT=18080 FIRMWARE="$TEST_FIRMWARE" ./scripts/run-qemu.sh
```

At the QEMU serial console, log in as `root` with password `routeradmin`. Run
the following commands in that **guest console**. The outer `sudo -u
fixtureenv` only starts the locked fixture account from the root test console;
the inner `sudo` is the restricted privileged operation being tested.

**Manual test — guest:**

1. Confirm that the permitted maintenance command runs as root:

   ```sh
   sudo -n -u fixtureenv -- /usr/bin/sudo -n /usr/bin/id -u
   echo "identity_exit=$?"
   ```

   Expected: `0`, then `identity_exit=0`. This proves that the inner command
   reached the policy-authorized root execution path.

2. Run the normal, environment-free baseline:

   ```sh
   unset POSIXLY_CORRECT
   sudo -n -u fixtureenv -- /usr/bin/sudo -n /usr/bin/du -s /etc/iotbench
   echo "baseline_exit=$?"
   ```

   For the router image, expect `3 /etc/iotbench` and `baseline_exit=0`.

3. Supply the one preserved environment variable before invoking the same
   authorized report:

   ```sh
   sudo -n -u fixtureenv -- /usr/bin/env POSIXLY_CORRECT=1 \
     /usr/bin/sudo -n /usr/bin/du -s /etc/iotbench
   echo "environment_exit=$?"
   ```

   For the router image, expect `6 /etc/iotbench` and
   `environment_exit=0`. The directory is unchanged, but the implicit unit is
   now 512 bytes, so the numeric report is exactly twice the baseline.

4. Keep the environment input but select `du`'s explicit 1024-byte-unit
   control:

   ```sh
   sudo -n -u fixtureenv -- /usr/bin/env POSIXLY_CORRECT=1 \
     /usr/bin/sudo -n /usr/bin/du -sk /etc/iotbench
   echo "control_exit=$?"
   ```

   Expected for the router: `3 /etc/iotbench` and `control_exit=0`. Thus the
   changed value in step 3 is caused by the preserved environment variable,
   not by a different directory or changed allocation. Other device images can
   have a different baseline count, but their environment-sensitive count must
   be exactly twice that baseline and their `-sk` control must return it.

Repeat steps 2–4 without changing the guest: their three counts remain in the
same baseline/doubled/baseline relation. Quit QEMU with **Ctrl-A**, then **X**.

### Scenario and scope

**⚙️ Implementation.** `/etc/sudoers.d/iotbench-sudo-environment` uses
`env_reset`, `!setenv`, and an allowlist containing only
`POSIXLY_CORRECT`. It grants `fixtureenv` three exact root commands:
`/usr/bin/id -u`, `/usr/bin/du -s /etc/iotbench`, and
`/usr/bin/du -sk /etc/iotbench`. The real `/usr/bin/du` is the BusyBox applet
installed in the firmware; the device configuration directory is provided by
the selected device profile.

**✅ Verification.** A root identity, an environment-free baseline, the
preserved-variable result, and the explicit-unit control are all required.
For `router`, the observable sequence is `3`, `6`, `3`; the same relation is
the acceptance criterion for every supported device profile.

> ⚠️ **Disclaimer:** Intentionally insecure lab fixture; not for deployment.
> It demonstrates environment influence on a restricted privileged report, not
> arbitrary root execution, changed disk allocation, or hardcoded credentials.
> `CWE-798` is retained as the historical catalog label.

Source: [cwe798-sudo-environment](../meta-iotbench/recipes-vulns/cwe798-sudo-environment/).

<a id="cronjob-wildcard-injection-cwe-8878269"></a>
<a id="test-5"></a>

## Test 5: Vulnerable cronjob configurations — Cronjob wildcard injection — CWE-88/78/269

### Build, boot and manual testing

**What this tests.** A real root-run CrOniE job invokes a shell command that
changes into a dedicated, fixturefiles-writable inbox and passes a bare `*` to
a parser-only native maintenance helper. A filename beginning with `-` is
therefore interpreted as an option. The fixed `--` form treats the identical
filename as an operand.

**Build — host:**

Run from the repository root:

```bash
TEST_DEVICE=router
TEST_SCENARIO=cwe088-cronjob-wildcard-injection
TEST_FIRMWARE="${TEST_DEVICE}-${TEST_SCENARIO}"

FIRMWARE="$TEST_FIRMWARE" docker compose run --rm yocto
```

Wait for a successful export. Selecting this scenario enables its required
fixture build mode and opt-in through the existing builder. Rebuild any older
export: it contains the former inert schedule.

**Boot — host:**

```bash
QEMU_HTTP_PORT=18080 FIRMWARE="$TEST_FIRMWARE" ./scripts/run-qemu.sh
```

At the QEMU serial console, log in as `root` with password `routeradmin`. Run
the following commands in that **guest console**. The guest root console is
used only to reproduce the local lab fixture; the input file itself is created
by the restricted `fixturefiles` account.

**Manual test — guest:**

1. Confirm that the image contains the active cron configuration and daemon:

   ```sh
   CRON_ROOT=/usr/share/iotbench/cronjob-wildcard-injection
   test -f /etc/cron.d/iotbench-cron-wildcard-injection
   grep -F -- '--fixture-test *' /etc/cron.d/iotbench-cron-wildcard-injection
   systemctl is-active crond.service
   ```

   Expected: the second command prints the root schedule with its bare `*`,
   and the last command prints `active`. Do not continue if either check fails.

2. Run the normal baseline with only the two installed `.record` names:

   ```sh
   rm -f "$CRON_ROOT/inbox/--fixture-diagnostic" \
     "$CRON_ROOT/logs/cron-vulnerable.jsonl"
   sleep 70
   cat "$CRON_ROOT/logs/cron-vulnerable.jsonl"
   ```

   Expected: the log names `alpha.record` and `beta.record` as `operand`s and
   ends with `"options":0,"operands":2,"result":"nominal"`. The 70-second
   wait crosses a real one-minute cron tick.

3. Create the concrete option-like filename as the only non-root writer, then
   let the next cron execution consume it:

   ```sh
   su -s /bin/sh fixturefiles -c \
     'touch -- /usr/share/iotbench/cronjob-wildcard-injection/inbox/--fixture-diagnostic'
   stat -c '%U:%G %a %n' "$CRON_ROOT/inbox/--fixture-diagnostic"
   rm -f "$CRON_ROOT/logs/cron-vulnerable.jsonl"
   sleep 70
   cat "$CRON_ROOT/logs/cron-vulnerable.jsonl"
   ```

   Expected: `stat` reports `fixturefiles:fixturefiles`; the fresh cron log
   contains `"kind":"option","argument":"--fixture-diagnostic"` and ends
   with `"options":1,"operands":2,"result":"synthetic-diagnostic"`. This
   differs from the baseline solely because the filename crossed the cron
   wildcard-to-argument boundary.

4. Run the exact secure command form against the unchanged inbox:

   ```sh
   (
     cd "$CRON_ROOT/inbox" || exit
     "$CRON_ROOT/bin/fixture-maintenance" --fixture-test -- *
   ) > "$CRON_ROOT/logs/secure-control.jsonl"
   cat "$CRON_ROOT/logs/secure-control.jsonl"
   ```

   Expected: the same `--fixture-diagnostic` value is an `operand`, not an
   `option`, and the final result is `"options":0,"operands":3,"result":"nominal"`.
   This is the command stored in the package's secure cron control.

5. To check repeatability, remove only the vulnerable log, wait one more tick
   and inspect its final event:

   ```sh
   rm -f "$CRON_ROOT/logs/cron-vulnerable.jsonl"
   sleep 70
   tail -n 1 "$CRON_ROOT/logs/cron-vulnerable.jsonl"
   ```

   Expected: the result remains `synthetic-diagnostic` while the option-like
   filename remains in the inbox. Quit QEMU with **Ctrl-A**, then **X**.

### Scenario and scope

**⚙️ Implementation.** The shared package installs `cronie`, a root-owned
`0644` schedule at `/etc/cron.d/iotbench-cron-wildcard-injection`, and a
root-owned diagnostic helper. `fixturefiles` (UID/GID 988) is the sole intended
non-root writer of the dedicated `0750` inbox. CrOniE runs the vulnerable
command as root once per minute; the helper itself only classifies argument
strings and emits JSON. It does not read operand contents, execute commands,
change UID, write files, listen on a network, or provide a remote entry point.

**✅ Verification.** Evidence requires the active CrOniE service and installed
schedule, a normal baseline, the option result after the concrete filename is
created by `fixturefiles`, the `--` control, and a repeated scheduled result.
The log is produced by the actual cron command, not by the legacy Python
emulator.

> ⚠️ **Disclaimer:** Intentionally insecure lab fixture; not for deployment.
> It demonstrates filename-to-option injection in a controlled cron job, not
> shell command execution, privilege escalation, persistence outside the
> disposable QEMU image, or access to any non-fixture data.

Source: [cwe088-cronjob-wildcard-injection](../meta-iotbench/recipes-vulns/cwe088-cronjob-wildcard-injection/).

<a id="password-leak--different-file-types-and-patterns-cwe-798"></a>
<a id="test-6"></a>

## Test 6: Password Leak — Different File Types and Patterns — CWE-798

### Build, boot and manual testing

**What this tests.** Each image deliberately installs one synthetic
credential-bearing file and a native local consumer. The consumer rereads the
selected installed file, extracts its configured field, and compares one stdin
candidate. It does not source or execute fixture data, create an account, start
a service, or contact a network.

**Build — host:**

Run from the repository root:

```bash
TEST_DEVICE=router
TEST_SCENARIO=cwe798-password-leak-conf-password
TEST_FIRMWARE="$TEST_DEVICE-$TEST_SCENARIO"

FIRMWARE="$TEST_FIRMWARE" docker compose run --rm \
  -e IOTBENCH_BUILD_MODE=fixture \
  -e IOTBENCH_ENABLE_PASSWORD_LEAK_FIXTURE=1 yocto
```

Both explicit variables are required: production/catalog builds cannot resolve
this package. Replace `router` with any [device keyword](#device-keywords) to
build the same variant for another supported device profile.

**Boot — host:**

```bash
FIRMWARE="$TEST_FIRMWARE" ./scripts/run-qemu.sh
```

At the serial console, log in as `root` with password `routeradmin`. Run all
remaining commands in the **guest**. This is a local filesystem fixture; no
Python command or test-runner script is used.

**Manual test — guest:**

1. Inspect the leaked file and native consumer:

   ```sh
   FIXTURE_ROOT=/usr/share/iotbench/password-leak/conf-password
   stat -c '%U:%G %a %n' "$FIXTURE_ROOT/auth.conf" "$FIXTURE_ROOT/fixture-auth"
   cat "$FIXTURE_ROOT/auth.conf"
   ```

   Expected: `auth.conf` is `root:root 644`, `fixture-auth` is
   `root:root 755`, and the file contains `password=FIXTURE_PASSWORD_001`.

2. Send a normal incorrect candidate:

   ```sh
   printf '%s\n' 'wrong-value' | "$FIXTURE_ROOT/fixture-auth" --isolated-fixture
   echo "baseline_exit=$?"
   ```

   Expected: `synthetic-auth: rejected` and `baseline_exit=1`.

3. Use the concrete credential recovered from the installed file:

   ```sh
   printf '%s\n' 'FIXTURE_PASSWORD_001' | "$FIXTURE_ROOT/fixture-auth" --isolated-fixture
   echo "recovered_exit=$?"
   ```

   Expected: `synthetic-auth: accepted` and `recovered_exit=0`.

4. Confirm that the consumer requires that source file, then restore it
   immediately:

   ```sh
   mv "$FIXTURE_ROOT/auth.conf" "$FIXTURE_ROOT/auth.conf.off"
   printf '%s\n' 'FIXTURE_PASSWORD_001' | "$FIXTURE_ROOT/fixture-auth" --isolated-fixture
   echo "source_control_exit=$?"
   mv "$FIXTURE_ROOT/auth.conf.off" "$FIXTURE_ROOT/auth.conf"
   ```

   Expected while the file is absent: `synthetic-auth: unavailable` and
   `source_control_exit=77`. The final `mv` restores the current guest; the
   disposable QEMU snapshot also discards the temporary rename.

5. Repeat the recovered candidate after restoration:

   ```sh
   printf '%s\n' 'FIXTURE_PASSWORD_001' | "$FIXTURE_ROOT/fixture-auth" --isolated-fixture
   echo "repeat_exit=$?"
   ```

   Expected: `synthetic-auth: accepted` and `repeat_exit=0`.

**Concrete Base64 pattern — optional second manual image:**

Build and boot a second, reversible representation:

```bash
TEST_DEVICE=router
TEST_SCENARIO=cwe798-password-leak-env-base64
TEST_FIRMWARE="$TEST_DEVICE-$TEST_SCENARIO"

FIRMWARE="$TEST_FIRMWARE" docker compose run --rm \
  -e IOTBENCH_BUILD_MODE=fixture \
  -e IOTBENCH_ENABLE_PASSWORD_LEAK_FIXTURE=1 yocto
FIRMWARE="$TEST_FIRMWARE" ./scripts/run-qemu.sh
```

After the normal guest login, run:

```sh
FIXTURE_ROOT=/usr/share/iotbench/password-leak/env-base64
cat "$FIXTURE_ROOT/encoded.env"
printf '%s\n' 'wrong-value' | "$FIXTURE_ROOT/fixture-auth" --isolated-fixture
echo "baseline_exit=$?"
printf '%s\n' 'FIXTURE_ENCODED_PASSWORD_001' | "$FIXTURE_ROOT/fixture-auth" --isolated-fixture
echo "recovered_exit=$?"
```

Expected: `encoded.env` contains
`PASSWORD_B64="RklYVFVSRV9FTkNPREVEX1BBU1NXT1JEXzAwMQ=="`; the wrong candidate
is rejected with exit `1` and the decoded synthetic value is accepted with
exit `0`. The native consumer performs Base64 decoding itself.

### Scenario and scope

**⚙️ Implementation.** The 15 variants cover `.conf`, `.cfg`, `.ini`, `.env`,
`.json`, `.xml`, shell, C/header, properties, init, log and text patterns;
`json-base64` and `env-base64` are the encoded forms. Each of the eleven device
profiles has one image per variant (165 recipes). The selected image contains
exactly one credential-bearing source file under
`/usr/share/iotbench/password-leak/<variant>/`. Its `fixture-auth` ELF reads
that file through installed metadata, handles key-value, INI, JSON, XML or
C-literal syntax, and internally decodes Base64. Build and rootfs guards
require fixture mode, one variant, ordinary root-owned permissions, the native
helper, and no duplicate credential in that helper.

**✅ Verification.** Evidence requires the installed source file, rejected
wrong input, accepted recovered input, the temporary-source control returning
`77`, and repeated acceptance after restoration. The separate `env-base64`
image confirms an encoded representation reaches the same native path.

> ⚠️ **Disclaimer:** Intentionally insecure lab fixture; not for deployment.
> It demonstrates a recoverable synthetic credential in firmware files
> (**CWE-798**), not a real OS account, external authentication, remote access,
> command execution, or persistence.

Source: [cwe798-password-leak](../meta-iotbench/recipes-vulns/cwe798-password-leak/).

<a id="exploitable-rest-interface--internal-files-cwe-22cwe-73"></a>
<a id="test-7"></a>

## Test 7: Exploitable REST interface — internal files — CWE-22/CWE-73

### Build, boot and manual testing

**What this tests.** A native HTTP-style REST service reads a requested file
under its intended `fs/api/` directory. On the vulnerable configuration route,
the client-controlled `file` value is concatenated without enforcing that
directory boundary, so a concrete `../restricted/marker.txt` value reads a
real internal synthetic file. The socket and all files remain inside the guest.

**Build — host:**

Run from the repository root:

```bash
TEST_DEVICE=router
TEST_SCENARIO=cwe022-rest-internal-files
TEST_FIRMWARE="$TEST_DEVICE-$TEST_SCENARIO"

FIRMWARE="$TEST_FIRMWARE" docker compose run --rm yocto
```

The selected scenario enables its required fixture build mode and opt-in through
the existing builder. It exports the image under
`deploy-images/router-cwe022-rest-internal-files/qemuarm64/`. Replace `router`
with any [device keyword](#device-keywords) to build the same fixture for a
different supported device profile.

**Boot — host:**

```bash
FIRMWARE="$TEST_FIRMWARE" ./scripts/run-qemu.sh
```

At the serial console, log in as `root` with password `routeradmin`. Run all
remaining commands in the **guest**. The service has no TCP or UDP listener:
the REST request travels only through a guest Unix-domain socket, so do not use
a browser or a host URL.

**Manual test — guest:**

1. Start the intentionally vulnerable server and confirm its private socket:

   ```sh
   REST_ROOT=/usr/share/iotbench/rest-internal-files
   stat -c '%U:%G %a %n' "$REST_ROOT/bin/fixture-rest" "$REST_ROOT/run"
   cat "$REST_ROOT/fs/.fixture-test-only"
   rm -f "$REST_ROOT/run/rest.sock" /tmp/iotbench-rest-vulnerable.log
   "$REST_ROOT/bin/fixture-rest" --isolated-fixture \
     > /tmp/iotbench-rest-vulnerable.log 2>&1 &
   REST_PID=$!
   sleep 1
   test -S "$REST_ROOT/run/rest.sock" && echo 'socket_ready=yes'
   ```

   Expected: the binary is `root:root 755`, `run` is `root:root 700`, the
   manifest says `mode=fixture` and `enabled=1`, and `socket_ready=yes` prints.

2. Send an in-bound baseline request:

   ```sh
   curl --path-as-is --unix-socket "$REST_ROOT/run/rest.sock" -sS -i \
     'http://fixture/api/config?file=config.cfg'
   echo "baseline_exit=$?"
   ```

   Expected: `HTTP/1.1 200 OK`, followed by
   `device=synthetic-fixture`, `profile=lab-only`, and `baseline_exit=0`.

3. Send the concrete boundary-crossing input and compare its response with the
   installed internal file:

   ```sh
   curl --path-as-is --unix-socket "$REST_ROOT/run/rest.sock" -sS -i \
     'http://fixture/api/config?file=%2e%2e%2frestricted%2fmarker.txt'
   echo "traversal_exit=$?"
   cat "$REST_ROOT/fs/restricted/marker.txt"
   cat /tmp/iotbench-rest-vulnerable.log
   ```

   Expected: `HTTP/1.1 200 OK`,
   `IOTBENCH_SYNTHETIC_REST_BOUNDARY_MARKER`, and `traversal_exit=0`. The
   marker printed by `cat` must match the REST response. The log must contain
   `fixture-read path=api/../restricted/marker.txt result=opened`, establishing
   that the response came from the internal file rather than a fixed response.
   Run the same `curl` command once more without changing the guest: it must
   again return `200` and the marker.

4. Replace the vulnerable process with the installed secure control and submit
   the identical input:

   ```sh
   kill "$REST_PID"
   wait "$REST_PID" 2>/dev/null || true
   rm -f "$REST_ROOT/run/rest.sock"
   "$REST_ROOT/bin/fixture-rest-secure" --isolated-fixture \
     > /tmp/iotbench-rest-secure.log 2>&1 &
   SECURE_PID=$!
   sleep 1
   curl --path-as-is --unix-socket "$REST_ROOT/run/rest.sock" -sS -i \
     'http://fixture/api/config?file=%2e%2e%2frestricted%2fmarker.txt'
   echo "secure_control_exit=$?"
   cat /tmp/iotbench-rest-secure.log
   kill "$SECURE_PID"
   wait "$SECURE_PID" 2>/dev/null || true
   rm -f "$REST_ROOT/run/rest.sock"
   ```

   Expected: `HTTP/1.1 403 Forbidden`, `file unavailable`, and
   `secure_control_exit=0`. The secure log contains only its readiness line;
   it must not report opening the restricted path. The QEMU snapshot discards
   the two temporary log files on exit.

### Scenario and scope

**⚙️ Implementation.** Each of the eleven
`<device>-cwe022-rest-internal-files` images installs only
`cwe022-rest-internal-files` as its vulnerability package. The vulnerable
route decodes the `file` query parameter, constructs `api/<file>`, and opens it
read-only with `openat2` relative to the fixture's `fs/` directory. The
intentional missing check is the `api/`-directory boundary: `api/../restricted/marker.txt`
therefore resolves to the installed synthetic marker. The kernel confinement
still prevents traversal outside `fs/`; no arbitrary guest or host file is
reachable. The separate `fixture-rest-secure` binary permits only a basename.

**✅ Verification.** The rebuilt `router` `qemuarm64` image was manually
checked with the commands above: the ordinary configuration read returned 200,
the concrete traversal returned the exact marker and an `opened` log entry, the
same request to the secure control returned 403, and a repeated vulnerable
request returned the same marker. These checks exercise HTTP parsing, file
opening and response construction in the built guest binary.

> ⚠️ **Disclaimer:** Intentionally insecure lab fixture; not for deployment.
> It demonstrates a controlled **CWE-22/CWE-73** path-boundary failure, not
> arbitrary file read, external network access, file modification, command
> execution, remote access, or persistence.

Source: [cwe022-rest-internal-files](../meta-iotbench/recipes-vulns/cwe022-rest-internal-files/).

<a id="exploitable-apache-application-fixtures"></a>
<a id="test-8"></a>

## Test 8: Apache web applications — CWE-89, CWE-79, CWE-20, CWE-352, CWE-78, CWE-22, CWE-77, CWE-306, CWE-862, CWE-287

### Build, boot and manual testing

**What this tests.** Each image contains a real Apache CGI application with
one selected, intentionally vulnerable web flow. The selected flow runs only
inside a disposable user/mount/network/PID namespace on guest loopback. Apache
does not start at boot and QEMU receives no NIC or host port-forwarding.

There are ten variants for each of the eleven device profiles. Build and boot
one variant at a time; the other nine application routes are absent from that
image.

| CWE | Firmware scenario |
| --- | --- |
| CWE-89 | `cwe089-apache-web` |
| CWE-79 | `cwe079-apache-web` |
| CWE-20 | `cwe020-apache-web` |
| CWE-352 | `cwe352-apache-web` |
| CWE-78 | `cwe078-apache-web` |
| CWE-22 | `cwe022-apache-web` |
| CWE-77 | `cwe077-apache-web` |
| CWE-306 | `cwe306-apache-web` |
| CWE-862 | `cwe862-apache-web` |
| CWE-287 | `cwe287-apache-web` |

**Build and boot — host:**

For example, to exercise the CWE-89 router image, run from the repository
root:

```bash
FIRMWARE=router-cwe089-apache-web docker compose run --rm yocto
FIRMWARE=router-cwe089-apache-web ./scripts/run-qemu.sh
```

Replace only `router-cwe089-apache-web` with one literal firmware ID from the
table above, using any supported device keyword. Wait for `login:` and sign in
as `root` with password `routeradmin`. All remaining commands run in the guest
serial console. Do not use a host URL: this image has no guest network device.

**Start the selected fixture — guest:**

```sh
rm -f /tmp/iotbench-apache.log
su -s /bin/sh -c 'cd /usr/share/iotbench/apache-fixture && ./manual-launch.sh --isolated-fixture > /tmp/iotbench-apache.log 2>&1 &' iotapache
until grep -q '^manual-apache-ready' /tmp/iotbench-apache.log; do sleep 1; done
cat /tmp/iotbench-apache.log
FIXTURE_PID=$(sed -n 's/^manual-launch-pid=//p' /tmp/iotbench-apache.log | tail -n 1)
```

Expected: `manual-apache-ready variant=CWE-... uid=1000`. The launcher only
stages fixed package files and starts Apache; it sends no HTTP request and makes
no assertion. `FIXTURE_PID` identifies its private network namespace.

The following login establishes a disposable admin session for CWE-89, CWE-79,
CWE-20, CWE-352, CWE-78, CWE-22 and CWE-77. It is not needed for CWE-306, and
CWE-862 and CWE-287 have their own commands below.

```sh
nsenter -t "$FIXTURE_PID" -n -- curl -sS --max-time 5 \
  -D /tmp/apache-login.headers -o /tmp/apache-login.json \
  -X POST -H 'Origin: http://127.0.0.1:18080' \
  --data-urlencode 'identity=admin' \
  --data-urlencode 'proof=fixture-admin-proof' \
  http://127.0.0.1:18080/app/login
SESSION=$(sed -n 's/^Set-Cookie: fixture_session=\([^;]*\).*/fixture_session=\1/p' /tmp/apache-login.headers | tr -d '\r')
CSRF=$(sed -n 's/.*"csrf": "\([^"]*\)".*/\1/p' /tmp/apache-login.json)
sed -n '1p' /tmp/apache-login.headers
cat /tmp/apache-login.json
```

Expected: HTTP 200, an `identity` of `admin`, and nonempty `SESSION` and `CSRF`
values. They are random per launcher invocation.

**Manual cases — guest:**

Run the two commands for the image selected at build time. The first is the
ordinary baseline where useful; the second is the concrete input that reaches
the intended condition.

**CWE-89 — SQL query construction.**

```sh
nsenter -t "$FIXTURE_PID" -n -- curl -sS --max-time 5 --get \
  --cookie "$SESSION" --data-urlencode 'name=public' \
  http://127.0.0.1:18080/app/query
nsenter -t "$FIXTURE_PID" -n -- curl -sS --max-time 5 --get \
  --cookie "$SESSION" --data-urlencode "name=' OR designated=1 --" \
  http://127.0.0.1:18080/app/query
```

Expected: the baseline returns `synthetic-public-record`; the second response
returns `synthetic-sql-sentinel`. The database is read-only, so this is a
bounded query-result witness rather than a database modification.

**CWE-79 — reflected HTML.**

```sh
nsenter -t "$FIXTURE_PID" -n -- curl -sS --max-time 5 --get \
  --cookie "$SESSION" --data-urlencode 'message=ordinary' \
  http://127.0.0.1:18080/app/reflect
nsenter -t "$FIXTURE_PID" -n -- curl -sS --max-time 5 --get \
  --cookie "$SESSION" \
  --data-urlencode 'message=<script>document.body.dataset.fixture="xss-marker"</script>' \
  http://127.0.0.1:18080/app/reflect
```

Expected: the first response contains `<main>ordinary</main>`; the second
contains the literal unencoded `<script>` element inside `main`. The terminal
test observes the missing output encoding; it deliberately does not execute a
browser payload.

**CWE-20 — missing numeric upper bound.**

```sh
nsenter -t "$FIXTURE_PID" -n -- curl -sS --max-time 5 -X POST \
  -H 'Origin: http://127.0.0.1:18080' --cookie "$SESSION" \
  --data-urlencode "csrf=$CSRF" --data-urlencode 'level=100' \
  http://127.0.0.1:18080/app/level
nsenter -t "$FIXTURE_PID" -n -- curl -sS --max-time 5 -X POST \
  -H 'Origin: http://127.0.0.1:18080' --cookie "$SESSION" \
  --data-urlencode "csrf=$CSRF" --data-urlencode 'level=101' \
  http://127.0.0.1:18080/app/level
```

Expected: the first response reports `"level": 100` and
the second reports `"level": 101`, although the fixture contract is 0 through
100 inclusive.

**CWE-352 — missing CSRF decision.**

```sh
nsenter -t "$FIXTURE_PID" -n -- curl -sS --max-time 5 -X POST \
  -H 'Origin: http://127.0.0.1:18080' --cookie "$SESSION" \
  --data-urlencode 'value=ordinary' \
  http://127.0.0.1:18080/app/setting
nsenter -t "$FIXTURE_PID" -n -- curl -sS --max-time 5 -X POST \
  -H 'Origin: http://127.0.0.1:18081' --cookie "$SESSION" \
  --data-urlencode 'value=csrf-marker' \
  http://127.0.0.1:18080/app/setting
```

Expected: the first response contains `"value": "ordinary"`. The second has
the local second-origin header and no CSRF token, but still returns
`"value": "csrf-marker"`.

**CWE-78 — shell command construction.**

```sh
HTTPD_PID=$(pidof httpd | awk '{print $1}')
nsenter -t "$HTTPD_PID" -m -- /usr/bin/cat /state/shell.marker 2>/dev/null || echo 'shell-marker=absent'
nsenter -t "$FIXTURE_PID" -n -- curl -sS --max-time 5 -X POST \
  -H 'Origin: http://127.0.0.1:18080' --cookie "$SESSION" \
  --data-urlencode "csrf=$CSRF" --data-urlencode 'label=ordinary' \
  http://127.0.0.1:18080/app/diagnostic
nsenter -t "$FIXTURE_PID" -n -- curl -sS --max-time 5 -X POST \
  -H 'Origin: http://127.0.0.1:18080' --cookie "$SESSION" \
  --data-urlencode "csrf=$CSRF" \
  --data-urlencode 'label=ordinary; printf shell-marker > shell.marker; #' \
  http://127.0.0.1:18080/app/diagnostic
nsenter -t "$HTTPD_PID" -m -- /usr/bin/cat /state/shell.marker
```

Expected: both requests report `"ran": true`; the final command prints
`shell-marker`. The file is a tmpfs marker inside the private fixture mount,
not a guest or host file.

**CWE-22 — allowed-directory escape.**

```sh
nsenter -t "$FIXTURE_PID" -n -- curl -sS --max-time 5 --get \
  --cookie "$SESSION" --data-urlencode 'file=public.txt' \
  http://127.0.0.1:18080/app/file
nsenter -t "$FIXTURE_PID" -n -- curl -sS --max-time 5 --get \
  --cookie "$SESSION" --data-urlencode 'file=../sentinel.txt' \
  http://127.0.0.1:18080/app/file
```

Expected: the baseline returns `synthetic-public`; the second response returns
`synthetic-traversal-sentinel`, which exists only in the fixture state tree.

**CWE-77 — application command interpreter.**

```sh
HTTPD_PID=$(pidof httpd | awk '{print $1}')
nsenter -t "$HTTPD_PID" -m -- /usr/bin/cat /state/interpreter.marker 2>/dev/null || echo 'interpreter-marker=absent'
nsenter -t "$FIXTURE_PID" -n -- curl -sS --max-time 5 -X POST \
  -H 'Origin: http://127.0.0.1:18080' --cookie "$SESSION" \
  --data-urlencode "csrf=$CSRF" --data-urlencode 'label=ordinary' \
  http://127.0.0.1:18080/app/command
nsenter -t "$FIXTURE_PID" -n -- curl -sS --max-time 5 -X POST \
  -H 'Origin: http://127.0.0.1:18080' --cookie "$SESSION" \
  --data-urlencode "csrf=$CSRF" --data-urlencode 'label=ordinary; MARK' \
  http://127.0.0.1:18080/app/command
nsenter -t "$HTTPD_PID" -m -- /usr/bin/cat /state/interpreter.marker
```

Expected: the first response shows `ordinary`; the second prints
`application-command-marker`. This variant invokes only the synthetic
application grammar, not an operating-system shell.

**CWE-306 — critical write without authentication.**

```sh
nsenter -t "$FIXTURE_PID" -n -- curl -sS --max-time 5 -X POST \
  --data-urlencode 'value=ordinary' \
  http://127.0.0.1:18080/app/critical
nsenter -t "$FIXTURE_PID" -n -- curl -sS --max-time 5 -X POST \
  --data-urlencode 'value=unauthenticated-marker' \
  http://127.0.0.1:18080/app/critical
```

Expected: the first response contains `"value": "ordinary"`; the second
contains `"value": "unauthenticated-marker"`, without any cookie or login.

**CWE-862 — authenticated reader changes an admin setting.**

```sh
nsenter -t "$FIXTURE_PID" -n -- curl -sS --max-time 5 -o /dev/null -w '%{http_code}\n' \
  -X POST --data-urlencode 'csrf=arbitrary' --data-urlencode 'value=ordinary' \
  http://127.0.0.1:18080/app/admin-setting
nsenter -t "$FIXTURE_PID" -n -- curl -sS --max-time 5 \
  -D /tmp/apache-reader.headers -o /tmp/apache-reader.json \
  -X POST -H 'Origin: http://127.0.0.1:18080' \
  --data-urlencode 'identity=reader' \
  --data-urlencode 'proof=fixture-reader-proof' \
  http://127.0.0.1:18080/app/login
READER_SESSION=$(sed -n 's/^Set-Cookie: fixture_session=\([^;]*\).*/fixture_session=\1/p' /tmp/apache-reader.headers | tr -d '\r')
READER_CSRF=$(sed -n 's/.*"csrf": "\([^"]*\)".*/\1/p' /tmp/apache-reader.json)
nsenter -t "$FIXTURE_PID" -n -- curl -sS --max-time 5 -X POST \
  -H 'Origin: http://127.0.0.1:18080' --cookie "$READER_SESSION" \
  --data-urlencode "csrf=$READER_CSRF" --data-urlencode 'value=reader-marker' \
  http://127.0.0.1:18080/app/admin-setting
```

Expected: the first command prints `401`; the reader login succeeds; the final
response returns `"value": "reader-marker"` even though the session role is
not admin.

**CWE-287 — truncated proof comparison.**

```sh
nsenter -t "$FIXTURE_PID" -n -- curl -sS --max-time 5 -o /dev/null -w '%{http_code}\n' \
  -X POST -H 'Origin: http://127.0.0.1:18080' \
  --data-urlencode 'identity=admin' --data-urlencode 'proof=wrong' \
  http://127.0.0.1:18080/app/login
nsenter -t "$FIXTURE_PID" -n -- curl -sS --max-time 5 \
  -D /tmp/apache-forged.headers -o /tmp/apache-forged.json -w '%{http_code}\n' \
  -X POST -H 'Origin: http://127.0.0.1:18080' \
  --data-urlencode 'identity=admin' --data-urlencode 'proof=fixture-INVALID' \
  http://127.0.0.1:18080/app/login
FORGED_SESSION=$(sed -n 's/^Set-Cookie: fixture_session=\([^;]*\).*/fixture_session=\1/p' /tmp/apache-forged.headers | tr -d '\r')
nsenter -t "$FIXTURE_PID" -n -- curl -sS --max-time 5 --get \
  --cookie "$FORGED_SESSION" http://127.0.0.1:18080/app/identity
```

Expected: the baseline prints `401`; the second login prints `200` and the final
response is `{"accepted_identity": "admin"}`. The supplied proof only
shares the first eight characters with the synthetic admin proof.

Stop the fixture before booting another variant:

```sh
kill "$FIXTURE_PID"
wait "$FIXTURE_PID" 2>/dev/null || true
```

The volatile staging directory and all sessions, databases and marker files are
removed when the fixture exits; a QEMU snapshot discards the outer guest files.

### Scenario and scope

**⚙️ Implementation.** Every `<device>-cweNNN-apache-web` image selects exactly
one `scenario.py` from `apache-web-fixture`; image guards reject a second
fixture package. `manual-launch.sh` reuses the package's namespace launcher,
starts Apache as UID 1000 with private loopback only, and provides fixed
synthetic SQLite/filesystem state. The `curl` commands above are the only HTTP
inputs: no host service, external address, production credential, persistence
or post-exploitation path is involved.

**✅ Runtime evidence.** All ten rebuilt `router` `qemuarm64` variants were
manually exercised through their guest serial consoles with the commands above.
The observed witnesses were, respectively: SQL sentinel (89), literal script
reflection (79), level `101` (20), `csrf-marker` from port 18081 (352),
`shell-marker` (78), traversal sentinel (22),
`application-command-marker` (77), unauthenticated marker (306), reader
marker after a 401 unauthenticated baseline (862), and an accepted `admin`
identity after the truncated-proof login (287). Each run used QEMU without a
NIC and a new disposable fixture state.

> ⚠️ **Disclaimer:** Intentionally insecure, isolated benchmark fixtures only.
> Apache listens solely on the fixture's private loopback interface; QEMU has no
> NIC for these images. Do not deploy this configuration or reuse its synthetic
> inputs outside this benchmark.

Source: [apache-web-fixture](../meta-iotbench/recipes-vulns/apache-web-fixture/).

<a id="vulnerable-c-binaries--path-traversal-and-filename-validation-cwe-22cwe-20"></a>
<a id="test-9"></a>

## Test 9: Vulnerable C binaries — path traversal and filename validation — CWE-22/CWE-20

### Build, boot and manual testing

**What this tests.** These images run the actual AArch64 C binary in a fresh,
unprivileged mount namespace. Each request copies the installed fixture into
that namespace, so the observed marker can only come from its synthetic
filesystem. The commands below are manual terminal commands; they do not use a
client script or Python.

**CWE-22 build and boot — host:**

```bash
TEST_DEVICE=router
TEST_SCENARIO=cwe022-native-path-traversal
TEST_FIRMWARE="${TEST_DEVICE}-${TEST_SCENARIO}"

FIRMWARE="$TEST_FIRMWARE" docker compose run --rm yocto
FIRMWARE="$TEST_FIRMWARE" ./scripts/run-qemu.sh
```

Log in on the serial console as `root` (password `routeradmin`). The named
scenario enables its fixture configuration automatically.

**CWE-22 baseline — guest:**

```sh
su -s /bin/sh iotpath -c '
root=$(mktemp -d /tmp/iotbench-path.XXXXXX) || exit 1
/usr/share/iotbench/native-path/bin/isolate-path --manual-request /usr/share/iotbench/native-path "$root" public.cfg
status=$?
rmdir "$root"
exit "$status"
'
echo "baseline_exit=$?"
```

Expected: `OK 32`, followed by `SYNTHETIC_ALLOWED_CONFIGURATION`, and
`baseline_exit=0`.

**CWE-22 traversal, containment control, and repeat — guest:**

```sh
cat /usr/share/iotbench/native-path/fs/sentinel.txt
su -s /bin/sh iotpath -c '
root=$(mktemp -d /tmp/iotbench-path.XXXXXX) || exit 1
/usr/share/iotbench/native-path/bin/isolate-path --manual-request /usr/share/iotbench/native-path "$root" ../sentinel.txt
status=$?
rmdir "$root"
exit "$status"
'
echo "traversal_exit=$?"

su -s /bin/sh iotpath -c '
root=$(mktemp -d /tmp/iotbench-path.XXXXXX) || exit 1
/usr/share/iotbench/native-path/bin/isolate-path --manual-request /usr/share/iotbench/native-path "$root" ../../etc/passwd
status=$?
rmdir "$root"
exit "$status"
'
echo "containment_exit=$?"

su -s /bin/sh iotpath -c '
root=$(mktemp -d /tmp/iotbench-path.XXXXXX) || exit 1
/usr/share/iotbench/native-path/bin/isolate-path --manual-request /usr/share/iotbench/native-path "$root" ../sentinel.txt
status=$?
rmdir "$root"
exit "$status"
'
echo "repeat_exit=$?"
```

Expected: the first command prints `SYNTHETIC_CWE22_SENTINEL_ONLY`. Both
`../sentinel.txt` requests return `OK 30` and that same marker with exit `0`:
the C code prefixes the input with `allowed/`, so `..` escapes only the
synthetic `allowed` directory. The `../../etc/passwd` control returns
`ERR DENIED` (and `containment_exit=0`, because the fixture handled the denied
request); it cannot leave the outer synthetic `/fixture/fs` root.

Shut down the guest (`poweroff`) before booting the second image.

**CWE-20 build and boot — host:**

```bash
TEST_DEVICE=router
TEST_SCENARIO=cwe020-native-filename-validation
TEST_FIRMWARE="${TEST_DEVICE}-${TEST_SCENARIO}"

FIRMWARE="$TEST_FIRMWARE" docker compose run --rm yocto
FIRMWARE="$TEST_FIRMWARE" ./scripts/run-qemu.sh
```

Log in again as `root` with password `routeradmin`.

**CWE-20 baseline, rejected control, bypass, and repeat — guest:**

```sh
cat /usr/share/iotbench/native-path/fs/allowed/private.cfg.bak

su -s /bin/sh iotpath -c '
root=$(mktemp -d /tmp/iotbench-path.XXXXXX) || exit 1
/usr/share/iotbench/native-path/bin/isolate-path --manual-request /usr/share/iotbench/native-path "$root" public.cfg
status=$?
rmdir "$root"
exit "$status"
'
echo "baseline_exit=$?"

su -s /bin/sh iotpath -c '
root=$(mktemp -d /tmp/iotbench-path.XXXXXX) || exit 1
/usr/share/iotbench/native-path/bin/isolate-path --manual-request /usr/share/iotbench/native-path "$root" private.bak
status=$?
rmdir "$root"
exit "$status"
'
echo "rejected_control_exit=$?"

su -s /bin/sh iotpath -c '
root=$(mktemp -d /tmp/iotbench-path.XXXXXX) || exit 1
/usr/share/iotbench/native-path/bin/isolate-path --manual-request /usr/share/iotbench/native-path "$root" private.cfg.bak
status=$?
rmdir "$root"
exit "$status"
'
echo "filename_bypass_exit=$?"

su -s /bin/sh iotpath -c '
root=$(mktemp -d /tmp/iotbench-path.XXXXXX) || exit 1
/usr/share/iotbench/native-path/bin/isolate-path --manual-request /usr/share/iotbench/native-path "$root" private.cfg.bak
status=$?
rmdir "$root"
exit "$status"
'
echo "repeat_exit=$?"
```

Expected: the initial `cat` prints `SYNTHETIC_CWE20_DISALLOWED_BACKUP`.
`public.cfg` returns `OK 32` and `SYNTHETIC_ALLOWED_CONFIGURATION`;
`private.bak` returns `ERR DENIED` with `rejected_control_exit=0`. Both
`private.cfg.bak` requests return `OK 34` and
`SYNTHETIC_CWE20_DISALLOWED_BACKUP` with exit `0`. The C
filename check accepts the `.cfg` prefix but does not require it to be the
end of the name, so it reads the otherwise disallowed synthetic backup.

### Scenario and scope

**⚙️ Implementation.** The same two thin image recipes exist for every listed
device category. The manual entry invokes the installed `isolate-path` and the
same `retrieve()` sink used by the package; it makes no listener, host mount,
or network request. The normal fixture ELF is static PIE so it remains
executable after the launcher pivots into its temporary root.

**✅ Runtime evidence.** On `router`/`qemuarm64`, both final exports were built
with the normal Compose workflow and manually exercised through QEMU's serial
console. CWE-22 produced the allowed baseline, the synthetic sentinel through
`../sentinel.txt`, an `ERR DENIED` outer-boundary control, and the same sentinel
on repetition. CWE-20 produced its allowed baseline, rejected `private.bak`,
read the synthetic backup through `private.cfg.bak`, and repeated that result.
The runtime evidence is limited to this built router/QEMU variant; the shared
recipes provide the corresponding fixture for the other device categories.

> ⚠️ **Disclaimer:** Intentionally insecure, isolated benchmark fixtures only.
> The requested files are synthetic and copied into a disposable namespace; do
> not deploy these inputs or configurations outside this benchmark.

Source: [native-path-fixture](../meta-iotbench/recipes-vulns/native-path-fixture/).

<a id="native-c-buffer-overflow-cwe-787-cwe-20-cwe-119"></a>
<a id="test-10"></a>

## Test 10: Vulnerable C binaries — buffer overflow — CWE-787/CWE-20/CWE-119

### Build, boot and manual testing

**What this tests.** The actual native AArch64 fixture accepts an exact binary
stdin frame: a two-byte big-endian length followed by printable bytes. It
validates the transport length only (maximum 256), then copies that many bytes
into a 64-byte global configuration array. This manual procedure uses the
ASan companion from the built firmware so the first out-of-bounds write is
observable without relying on undefined behavior from the normal ELF.

**Build — host:**

Run this from the repository root. `IOTBENCH_NATIVE_BUFFER_ASAN=1` installs
the diagnostic companion used below; the selected image enables its own fixture
mode and opt-in only.

```bash
TEST_DEVICE=router
TEST_SCENARIO=cwe787-native-buffer-overflow
TEST_FIRMWARE="${TEST_DEVICE}-${TEST_SCENARIO}"

docker compose run --rm \
  -e FIRMWARE="$TEST_FIRMWARE" \
  -e IOTBENCH_BUILD_MODE=fixture \
  -e IOTBENCH_ENABLE_NATIVE_BUFFER_FIXTURE=1 \
  -e IOTBENCH_NATIVE_BUFFER_ASAN=1 yocto
```

**Boot — host:**

```bash
FIRMWARE="$TEST_FIRMWARE" ./scripts/run-qemu.sh
```

This serial-only fixture starts QEMU without a network device. Log in with
`root` / `routeradmin`; run the remaining commands in that guest console.

**64-byte baseline — guest:**

```sh
{ printf '\000\100'; printf '%064d' 0; } | \
  setpriv --reuid=65534 --regid=65534 --clear-groups --no-new-privs \
  env ASAN_OPTIONS='detect_leaks=0:halt_on_error=1:abort_on_error=0:symbolize=1:exitcode=86' \
  /usr/bin/fixture-buffer-write-asan
echo "baseline_exit=$?"
```

Expected: the fixture warning, then `OK 64 3072` and `baseline_exit=0`.
`\000\100` is the big-endian length `64`; `printf '%064d' 0` supplies exactly
64 printable `0` bytes. This is the safe boundary of the actual destination.

**65-byte witness — guest:**

```sh
{ printf '\000\101'; printf '%065d' 0; } | \
  setpriv --reuid=65534 --regid=65534 --clear-groups --no-new-privs \
  env ASAN_OPTIONS='detect_leaks=0:halt_on_error=1:abort_on_error=0:symbolize=1:exitcode=86' \
  /usr/bin/fixture-buffer-write-asan 2>/tmp/iotbench-cwe787-asan.log
echo "witness_exit=$?"
grep -E 'global-buffer-overflow|WRITE of size 1|fixture-buffer-write.c:51' \
  /tmp/iotbench-cwe787-asan.log
```

Expected: no normal `OK` line, `witness_exit=86`, and all three ASan witnesses:
`global-buffer-overflow`, `WRITE of size 1`, and
`fixture-buffer-write.c:51`. `\000\101` declares 65 printable `0` bytes: the
parser accepts the frame, while the 65th indexed store is the first write past
the 64-byte global array. Repeat this same 65-byte block once; it must again
exit `86` and report the same ASan class, write size, and source line.

### Scenario and scope

**⚙️ Implementation.** Every supported device category has a thin
`<device>-cwe787-native-buffer-overflow` image recipe. It retains device
metadata but installs only `cwe787-native-buffer-overflow`, with no device
daemon or network listener. The installed normal and ASan binaries are both
compiled from `fixture-buffer-write.c`; the latter only makes the same
`configuration[index] = payload[index]` store observable. The one missing
check is `length <= sizeof(configuration)`: CWE-787 is the primary label,
CWE-20 is the contributing validation failure, and CWE-119 is the broader
category.

**✅ Runtime evidence.** The `router`/`qemuarm64` ASan-enabled image was built
with the normal Compose workflow and its exported root filesystem contained
both `/usr/bin/fixture-buffer-write` and
`/usr/bin/fixture-buffer-write-asan`, root-owned and mode `0755`. In QEMU, the
64-byte frame returned `OK 64 3072` with exit `0`; the 65-byte frame returned
exit `86` and ASan reported a global-buffer-overflow, one-byte write, and
`fixture-buffer-write.c:51` on two consecutive manual runs. This evidence is
limited to that built router/QEMU variant; the same shared package and image
pattern provide the fixture for the other device categories.

> ⚠️ **Disclaimer:** Intentionally insecure, isolated benchmark fixture only.
> The input is a local synthetic configuration frame; it starts no service,
> enables no networking, and is not an exploitation procedure. Do not deploy
> this configuration or reuse it outside the benchmark.

Source: [cwe787-native-buffer-overflow](../meta-iotbench/recipes-vulns/cwe787-native-buffer-overflow/).

<a id="native-connection-string-injection-cwe-20"></a>
<a id="test-11"></a>

## Test 11: Vulnerable C binaries — Connection String Injection — CWE-20

### Build, boot and manual testing

**What this tests.** The actual native C binary builds a SQLite `file:` URI
from a caller-controlled `cache` field and an intended fixed `mode=ro` suffix.
The input is a two-byte big-endian length followed by printable ASCII. The
fixture creates a new private synthetic database for every invocation; no
network service, existing database or external endpoint is involved.

**Build — host:**

Run from the repository root. The named scenario selects the fixture-only build
mode and its connection-fixture opt-in automatically.

```bash
TEST_DEVICE=router
TEST_SCENARIO=cwe020-native-connection-string
TEST_FIRMWARE="${TEST_DEVICE}-${TEST_SCENARIO}"

FIRMWARE="$TEST_FIRMWARE" docker compose run --rm yocto
```

**Boot — host:**

```bash
FIRMWARE="$TEST_FIRMWARE" ./scripts/run-qemu.sh
```

This is a serial-only fixture: QEMU starts with no NIC. Log in with `root` /
`routeradmin`, then run the remaining commands in the guest console.

**Baseline — guest:**

```sh
printf '\000\007private' | \
  setpriv --reuid=65534 --regid=65534 --clear-groups --no-new-privs \
  /usr/bin/fixture-connection
echo "baseline_exit=$?"
```

Expected: the fixture notice, then
`OK readonly=1 marker=SYNTHETIC_CONNECTION_RESOURCE` and
`baseline_exit=0`. The normal `private` cache value leaves the intended
read-only SQLite connection in effect.

**Connection-string injection — guest:**

```sh
printf '\000\020private&mode=rw#' | \
  setpriv --reuid=65534 --regid=65534 --clear-groups --no-new-privs \
  /usr/bin/fixture-connection
echo "injected_exit=$?"
```

Expected: the same synthetic marker but
`OK readonly=0 marker=SYNTHETIC_CONNECTION_RESOURCE` and
`injected_exit=0`. `\000\020` declares the 16-byte value
`private&mode=rw#`; its `#` starts a URI fragment, so SQLite applies the
attacker-controlled `mode=rw` and ignores the intended trailing `&mode=ro`.

**Repeat control — guest:**

```sh
printf '\000\007private' | \
  setpriv --reuid=65534 --regid=65534 --clear-groups --no-new-privs \
  /usr/bin/fixture-connection
echo "repeat_baseline_exit=$?"
```

Expected: again `OK readonly=1 marker=SYNTHETIC_CONNECTION_RESOURCE` and
`repeat_baseline_exit=0`. Each process creates and removes its own private
database, so the result returns to the normal read-only state. Repeating the
injected command above consistently returns `readonly=0`.

### Scenario and scope

**⚙️ Implementation.** Every supported device category has a thin
`<device>-cwe020-native-connection-string` image recipe that installs only
`cwe020-native-connection-string` plus its device metadata. The executable's
data flow is `stdin` -> `read_cache()` -> `snprintf()` URI construction ->
`sqlite3_open_v2()` -> `sqlite3_db_readonly()`. The sole intentional defect is
missing exact validation/URI encoding of the `cache` field; the database path,
SQL query and Unix VFS are fixed. The helper rejects root execution, runs with
matching unprivileged IDs, enables `no_new_privs` and seccomp denial of socket,
connect and exec syscalls.

**✅ Runtime evidence.** On 2026-11-04, the `router`/`qemuarm64` image built and
exported successfully with the normal Compose workflow. Its compressed ext4
passed `zstd -t`; offline inspection found root-owned mode `0755`
`/usr/bin/fixture-connection` and its installed source/ground truth. In the
disposable serial-only QEMU guest, the manual baseline returned `readonly=1`,
the concrete injected field returned `readonly=0`, the baseline reset to
`readonly=1`, and a repeated injected field returned `readonly=0`; all four
commands exited 0. Runtime evidence is limited to this built router/QEMU
variant. The eleven recipe inclusions were inspected and share the same package
and fixture configuration.

> ⚠️ **Disclaimer:** Intentionally insecure, isolated benchmark fixture only.
> The input changes capability only for a newly created private SQLite database;
> it starts no service, reaches no network and provides no persistence or
> post-exploitation path. Do not deploy this configuration or reuse the input
> outside this benchmark.

Source: [cwe020-native-connection-string](../meta-iotbench/recipes-vulns/cwe020-native-connection-string/).

<a id="native-c-symbolic-link-following-cwe-61-and-cwe-59"></a>
<a id="test-12"></a>

## Test 12: Vulnerable C binaries — symbolic-link following — CWE-61/CWE-59

### Build, boot and manual testing

**What this tests.** The actual target C handler reads the fixed
`public.cfg` entry from a pinned `allowed/` directory. The existing
`isolate-path` manual entry copies only the two fixed synthetic resources into
a fresh unprivileged tmpfs namespace. Its concrete `ordinary` and `symlink`
arguments select either the ordinary file or the pre-established
`public.cfg -> ../sentinel.txt` entry before the C handler opens it. The
one-shot terminal entry then calls the same `retrieve()` sink as the Unix
socket service; it uses no Python client, network listener, or caller-selected
filename.

**Build — host:**

Run from the repository root. Selecting this scenario enables its own
fixture-only build configuration automatically.

```bash
TEST_DEVICE=router
TEST_SCENARIO=cwe061-native-symlink-following
TEST_FIRMWARE="${TEST_DEVICE}-${TEST_SCENARIO}"

FIRMWARE="$TEST_FIRMWARE" docker compose run --rm yocto
```

**Boot — host:**

```bash
FIRMWARE="$TEST_FIRMWARE" ./scripts/run-qemu.sh
```

This is a serial-only fixture: QEMU starts with no NIC. Log in with `root` /
`routeradmin`, then run the remaining commands in the guest console.

**Ordinary-file baseline — guest:**

```sh
su -s /bin/sh iotsymlink -c '
root=$(mktemp -d /tmp/iotbench-symlink.XXXXXX) || exit 1
/usr/share/iotbench/native-symlink/bin/isolate-path --manual-request \
  /usr/share/iotbench/native-symlink "$root" ordinary
status=$?
rmdir "$root"
exit "$status"
'
echo "baseline_exit=$?"
```

Expected: `ENTRY ordinary public.cfg`, followed by `OK 39` and
`SYNTHETIC_CWE61_ORDINARY_CONFIGURATION`, then `baseline_exit=0`. The ordinary
entry is the allowed boundary condition.

**Pre-established symbolic-link witness and repeat — guest:**

```sh
for label in witness repeat; do
  su -s /bin/sh iotsymlink -c '
root=$(mktemp -d /tmp/iotbench-symlink.XXXXXX) || exit 1
/usr/share/iotbench/native-symlink/bin/isolate-path --manual-request \
  /usr/share/iotbench/native-symlink "$root" symlink
status=$?
rmdir "$root"
exit "$status"
'
  printf '%s_exit=%s\n' "$label" "$?"
done
```

Expected on both iterations: `ENTRY symlink public.cfg -> ../sentinel.txt`,
then `OK 30` and `SYNTHETIC_CWE61_SENTINEL_ONLY`, with exit `0`. The launcher
creates the link before the target C process starts, while the process pins
the parent directory. The vulnerable `openat()` lacks `O_NOFOLLOW`, so it
follows only that fixed final-component link and reads the synthetic sentinel.
Each invocation receives a new private tmpfs, so the repeated result confirms
that no guest or host state is retained.

### Scenario and scope

**⚙️ Implementation.** Every supported device category has a thin
`<device>-cwe061-native-symlink-following` image recipe that installs only
`cwe061-native-symlink-following` plus device metadata. Its static-PIE target
ELF remains executable after the existing launcher pivots into the minimal
tmpfs. The only intentional defect is omission of `O_NOFOLLOW` on the fixed
`public.cfg` final component; the corrected twin uses the same manual input
but refuses the link with `ERR DENIED`. The test never accepts a path from the
researcher and cannot reach files outside its disposable synthetic namespace.

**✅ Runtime evidence.** On 2026-11-04, the normal Compose build and export of
the `router`/`qemuarm64` vulnerable image succeeded. Its compressed ext4
passed `zstd -t`; offline inspection found the root-owned mode-`0755` target
ELF and fixture resources. In the disposable QEMU serial guest, the documented
`ordinary` request returned `OK 39` and the ordinary marker; two independent
`symlink` requests each returned `OK 30` and the sentinel with exit `0`. The
same router fixed twin built and booted successfully: its ordinary request
remained accepted, while its pre-established `symlink` request returned
`ERR DENIED`. No Python runner or network interface was used. Runtime evidence
is limited to these built router/QEMU images; the eleven thin recipes reuse the
same package and explicit fixture configuration.

> ⚠️ **Disclaimer:** Intentionally insecure, isolated benchmark fixture only.
> The link and both resources exist solely inside a fresh private tmpfs; no
> network service, persistence, external file, or exploitation chain is
> involved. Do not deploy this configuration or reuse its input outside this
> benchmark.

Source: [cwe061-native-symlink-following](../meta-iotbench/recipes-vulns/cwe061-native-symlink-following/).

<a id="test-13"></a>

## Test 13: Vulnerable Java JARs — command injection — CWE-78/CWE-77/CWE-20

### Build, boot and manual testing

**What this tests.** This fixture provides two deliberately narrow Java JARs.
Both require the `--fixture-test` argument, the
`IOTBENCH_ENABLE_JAVA_COMMAND_FIXTURE=1` opt-in, and a writable `/work`
directory owned by the unprivileged `javacommand` user. Their shared
intentional CWE-20 defect accepts any printable-ASCII `label` rather than the
intended `[A-Za-z0-9_-]` form. The CWE-78 variant concatenates that label into
a fixed `/bin/sh -c` command; the concrete witness below closes its quoted
argument and writes the fixed synthetic `os-marker.txt` marker. The CWE-77
variant sends the label to a tiny application command interpreter whose `;`
separator permits the fixed `mark` command and its synthetic
`app-marker.txt` file. Neither JAR starts a service or needs a network path.

**Build and boot the OS-command variant — host:**

Run from the repository root. Selecting this scenario enables only its own
fixture configuration automatically.

```bash
TEST_DEVICE=router
TEST_SCENARIO=cwe078-java-os-command-injection
TEST_FIRMWARE="${TEST_DEVICE}-${TEST_SCENARIO}"

FIRMWARE="$TEST_FIRMWARE" docker compose run --rm yocto
FIRMWARE="$TEST_FIRMWARE" ./scripts/run-qemu.sh
```

QEMU is serial-only and starts with no NIC. Log in with `root` / `routeradmin`.
In a fresh default QEMU snapshot, create the fixture's isolated working
directory; the JAR itself will run as `javacommand`.

```sh
mkdir /work
chown javacommand:javacommand /work
chmod 0700 /work
```

**CWE-78 baseline — guest:**

```sh
su -s /bin/sh javacommand -c 'cd /work && rm -f normal.txt os-marker.txt && printf "label=sensor_01\n" | env IOTBENCH_ENABLE_JAVA_COMMAND_FIXTURE=1 java -Xmx32m -XX:-UsePerfData -jar /usr/share/iotbench/java-command-fixture/fixture-os-command.jar --fixture-test && printf "normal=" && cat normal.txt && test ! -e os-marker.txt && printf "marker=absent\n"'
printf 'baseline_exit=%s\n' "$?"
```

Expected: `normal=sensor_01`, then `marker=absent` and `baseline_exit=0`.
The input is within the intended label boundary and creates no marker.

**CWE-78 witness — guest:**

```sh
su -s /bin/sh javacommand <<'EOF'
set -eu
cd /work
rm -f normal.txt os-marker.txt
printf "%s\n" "label=sensor' > normal.txt; printf 'JAVA_OS_MARKER\\n' > os-marker.txt; #" |
  env IOTBENCH_ENABLE_JAVA_COMMAND_FIXTURE=1 \
  java -Xmx32m -XX:-UsePerfData -jar \
  /usr/share/iotbench/java-command-fixture/fixture-os-command.jar --fixture-test
printf 'normal='
cat normal.txt
printf 'marker='
cat os-marker.txt
EOF
printf 'witness_exit=%s\n' "$?"
```

Expected: `normal=sensor`, `marker=JAVA_OS_MARKER`, and `witness_exit=0`.
The marker is produced by the JAR's intentionally concatenated shell command,
in `/work` only. For the reproducibility control, paste the same witness block
once more (it removes both files first): it must again print the same two
values and exit `0`.

**Build and boot the application-command variant — host:**

Quit the first guest with `Ctrl-A`, then `x`; the default QEMU disk is a
snapshot. Build and boot a fresh guest for the second JAR.

```bash
TEST_DEVICE=router
TEST_SCENARIO=cwe077-java-app-command-injection
TEST_FIRMWARE="${TEST_DEVICE}-${TEST_SCENARIO}"

FIRMWARE="$TEST_FIRMWARE" docker compose run --rm yocto
FIRMWARE="$TEST_FIRMWARE" ./scripts/run-qemu.sh
```

Log in with `root` / `routeradmin` and prepare its fresh `/work` directory:

```sh
mkdir /work
chown javacommand:javacommand /work
chmod 0700 /work
```

**CWE-77 baseline — guest:**

```sh
su -s /bin/sh javacommand -c 'cd /work && rm -f normal.txt app-marker.txt && printf "label=sensor_01\n" | env IOTBENCH_ENABLE_JAVA_COMMAND_FIXTURE=1 java -Xmx32m -XX:-UsePerfData -jar /usr/share/iotbench/java-command-fixture/fixture-app-command.jar --fixture-test && printf "normal=" && cat normal.txt && test ! -e app-marker.txt && printf "marker=absent\n"'
printf 'baseline_exit=%s\n' "$?"
```

Expected: `normal=sensor_01`, `marker=absent`, and `baseline_exit=0`.

**CWE-77 witness — guest:**

```sh
su -s /bin/sh javacommand <<'EOF'
set -eu
cd /work
rm -f normal.txt app-marker.txt
printf 'label=sensor;mark\n' |
  env IOTBENCH_ENABLE_JAVA_COMMAND_FIXTURE=1 \
  java -Xmx32m -XX:-UsePerfData -jar \
  /usr/share/iotbench/java-command-fixture/fixture-app-command.jar --fixture-test
printf 'normal='
cat normal.txt
printf 'marker='
cat app-marker.txt
EOF
printf 'witness_exit=%s\n' "$?"
```

Expected: `normal=sensor`, `marker=JAVA_APP_MARKER`, and `witness_exit=0`.
Here `mark` is an extra application-language statement, not an operating-system
command. Paste the same witness block once more for the reproducibility
control; it must produce the same output and exit `0` after its local cleanup.

### Scenario and scope

**⚙️ Implementation.** Each supported device category — `doorlock`,
`envsensor`, `healthmonitor`, `ipcamera`, `plc`, `router`, `smartbulb`,
`smarthub`, `smartplug`, `smartspeaker`, and `thermostat` — has one thin
`<device>-cwe078-java-os-command-injection` image and one thin
`<device>-cwe077-java-app-command-injection` image. Each installs only the
corresponding JAR fixture and device metadata. `FixtureRequest` enforces the
explicit argument, environment, working-directory, length, and ASCII gates;
its intentionally weak label grammar is the common input-validation defect.
Only `FixtureOsCommand` invokes `/bin/sh`; `FixtureAppCommand` implements the
separate application-command condition. The documented manual inputs write
only fixed markers in the unprivileged `/work` directory; no other target is
needed to observe either condition.

**✅ Runtime evidence.** On 2026-11-04, the normal Compose workflow built and
exported both `router`/`qemuarm64` images. Each compressed ext4 passed
`zstd -t`; offline ext4 inspection found the corresponding root-owned,
mode-`0644` JAR plus its source and ground-truth resources. In fresh
serial-only QEMU guests, each documented baseline returned
`normal=sensor_01` with no marker. Two independent CWE-78 witness executions
returned `normal=sensor` and `JAVA_OS_MARKER`; two independent CWE-77 witness
executions returned `normal=sensor` and `JAVA_APP_MARKER`; all runs exited
`0`. No Python runner, automatic test harness, network interface, or external
system was used. Runtime evidence is limited to the built router/QEMU images;
the eleven image recipes per variant reuse the inspected fixture package and
configuration.

> ⚠️ **Disclaimer:** Intentionally insecure, isolated benchmark fixture only.
> The concrete inputs write fixed synthetic markers in the disposable guest's
> `/work` directory; they start no service, access no network, provide no
> persistence, and are not for use outside this benchmark.

Source: [java-command-fixture](../meta-iotbench/recipes-vulns/java-command-fixture/).

<a id="test-14"></a>

## Test 14: Vulnerable Java JARs — deserialization — CWE-502/CWE-20

### Build, boot and manual testing

**What this tests.** The local JAR reads one Java serialization stream from
standard input. `FixtureData` is the only intended request type, but the
vulnerable image applies resource limits without a type allowlist before
`ObjectInputStream.readObject()`. The concrete `FixtureMarker` stream below
therefore runs its harmless `readObject()` callback, which increments only an
in-memory counter, before the later `instanceof FixtureData` check returns
`UNEXPECTED_TYPE`. The explicit `--show-events` option exposes that counter for
this benchmark observation; it neither writes a file nor starts a service.

**Build and boot — host:**

Run from the repository root. The selected scenario enables only its own
fixture build configuration.

```bash
TEST_DEVICE=router
TEST_SCENARIO=cwe502-java-deserialization
TEST_FIRMWARE="${TEST_DEVICE}-${TEST_SCENARIO}"

FIRMWARE="$TEST_FIRMWARE" docker compose run --rm yocto
FIRMWARE="$TEST_FIRMWARE" ./scripts/run-qemu.sh
```

This is a serial-only fixture: QEMU starts with no NIC or forwarded port. Log
in with `root` / `routeradmin`, then run the remaining commands in the guest
console. The two variables below are complete fixed Java serialization streams;
`printf '%b'` interprets their concrete octal bytes and needs no Python,
generator or test harness.

```sh
FIXTURE=/usr/share/iotbench/java-deserialization-fixture
NORMAL_STREAM='\254\355\000\005\163\162\000\060\157\162\147\056\151\157\164\142\145\156\143\150\056\146\151\170\164\165\162\145\056\144\145\163\145\162\151\141\154\151\172\141\164\151\157\156\056\106\151\170\164\165\162\145\104\141\164\141\000\000\000\000\000\000\000\001\002\000\002\111\000\007\162\145\141\144\151\156\147\114\000\006\163\145\156\163\157\162\164\000\022\114\152\141\166\141\057\154\141\156\147\057\123\164\162\151\156\147\073\170\160\000\000\000\027\164\000\011\163\145\156\163\157\162\137\060\061'
MARKER_STREAM='\254\355\000\005\163\162\000\062\157\162\147\056\151\157\164\142\145\156\143\150\056\146\151\170\164\165\162\145\056\144\145\163\145\162\151\141\154\151\172\141\164\151\157\156\056\106\151\170\164\165\162\145\115\141\162\153\145\162\000\000\000\000\000\000\000\001\002\000\000\170\160'
```

**Baseline — guest:**

```sh
printf '%b' "$NORMAL_STREAM" | \
  setpriv --reuid=992 --regid=992 --clear-groups \
  env IOTBENCH_ENABLE_JAVA_DESERIALIZATION_FIXTURE=1 \
  java -Xmx32m -XX:-UsePerfData -jar "$FIXTURE/fixture-deserialization.jar" \
  --fixture-test --show-events
printf 'baseline_exit=%s\n' "$?"
```

Expected: `OK sensor=sensor_01 reading=23`, `CALLBACK_EVENTS=0`, then
`baseline_exit=0`. This valid `FixtureData` request reaches the same
deserialization path but no marker callback.

**Callback witness — guest:**

```sh
printf '%b' "$MARKER_STREAM" | \
  setpriv --reuid=992 --regid=992 --clear-groups \
  env IOTBENCH_ENABLE_JAVA_DESERIALIZATION_FIXTURE=1 \
  java -Xmx32m -XX:-UsePerfData -jar "$FIXTURE/fixture-deserialization.jar" \
  --fixture-test --show-events
printf 'witness_exit=%s\n' "$?"
```

Expected: `UNEXPECTED_TYPE`, `CALLBACK_EVENTS=1`, then `witness_exit=2`.
The nonzero application status is the intentional late rejection, not a failed
test: the event count proves that the input class was reconstructed and its
callback ran first. Paste this same block once more; it must again print
`UNEXPECTED_TYPE`, `CALLBACK_EVENTS=1`, and `witness_exit=2`.

**Corrected allowlist control (optional, host and guest):** quit QEMU with
**Ctrl-A**, then **X**, build and boot the existing twin, log in again, and
reuse the same `MARKER_STREAM` definition from above.

```bash
FIRMWARE=router-cwe502-java-deserialization-fixed docker compose run --rm yocto
FIRMWARE=router-cwe502-java-deserialization-fixed ./scripts/run-qemu.sh
```

```sh
FIXTURE=/usr/share/iotbench/java-deserialization-fixture
MARKER_STREAM='\254\355\000\005\163\162\000\062\157\162\147\056\151\157\164\142\145\156\143\150\056\146\151\170\164\165\162\145\056\144\145\163\145\162\151\141\154\151\172\141\164\151\157\156\056\106\151\170\164\165\162\145\115\141\162\153\145\162\000\000\000\000\000\000\000\001\002\000\000\170\160'
printf '%b' "$MARKER_STREAM" | \
  setpriv --reuid=992 --regid=992 --clear-groups \
  env IOTBENCH_ENABLE_JAVA_DESERIALIZATION_FIXTURE=1 \
  java -Xmx32m -XX:-UsePerfData -jar "$FIXTURE/fixture-deserialization.jar" \
  --fixture-test --show-events
printf 'fixed_marker_exit=%s\n' "$?"
```

Expected: `FILTER_REJECTED`, `CALLBACK_EVENTS=0`, and
`fixed_marker_exit=2`. The corrected twin's allowlist rejects
`FixtureMarker` before its callback while keeping the normal `FixtureData`
baseline valid.

### Scenario and scope

**⚙️ Implementation.** Every supported device category — `doorlock`,
`envsensor`, `healthmonitor`, `ipcamera`, `plc`, `router`, `smartbulb`,
`smarthub`, `smartplug`, `smartspeaker`, and `thermostat` — has one thin
`<device>-cwe502-java-deserialization` image and an existing corrected twin.
The shared image include installs only the Java fixture and core boot packages,
copies device metadata, disables device daemons, and requires explicit fixture
mode. The source-to-observation flow is fixed: stdin → bounded byte array →
`ObjectInputStream.readObject()` → `FixtureMarker.readObject()` → late
`instanceof` rejection → `CALLBACK_EVENTS`. Resource bounds remain in place
(4096 bytes, depth 8, 32 references and array length 16); CWE-502 is the
missing type restriction at the reconstruction boundary, with CWE-20 as the
contributing input-validation error. The fixture establishes an unintended
synthetic callback only, not arbitrary code execution.

**✅ Runtime evidence.** On 2026-11-05, the normal Compose workflow built and
exported all eleven vulnerable `qemuarm64` images, plus both `router` variants.
Every vulnerable compressed ext4 artifact passed `zstd -t`; offline ext4
inspection found the matching shared `FixtureDeserialize.java` source and the
application JAR in each one. The two router artifacts additionally contained the
root-owned mode-`0644` application and test JARs, sources and ground-truth
resources. In fresh serial-only QEMU guests, the vulnerable JAR accepted the normal stream with
`CALLBACK_EVENTS=0`; two independent marker-stream executions returned
`UNEXPECTED_TYPE`, `CALLBACK_EVENTS=1`, and exit `2`. The corrected router twin
accepted the normal stream but returned `FILTER_REJECTED`,
`CALLBACK_EVENTS=0`, and exit `2` for the identical marker stream. No Python
runner, automatic test harness, network interface or external system was used.
Dynamic runtime evidence is limited to the built router/QEMU images; the artifact
checks establish package inclusion across the eleven thin device recipes.

> ⚠️ **Disclaimer:** Intentionally insecure, isolated benchmark fixture only.
> The two byte streams are synthetic local Java objects; their only observable
> side effect is an in-memory counter in the disposable guest. They provide no
> persistence, remote access or exploitation chain and must not be reused
> outside this benchmark.

Source: [cwe502-java-deserialization](../meta-iotbench/recipes-vulns/cwe502-java-deserialization/).
