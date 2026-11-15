import SwiftUI
import UIKit

// Eval 5 Fixture: Plurigent Anti-Patterns
// 1. Hardcoded iPhone Duo dimensions (466 pt outer, 951 pt inner, 475.5 pt fold)
// 2. Symmetric safe-area doubling assumption (safeAreaInsets.left * 2)

struct DimensionBranchingView: View {
    var body: some View {
        GeometryReader { proxy in
            if proxy.size.width == 466 {
                Text("Outer display detected via hardcoded constant")
            } else if proxy.size.width >= 951 {
                Text("Inner display detected via hardcoded constant")
            } else {
                Text("Default")
            }
        }
    }
}

class InsetDoublingViewController: UIViewController {
    override func viewDidLayoutSubviews() {
        super.viewDidLayoutSubviews()
        // Anti-pattern: assumes opposite insets are equal
        let usableWidth = view.bounds.width - (view.safeAreaInsets.left * 2)
        print("Calculated width: \(usableWidth)")
    }
}
