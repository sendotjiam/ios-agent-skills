#!/usr/bin/env python3
"""
run_evals.py
Executes the evaluation benchmark suite for the unified iOS auditor and adoption engine.
"""

import json
import os
import re
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EVALS_DIR = REPO_ROOT / "evals"
FILES_DIR = EVALS_DIR / "files"
SCRIPTS_DIR = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from ios_audit import UnifiedAuditor, format_xcode

# ANSI Colors
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def run_evals():
    evals_json = EVALS_DIR / "evals.json"
    with open(evals_json, "r") as f:
        spec = json.load(f)

    print(f"\n{BOLD}{CYAN}======================================================================{RESET}")
    print(f"{BOLD}{CYAN} 🧪 Running Evals for: {spec['suite_name']} (v{spec['version']}){RESET}")
    print(f"{BOLD}{CYAN}======================================================================{RESET}\n")

    start_total_time = time.perf_counter()
    results = []
    total_checks = 0
    passed_checks = 0

    # -------------------------------------------------------------
    # Eval 1: Suppression Engine Matrix
    # -------------------------------------------------------------
    e1_start = time.perf_counter()
    p1 = FILES_DIR / "SuppressionView.swift"
    auditor1 = UnifiedAuditor(target_path=p1, skills=["concurrency", "memory"], min_severity="LOW")
    findings1 = auditor1.run()
    e1_time = (time.perf_counter() - e1_start) * 1000

    hang_findings = [f for f in findings1 if f.rule_id == "HANG-001"]
    combine_findings = [f for f in findings1 if f.rule_id == "COMBINE_ASSIGN_CYCLE"]

    e1_checks = [
        ("Line 13 with same-line // ios-audit:ignore HANG-001 is suppressed", not any(f.line_number == 13 for f in hang_findings)),
        ("Line 16 unsuppressed Data(contentsOf:) is detected as HANG-001", any(f.line_number == 16 and f.rule_id == "HANG-001" for f in findings1)),
        ("Line 20 with previous-line // ios-audit:ignore-next-line is suppressed", not any(f.line_number == 20 for f in combine_findings)),
        ("Line 23 unsuppressed assign(to:on:) is detected as COMBINE_ASSIGN_CYCLE", any(f.line_number == 23 and f.rule_id == "COMBINE_ASSIGN_CYCLE" for f in findings1)),
        ("Total findings on SuppressionView.swift exactly equals 2 (zero bleed)", len(findings1) == 2),
    ]

    e1_pass = all(c[1] for c in e1_checks)
    results.append(("Eval 1: Suppression Engine Matrix", e1_pass, e1_time, e1_checks))

    # -------------------------------------------------------------
    # Eval 2: Test & Mock Directory Filtering
    # -------------------------------------------------------------
    e2_start = time.perf_counter()
    p2 = FILES_DIR / "SampleProject"

    # Default scan without --include-tests
    auditor2_default = UnifiedAuditor(target_path=p2, skills=["concurrency", "memory", "renders", "a11y"], include_tests=False)
    findings2_default = auditor2_default.run()

    # Opt-in scan with --include-tests
    auditor2_tests = UnifiedAuditor(target_path=p2, skills=["concurrency"], include_tests=True)
    findings2_tests = auditor2_tests.run()
    e2_time = (time.perf_counter() - e2_start) * 1000

    e2_checks = [
        ("Default scan of SampleProject ignores Tests/ (0 findings reported)", len(findings2_default) == 0),
        ("Scan with --include-tests detects test violations (Thread.sleep)", len(findings2_tests) >= 1 and any(f.rule_id == "DEADLOCK-002" for f in findings2_tests)),
        ("Test violation correctly attributed to AppTests.swift", any("AppTests.swift" in f.file_path for f in findings2_tests)),
    ]

    e2_pass = all(c[1] for c in e2_checks)
    results.append(("Eval 2: Test & Mock Directory Filtering", e2_pass, e2_time, e2_checks))

    # -------------------------------------------------------------
    # Eval 3: Xcode Build Log Conformance
    # -------------------------------------------------------------
    e3_start = time.perf_counter()
    p3 = FILES_DIR / "XcodeFormatTest.swift"
    auditor3 = UnifiedAuditor(target_path=p3, skills=["concurrency", "renders"], min_severity="LOW")
    findings3 = auditor3.run()
    xcode_output = format_xcode(auditor3)
    e3_time = (time.perf_counter() - e3_start) * 1000

    xcode_lines = [line for line in xcode_output.strip().splitlines() if line.strip()]
    xcode_regex = re.compile(r"^([^:]+):([0-9]+):([0-9]+):\s*(error|warning):\s*\[([^\]]+)\]\s*\[([^\]]+)\]\s*(.*)$")

    valid_lines = [bool(xcode_regex.match(line)) for line in xcode_lines]

    e3_checks = [
        ("All Xcode output lines conform to standard compiler regex", len(xcode_lines) > 0 and all(valid_lines)),
        ("Critical deadlock correctly mapped to 'error'", any(": error: [ios-concurrency-audit]" in l for l in xcode_lines)),
        ("SwiftUI render churn correctly formatted", any("[swiftui-render-optimization]" in l for l in xcode_lines)),
    ]

    e3_pass = all(c[1] for c in e3_checks)
    results.append(("Eval 3: Xcode Build Log Conformance", e3_pass, e3_time, e3_checks))

    # -------------------------------------------------------------
    # Eval 4: Multi-Skill Orchestration & Speed
    # -------------------------------------------------------------
    e4_start = time.perf_counter()
    all_10_skills = ["concurrency", "renders", "memory", "persistence", "a11y", "cleanup", "privacy", "launch", "testing", "duo"]
    auditor4 = UnifiedAuditor(
        target_path=p3,
        skills=all_10_skills,
        min_severity="LOW",
    )
    findings4 = auditor4.run()
    e4_time = (time.perf_counter() - e4_start) * 1000

    e4_checks = [
        ("All 10 skills executed with zero symbol or namespace collisions", len(auditor4.execution_times) == 10),
        ("Execution times measured for all 10 skills", all(k in auditor4.execution_times for k in all_10_skills)),
        ("Total multi-skill scan execution completes in < 50ms", e4_time < 50.0),
    ]

    e4_pass = all(c[1] for c in e4_checks)
    results.append(("Eval 4: Multi-Skill Orchestration & Speed", e4_pass, e4_time, e4_checks))

    # -------------------------------------------------------------
    # Output Benchmark Results
    # -------------------------------------------------------------
    total_time = (time.perf_counter() - start_total_time) * 1000

    for name, passed, duration, checks in results:
        status_color = GREEN if passed else RED
        status_text = "✓ PASSED" if passed else "✗ FAILED"
        print(f"  {BOLD}{name}{RESET} ({duration:.2f}ms)")
        print(f"  Status: {status_color}{status_text}{RESET}")
        for desc, check_pass in checks:
            total_checks += 1
            if check_pass:
                passed_checks += 1
                print(f"    {GREEN}✓{RESET} {desc}")
            else:
                print(f"    {RED}✗{RESET} {desc}")
        print()

    pass_rate = (passed_checks / total_checks) * 100 if total_checks else 0

    print(f"{BOLD}----------------------------------------------------------------------{RESET}")
    print(f"  Total Evals: {len(results)}  |  Checks Passed: {passed_checks}/{total_checks} ({pass_rate:.1f}%)")
    print(f"  Total Duration: {total_time:.2f}ms")
    print()

    if pass_rate == 100.0:
        print(f"  {GREEN}{BOLD}🎉 ALL BENCHMARK EVALS PASSED WITH 100% SUCCESS RATE!{RESET}\n")
    else:
        print(f"  {RED}{BOLD}❌ SOME EVAL CHECKS FAILED!{RESET}\n")

    return pass_rate == 100.0


if __name__ == "__main__":
    success = run_evals()
    sys.exit(0 if success else 1)
