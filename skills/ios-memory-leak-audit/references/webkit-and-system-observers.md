# WebKit Handlers, AVFoundation & System Observers

System frameworks in iOS contain several classes designed before modern Swift memory safety conventions that hold **strong references to delegates or targets**. Failing to decouple these objects results in permanent memory leaks where `UIViewController` instances stay alive for the entire duration of the app session.

---

## 1. WebKit Script Message Handler Retain Cycle

When configuring a `WKWebView` to bridge JavaScript events to Swift, `WKUserContentController.add(_:name:)` strongly retains the handler passed to it:

$$\text{UIViewController} \longrightarrow \text{WKWebView} \longrightarrow \text{WKUserContentController} \overset{\text{STRONG}}{\longrightarrow} \text{UIViewController}$$

```swift
// ❌ CRITICAL LEAK: Permanent Retain Cycle
class WebViewController: UIViewController, WKScriptMessageHandler {
    var webView: WKWebView!

    override func viewDidLoad() {
        super.viewDidLoad()
        let config = WKWebViewConfiguration()
        // WKUserContentController holds a STRONG reference to self!
        config.userContentController.add(self, name: "appHandler")
        webView = WKWebView(frame: view.bounds, configuration: config)
        view.addSubview(webView)
    }

    func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
        // Handle JS messages
    }
}
```

### The Fix: Generic `WeakScriptMessageHandler` Trampoline

Break the cycle by interposing a lightweight proxy object that holds `self` weakly:

```swift
import WebKit

final class WeakScriptMessageHandler: NSObject, WKScriptMessageHandler {
    private weak var delegate: WKScriptMessageHandler?

    init(delegate: WKScriptMessageHandler) {
        self.delegate = delegate
        super.init()
    }

    func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
        delegate?.userContentController(userContentController, didReceive: message)
    }
}

// ✅ CLEAN: WebViewController deallocates cleanly
override func viewDidLoad() {
    super.viewDidLoad()
    let config = WKWebViewConfiguration()
    config.userContentController.add(WeakScriptMessageHandler(delegate: self), name: "appHandler")
    webView = WKWebView(frame: view.bounds, configuration: config)
}

deinit {
    webView.configuration.userContentController.removeScriptMessageHandler(forName: "appHandler")
}
```

---

## 2. AVFoundation: `AVPlayer` Periodic Time Observers

When building custom video or audio player interfaces, observing playback progress requires calling `AVPlayer.addPeriodicTimeObserver(forInterval:queue:using:)`.

### The Hazard:
1. `addPeriodicTimeObserver` returns an opaque `Any` observer token.
2. The player retains the observation block until explicitly instructed to remove it.
3. If the token is discarded, or if the closure captures `self` strongly without removing the observer upon view dismissal, the player and view controller continue running in background RAM.

```swift
// ❌ MEDIUM LEAK: Token discarded, self retained
class VideoPlayerViewController: UIViewController {
    private var player = AVPlayer()

    override func viewDidLoad() {
        super.viewDidLoad()
        let interval = CMTime(seconds: 0.5, preferredTimescale: CMTimeScale(NSEC_PER_SEC))
        // Token is discarded! Observation continues forever.
        player.addPeriodicTimeObserver(forInterval: interval, queue: .main) { time in
            self.updateProgressBar(time: time)
        }
    }
}
```

### The Fix: Store and Remove Token in `deinit` / `viewDidDisappear`

```swift
// ✅ CLEAN: Token stored and cleanly removed
class VideoPlayerViewController: UIViewController {
    private var player = AVPlayer()
    private var timeObserverToken: Any?

    override func viewDidLoad() {
        super.viewDidLoad()
        let interval = CMTime(seconds: 0.5, preferredTimescale: CMTimeScale(NSEC_PER_SEC))
        timeObserverToken = player.addPeriodicTimeObserver(forInterval: interval, queue: .main) { [weak self] time in
            self?.updateProgressBar(time: time)
        }
    }

    deinit {
        if let token = timeObserverToken {
            player.removeTimeObserver(token)
            timeObserverToken = nil
        }
    }
}
```

---

## 3. `NotificationCenter` Block-Based Observers

Since iOS 9, selector-based observers (`addObserver(_:selector:name:object:)`) do not require manual removal in `deinit` if registered on `self`.

**However**, block-based observers (`addObserver(forName:object:queue:using:)`) behave completely differently! They register an anonymous closure inside the internal `NotificationCenter` registry.

```swift
// ❌ CRITICAL LEAK: Discarding token retains block and captured self permanently
final class LocationTracker {
    func startTracking() {
        // Discarding the return value means it can NEVER be unregistered
        NotificationCenter.default.addObserver(
            forName: UIApplication.didEnterBackgroundNotification,
            object: nil,
            queue: .main
        ) { notification in
            self.persistCurrentCoordinates()
        }
    }
}
```

### The Fix: Store `NSObjectProtocol` and Remove in `deinit`

```swift
// ✅ CLEAN: Token retained and unregistered
final class LocationTracker {
    private var backgroundObserverToken: NSObjectProtocol?

    func startTracking() {
        backgroundObserverToken = NotificationCenter.default.addObserver(
            forName: UIApplication.didEnterBackgroundNotification,
            object: nil,
            queue: .main
        ) { [weak self] _ in
            self?.persistCurrentCoordinates()
        }
    }

    deinit {
        if let token = backgroundObserverToken {
            NotificationCenter.default.removeObserver(token)
        }
    }
}
```

---

## 4. RunLoop Target-Action: `CADisplayLink` & `Timer`

Both `CADisplayLink` and `Timer.scheduledTimer` add the specified `target` directly into the current `RunLoop`. The RunLoop retains the target strongly until invalidated.

```swift
// ❌ LEAK: DisplayLink keeps view controller alive indefinitely
class AnimationViewController: UIViewController {
    private var displayLink: CADisplayLink?

    override func viewDidLoad() {
        super.viewDidLoad()
        // RunLoop holds strong reference to self via displayLink
        displayLink = CADisplayLink(target: self, selector: #selector(handleFrame))
        displayLink?.add(to: .main, forMode: .common)
    }

    @objc private func handleFrame() { ... }
}
```

### The Fix: `WeakProxy` or Teardown in `viewWillDisappear`
```swift
// ✅ FIX: Invalidate displayLink when leaving screen
override func viewWillDisappear(_ animated: Bool) {
    super.viewWillDisappear(animated)
    displayLink?.invalidate()
    displayLink = nil
}
```
