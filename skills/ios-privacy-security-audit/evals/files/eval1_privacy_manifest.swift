import Foundation

final class DeviceDiagnostics {
    func collectMetrics() {
        // HAZARD 1: UserDefaults Required Reason API
        let count = UserDefaults.standard.integer(forKey: "app_launch_count")
        UserDefaults.standard.set(count + 1, forKey: "app_launch_count")

        // HAZARD 2: System Boot Time Required Reason API
        let uptime = ProcessInfo.processInfo.systemUptime

        // HAZARD 3: Disk Space Required Reason API
        let fileUrl = URL(fileURLWithPath: NSTemporaryDirectory())
        let values = try? fileUrl.resourceValues(forKeys: [.volumeAvailableCapacityKey])

        // HAZARD 4: File Timestamp Required Reason API
        let docValues = try? fileUrl.resourceValues(forKeys: [.URLContentModificationDateKey])

        print(uptime, values?.volumeAvailableCapacity ?? 0, docValues?.contentModificationDate ?? Date())
    }
}
