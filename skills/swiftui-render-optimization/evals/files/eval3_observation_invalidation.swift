import SwiftUI

@Observable
final class DashboardStore {
    var title: String = "Dashboard"
    var heartRate: Int = 72
    var stepCount: Int = 8450
    
    // ⚠️ ISSUE 1: Background timer & cancellables not marked with @ObservationIgnored
    var pollingTimer: Timer?
    var networkCallsInFlight: Int = 0
}

struct MetricBadgeView: View {
    // ⚠️ ISSUE 2: Passing entire observable store when only stepCount is rendered
    let store: DashboardStore

    var body: some View {
        Text("Steps: \(store.stepCount)")
    }
}

struct DashboardContainerView: View {
    // ⚠️ ISSUE 3: Recreating @ObservedObject inline on every render pass
    @ObservedObject var legacyStore = LegacyObservableStore()
    @State private var store = DashboardStore()

    var body: some View {
        VStack {
            Text(store.title)
            MetricBadgeView(store: store)
        }
    }
}

class LegacyObservableStore: ObservableObject {
    @Published var data: [String] = []
}
