# Automated Memory Leak Unit Testing in CI

Waiting for manual Instruments profiling or QA bug reports is too late in the software development lifecycle. By integrating automated memory leak assertions into unit and integration test suites, teams can catch retain cycles in Pull Requests before merging.

---

## 1. The `XCTestCase` Teardown Leak Tracker

In `XCTest`, each test method executes, followed by teardown. The `addTeardownBlock` API allows registering a closure to execute after the test completes.

By holding a **`weak` reference** to the System Under Test (SUT) inside the teardown block, we can assert that the object's reference count dropped to zero and became `nil` after the test scope finished.

### Reusable Test Helper Extension

```swift
import XCTest

extension XCTestCase {
    /// Asserts that an instance is deallocated after the test finishes execution.
    ///
    /// - Parameters:
    ///   - instance: The object to monitor for retain cycles.
    ///   - file: The source file of the caller.
    ///   - line: The line number of the caller.
    func trackForMemoryLeaks(
        _ instance: AnyObject,
        file: StaticString = #filePath,
        line: UInt = #line
    ) {
        addTeardownBlock { [weak instance] in
            XCTAssertNil(
                instance,
                "🚨 Memory Leak Detected: Instance '\(String(describing: instance))' was not deallocated. Check for closure retain cycles, strong delegates, or dangling subscriptions.",
                file: file,
                line: line
            )
        }
    }
}
```

---

## 2. Testing View Models & Coordinators

```swift
import XCTest
@testable import MyApp

final class CheckoutViewModelTests: XCTestCase {

    func test_checkoutViewModel_doesNotLeakWhenOrderCompletes() {
        // Arrange
        let mockPaymentGateway = MockPaymentGateway()
        let sut = CheckoutViewModel(paymentGateway: mockPaymentGateway)

        // Track SUT for memory leaks!
        trackForMemoryLeaks(sut)

        // Act
        sut.submitOrder()
        mockPaymentGateway.simulateSuccess()

        // Assert
        XCTAssertEqual(sut.state, .completed)
        // Once this test scope exits, addTeardownBlock executes and asserts sut is nil.
    }
}
```

---

## 3. Testing UIKit `UIViewController` Deallocation

View controllers often leak through child coordinators, navigation controllers, or notification observers. To test UIViewController deallocation:

```swift
final class DetailViewControllerTests: XCTestCase {

    func test_viewController_deallocatesAfterDismissal() {
        var sut: DetailViewController? = DetailViewController()
        trackForMemoryLeaks(sut!)

        // Trigger view lifecycle
        sut?.loadViewIfNeeded()

        // Simulate presentation & dismissal
        sut = nil // Release local strong reference

        // If DetailViewController captured self in a closure or notification observer,
        // teardown assertion will fail with a clear stack trace.
    }
}
```

---

## 4. Modern `Swift Testing` (Swift 6) Pattern

In Swift 6's new `@Test` framework (`import Testing`), tests are structured as structs or functions without `XCTestCase` inheritance. You can implement leak tracking using a scoped defer block or custom wrapper:

```swift
import Testing

struct MemoryLeakTracker {
    private weak var object: AnyObject?

    init(_ object: AnyObject) {
        self.object = object
    }

    func verifyDeallocated(sourceLocation: SourceLocation = #_sourceLocation) {
        #expect(object == nil, "Instance was not deallocated. Retain cycle present.", sourceLocation: sourceLocation)
    }
}

@Suite("Settings Feature Memory Tests")
struct SettingsTests {

    @Test("SettingsViewModel deallocates after logout")
    func viewModelDeallocates() async {
        var sut: SettingsViewModel? = SettingsViewModel()
        let tracker = MemoryLeakTracker(sut!)

        await sut?.logout()
        sut = nil // Release local reference

        tracker.verifyDeallocated()
    }
}
```
