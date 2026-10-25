# Xcode Instruments & Empirical Profiling Recipes

Optimization without measurement is guesswork. This guide provides repeatable profiling recipes using Xcode Instruments, console diagnostics, and MetricKit.

---

## 1. Diagnostic Console Logging: `Self._printChanges()`

`Self._printChanges()` is an internal SwiftUI method available in iOS 15+ that prints the exact property, binding, or identity change that caused `body` to evaluate.

### Usage
```swift
struct FeedListView: View {
    @ObservedObject var viewModel: FeedViewModel

    var body: some View {
        #if DEBUG
        let _ = Self._printChanges()
        #endif

        List(viewModel.items) { item in
            FeedRow(item: item)
        }
    }
}
```

### Deciphering the Console Output

| Output | Meaning | Actionable Fix |
| :--- | :--- | :--- |
| `FeedListView: @self changed.` | The view struct's parameters or properties were re-evaluated. | Ensure parameters are POD values or conform to `Equatable`. Extract subviews. |
| `FeedListView: _viewModel changed.` | An `@ObservedObject` emitted `objectWillChange` or an `@Observable` property was read. | Check if unrelated properties in `viewModel` are mutating. Split view models. |
| `FeedListView: @identity changed.` | Structural or explicit identity changed (e.g., conditional branching or `.id()`). | Preserve view hierarchy; avoid switching `if/else` on same view type. |

---

## 2. Xcode Instruments: SwiftUI Template

Use the dedicated **SwiftUI** Instruments template in Xcode 15/16:

1. Open Xcode: **Product $\rightarrow$ Profile** (`Cmd + I`).
2. Select the **SwiftUI** template (or start with **Time Profiler** and add the SwiftUI instruments).

### Key Instruments & Metrics:

### A. SwiftUI View Body
- **View Body Invocations**: Sort by invocation count. If a leaf view has thousands of invocations during a short interaction, investigate parent over-invalidation.
- **Duration**: Target $< 1.0\text{ms}$ per evaluation. Any view averaging $> 16\text{ms}$ will drop a frame instantly.

### B. SwiftUI View Properties
- Inspect which dynamic properties (`@State`, `@Binding`, `@Environment`, `@Query`) are invalidating most frequently.

### C. Core Animation Commits
- Shows render server commit cost.
- High commit times ($> 4\text{ms}$) indicate complex layer hierarchies, excessive view depth, or heavy offscreen drawing.

---

## 3. Core Animation Hitches & Hangs Profiling

Scroll smoothness is measured by **Hitch Time Ratio** ($\text{ms/s}$):

$$\text{Hitch Ratio} = \frac{\text{Total Hitch Time (ms)}}{\text{Total Scroll Duration (s)}}$$

- **Target**: $< 5\text{ms/s}$ (Good)
- **Warning**: $5 - 10\text{ms/s}$ (Noticeable stutter)
- **Critical**: $> 10\text{ms/s}$ (Severe hitching)

### Identifying Hitch Culprits:
1. In Instruments, open the **Hangs** instrument track alongside **Time Profiler**.
2. Zoom into frame drops marked red or yellow during a fling gesture.
3. Check the heaviest stack trace:
   - If blocked on `Main Thread` executing `JSONDecoder`, `NSRegularExpression`, or `DateFormatter`: **CPU body compute bottleneck**.
   - If blocked on `CA::Render::Server`: **GPU offscreen rasterization bottleneck** (shadows, blurs, or layer masks).

---

## 4. Production Telemetry: MetricKit

Track aggregate real-world scroll hitches in production using `MXMetricManager`:

```swift
import MetricKit

final class PerformanceMetricsLogger: NSObject, MXMetricManagerSubscriber {
    override init() {
        super.init()
        MXMetricManager.shared.add(self)
    }

    func didReceive(_ payloads: [MXMetricPayload]) {
        for payload in payloads {
            if let animationMetrics = payload.animationMetrics {
                let scrollHitchRatio = animationMetrics.scrollHitchTimeRatio
                // Send telemetry to backend for monitoring release health
                print("Aggregate Scroll Hitch Ratio: \(scrollHitchRatio)")
            }
        }
    }
}
```
