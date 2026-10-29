"""Validate that the extracted repository stands on its own."""
import ast
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]


class SubmissionLayoutTests(unittest.TestCase):
    def test_both_mode_configs_load_from_an_unrelated_working_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            for mode in ("fixed", "dynamic"):
                result = subprocess.run(
                    [sys.executable, "-I", str(ROOT / "scripts/full_run_controller.py"),
                     "--avoidance-mode", mode, "--check-config",
                     "--log-dir", str(Path(directory) / "logs")],
                    cwd=directory, capture_output=True, text=True, timeout=10,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                report = json.loads(result.stdout)
                self.assertEqual(report["avoidance_mode"], mode)
                self.assertEqual(report["mcu_protocol"], "legacy")
                self.assertEqual(report["side_sensor_source"], "mcu")
                self.assertFalse((Path(directory) / "logs").exists())

    def test_local_python_imports_have_no_missing_runtime_files(self):
        roots = (ROOT / "jetson", ROOT / "scripts")
        for directory in roots:
            for source in directory.rglob("*.py"):
                tree = ast.parse(source.read_text(encoding="utf-8"))
                for node in ast.walk(tree):
                    if not isinstance(node, ast.ImportFrom):
                        continue
                    module = node.module or ""
                    if node.level:
                        parent = source.parent
                        for _ in range(node.level - 1):
                            parent = parent.parent
                        target = parent.joinpath(*module.split("."))
                    elif module == "jetson" or module.startswith("jetson."):
                        target = ROOT.joinpath(*module.split("."))
                    else:
                        continue
                    self.assertTrue(target.with_suffix(".py").is_file() or target.is_dir(),
                                    f"{source.relative_to(ROOT)} needs {module}")

    def test_runtime_source_snapshot_contains_only_present_files(self):
        source = (ROOT / "scripts/start_full_run.sh").read_text(encoding="utf-8")
        block = source.split('tar -czf "$LOG_DIR/source.tar.gz" -C "$PROJECT_DIR"', 1)[1]
        block = block.split("sha256sum", 1)[0].replace("\\\n", " ")
        files = shlex.split(block)
        self.assertIn("jetson/amr_core/full_run.py", files)
        self.assertIn("scripts/full_run_controller.py", files)
        for relative in files:
            self.assertTrue((ROOT / relative).is_file(), f"Missing snapshot dependency: {relative}")
            self.assertFalse(relative.startswith(("stm32/", "protocol/", "monitoring/")))

    def test_setup_snapshot_contains_only_present_files(self):
        source = (ROOT / "scripts/full_run_setup_steps.sh").read_text(encoding="utf-8")
        block = source.split("for source_file in ", 1)[1].split("; do", 1)[0]
        for relative in shlex.split(block.replace("\\\n", " ")):
            self.assertTrue((ROOT / relative).is_file(), relative)

    def test_ros_packages_reference_only_included_messages_and_entrypoints(self):
        workspace = ROOT / "jetson_ws/src"
        cmake = (workspace / "amr_interfaces/CMakeLists.txt").read_text(encoding="utf-8")
        for message in re.findall(r'"(msg/[^\"]+)"', cmake):
            self.assertTrue((workspace / "amr_interfaces" / message).is_file())
        for package in ("amr_interfaces", "amr_vision"):
            metadata = ET.parse(workspace / package / "package.xml").getroot()
            self.assertEqual(metadata.findtext("name"), package)
        setup = (workspace / "amr_vision/setup.py").read_text(encoding="utf-8")
        self.assertNotIn("amr_vision.yolo_node", setup)
        self.assertIn("amr_vision.yolo_udp_bridge_node:main", setup)


if __name__ == "__main__":
    unittest.main()
