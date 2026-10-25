#!/usr/bin/env python3
"""
test_scanner.py - Verification test suite for ios-a11y-audit scanner
"""

import sys
import os
import unittest
import json
from pathlib import Path

# Add scripts directory to path
SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
EVAL_FILES_DIR = SKILL_DIR / "evals" / "files"
sys.path.insert(0, str(SCRIPTS_DIR))

from scan_a11y import AccessibilityScanner, format_text, format_markdown, format_json

class TestAccessibilityScanner(unittest.TestCase):
    def test_accessible_view_zero_violations(self):
        """Clean accessible view must trigger 0 false positives"""
        scanner = AccessibilityScanner(str(EVAL_FILES_DIR / "AccessibleView.swift"), min_severity="low")
        findings = scanner.scan()
        self.assertEqual(len(findings), 0, f"Expected 0 violations, found {len(findings)}: {[f.rule_id for f in findings]}")

    def test_violations_view_comprehensive_detection(self):
        """ViolationsView must trigger multiple accessibility rules across all categories"""
        scanner = AccessibilityScanner(str(EVAL_FILES_DIR / "ViolationsView.swift"), min_severity="low")
        findings = scanner.scan()
        self.assertGreater(len(findings), 8, f"Expected >8 violations, found {len(findings)}")

        rule_ids = {f.rule_id for f in findings}
        expected_rules = {
            "A11Y-001", # Unlabelled icon button
            "A11Y-003", # Dynamic Type text clipping
            "A11Y-004", # Strict line limit
            "A11Y-005", # Sub-44pt tap target
            "A11Y-006", # Looping animation without reduce motion
            "A11Y-007", # Translucent material without fallback
            "A11Y-008", # Color-only state indicator
            "A11Y-009", # AsyncImage missing invert colors
            "A11Y-010", # Tap gesture missing .isButton trait
            "A11Y-011", # Hardcoded RGB color
            "A11Y-012"  # Redundant trait verbiage
        }
        for rule in expected_rules:
            self.assertIn(rule, rule_ids, f"Expected rule {rule} to be triggered in ViolationsView")

    def test_dynamic_type_violations(self):
        """DynamicTypeViolationView must trigger clipping and unscaled metric rules"""
        scanner = AccessibilityScanner(str(EVAL_FILES_DIR / "DynamicTypeViolation.swift"), min_severity="low")
        findings = scanner.scan()
        rule_ids = {f.rule_id for f in findings}
        self.assertIn("A11Y-003", rule_ids)
        self.assertIn("A11Y-013", rule_ids)

    def test_format_outputs(self):
        """Test text, markdown, and JSON output formatters"""
        scanner = AccessibilityScanner(str(EVAL_FILES_DIR / "ViolationsView.swift"))
        findings = scanner.scan()

        text_out = format_text(scanner, findings, 0.05)
        self.assertIn("iOS Accessibility Audit", text_out)
        self.assertIn("Critical:", text_out)

        md_out = format_markdown(scanner, findings, 0.05)
        self.assertIn("# iOS Accessibility Audit Report", md_out)
        self.assertIn("## Detailed Findings", md_out)

        json_out = format_json(scanner, findings, 0.05)
        data = json.loads(json_out)
        self.assertIn("metadata", data)
        self.assertIn("findings", data)
        self.assertEqual(data["metadata"]["files_scanned"], 1)

if __name__ == "__main__":
    unittest.main()
