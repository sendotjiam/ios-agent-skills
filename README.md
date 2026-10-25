# iOS Agent Skills (`ios-skills`)

A curated collection of production-grade agentic AI skills for iOS, iPadOS, macOS, and watchOS engineering. Designed to run across **Antigravity**, **Claude Code**, and **OpenAI Codex**.

---

## 📦 Available Skills

| Skill | Directory | Description |
| :--- | :--- | :--- |
| **`ios-concurrency-audit`** | [`skills/ios-concurrency-audit`](./skills/ios-concurrency-audit) | Audits codebases for severe hangs ($\ge 250\text{ms}$), mini-hangs/hitches ($16-250\text{ms}$), main-thread blocking calls, actor reentrancy hazards, data races, deadlocks, Swift 6 unsafety, and cooperative thread pool starvation across Swift Concurrency and GCD. |

---

## 🚀 Quick Setup & Installation

### Option 1: Unified Agent Hub (`~/.agents/skills`)
If using the cross-assistant unified skills hub:

```bash
# Clone the repository
git clone https://github.com/sendotjiam/ios-skills.git ~/Documents/ios-skills

# Symlink skills into your hub
ln -s ~/Documents/ios-skills/skills/ios-concurrency-audit ~/.agents/skills/ios-concurrency-audit

# Sync across Antigravity, Claude Code, and Codex
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

### Capabilities
- **Automated CLI Fast-Scanner (`scan_concurrency.py`)**: Zero-dependency Python CLI tool to scan any Xcode repository in seconds before conducting deep LLM-guided audits:
  ```bash
  python3 skills/ios-concurrency-audit/scripts/scan_concurrency.py /path/to/ios/project --format markdown
  ```
- **Screen-First Triage**: Inspects execution flow from UI lifecycle (`body`, `viewDidLoad`, `cellForRowAt`) down to ViewModel and Service layers.
- **Severity Classification**:
  - **Critical**: Severe hangs ($\ge 250\text{ms}$), deadlocks (`main.sync`, semaphore waits in `Task`), system watchdog kills (`0x8badf00d`).
  - **High**: Mini-hangs ($100-250\text{ms}$), actor reentrancy invariant violations across `await`, Swift 6 `@unchecked Sendable` escapes, `MainActor.assumeIsolated` crashes, Core Data / SwiftData isolation breaches.
  - **Medium**: Scroll hitches / frame drops ($16.6-100\text{ms}$), main-thread image decoding, heavy formatters/regex in cell loops, Task retain cycle leaks.
  - **Low**: Unstructured `Task` leaks without cancellation, redundant `.receive(on: .main)` actor hops.
- **Empirical Profiling Recipes**: Actionable instructions for Xcode Instruments (Time Profiler, Hangs track, Swift Concurrency Visualizer), Thread Sanitizer (TSan), and MetricKit `MXHangDiagnostic`.

---

## 🗺️ Roadmap & Planned Skills

- [ ] `ios-memory-leak-audit`: Retain cycles, closure capture lists, autorelease pool exhaustion, CoreFoundation leaks.
- [ ] `swiftui-render-optimization`: Identity churn, view graph invalidations, EquatableView conformance, body re-evaluations.
- [ ] `coredata-swiftdata-audit`: Context concurrency violations, fault thrashing, migration safety, batching.
- [ ] `ios-a11y-audit`: VoiceOver accessibility elements, Dynamic Type scaling, contrast ratios, assistive traits.

---

## 📄 License

MIT License. Feel free to use and contribute!
