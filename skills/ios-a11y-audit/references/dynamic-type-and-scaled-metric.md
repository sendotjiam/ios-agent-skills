# Dynamic Type, `@ScaledMetric` & Responsive AX Layouts

Dynamic Type allows users to choose their preferred text size across iOS and iPadOS. At accessibility sizes (`accessibilityMedium` through `accessibilityExtraExtraExtraLarge` / AX1–AX5), body text scales up to **300%–350%** of standard size. Layouts that rely on rigid frames clip, truncate, or completely occlude critical text.

---

## 1. The Dynamic Type Hierarchy

Always prioritize standard Apple semantic text styles over hardcoded point sizes:

| SwiftUI Text Style | UIKit Text Style | Default Size (Large) | Role |
| :--- | :--- | :--- | :--- |
| `.largeTitle` | `UIFont.TextStyle.largeTitle` | 34pt | Primary screen headings |
| `.title` | `UIFont.TextStyle.title1` | 28pt | Section titles |
| `.headline` | `UIFont.TextStyle.headline` | 17pt (Semibold) | Emphasized content titles |
| `.body` | `UIFont.TextStyle.body` | 17pt | Primary reading copy |
| `.callout` | `UIFont.TextStyle.callout` | 16pt | Lead-in details and callouts |
| `.subheadline` | `UIFont.TextStyle.subheadline` | 15pt | Secondary row details |
| `.footnote` | `UIFont.TextStyle.footnote` | 13pt | Disclaimers and metadata |
| `.caption` | `UIFont.TextStyle.caption1` | 12pt | Supporting annotations |

When custom fonts are required, pin them to a standard style using `relativeTo`:

```swift
// ❌ ANTI-PATTERN: Hardcoded size never scales with Dynamic Type
Text("Total Balance")
    .font(.system(size: 20, weight: .bold))

// ✅ MODERN SWIFTUI: Custom font scaling dynamically with body text
Text("Total Balance")
    .font(.custom("Inter-Bold", size: 20, relativeTo: .body))
```

---

## 2. Proportional Geometry with `@ScaledMetric`

When text expands, associated iconography, avatar thumbnails, and cell padding must scale proportionally. Hardcoded `CGFloat` dimensions create distorted, clipped layouts:

```swift
// ❌ ANTI-PATTERN: Fixed 24pt icon alongside text scaling to 48pt
struct StatusBadge: View {
    var body: some View {
        HStack(spacing: 8) {
            Image(systemName: "checkmark.seal.fill")
                .frame(width: 24, height: 24)
            Text("Verified Account")
                .font(.headline)
        }
    }
}

// ✅ MODERN SWIFTUI: Dynamic scaling using @ScaledMetric
struct StatusBadge: View {
    @ScaledMetric(relativeTo: .headline) private var iconSize: CGFloat = 24
    @ScaledMetric(relativeTo: .headline) private var spacing: CGFloat = 8

    var body: some View {
        HStack(spacing: spacing) {
            Image(systemName: "checkmark.seal.fill")
                .resizable()
                .scaledToFit()
                .frame(width: iconSize, height: iconSize)
            Text("Verified Account")
                .font(.headline)
        }
    }
}
```

---

## 3. Eliminating Fixed-Height Clipping Anti-Patterns

A common flaw is bounding text views with rigid frame heights (`.frame(height: 44)`). As text scales, iOS clips characters or drops whole lines:

```swift
// ❌ ANTI-PATTERN: Text container locked to 50pt clips at AX1
Text("Your reservation has been confirmed for Friday evening.")
    .font(.body)
    .frame(height: 50) // Clamps text height; truncated when font scales

// ✅ MODERN SWIFTUI: Minimum flexible height with vertical expansion
Text("Your reservation has been confirmed for Friday evening.")
    .font(.body)
    .frame(minHeight: 50)
    .fixedSize(horizontal: false, vertical: true)
```

---

## 4. Layout Adaptation: Switching `HStack` to `VStack`

At accessibility font sizes, horizontal layouts (`HStack`) run out of horizontal screen real estate, causing severe truncation.

### Technique A: `ViewThatFits` (Declarative Sizing)
```swift
struct ResponsiveActionBar: View {
    var body: some View {
        ViewThatFits(in: .horizontal) {
            // Priority 1: Side-by-side on standard sizes
            HStack(spacing: 16) {
                ActionButton(title: "Decline", role: .cancel)
                ActionButton(title: "Accept Offer", role: .confirm)
            }
            // Priority 2: Stacked vertically when text scales or screens are narrow
            VStack(spacing: 12) {
                ActionButton(title: "Accept Offer", role: .confirm)
                ActionButton(title: "Decline", role: .cancel)
            }
        }
    }
}
```

### Technique B: `@Environment(\.dynamicTypeSize)`
```swift
struct UserProfileHeader: View {
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize

    var body: some View {
        let isAccessibility = dynamicTypeSize.isAccessibilitySize

        let layout = isAccessibility
            ? AnyLayout(VStackLayout(alignment: .leading, spacing: 12))
            : AnyLayout(HStackLayout(alignment: .center, spacing: 16))

        layout {
            AvatarView()
            VStack(alignment: .leading) {
                Text("Alexandra Smith").font(.headline)
                Text("Senior Engineer").font(.subheadline)
            }
        }
    }
}
```

---

## 5. UIKit Dynamic Type & AutoLayout Rules

In UIKit, three rules guarantee Dynamic Type fidelity:
1. Always set `adjustsFontForContentSizeCategory = true` on `UILabel`, `UITextView`, and `UIButton`.
2. Use `UIFontMetrics.default.scaledFont(for: customFont)`.
3. Never set rigid height constraints (`== 44`) on labels. Use greater-than-or-equal constraints (`>= 44`) or set `numberOfLines = 0`.

```swift
let titleLabel = UILabel()
titleLabel.translatesAutoresizingMaskIntoConstraints = false
titleLabel.numberOfLines = 0
titleLabel.font = UIFontMetrics(forTextStyle: .headline).scaledFont(for: customHeadlineFont)
titleLabel.adjustsFontForContentSizeCategory = true

NSLayoutConstraint.activate([
    titleLabel.topAnchor.constraint(equalTo: view.topAnchor, constant: 16),
    titleLabel.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 16),
    titleLabel.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -16),
    titleLabel.bottomAnchor.constraint(lessThanOrEqualTo: view.bottomAnchor, constant: -16)
])
```
