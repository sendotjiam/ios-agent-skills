# Skill Benchmark: ios-memory-leak-audit

**Model**: Gemini 3.8 Flash (via Antigravity)  
**Date**: 2026-10-25T22:15:00Z  
**Evals**: 1, 2, 3, 4 (Multi-category evaluation suite)

## Summary

| Metric | With Skill | Without Skill | Delta |
| :--- | :---: | :---: | :---: |
| **Pass Rate** | **100% ± 0%** | 46.2% ± 5% | **+53.8%** |
| **Detection Coverage** | **13 / 13 (100%)** | 6 / 13 (46.2%) | **+53.8%** |
| **Scan Execution Time** | **< 0.01s (4.02ms)** | N/A | Fast CLI |

---

## Evaluation Scenarios & Coverage Breakdown

### Eval 1: `eval1_combine_closures.swift` (Combine & Closure Capture Retain Cycles)
- [x] Identified `COMBINE_ASSIGN_CYCLE`: `assign(to: \.username, on: self)` permanent retain cycle.
- [x] Identified `COMBINE_SINK_CYCLE`: `.sink` closure strongly capturing `self`.
- [x] Recommended `assign(to: &$username)` and `[weak self]` surgical remediations.
- [x] Assigned Critical severity rating.

### Eval 2: `eval2_delegates_timers_gcd.swift` (Strong Delegates, Timers & GCD Delays)
- [x] Identified `STRONG_DELEGATE`: `var delegate: SettingsViewDelegate?` missing `weak` keyword.
- [x] Identified `TIMER_TARGET_SELF`: `Timer.scheduledTimer` retaining target `self` in RunLoop.
- [x] Identified `GCD_TIMER_CYCLE`: `DispatchSourceTimer` event handler strongly capturing `self`.
- [x] Identified `GCD_DELAYED_RETENTION`: `DispatchQueue.main.asyncAfter` retaining `self` across 60s delay.
- [x] Recommended `weak var`, block-based Timer / `WeakProxy`, and weak self captures.

### Eval 3: `eval3_autorelease_bloat.swift` (Memory Bloat, Autorelease Pools & Core Data Faults)
- [x] Identified `LOOP_WITHOUT_AUTORELEASE`: Batch loop processing `UIImage(contentsOfFile:)` without `@autoreleasepool`.
- [x] Identified `UNBOUNDED_CACHE`: Swift `Dictionary` used as cache without memory-pressure eviction.
- [x] Identified `CORE_DATA_BATCH_BLOAT`: Batch fetch loop lacking `context.reset()` or `refreshAllObjects()`.
- [x] Recommended `@autoreleasepool` iteration wrapping, `NSCache<Key, Value>`, and periodic `context.reset()`.

### Eval 4: `eval4_concurrency_cf_webkit.swift` (WebKit Handlers, AVFoundation & CoreFoundation)
- [x] Identified `WEBKIT_HANDLER_CYCLE`: `userContentController.add(self)` leaking `UIViewController`.
- [x] Identified `AVFOUNDATION_OBSERVER_LEAK`: `addPeriodicTimeObserver` called without capturing returned token.
- [x] Identified `NOTIFICATION_TOKEN_DISCARD`: `NotificationCenter.default.addObserver(forName:)` token discarded.
- [x] Identified `UNMANAGED_CF_LEAK`: `Unmanaged.passRetained` pointer allocation without matching release.
- [x] Recommended `WeakScriptMessageHandler`, token storage + `removeTimeObserver`, and pointer release.
