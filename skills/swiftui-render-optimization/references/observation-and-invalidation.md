# Observation, State Slicing & Invalidation Dynamics

Over-invalidation occurs when views re-evaluate their `body` in response to state changes they do not actually render. This reference outlines how to establish surgical observation boundaries across both modern (iOS 17+) and legacy (iOS 14–16) SwiftUI architectures.

---

## 1. Modern Observation (iOS 17+ `@Observable` Macro)

The Swift 5.9+ `@Observable` macro replaces Combine's `ObservableObject`. Instead of emitting whole-object change notifications, the runtime tracks **exact property reads** occurring inside a view's `body`.

### The Tracking Mechanism
```swift
@Observable
final class UserSession {
    var username: String = ""
    var unreadMessageCount: Int = 0
    var networkActivityIndicator: Bool = false
}

struct UsernameBadge: View {
    let session: UserSession

    var body: some View {
        // ✅ SwiftUI only registers a dependency on `session.username`
        Text(session.username)
    }
}
```
When `session.unreadMessageCount` or `session.networkActivityIndicator` mutates, `UsernameBadge.body` **does NOT execute**.

---

## 2. `@ObservationIgnored` for Background State

Properties that exist for business logic, logging, caching, or background coordination should be marked with `@ObservationIgnored`:

```swift
@Observable
final class FeedViewModel {
    var items: [FeedItem] = []
    
    // ⚠️ ANTI-PATTERN: Mutating this will trigger body evaluations in any view reading viewModel
    var activeTimer: Timer?
    var analyticsTracker: AnalyticsService?
    var networkCancellables: Set<AnyCancellable> = []
    
    // ✅ OPTIMIZED:
    @ObservationIgnored private var activeTimer: Timer?
    @ObservationIgnored private var analyticsTracker: AnalyticsService?
    @ObservationIgnored private var networkCancellables: Set<AnyCancellable> = []
}
```

---

## 3. State Slicing & Granular Subviews

Even with `@Observable`, passing a monolithic object down a deep hierarchy increases memory coupling and closure captures.

### Anti-Pattern: Passing Monolithic ViewModels to Leaf Rows
```swift
struct ItemRow: View {
    let viewModel: FeedViewModel // ⚠️ Passes entire VM
    let itemID: UUID

    var body: some View {
        if let item = viewModel.items.first(where: { $0.id == itemID }) {
            Text(item.title)
        }
    }
}
```
Every `ItemRow` evaluates `.first(where:)` on every collection update, turning $O(N)$ updates into $O(N^2)$ main-thread work.

### Optimized: Pass Discrete Value Types
```swift
struct ItemRow: View {
    let title: String // ✅ Pure value parameter
    let isSelected: Bool

    var body: some View {
        Text(title)
            .fontWeight(isSelected ? .bold : .regular)
    }
}
```

---

## 4. Legacy SwiftUI: Combine & `ObservableObject` Pitfalls (iOS 14–16)

In iOS 14–16, `ObservableObject` relies on `objectWillChange`. Any change to any `@Published` property notifies **all** observing views, regardless of whether they consume that property.

### Invalidation Storms
```swift
class OrderFormViewModel: ObservableObject {
    @Published var name: String = ""
    @Published var email: String = ""
    @Published var typingCharacterCount: Int = 0 // ⚠️ Fires on every keystroke!
}
```
Whenever `typingCharacterCount` updates, every view observing `OrderFormViewModel` evaluates its `body`.

### Mitigation Strategies:
1. **Split ViewModels**: Decouple high-frequency state (`typingCharacterCount`, scroll offsets) from low-frequency state (`name`, `email`) into separate `ObservableObject` classes.
2. **Debounce Inputs**: Apply `.debounce(for: .milliseconds(300), scheduler: DispatchQueue.main)` before updating `@Published` properties.
3. **State Slicing**: Wrap sub-components with explicit views consuming only the required value or binding.
