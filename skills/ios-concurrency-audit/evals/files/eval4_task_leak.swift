import UIKit

class LiveEventViewController: UIViewController {
    private var eventTask: Task<Void, Never>?
    private var eventCount = 0

    override func viewDidLoad() {
        super.viewDidLoad()
        
        // HAZARD: Strong self capture inside infinite AsyncSequence prevents UIViewController deallocation
        eventTask = Task {
            for await _ in NotificationCenter.default.notifications(named: .NSCalendarDayChanged) {
                self.eventCount += 1
                self.updateBadge()
            }
        }
    }

    private func updateBadge() {
        print("Updated count to \(eventCount)")
    }
}
