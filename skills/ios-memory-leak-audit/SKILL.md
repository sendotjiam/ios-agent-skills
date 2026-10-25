---
name: ios-memory-leak-audit
description: Comprehensive iOS memory leak, retain cycle, and ARC auditor. Scans iOS/macOS codebases for strong reference cycles in closures, delegates, Combine pipelines (assign(to:on:), .sink), GCD (asyncAfter, DispatchSourceTimer), NotificationCenter tokens, Timer target:self, WKWebView script message handlers, memory bloat (missing @autoreleasepool, raw image decoding, Core Data context bloat), CoreFoundation/Unmanaged leaks, and detached Task cycles. Use whenever auditing iOS apps for memory leaks, diagnosing JetSam/OOM crashes, inspecting retain cycles, reviewing dealloc/deinit issues, or analyzing Xcode Memory Graph and Instruments Allocations/Leaks reports.
---

# iOS Memory Leak & Retain Cycle Audit Guide

This skill guides deep static and diagnostic audits of iOS, iPadOS, and macOS codebases to detect permanent memory leaks (retain cycles, unmanaged CoreFoundation allocations) and transient memory bloat (missing `@autoreleasepool`, un-downsampled bitmaps, Core Data context fault retention) that trigger system JetSam / Out-Of-Memory (OOM) kills.

---

## 1. Audit Taxonomy & Severity Tiers

When inspecting code or profiling diagnostic graphs, classify all findings into four severity tiers:

### 🔴 Critical (Permanent Retain Cycle / Unbounded Memory Leak)
- **Closure Retain Cycles**: Storing an escaping closure as a property on an object where the closure captures `self` strongly (omitting `[weak self]`).
- **Strong Delegate References**: Declaring delegate properties without `weak` (`var delegate: SomeDelegate?`), forming a bidirectional reference cycle between parent and child/coordinator.
- **Target-Action RunLoop Cycles**: Initializing repeating `Timer.scheduledTimer(withTimeInterval:target:self,...)` or `CADisplayLink(target: self, ...)` where the RunLoop strongly retains the target, preventing `deinit`.
- **Combine `assign(to:on:)` Retain Cycle**: Using `assign(to: \.property, on: self)` in Combine. Apple explicitly documents that this captures `self` strongly and creates a permanent retain cycle (fixed with `assign(to: &$prop)` or `.sink [weak self]`).
- **WebKit Script Message Handler Leak**: Registering `userContentController.add(self, name: "...")` where `WKUserContentController` retains the handler strongly, permanently leaking the `UIViewController`.
- **Unbalanced Unmanaged / CoreFoundation Allocations**: Calling `Unmanaged.passRetained` without a matching `takeRetainedValue()` / `release()`, or allocating C/CF objects (`CGPathCreateMutable()`, `CVPixelBufferCreate()`) without releasing them.

### 🟠 High (Memory Bloat & JetSam / OOM Crash Risk)
- **Tight Loops Lacking `@autoreleasepool`**: Processing large batches of images, audio buffers, or disk payloads (`Data(contentsOf:)`, `UIImage(contentsOfFile:)`) in a tight loop. Because ARC releases autoreleased objects at the end of the RunLoop turn, resident memory spikes monotonically until the iOS kernel terminates the app (`EXC_RESOURCE RESOURCE_TYPE_MEMORY`).
- **Full-Resolution Image Decoding**: Assigning multi-megabyte compressed photos directly to `UIImageView` or SwiftUI `Image` without downsampling via `CGImageSourceCreateThumbnailAtIndex`, forcing the system to decode a 40–80MB raw bitmap into RAM for a 100x100 point cell.
- **Unbounded In-Memory Caches**: Using standard Swift `Dictionary<Key, Value>` or `Array` instances as persistent caches without an eviction policy, instead of `NSCache` (which automatically purges under memory pressure).
- **Core Data / SwiftData Batch Retention**: Executing large imports or batch fetches without calling `context.reset()` or `context.refreshAllObjects()`, accumulating thousands of registered managed objects in memory.

### 🟡 Medium (Zombie Tasks & Subscription Leaks / Abandoned Memory)
- **Discarded NotificationCenter Observer Tokens**: Calling `NotificationCenter.default.addObserver(forName:object:queue:using:)` without capturing the returned `NSObjectProtocol` token or without removing it in `deinit` / teardown.
- **Combine `.sink` Lifecycles**: Storing `.sink { ... }` subscriptions in a long-lived singleton or coordinator rather than tying them to the view controller or view model lifecycle.
- **GCD Delayed Retention**: Using `DispatchQueue.main.asyncAfter(deadline: .now() + 60.0) { self.update() }` without `[weak self]`, preventing deallocation until the delay elapses.
- **DispatchSourceTimer Cycles**: Registering `.setEventHandler { self.poll() }` on a `DispatchSourceTimer` stored on `self` without `[weak self]`.
- **AVFoundation Time Observers**: Adding `player.addPeriodicTimeObserver(forInterval:queue:using:)` without saving the token and calling `player.removeTimeObserver(token)` upon teardown.
- **SwiftUI View Model Inline Instantiation**: Using `@ObservedObject var vm = ViewModel()` inside a view initializer or body, causing repeated allocations and dangling subscriptions on every parent redraw.

### 🔵 Low (Inefficiency & Scope Hygiene)
- **Over-Capturing Closures**: Using `[weak self]` in non-escaping closures (e.g., standard `Array.map`, `Array.filter`) where ARC does not retain the closure beyond the call stack.
- **Non-Purged Notification Subscriptions**: Relying on iOS 9+ automatic `removeObserver` behavior for selector-based observers while leaving dangling closures on modern block-based observers.

---

## 2. Automated Fast-Scan (CLI Pre-Scan)

Before conducting deep AST manual inspection, run the bundled zero-dependency Python scanner to surface project-wide memory hazards in seconds:

```bash
# Output colored table summary of memory hazards
python3 skills/ios-memory-leak-audit/scripts/scan_memory_leaks.py <path/to/ios/project>

# Export structured Markdown report for pull requests
python3 skills/ios-memory-leak-audit/scripts/scan_memory_leaks.py <path/to/ios/project> --format markdown -o memory_leak_report.md

# Machine-readable JSON output
python3 skills/ios-memory-leak-audit/scripts/scan_memory_leaks.py <path/to/ios/project> --format json
```

The scanner analyzes Swift files for:
- Strong delegates (`var delegate:` without `weak`)
- Combine `.sink` without `[weak self]`
- Combine `assign(to: \.prop, on: self)` retain cycles
- `Timer.scheduledTimer` with strong `target: self`
- `DispatchSourceTimer` and `asyncAfter` retaining `self`
- `NotificationCenter.default.addObserver` with discarded token
- `WKUserContentController.add(self, ...)` WebKit leaks
- `AVPlayer.addPeriodicTimeObserver` without token tracking
- Batch loops missing `@autoreleasepool`
- Unbounded dictionary caches instead of `NSCache`
- `Unmanaged.passRetained` without matching releases

---

## 3. Screen & Component Audit Protocol

Perform the memory audit methodically across the application layers:

```
[UI View / Screen] ──────> [ViewModel / Coordinator] ──────> [Services & Networking]
  (Delegates, Views)         (Combine, Tasks, GCD)             (Streams, Caches)
         │                           │                                │
         ▼                           ▼                                ▼
[RunLoop & Timers]          [Observers & WebKit]            [CoreFoundation & C]
  (CADisplayLink, Timer)      (NotificationCenter, WKWebView) (Unmanaged, CVPixelBuffer)
```

### Step 1: Scan View & ViewController Lifecycles
- Check all `protocol ...Delegate: AnyObject` definitions. Are all consuming delegate properties marked `weak`?
- Verify whether `UIHostingController` or child view controllers hold closures that capture their parent.
- In SwiftUI views, ensure ViewModel dependencies use `@StateObject` (or `@State` with `@Observable`), never `@ObservedObject var vm = ViewModel()`.

### Step 2: Audit Closures, Combine & Concurrency
- Inspect all `.sink` calls. Do they use `[weak self]`?
- Search for `assign(to:on:)`. Replace every `assign(to: \.prop, on: self)` with `assign(to: &$prop)` or a `.sink [weak self]` block.
- Search for `Task { ... }` or `Task.detached { ... }` inside class methods. If iterating an infinite sequence (`AsyncStream`, `NotificationCenter.notifications`), ensure `self` is captured weakly or the task handle is cancelled in `deinit`.

### Step 3: Audit Timers, GCD & WebKit Handlers
- Search for `Timer.scheduledTimer`. If using `target: self`, replace with block-based `Timer.scheduledTimer(withTimeInterval:repeats:block:) { [weak self] _ in }` or use the `WeakProxy` pattern.
- In `WKWebView` integrations, ensure `userContentController.add(self, name:)` uses a `WeakScriptMessageHandler` proxy.
- Inspect `DispatchQueue.main.asyncAfter` and `DispatchSourceTimer`. Verify they use `[weak self]` and are invalidated properly.

### Step 4: Audit Memory Bloat & High-Water Mark Loops
- Search for `for ... in` loops performing bulk disk I/O, Core Graphics, or image rendering. Wrap the loop body in `@autoreleasepool { ... }`.
- Verify photo loading in collection/table views uses downsampled thumbnails (`CGImageSourceCreateThumbnailAtIndex`) rather than raw full-resolution bitmaps.
- Search for `var ...Cache = [Key: Value]()`. Replace with `NSCache<Key, Value>()` to ensure automatic memory eviction under memory pressure.

---

## 4. Reusable Production Recipes

### Recipe 1: Generic `WeakProxy` Trampoline
Use this trampoline to break retain cycles in `Timer`, `CADisplayLink`, and `WKScriptMessageHandler`:

```swift
import WebKit

final class WeakProxy<T: AnyObject>: NSObject, WKScriptMessageHandler {
    private weak var target: T?

    init(_ target: T) {
        self.target = target
        super.init()
    }

    // WebKit handler forwarding
    func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
        (target as? WKScriptMessageHandler)?.userContentController(userContentController, didReceive: message)
    }

    // Timer / Selector forwarding
    @objc func timerFired(_ timer: Timer) {
        let selector = #selector(timerFired(_:))
        if let target = target, target.responds(to: selector) {
            target.perform(selector, with: timer)
        } else {
            timer.invalidate()
        }
    }
}
```

### Recipe 2: Automated Unit Test Memory Leak Assertion
Drop this helper into your test target to catch retain cycles automatically during CI:

```swift
import XCTest

extension XCTestCase {
    func trackForMemoryLeaks(_ instance: AnyObject, file: StaticString = #filePath, line: UInt = #line) {
        addTeardownBlock { [weak instance] in
            XCTAssertNil(
                instance,
                "Instance was not deallocated. Possible retain cycle detected.",
                file: file,
                line: line
            )
        }
    }
}

// Usage in tests:
final class ProfileViewModelTests: XCTestCase {
    func test_viewModel_doesNotLeakOnTeardown() {
        let sut = ProfileViewModel(apiClient: MockClient())
        trackForMemoryLeaks(sut)
        sut.loadData()
    }
}
```

### Recipe 3: High-Performance Image Downsampling
Avoid 50MB bitmap decodes in memory by generating display-sized thumbnails:

```swift
import ImageIO
import UIKit

func downsampleImage(at url: URL, to pointSize: CGSize, scale: CGFloat = UIScreen.main.scale) -> UIImage? {
    let imageSourceOptions = [kCGImageSourceShouldCache: false] as CFDictionary
    guard let imageSource = CGImageSourceCreateWithURL(url as CFURL, imageSourceOptions) else { return nil }

    let maxDimensionInPixels = max(pointSize.width, pointSize.height) * scale
    let downsampleOptions = [
        kCGImageSourceCreateThumbnailFromImageAlways: true,
        kCGImageSourceShouldCacheImmediately: true,
        kCGImageSourceCreateThumbnailWithTransform: true,
        kCGImageSourceThumbnailMaxPixelSize: maxDimensionInPixels
    ] as [CFString: Any] as CFDictionary

    guard let downsampledImage = CGImageSourceCreateThumbnailAtIndex(imageSource, 0, downsampleOptions) else { return nil }
    return UIImage(cgImage: downsampledImage)
}
```

---

## 5. Reporting Structure

Format all audit findings screen-by-screen, ordering results by severity:

````markdown
# Memory Leak & ARC Audit Report: [Module / App Name]

## Executive Summary
- **Files Audited**: [N]
- **Critical Retain Cycles**: [N]
- **Memory Bloat Hazards**: [N]
- **Medium Subscription Leaks**: [N]

## Screen / Component Findings

### 1. [ScreenName / ViewModelName]
- **Severity**: 🔴 Critical
- **Category**: Closure Retain Cycle (Combine `assign(to:on:)`)
- **Location**: `Sources/Features/Profile/ProfileViewModel.swift:42`
- **Root Cause**: `assign(to: \.userData, on: self)` creates a strong reference cycle back to the view model.
- **Surgical Fix**:

```swift
// BEFORE
userRepository.userPublisher
    .assign(to: \.userData, on: self)
    .store(in: &cancellables)

// AFTER
userRepository.userPublisher
    .sink { [weak self] user in
        self?.userData = user
    }
    .store(in: &cancellables)
```

- **Verification Plan**:
  - Run `trackForMemoryLeaks(viewModel)` in unit tests.
  - Profile in Xcode Memory Graph Debugger to confirm node deallocation.
````

---

## 6. Bundled Reference Guides

- 📖 [`references/retain-cycles-and-closures.md`](./references/retain-cycles-and-closures.md): In-depth mechanics of `[weak self]`, unowned hazards, Combine subscriptions, GCD delays, and Swift Concurrency Task retain loops.
- 🌊 [`references/memory-bloat-and-autorelease.md`](./references/memory-bloat-and-autorelease.md): RunLoop mechanics, `@autoreleasepool` in batch operations, Core Data context clearing, and downsampling.
- 🌐 [`references/webkit-and-system-observers.md`](./references/webkit-and-system-observers.md): `WKScriptMessageHandler` leaks, `AVPlayer` periodic time observers, and block-based `NotificationCenter` tokens.
- 🛠️ [`references/instruments-memory-debugging.md`](./references/instruments-memory-debugging.md): Step-by-step recipes for Xcode Memory Graph Debugger, Malloc Stack Logging, Allocations **Mark Generation**, and terminal commands (`leaks`, `vmmap`).
- 🧪 [`references/automated-leak-testing.md`](./references/automated-leak-testing.md): Automated CI leak assertions in `XCTestCase` and modern `Swift Testing`.
- 📊 [`evals/benchmark.md`](./evals/benchmark.md): Multi-scenario benchmark evaluation validating 100% detection rate.
