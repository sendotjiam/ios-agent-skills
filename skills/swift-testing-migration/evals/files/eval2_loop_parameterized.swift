import XCTest

class CalculatorTests: XCTestCase {
    func testAddOperations() {
        let testCases = [
            (1, 2, 3),
            (2, 3, 5),
            (5, 5, 10)
        ]

        // HAZARD 1: Loop executing assertions (candidate for @Test(arguments: [...]))
        for (a, b, expected) in testCases {
            XCTAssertEqual(a + b, expected)
        }
    }
}
