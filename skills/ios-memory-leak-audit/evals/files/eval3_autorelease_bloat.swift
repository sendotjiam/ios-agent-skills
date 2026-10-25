import UIKit
import CoreData

// Scenario 3: Memory Bloat, Missing @autoreleasepool, Unbounded Cache & Core Data

final class ImagePipelineService {
    // HAZARD 1: Unbounded dictionary cache without memory pressure purge
    var imageCache = [String: UIImage]()

    func processPhotoBatch(photoURLs: [URL]) {
        // HAZARD 2: High-iteration batch loop without @autoreleasepool
        for url in photoURLs {
            if let image = UIImage(contentsOfFile: url.path) {
                let key = url.lastPathComponent
                imageCache[key] = image
            }
        }
    }

    func syncCoreDataEntities(context: NSManagedObjectContext, queryCount: Int) {
        let request = NSFetchRequest<NSManagedObject>(entityName: "AssetEntity")
        // HAZARD 3: Core Data batch loop without context.reset()
        for page in 0..<queryCount {
            request.fetchOffset = page * 100
            request.fetchLimit = 100
            if let results = try? context.fetch(request) {
                for item in results {
                    _ = item.value(forKey: "data")
                }
            }
        }
    }
}
