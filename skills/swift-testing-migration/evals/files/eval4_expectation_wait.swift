import XCTest

class NetworkCallbackTests: XCTestCase {
    func testFetchUserData() {
        // HAZARD 1: Legacy XCTest expectation
        let exp = expectation(description: "Network response")

        DispatchQueue.global().async {
            exp.fulfill()
        }

        wait(for: [exp], timeout: 2.0)
    }
}
