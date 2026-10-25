import SwiftUI

struct UserProfile {
    var id: String
    var name: String
    var avatarURL: String
}

struct UserEditorView: View {
    let user: UserProfile
    // ⚠️ ISSUE 1: @State initialized in init() from parameter causing stale state trap
    @State private var name: String
    @State private var selectedBadge: String?

    init(user: UserProfile) {
        self.user = user
        _name = State(initialValue: user.name)
        // ⚠️ ISSUE 2: Side-effects / analytics executed in view init()
        print("Logged screen event: UserEditorView initialized")
    }

    var body: some View {
        Form {
            TextField("Name", text: $name)

            ForEach(["Bronze", "Silver", "Gold"], id: \.self) { badge in
                Text(badge)
                    // ⚠️ ISSUE 3: Sheet presentation modifier inside ForEach row
                    .sheet(item: $selectedBadge) { item in
                        Text("Badge Details: \(item)")
                    }
            }
        }
        // ⚠️ ISSUE 4: Unstructured Task in onAppear without automatic cancellation
        .onAppear {
            Task {
                try? await Task.sleep(nanoseconds: 1_000_000_000)
            }
        }
    }
}

extension String: @retroactive Identifiable {
    public var id: String { self }
}
