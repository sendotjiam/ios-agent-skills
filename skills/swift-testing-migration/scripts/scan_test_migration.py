#!/usr/bin/env python3
"""
scan_test_migration.py - Swift Testing Migration & Modernization Fast-Scanner

Audits Swift test suites for modernization to the WWDC24 Swift Testing framework:
  1. Legacy XCTestCase classes and test methods candidates for @Suite and @Test
  2. Legacy XCTAssert* assertions candidates for #expect(...) and #require(...)
  3. Loop-based assertions inside test functions candidates for @Test(arguments: [...])
  4. Flaky Thread.sleep / Task.sleep waits in tests candidates for confirmation(...)
  5. Legacy expectation(description:) + wait(for:) candidates for Swift Testing confirmations
"""

import argparse
import json
import os
import re
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# ANSI Colors
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


@dataclass
class Finding:
    severity: str  # Critical, High, Medium, Low
    category: str
    rule_id: str
    file_path: str
    line_number: int
    matched_snippet: str
    description: str
    remediation: str


XCT_ASSERTION_PATTERNS = [
    (re.compile(r'\bXCTAssertEqual\s*\('), "TEST_LEGACY_ASSERT_EQUAL", "XCTAssertEqual(a, b)", "#expect(a == b)"),
    (re.compile(r'\bXCTAssertTrue\s*\('), "TEST_LEGACY_ASSERT_TRUE", "XCTAssertTrue(x)", "#expect(x)"),
    (re.compile(r'\bXCTAssertFalse\s*\('), "TEST_LEGACY_ASSERT_FALSE", "XCTAssertFalse(x)", "#expect(!x)"),
    (re.compile(r'\bXCTAssertNil\s*\('), "TEST_LEGACY_ASSERT_NIL", "XCTAssertNil(x)", "#expect(x == nil)"),
    (re.compile(r'\bXCTAssertNotNil\s*\('), "TEST_LEGACY_ASSERT_NOT_NIL", "XCTAssertNotNil(x)", "try #require(x) or #expect(x != nil)"),
    (re.compile(r'\bXCTFail\s*\('), "TEST_LEGACY_XCTFAIL", "XCTFail(...)", "Issue.record(...)"),
]


class TestMigrationScanner:
    def __init__(
        self,
        target_path: str,
        min_severity: str = "low",
        ignore_patterns: Optional[List[str]] = None,
        include_tests: bool = True,  # Default to True because this skill targets tests!
    ):
        self.target_path = Path(target_path).resolve()
        self.min_severity = min_severity.lower()
        self.include_tests = include_tests
        base_ignores = ["Pods", "DerivedData", ".build", ".swiftpm", "Carthage", ".git", "golden_fixes"]
        if ignore_patterns:
            base_ignores.extend(ignore_patterns)
        self.ignore_patterns = base_ignores
        self.severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        self.findings: List[Finding] = []
        self.files_scanned = 0
        self.lines_scanned = 0

    def should_ignore(self, path: Path) -> bool:
        path_str = str(path)
        for pattern in self.ignore_patterns:
            if pattern in path_str.split(os.sep):
                return True
        return False

    def is_rule_suppressed(self, line: str, prev_line: Optional[str], rule_id: str) -> bool:
        if "//" in line:
            same_line_pat = re.compile(r"//\s*(?:ios-audit|swift-audit)\s*:\s*ignore\s+([\w\-, ]+)", re.IGNORECASE)
            m = same_line_pat.search(line)
            if m:
                ignored = [r.strip().upper() for r in m.group(1).split(",")]
                if "ALL" in ignored or rule_id.upper() in ignored:
                    return True
            if re.search(r"//\s*(?:ios-audit|swift-audit)\s*:\s*ignore-all\b", line, re.IGNORECASE):
                return True

        if prev_line and "//" in prev_line:
            next_line_pat = re.compile(r"//\s*(?:ios-audit|swift-audit)\s*:\s*(?:ignore-next-line|disable-next-line)\s+([\w\-, ]+)", re.IGNORECASE)
            m_next = next_line_pat.search(prev_line)
            if m_next:
                ignored = [r.strip().upper() for r in m_next.group(1).split(",")]
                if "ALL" in ignored or rule_id.upper() in ignored:
                    return True
            if re.search(r"//\s*(?:ios-audit|swift-audit)\s*:\s*(?:ignore-next-line-all|disable-next-line-all)\b", prev_line, re.IGNORECASE):
                return True

        return False

    def scan(self) -> List[Finding]:
        swift_files: List[Path] = []

        if self.target_path.is_file():
            if self.target_path.suffix == ".swift":
                swift_files.append(self.target_path)
        else:
            for root, dirs, files in os.walk(self.target_path):
                dirs[:] = [d for d in dirs if not any(ign in d for ign in self.ignore_patterns)]
                for file in files:
                    if file.endswith(".swift"):
                        full_p = Path(root) / file
                        if not self.should_ignore(full_p):
                            swift_files.append(full_p)

        self.files_scanned = len(swift_files)
        for s_file in swift_files:
            self._scan_file(s_file)

        min_rank = self.severity_order.get(self.min_severity, 1)
        self.findings = [
            f for f in self.findings if self.severity_order.get(f.severity.lower(), 1) >= min_rank
        ]
        self.findings.sort(
            key=lambda x: (-self.severity_order.get(x.severity.lower(), 1), x.file_path, x.line_number)
        )
        return self.findings

    def _scan_file(self, file_path: Path):
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return

        lines = content.splitlines()
        self.lines_scanned += len(lines)
        file_str = str(file_path)

        in_test_method = False
        in_loop = False

        for idx, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
                continue

            prev_line = lines[idx - 1] if idx > 0 else ""

            # 1. Legacy XCTestCase Class Declaration
            if re.search(r'\bclass\s+[A-Za-z0-9_]+\s*:\s*XCTestCase\b', line):
                rule_id = "TEST_LEGACY_XCTESTCASE_CLASS"
                if not self.is_rule_suppressed(line, prev_line, rule_id):
                    self.findings.append(Finding(
                        severity="High",
                        category="XCTest to Swift Testing Migration",
                        rule_id=rule_id,
                        file_path=file_str,
                        line_number=idx + 1,
                        matched_snippet=stripped,
                        description="Legacy XCTestCase class declaration. Can be migrated to modern Swift Testing @Suite.",
                        remediation="Migrate to '@Suite struct SuiteName' and replace 'func test*()' with '@Test func *()'."
                    ))

            # Track test method scope
            if re.search(r'\bfunc\s+test[A-Za-z0-9_]*\s*\(', line):
                in_test_method = True

            if in_test_method and stripped.startswith("for ") and " in " in stripped:
                in_loop = True

            # 2. Loop-based parameterized test candidates
            if in_loop and ("XCTAssert" in line or "#expect" in line):
                rule_id = "TEST_PARAMETERIZED_CANDIDATE"
                if not self.is_rule_suppressed(line, prev_line, rule_id):
                    self.findings.append(Finding(
                        severity="Medium",
                        category="Parameterized Test Modernization",
                        rule_id=rule_id,
                        file_path=file_str,
                        line_number=idx + 1,
                        matched_snippet=stripped,
                        description="Loop executing assertions over collection candidates for Swift Testing parameterized test.",
                        remediation="Replace loop with '@Test(arguments: [...]) func testItem(input: Type) { #expect(...) }'."
                    ))
                in_loop = False  # Avoid repeated alerts per loop

            # 3. Flaky Thread.sleep / Task.sleep in tests
            if ("Thread.sleep(" in line or "Task.sleep(" in line):
                rule_id = "TEST_FLAKY_SLEEP_WAIT"
                if not self.is_rule_suppressed(line, prev_line, rule_id):
                    self.findings.append(Finding(
                        severity="High",
                        category="Flaky Asynchronous Test Wait",
                        rule_id=rule_id,
                        file_path=file_str,
                        line_number=idx + 1,
                        matched_snippet=stripped,
                        description="Arbitrary Thread.sleep or Task.sleep used for async test synchronization, causing test flakiness and slow CI.",
                        remediation="Use Swift Testing 'await confirmation { confirm in ... }' or async polling."
                    ))

            # 4. Legacy expectation(description:) + wait(for: ...)
            if "expectation(description:" in line:
                rule_id = "TEST_LEGACY_XCT_EXPECTATION"
                if not self.is_rule_suppressed(line, prev_line, rule_id):
                    self.findings.append(Finding(
                        severity="Medium",
                        category="Legacy XCTExpectation Async Wait",
                        rule_id=rule_id,
                        file_path=file_str,
                        line_number=idx + 1,
                        matched_snippet=stripped,
                        description="Legacy XCTest expectation(description:) used for async callback waiting.",
                        remediation="Migrate to Swift Testing 'await confirmation(\"...\") { confirm in ... }'."
                    ))

            # 5. Legacy XCTest Assertions
            for pat, rule_id, old_fmt, new_fmt in XCT_ASSERTION_PATTERNS:
                if pat.search(line):
                    if not self.is_rule_suppressed(line, prev_line, rule_id):
                        self.findings.append(Finding(
                            severity="Low",
                            category="Legacy Assertion Macro",
                            rule_id=rule_id,
                            file_path=file_str,
                            line_number=idx + 1,
                            matched_snippet=stripped,
                            description=f"Legacy {old_fmt} macro. Swift Testing uses native expression macros.",
                            remediation=f"Replace with '{new_fmt}'."
                        ))


def format_table(scanner: TestMigrationScanner) -> str:
    lines = []
    lines.append(f"\n{BOLD}{CYAN}=== Swift Testing Modernization Audit ==={RESET}")
    lines.append(f"Scanned {scanner.files_scanned} files ({scanner.lines_scanned} lines)\n")

    counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    for f in scanner.findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1

    lines.append(
        f"{BOLD}Summary Findings:{RESET} "
        f"{RED}Critical: {counts['Critical']}{RESET} | "
        f"{YELLOW}High: {counts['High']}{RESET} | "
        f"{CYAN}Medium: {counts['Medium']}{RESET} | "
        f"{DIM}Low: {counts['Low']}{RESET}\n"
    )

    if not scanner.findings:
        lines.append(f"{GREEN}✅ Test suite fully modernized with Swift Testing!{RESET}\n")
        return "\n".join(lines)

    lines.append(f"{'SEV':<10} {'RULE ID':<32} {'LOCATION':<36} {'CATEGORY'}")
    lines.append("-" * 96)

    for f in scanner.findings:
        color = RED if f.severity == "Critical" else YELLOW if f.severity == "High" else CYAN if f.severity == "Medium" else DIM
        loc = f"{Path(f.file_path).name}:{f.line_number}"
        lines.append(f"{color}{f.severity:<10}{RESET} {f.rule_id:<32} {loc:<36} {f.category}")
        lines.append(f"  {DIM}Snippet:{RESET} {f.matched_snippet}")
        lines.append(f"  {DIM}Fix:{RESET} {f.remediation}\n")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Swift Testing Migration & Modernization Fast-Scanner")
    parser.add_argument("path", nargs="?", default=".", help="Target Xcode project, tests folder, or Swift file")
    parser.add_argument("--format", choices=["table", "json", "markdown", "xcode"], default="table")
    parser.add_argument("--min-severity", choices=["critical", "high", "medium", "low"], default="low")
    parser.add_argument("-o", "--output", help="Write report to file")

    args = parser.parse_args()
    scanner = TestMigrationScanner(args.path, min_severity=args.min_severity, include_tests=True)
    findings = scanner.scan()

    if args.format == "table":
        out = format_table(scanner)
    elif args.format == "xcode":
        out = "\n".join([f"{f.file_path}:{f.line_number}:1: {'error' if f.severity in ['Critical', 'High'] else 'warning'}: [swift-testing-migration] [{f.rule_id}] {f.description}" for f in findings])
    elif args.format == "markdown":
        out = f"# Swift Testing Modernization Report\n\nTotal findings: {len(findings)}\n"
    else:
        out = json.dumps([asdict(f) for f in findings], indent=2)

    if args.output:
        Path(args.output).write_text(out, encoding="utf-8")
        print(f"Report written to: {args.output}")
    else:
        if out:
            print(out)

    has_crit_or_high = any(f.severity in ["Critical", "High"] for f in findings)
    sys.exit(1 if has_crit_or_high else 0)


if __name__ == "__main__":
    main()
