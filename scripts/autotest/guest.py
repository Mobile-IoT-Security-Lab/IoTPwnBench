"""Boot an exported firmware under QEMU in a container and drive it.

Each guest runs in its own container on the default Docker network. QEMU forwards
the guest ports to 127.0.0.1 inside that container, so several guests can run
side by side. Checks run inside the same container, through "docker exec", and
shell commands run in the guest over the serial console.
"""
import os
from pathlib import Path
import queue
import re
import subprocess
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
IMAGE = os.environ.get("YOCTO_BUILDER_IMAGE", "yocto-builder") + ":6.0.3"
ROOT_PASSWORD = "routeradmin"


class Guest:
    def __init__(self, firmware, machine="qemuarm64", build_volume="yocto-build"):
        self.firmware, self.machine = firmware, machine
        self.name = f"autotest-{firmware}-{os.getpid()}"[:60]
        self.lines = queue.Queue()
        self.log = []
        script = f"""
        for native in /workdir/build/tmp/work/*/qemu-helper-native/*/recipe-sysroot-native; do
            if [ -x "$native/usr/bin/qemu-system-aarch64" ]; then
                export PATH="$native/usr/bin:$PATH"
                export LD_LIBRARY_PATH="$native/usr/lib:$native/lib"
                exec sh /scripts/run-qemu.sh
            fi
        done
        echo "native QEMU not found" >&2; exit 1
        """
        self.process = subprocess.Popen(
            ["docker", "run", "--rm", "-i", "--name", self.name, "--user", "1000:1000", "--cap-drop", "ALL",
             "--read-only", "--tmpfs", "/tmp:rw,mode=1777", "--tmpfs", "/var/tmp:rw,mode=1777",
             "-v", f"{build_volume}:/workdir:ro", "-v", f"{ROOT}/deploy-images:/deploy-images:ro",
             "-v", f"{ROOT}/scripts:/scripts:ro", "-e", f"FIRMWARE={firmware}", "-e", f"YOCTO_MACHINE={machine}",
             "-e", "TMPDIR=/tmp", "-e", "QEMU_ROOTFS_DIR=/tmp/rootfs", IMAGE, "bash", "-euc", script],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        threading.Thread(target=self._read, daemon=True).start()
        self.buffer = ""

    def _read(self):
        for chunk in iter(lambda: self.process.stdout.read1(4096), b""):
            self.lines.put(chunk.decode("utf-8", "replace"))
        self.lines.put(None)

    def expect(self, pattern, timeout=180):
        """Wait until the console output matches the regex, return the text before the match."""
        end = time.time() + timeout
        regex = re.compile(pattern, re.S)
        while True:
            match = regex.search(self.buffer)
            if match:
                before, self.buffer = self.buffer[:match.start()], self.buffer[match.end():]
                self.log.append(before + match.group(0))
                return before
            remaining = end - time.time()
            if remaining <= 0:
                raise TimeoutError(f"no match for {pattern!r} in the last output: {self.buffer[-300:]!r}")
            try:
                chunk = self.lines.get(timeout=min(remaining, 5))
            except queue.Empty:
                continue
            if chunk is None:
                raise EOFError(f"QEMU ended: {self.buffer[-300:]!r}")
            self.buffer += chunk

    def send(self, text):
        self.process.stdin.write(text.encode())
        self.process.stdin.flush()

    def login(self, timeout=900):
        self.expect(r"login: ", timeout)
        self.send("root\n")
        self.expect(r"[Pp]assword: ", 30)
        self.send(ROOT_PASSWORD + "\n")
        self.expect(r"# ", 60)
        self.run("stty -echo; export PS1='# '; PATH=$PATH:/usr/sbin:/sbin", 10)

    def run(self, command, timeout=60):
        """Run a shell command in the guest and return its output."""
        marker = f"__done{time.time_ns()}__"
        self.send(f"{command}; echo {marker}$?\n")
        out = self.expect(marker + r"\d+", timeout)
        code = re.search(marker + r"(\d+)", self.log[-1]).group(1)
        lines = out.replace("\r", "").split("\n")
        return "\n".join(lines[1:]).strip(), int(code)

    def interactive(self, send_expect, timeout=30):
        out = []
        for text, pattern in send_expect:
            if text:
                self.send(text)
            out.append(self.expect(pattern, timeout))
        return "\n".join(out)

    def host(self, code, timeout=60):
        """Run Python code inside the QEMU container, next to the forwarded ports."""
        if isinstance(code, (tuple, list)):
            command, code = ["docker", "exec", self.name, *code], None
        else:
            command = ["docker", "exec", "-i", self.name, "python3", "-"]
        result = subprocess.run(command, input=code, text=True, capture_output=True, timeout=timeout)
        return (result.stdout + result.stderr).strip()

    def stop(self):
        subprocess.run(["docker", "kill", self.name], capture_output=True)
        try:
            self.process.wait(timeout=20)
        except subprocess.TimeoutExpired:
            self.process.kill()
