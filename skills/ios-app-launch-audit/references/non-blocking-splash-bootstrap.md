# Non-Blocking Splash & Asynchronous Bootstrap Architecture

## Problem: Synchronous SDK & Store Loading
When `FirebaseApp.configure()`, `SentrySDK.start()`, and database migrations are invoked directly inside `didFinishLaunchingWithOptions`, they execute serially on the main thread, holding up the RunLoop and keeping the launch screen visible.

---

## Solution: Staged Bootstrap Pipeline

```swift
import SwiftUI

@main
struct ModernApp: App {
    @State private var isBootstrapped = false

    var body: some Scene {
        WindowGroup {
            ZStack {
                if isBootstrapped {
                    MainTabView()
                } else {
                    LaunchSkeletonView()
                }
            }
            .task {
                await bootstrapApp()
            }
        }
    }

    private func bootstrapApp() async {
        // Stage 1: Async database load
        await PersistenceController.shared.loadStoresAsync()

        // Stage 2: Background SDK dispatch
        Task.detached(priority: .utility) {
            FirebaseApp.configure()
            SentrySDK.start { _ in }
        }

        withAnimation {
            isBootstrapped = true
        }
    }
}
```
