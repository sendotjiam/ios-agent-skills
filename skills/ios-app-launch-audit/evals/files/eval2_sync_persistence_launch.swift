import SwiftUI
import CoreData

@main
struct ProductionApp: App {
    let persistenceController: NSPersistentContainer

    init() {
        persistenceController = NSPersistentContainer(name: "DataModel")
        // HAZARD 1: Synchronous loadPersistentStores in @main init()
        persistenceController.loadPersistentStores { description, error in
            if let error = error {
                fatalError("Store load failed: \(error)")
            }
        }
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}

struct ContentView: View {
    var body: some View {
        Text("App Launched")
    }
}
