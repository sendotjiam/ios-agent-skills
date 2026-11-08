import UIKit

final class AppDelegate: UIResponder, UIApplicationDelegate {
    var window: UIWindow?

    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
    ) -> Bool {
        // HAZARD 1: Synchronous Data(contentsOf:) blocking main thread during launch
        let configUrl = Bundle.main.url(forResource: "remote_flags", withExtension: "json")!
        let data = try? Data(contentsOf: configUrl)

        // HAZARD 2: Obsolete synchronous UserDefaults disk flush
        UserDefaults.standard.set(true, forKey: "app_launched_once")
        UserDefaults.standard.synchronize()

        return true
    }
}
