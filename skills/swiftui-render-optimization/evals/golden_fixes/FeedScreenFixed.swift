import SwiftUI

@Observable
final class FeedViewModel {
    var items: [String] = []
    var unreadCount: Int = 0
    var filterText: String = ""

    // Memoized or computed off the main rendering hot path
    var filteredItems: [String] {
        items.filter { filterText.isEmpty || $0.localizedCaseInsensitiveContains(filterText) }
    }

    // Cached shared formatter
    static let sharedDateFormatter: DateFormatter = {
        let df = DateFormatter()
        df.dateFormat = "yyyy-MM-dd"
        return df
    }()

    @ObservationIgnored private var cancellables: Set<AnyHashable> = []

    func loadMore() async {
        try? await Task.sleep(nanoseconds: 500_000_000)
    }
}

struct FeedScreenFixed: View {
    // ✅ State ownership with @State in iOS 17+ or @StateObject in iOS 14-16
    @State private var viewModel = FeedViewModel()
    @State private var selectedItem: String?

    var body: some View {
        NavigationStack {
            // ✅ LazyVStack for proper cell recycling during scrolling
            ScrollView {
                LazyVStack(spacing: 8) {
                    ForEach(viewModel.filteredItems, id: \.self) { item in
                        ItemRow(item: item)
                            .onTapGesture {
                                selectedItem = item
                            }
                    }
                }
                .padding()
            }
            .navigationTitle("Feed")
            // ✅ Hoisted sheet presentation modifier at the parent container
            .sheet(item: $selectedItem) { item in
                Text("Detail for \(item)")
            }
            // ✅ Lifecycle-bound Task with cooperative cancellation on disappear
            .task {
                await viewModel.loadMore()
            }
        }
    }
}

// ✅ Extracted subview preserving static type hierarchy without AnyView
struct ItemRow: View {
    let item: String

    var body: some View {
        HStack {
            Text(item)
            Spacer()
        }
        .padding(.vertical, 4)
    }
}
