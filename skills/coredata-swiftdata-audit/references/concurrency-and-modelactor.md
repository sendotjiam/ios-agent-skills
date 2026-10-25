# Core Data & SwiftData Concurrency and `@ModelActor`

Thread confinement and actor isolation are the most critical correctness invariants in Apple persistence frameworks. Both Core Data (`NSManagedObjectContext`) and SwiftData (`ModelContext`) are **strictly thread-confined** and non-`Sendable`. Accessing a managed object or context from the wrong execution context causes intermittent race conditions, internal cache corruption, or immediate `EXC_BAD_ACCESS` crashes.

---

## 1. Concurrency Architecture: Core Data vs SwiftData

| Dimension | Core Data (`NSManagedObjectContext`) | SwiftData (`ModelContext` / `@ModelActor`) |
|---|---|---|
| **Thread Model** | Queue/Thread confinement (`.mainQueueConcurrencyType` vs `.privateQueueConcurrencyType`) | Actor isolation (`@MainActor` vs custom `@ModelActor`) |
| **Execution Block** | `context.perform { ... }` (async) / `context.performAndWait { ... }` (sync) | Async actor method invocation (`await actor.doWork()`) |
| **Main Context** | `persistentContainer.viewContext` (Main thread only) | `container.mainContext` / `@Environment(\.modelContext)` (MainActor only) |
| **Cross-Thread Identity** | `NSManagedObjectID` (Thread-safe & `Sendable`) | `PersistentIdentifier` (Thread-safe & `Sendable`) |
| **Swift 6 Sendability** | `NSManagedObject`: **Non-Sendable** | `@Model class`: **Non-Sendable** |

---

## 2. Core Data Concurrency Violations & Remediation

### 🔴 Anti-Pattern: Accessing Context Outside `perform`

```swift
// ❌ CRITICAL: Unconfined background context mutation
DispatchQueue.global(qos: .background).async {
    let context = persistentContainer.newBackgroundContext()
    let user = User(context: context)
    user.name = "Alice"
    try? context.save() // Crash or SQLite deadlock
}
```

### ✅ Clean Solution: `perform` and `performAndWait`

```swift
// ✅ Enclose all context operations inside perform
let context = persistentContainer.newBackgroundContext()
context.perform {
    let user = User(context: context)
    user.name = "Alice"
    do {
        try context.save()
    } catch {
        // Handle error
    }
}

// Or modern async/await wrapper:
await context.perform {
    // Isolated to the context's private queue
}
```

---

## 3. Passing Objects Across Boundaries

`NSManagedObject` and `@Model` instances hold internal references to their owning context. If passed across `Task` or thread boundaries, two threads concurrently inspect or mutate the object's fault status or row cache.

### 🔴 Anti-Pattern: Leaking Models into Detached Tasks

```swift
// ❌ Passing raw managed object into Task
func exportUser(_ user: User) {
    Task.detached {
        print(user.name) // Thread violation: reading fault on background thread
    }
}
```

### ✅ Clean Solution: Pass Identifiers

```swift
// ✅ Core Data: Pass NSManagedObjectID
func exportUser(_ user: User) {
    let objectID = user.objectID
    Task.detached {
        let bgContext = persistentContainer.newBackgroundContext()
        await bgContext.perform {
            guard let bgUser = try? bgContext.existingObject(with: objectID) as? User else { return }
            print(bgUser.name)
        }
    }
}

// ✅ SwiftData: Pass PersistentIdentifier
func exportItem(_ item: Item) {
    let id = item.persistentModelID
    Task {
        await backgroundWorker.processItem(with: id)
    }
}
```

---

## 4. SwiftData Concurrency & `@ModelActor`

SwiftData unifies persistence with Swift Concurrency via the `@ModelActor` macro. An actor decorated with `@ModelActor` automatically synthesizes an isolated `ModelContext` running on its own dedicated serial executor.

### Standard Background Worker Pattern

```swift
import SwiftData

@ModelActor
actor ItemProcessor {
    func batchProcess(with ids: [PersistentIdentifier]) throws {
        for id in ids {
            if let item = modelContext.model(for: id) as? Item {
                item.status = "processed"
                item.processedAt = Date()
            }
        }
        try modelContext.save()
    }
    
    func insertItems(titles: [String]) throws {
        for title in titles {
            let item = Item(title: title)
            modelContext.insert(item)
        }
        try modelContext.save()
    }
}
```

### Invocation from SwiftUI or View Models

```swift
@MainActor
final class ItemViewModel: ObservableObject {
    private let container: ModelContainer
    private lazy var processor = ItemProcessor(modelContainer: container)
    
    init(container: ModelContainer) {
        self.container = container
    }
    
    func triggerBackgroundImport(payloads: [String]) {
        Task {
            do {
                try await processor.insertItems(titles: payloads)
            } catch {
                print("Import failed: \(error)")
            }
        }
    }
}
```

---

## 5. Concurrency Debugging Flag

Enable Apple's internal runtime assertion checker in Xcode Scheme -> Run -> Arguments:

```
-com.apple.CoreData.ConcurrencyDebug 1
```

When this flag is active, any attempt to access an `NSManagedObject` or `NSManagedObjectContext` outside its designated queue triggers an immediate breakpoint crash with a clear stack trace (`_checkCoreDataConcurrency_flag`).
