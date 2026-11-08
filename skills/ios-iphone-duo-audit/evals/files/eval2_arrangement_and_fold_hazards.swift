import SwiftUI

struct MediaPlayerFoldView: View {
    let columns = [GridItem(.flexible()), GridItem(.flexible()), GridItem(.flexible())]

    var body: some View {
        ScrollView {
            ArrangementView {
                NavigationSplitView {
                    List(0..<10, id: \.self) { idx in
                        Text("Track \(idx)")
                    }
                } detail: {
                    Text("Player")
                }
            } secondary: {
                LazyVGrid(columns: columns) {
                    ForEach(0..<9, id: \.self) { item in
                        RoundedRectangle(cornerRadius: 12)
                            .frame(height: 100)
                    }
                }
            }
        }
    }
}
