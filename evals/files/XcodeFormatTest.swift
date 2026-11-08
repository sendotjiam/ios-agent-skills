import Foundation
import SwiftUI

struct XcodeFormatTestView: View {
    var body: some View {
        VStack {
            // High / Critical violation
            Button("Deadlock") {
                DispatchQueue.main.sync {
                    print("deadlock risk")
                }
            }
            // Warning violation
            AnyView(Text("Type erased"))
        }
    }
}
