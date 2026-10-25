# Retain Cycles, Closures & Modern Concurrency Leaks

In Swift, Automatic Reference Counting (ARC) automatically manages object memory by tracking active references to class instances. An instance is deallocated only when its reference count drops to zero.

A **strong reference cycle** (or retain cycle) occurs when two or more objects hold strong references to each other, preventing their reference counts from ever reaching zero. When this happens, `deinit` is never invoked, and memory is permanently leaked.

---

## 1. Closure Capture Lists: `[weak self]` vs `[unowned self]`

Closures in Swift capture variables by reference by default. When an object stores a closure as a property, and that closure accesses properties or methods on `self`, a bidirectional retain cycle is formed.

### The Strong Retain Cycle

```swift
// ❌ CRITICAL LEAK: Bi-directional retain cycle
final class OrderViewModel {
    var onOrderCompleted: (() -> Void)?
    var orderId: String = "12345"

    func configureCompletionHandler() {
        // self holds onOrderCompleted closure
        // onOrderCompleted closure holds self
        self.onOrderCompleted = {
            self.analyticsLog(orderId: self.orderId)
        }
    }

    private func analyticsLog(orderId: String) { ... }
}
```

### The Fix: `[weak self]`

```swift
// ✅ CLEAN: Weak reference breaks the cycle
final class OrderViewModel {
    var onOrderCompleted: (() -> Void)?
    var orderId: String = "12345"

    func configureCompletionHandler() {
        self.onOrderCompleted = { [weak self] in
            guard let self else { return }
            self.analyticsLog(orderId: self.orderId)
        }
    }
}
```

### The Hazard of `[unowned self]`

`unowned` does not increment reference count, but assumes the target is *guaranteed* to be alive when invoked. If the captured object is deallocated before the closure is called (e.g. an asynchronous network callback returning after the user dismissed the screen), accessing `self` triggers a fatal runtime crash:

```
Fatal error: Attempted to read an unowned reference but the object was already deallocated
```

> **Best Practice Rule:** Never use `unowned` for asynchronous callbacks, network closures, or timers. Use `[weak self]` with `guard let self else { return }`. Reserve `unowned` exclusively for parent-child relationships where the child's lifetime is strictly bounded by the parent.

---

## 2. Strong Delegates Anti-Pattern

In UIKit and classic Swift design patterns, delegates must be declared `weak` to prevent retain cycles between the delegator and the delegate:

```swift
// ❌ CRITICAL LEAK: Strong delegate cycle
protocol PaymentSheetDelegate: AnyObject {
    func paymentDidComplete()
}

final class PaymentSheetViewController: UIViewController {
    // Missing 'weak' - parent view controller retains PaymentSheetViewController,
    // and PaymentSheetViewController retains parent via delegate.
    var delegate: PaymentSheetDelegate?
}

// ✅ CLEAN: Weak delegate
final class PaymentSheetViewController: UIViewController {
    weak var delegate: PaymentSheetDelegate?
}
```

> **Compiler Constraint:** The delegate protocol **must** inherit from `AnyObject` (or `@objc`) so the compiler knows it can only be conformed to by class types. Value types (`struct`) cannot be held weakly.

---

## 3. Combine Pipelines & The `assign(to:on:)` Trap

Combine publishers provide two primary ways to subscribe: `.sink` and `.assign`. Both can cause retain cycles if not handled with care.

### The `assign(to:on: self)` Trap
Apple's Combine framework has a documented trap: `assign(to: \.property, on: self)` captures `self` **strongly**. If the publisher is stored in a cancellable on `self`, a permanent retain cycle is created:

```swift
// ❌ CRITICAL LEAK: Permanent retain cycle
final class UserProfileViewModel {
    @Published var userName: String = ""
    private var cancellables = Set<AnyCancellable>()

    func bind(userService: UserService) {
        userService.namePublisher
            .assign(to: \.userName, on: self) // Strongly captures 'self'
            .store(in: &cancellables)
    }
}
```

### The Solutions:
1. **iOS 14+ `@Published` inout assign**:
   ```swift
   // ✅ CLEAN: Captures publisher internally without retaining self
   userService.namePublisher
       .assign(to: &$userName)
   ```
2. **Sink with `[weak self]`**:
   ```swift
   // ✅ CLEAN: Explicit weak capture
   userService.namePublisher
       .sink { [weak self] name in
           self?.userName = name
       }
       .store(in: &cancellables)
   ```

---

## 4. GCD & Delayed Block Retention

Grand Central Dispatch operations dispatched asynchronously hold strong references to captured variables for the duration of the dispatch.

```swift
final class DetailViewController: UIViewController {
    func scheduleDelayedSync() {
        // ❌ MEDIUM: View controller cannot deallocate for 60 seconds after dismissal!
        DispatchQueue.main.asyncAfter(deadline: .now() + 60.0) {
            self.refreshContent()
        }

        // ✅ CLEAN: Immediate deallocation on dismissal
        DispatchQueue.main.asyncAfter(deadline: .now() + 60.0) { [weak self] in
            self?.refreshContent()
        }
    }
}
```

### `DispatchSourceTimer` Retain Cycles
A `DispatchSourceTimer` stored as an instance property with an event handler referencing `self` creates an unbreakable cycle:

```swift
final class HeartbeatMonitor {
    private var timer: DispatchSourceTimer?

    func start() {
        let t = DispatchSource.makeTimerSource(queue: .global())
        t.schedule(deadline: .now(), repeating: 5.0)
        // ❌ CRITICAL: Event handler captures self; self retains timer
        t.setEventHandler {
            self.ping()
        }
        self.timer = t
        t.resume()
    }

    // ✅ FIX: Use weak self
    func startFixed() {
        let t = DispatchSource.makeTimerSource(queue: .global())
        t.schedule(deadline: .now(), repeating: 5.0)
        t.setEventHandler { [weak self] in
            self?.ping()
        }
        self.timer = t
        t.resume()
    }

    deinit {
        timer?.cancel()
    }
}
```

---

## 5. Modern Swift Concurrency (`Task` & `AsyncStream` Retain Traps)

Swift Concurrency tasks participate in ARC differently depending on whether they are structured or unstructured:

1. **Structured Tasks (`withTaskGroup`, `async let`)**: Automatically scoped to their enclosing lexical scope. They cancel and wait before exiting.
2. **Unstructured Tasks (`Task { }`, `Task.detached { }`)**: Detached from the calling scope lifetime! If an unstructured task runs an infinite loop or listens to an `AsyncSequence` while referencing `self`, `self` is held indefinitely in memory.

```swift
final class NotificationListener {
    private var task: Task<Void, Never>?

    func startListening() {
        // ❌ LEAK: Infinite loop strongly capturing self in unstructured task
        task = Task {
            for await notification in NotificationCenter.default.notifications(named: .userDidLogin) {
                self.handleNotification(notification)
            }
        }
    }

    // ✅ FIX: Weak capture + cancellation in deinit
    func startListeningFixed() {
        task = Task { [weak self] in
            for await notification in NotificationCenter.default.notifications(named: .userDidLogin) {
                guard let self else { return }
                self.handleNotification(notification)
            }
        }
    }

    deinit {
        task?.cancel()
    }
}
```
