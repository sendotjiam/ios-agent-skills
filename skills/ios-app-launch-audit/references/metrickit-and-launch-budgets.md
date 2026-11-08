# MetricKit App Launch Metrics & 400ms Cold Launch Budget

## 1. Apple's Launch Time Budget
- **Target Cold Launch Duration:** $\le 400\text{ms}$ to first interactive frame.
- **Watchdog Timeout Limit (`0x8badf00d`):** 20 seconds. If an app takes too long to launch (e.g. during a heavy database migration), iOS sends SIGKILL.

---

## 2. MetricKit Implementation for Launch Tracking

```swift
import Foundation
import MetricKit

public final class AppLaunchMonitor: NSObject, MXMetricManagerSubscriber, Sendable {
    public static let shared = AppLaunchMonitor()

    public func startMonitoring() {
        MXMetricManager.shared.add(self)
    }

    public func didReceive(_ payloads: [MXMetricPayload]) {
        for payload in payloads {
            if let launchMetrics = payload.applicationLaunchMetrics {
                let timeToFirstDraw = launchMetrics.histogrammedTimeToFirstDraw
                print("Cold launch time to first draw: \(timeToFirstDraw)")
                
                if let resumeTime = launchMetrics.histogrammedApplicationResumeTime {
                    print("Warm launch resume time: \(resumeTime)")
                }
            }
        }
    }
}
```
