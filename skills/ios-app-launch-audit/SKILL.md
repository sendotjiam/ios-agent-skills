---
name: ios-app-launch-audit
description: Audits iOS, iPadOS, macOS, and watchOS projects for cold and warm app launch bottlenecks (<400ms MetricKit budget), main-thread blocking I/O and synchronous store loading during didFinishLaunching, third-party SDK init pileups, and Objective-C +load pre-main overhead.
---

# `ios-app-launch-audit`

## Purpose
A specialized performance auditor for Apple platforms focused on optimizing cold and warm startup latency. Helps engineering teams keep app startup within Apple's recommended **$<400\text{ms}$ time-to-first-draw budget** and prevents `0x8badf00d` watchdog crash terminations.

---

## ⚡ Fast-Scanner CLI

```bash
# Terminal table output
python3 skills/ios-app-launch-audit/scripts/scan_app_launch.py /path/to/project

# Xcode Issue Navigator inline format
python3 skills/ios-app-launch-audit/scripts/scan_app_launch.py /path/to/project --format xcode

# Machine-readable JSON output
python3 skills/ios-app-launch-audit/scripts/scan_app_launch.py /path/to/project --format json
```

---

## 🛑 Detection Taxonomy & Severity Tiers

| Severity | Rule ID | Category | Detection Target |
| :--- | :--- | :--- | :--- |
| **Critical** | `LAUNCH_SYNC_PERSISTENCE_LOAD` | Persistence Concurrency | Synchronous `loadPersistentStores` in `didFinishLaunching` or `@main` `init()`. |
| **Critical** | `LAUNCH_BLOCKING_FILE_IO` | Main-Thread I/O | Synchronous `Data(contentsOf:)` or heavy JSON decoding on launch. |
| **High** | `LAUNCH_SDK_INIT_*` | SDK Overhead | Synchronous third-party SDK initializations (`FirebaseApp.configure()`, `SentrySDK.start()`). |
| **High** | `LAUNCH_OBJC_PLUS_LOAD` | Pre-Main dyld | Objective-C `+ (void)load` methods executed before `main()` during image loading. |
| **Medium** | `LAUNCH_OBSOLETE_USERDEFAULTS_SYNC` | Disk Overhead | Synchronous `UserDefaults.standard.synchronize()` disk flush calls on startup. |
| **Medium** | `LAUNCH_HEAVY_STATIC_INIT` | Global Statics | Top-level global properties initialized with synchronous file or image loading. |

---

## 📖 Bundled References & Recipes
- [MetricKit Launch Metrics & Budgets](./references/metrickit-and-launch-budgets.md)
- [Non-Blocking Splash & Asynchronous Bootstrap Architecture](./references/non-blocking-splash-bootstrap.md)
- [Benchmark Evaluation Report](./evals/benchmark.md)
