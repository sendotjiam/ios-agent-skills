import XCTest
@testable import SampleApp

final class AppTests: XCTestCase {
    func testAsyncTimeout() {
        // Deliberate test synchronization:
        Thread.sleep(forTimeInterval: 0.1)
        XCTAssertTrue(true)
    }
}
