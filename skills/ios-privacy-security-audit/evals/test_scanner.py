#!/usr/bin/env python3
"""
test_scanner.py - Automated Evaluation Benchmark for ios-privacy-security-audit
"""

import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from scan_privacy_security import PrivacySecurityScanner

EVALS_DIR = Path(__file__).resolve().parent / "files"

EXPECTED_RULES = {
    "eval1_privacy_manifest.swift": [
        "PRIV_REQ_USERDEFAULTS",
        "PRIV_REQ_BOOTTIME",
        "PRIV_REQ_DISKSPACE",
        "PRIV_REQ_FILETIME",
    ],
    "eval2_insecure_storage.swift": [
        "INSECURE_USERDEFAULTS_STORAGE",
    ],
    "eval3_hardcoded_secrets.swift": [
        "SEC_OPENAI_KEY",
        "SEC_GOOGLE_KEY",
        "SEC_AWS_KEY",
    ],
    "eval4_ats_biometrics.swift": [
        "INSECURE_HTTP_TRANSPORT",
        "BIOMETRIC_CHECK_WITHOUT_CAN_EVALUATE",
    ],
}


def run_benchmarks():
    print("=" * 70)
    print("Running ios-privacy-security-audit Evaluation Benchmark Suite")
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
        scanner = PrivacySecurityScanner(str(file_path), min_severity="low")
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
