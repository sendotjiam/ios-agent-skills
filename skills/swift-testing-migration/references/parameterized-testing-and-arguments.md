# Parameterized Testing with `@Test(arguments:)`

## Problem: Loops in XCTest
In `XCTest`, testing multiple inputs required `for (input, expected) in testCases` loops.
- If item 3 failed, the entire test aborted or required deciphering custom failure messages.
- Xcode's Test Navigator showed only 1 test, hiding which specific argument failed.

---

## Solution: Native Swift Testing `@Test(arguments:)`

```swift
import Testing

@Suite("Tax Calculation Tests")
struct TaxCalculatorTests {
    @Test("Sales tax calculation across states", arguments: [
        ("CA", 100.0, 107.25),
        ("NY", 100.0, 108.875),
        ("TX", 100.0, 106.25),
        ("OR", 100.0, 100.00)
    ])
    func calculateStateTax(state: String, subtotal: Double, expectedTotal: Double) {
        let calculator = TaxCalculator()
        let result = calculator.total(for: subtotal, state: state)
        #expect(result == expectedTotal)
    }
}
```

### Benefits:
1. Each argument tuple executes as an independent sub-test in Xcode.
2. If `NY` fails, `CA`, `TX`, and `OR` continue to run and report success.
3. Test failures pinpoint the exact input parameters automatically.
