# Batch Operations, High-Throughput Ingestion & Memory Reclamation

Attempting to mutate or delete thousands of records using standard object-graph loops leads to rapid memory bloat, high CPU usage, and eventual JetSam / OOM termination. Core Data and SwiftData provide direct database-level batch APIs that bypass object materialization.

---

## 1. Batch Deletions: Row-by-Row vs Direct SQLite Execution

### 🔴 The Anti-Pattern: Individual Loop Deletions

```swift
// ❌ Disaster: 10,000 objects loaded into RAM, 10,000 SQL statements executed
let request: NSFetchRequest<LogEntry> = LogEntry.fetchRequest()
let entries = try context.fetch(request)
for entry in entries {
    context.delete(entry)
}
try context.save()
```

### ✅ Clean Solution (Core Data): `NSBatchDeleteRequest`

```swift
// ✅ Executes single SQL DELETE statement directly on SQLite disk storage
let fetchRequest: NSFetchRequest<NSFetchRequestResult> = LogEntry.fetchRequest()
fetchRequest.predicate = NSPredicate(format: "createdAt < %@", cutoffDate as NSDate)

let batchDelete = NSBatchDeleteRequest(fetchRequest: fetchRequest)
batchDelete.resultType = .resultTypeObjectIDs

let result = try context.execute(batchDelete) as? NSBatchDeleteResult
if let objectIDs = result?.result as? [NSManagedObjectID] {
    let changes = [NSDeletedObjectsKey: objectIDs]
    // Merge changes so in-memory viewContext stays in sync
    NSManagedObjectContext.mergeChanges(fromRemoteContextSave: changes, into: [context])
}
```

### ✅ Clean Solution (SwiftData iOS 18+): `delete(model:where:)`

```swift
// ✅ SwiftData 18 batch deletion
try modelContext.delete(
    model: LogEntry.self,
    where: #Predicate { $0.createdAt < cutoffDate }
)
```

---

## 2. High-Throughput Ingestion: Chunking & Memory Cleansing

When importing large data sets (e.g. 10,000+ API records):
1. **Never** import in a single monolithic transaction.
2. Group records into chunks (500–1,000 records).
3. Wrap each chunk in `@autoreleasepool` so ARC discards autoreleased SQLite strings/buffers.
4. Call `context.save()` and then immediately `context.reset()`.

### The Chunked Ingest Pattern

```swift
func importRecords(_ payloads: [RecordDTO], in context: NSManagedObjectContext) throws {
    let chunkSize = 500
    
    for i in stride(from: 0, to: payloads.count, by: chunkSize) {
        try autoreleasepool {
            let chunk = payloads[i..<min(i + chunkSize, payloads.count)]
            
            for dto in chunk {
                let obj = Record(context: context)
                obj.apply(dto)
            }
            
            try context.save()
            // Evict all managed objects from memory to release RAM
            context.reset()
        }
    }
}
```

---

## 3. High-Speed Bulk Insertion: `NSBatchInsertRequest`

For inserting raw data into Core Data without creating `NSManagedObject` instances:

```swift
let totalItems = 100_000
var index = 0

let batchInsert = NSBatchInsertRequest(
    entityName: "TelemetryEvent",
    managedObjectHandler: { managedObject in
        guard index < totalItems else { return true }
        let event = managedObject as! TelemetryEvent
        event.timestamp = Date()
        event.code = Int64(index)
        index += 1
        return false // continue inserting
    }
)

try context.execute(batchInsert)
```
`NSBatchInsertRequest` processes records up to **20x faster** than normal `NSManagedObject` instantiation and consumes a tiny fraction of memory.
