import SwiftUI

struct MessageItem: Hashable {
    var id: UUID
    var text: String
    var isRead: Bool
}

struct MessageHistoryView: View {
    var messages: [MessageItem]
    @State private var refreshTrigger = false

    var body: some View {
        ScrollView {
            // ⚠️ ISSUE 1: ForEach with id: \.self on mutated struct causing identity thrashing
            ForEach(messages, id: \.self) { message in
                // ⚠️ ISSUE 2: AnyView type erasure destroying structural diffing
                makeMessageRow(message)
            }
        }
        // ⚠️ ISSUE 3: Volatile explicit ID resetting view graph and dropping subview state
        .id(UUID())
    }

    private func makeMessageRow(_ message: MessageItem) -> AnyView {
        if message.isRead {
            return AnyView(Text(message.text).foregroundColor(.gray))
        } else {
            return AnyView(Text(message.text).bold())
        }
    }
}
