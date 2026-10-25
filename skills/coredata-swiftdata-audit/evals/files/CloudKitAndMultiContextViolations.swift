// CloudKitAndMultiContextViolations.swift
// Test fixture containing CloudKit inverse omissions, unique constraint traps, inline binary bloat, and preview leaks

import Foundation
import SwiftData
import SwiftUI
import CoreData

// Active CloudKit sync container
final class CloudStoreManager {
    let cloudContainer: NSPersistentCloudKitContainer
    
    init() {
        self.cloudContainer = NSPersistentCloudKitContainer(name: "CloudStore")
    }
    
    // 5. CD_SYNCHRONOUS_STORE_LOAD
    func application(_ application: Any, didFinishLaunchingWithOptions launchOptions: Any?) -> Bool {
        cloudContainer.loadPersistentStores(completionHandler: { desc, err in // VIOLATION: synchronous on main thread
            print("Loaded")
        })
        return true
    }
}

// 1. CLOUDKIT_MISSING_RELATIONSHIP_INVERSE
@Model
final class Author {
    var name: String
    // VIOLATION: CloudKit requires explicit inverse
    @Relationship(deleteRule: .cascade)
    var books: [Book] = []
    
    init(name: String) { self.name = name }
}

@Model
final class Book {
    var title: String
    // 2. CLOUDKIT_UNSUPPORTED_UNIQUE_CONSTRAINT
    @Attribute(.unique) var isbn: String // VIOLATION: unique constraint under CloudKit
    
    // 3. PERSISTENCE_LARGE_BINARY_INLINE
    var coverImageData: Data // VIOLATION: inline binary without @Attribute(.externalStorage)
    
    // 6. SWIFTDATA_UNMARKED_TRANSIENT_PROPERTY
    var cachedThumbnail: UIImage? // VIOLATION: UI state without @Transient
    
    init(title: String, isbn: String, coverImageData: Data) {
        self.title = title
        self.isbn = isbn
        self.coverImageData = coverImageData
    }
}

// 4. PERSISTENCE_PREVIEW_DISK_LEAK
#Preview {
    let container = try! ModelContainer(for: Book.self) // VIOLATION: disk store in preview
    return Text("Preview")
        .modelContainer(container)
}
