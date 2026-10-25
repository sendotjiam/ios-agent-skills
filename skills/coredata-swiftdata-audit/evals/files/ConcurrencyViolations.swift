// ConcurrencyViolations.swift
// Test fixture containing high-risk Core Data and SwiftData concurrency anti-patterns

import Foundation
import CoreData
import SwiftData

final class SyncManager {
    let persistentContainer: NSPersistentContainer
    let modelContainer: ModelContainer
    
    init(container: NSPersistentContainer, modelContainer: ModelContainer) {
        self.persistentContainer = container
        self.modelContainer = modelContainer
    }
    
    // 1. CD_THREAD_UNCONFINED_ACCESS
    func performUnconfinedSave() {
        DispatchQueue.global(qos: .background).async {
            let context = self.persistentContainer.newBackgroundContext()
            let user = NSEntityDescription.insertNewObject(forEntityName: "User", into: context)
            user.setValue("Bob", forKey: "name")
            try? context.save() // VIOLATION: missing perform/performAndWait
        }
    }
    
    // 2. CD_TASK_DETACHED_CONTEXT_LEAK
    func processUserDetached(userId: String) {
        let context = persistentContainer.viewContext
        Task.detached {
            let user = NSEntityDescription.insertNewObject(forEntityName: "User", into: context)
            try? context.save() // VIOLATION: detached task accessing context
        }
    }
    
    // 3. CD_VIEWCONTEXT_BACKGROUND_ACCESS
    func updateInAsyncBackground() async {
        // VIOLATION: Calling viewContext inside async method without @MainActor
        persistentContainer.viewContext.insert(NSManagedObject())
        try? persistentContainer.viewContext.save()
    }
    
    // 4. SWIFTDATA_UNISOLATED_MODEL_CONTEXT
    func unisolatedSwiftDataOperation() {
        Task {
            let context = ModelContext(self.modelContainer) // VIOLATION: unisolated ModelContext in Task
            try? context.save()
        }
    }
    
    // 5. SWIFTDATA_MAINCONTEXT_IN_TASK
    func backgroundMainContextAccess() {
        Task.detached {
            let count = self.modelContainer.mainContext // VIOLATION: mainContext inside detached task
            print(count)
        }
    }
}
