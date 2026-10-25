# CloudKit Syncing Constraints & Multi-Context Synchronization

Enabling iCloud synchronization via `NSPersistentCloudKitContainer` or SwiftData's automatic CloudKit integration introduces strict architectural constraints. Violating these rules results in immediate runtime crashes or silent synchronization termination.

---

## 1. CloudKit Persistence Invariants

### 🔴 Invariant 1: Mandatory Reciprocal Inverses
CloudKit constructs a graph of records (`CKRecord`) linked via `CKRecord.Reference`. To maintain referential integrity without orphan records, **every relationship in a CloudKit-synced schema must have an explicit inverse**.

```swift
// ❌ CRITICAL: Fails CloudKit schema validation!
@Model
final class Author {
    var name: String
    var books: [Book] = [] // Missing inverse
}

// ✅ Explicit reciprocal inverse
@Model
final class Author {
    var name: String
    @Relationship(inverse: \Book.author)
    var books: [Book] = []
}

@Model
final class Book {
    var title: String
    var author: Author?
}
```

### 🔴 Invariant 2: No Unique Constraints
CloudKit records are eventually consistent and can be inserted concurrently across multiple devices offline. SQLite unique constraints (`@Attribute(.unique)` in SwiftData or unique constraints in Core Data `.xcdatamodeld`) cannot be enforced by the CloudKit server.

```swift
// ❌ CRITICAL: CloudKit rejects or crashes on unique constraints
@Model
final class Contact {
    @Attribute(.unique) var email: String // FORBIDDEN under CloudKit
}
```

**Remediation for Unique Records**:
1. Remove `@Attribute(.unique)`.
2. Generate deterministic unique IDs (e.g. hashing user ID + email).
3. Perform client-side deduplication during query fetches or ingestion routines.

### 🔴 Invariant 3: Optional Attributes or Default Values
When a new property is introduced in an updated app version, older devices or CloudKit server records may lack this property during sync. Therefore, all non-primary attributes **must either be optional (`String?`) or have an explicit default value**.

```swift
// ❌ Will fail partial record sync
var score: Int 

// ✅ Supported
var score: Int = 0
var nickname: String?
```

### 🟠 Invariant 4: External Storage for Large Binary Bloats
CloudKit records have an absolute upper size limit of 1MB. Any entity property storing raw images or file buffers must be backed by `CKAsset`, configured via external storage:

```swift
// ✅ Uses CKAsset for storage outside the SQLite row
@Attribute(.externalStorage) var avatarData: Data?
```

---

## 2. Multi-Context Synchronization & Merge Policies

When background contexts write to SQLite, those changes are committed to the file on disk. The main `viewContext` / `mainContext` is unaware of these writes unless notified.

### Enabling Automatic Parent Merging

```swift
container.loadPersistentStores { description, error in
    // Critical: Auto-merge background saves into viewContext
    container.viewContext.automaticallyMergesChangesFromParent = true
}
```

### Selecting the Right Merge Policy

The default merge policy is `NSErrorMergePolicyType`, which throws an unhandled error when an in-memory object was modified while a background context was writing to the same entity row.

```swift
// In-memory changes trump disk changes
container.viewContext.mergePolicy = NSMergeByPropertyObjectTrumpMergePolicy

// Or: Disk changes trump in-memory changes (ideal for background sync)
container.viewContext.mergePolicy = NSMergeByPropertyStoreTrumpMergePolicy
```

### Listening for Remote Store Notifications

For multi-process or CloudKit remote updates, subscribe to `NSPersistentStoreRemoteChangeNotification`:

```swift
NotificationCenter.default.addObserver(
    forName: .NSPersistentStoreRemoteChange,
    object: container.persistentStoreCoordinator,
    queue: .main
) { notification in
    // Refresh active UI queries or reload data
}
```
