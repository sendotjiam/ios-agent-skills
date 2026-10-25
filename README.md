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
| **`swiftui-render-optimization`** | UI/UX & Render Performance | [`skills/swiftui-render-optimization`](./skills/swiftui-render-optimization) | Audits and optimizes SwiftUI view hierarchies for 120fps/60fps smoothness. Detects view graph invalidations, identity churn (structural vs explicit, AnyView), observation over-invalidation (@Observable vs ObservableObject), main-thread body computation, layout thrashing, and lifecycle anti-patterns. |
| **`ios-codebase-cleanup`** | Architecture & Maintenance | [`skills/ios-codebase-cleanup`](./skills/ios-codebase-cleanup) | Audits and safely purges dead Swift files, orphaned asset catalogs (`.imageset`, `.colorset`, `.appiconset`), dead documentation (`.md`, loose media), dead internal code symbols, and unused imports. Includes Xcode PBXProj synchronization and git tracking safety checkpoints. |
| **`ios-memory-leak-audit`** | Memory & ARC Diagnostics | [`skills/ios-memory-leak-audit`](./skills/ios-memory-leak-audit) | Audits codebases for ARC retain cycles (closures, delegates, Combine `assign(to:on:)`), target-action leaks (`Timer`, `CADisplayLink`), WebKit/AVFoundation observers, memory bloat (missing `@autoreleasepool`, raw image decoding, Core Data context bloat), GCD delays, and unmanaged CoreFoundation leaks. |
| **`coredata-swiftdata-audit`** | Persistence & Data Architecture | [`skills/coredata-swiftdata-audit`](./skills/coredata-swiftdata-audit) | Audits Core Data and SwiftData stacks for context concurrency hazards (`perform`/`performAndWait`), fault thrashing, batch delete/insert inefficiencies, CloudKit sync constraints, schema migration safety, and SQL query performance. |
| **`ios-a11y-audit`** | Accessibility & Assistive Tech | [`skills/ios-a11y-audit`](./skills/ios-a11y-audit) | Audits SwiftUI and UIKit view hierarchies for VoiceOver tree integrity (unlabelled buttons, grouping, rotors), Dynamic Type text clipping, `@ScaledMetric`, 44x44pt tap target minimums, WCAG 2.1 AA/AAA color contrast, assistive traits, sensory adaptations (Reduce Motion, Reduce Transparency, Differentiate Without Color), Smart Invert, and Xcode 15+ automated tests (`performAccessibilityAudit`). |

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
ln -s ~/Documents/ios-skills/skills/swiftui-render-optimization ~/.agents/skills/swiftui-render-optimization
ln -s ~/Documents/ios-skills/skills/ios-codebase-cleanup ~/.agents/skills/ios-codebase-cleanup
ln -s ~/Documents/ios-skills/skills/ios-memory-leak-audit ~/.agents/skills/ios-memory-leak-audit
ln -s ~/Documents/ios-skills/skills/coredata-swiftdata-audit ~/.agents/skills/coredata-swiftdata-audit
ln -s ~/Documents/ios-skills/skills/ios-a11y-audit ~/.agents/skills/ios-a11y-audit

# 3. Synchronize across Antigravity, Claude Code, and Codex
~/.agents/sync-skills.sh
```

### Option 2: Claude Code Direct
```bash
ln -s ~/Documents/ios-skills/skills/ios-concurrency-audit ~/.claude/skills/ios-concurrency-audit
ln -s ~/Documents/ios-skills/skills/swiftui-render-optimization ~/.claude/skills/swiftui-render-optimization
ln -s ~/Documents/ios-skills/skills/ios-codebase-cleanup ~/.claude/skills/ios-codebase-cleanup
ln -s ~/Documents/ios-skills/skills/ios-memory-leak-audit ~/.claude/skills/ios-memory-leak-audit
ln -s ~/Documents/ios-skills/skills/coredata-swiftdata-audit ~/.claude/skills/coredata-swiftdata-audit
ln -s ~/Documents/ios-skills/skills/ios-a11y-audit ~/.claude/skills/ios-a11y-audit
```

### Option 3: Codex Direct
```bash
ln -s ~/Documents/ios-skills/skills/ios-concurrency-audit ~/.codex/skills/ios-concurrency-audit
ln -s ~/Documents/ios-skills/skills/swiftui-render-optimization ~/.codex/skills/swiftui-render-optimization
ln -s ~/Documents/ios-skills/skills/ios-codebase-cleanup ~/.codex/skills/ios-codebase-cleanup
ln -s ~/Documents/ios-skills/skills/ios-memory-leak-audit ~/.codex/skills/ios-memory-leak-audit
ln -s ~/Documents/ios-skills/skills/coredata-swiftdata-audit ~/.codex/skills/coredata-swiftdata-audit
ln -s ~/Documents/ios-skills/skills/ios-a11y-audit ~/.codex/skills/ios-a11y-audit
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

## 🔍 Skill Spotlight: `swiftui-render-optimization`

### 1. Automated CLI Fast-Scanner (`scan_swiftui_renders.py`)
Quickly scan SwiftUI views across your project for render bottlenecks, heavy allocations, and lifecycle leaks:

```bash
# Output formatted table
python3 skills/swiftui-render-optimization/scripts/scan_swiftui_renders.py /path/to/ios/project

# Or export structured Markdown for pull request reviews
python3 skills/swiftui-render-optimization/scripts/scan_swiftui_renders.py /path/to/ios/project --format markdown -o render_scan.md
```

### 2. Severity Taxonomy
- **Critical (View Graph Loops / Invalidation)**: Inline `@ObservedObject var vm = ViewModel()` allocations, mutating state inside `body`, `@State(initialValue:)` in `init()` desynchronization, and volatile `UUID()` keys in `ForEach`.
- **High (Over-Invalidation / Body Bottlenecks)**: `DateFormatter()`, `JSONDecoder()`, or array `.sorted()` / `.filter()` inside `body`, `AnyView` type erasure destroying render nodes, row-level `.sheet` modifiers in loops, and unstructured `Task` leaks in `.onAppear`.
- **Medium (Scroll Hitches / Layout Thrashing)**: Eager `VStack`/`HStack` in `ScrollView`, `GeometryReader` inside scrolling cells, and unscoped implicit `.animation()` calls without `value:`.
- **Low (Diagnostics & Cleanups)**: Leftover `Self._printChanges()` in release builds, and missing `@ObservationIgnored` on non-UI properties in `@Observable` classes.

### 3. Bundled Reference Guides & Eval Suite
- 📖 [Identity & View Graph Mechanics](./skills/swiftui-render-optimization/references/identity-and-viewgraph.md): Structural vs explicit identity, `AnyView` diffing traps, and `.equatable()` subviews.
- 🔄 [Observation & State Slicing](./skills/swiftui-render-optimization/references/observation-and-invalidation.md): iOS 17 `@Observable` macro vs Combine `ObservableObject`, and `@ObservationIgnored`.
- ⏱️ [View Lifecycle & State Flow](./skills/swiftui-render-optimization/references/lifecycle-and-state-flow.md): View `init()` vs view lifetime, `.task` vs `.onAppear`, and `.onChange` state loops.
- 📊 [Xcode Instruments Profiling Recipes](./skills/swiftui-render-optimization/references/instruments-profiling-recipes.md): SwiftUI View Body track, Core Animation commits, `Self._printChanges()`, and MetricKit hitch ratios.
- 🧪 [Evaluation Test Suite & Benchmark](./skills/swiftui-render-optimization/evals/benchmark.md): 4-scenario benchmark covering 13 anti-patterns with 100% detection rate.

---

## 🔍 Skill Spotlight: `ios-codebase-cleanup`

### 1. Automated CLI Fast-Scanner (`scan_codebase_cleanup.py`)
Quickly audit your codebase for dead files, orphaned assets, unlinked docs, and unused internal symbols in <2 seconds:

```bash
# Output formatted table (non-destructive dry-run)
python3 skills/ios-codebase-cleanup/scripts/scan_codebase_cleanup.py /path/to/ios/project

# Deep symbol & import audit across active files
python3 skills/ios-codebase-cleanup/scripts/scan_codebase_cleanup.py /path/to/ios/project --scope all

# Or export structured Markdown for pull request reviews
python3 skills/ios-codebase-cleanup/scripts/scan_codebase_cleanup.py /path/to/ios/project --format markdown -o cleanup_audit.md

# Safe interactive pruning (creates git branch + cleans PBXProj references)
python3 skills/ios-codebase-cleanup/scripts/scan_codebase_cleanup.py /path/to/ios/project --delete
```

### 2. Detection Taxonomy & Confidence Ratings
- **Dead Swift Files (🔴 High)**: Top-level classes, structs, enums, actors with 0 project-wide occurrences. Preserves `@main`, App Delegate, and `#Preview` / `PreviewProvider` blocks.
- **Dead Asset Catalogs (🔴 High)**: Scans `.xcassets` for orphaned `.imageset`, `.colorset`, `.appiconset`. Supports string literals (`"icon"`) and Xcode 15+ generated Swift symbols (`Image(.icon)`).
- **Orphan Docs & Loose Media (🟡 Medium)**: Scans unlinked markdown documents and unreferenced images outside `.xcassets`.
- **Dead Code Symbols (🔴 High)**: Scans inside active files for uncalled `private func` and unread `private let/var` declarations.
- **Unused Framework Imports (🟡 Medium)**: Identifies framework imports with no direct symbol or prefix usage (`CG*`, `SM*`, `UTType`).

### 3. Safety Guardrails & Xcode Integrity
- **Git Branch Checkpoint**: Enforces clean working tree and auto-creates `cleanup/ios-codebase-YYYYMMDD-HHMMSS` before touching disk.
- **PBXProj Synchronization**: Surgically strips deleted file UUIDs from `project.pbxproj` (`PBXBuildFile`, `PBXFileReference`) to prevent compiler "missing file" errors.
- **Preview Preservation**: Treats SwiftUI `#Preview` as active usage so design-time components are never accidentally deleted.

### 4. Bundled Reference Guides & Eval Suite
- 📖 [False-Positive Avoidance Rules](./skills/ios-codebase-cleanup/references/false-positive-rules.md): Guidance on `@objc` runtime reflection, DI frameworks (Factory, Swinject), string-interpolated asset names, and multi-target projects.
- 🔧 [Xcode PBXProj Safe Reference Removal](./skills/ios-codebase-cleanup/references/pbxproj-safe-removal.md): Deep dive into Xcode project structure and safe reference pruning commands.
- 🧪 [Evaluation Test Suite & Benchmark](./skills/ios-codebase-cleanup/evals/benchmark.md): 4-scenario benchmark with 100% pass rate in 3.8ms.

---

## 🔍 Skill Spotlight: `ios-memory-leak-audit`

### 1. Automated CLI Fast-Scanner (`scan_memory_leaks.py`)
Quickly audit your codebase for ARC retain cycles, memory bloat, and observer leaks in <1 second:

```bash
# Output formatted table
python3 skills/ios-memory-leak-audit/scripts/scan_memory_leaks.py /path/to/ios/project

# Or export structured Markdown for pull request reviews
python3 skills/ios-memory-leak-audit/scripts/scan_memory_leaks.py /path/to/ios/project --format markdown -o memory_leak_audit.md

# Machine-readable JSON output for CI pipelines
python3 skills/ios-memory-leak-audit/scripts/scan_memory_leaks.py /path/to/ios/project --format json
```

### 2. Detection Taxonomy & Severity Tiers
- **Critical (Permanent Retain Cycles & ARC Leaks)**: Strong delegate properties missing `weak`, Combine `assign(to:on: self)` retain cycles, `Timer.scheduledTimer` with strong `target: self`, `WKUserContentController.add(self)` WebKit leaks, and unbalanced `Unmanaged.passRetained` allocations.
- **High (Memory Bloat & JetSam / OOM Crash Risk)**: Batch loops processing `UIImage`, `CIImage`, or `Data` without `@autoreleasepool`, full-resolution image decoding without downsampling, unbounded `Dictionary` caches instead of `NSCache`, and Core Data batch loops without `context.reset()`.
- **Medium (Zombie Tasks & Subscription Leaks)**: Combine `.sink` without `[weak self]`, `NotificationCenter.default.addObserver` with discarded tokens, `AVPlayer.addPeriodicTimeObserver` without token tracking, `DispatchSourceTimer` event handler cycles, and delayed `asyncAfter` closures retaining `UIViewController`.
- **Low (Scope Hygiene)**: Redundant closure captures and over-scoped closures where non-escaping patterns suffice.

### 3. Bundled Reference Guides & Production Recipes
- 📖 [Retain Cycles, Closures & Concurrency](./skills/ios-memory-leak-audit/references/retain-cycles-and-closures.md): `[weak self]` vs `[unowned self]`, weak delegates, Combine pipelines, GCD delays, and detached Task retain traps.
- 🌊 [Memory Bloat, Autorelease Pools & JetSam](./skills/ios-memory-leak-audit/references/memory-bloat-and-autorelease.md): RunLoop mechanics, `@autoreleasepool` in loops, `CGImageSourceCreateThumbnailAtIndex` downsampling, and Core Data fault management.
- 🌐 [WebKit & System Observers](./skills/ios-memory-leak-audit/references/webkit-and-system-observers.md): `WeakScriptMessageHandler` proxy, `AVPlayer` periodic time observers, and `NotificationCenter` tokens.
- 🛠️ [Runtime Memory Profiling Recipes](./skills/ios-memory-leak-audit/references/instruments-memory-debugging.md): Xcode Memory Graph Debugger (`MallocStackLoggingNoCompact=1`), Instruments Allocations **Mark Generation**, and CLI `leaks`/`vmmap`.
- 🧪 [Automated CI Memory Leak Testing](./skills/ios-memory-leak-audit/references/automated-leak-testing.md): Drop-in `XCTestCase.trackForMemoryLeaks` helper and modern Swift 6 `Testing` deallocation assertions.
- 📊 [Evaluation Test Suite & Benchmark](./skills/ios-memory-leak-audit/evals/benchmark.md): 4-scenario benchmark covering 13 memory hazard signatures with 100% detection rate in 4.02ms.

---

## 🔍 Skill Spotlight: `coredata-swiftdata-audit`

### 1. Automated CLI Fast-Scanner (`scan_coredata_swiftdata.py`)
Audit your persistence layer for context concurrency hazards, fault thrashing, and CloudKit sync violations in <5ms:

```bash
# Output formatted colored table
python3 skills/coredata-swiftdata-audit/scripts/scan_coredata_swiftdata.py /path/to/ios/project

# Export structured Markdown report for pull requests or reviews
python3 skills/coredata-swiftdata-audit/scripts/scan_coredata_swiftdata.py /path/to/ios/project --format markdown -o persistence_audit.md

# Machine-readable JSON output for CI quality gates
python3 skills/coredata-swiftdata-audit/scripts/scan_coredata_swiftdata.py /path/to/ios/project --format json
```

### 2. Detection Taxonomy & Severity Tiers
- **🔴 Critical (Concurrency Violations & CloudKit Sync Failure)**: Context operations outside `perform`/`performAndWait`, raw model passing across `Task` or actor boundaries, unisolated `ModelContext` initialization, `mainContext` misuse in background tasks, CloudKit relationships missing reciprocal `inverse:`, and `@Attribute(.unique)` on CloudKit-synced models.
- **🟠 High (Batch Inefficiency & Memory Bloat)**: Deleting records in loops instead of `NSBatchDeleteRequest` / SwiftData 18 `delete(model:where:)`, bulk ingestion loops saving without `@autoreleasepool` and `context.reset()`, missing `automaticallyMergesChangesFromParent = true`, and inline binary `Data` > 1MB.
- **🟡 Medium (Fault Thrashing & Reactive View Churn)**: Nested relationship traversal in loops without `relationshipKeyPathsForPrefetching`, `NSFetchRequest` lacking `fetchBatchSize`, dynamic `@Query` predicates bound to text input without debouncing, and `@Model` UI state lacking `@Transient`.
- **🔵 Low (Store Hygiene & Startup Latency)**: Synchronous `loadPersistentStores` blocking app launch on main thread, disk-backed `ModelContainer` leaks in `#Preview`, and unversioned schema modifications.

### 3. Bundled Reference Guides & Production Recipes
- 📖 [Concurrency, Thread Confinement & @ModelActor](./skills/coredata-swiftdata-audit/references/concurrency-and-modelactor.md): Queue confinement vs `@ModelActor`, thread-safe `NSManagedObjectID` and `PersistentIdentifier` passing, and `-com.apple.CoreData.ConcurrencyDebug 1`.
- ⚡ [Fault Thrashing, Prefetching & N+1 Queries](./skills/coredata-swiftdata-audit/references/fault-thrashing-and-prefetching.md): Fault mechanics, `relationshipKeyPathsForPrefetching`, `fetchBatchSize` tuning (2x-3x visible rows), and DTO projections.
- 📦 [Batch Operations & Memory Reclamation](./skills/coredata-swiftdata-audit/references/batch-operations-and-memory.md): `NSBatchDeleteRequest`, `NSBatchInsertRequest`, SwiftData 18 batch operations, chunked imports with `context.reset()`.
- ☁️ [CloudKit Sync Constraints & Multi-Context Sync](./skills/coredata-swiftdata-audit/references/cloudkit-sync-and-multi-context.md): Mandatory inverses, unique constraint prohibitions, optional attributes with defaults, and `automaticallyMergesChangesFromParent`.
- 🔄 [Migration Safety & SchemaMigrationPlans](./skills/coredata-swiftdata-audit/references/migration-safety-and-schemaplans.md): Lightweight vs custom migrations, `VersionedSchema`, `MigrationStage` chains, and asynchronous store loading to avoid `0x8badf00d` watchdog kills.
- 🛠️ [Instruments & SQL Tracing Diagnostics](./skills/coredata-swiftdata-audit/references/instruments-and-sql-tracing.md): `-com.apple.CoreData.SQLDebug 3` interpretation, Xcode Instruments Core Data template (Faults/Fetches/Saves), and SQLite WAL runaway prevention.
- 🧪 [Evaluation Test Suite & Benchmark](./skills/coredata-swiftdata-audit/evals/benchmark.md): 4-scenario benchmark covering 17 persistence rules with 100% detection rate in 4.55ms.

---

## 🔍 Skill Spotlight: `ios-a11y-audit`

### 1. Automated CLI Fast-Scanner (`scan_a11y.py`)
Audit your SwiftUI and UIKit view hierarchies for accessibility non-compliance, VoiceOver blockers, and Dynamic Type clipping in <5ms:

```bash
# Output formatted colored table
python3 skills/ios-a11y-audit/scripts/scan_a11y.py /path/to/ios/project

# Export structured Markdown report for pull requests or reviews
python3 skills/ios-a11y-audit/scripts/scan_a11y.py /path/to/ios/project --format markdown -o a11y_report.md

# Machine-readable JSON output for CI quality gates
python3 skills/ios-a11y-audit/scripts/scan_a11y.py /path/to/ios/project --format json
```

### 2. Detection Taxonomy & Severity Tiers
- **🔴 Critical (Screen Reader Blockers & Text Clipping)**: Unlabelled icon buttons (`Image(systemName:)` with zero label), rigid `.frame(height: N)` text containers clipping at AX font sizes, sub-30pt tap targets, severe contrast failures ($< 3.0:1$), and gesture-only traps lacking accessible actions.
- **🟠 High (Navigation Hazards & Structural Impediments)**: Looping `.repeatForever()` animations ignoring `accessibilityReduceMotion`, translucent `.ultraThinMaterial` backgrounds lacking `accessibilityReduceTransparency` fallbacks, red/green status indicators violating Differentiate Without Color, custom views with `.onTapGesture` missing `.accessibilityAddTraits(.isButton)`, horizontal stacks refusing to wrap at AX sizes, and sub-44pt touch targets.
- **🟡 Medium (Suboptimal Experience & Sensory Gaps)**: Fixed `CGFloat` layout properties missing `@ScaledMetric`, photo/video components missing `accessibilityIgnoresInvertColors(true)` under Smart Invert, Swift Charts lacking `AXChartDescriptor` audio graphs, and hardcoded RGB colors risking contrast failures in Dark Mode.
- **🔵 Low (Hygiene & Polish)**: Redundant trait words in accessibility labels (e.g. `"Dismiss button"` causing VoiceOver to announce *"Dismiss button, button"*), and fragmented element reading order.

### 3. Bundled Reference Guides & Production Recipes
- 🗣️ [VoiceOver Tree, Rotors & Traits](./skills/ios-a11y-audit/references/voiceover-tree-and-rotors.md): Semantic element grouping (`.accessibilityElement(children: .combine)`), custom rotors, discrete custom actions, Voice Control (`accessibilityInputLabels`), and assistive traits.
- 🔠 [Dynamic Type, @ScaledMetric & AX Layouts](./skills/ios-a11y-audit/references/dynamic-type-and-scaled-metric.md): `@ScaledMetric(relativeTo:)`, eliminating fixed-height clipping, layout adaptation with `ViewThatFits` and `dynamicTypeSize`, and UIKit `UIFontMetrics`.
- 🎯 [Hit Targets & Touch Handling](./skills/ios-a11y-audit/references/hit-targets-and-touch-handling.md): $44\times 44\text{pt}$ Apple HIG & WCAG 2.5.5 minimums, `.contentShape(Rectangle())` touch expansion, UIKit `touchAreaInsets`, and motor accessibility.
- 🎨 [WCAG Contrast & Color Independence](./skills/ios-a11y-audit/references/wcag-contrast-and-color.md): WCAG 2.1 AA/AAA contrast ratios ($4.5:1$ / $3:1$), dynamic semantic system colors, `accessibilityContrast` High Contrast mode, and Differentiate Without Color.
- 🧘 [Sensory Adaptations: Motion, Materials & Smart Invert](./skills/ios-a11y-audit/references/sensory-motion-and-materials.md): Vestibular protection via `accessibilityReduceMotion`, solid fallbacks for `accessibilityReduceTransparency`, and Smart Invert protection via `accessibilityIgnoresInvertColors`.
- 📊 [Automated Testing & Swift Charts Audio Graphs](./skills/ios-a11y-audit/references/automated-a11y-testing-and-charts.md): Xcode 15+ `performAccessibilityAudit(for: [...])`, Swift Charts `AXChartDescriptor` data sonification, preview matrices, and CI/CD GitHub Actions.
- 🧪 [Evaluation Test Suite & Benchmark](./skills/ios-a11y-audit/evals/benchmark.md): 3-scenario evaluation suite covering 13 accessibility rules with 100% detection rate and 0% false positives in 4.1ms.

---

## 🗺️ Roadmap & Planned Skills

- [x] `ios-concurrency-audit`: Hangs $\ge 250\text{ms}$, actor reentrancy, data races, deadlocks, Swift 6 strict concurrency.
- [x] `swiftui-render-optimization`: Identity churn, view graph invalidations, EquatableView conformance, body re-evaluations.
- [x] `ios-codebase-cleanup`: Dead files, orphaned `.xcassets`, unlinked docs, dead internal symbols, PBXProj sync.
- [x] `ios-memory-leak-audit`: Retain cycles, closure capture lists, autorelease pool exhaustion, CoreFoundation leaks.
- [x] `coredata-swiftdata-audit`: Context concurrency violations, fault thrashing, migration safety, batching, CloudKit sync.
- [x] `ios-a11y-audit`: VoiceOver accessibility elements, Dynamic Type scaling, contrast ratios, assistive traits, sensory adaptations, Smart Invert.

---

## 📄 License

MIT License. Free to use, fork, and contribute!
