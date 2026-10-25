# Migration Safety, `VersionedSchema` & `SchemaMigrationPlan`

Schema migrations in persistent applications must be deterministic, non-destructive, and non-blocking. A failed schema migration can cause permanent user data loss or unrecoverable startup crashes (`NSMigrationMissingSourceModelException`, `fatalError("Failed to initialize ModelContainer")`).

---

## 1. Lightweight vs Custom Migrations

### When Lightweight Migration Works Automatically:
- Adding a new **optional** attribute.
- Adding a new **non-optional** attribute with a defined **default value**.
- Removing an attribute or entity.
- Renaming an attribute using `@Attribute(originalName: "oldName")` (SwiftData) or setting the **Renaming Identifier** in Xcode's Core Data Data Model Inspector.
- Changing an attribute from non-optional to optional.

### When Lightweight Migration Fails (Requires Custom Migration Stage):
- Changing the data type of an attribute (e.g. `Int32` $\rightarrow$ `String` or `String` $\rightarrow$ `URL`).
- Splitting one entity into two related entities.
- Merging two entities into one.
- Adding a non-optional attribute without a default value.
- Computing transformed values during migration.

---

## 2. SwiftData Versioning: `VersionedSchema` and `SchemaMigrationPlan`

In SwiftData, schemas are explicitly versioned using static enums conforming to `VersionedSchema`.

### Step 1: Declare Versioned Schemas

```swift
import SwiftData

enum AppSchemaV1: VersionedSchema {
    static var versionIdentifier = Schema.Version(1, 0, 0)
    static var models: [any PersistentModel.Type] {
        [User.self]
    }
    
    @Model
    final class User {
        var id: UUID
        var fullName: String
        
        init(id: UUID = UUID(), fullName: String) {
            self.id = id
            self.fullName = fullName
        }
    }
}

enum AppSchemaV2: VersionedSchema {
    static var versionIdentifier = Schema.Version(2, 0, 0)
    static var models: [any PersistentModel.Type] {
        [User.self]
    }
    
    @Model
    final class User {
        var id: UUID
        var firstName: String
        var lastName: String
        
        init(id: UUID = UUID(), firstName: String, lastName: String) {
            self.id = id
            self.firstName = firstName
            self.lastName = lastName
        }
    }
}
```

### Step 2: Implement the `SchemaMigrationPlan`

```swift
enum AppMigrationPlan: SchemaMigrationPlan {
    static var schemas: [any VersionedSchema.Type] {
        [AppSchemaV1.self, AppSchemaV2.self]
    }
    
    static var stages: [MigrationStage] {
        [migrateV1toV2]
    }
    
    static let migrateV1toV2 = MigrationStage.custom(
        fromVersion: AppSchemaV1.self,
        toVersion: AppSchemaV2.self,
        willMigrate: { context in
            // Pre-migration checks or cleanup
        },
        didMigrate: { context in
            // Transform existing data
            let descriptor = FetchDescriptor<AppSchemaV2.User>()
            let users = try context.fetch(descriptor)
            for user in users {
                // Perform data split or mapping
            }
            try context.save()
        }
    )
}
```

### Step 3: Wire into `ModelContainer`

```swift
let container = try ModelContainer(
    for: AppSchemaV2.User.self,
    migrationPlan: AppMigrationPlan.self
)
```

---

## 3. Preventing Startup Watchdog Kills (`0x8badf00d`)

When databases grow large (>50MB), running schema migrations synchronously on the main thread during `application(_:didFinishLaunchingWithOptions:)` or SwiftUI `App.init` can take several seconds. iOS terminates apps taking more than ~15-20 seconds to finish launching with exception `0x8badf00d`.

### Core Data Asynchronous Store Loading

```swift
class PersistenceController {
    static let shared = PersistenceController()
    let container: NSPersistentContainer
    
    @Published var isReady: Bool = false

    init() {
        container = NSPersistentContainer(name: "AppModel")
        
        // Enable automatic lightweight migration
        guard let description = container.persistentStoreDescriptions.first else { return }
        description.shouldMigrateStoreAutomatically = true
        description.shouldInferMappingModelAutomatically = true
        
        // Load in background
        container.loadPersistentStores { description, error in
            if let error = error {
                fatalError("Unresolved store loading error: \(error)")
            }
            DispatchQueue.main.async {
                self.container.viewContext.automaticallyMergesChangesFromParent = true
                self.isReady = true
            }
        }
    }
}
```

Display a lightweight splash or migration loading view until `isReady == true`.
