// FaultThrashingNPlusOne.swift
// Test fixture containing fault thrashing, missing batch size, and reactive query churn

import Foundation
import CoreData
import SwiftUI
import SwiftData

final class ReportGenerator {
    let context: NSManagedObjectContext
    
    init(context: NSManagedObjectContext) {
        self.context = context
    }
    
    // 1. CD_FETCH_MISSING_BATCH_SIZE
    func fetchAllLogs() throws -> [NSManagedObject] {
        let request: NSFetchRequest<NSManagedObject> = NSFetchRequest(entityName: "LogEntry")
        // VIOLATION: Missing request.fetchBatchSize
        return try context.fetch(request)
    }
    
    // 2. CD_FAULT_THRASHING_N_PLUS_ONE
    func generateDepartmentSummaries(departments: [NSManagedObject]) {
        for dept in departments {
            if let employees = dept.value(forKey: "employees") as? [NSManagedObject] {
                for emp in dept.employees { // VIOLATION: nested traversal without relationshipKeyPathsForPrefetching
                    print(emp)
                }
            }
        }
    }
}

// 3. REACTIVE_QUERY_SEARCH_THRASH
struct SearchListView: View {
    @State private var searchText = ""
    @Query private var items: [Item]
    
    var body: some View {
        List(items) { item in
            Text(item.name)
        }
        .searchable(text: $searchText) // VIOLATION: dynamic search without debounce
    }
}

@Model
final class Item {
    var name: String
    init(name: String) { self.name = name }
}
