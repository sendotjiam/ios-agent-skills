# Swift Testing Migration Guide (XCTest to WWDC24 Swift Testing)

## Overview
Introduced in Xcode 16 / Swift 6, **Swift Testing** replaces `XCTest` with a modern, macro-based, async-first testing engine that runs seamlessly across iOS, macOS, watchOS, and Linux.

---

## 1. Syntax Comparison Cheat Sheet

| Feature | Legacy `XCTest` | Modern Swift `Testing` |
| :--- | :--- | :--- |
| **Import** | `import XCTest` | `import Testing` |
| **Suite** | `class FooTests: XCTestCase` | `@Suite struct FooTests` |
| **Test Case** | `func testExample()` | `@Test func example()` |
| **Equality** | `XCTAssertEqual(a, b)` | `#expect(a == b)` |
| **Boolean** | `XCTAssertTrue(x)` / `XCTAssertFalse(x)` | `#expect(x)` / `#expect(!x)` |
| **Nil / Unwrap** | `XCTAssertNotNil(x)` | `try #require(x)` |
| **Forced Failure**| `XCTFail("reason")` | `Issue.record("reason")` |
| **Async Waiting**| `expectation(description:)` + `wait(for:)` | `await confirmation { confirm in ... }` |

---

## 2. Before / After Migration Example

### Before (`XCTest`):
```swift
import XCTest

final class UserTests: XCTestCase {
    func testFullName() {
        let user = User(firstName: "Jane", lastName: "Doe")
        XCTAssertEqual(user.fullName, "Jane Doe")
        XCTAssertFalse(user.isBanned)
    }
}
```

### After (Swift `Testing`):
```swift
import Testing

@Suite("User Model Tests")
struct UserTests {
    @Test("Full name formatting and ban status")
    func fullName() {
        let user = User(firstName: "Jane", lastName: "Doe")
        #expect(user.fullName == "Jane Doe")
        #expect(!user.isBanned)
    }
}
```
