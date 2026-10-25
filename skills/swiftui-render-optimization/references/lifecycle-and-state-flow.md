# SwiftUI View Lifecycle & State Flow Hazards

View lifecycle in SwiftUI differs fundamentally from UIKit/AppKit. A SwiftUI view is a short-lived configuration struct, not a persistent object on screen. Misunderstanding this distinction causes severe performance regressions, infinite render loops, and memory leaks.

---

## 1. `init()` Execution Frequency vs View Lifetime

### The Core Principle
> **View `init()` is NOT the View's Lifetime.**
> A View's `init()` is called every time its parent evaluates `body`, even when the child's `body` is never invoked and its on-screen representation remains unchanged.

### Anti-Pattern: Heavy Work or Side Effects in `init()`
```swift
struct ProductDetailView: View {
    let productID: String

    init(productID: String) {
        self.productID = productID
        // ⚠️ ANTI-PATTERN: Fires on EVERY parent render pass!
        Analytics.trackScreenView("ProductDetail")
        NetworkClient.shared.preloadImages(for: productID)
    }

    var body: some View {
        Text("Product \(productID)")
    }
}
```

### The Fix: Defer to `.task` or `.onAppear`
```swift
struct ProductDetailView: View {
    let productID: String

    var body: some View {
        Text("Product \(productID)")
            .task(id: productID) {
                // ✅ Executes once when displayed, re-executes only if productID changes
                Analytics.trackScreenView("ProductDetail")
                await NetworkClient.shared.preloadImages(for: productID)
            }
    }
}
```

---

## 2. The `@State(initialValue:)` in `init()` Desynchronization Trap

### The Trap
```swift
struct UserEditor: View {
    @State private var name: String

    // ⚠️ BUG / ANTI-PATTERN:
    init(user: User) {
        _name = State(initialValue: user.name)
    }

    var body: some View {
        TextField("Name", text: $name)
    }
}
```

### Why it Fails:
- SwiftUI initializes `@State` memory **once** when the view node enters the view graph.
- If the parent passes an updated `user`, the new `user.name` in `init()` is **ignored** by `@State`.
- Developers frequently "fix" this by adding `.id(user.id)` to force complete view destruction, causing layout hitches and losing focus states.

### Correct Patterns:
1. **Use `@Binding`** if the parent owns the source of truth:
   ```swift
   struct UserEditor: View {
       @Binding var name: String
   }
   ```
2. **Synchronize via `.onChange`** if local draft state is strictly required:
   ```swift
   struct UserEditor: View {
       let user: User
       @State private var draftName: String = ""

       var body: some View {
           TextField("Name", text: $draftName)
               .onAppear { draftName = user.name }
               .onChange(of: user.name) { _, newName in draftName = newName }
       }
   }
   ```

---

## 3. Cooperative Cancellation: `.task` vs `.onAppear`

### Anti-Pattern: Leaking Tasks in `.onAppear`
```swift
.onAppear {
    // ⚠️ ANTI-PATTERN: Unstructured Task does not cancel when row is scrolled off-screen
    Task {
        let data = await API.fetchHeavyFeed()
        self.items = data
    }
}
```
In a fast-scrolling list, scrolling past 100 rows spawns 100 concurrent un-cancelled tasks competing for network sockets and CPU.

### The Fix: Native `.task`
```swift
.task {
    // ✅ Automatically receives cooperative cancellation (Task.isCancelled) on disappear
    guard let data = try? await API.fetchHeavyFeed() else { return }
    self.items = data
}
```

---

## 4. Preventing Cascading State Loops in `.onChange`

### The Loop Condition
```swift
.onChange(of: query) { _, newQuery in
    self.isLoading = true // State change 1
    self.results = compute(newQuery) // State change 2
}
.onChange(of: results) { _, newResults in
    self.filterCount = newResults.count // State change 3 (triggers parent render)
}
```
Cascading state modifications during a render phase cause SwiftUI to log:
`Modifying state during view update, this will cause undefined behavior.`

**Rule**: Derive secondary values inline as computed properties rather than storing redundant state that requires synchronizing via `.onChange`.

---

## 5. UIHostingController Reuse in UIKit Lists

When embedding SwiftUI views inside `UITableViewCell` or `UICollectionViewCell`:

- **iOS 16+**: Always prefer `UIHostingConfiguration`:
  ```swift
  cell.contentConfiguration = UIHostingConfiguration {
      MySwiftUIView(item: item)
  }
  ```
- **Pre-iOS 16**: If reusing `UIHostingController`, ensure child controllers are properly added via `addChild` / `didMove(toParent:)` and detach `rootView` bindings during `prepareForReuse()`.
