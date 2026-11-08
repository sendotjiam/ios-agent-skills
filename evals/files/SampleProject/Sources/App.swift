import SwiftUI

@main
struct SampleApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}

struct ContentView: View {
    @State private var title = "Hello World"

    var body: some View {
        VStack {
            Text(title)
                .font(.headline)
            Button(action: {
                title = "Updated"
            }) {
                Label("Update Title", systemImage: "arrow.clockwise")
            }
            .frame(minWidth: 44, minHeight: 44)
        }
    }
}
