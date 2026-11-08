# Vertical Axis Controls, Bar Compression & Overflow Menus (iOS 27.1+)

Reference patterns for configuring toolbars, tab bars, and sheets on iPhone Duo's vertical side bar.

---

## 1. How Vertical Controls Work on iPhone Duo

On the outer display (and on the inner display in landscape or Split View multitasking), iOS moves top and bottom bars to a **vertical column along the side edge** (from top to bottom: Dynamic Island, status bar, toolbar, tab bar).
- In **Split View multitasking** on the inner display, the left app places vertical controls on the left edge and the right app places vertical controls on the right edge.
- In **Right-to-Left (RTL)** languages, vertical controls remain anchored to the hardware camera side.
- Only the **inner display in portrait** retains enough vertical height for horizontal bars.

---

## 2. Mandatory Icon + Title Rule for Vertical Toolbar Items

iPhone Duo presents toolbar items vertically (icon only), horizontally (icon or title), or inside the overflow menu (icon + title):
- **If an item has a title and NO icon, the system DOES NOT present it vertically.**
- **If an item uses a custom view rather than a standard title + icon, the system DOES NOT present it vertically.**

### SwiftUI: Adaptable Toolbar Organization
```swift
import SwiftUI

struct MailThreadView: View {
    @Environment(\.toolbarVerticalEdge) private var verticalEdge

    var body: some View {
        ScrollView {
            ThreadMessagesView(isVerticalBarActive: verticalEdge != nil)
        }
        // Extend hero/background artwork beneath vertical side bars
        .backgroundExtensionEffect()
        .toolbar {
            // 1. Top of vertical axis: cancellation / back / close
            ToolbarItem(placement: .cancellationAction) {
                Button("Close", systemImage: "xmark") { }
            }

            // 2. Prominent action pinned near the top of the vertical axis
            ToolbarItem(placement: .topBarPinnedTrailing) {
                Button("Done", systemImage: "checkmark") { }
            }

            // 3. Semantic groups with visibility priority (items overflow bottom-to-top by default)
            ToolbarItemGroup(placement: .primaryAction) {
                Button("Compose", systemImage: "square.and.pencil") { }
                    .visibilityPriority(.high)

                Button("Filter", systemImage: "line.3.horizontal.decrease.circle") { }
                    .visibilityPriority(.medium)
            }

            // 4. System Overflow Menu (never create a custom "ellipsis" button)
            ToolbarOverflowMenu {
                Button("Archive Thread", systemImage: "archivebox") { }
                Button("Mute Notifications", systemImage: "bell.slash") { }
            }
        }
        // Preserve toolbar items in task-focused views (.prefersToolbarItems)
        // or preserve tab bar in navigation-focused views (.prefersTabBar, default)
        .toolbarVerticalCompressionBehavior(.prefersToolbarItems)
    }
}
```

---

## 3. UIKit: Vertical Bar Traits, Groups & Compression

```swift
import UIKit

final class TaskEditorViewController: UIViewController {
    override func viewDidLoad() {
        super.viewDidLoad()

        // 1. Prominent action pinned at top of vertical bar
        let doneItem = UIBarButtonItem(
            title: "Done",
            image: UIImage(systemName: "checkmark"),
            primaryAction: UIAction { _ in }
        )
        navigationItem.pinnedTrailingGroup = UIBarButtonItemGroup(
            barButtonItems: [doneItem],
            representativeItem: nil
        )

        // 2. Prioritized action items (both title + image required for vertical rendering)
        let composeItem = UIBarButtonItem(
            title: "Compose",
            image: UIImage(systemName: "square.and.pencil"),
            primaryAction: UIAction { _ in }
        )
        composeItem.visibilityPriority = .high
        composeItem.axisBehavior = .automatic

        toolbarItems = [composeItem]

        // 3. System overflow menu items
        navigationItem.additionalOverflowItems = UIDeferredMenuElement.uncached { completion in
            completion([
                UIAction(title: "Export PDF", image: UIImage(systemName: "arrow.up.doc")) { _ in }
            ])
        }

        // 4. Task-focused compression behavior: collapse tab bar before toolbar items
        preferredVerticalBarCompressionBehavior = .prefersToolbarItems

        // 5. Inspect vertical bar edge via automatic trait tracking
        registerForTraitChanges([UITraitVerticalBarEdge.self]) { (self: Self, _) in
            let isVertical = self.traitCollection.verticalBarEdge != .none
            self.updateContentInsets(forVerticalBar: isVertical)
        }
    }
}
```

---

## 4. Sheets, Split Views & Inspectors Behavior

- **Split Views (`NavigationSplitView` / `UISplitViewController`)**: When showing multiple columns on the inner display, the sidebar/leading pane keeps **horizontal** bars at the top of its pane (so actions clearly belong to the list), while the trailing detail pane uses the **vertical** side bar.
- **Inspectors**: Present bars horizontally.
- **Sheets**:
  - Outer display: Vertical bars by default. Override with `.toolbarVerticalBehavior(.disabled)` (SwiftUI) or `preferredVerticalBarBehavior` (UIKit) if inappropriate.
  - Inner display: Horizontal bars when centered or leading; vertical bars when placed on the trailing edge via `.presentationPlacement(_:)` or `UISheetPresentationController.preferredPlacement`.
