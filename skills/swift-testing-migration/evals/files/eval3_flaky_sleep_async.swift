import XCTest

class AsyncWorkerTests: XCTestCase {
    func testAsyncNotification() {
        var notified = false
        NotificationCenter.default.addObserver(forName: NSNotification.Name("Done"), object: nil, queue: nil) { _ in
            notified = true
        }

        NotificationCenter.default.post(name: NSNotification.Name("Done"), object: nil)

        // HAZARD 1: Flaky sleep wait in test
        Thread.sleep(forTimeInterval: 0.5)
        XCTAssertTrue(notified)
    }
}
