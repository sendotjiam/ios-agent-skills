# VoiceOver Accessibility Tree, Rotors & Trait Architecture

VoiceOver transforms visual user interfaces into a sequential, spoken navigation graph. When views fail to expose meaningful labels, traits, or hierarchy, blind and low-vision users encounter inaccessible dead ends or cryptic announcements.

---

## 1. Accessibility Tree Construction

### A. Element Grouping & Child Combination
By default, SwiftUI exposes every nested `Text`, `Image`, and icon as an individual VoiceOver stop. In a list card with title, subtitle, timestamp, and chevron, this forces 4–5 individual swipes to parse a single row.

```swift
// ❌ ANTI-PATTERN: Fractured tree, 4 separate VoiceOver stops
VStack(alignment: .leading) {
    HStack {
        Image(systemName: "envelope.fill")
        Text("Support Team")
        Spacer()
        Text("10:42 AM")
    }
    Text("Your ticket #4829 has been updated.")
        .font(.subheadline)
}

// ✅ MODERN SWIFTUI: Combined semantic element with unified announcement
VStack(alignment: .leading) {
    HStack {
        Image(systemName: "envelope.fill")
        Text("Support Team")
        Spacer()
        Text("10:42 AM")
    }
    Text("Your ticket #4829 has been updated.")
        .font(.subheadline)
}
.accessibilityElement(children: .combine)
.accessibilityLabel("Support Team, 10:42 AM. Your ticket 4829 has been updated.")
```

### B. Silencing Purely Decorative Elements
Background gradients, card borders, and dividing icons create noise for VoiceOver users:

```swift
// ❌ ANTI-PATTERN: VoiceOver reads decorative image as "chevron right"
Image(systemName: "chevron.right")
    .foregroundColor(.secondary)

// ✅ CORRECT: Silenced from accessibility tree
Image(systemName: "chevron.right")
    .accessibilityHidden(true)
```

---

## 2. Interactive Controls & Assistive Traits

VoiceOver relies on traits to inform users how an element behaves (e.g., button, link, header, selected state).

```swift
// ❌ ANTI-PATTERN: Custom toggle built with Text + onTapGesture
// VoiceOver announces: "Notifications, text" with no action hint
Text("Notifications")
    .onTapGesture { isEnabled.toggle() }

// ✅ MODERN SWIFTUI: Explicit assistive traits and dynamic values
HStack {
    Text("Notifications")
    Spacer()
    Image(systemName: isEnabled ? "checkmark.circle.fill" : "circle")
}
.contentShape(Rectangle())
.onTapGesture { isEnabled.toggle() }
.accessibilityElement(children: .combine)
.accessibilityAddTraits(.isButton)
.accessibilityValue(isEnabled ? "On" : "Off")
.accessibilityHint("Double tap to toggle notifications")
```

### Essential Assistive Traits Table

| Trait (`AccessibilityTraits`) | Purpose | VoiceOver Announcement |
| :--- | :--- | :--- |
| `.isButton` | Interactive push/trigger element | *"Button"* |
| `.isHeader` | Section heading for quick rotor navigation | *"Heading"* |
| `.isSelected` | Current active tab, filter chip, or item | *"Selected"* |
| `.isToggle` | State toggle switch | Reads value (*"On/Off"*) |
| `.isLink` | External or web navigation link | *"Link"* |
| `.isSearchField` | Text search input | *"Search Field"* |
| `.causesPageTurn` | Carousels or book-flipping views | Paging affordance |

---

## 3. Custom Rotors & Shortcut Navigation

Custom Rotors allow VoiceOver users to flick up/down with two fingers to jump directly to specific categories (e.g. "Unread Messages", "Overdue Invoices", "Headings").

```swift
struct TaskListView: View {
    @State private var tasks: [TaskItem]

    var body: some View {
        List(tasks) { task in
            TaskRow(task: task)
        }
        .accessibilityRotor("High Priority") {
            ForEach(tasks.filter { $0.isHighPriority }) { task in
                AccessibilityRotorEntry(task.title, id: task.id)
            }
        }
        .accessibilityRotor("Incomplete") {
            ForEach(tasks.filter { !$0.isCompleted }) { task in
                AccessibilityRotorEntry(task.title, id: task.id)
            }
        }
    }
}
```

---

## 4. Custom Accessibility Actions

Complex swipe menus or floating gesture actions must be mapped to discrete accessibility actions so VoiceOver users can invoke them without dragging:

```swift
MessageRowView(message: message)
    .accessibilityElement(children: .combine)
    .accessibilityLabel("\(message.sender): \(message.preview)")
    .accessibilityAction(named: "Archive") {
        archiveMessage(message)
    }
    .accessibilityAction(named: "Mark as Unread") {
        markAsUnread(message)
    }
    .accessibilityAction(.escape) {
        dismissMessage()
    }
```

---

## 5. Voice Control (`accessibilityInputLabels`)

Users navigating via Apple Voice Control speak the visible name on screen. If an icon button has an internal accessibility label like `"Cancel Order"`, but the screen displays `"Cancel"`, Voice Control fails to map the spoken phrase unless provided input label synonyms:

```swift
Button {
    deleteAccount()
} label: {
    Image(systemName: "trash")
}
.accessibilityLabel("Permanently delete account")
.accessibilityInputLabels(["Delete", "Trash", "Remove account"])
```

---

## 6. Live Announcements & Dynamic Notifications

When asynchronous actions finish (e.g., checkout success, network error), post a dynamic announcement so VoiceOver notifies the user immediately:

```swift
// Modern Swift (iOS 17+)
AccessibilityNotification.Announcement("Payment succeeded. Order #1042 placed.")
    .post()

// Backwards-Compatible UIKit / SwiftUI
UIAccessibility.post(
    notification: .announcement,
    argument: "Network connection lost. Please try again."
)
```
