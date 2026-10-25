import UIKit

// Scenario 2: Strong Delegates, Timers, and GCD Delayed Blocks

protocol SettingsViewDelegate: AnyObject {
    func didUpdateSettings()
}

final class SettingsViewController: UIViewController {
    // HAZARD 1: Strong delegate reference missing 'weak'
    var delegate: SettingsViewDelegate?

    private var repeatingTimer: Timer?
    private var heartbeatSource: DispatchSourceTimer?

    override func viewDidLoad() {
        super.viewDidLoad()
        startSyncTimer()
        startHeartbeat()
        scheduleDelayedRefresh()
    }

    private func startSyncTimer() {
        // HAZARD 2: Timer.scheduledTimer with strong target: self
        repeatingTimer = Timer.scheduledTimer(
            timeInterval: 10.0,
            target: self,
            selector: #selector(handleTimerFired),
            userInfo: nil,
            repeats: true
        )
    }

    private func startHeartbeat() {
        // HAZARD 3: DispatchSourceTimer setEventHandler strongly capturing self
        let source = DispatchSource.makeTimerSource(queue: .global())
        source.schedule(deadline: .now(), repeating: 5.0)
        source.setEventHandler {
            self.pingBackendServer()
        }
        self.heartbeatSource = source
        source.resume()
    }

    private func scheduleDelayedRefresh() {
        // HAZARD 4: GCD asyncAfter delayed retention keeping VC alive
        DispatchQueue.main.asyncAfter(deadline: .now() + 60.0) {
            self.refreshUIState()
        }
    }

    @objc private func handleTimerFired() {}
    private func pingBackendServer() {}
    private func refreshUIState() {}
}
