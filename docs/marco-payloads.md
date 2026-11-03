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
| [Test 8: Apache applications](#test-8) | `cwe<CWE>-apache-web` | Guest / isolated host; browser for XSS and CSRF | Selected defect produces its marker or unauthorized state change |
| [Test 9: C path and filename](#test-9) | `cwe022-native-path-traversal`, `cwe020-native-filename-validation` | Guest / isolated host | Disallowed synthetic file is read; corrected control rejects it |
| [Test 10: C buffer overflow](#test-10) | `cwe787-native-buffer-overflow` | Host / guest with ASan | ASan identifies the out-of-bounds write; corrected control rejects the input |
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
