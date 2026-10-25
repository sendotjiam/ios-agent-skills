import SwiftUI

class FeedViewModel: ObservableObject {
    @Published var items: [String] = []
    @Published var unreadCount: Int = 0
    var cancellables: Set<AnyHashable> = []

    func loadMore() async {
        try? await Task.sleep(nanoseconds: 500_000_000)
    }
}

struct FeedScreenBad: View {
    // ⚠️ CRITICAL: Inline @ObservedObject instantiation recreates VM on every parent render
    @ObservedObject var viewModel = FeedViewModel()
    
    @State private var filterText: String
    @State private var selectedItem: String?

    // ⚠️ CRITICAL: Initializing @State in init() from parameter
    init(initialFilter: String = "") {
        _filterText = State(initialValue: initialFilter)
    }

    var body: some View {
        // ⚠️ LOW: Leftover debug print
        let _ = Self._printChanges()

        NavigationView {
            // ⚠️ MEDIUM: Eager VStack in ScrollView instead of LazyVStack or List
            ScrollView {
                VStack {
                    // ⚠️ HIGH: Heavy computation and DateFormatter in body
                    let formatter = DateFormatter()
                    let _ = formatter.dateFormat = "yyyy-MM-dd"
                    let sortedItems = viewModel.items.sorted().filter { $0.contains(filterText) }

                    ForEach(sortedItems, id: \.self) { item in
                        // ⚠️ HIGH: AnyView type erasure
                        makeItemRow(item: item)
                            // ⚠️ HIGH: Sheet modifier placed inside ForEach row
                            .sheet(item: $selectedItem) { item in
                                Text("Detail for \(item)")
                            }
                    }
                }
            }
            // ⚠️ HIGH: Unstructured Task in onAppear
            .onAppear {
                Task {
                    await viewModel.loadMore()
                }
            }
            // ⚠️ MEDIUM: Unscoped implicit animation
            .animation(.easeInOut)
        }
    }

    private func makeItemRow(item: String) -> AnyView {
        AnyView(
            HStack {
                Text(item)
                Spacer()
            }
        )
    }
}

extension String: @retroactive Identifiable {
    public var id: String { self }
}
