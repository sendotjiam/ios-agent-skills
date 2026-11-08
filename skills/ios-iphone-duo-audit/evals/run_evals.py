#!/usr/bin/env python3
"""
run_evals.py
Executes the evaluation suite for ios-iphone-duo-audit against all fixtures in evals/files/.
"""

import json
import sys
import time
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
EVALS_DIR = SKILL_DIR / "evals"
FILES_DIR = EVALS_DIR / "files"
sys.path.insert(0, str(SCRIPTS_DIR))

from scan_iphone_duo import IPhoneDuoScanner

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

    # --- Eval 1: Screen bounds, idiom/orientation branching & fixed frame ---
    e1_start = time.perf_counter()
    p1 = str(FILES_DIR / "eval1_screen_and_idiom_layout.swift")
    s1 = IPhoneDuoScanner(p1, min_severity="low")
    findings1 = s1.scan()
    e1_time = (time.perf_counter() - e1_start) * 1000
    rule_ids1 = {f.rule_id for f in findings1}

    e1_checks = [
        ("Identifies UIScreen.main.bounds as DUO_SCREEN_BOUNDS_HARDCODED", "DUO_SCREEN_BOUNDS_HARDCODED" in rule_ids1),
        ("Identifies idiom/orientation branching as DUO_IDIOM_OR_ORIENTATION_LAYOUT", "DUO_IDIOM_OR_ORIENTATION_LAYOUT" in rule_ids1),
        ("Identifies rigid frame width as DUO_FIXED_FRAME_WIDTH", "DUO_FIXED_FRAME_WIDTH" in rule_ids1),
        ("DUO_SCREEN_BOUNDS_HARDCODED has Critical severity", any(f.rule_id == "DUO_SCREEN_BOUNDS_HARDCODED" and f.severity == "Critical" for f in findings1)),
    ]
    e1_passed = all(c[1] for c in e1_checks)
    results.append(("Eval 1: eval1_screen_and_idiom_layout.swift", e1_passed, e1_time, e1_checks))

    # --- Eval 2: ArrangementView nesting & fold division grid ---
    e2_start = time.perf_counter()
    p2 = str(FILES_DIR / "eval2_arrangement_and_fold_hazards.swift")
    s2 = IPhoneDuoScanner(p2, min_severity="low")
    findings2 = s2.scan()
    e2_time = (time.perf_counter() - e2_start) * 1000
    rule_ids2 = {f.rule_id for f in findings2}

    e2_checks = [
        ("Identifies invalid ArrangementView nesting as DUO_ARRANGEMENT_INVALID_NESTING", "DUO_ARRANGEMENT_INVALID_NESTING" in rule_ids2),
        ("Identifies 3-column LazyVGrid across fold division as DUO_ODD_GRID_COLUMNS_ON_FOLD", "DUO_ODD_GRID_COLUMNS_ON_FOLD" in rule_ids2),
        ("Flags both ScrollView nesting and NavigationSplitView nesting under ArrangementView", sum(1 for f in findings2 if f.rule_id == "DUO_ARRANGEMENT_INVALID_NESTING") >= 2),
    ]
    e2_passed = all(c[1] for c in e2_checks)
    results.append(("Eval 2: eval2_arrangement_and_fold_hazards.swift", e2_passed, e2_time, e2_checks))

    # --- Eval 3: Vertical Toolbar text buttons & manual spacers ---
    e3_start = time.perf_counter()
    p3 = str(FILES_DIR / "eval3_vertical_toolbar_hazards.swift")
    s3 = IPhoneDuoScanner(p3, min_severity="low")
    findings3 = s3.scan()
    e3_time = (time.perf_counter() - e3_start) * 1000
    rule_ids3 = {f.rule_id for f in findings3}

    e3_checks = [
        ("Identifies text-only ToolbarItem button as DUO_TOOLBAR_TEXT_ONLY_ITEM", "DUO_TOOLBAR_TEXT_ONLY_ITEM" in rule_ids3),
        ("Identifies manual toolbar spacer or custom ellipsis as DUO_MANUAL_TOOLBAR_SPACER", "DUO_MANUAL_TOOLBAR_SPACER" in rule_ids3),
        ("DUO_TOOLBAR_TEXT_ONLY_ITEM has High severity", any(f.rule_id == "DUO_TOOLBAR_TEXT_ONLY_ITEM" and f.severity == "High" for f in findings3)),
    ]
    e3_passed = all(c[1] for c in e3_checks)
    results.append(("Eval 3: eval3_vertical_toolbar_hazards.swift", e3_passed, e3_time, e3_checks))

    # --- Eval 4: Standalone UIKit bars bypassing vertical presentation ---
    e4_start = time.perf_counter()
    p4 = str(FILES_DIR / "eval4_uikit_custom_bars.swift")
    s4 = IPhoneDuoScanner(p4, min_severity="low")
    findings4 = s4.scan()
    e4_time = (time.perf_counter() - e4_start) * 1000
    rule_ids4 = {f.rule_id for f in findings4}

    e4_checks = [
        ("Identifies standalone UIToolbar/UITabBar instantiation as DUO_CUSTOM_BAR_BYPASS", "DUO_CUSTOM_BAR_BYPASS" in rule_ids4),
        ("Flags both UIToolbar and UITabBar standalone instances", sum(1 for f in findings4 if f.rule_id == "DUO_CUSTOM_BAR_BYPASS") >= 2),
    ]
    e4_passed = all(c[1] for c in e4_checks)
    results.append(("Eval 4: eval4_uikit_custom_bars.swift", e4_passed, e4_time, e4_checks))

    # --- Report Output ---
    total_time = (time.perf_counter() - start_total_time) * 1000
    total_checks = 0
    passed_checks = 0

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
