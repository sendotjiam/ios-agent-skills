import WebKit
import AVFoundation

// Scenario 4: WebKit Handlers, AVFoundation Observers, and CoreFoundation Leaks

final class MediaWebViewController: UIViewController, WKScriptMessageHandler {
    private var webView: WKWebView!
    private var player: AVPlayer?

    override func viewDidLoad() {
        super.viewDidLoad()
        setupWebView()
        setupPlayer()
        setupNotifications()
        allocateNativeBuffer()
    }

    private func setupWebView() {
        let config = WKWebViewConfiguration()
        // HAZARD 1: userContentController.add(self) strongly retains UIViewController
        config.userContentController.add(self, name: "bridgeHandler")
        webView = WKWebView(frame: view.bounds, configuration: config)
    }

    private func setupPlayer() {
        player = AVPlayer()
        let interval = CMTime(seconds: 1.0, preferredTimescale: 1000)
        // HAZARD 2: addPeriodicTimeObserver called without capturing returned token
        player?.addPeriodicTimeObserver(forInterval: interval, queue: .main) { time in
            self.trackPlayback(time: time)
        }
    }

    private func setupNotifications() {
        // HAZARD 3: NotificationCenter block observer without saving token
        NotificationCenter.default.addObserver(
            forName: UIApplication.didEnterBackgroundNotification,
            object: nil,
            queue: .main
        ) { notification in
            self.saveAppState()
        }
    }

    private func allocateNativeBuffer() {
        // HAZARD 4: Unmanaged.passRetained without matching release
        let buffer = NSString(string: "raw_data")
        _ = Unmanaged.passRetained(buffer).toOpaque()
    }

    func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {}
    private func trackPlayback(time: CMTime) {}
    private func saveAppState() {}
}
