#!/usr/bin/env python3
"""
test_ios_audit.py - Unit & integration tests for the unified iOS auditor (scripts/ios_audit.py).
"""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CLI_PATH = REPO_ROOT / "bin/ios-audit"


class TestUnifiedAuditor(unittest.TestCase):
    def test_cli_help(self):
        proc = subprocess.run([str(CLI_PATH), "--help"], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("Unified Multi-Skill iOS & Apple Engineering Auditor", proc.stdout)

    def test_single_file_audit(self):
        fixture = REPO_ROOT / "skills/ios-concurrency-audit/evals/files/eval1_transfer.swift"
        proc = subprocess.run(
            [str(CLI_PATH), str(fixture), "--skills", "concurrency", "--format", "json", "--no-exit-code"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0)
        data = json.loads(proc.stdout)
        self.assertGreaterEqual(data["total_findings"], 1)
        self.assertTrue(any(f["rule_id"] == "HANG-001" for f in data["findings"]))

    def test_xcode_format(self):
        fixture = REPO_ROOT / "skills/ios-concurrency-audit/evals/files/eval1_transfer.swift"
        proc = subprocess.run(
            [str(CLI_PATH), str(fixture), "--skills", "concurrency", "--format", "xcode", "--no-exit-code"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn(":1: error: [ios-concurrency-audit] [HANG-001]", proc.stdout)

    def test_inline_suppression_same_line(self):
        with tempfile.NamedTemporaryFile(suffix=".swift", mode="w", delete=False) as f:
            f.write(
                "import Foundation\n"
                "func test() {\n"
                "    let d = try? Data(contentsOf: url) // ios-audit:ignore HANG-001\n"
                "    let d2 = try? Data(contentsOf: url)\n"
                "}\n"
            )
            f_path = Path(f.name)

        try:
            proc = subprocess.run(
                [str(CLI_PATH), str(f_path), "--skills", "concurrency", "--format", "json", "--no-exit-code"],
                capture_output=True,
                text=True,
            )
            data = json.loads(proc.stdout)
            self.assertEqual(data["total_findings"], 1)
            self.assertEqual(data["findings"][0]["line_number"], 4)
        finally:
            f_path.unlink()

    def test_inline_suppression_next_line(self):
        with tempfile.NamedTemporaryFile(suffix=".swift", mode="w", delete=False) as f:
            f.write(
                "import Foundation\n"
                "func test() {\n"
                "    // ios-audit:ignore-next-line HANG-001\n"
                "    let d = try? Data(contentsOf: url)\n"
                "    let d2 = try? Data(contentsOf: url)\n"
                "}\n"
            )
            f_path = Path(f.name)

        try:
            proc = subprocess.run(
                [str(CLI_PATH), str(f_path), "--skills", "concurrency", "--format", "json", "--no-exit-code"],
                capture_output=True,
                text=True,
            )
            data = json.loads(proc.stdout)
            self.assertEqual(data["total_findings"], 1)
            self.assertEqual(data["findings"][0]["line_number"], 5)
        finally:
            f_path.unlink()

    def test_markdown_format(self):
        fixture = REPO_ROOT / "skills/ios-concurrency-audit/evals/files/eval1_transfer.swift"
        proc = subprocess.run(
            [str(CLI_PATH), str(fixture), "--skills", "concurrency", "--format", "markdown", "--no-exit-code"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("# iOS Agent Skills Unified Audit Report", proc.stdout)
        self.assertIn("`HANG-001`", proc.stdout)

    def test_sarif_format(self):
        fixture = REPO_ROOT / "skills/ios-concurrency-audit/evals/files/eval1_transfer.swift"
        proc = subprocess.run(
            [str(CLI_PATH), str(fixture), "--skills", "concurrency", "--format", "sarif", "--no-exit-code"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0)
        sarif = json.loads(proc.stdout)
        self.assertEqual(sarif["version"], "2.1.0")
        self.assertGreaterEqual(len(sarif["runs"][0]["results"]), 1)
        self.assertEqual(sarif["runs"][0]["tool"]["driver"]["name"], "ios-audit")


if __name__ == "__main__":
    unittest.main()
