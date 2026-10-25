---
name: ios-concurrency-audit
description: Comprehensive iOS concurrency and main-thread performance auditor. Scans iOS/macOS codebases for severe hangs (250ms or greater), mini-hangs/hitches (16-250ms), main-thread blocking calls, actor reentrancy hazards, data races, deadlocks, and cooperative thread pool starvation across Swift Concurrency and GCD. Use whenever auditing iOS apps for performance or concurrency, diagnosing UI freezes or frame drops, reviewing Swift 6 migration safety, inspecting View/ViewModel threading, or analyzing Instruments/TSan reports.
---

# iOS Concurrency & Hang Audit Guide

This skill guides deep static and diagnostic audits of iOS/macOS codebases to detect concurrency hazards, data races, deadlocks, and main-thread execution stalls (hangs and mini-hangs).

---

## 1. Audit Taxonomy & Severity Tiers

When inspecting code or profiling data, classify all findings into four severity tiers:

### Critical (Hang >= 250ms or App Freeze / Deadlock)
- **Deadlock**: Calling `DispatchQueue.main.sync` from the main thread, or synchronous blocking (`DispatchSemaphore.wait`, `DispatchGroup.wait`, `NSLock.lock`) inside a cooperative Swift `Task` waiting on work dispatched back to the caller.
- **Main-Thread I/O Block**: Synchronous disk reading (`Data(contentsOf: fileURL)`), synchronous network requests, or synchronous SQLite/CoreData fetches executed directly on the main thread or inside `@MainActor`.
- **System Watchdog Kill Risk**: Any synchronous blocking sequence during application launch (`didFinishLaunchingWithOptions`) or view appearance exceeding 250ms (risking `0x8badf00d` termination).

### High (Mini-Hang 100–250ms or Actor Reentrancy / Data Race)
- **Actor Reentrancy Invariant Hazard**: State validated before an `await` suspension point that is mutated before the continuation resumes, causing duplicate actions, inconsistent local caches, or double-payments.
- **Micro-Hangs during Transitions**: Heavy synchronous work (`JSONDecoder.decode`, cryptographic hashing, complex regex compilation) executed inside `@MainActor` or view lifecycle (`viewDidLoad`, `viewWillAppear`, SwiftUI `.task` without background hop).
- **Unsynchronized Mutable Shared State**: Non-`Sendable` mutable class instances or pointers passed across task boundaries or background queues without mutual exclusion.

### Medium (Hitch / Scroll Stutter 16.6ms – 100ms)
- **Main-Thread Image Decoding**: Assigning raw image data directly to `UIImageView` or SwiftUI `Image` without prior off-main decompression (`preparingForDisplay()` or `preparingThumbnail(of:)`).
- **Expensive Allocations in Hot Paths**: Instantiating `DateFormatter`, `ISO8601DateFormatter`, `NumberFormatter`, or compiling `NSRegularExpression` inside cell rendering (`cellForRowAt`, SwiftUI `List` / `ForEach` body).
- **Core Data Main Context Thrash**: Running unbounded or non-faulting fetches on `viewContext` while scrolling.

### Low (Inefficiency / Anti-Pattern)
- **Unstructured Fire-and-Forget**: Spawning `Task { ... }` in SwiftUI views without cancellation handling or view lifecycle detachment.
- **Unnecessary Main-Thread Hops**: Repeatedly jumping between background queues and `@MainActor` in a tight processing loop.

---

## 2. Screen & Component Audit Protocol

Perform the audit systematically from the UI layer down to data/network services:

```
[UI View / Screen] -> [ViewModel / Presenter] -> [Domain / Use Case] -> [Data Repository / Client]
  (Lifecycle/Events)       (@MainActor isolation)    (Actors / Concurrency)       (I/O & Background work)
```

### Step 1: Scan View & Lifecycle Entry Points
Inspect all user-facing views:
- **SwiftUI**: `body`, `.task`, `.onAppear`, `.onChange`, button actions, sheet/navigation transitions.
- **UIKit**: `viewDidLoad`, `viewWillAppear`, `viewDidLayoutSubviews`, `tableView(_:cellForRowAt:)`, `collectionView(_:cellForItemAt:)`, gesture handlers.

**Check for**:
- Are heavy initializations running synchronously in `init` or `viewDidLoad`?
- Does SwiftUI `body` contain expensive computation, database queries, or string parsing?
- Is `.task` being cancelled when the view disappears, or is `Task.detached` leaking work?

### Step 2: Audit ViewModel Isolation & Boundaries
- Verify if the `ObservableObject` or `@Observable` class is marked `@MainActor`.
- Check if background asynchronous tasks jump back to `@MainActor` before updating published state.
- Inspect whether heavy transformations (filtering 10,000 items, JSON parsing) are executed on `@MainActor` or offloaded using non-isolated functions or `Task.detached`.

### Step 3: Inspect Service Layer & Shared State
- **Actors**: Check methods with multiple `await` calls. Do properties get verified before an `await` and modified after? (See `references/concurrency-anti-patterns.md`).
- **GCD Interop**: Search for `DispatchSemaphore`, `pthread_mutex`, `os_unfair_lock`, or `DispatchQueue.sync` inside async contexts.
- **Thread Pool Starvation**: Ensure long synchronous loops or blocking waits (`sleep()`) are not occupying Swift Concurrency cooperative worker threads.

---

## 3. Reporting Structure

Format all audit results screen-by-screen, ordering findings by severity:

````markdown
# Concurrency & Performance Audit Report: [Module / App Name]

## Executive Summary
- **Screens Audited**: [List of Screens / ViewControllers]
- **Critical Hangs / Deadlocks Found**: [Count]
- **Mini-Hangs / Hitches Detected**: [Count]
- **Data Races & Actor Hazards**: [Count]

---

## Screen: [ScreenName] (`[FilePath]`)

### 1. [[SEVERITY]] [Concise Hazard Title]
- **Location**: `[FilePath]:[LineNumber]` in `[Function/Method]`
- **Hazard Type**: [Main Thread Hang | Mini-Hang | Actor Reentrancy | Data Race | Thread Starvation]
- **Mechanism**: Explain exactly why this hangs or races (e.g., synchronous disk read on main thread during scroll).
- **Estimated Stall**: [e.g., ~150ms-400ms on real devices / infinite deadlock]
- **Remediation**:
```swift
// BEFORE (Vulnerable / Blocking)
[Vulnerable code snippet]

// AFTER (Fixed & Idiomatic)
[Corrected surgical diff]
```

---

## Runtime Verification Plan
Instructions for verifying with Instruments, TSan, or MetricKit (see `references/hangs-and-profiling.md`).
````

---

## 4. Key Patterns Quick-Reference

### A. Preventing Mini-Hangs from Image Decompression
```swift
// AVOID: Decompresses on main thread during layout/render
let image = UIImage(data: rawData)
self.imageView.image = image

// PREFERRED: Background decode before main thread assignment
let decodedImage = await Task.detached(priority: .userInitiated) {
    let raw = UIImage(data: rawData)
    return raw?.preparingForDisplay()
}.value
self.imageView.image = decodedImage
```

### B. Eliminating Actor Reentrancy Race Conditions
```swift
// AVOID: State changes across await boundary
actor BalanceManager {
    var balance: Decimal = 100
    func withdraw(amount: Decimal) async -> Bool {
        guard balance >= amount else { return false }
        // SUSPENSION POINT: Another caller can withdraw here!
        await paymentGateway.charge(amount)
        balance -= amount // Overdraw hazard!
        return true
    }
}

// PREFERRED: Reserve/lock state before suspending
actor BalanceManager {
    var balance: Decimal = 100
    func withdraw(amount: Decimal) async -> Bool {
        guard balance >= amount else { return false }
        balance -= amount // Deduct immediately or set to pending
        do {
            try await paymentGateway.charge(amount)
            return true
        } catch {
            balance += amount // Revert on failure
            return false
        }
    }
}
```

### C. Cooperative Thread Starvation & Semaphore Deadlock
```swift
// CRITICAL FAULT: Blocking cooperative pool thread
func fetchSynchronously() async -> Data {
    let semaphore = DispatchSemaphore(value: 0) // NEVER wait in async context
    var result: Data?
    DispatchQueue.global().async {
        result = loadData()
        semaphore.signal()
    }
    semaphore.wait() // DEADLOCK / STARVATION HAZARD!
    return result!
}

// PREFERRED: Use withCheckedContinuation
func fetchSafely() async -> Data {
    await withCheckedContinuation { continuation in
        DispatchQueue.global().async {
            let result = loadData()
            continuation.resume(returning: result)
        }
    }
}
```

---

## 5. Supplementary Resources

- For deep catalog of concurrency traps and anti-patterns, read [concurrency-anti-patterns.md](file:///Users/sendotjiamis/.agents/skills/ios-concurrency-audit/references/concurrency-anti-patterns.md).
- For step-by-step Instruments, TSan, and MetricKit recipes, read [hangs-and-profiling.md](file:///Users/sendotjiamis/.agents/skills/ios-concurrency-audit/references/hangs-and-profiling.md).
