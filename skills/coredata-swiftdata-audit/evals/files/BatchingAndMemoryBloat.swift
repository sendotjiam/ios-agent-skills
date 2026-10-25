// BatchingAndMemoryBloat.swift
// Test fixture containing row-by-row batch loops, accumulator leaks, and missing auto-merge

import Foundation
import CoreData

final class DataPurgeService {
    let container: NSPersistentContainer
    
    init(container: NSPersistentContainer) {
        self.container = container
        // 3. CD_MISSING_AUTO_MERGE
        let bgContext = container.newBackgroundContext() // VIOLATION: no automaticallyMergesChangesFromParent
    }
    
    // 1. CD_LOOP_ROW_BY_ROW_DELETE
    func purgeOldLogs(logs: [NSManagedObject], context: NSManagedObjectContext) throws {
        for log in logs {
            context.delete(log) // VIOLATION: row-by-row delete instead of NSBatchDeleteRequest
        }
        try context.save()
    }
    
    // 2. CD_UNBOUNDED_BATCH_IMPORT
    func importHugePayload(items: [String], context: NSManagedObjectContext) throws {
        for item in items {
            let entity = NSEntityDescription.insertNewObject(forEntityName: "Item", into: context)
            entity.setValue(item, forKey: "name")
            try context.save() // VIOLATION: missing context.reset() or autoreleasepool in loop
        }
    }
}
