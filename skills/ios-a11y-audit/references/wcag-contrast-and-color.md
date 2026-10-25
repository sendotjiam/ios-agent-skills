# WCAG Color Contrast, High Contrast & Color Independence

Vision impairments (including low vision, cataract blur, and color blindness) require high-contrast text and interfaces that do not convey critical state solely through color differences.

---

## 1. WCAG 2.1 Contrast Thresholds

| Element Type | WCAG AA Minimum | WCAG AAA Enhanced | Description |
| :--- | :--- | :--- | :--- |
| **Normal Text** | **$4.5 : 1$** | **$7.0 : 1$** | Text below $18\text{pt}$ (or below $14\text{pt}$ if bold) |
| **Large Text** | **$3.0 : 1$** | **$4.5 : 1$** | Text $\ge 18\text{pt}$ regular or $\ge 14\text{pt}$ bold |
| **Non-Text Components** | **$3.0 : 1$** | **$4.5 : 1$** | Active buttons, input field outlines, icons |

### Formula for Relative Luminance Contrast
The contrast ratio is calculated from the relative luminance ($L_1, L_2$) of the foreground and background:
$$\text{Contrast Ratio} = \frac{L_1 + 0.05}{L_2 + 0.05} \quad (\text{where } L_1 > L_2)$$

---

## 2. Dynamic Semantic Colors vs Hardcoded RGB

Hardcoded hex or RGB colors almost always fail contrast standards when users switch between iOS Light and Dark modes:

```swift
// ❌ ANTI-PATTERN: Hardcoded gray text fails contrast on dark backgrounds
Text("Last updated 5 mins ago")
    .foregroundColor(Color(red: 0.6, green: 0.6, blue: 0.6)) // 2.8:1 contrast in Dark Mode

// ✅ MODERN SWIFTUI: Dynamic semantic color adapting automatically
Text("Last updated 5 mins ago")
    .foregroundColor(.secondary) // Automatically calibrated by iOS for 4.5:1+ in both modes
```

### iOS Semantic System Colors

| SwiftUI Token | UIKit Equivalent | Role & Guaranteed Contrast |
| :--- | :--- | :--- |
| `Color.primary` | `UIColor.label` | Primary content text ($> 10:1$) |
| `Color.secondary` | `UIColor.secondaryLabel` | Supporting metadata ($> 4.5:1$) |
| `Color(uiColor: .systemBackground)` | `UIColor.systemBackground` | Base surface layer |
| `Color(uiColor: .secondarySystemBackground)` | `UIColor.secondarySystemBackground` | Grouped cards and input backgrounds |
| `Color.accentColor` | `UIColor.tintColor` | Interactive interactive buttons and links |

---

## 3. High Contrast Mode Adaptation (`accessibilityContrast`)

iOS includes an **Increase Contrast** accessibility setting (`Settings > Accessibility > Display & Text Size > Increase Contrast`). Apps should listen to this preference and elevate border thickness and text contrast:

```swift
struct AdaptiveCardView: View {
    @Environment(\.colorSchemeContrast) private var contrast

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Pro Subscription").font(.headline)
            Text("$9.99 / month").font(.subheadline)
        }
        .padding()
        .background(Color(uiColor: .secondarySystemBackground))
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(
                    contrast == .increased ? Color.primary : Color.clear,
                    lineWidth: contrast == .increased ? 2 : 0
                )
        )
    }
}
```

---

## 4. Differentiate Without Color (`accessibilityDifferentiateWithoutColor`)

Approximately **8% of men and 0.5% of women** experience color blindness (protanopia, deuteranopia, tritanopia, or monochromacy). Critical status must never rely exclusively on color differences (e.g., green dot for Online, red dot for Offline):

```swift
// ❌ ANTI-PATTERN: Only color conveys status; indistinguishable to red-green color-blind users
HStack {
    Circle()
        .fill(isServerOnline ? Color.green : Color.red)
        .frame(width: 12, height: 12)
    Text("Server Status")
}

// ✅ MODERN SWIFTUI: Combined color, icon symbol, and explicit label
struct ServerStatusRow: View {
    let isServerOnline: Bool
    @Environment(\.accessibilityDifferentiateWithoutColor) private var differentiateWithoutColor

    var body: some View {
        HStack(spacing: 8) {
            Image(systemName: isServerOnline ? "checkmark.circle.fill" : "exclamationmark.circle.fill")
                .foregroundColor(isServerOnline ? .green : .red)
                .font(.system(size: 14, weight: .bold))

            Text("Server Status: \(isServerOnline ? "Online" : "Offline")")
                .font(.subheadline)
        }
        .accessibilityElement(children: .combine)
        .accessibilityLabel("Server Status, \(isServerOnline ? "Online" : "Offline")")
    }
}
```
