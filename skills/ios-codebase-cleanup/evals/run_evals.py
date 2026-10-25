#!/usr/bin/env python3
"""
run_evals.py
Executes the evaluation suite for ios-codebase-cleanup against all fixtures.
"""

import sys
import json
import time
from pathlib import Path

# Add scripts directory
SKILL_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_DIR / "scripts"))

from scan_codebase_cleanup import CleanupScanner

def run_evals():
    evals_file = SKILL_DIR / "evals" / "evals.json"
    with open(evals_file, "r") as f:
        data = json.load(f)

    print("=" * 70)
    print(" 🧪 Running Evals for: ios-codebase-cleanup")
    print("=" * 70)

    start_total_time = time.perf_counter()
    results = []

    # --- Eval 1: Dead Swift Files ---
    e1_start = time.perf_counter()
    e1_dir = SKILL_DIR / "evals" / "files" / "eval1_dead_files"
    s1 = CleanupScanner(str(e1_dir), scopes=["files"])
    s1.run()
    res1 = s1.get_summary()
    e1_time = time.perf_counter() - e1_start

    dead_files = [f["path"] for f in res1["dead_files"]]
    e1_checks = [
        ("Identifies DeadLegacyHelper.swift", any("DeadLegacyHelper.swift" in f for f in dead_files)),
        ("Preserves ActiveService.swift", not any("ActiveService.swift" in f for f in dead_files)),
        ("Preserves PreviewCardView.swift (#Preview)", not any("PreviewCardView.swift" in f for f in dead_files)),
        ("High confidence rating", any(f["confidence"] == "High" for f in res1["dead_files"]))
    ]
    e1_passed = all(c[1] for c in e1_checks)
    results.append(("Eval 1: Dead Swift Files", e1_passed, e1_time, e1_checks))

    # --- Eval 2: Dead Asset Catalogs ---
    e2_start = time.perf_counter()
    e2_dir = SKILL_DIR / "evals" / "files" / "eval2_dead_assets"
    s2 = CleanupScanner(str(e2_dir), scopes=["assets"])
    s2.run()
    res2 = s2.get_summary()
    e2_time = time.perf_counter() - e2_start

    dead_assets = [a["path"] for a in res2["dead_assets"]]
    e2_checks = [
        ("Identifies zombie_banner.imageset", any("zombie_banner.imageset" in a for a in dead_assets)),
        ("Identifies dead_brand_color.colorset", any("dead_brand_color.colorset" in a for a in dead_assets)),
        ("Preserves app_logo.imageset (symbol usage)", not any("app_logo.imageset" in a for a in dead_assets)),
        ("Calculates reclaimable size", res2["summary"]["reclaimable_bytes"] > 0)
    ]
    e2_passed = all(c[1] for c in e2_checks)
    results.append(("Eval 2: Dead Asset Catalogs", e2_passed, e2_time, e2_checks))

    # --- Eval 3: Orphan Docs & Loose Media ---
    e3_start = time.perf_counter()
    e3_dir = SKILL_DIR / "evals" / "files" / "eval3_orphan_docs"
    s3 = CleanupScanner(str(e3_dir), scopes=["docs"])
    s3.run()
    res3 = s3.get_summary()
    e3_time = time.perf_counter() - e3_start

    dead_docs = [d["path"] for d in res3["dead_docs"]]
    e3_checks = [
        ("Identifies abandoned_v1_notes.md", any("abandoned_v1_notes.md" in d for d in dead_docs)),
        ("Identifies dead_screenshot.png", any("dead_screenshot.png" in d for d in dead_docs)),
        ("Preserves linked architecture.md", not any("architecture.md" in d for d in dead_docs))
    ]
    e3_passed = all(c[1] for c in e3_checks)
    results.append(("Eval 3: Orphan Docs & Loose Media", e3_passed, e3_time, e3_checks))

    # --- Eval 4: Dead Symbols & Unused Imports ---
    e4_start = time.perf_counter()
    e4_dir = SKILL_DIR / "evals" / "files" / "eval4_symbols_and_imports"
    s4 = CleanupScanner(str(e4_dir), scopes=["symbols", "imports"])
    s4.run()
    res4 = s4.get_summary()
    e4_time = time.perf_counter() - e4_start

    dead_symbols = [s["symbol"] for s in res4["dead_symbols"]]
    dead_imports = [i["import"] for i in res4["dead_imports"]]
    e4_checks = [
        ("Identifies dead private func legacyCryptoHasher()", any("legacyCryptoHasher" in s for s in dead_symbols)),
        ("Identifies dead private let unusedSecretSeed", any("unusedSecretSeed" in s for s in dead_symbols)),
        ("Identifies unused CoreLocation import", any("CoreLocation" in i for i in dead_imports)),
        ("Preserves Foundation import", not any("Foundation" in i for i in dead_imports))
    ]
    e4_passed = all(c[1] for c in e4_checks)
    results.append(("Eval 4: Dead Symbols & Imports", e4_passed, e4_time, e4_checks))

    total_duration = time.perf_counter() - start_total_time

    # Output report
    all_passed = True
    total_checks = 0
    passed_checks = 0

    for name, passed, duration, checks in results:
        status_icon = "✅ PASS" if passed else "❌ FAIL"
        if not passed:
            all_passed = False
        print(f"\n{status_icon} | {name} ({duration*1000:.2f}ms)")
        for desc, check_res in checks:
            total_checks += 1
            if check_res:
                passed_checks += 1
                print(f"   [x] {desc}")
            else:
                print(f"   [ ] {desc} (FAILED)")

    print("\n" + "=" * 70)
    print(f" 📊 Final Evaluation Summary:")
    print(f"    Pass Rate:          {passed_checks}/{total_checks} ({passed_checks/total_checks*100:.1f}%)")
    print(f"    Total Scan Time:    {total_duration*1000:.2f}ms")
    print(f"    Scenarios Passing:  {sum(1 for _, p, _, _ in results)}/{len(results)}")
    print("=" * 70)

    return all_passed

if __name__ == "__main__":
    success = run_evals()
    sys.exit(0 if success else 1)
