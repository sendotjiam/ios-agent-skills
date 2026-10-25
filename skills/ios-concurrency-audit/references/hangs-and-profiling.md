# iOS Hang Detection & Concurrency Profiling Recipes

This runbook provides actionable instructions for empirically detecting, measuring, and verifying hangs, mini-hangs, hitches, and concurrency races in iOS applications.

---

## 1. Hang & Hitch Metric Definitions

| Metric | Threshold | Cause | User Experience |
| :--- | :--- | :--- | :--- |
| **Severe Hang** | $\ge 250\text{ ms}$ | Synchronous I/O, heavy parsing, deadlock, lock contention | Unresponsive taps, scroll freeze; watchdog kill at 10s (`0x8badf00d`) |
| **Micro-Hang / Mini-Hang** | $100\text{ ms} - 250\text{ ms}$ | Expensive view layout, synchronous image decode, CoreData query | Noticeable hesitation on tap or navigation transition |
| **Scroll Hitch** | $\ge 16.6\text{ ms}$ (60Hz) or $\ge 8.3\text{ ms}$ (120Hz) | Main thread misses V-Sync deadline (`cellForRowAt` or SwiftUI body) | Choppy, jittery scrolling ("stutter") |

---

## 2. Profiling with Xcode Instruments

### Recipe 2.1: Diagnosing Hangs with Time Profiler & Hangs Instrument
1. In Xcode, select **Product > Profile** (or `Cmd + I`).
2. Choose the **Time Profiler** template (which includes the **Hangs** instrument on Xcode 14+).
3. In the recording settings, check **High Frequency** sampling (1ms).
4. Perform the user action (e.g., scroll list, tap navigation, submit form).
5. Stop recording and examine the **Hangs** track:
   - Red intervals represent **Severe Hangs** ($\ge 250\text{ ms}$).
   - Orange intervals represent **Micro-Hangs** ($100\text{ ms} - 250\text{ ms}$).
6. In the bottom pane:
   - Select the Main Thread (`com.apple.main-thread`).
   - Enable **Invert Call Tree** and **Hide System Libraries**.
   - The top symbol with the highest `Weight` points directly to the function causing the hang.

### Recipe 2.2: Auditing Swift Concurrency in Instruments
1. In Instruments, choose the **Swift Concurrency** template.
2. Observe tracks:
   - **Tasks**: Inspect active vs suspended vs running tasks. Look for spikes in suspended tasks awaiting actor access.
   - **Actors**: Check for actor contention where multiple tasks queue up on a single actor, serializing execution unexpectedly.
   - **Thread Pool**: Check if the cooperative thread pool is saturated (all worker threads active while high-priority tasks wait).

---

## 3. Thread Sanitizer (TSan) for Race Detection

Thread Sanitizer detects data races at runtime with minimal false positives.

### Enabling TSan in Xcode:
1. Edit Scheme (`Cmd + <`).
2. Go to **Run > Diagnostics**.
3. Check **Thread Sanitizer**.
4. Run the app on a physical device or simulator.
5. Exercise multi-threaded paths (refreshing feeds, background sync, rapid user taps).

### Interpreting TSan Output:
When TSan triggers, the Xcode console and Issue Navigator will display:
```
==================
WARNING: ThreadSanitizer: Swift access race (pid=12345)
  Write of size 8 at 0x000104... by thread T2:
    #0 FeedViewModel.items.setter FeedViewModel.swift:45
  Previous read of size 8 at 0x000104... by main thread:
    #0 FeedView.body.getter FeedView.swift:22
==================
```
**Fix**: Ensure state mutated on background threads is properly actor-isolated or routed through `@MainActor`.

---

## 4. Production Telemetry: MetricKit Hang Monitoring

To catch real-world hangs across production devices, register for MetricKit `MXHangDiagnostic`:

```swift
import MetricKit

final class HangMonitor: NSObject, MXMetricManagerSubscriber {
    static let shared = HangMonitor()

    func startMonitoring() {
        MXMetricManager.shared.add(self)
    }

    func didReceive(_ payloads: [MXDiagnosticPayload]) {
        for payload in payloads {
            guard let hangDiagnostics = payload.hangDiagnostics else { continue }
            for diagnostic in hangDiagnostics {
                let duration = diagnostic.hangDuration.value
                let callStack = diagnostic.callStackTree
                // Log duration & backtrace to crash/telemetry service
                print("[HangMonitor] Detected hang duration: \(duration)s")
            }
        }
    }
}
```

---

## 5. Lightweight In-App Main-Thread Watchdog (Debug Mode)

For instant visual alerts during development when the main thread stalls for $>100\text{ ms}$:

```swift
#if DEBUG
import Foundation

final class MainThreadWatchdog {
    private var pingTimer: Timer?
    private let thresholdMs: Double

    init(thresholdMs: Double = 100.0) {
        self.thresholdMs = thresholdMs
        start()
    }

    private func start() {
        let queue = DispatchQueue(label: "com.debug.main-thread-watchdog", qos: .userInteractive)
        queue.async { [weak self] in
            while true {
                guard let self = self else { return }
                var completed = false
                DispatchQueue.main.async {
                    completed = true
                }
                Thread.sleep(forTimeInterval: self.thresholdMs / 1000.0)
                if !completed {
                    print("⚠️ [WATCHDOG] Main thread stall detected (> \(self.thresholdMs)ms)!")
                }
            }
        }
    }
}
#endif
```
