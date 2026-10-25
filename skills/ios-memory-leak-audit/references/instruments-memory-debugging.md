# Runtime Memory Profiling: Xcode Memory Graph & Instruments

Static analysis identifies suspicious patterns, but runtime profiling provides indisputable empirical proof of retained objects, abandoned heap allocations, and JetSam memory limits.

---

## 1. Xcode Memory Graph Debugger

The **Memory Graph Debugger** pauses process execution and generates a complete visual graph of all live heap allocations and their incoming/outgoing references.

### Enabling Malloc Stack Logging
To see the exact code line and stack trace where a leaked object was allocated:
1. In Xcode, select **Product > Scheme > Edit Scheme...** (`⌘<`).
2. Select **Run** on the left sidebar, then click the **Diagnostics** tab.
3. Check **Malloc Stack Logging** and select **All Allocation and Free History**.
4. *(Optional via Terminal / Environment)*: Set `MallocStackLoggingNoCompact=1`.

### Step-by-Step Graph Inspection Protocol
1. Launch the app and navigate to the target screen.
2. Perform user actions (scroll, interact, trigger network loads).
3. Navigate **back** (dismiss the screen).
4. In Xcode's debug bar at the bottom, click the **Debug Memory Graph** button (the icon showing 3 connected nodes).
5. In the left Navigator sidebar, filter by your app's module name.
6. Look for purple exclamation mark icons (`!`) indicating detected ARC retain cycles.
7. Click any retained instance. The right inspector displays the **Allocation Backtrace** showing exactly where `init` was called.

---

## 2. Instruments Allocations: The "Mark Generation" Technique

The **Mark Generation** (Generation Analysis) technique is the gold standard for detecting **abandoned memory**—objects that are not technically orphaned (they have owners), but should have been deallocated when leaving a screen.

### Step-by-Step Generation Analysis
1. In Xcode, select **Product > Profile** (`⌘I`).
2. Choose the **Allocations** instrument template.
3. Once the app launches to the home/root screen, click **Mark Generation** in the Instruments sidebar (creates `Generation A`).
4. Navigate into the suspect screen (e.g., User Profile).
5. Interact with the screen, then navigate **back** to the home screen.
6. Click **Mark Generation** again (creates `Generation B`).
7. Repeat the navigation push/pop cycle 3 times (`Generation C`, `Generation D`).

### Evaluating Generations
- Expand `Generation D`.
- Sort by **Growth** descending.
- If your view controllers, view models, or caches appear in `Generation D` with non-zero growth after navigating back to the root, **they are leaking**.

---

## 3. Terminal Diagnostics: `leaks`, `vmmap` & `heap`

When running inside the iOS Simulator or macOS CLI, you can inspect processes directly from the terminal without launching Xcode.

### Identifying Process ID
```bash
pgrep -f "MyApp.app"
```

### Checking for Live Leaks
```bash
# Run leaks audit against live simulator process
xcrun leaks <PID>

# Or generate a detailed reference trace
xcrun leaks --trace <PID>
```

### Analyzing Virtual Memory Map (`vmmap`)
```bash
# View resident memory pages by region (Dirty vs Clean RAM)
vmmap -resident <PID> | grep -E "(MALLOC|CG image|Stack)"

# Check overall memory footprint summary
vmmap --summary <PID>
```

---

## 4. Production Telemetry: MetricKit & JetSam Tracking

To catch memory terminations on real user devices in production, monitor **MetricKit** payloads:

```swift
import MetricKit

final class MemoryDiagnosticsService: NSObject, MXMetricManagerSubscriber {
    static let shared = MemoryDiagnosticsService()

    func start() {
        MXMetricManager.shared.add(self)
    }

    func didReceive(_ payloads: [MXDiagnosticPayload]) {
        for payload in payloads {
            // Check for memory limit termination reports
            if let exitMetrics = payload.applicationExitMetrics {
                let jetsamExits = exitMetrics.backgroundExitData.cumulativeMemoryResourceLimitExceededExitCount
                if jetsamExits > 0 {
                    print("⚠️ JetSam terminations detected: \(jetsamExits)")
                }
            }
        }
    }
}
```
