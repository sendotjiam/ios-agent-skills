import SwiftUI

struct NoteEditorDuoView: View {
    var body: some View {
        NavigationStack {
            Text("Note Content")
                .toolbar {
                    ToolbarItem(placement: .topBarTrailing) {
                        Button("Save Draft") {
                            // Text-only button cannot render on vertical side bar
                        }
                    }
                    ToolbarItem(placement: .bottomBar) {
                        Spacer(minLength: 24)
                    }
                    ToolbarItem(placement: .topBarTrailing) {
                        Button(action: {}) {
                            Image(systemName: "ellipsis")
                        }
                    }
                }
        }
    }
}
