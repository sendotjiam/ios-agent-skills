import Foundation
import CoreData

// HAZARD 1: Unsafe Sendable Escape concealing mutable dictionary data race
final class TokenStore: @unchecked Sendable {
    private var tokens: [String: String] = [:]

    func setToken(_ token: String, for service: String) {
        tokens[service] = token
    }

    func getToken(for service: String) -> String? {
        tokens[service]
    }
}

// HAZARD 2: Core Data Context / Thread Concurrency Violation
actor OrderProcessor {
    func processOrder(order: NSManagedObject) async {
        // HAZARD: Accessing NSManagedObject properties across actor/task boundary
        let orderID = order.value(forKey: "orderID") as? String
        let total = order.value(forKey: "totalAmount") as? Double
        print("Processing order: \(orderID ?? "") for \(total ?? 0)")
    }
}
