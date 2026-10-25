#!/usr/bin/env python3
"""
test_scanner.py - Automated Evaluation Benchmark for ios-memory-leak-audit

Runs MemoryLeakScanner against all eval test files and verifies detection accuracy.
"""

import sys
import time
from pathlib import Path

# Add scripts directory to sys.path
SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from scan_memory_leaks import MemoryLeakScanner

EVALS_DIR = Path(__file__).resolve().parent / "files"

EXPECTED_RULES = {
    "eval1_combine_closures.swift": [
        "COMBINE_ASSIGN_CYCLE",
        "COMBINE_SINK_CYCLE"
    ],
    "eval2_delegates_timers_gcd.swift": [
        "STRONG_DELEGATE",
        "TIMER_TARGET_SELF",
        "GCD_TIMER_CYCLE",
        "GCD_DELAYED_RETENTION"
    ],
    "eval3_autorelease_bloat.swift": [
        "LOOP_WITHOUT_AUTORELEASE",
        "UNBOUNDED_CACHE",
        "CORE_DATA_BATCH_BLOAT"
    ],
    "eval4_concurrency_cf_webkit.swift": [
        "WEBKIT_HANDLER_CYCLE",
        "AVFOUNDATION_OBSERVER_LEAK",
        "NOTIFICATION_TOKEN_DISCARD",
        "UNMANAGED_CF_LEAK"
    ]
}

def run_benchmarks():
    print("=" * 70)
    print("Running ios-memory-leak-audit Evaluation Benchmark Suite")
    print("=" * 70)

    total_scenarios = len(EXPECTED_RULES)
    passed_scenarios = 0
    total_expected_rules = sum(len(rules) for rules in EXPECTED_RULES.values())
    total_detected_rules = 0

    overall_start = time.time()

    for filename, expected_rules in EXPECTED_RULES.items():
        file_path = EVALS_DIR / filename
        if not file_path.exists():
            print(f"❌ File not found: {file_path}")
            continue

        print(f"\nEvaluating: {filename}...")
        start_time = time.time()
        scanner = MemoryLeakScanner(str(file_path), min_severity="low")
        findings = scanner.scan()
        elapsed = (time.time() - start_time) * 1000

        detected_rule_ids = {f.rule_id for f in findings}
        missing_rules = [r for r in expected_rules if r not in detected_rule_ids]

        total_detected_rules += (len(expected_rules) - len(missing_rules))

        if not missing_rules:
            print(f"  ✓ Passed ({elapsed:.2f}ms) - All {len(expected_rules)} expected rules detected:")
            for r in expected_rules:
                print(f"    - {r}")
            passed_scenarios += 1
        else:
            print(f"  ❌ Failed ({elapsed:.2f}ms) - Missing {len(missing_rules)} rules: {missing_rules}")
            print(f"    Detected rule IDs: {detected_rule_ids}")

    total_time = (time.time() - overall_start) * 1000
    pass_rate = (passed_scenarios / total_scenarios) * 100
    rule_rate = (total_detected_rules / total_expected_rules) * 100

    print("\n" + "=" * 70)
    print(f"Benchmark Results: {passed_scenarios}/{total_scenarios} scenarios passed ({pass_rate:.1f}%)")
    print(f"Rules Detected:    {total_detected_rules}/{total_expected_rules} ({rule_rate:.1f}%)")
    print(f"Total Scan Time:   {total_time:.2f}ms")
    print("=" * 70)

    if pass_rate < 100.0:
        sys.exit(1)
    else:
        print("🎉 ALL BENCHMARK EVALUATIONS PASSED!")

if __name__ == "__main__":
    run_benchmarks()
