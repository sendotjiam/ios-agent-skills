# Hit Targets, Touch Bounding Boxes & Motor Accessibility

Apple Human Interface Guidelines (HIG) mandate a minimum interactive target size of **$44\times 44\text{ points}$** on iOS and iPadOS. This requirement ensures that users with tremors, motor impairments, or limited dexterity can reliably activate controls without triggering adjacent items.

---

## 1. Compliance Standards: Apple HIG vs WCAG

| Standard | Minimum Target Size | Scope |
| :--- | :--- | :--- |
| **Apple HIG** | **$44 \times 44\text{ pt}$** | Mandatory baseline for all interactive iOS/iPadOS controls |
| **WCAG 2.1 Success Criterion 2.5.5 (Level AAA)** | **$44 \times 44\text{ CSS px}$** | Enhanced touch target accessibility standard |
| **WCAG 2.2 Success Criterion 2.5.8 (Level AA)** | **$24 \times 24\text{ CSS px}$** | Minimum pass threshold for web and mobile components |

> [!IMPORTANT]
> The visual representation of an icon does not have to be $44\times 44\text{pt}$ (e.g. an $18\times 18\text{pt}$ close icon or disclosure chevron is common). However, its **interactive tap bounding box** must expand to at least $44\times 44\text{pt}$.

---

## 2. Expanding Hit Targets in SwiftUI

### A. The Bounding Box Anti-Pattern
By default, SwiftUI sizes the hit area strictly to the rendered content of the button:

```swift
// ❌ ANTI-PATTERN: Active hit area is only 16x16pt!
Button {
    dismiss()
} label: {
    Image(systemName: "xmark")
        .frame(width: 16, height: 16)
}

// ✅ MODERN SWIFTUI: Visual icon 16pt, interactive target 44x44pt
Button {
    dismiss()
} label: {
    Image(systemName: "xmark")
        .font(.system(size: 16, weight: .bold))
        .frame(width: 16, height: 16)
        .frame(minWidth: 44, minHeight: 44) // Expands invisible touch boundary
        .contentShape(Rectangle())           // Makes full 44x44 area tappable
}
.accessibilityLabel("Dismiss")
```

### B. Transparent Container Hit Testing Trap
When assigning `.onTapGesture` to an `HStack` or `VStack`, SwiftUI only detects taps on visible sub-views (text characters, icons), ignoring the blank space between them:

```swift
// ❌ ANTI-PATTERN: Taps between text and chevron fail silently
HStack {
    Text("Account Settings")
    Spacer()
    Image(systemName: "chevron.right")
}
.onTapGesture { navigateToSettings() }

// ✅ MODERN SWIFTUI: Whole row is interactive and conforms to 44pt minimum
HStack {
    Text("Account Settings")
    Spacer()
    Image(systemName: "chevron.right")
}
.frame(minHeight: 44)
.contentShape(Rectangle()) // Ensures transparent Spacer() receives touch events
.onTapGesture { navigateToSettings() }
.accessibilityElement(children: .combine)
.accessibilityAddTraits(.isButton)
```

---

## 3. Expanding Hit Targets in UIKit

### A. Modern `UIButton.Configuration` (iOS 15+)
```swift
var config = UIButton.Configuration.plain()
config.image = UIImage(systemName: "trash")
// Generates padding to ensure touch area >= 44x44pt
config.contentInsets = NSDirectionalEdgeInsets(top: 14, leading: 14, bottom: 14, trailing: 14)

let button = UIButton(configuration: config)
button.accessibilityLabel = "Delete Item"
```

### B. Custom Hit Area Overriding (`point(inside:with:)`)
For custom subclasses or compact toolbar buttons where visual layout cannot allow frame padding:

```swift
final class AccessibleTouchButton: UIButton {
    var touchAreaInsets = UIEdgeInsets(top: -10, left: -10, bottom: -10, right: -10)

    override func point(inside point: CGPoint, with event: UIEvent?) -> Bool {
        let expandedBounds = bounds.inset(by: touchAreaInsets)
        return expandedBounds.contains(point)
    }
}
```

---

## 4. Motor Accessibility & Complex Gesture Alternatives

Users with motor disabilities may not be able to perform multi-touch gestures (e.g., pinch-to-zoom, 3-finger swipes, shake-to-undo, or precision dragging).

### Accessible Alternatives for Drag-and-Drop / Reordering
When providing a list with reorder drag handles, expose discrete VoiceOver actions or accessible buttons to move items:

```swift
TaskRow(task: task)
    .accessibilityAction(named: "Move Up") {
        moveTaskUp(task)
    }
    .accessibilityAction(named: "Move Down") {
        moveTaskDown(task)
    }
```

### Shake-to-Undo Fallbacks
Relying solely on physical device shaking (`motionEnded(.motionShake)`) excludes users with motor impairments or those mounting the device on a wheelchair:

```swift
// Always provide an accessible button alongside shake detection
Button {
    undoLastAction()
} label: {
    Label("Undo", systemImage: "arrow.uturn.backward")
}
.accessibilityLabel("Undo last action")
```
