import SwiftUI
import Combine

// Protocol lacking : AnyObject
protocol UnboundFilterDelegate {
    func didChangeFilter()
}

// Class with delegate to unbound protocol
final class FilterCoordinator {
    var filterDelegate: UnboundFilterDelegate?
}

// SwiftUI struct View capturing self - NO ARC retain cycle possible for value types
struct FeedCardView: View {
    @State private var text: String = ""
    private var cancellables = Set<AnyCancellable>()

    var body: some View {
        Text(text)
            .onAppear {
                // Should NOT flag COMBINE_SINK_CYCLE because self is a struct (value type)
                Just("Hello")
                    .sink { value in
                        print(self.text, value)
                    }
                    .store(in: &cancellables)

                // Should NOT flag GCD_DELAYED_RETENTION because self is a struct
                DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
                    print(self.text)
                }
            }
    }
}
