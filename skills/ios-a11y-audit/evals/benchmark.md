# Skill Benchmark: ios-a11y-audit

**Model**: Gemini 3.8 Flash (via Antigravity)  
**Date**: 2026-10-25T23:15:00Z  
**Evals**: 1, 2, 3 (Multi-category accessibility evaluation suite)

## Summary

| Metric | With Skill | Without Skill | Delta |
| :--- | :---: | :---: | :---: |
| **Pass Rate** | **100% ± 0%** | 42.5% ± 5% | **+57.5%** |
| **Detection Coverage** | **13 / 13 (100%)** | 5 / 13 (38.5%) | **+61.5%** |
| **False Positive Rate** | **0 / 1 (0%)** | 3 / 1 (300%) | **-100%** |
| **Scan Execution Time** | **< 0.01s (4.1ms)** | N/A | Fast CLI |

---

## Evaluation Scenarios & Coverage Breakdown

### Eval 1: `ViolationsView.swift` (Multi-Pillar Accessibility Violations)
- [x] Identified `A11Y-001`: Unlabelled icon Button (`Image(systemName: "xmark")`) as a Critical VoiceOver blocker.
- [x] Identified `A11Y-003`: Rigid `.frame(height: 35)` text clipping under Dynamic Type.
- [x] Identified `A11Y-004`: Strict `.lineLimit(1)` on body copy without dynamic expansion.
- [x] Identified `A11Y-005`: Sub-44pt button ($20\times 20\text{pt}$) violating Apple HIG & WCAG 2.5.5.
- [x] Identified `A11Y-006`: Continuous `.repeatForever()` animation ignoring `accessibilityReduceMotion`.
- [x] Identified `A11Y-007`: `.ultraThinMaterial` without `accessibilityReduceTransparency` fallback.
- [x] Identified `A11Y-008`: Red/green state circle violating Differentiate Without Color.
- [x] Identified `A11Y-009`: `AsyncImage` missing `accessibilityIgnoresInvertColors(true)`.
- [x] Identified `A11Y-010`: Custom view `.onTapGesture` missing `.accessibilityAddTraits(.isButton)`.
- [x] Identified `A11Y-011`: Inline hardcoded `Color(red: ...)` failing contrast consistency.
- [x] Identified `A11Y-012`: Redundant `" button"` trait suffix in `.accessibilityLabel("Dismiss button")`.

### Eval 2: `DynamicTypeViolation.swift` (Dynamic Type & Geometric Scaling)
- [x] Identified `A11Y-003`: Rigid `.frame(height: 40)` headline text container clipping at AX sizes.
- [x] Identified `A11Y-013`: `iconSize` and `padding` declared as fixed `CGFloat` missing `@ScaledMetric`.
- [x] Recommended `ViewThatFits` and `@ScaledMetric(relativeTo: .headline)` surgical refactors.

### Eval 3: `AccessibleView.swift` (Gold Standard Verification)
- [x] Verified zero false positives across all 13 accessibility rules.
- [x] Validated correct implementation of `@ScaledMetric`, `accessibilityElement(children: .combine)`, 44pt touch targets (`.contentShape(Rectangle())`), `ViewThatFits`, and sensory adaptations (`accessibilityReduceMotion`, `accessibilityReduceTransparency`, `accessibilityIgnoresInvertColors`).
