# Skill Benchmark: ios-codebase-cleanup

**Model**: Gemini 3.8 Flash (via Antigravity)  
**Date**: 2026-10-25T21:46:00Z  
**Evals**: 1, 2, 3, 4 (Multi-category evaluation suite)

## Summary

| Metric | With Skill | Without Skill | Delta |
| :--- | :---: | :---: | :---: |
| **Pass Rate** | **100% ± 0%** | 53.3% ± 5% | **+46.7%** |
| **Detection Coverage** | **15 / 15 (100%)** | 8 / 15 (53.3%) | **+46.7%** |
| **Scan Execution Time** | **< 0.01s (3.8ms)** | N/A | Fast CLI |

---

## Evaluation Scenarios & Coverage Breakdown

### Eval 1: `eval1_dead_files` (Dead Swift Source Files & Preview Retention)
- [x] Identified `DeadLegacyHelper.swift` as dead file with 0 occurrences.
- [x] Preserved `ActiveService.swift` (referenced across views).
- [x] Preserved `PreviewCardView.swift` containing `#Preview` per user design checkpoint.
- [x] Assigned High Confidence rating.

### Eval 2: `eval2_dead_assets` (Asset Catalogs & Swift 6 Generated Symbols)
- [x] Identified `zombie_banner.imageset` as dead unreferenced asset catalog.
- [x] Identified `dead_brand_color.colorset` as dead color catalog.
- [x] Preserved `app_logo.imageset` referenced via Xcode 15+ generated Swift symbol (`Image(.appLogo)`).
- [x] Accurately computed reclaimable disk space across bundle folders.

### Eval 3: `eval3_orphan_docs` (Orphaned Markdown & Loose Media)
- [x] Identified `docs/abandoned_v1_notes.md` unlinked in README navigation.
- [x] Identified `docs/dead_screenshot.png` loose media with zero markdown citations.
- [x] Preserved `docs/architecture.md` linked from `README.md`.

### Eval 4: `eval4_symbols_and_imports` (Dead Internal Symbols & Unused Imports)
- [x] Identified dead `private func legacyCryptoHasher()` inside active class.
- [x] Identified dead `private let unusedSecretSeed` property.
- [x] Identified unused `import CoreLocation` module dependency.
- [x] Preserved active `import Foundation` and public methods.
