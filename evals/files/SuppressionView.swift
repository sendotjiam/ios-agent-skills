import Foundation
import Combine
import SwiftUI

class SuppressionTestViewModel: ObservableObject {
    @Published var data: Data?
    @Published var count: Int = 0
    private var cancellables = Set<AnyCancellable>()
    private let url = URL(string: "https://example.com")!

    func runTests() {
        // Line 13: Suppressed via same-line comment
        let _ = try? Data(contentsOf: url) // ios-audit:ignore HANG-001

        // Line 16: NOT suppressed - MUST be detected as HANG-001
        let _ = try? Data(contentsOf: url)

        // Line 18: Suppressed via next-line directive
        // ios-audit:ignore-next-line COMBINE_ASSIGN_CYCLE
        Just(1).assign(to: \.count, on: self).store(in: &cancellables)

        // Line 23: NOT suppressed - MUST be detected as COMBINE_ASSIGN_CYCLE
        Just(2).assign(to: \.count, on: self).store(in: &cancellables)
    }
}
