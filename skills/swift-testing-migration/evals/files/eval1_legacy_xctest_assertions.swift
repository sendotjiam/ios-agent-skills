import XCTest

// HAZARD 1: Legacy XCTestCase class
class UserProfileTests: XCTestCase {
    func testUserAttributes() {
        let user = "Alice"
        // HAZARD 2: Legacy assertions
        XCTAssertEqual(user, "Alice")
        XCTAssertTrue(user.count > 0)
        XCTAssertNil(nil)
    }
}
