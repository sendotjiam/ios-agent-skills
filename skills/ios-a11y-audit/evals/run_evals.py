#!/usr/bin/env python3
"""
run_evals.py
Executes the comprehensive evaluation suite for ios-a11y-audit against all fixtures.
"""

import sys
import json
import time
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
EVALS_DIR = SKILL_DIR / "evals"
FILES_DIR = EVALS_DIR / "files"
sys.path.insert(0, str(SCRIPTS_DIR))

from scan_a11y import AccessibilityScanner

# ANSI Colors
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

def run_evals():
    evals_file = EVALS_DIR / "evals.json"
    with open(evals_file, "r") as f:
        spec = json.load(f)

    print(f"\n{BOLD}{CYAN}======================================================================{RESET}")
    print(f"{BOLD}{CYAN} 🧪 Running Evals for: {spec['skill_name']}{RESET}")
    print(f"{BOLD}{CYAN}======================================================================{RESET}\n")

    start_total_time = time.perf_counter()
    results = []

    # --- Eval 1: Multi-Category Accessibility Violations ---
    e1_start = time.perf_counter()
    p1 = str(FILES_DIR / "ViolationsView.swift")
    s1 = AccessibilityScanner(p1, min_severity="low")
    findings1 = s1.scan()
    e1_time = (time.perf_counter() - e1_start) * 1000
    rule_ids1 = {f.rule_id for f in findings1}

    e1_checks = [
        ("A11Y-001: Unlabelled icon button flagged as Critical VoiceOver blocker", "A11Y-001" in rule_ids1 and any(f.rule_id == "A11Y-001" and f.severity == "Critical" for f in findings1)),
        ("A11Y-003: Fixed height frame (35pt) on text flagged as Critical clipping", "A11Y-003" in rule_ids1 and any(f.rule_id == "A11Y-003" and f.severity == "Critical" for f in findings1)),
        ("A11Y-004: Strict .lineLimit(1) on body text flagged", "A11Y-004" in rule_ids1),
        ("A11Y-005: Sub-44pt button (20x20pt) flagged for touch bounding box violation", "A11Y-005" in rule_ids1),
        ("A11Y-006: Continuous .repeatForever() animation flagged for vestibular risk", "A11Y-006" in rule_ids1),
        ("A11Y-007: .ultraThinMaterial flagged for missing Reduce Transparency fallback", "A11Y-007" in rule_ids1),
        ("A11Y-008: Red/green state circle flagged for Differentiate Without Color", "A11Y-008" in rule_ids1),
        ("A11Y-009: AsyncImage flagged for missing Smart Invert protection", "A11Y-009" in rule_ids1),
        ("A11Y-010: Custom .onTapGesture flagged for missing .isButton trait", "A11Y-010" in rule_ids1),
        ("A11Y-011: Inline hardcoded RGB color flagged for contrast risk", "A11Y-011" in rule_ids1),
        ("A11Y-012: Redundant 'button' trait in accessibilityLabel flagged", "A11Y-012" in rule_ids1),
    ]
    e1_passed = all(c[1] for c in e1_checks)
    results.append(("Eval 1: ViolationsView.swift (Multi-Pillar Violations)", e1_passed, e1_time, e1_checks))

    # --- Eval 2: Dynamic Type Clipping & Geometry ---
    e2_start = time.perf_counter()
    p2 = str(FILES_DIR / "DynamicTypeViolation.swift")
    s2 = AccessibilityScanner(p2, min_severity="low")
    findings2 = s2.scan()
    e2_time = (time.perf_counter() - e2_start) * 1000
    rule_ids2 = {f.rule_id for f in findings2}

    e2_checks = [
        ("A11Y-003: Fixed height frame (40pt) on headline text flagged", "A11Y-003" in rule_ids2),
        ("A11Y-013: Layout dimensions declared as fixed CGFloat without @ScaledMetric", "A11Y-013" in rule_ids2),
        ("Surgical fix recommendation includes @ScaledMetric and minHeight", any("@ScaledMetric" in f.remediation for f in findings2))
    ]
    e2_passed = all(c[1] for c in e2_checks)
    results.append(("Eval 2: DynamicTypeViolation.swift (Scaling & Geometry)", e2_passed, e2_time, e2_checks))

    # --- Eval 3: AccessibleView.swift (Zero False Positives) ---
    e3_start = time.perf_counter()
    p3 = str(FILES_DIR / "AccessibleView.swift")
    s3 = AccessibilityScanner(p3, min_severity="low")
    findings3 = s3.scan()
    e3_time = (time.perf_counter() - e3_start) * 1000

    e3_checks = [
        ("0 violations detected in gold-standard compliant view", len(findings3) == 0),
        ("0 false positives on @ScaledMetric usage", not any(f.rule_id == "A11Y-013" for f in findings3)),
        ("0 false positives on 44pt touch targets", not any(f.rule_id == "A11Y-005" for f in findings3)),
        ("0 false positives on AsyncImage with invert color protection", not any(f.rule_id == "A11Y-009" for f in findings3)),
        ("0 false positives on Reduce Motion / Transparency wrappers", not any(f.rule_id in ["A11Y-006", "A11Y-007"] for f in findings3)),
    ]
    e3_passed = all(c[1] for c in e3_checks)
    results.append(("Eval 3: AccessibleView.swift (Gold Standard Verification)", e3_passed, e3_time, e3_checks))

    total_time = (time.perf_counter() - start_total_time) * 1000

    # Print summary cards
    all_passed = True
    total_checks = 0
    passed_checks = 0

    for title, passed, elapsed, checks in results:
        status_badge = f"{GREEN}✓ PASSED{RESET}" if passed else f"{RED}✗ FAILED{RESET}"
        print(f"  {BOLD}{title}{RESET} ({elapsed:.2f}ms)")
        print(f"  Status: {status_badge}")
        for desc, ok in checks:
            total_checks += 1
            if ok:
                passed_checks += 1
                print(f"    {GREEN}✓{RESET} {DIM}{desc}{RESET}")
            else:
                print(f"    {RED}✗ {desc}{RESET}")
                all_passed = False
        print()

    # Final summary box
    print(f"{BOLD}{CYAN}----------------------------------------------------------------------{RESET}")
    pass_rate = (passed_checks / total_checks) * 100 if total_checks > 0 else 0
    print(f"  {BOLD}Total Evals:{RESET} {len(results)}  |  {BOLD}Checks Passed:{RESET} {passed_checks}/{total_checks} ({pass_rate:.1f}%)")
    print(f"  {BOLD}Total Duration:{RESET} {total_time:.2f}ms")

    if all_passed:
        print(f"\n  {GREEN}{BOLD}🎉 ALL EVALS PASSED WITH 100% SUCCESS RATE!{RESET}\n")
        return 0
    else:
        print(f"\n  {RED}{BOLD}⚠️ SOME EVAL CHECKS FAILED.{RESET}\n")
        return 1

if __name__ == "__main__":
    sys.exit(run_evals())
