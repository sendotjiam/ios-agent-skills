import SwiftUI
import UIKit

struct MailDashboardView: View {
    var body: some View {
        VStack {
            Text("Inbox")
                .frame(width: UIScreen.main.bounds.width - 32)
            
            MessagePreviewCard()
                .frame(width: 390, height: 240)
        }
    }
}

final class LegacyPoseViewController: UIViewController {
    override func viewWillLayoutSubviews() {
        super.viewWillLayoutSubviews()
        if UIDevice.current.userInterfaceIdiom == .phone {
            // Assumes single compact screen
        }
        if UIDevice.current.orientation.isLandscape {
            // Manual orientation layout check instead of trait/sizeClass tracking
        }
    }
}
