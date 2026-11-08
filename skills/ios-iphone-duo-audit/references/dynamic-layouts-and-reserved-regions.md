# Dynamic Layouts, Reserved Regions & Arrangement Views (iOS 27.1+)

Reference patterns for adapting SwiftUI and UIKit views across iPhone Duo's compact outer display, regular inner display, 6 device poses, and center hinge fold.

---

## 1. Reserved Regions (`ReservedRegion` & `UIView.ReservedRegion`)

On iPhone Duo, available space is shaped by **reserved regions** (`ReservedRegion.Kind`):
- **`.occlusion`**: Hardware regions that cover content:
  - **Outer front-facing camera**: Always present in the corner, vertically aligned with side controls; expands into Dynamic Island for Live Activities.
  - **Inner front-facing camera**: Hidden behind the display when inactive; becomes an active `.occlusion` region only when the camera is active.
- **`.division`**: Conditional center hinge folding region when iPhone Duo is partially open (book, tent, or laptop pose), splitting the inner display into two usable regions.

### SwiftUI: Querying `ReservedRegion` via `GeometryProxy`
```swift
import SwiftUI

struct AdaptiveFoldCanvasView: View {
    var body: some View {
        GeometryReader { proxy in
            let divisions = proxy.reservedRegions(kind: .division)
            let occlusions = proxy.reservedRegions(kind: .occlusion)

            if let fold = divisions.first {
                // Device is partially folded: place content cleanly on either side of fold.frame
                HStack(spacing: fold.frame.width) {
                    LeadingWorkspacePane()
                    TrailingInspectorPane()
                }
            } else {
                // Device is flat (closed on outer display or fully open on inner display)
                UnifiedWorkspaceView(avoiding: occlusions.map(\.frame))
            }
        }
    }
}
```

### UIKit: Querying `UIView.ReservedRegion`
```swift
import UIKit

final class CustomCanvasViewController: UIViewController {
    override func viewDidLayoutSubviews() {
        super.viewDidLayoutSubviews()

        let divisions = view.reservedRegions(kind: .division)
        let occlusions = view.reservedRegions(kind: .occlusion)

        if let foldRegion = divisions.first {
            layoutAroundFold(foldRegion.frame)
        } else {
            layoutFlat(avoiding: occlusions.map(\.frame))
        }
    }
}
```

---

## 2. Arrangement Views (`ArrangementView` & `UIArrangementViewController`)

An **arrangement view** dynamically organizes a `primary` view and a `secondary` view based on display size, orientation, and `.division` reserved regions:
- **`.split`**: Divides space horizontally when wider than tall, or vertically when taller than wide, and automatically adjusts pane widths and margins around the center fold. Replaces manual `HStack`/`VStack` orientation switching.
- **`.overlay`**: Layers `primary` over `secondary` when the display is flat (closed or fully open), and automatically separates `primary` (trailing/bottom) and `secondary` (leading/top) onto opposite sides of the fold when partially open. Replaces `ZStack` for foreground controls over media/canvases.

### SwiftUI: Split and Overlay `ArrangementView`
```swift
import SwiftUI

// 1. Split Arrangement (e.g., side-by-side in landscape, stacked in portrait, fold-aware)
struct DocumentSplitWorkspace: View {
    var body: some View {
        NavigationStack {
            ArrangementView {
                DocumentCanvasView()
            } secondary: {
                ToolPaletteView()
            }
            .arrangementViewStyle(.split.axes(.horizontal))
        }
    }
}

// 2. Overlay Arrangement (e.g., video playback with transport controls that separate when folded like a laptop)
struct VideoPlaybackDuoView: View {
    var body: some View {
        ArrangementView {
            PlaybackControlsView() // Primary: overlays bottom when flat, moves to bottom/trailing half when folded
        } secondary: {
            VideoPlayerSurface()   // Secondary: fills screen when flat, moves to top/leading half when folded
        }
        .arrangementViewStyle(.overlay)
    }
}
```

### UIKit: `UIArrangementViewController`
```swift
import UIKit

final class StudioContainerViewController: UIViewController {
    private let arrangementVC = UIArrangementViewController()

    override func viewDidLoad() {
        super.viewDidLoad()

        let primaryVC = PlaybackControlsViewController()
        let secondaryVC = VideoSurfaceViewController()

        arrangementVC.setViewController(primaryVC, for: .primary)
        arrangementVC.setViewController(secondaryVC, for: .secondary)
        arrangementVC.updateArrangement(.split.axes(.horizontal))

        addChild(arrangementVC)
        view.addSubview(arrangementVC.view)
        arrangementVC.view.frame = view.bounds
        arrangementVC.view.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        arrangementVC.didMove(toParent: self)
    }
}
```

### Container Nesting Rules
- **NEVER** place `ArrangementView` inside a `ScrollView`, `List`, `Grid`, or `NavigationSplitView`.
- **NEVER** place a navigation container (`NavigationSplitView`, `TabView`) *inside* an `ArrangementView` — wrap navigation containers *outside* the `ArrangementView`.
