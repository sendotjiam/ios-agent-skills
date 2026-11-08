import UIKit

final class AnalyticsAppDelegate: UIResponder, UIApplicationDelegate {
    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
    ) -> Bool {
        // HAZARD 1: Synchronous Firebase initialization
        FirebaseApp.configure()

        // HAZARD 2: Synchronous Sentry initialization
        SentrySDK.start { options in
            options.dsn = "https://examplePublicKey@o0.ingest.sentry.io/0"
        }

        return true
    }
}

// Stubs for scanning
final class FirebaseApp {
    static func configure() {}
}

final class SentrySDK {
    static func start(configure: (SentryOptions) -> Void) {}
}

final class SentryOptions {
    var dsn: String = ""
}
