---
name: coredata-swiftdata-audit
description: Comprehensive Core Data & SwiftData persistence auditor for iOS, iPadOS, and macOS apps. Audits codebases for background context concurrency violations, missing perform/performAndWait, cross-actor raw model leaks, SwiftData @ModelActor isolation, fault thrashing, N+1 query loops, missing fetchBatchSize, row-by-row batch mutations, unbounded memory accumulation in ingestion loops, CloudKit mirroring traps (missing reciprocal relationship inverses, unsupported unique constraints, unpinned binary bloats), multi-context merge omissions, unversioned schema migrations, and main-thread synchronous store loading. Use whenever auditing iOS persistence layers, troubleshooting Core Data/SwiftData crashes, diagnosing EXC_BAD_ACCESS or JetSam/OOM memory kills, resolving CloudKit sync failures, or profiling SQLite performance with SQLDebug and Instruments.
---

# Core Data & SwiftData Persistence Audit Guide

This skill guides deep static and diagnostic audits of iOS, iPadOS, and macOS persistence layers covering **Core Data** and **SwiftData** (iOS 17 & 18+). It systematically identifies concurrency violations, performance killers (fault thrashing, N+1 query cascades), migration catastrophes, CloudKit sync invariants, and unbounded memory bloat.

---

## 1. Audit Taxonomy & Severity Tiers

When inspecting code or profiling diagnostic graphs, classify all persistence findings into four severity tiers:

### 🔴 Critical (Concurrency Crashes, Data Corruption & CloudKit Sync Failure)
- **Thread Unconfined Context Access**: Mutating or fetching `NSManagedObjectContext` without enclosing `context.perform { ... }` or `context.performAndWait { ... }`, particularly inside `DispatchQueue.global().async` or unisolated functions.
- **Cross-Actor / Cross-Thread Model Passing**: Passing raw `NSManagedObject` or `@Model` instances across `Task`, `Task.detached`, or actor boundaries (violates thread confinement; must pass `NSManagedObjectID` or `PersistentIdentifier` and re-fetch).
- **Background `viewContext` / `mainContext` Misuse**: Invoking `container.viewContext` or `container.mainContext` from non-`@MainActor` functions, background queues, or detached Tasks.
- **Unisolated `ModelContext`**: Manually instantiating `ModelContext(container)` inside background concurrency scopes without `@ModelActor` or actor boundary confinement.
- **CloudKit Missing Relationship Inverses**: Declaring to-one or to-many relationships without an explicit reciprocal `inverse:` on models synced with `NSPersistentCloudKitContainer` or SwiftData CloudKit sync.
- **CloudKit Unsupported Unique Constraints**: Using `@Attribute(.unique)` or Core Data entity constraints on CloudKit-synced models (CloudKit does not support unique constraints and fails sync).

### 🟠 High (Batch Inefficiency, Unbounded Memory Bloat & Lost Updates)
- **Row-by-Row Loop Deletions**: Deleting records in a `for-in` loop with `context.delete(item)` instead of executing `NSBatchDeleteRequest` (Core Data) or `delete(model:where:)` (SwiftData iOS 18).
- **Unbounded Ingestion Memory Leaks**: Importing large datasets (>500 items) in a loop without `@autoreleasepool` wrapping, periodic saves, and `context.reset()`, triggering system JetSam / OOM kills.
- **Missing Auto-Merge Configuration**: Initializing background contexts via `newBackgroundContext()` without setting `viewContext.automaticallyMergesChangesFromParent = true`, causing UI desynchronization.
- **Large Inline Binary Storage**: Storing binary `Data` > 1MB inline without `@Attribute(.externalStorage)` or `allowsExternalBinaryDataStorage`, causing massive SQLite and CloudKit payload bloat.

### 🟡 Medium (Fault Thrashing & Reactive View Churn)
- **N+1 Fault Thrashing Loops**: Iterating over related entities in a loop without configuring `relationshipKeyPathsForPrefetching` (Core Data) or `FetchDescriptor(prefetch: ...)` (SwiftData).
- **Missing `fetchBatchSize`**: Executing fetch requests on large tables without setting `request.fetchBatchSize = 20` (or 2x screen capacity), materializing all matching records in RAM at once.
- **Reactive Query Search Thrashing**: Binding dynamic `@Query` or `@FetchRequest` predicates directly to SwiftUI search text without debouncing, hammering SQLite on every keystroke.
- **SwiftData Non-Transient UI State**: Storing transient UI or runtime caching properties on `@Model` classes without `@Transient`, causing unnecessary Swift Observation re-renders.

### 🔵 Low (Store Hygiene & Startup Latency)
- **Synchronous Store Loading on Main Thread**: Calling `container.loadPersistentStores` synchronously inside `AppDelegate` or `App.init`, risking watchdog termination (`0x8badf00d`) during heavy migrations.
- **Disk Container Leaks in `#Preview`**: Instantiating persistent disk-backed `ModelContainer` or `NSPersistentContainer` in SwiftUI previews instead of in-memory stores (`isStoredInMemoryOnly: true`).
- **Unversioned Schema Changes**: Modifying `@Model` entities without `VersionedSchema` or `SchemaMigrationPlan` in production apps.

---

## 2. Automated Fast-Scan (CLI Pre-Scan)

Before conducting manual AST inspection, run the bundled zero-dependency Python scanner to locate persistence hazards across the project in seconds:

```bash
# Output colored table summary of persistence hazards
python3 skills/coredata-swiftdata-audit/scripts/scan_coredata_swiftdata.py <path/to/ios/project>

# Export structured Markdown report for pull requests or reviews
python3 skills/coredata-swiftdata-audit/scripts/scan_coredata_swiftdata.py <path/to/ios/project> --format markdown -o persistence_report.md

# Machine-readable JSON output
python3 skills/coredata-swiftdata-audit/scripts/scan_coredata_swiftdata.py <path/to/ios/project> --format json
```

The scanner detects:
- Context thread-hopping and unconfined `save`/`fetch`
- Raw model leaking across `Task` boundaries
- Unisolated `ModelContext` and `mainContext` misuse in background tasks
- CloudKit missing inverses and unique constraint conflicts
- Row-by-row deletion and update loops lacking batch operations
- Loop imports missing `@autoreleasepool` and `context.reset()`
- Fetch requests missing `fetchBatchSize` and loop fault thrashing
- Missing `automaticallyMergesChangesFromParent`
- SwiftUI `#Preview` disk container leaks

---

## 3. Step-by-Step Audit Workflow

### Step 1: Thread Concurrency & Model Actor Audit
1. Verify all background Core Data operations are wrapped in `context.perform` or `context.performAndWait`.
2. Inspect async functions and Tasks: Ensure raw models are never passed across actor boundaries. Only pass `NSManagedObjectID` (Core Data) or `PersistentIdentifier` (SwiftData).
3. Verify that all background SwiftData workers are implemented as `@ModelActor` actors.
4. *Reference:* [concurrency-and-modelactor.md](file:///Users/sendotjiamis/Documents/ios-agent-skills/skills/coredata-swiftdata-audit/references/concurrency-and-modelactor.md).

### Step 2: Fault Thrashing & Prefetching Audit
1. Audit all `for ... in` loops accessing entity relationships: verify `relationshipKeyPathsForPrefetching` is configured on the fetch request.
2. Check table and collection view datasources: verify `fetchBatchSize` is configured on all `NSFetchRequest` instances.
3. Check SwiftUI `@Query` usage: ensure search text filters are debounced before updating predicates.
4. *Reference:* [fault-thrashing-and-prefetching.md](file:///Users/sendotjiamis/Documents/ios-agent-skills/skills/coredata-swiftdata-audit/references/fault-thrashing-and-prefetching.md).

### Step 3: Batch Operations & Memory Reclamation Audit
1. Search for bulk deletion patterns: replace loops calling `context.delete()` with `NSBatchDeleteRequest` (Core Data) or `modelContext.delete(model:where:)` (SwiftData 18).
2. Inspect ingestion and sync loops: ensure transactions are broken into 500-1000 item chunks wrapped in `@autoreleasepool` with `context.save()` and `context.reset()`.
3. *Reference:* [batch-operations-and-memory.md](file:///Users/sendotjiamis/Documents/ios-agent-skills/skills/coredata-swiftdata-audit/references/batch-operations-and-memory.md).

### Step 4: CloudKit & Schema Migration Audit
1. If using `NSPersistentCloudKitContainer` or SwiftData CloudKit sync:
   - Check that every `@Relationship` has an explicit `inverse:` defined.
   - Verify no `@Attribute(.unique)` or Core Data entity constraints exist.
   - Verify large binary properties have `@Attribute(.externalStorage)` enabled.
2. Check schema migration safety:
   - Verify changes are handled by `VersionedSchema` and `SchemaMigrationPlan`.
   - Ensure store loading is performed asynchronously to avoid watchdog kills.
3. *References:* [cloudkit-sync-and-multi-context.md](file:///Users/sendotjiamis/Documents/ios-agent-skills/skills/coredata-swiftdata-audit/references/cloudkit-sync-and-multi-context.md) and [migration-safety-and-schemaplans.md](file:///Users/sendotjiamis/Documents/ios-agent-skills/skills/coredata-swiftdata-audit/references/migration-safety-and-schemaplans.md).

---

## 4. Diagnostics & Tooling Reference

### Xcode Launch Arguments
Add these to Scheme -> Run -> Arguments:
- `-com.apple.CoreData.ConcurrencyDebug 1`: Asserts and crashes on any cross-thread context violation.
- `-com.apple.CoreData.SQLDebug 3`: Dumps full SQL statements, bind variables, query durations, and row counts.

### Instruments Profiling
- Use **Product -> Profile -> Core Data** to track Fault Trips, Fetches, and Saves over time.
- *Reference:* [instruments-and-sql-tracing.md](file:///Users/sendotjiamis/Documents/ios-agent-skills/skills/coredata-swiftdata-audit/references/instruments-and-sql-tracing.md).
