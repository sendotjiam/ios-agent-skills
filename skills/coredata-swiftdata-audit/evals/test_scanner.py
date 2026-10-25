#!/usr/bin/env python3
"""
test_scanner.py - Automated Evaluation Benchmark for coredata-swiftdata-audit

Runs CoreDataSwiftDataScanner against all eval test fixtures and verifies detection accuracy.
"""

import sys
import time
from pathlib import Path

# Add scripts directory to sys.path
SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from scan_coredata_swiftdata import CoreDataSwiftDataScanner

EVALS_DIR = Path(__file__).resolve().parent / "files"

EXPECTED_RULES = {
    "ConcurrencyViolations.swift": [
        "CD_THREAD_UNCONFINED_ACCESS",
        "CD_TASK_DETACHED_CONTEXT_LEAK",
        "CD_VIEWCONTEXT_BACKGROUND_ACCESS",
        "SWIFTDATA_UNISOLATED_MODEL_CONTEXT",
        "SWIFTDATA_MAINCONTEXT_IN_TASK"
    ],
    "FaultThrashingNPlusOne.swift": [
        "CD_FETCH_MISSING_BATCH_SIZE",
        "CD_FAULT_THRASHING_N_PLUS_ONE",
        "REACTIVE_QUERY_SEARCH_THRASH"
    ],
    "BatchingAndMemoryBloat.swift": [
        "CD_MISSING_AUTO_MERGE",
        "CD_LOOP_ROW_BY_ROW_DELETE",
        "CD_UNBOUNDED_BATCH_IMPORT"
    ],
    "CloudKitAndMultiContextViolations.swift": [
        "CD_SYNCHRONOUS_STORE_LOAD",
        "CLOUDKIT_MISSING_RELATIONSHIP_INVERSE",
        "CLOUDKIT_UNSUPPORTED_UNIQUE_CONSTRAINT",
        "PERSISTENCE_LARGE_BINARY_INLINE",
        "SWIFTDATA_UNMARKED_TRANSIENT_PROPERTY",
        "PERSISTENCE_PREVIEW_DISK_LEAK"
    ]
}

def run_benchmarks():
    print("=" * 70)
    print("Running coredata-swiftdata-audit Evaluation Benchmark Suite")
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
        scanner = CoreDataSwiftDataScanner(str(file_path), min_severity="low")
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
