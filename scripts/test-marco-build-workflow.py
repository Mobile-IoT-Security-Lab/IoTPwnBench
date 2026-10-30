#!/usr/bin/env python3
"""Check the shared firmware-selection workflow using command doubles only."""

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
LAYER = ROOT / "meta-iotbench"


def marco_recipes():
    """Read expected flags from recipe metadata, independently of the wrapper."""
    recipes = {}
    for recipe in sorted((LAYER / "recipes-images").glob("iotbench-*.bb")):
        for include in re.findall(r"^require (recipes-images/\S+)", recipe.read_text(), re.M):
            flags = re.findall(r'^(IOTBENCH_ENABLE_[A-Z_]+_FIXTURE)\s*\?=\s*"0"',
                               (LAYER / include).read_text(), re.M)
            if flags:
                assert len(flags) == 1, include
                recipes[recipe.stem.removeprefix("iotbench-")] = flags[0]
            elif include.endswith("/iotbench-permit-empty-passwords.inc"):
                recipes[recipe.stem.removeprefix("iotbench-")] = None
    return recipes


class BuildWorkflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.recipes = marco_recipes()
        cls.temporary = tempfile.TemporaryDirectory(prefix="marco-build-workflow-")
        cls.work = Path(cls.temporary.name)
        cls.record = cls.work / "record.json"
        cls.wrapper = cls.work / "build.sh"
        cls.wrapper.write_text((ROOT / "scripts/container-build-and-export.sh").read_text().replace(
            "source /opt/yocto/yocto-env.sh", ": # offline dispatch check"))
        bitbake = cls.work / "bitbake"
        bitbake.write_text("#!" + sys.executable + "\n" + '''import json, os, sys
from pathlib import Path
args = sys.argv[1:]
config = Path(args[1]) if args[0] == '-r' else None
Path(os.environ['CAPTURE']).write_text(json.dumps({
    'target': args[-1], 'config': config.read_text() if config else None,
    'temporary': str(config) if config else None,
}))
raise SystemExit(39)
''')
        bitbake.chmod(0o755)
        cls.environment = {
            "PATH": str(cls.work) + os.pathsep + "/usr/bin:/bin",
            "CAPTURE": str(cls.record), "TMPDIR": str(cls.work),
            "IOTBENCH_ENABLE_CWE120_FIXTURE": "0",
        }

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def invoke(self, firmware, **overrides):
        self.record.unlink(missing_ok=True)
        return subprocess.run(["bash", str(self.wrapper)],
                              env=dict(self.environment, FIRMWARE=firmware, **overrides),
                              capture_output=True, text=True, timeout=10)

    def test_named_selection_covers_every_marco_image(self):
        self.assertEqual(len(self.recipes), 517)  # 39 catalog + 8 extra, for 11 devices.
        self.assertEqual(sum(name.startswith("router-") for name in self.recipes), 47)
        for firmware, flag in self.recipes.items():
            with self.subTest(firmware=firmware):
                result = self.invoke(firmware)
                self.assertEqual(result.returncode, 39, result.stderr)
                record = json.loads(self.record.read_text())
                self.assertEqual(record["target"], "iotbench-" + firmware)
                if flag:
                    self.assertIn('IOTBENCH_BUILD_MODE = "fixture"', record["config"])
                    self.assertEqual(re.findall(r'^(IOTBENCH_ENABLE_\w+) = "1"$',
                                               record["config"], re.M), [flag])
                    self.assertFalse(Path(record["temporary"]).exists())
                    if flag == "IOTBENCH_ENABLE_FTP_WRITE_FIXTURE":
                        self.assertIn('DISTRO_FEATURES:append = " pam systemd"', record["config"])
                else:
                    self.assertIsNone(record["config"])

    def test_explicit_disable_production_and_mixing_are_rejected(self):
        representatives = {flag: firmware for firmware, flag in self.recipes.items() if flag}
        for flag, firmware in representatives.items():
            for overrides in ({flag: "0"}, {flag: ""}, {flag: "invalid"},
                              {"IOTBENCH_BUILD_MODE": "production"},
                              {"IOTBENCH_ENABLE_UNRELATED_FIXTURE": "1"}):
                with self.subTest(firmware=firmware, overrides=overrides):
                    result = self.invoke(firmware, **overrides)
                    self.assertEqual(result.returncode, 1, result.stderr)
                    self.assertFalse(self.record.exists(), "Rejected selection invoked BitBake")

    def test_unrelated_firmware_keeps_ordinary_build(self):
        result = self.invoke("router-cwe078-os-command-injection")
        self.assertEqual(result.returncode, 39, result.stderr)
        self.assertIsNone(json.loads(self.record.read_text())["config"])


class FtpWorkflow(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location("ftp_workflow", ROOT / "scripts/test-ftp-write-rights.py")
        self.ftp = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.ftp)

    def test_build_uses_shared_compose_command(self):
        with mock.patch.object(sys, "argv", ["ftp", "--device", "router", "--build"]), \
                mock.patch.object(self.ftp.subprocess, "run") as run, \
                mock.patch.object(self.ftp, "verify") as verify:
            self.ftp.main()
        self.assertEqual(run.call_args.args[0], ["docker", "compose", "run", "--rm", "yocto"])
        self.assertEqual(run.call_args.kwargs["env"]["FIRMWARE"], "router-cwe276-bad-write-rights")
        verify.assert_called_once_with("router", 150)

    def test_missing_native_dependencies_fail_before_starting_a_vm(self):
        with mock.patch.object(self.ftp.shutil, "which", return_value=None), \
                mock.patch.object(self.ftp.subprocess, "Popen") as popen:
            with self.assertRaisesRegex(RuntimeError, "Install the host QEMU requirements"):
                self.ftp.verify("router", 1)
        popen.assert_not_called()

    def test_help_has_no_backend_choice(self):
        output = io.StringIO()
        with mock.patch.object(sys, "argv", ["ftp", "--help"]), contextlib.redirect_stdout(output):
            with self.assertRaises(SystemExit) as result:
                self.ftp.main()
        self.assertEqual(result.exception.code, 0)
        self.assertNotIn("qemu-backend", output.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
