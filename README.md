# iOS Agent Skills (`ios-skills`)

<p align="center">
  <img src="https://img.shields.io/badge/Swift-6.0%2B-F05138?logo=swift&logoColor=white" alt="Swift 6" />
  <img src="https://img.shields.io/badge/iOS-15.0%2B-000000?logo=apple&logoColor=white" alt="iOS 15+" />
  <img src="https://img.shields.io/badge/Ecosystem-Antigravity%20%7C%20Claude%20Code%20%7C%20Codex-6366F1" alt="Agents" />
  <img src="https://img.shields.io/badge/Eval%20Suite-100%25%20Pass%20Rate-10B981" alt="Eval Pass Rate" />
  <img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="MIT License" />
</p>

A curated collection of production-grade agentic AI skills for iOS, iPadOS, macOS, and watchOS engineering. Designed to run seamlessly across **Google Antigravity**, **Anthropic Claude Code**, and **OpenAI Codex**.

---

## 📦 Available Skills

| Skill | Category | Directory | Description |
| :--- | :--- | :--- | :--- |
| **`ios-concurrency-audit`** | Performance & Concurrency | [`skills/ios-concurrency-audit`](./skills/ios-concurrency-audit) | Audits codebases for severe hangs ($\ge 250\text{ms}$), mini-hangs/hitches ($16-250\text{ms}$), main-thread blocking calls, actor reentrancy hazards, data races, deadlocks, Swift 6 unsafety, and cooperative thread pool starvation across Swift Concurrency and GCD. |

---

## ⚡ Architecture & Audit Flow

```
┌─────────────────────────────────┐
│  CLI Fast-Scanner               │  python3 scan_concurrency.py /path/to/project
│  (Zero-Dependency Python 3)    │  Scans 1,000+ files in <1 second for red flags
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│  AI Call-Flow & AST Audit       │  Screen-first analysis: View -> ViewModel -> Service
│  (ios-concurrency-audit)        │  Traces execution down to background & actor boundaries
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│  Triage Report & Surgical Diffs │  Classifies findings into Critical, High, Medium, Low
│  (Screen-by-Screen Output)      │  Provides verified BEFORE / AFTER modern Swift refactors
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│  Empirical Runtime Verification │  Xcode Instruments (Time Profiler / Hangs track),
│  (Profiling Runbooks)           │  Thread Sanitizer (TSan), & MetricKit MXHangDiagnostic
└─────────────────────────────────┘
```

---

## 🚀 Quick Setup & Installation

### Option 1: Unified Agent Hub (`~/.agents/skills`)
Recommended if you use a centralized skills repository shared across assistants:

```bash
# 1. Clone the repository
git clone https://github.com/sendotjiam/ios-skills.git ~/Documents/ios-skills

# 2. Symlink skills into your agent hub
ln -s ~/Documents/ios-skills/skills/ios-concurrency-audit ~/.agents/skills/ios-concurrency-audit

# 3. Synchronize across Antigravity, Claude Code, and Codex
~/.agents/sync-skills.sh
```

### Option 2: Claude Code Direct
```bash
ln -s ~/Documents/ios-skills/skills/ios-concurrency-audit ~/.claude/skills/ios-concurrency-audit
```

### Option 3: Codex Direct
```bash
ln -s ~/Documents/ios-skills/skills/ios-concurrency-audit ~/.codex/skills/ios-concurrency-audit
```

---

## 🔍 Skill Spotlight: `ios-concurrency-audit`

### 1. Automated CLI Fast-Scanner
Run the bundled pre-scanner to instantly surface concurrency hot spots across your Xcode workspace:

```bash
# Output formatted table
python3 skills/ios-concurrency-audit/scripts/scan_concurrency.py /path/to/ios/project

# Or export structured Markdown for pull request reviews
python3 skills/ios-concurrency-audit/scripts/scan_concurrency.py /path/to/ios/project --format markdown -o scan_report.md
```

### 2. Severity Taxonomy
- **Critical (Hangs $\ge 250\text{ms}$ / Deadlocks)**: Synchronous I/O on main thread (`Data(contentsOf:)`), `DispatchQueue.main.sync`, semaphore waits in `Task`, and watchdog termination risks (`0x8badf00d`).
- **High (Mini-Hangs $100-250\text{ms}$ / Races / Swift 6)**: Actor reentrancy state mutations across `await`, `@unchecked Sendable` escapes concealing mutable state, `MainActor.assumeIsolated` crashes, and Core Data (`NSManagedObject`) / SwiftData (`@Model`) crossing actor boundaries.
- **Medium (Scroll Hitches $16.6-100\text{ms}$ / Task Leaks)**: Main-thread image decompression without `preparingForDisplay()`, repeated `DateFormatter` instantiations in cell render loops, and strong `[self]` retain cycles in infinite `AsyncSequence` iterators.
- **Low (Inefficiency)**: Unstructured fire-and-forget tasks without cancellation, and redundant `.receive(on: .main)` actor hops.

### 3. Bundled Reference Guides
- 📖 [Concurrency Anti-Patterns Catalog](./skills/ios-concurrency-audit/references/concurrency-anti-patterns.md): Concrete before/after diffs for actor reentrancy deduplication, Core Data / SwiftData actor boundaries, Task cancellation, and Combine bridges.
- ⏱️ [Hangs & Concurrency Profiling Recipes](./skills/ios-concurrency-audit/references/hangs-and-profiling.md): Step-by-step recipes for Xcode Time Profiler, Hangs track, Swift Concurrency Visualizer, TSan, and MetricKit.
- 📊 [Benchmark Evaluation Report](./skills/ios-concurrency-audit/evals/benchmark.md): Verified against multi-scenario test suites with 100% pass rates.

---

## 🗺️ Roadmap & Planned Skills

- [ ] `ios-memory-leak-audit`: Retain cycles, closure capture lists, autorelease pool exhaustion, CoreFoundation leaks.
- [ ] `swiftui-render-optimization`: Identity churn, view graph invalidations, EquatableView conformance, body re-evaluations.
- [ ] `coredata-swiftdata-audit`: Context concurrency violations, fault thrashing, migration safety, batching.
- [ ] `ios-a11y-audit`: VoiceOver accessibility elements, Dynamic Type scaling, contrast ratios, assistive traits.

---

## 📄 License

MIT License. Free to use, fork, and contribute!
