#!/usr/bin/env python3
"""Verify the actual 3DES helper, including interoperability and malformed input."""
import concurrent.futures
import hashlib
import hmac
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: test-weak-cipher.py /path/to/iotbench-weak-cipher")
    binary = str(Path(sys.argv[1]).resolve())
    openssl = shutil.which("openssl")
    if not openssl:
        raise SystemExit("OpenSSL CLI is required")
    with tempfile.TemporaryDirectory(prefix="iotbench-3des-") as directory:
        key = bytes.fromhex("0123456789abcdef23456789abcdef01456789abcdef0123")
        iv = bytes.fromhex("1234567890abcdef")
        mac_key = bytes(range(0xa0, 0xc0))

        def run(operation, data, success=True, cwd=directory):
            result = subprocess.run(
                [binary, operation], input=data, cwd=cwd,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
            )
            assert (result.returncode == 0) == success, result.stderr.decode()
            if not success:
                assert result.stdout == b"", "Failed operation leaked output"
            return result.stdout

        samples = [b"", b"backup", b"12345678", b"123456789",
                   'Device backup: temperatura 21°C'.encode(),
                   bytes(range(256)), b"A" * 4096,
                   b"'; id; $(touch /tmp/unused); `uname`"]
        for plain in samples:
            frame = run("encrypt", plain)
            assert frame.startswith(b"3DES-CBC:")
            assert run("decrypt", frame) == plain
            assert run("decrypt", frame.rstrip(b"\n")) == plain
            raw = bytes.fromhex(frame.decode().strip().split(":", 1)[1])
            assert raw[:8] == iv, "Frame does not contain the hardcoded IV"
            assert hmac.compare_digest(
                raw[-32:], hmac.new(mac_key, raw[:-32], hashlib.sha256).digest()
            ), "Invalid HMAC-SHA256"
            reference = subprocess.run(
                [openssl, "enc", "-d", "-des-ede3-cbc", "-K", key.hex(),
                 "-iv", iv.hex()], input=raw[8:-32],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
            )
            assert reference.stdout == plain, "OpenSSL 3DES interoperability failed"

        first = run("encrypt", b"same backup")
        second = run("encrypt", b"same backup")
        assert first == second, "Hardcoded key and IV must give deterministic output"
        other_instance = Path(directory) / "other-instance"
        other_instance.mkdir()
        assert run("encrypt", b"same backup", cwd=other_instance) == first
        assert run("decrypt", first, cwd=other_instance) == b"same backup"
        assert not list(other_instance.iterdir()), "Helper created runtime key files"

        # Public keys allow anyone to create a valid encrypted frame independently.
        forged_plain = b"backup-from-public-keys"
        ciphertext = subprocess.run(
            [openssl, "enc", "-des-ede3-cbc", "-K", key.hex(), "-iv", iv.hex()],
            input=forged_plain, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
        ).stdout
        forged = iv + ciphertext
        forged += hmac.new(mac_key, forged, hashlib.sha256).digest()
        assert run("decrypt", b"3DES-CBC:" + forged.hex().encode()) == forged_plain

        raw = bytearray.fromhex(first.decode().strip().split(":", 1)[1])
        for offset in (0, 8, len(raw) - 1):
            altered = bytearray(raw)
            altered[offset] ^= 1
            run("decrypt", b"3DES-CBC:" + altered.hex().encode(), success=False)
        for malformed in (b"", b"AES:" + raw.hex().encode(), b"3DES-CBC:0",
                          b"3DES-CBC:zz", b"3DES-CBC:" + b"00" * 48,
                          first[:-5], b"3DES-CBC:" + b"00" * 4145):
            run("decrypt", malformed, success=False)
        run("encrypt", b"A" * 4097, success=False)
        run("unknown", b"backup", success=False)

        # Separate helper processes must use the same embedded constants.
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            frames = list(pool.map(
                lambda _: run("encrypt", b"concurrent backup"), range(16)
            ))
        assert len(set(frames)) == 1
        for frame in frames:
            assert run("decrypt", frame) == b"concurrent backup"
        assert set(Path(directory).iterdir()) == {other_instance}, "Unexpected runtime key files"
    print("PASS: hardcoded 3DES/HMAC keys and IV, deterministic frames, OpenSSL interoperability and input limits")


if __name__ == "__main__":
    main()
