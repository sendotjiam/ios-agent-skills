---
name: ios-a11y-audit
description: Comprehensive iOS and macOS accessibility auditor. Audits SwiftUI and UIKit view hierarchies for VoiceOver tree integrity (unlabelled icons/buttons, element grouping, custom rotors, custom actions), Dynamic Type scaling and text clipping (fixed-height frames, @ScaledMetric, ViewThatFits, AX sizes), 44x44pt minimum tap targets (.contentShape hit expansion, touchAreaInsets), WCAG 2.1 AA/AAA color contrast, assistive traits (.isButton, .isHeader, .isSelected), sensory & motion adaptations (accessibilityReduceMotion, accessibilityReduceTransparency, accessibilityDifferentiateWithoutColor), Smart Invert media protection (accessibilityIgnoresInvertColors), Swift Charts audio graphs (AXChartDescriptor), and Xcode 15+ automated test integration (performAccessibilityAudit). Use whenever auditing iOS apps for accessibility, reviewing VoiceOver support, fixing Dynamic Type truncation, resolving touch target violations, or preparing an App Store accessibility compliance audit.
---

# iOS Accessibility & Assistive Technology Audit Guide

This skill guides deep static and diagnostic audits of iOS, iPadOS, and macOS codebases to guarantee full accessibility compliance under Apple Human Interface Guidelines (HIG) and WCAG 2.1/2.2 AA/AAA standards. It covers screen reader navigation (VoiceOver), typography scaling (Dynamic Type & `@ScaledMetric`), motor accessibility ($44\times 44\text{pt}$ hit targets), sensory adaptations (Reduce Motion, Reduce Transparency, Differentiate Without Color), and automated testing (`performAccessibilityAudit`).

---

## 1. Audit Taxonomy & Severity Tiers

Classify all accessibility findings into four standardized severity tiers:

### 🔴 Critical (Screen Reader Blockers & Text Clipping)
- **Unlabelled Interactive Elements**: Buttons, icon controls, or custom gestures rendered with bare SF Symbols or raw images with zero accessible label (`Image(systemName: "xmark")`), rendering the control invisible or announcing cryptic file names to screen readers.
- **Dynamic Type Text Clipping / Truncation**: Rigid `.frame(height: 44)` or fixed-size containers enclosing dynamic text that truncate or clip text entirely when Dynamic Type is scaled to accessibility sizes (`accessibilityMedium` through `accessibilityExtraExtraExtraLarge`).
- **Sub-30pt Tap Targets**: Interactive elements with active tap bounding boxes smaller than 30pt (far below Apple HIG $\ge 44\text{pt}$ and WCAG 2.5.5 AAA 44pt / 2.5.8 AA 24pt), causing high touch failure rates for motor-impaired users.
- **Severe WCAG Contrast Failures ($< 3.0:1$)**: Primary text or essential interactive icons with contrast lower than $3.0:1$ against their background in Light or Dark mode.
- **Custom Gesture Traps**: Multi-touch or drag workflows (e.g. swipe-to-delete, drag reorder) lacking discrete accessible button or rotor action alternatives.

### 🟠 High (Navigation Hazards & Structural Impediments)
- **Vestibular Motion Hazards**: Continuous parallax effects, looping spring animations, or auto-playing carousel transitions that fail to check `@Environment(\.accessibilityReduceMotion)` / `UIAccessibility.isReduceMotionEnabled`.
- **Translucent Material Illegibility**: Floating text or controls placed over `.ultraThinMaterial` / `.thinMaterial` that lack an opaque fallback when `@Environment(\.accessibilityReduceTransparency)` is active.
- **Color-Only State Communication**: Status indicators conveyed *exclusively* via red/green colored circles without accompanying icons, text, or shapes, failing users with protanopia or deuteranopia (`accessibilityDifferentiateWithoutColor`).
- **Missing or Incorrect Assistive Traits**: Custom controls (e.g. custom checkboxes, toggles, accordions, segmented buttons) lacking `.isButton`, `.isHeader`, or `.isSelected` traits.
- **Fixed Layout Containers at Large AX Sizes**: Horizontal multi-column layouts (`HStack`) with 3+ items that refuse to wrap into vertical stacks (`ViewThatFits` or `@Environment(\.dynamicTypeSize)`) at accessibility font sizes.
- **Tap Targets Between 30pt and 43pt**: Interactive elements that do not meet Apple's $44\times 44\text{pt}$ minimum target area and omit `.contentShape(Rectangle())` frame expansion.
- **WCAG AA Contrast Non-Compliance ($3.0:1 - 4.49:1$ on Normal Text)**: Body copy and form labels failing the 4.5:1 contrast threshold.

### 🟡 Medium (Suboptimal Experience & Sensory Gaps)
- **Missing `@ScaledMetric` on Custom Spacing and Iconography**: Custom icon sizing, borders, or layout margins hardcoded as plain `CGFloat` without `@ScaledMetric`, causing layouts to look unbalanced when text scales $200\%+$.
- **Smart Invert Distortion on Media**: Photo viewers, video players, and image galleries missing `.accessibilityIgnoresInvertColors(true)`, turning them into photographic negatives under Smart Invert.
- **Data Charts Missing Audio Graph Sonification**: Swift Charts or custom graphs missing `AXChartDescriptor` / `AXDataSeriesDescriptor`, preventing blind and low-vision users from hearing pitch-based auditory data curves.
- **Voice Control Friction**: Custom visual iconography lacking `.accessibilityInputLabels(["Search", "Find"])` so speech-to-control users can verbally trigger the button.
- **Hardware Keyboard & Focus Engine Omission**: Interactive custom components on iPadOS/macOS failing to support `.focusable()`, `.focused()`, or standard Tab key navigation rings.
- **Redundant Decorative Elements Exposed to VoiceOver**: Purely decorative illustrations, background cards, or dividing icons announced by VoiceOver instead of being silenced with `.accessibilityHidden(true)`.
- **Hardcoded Absolute Hex/RGB Colors**: Color definitions that bypass iOS dynamic semantic tokens (`Color(uiColor: .label)`, `Color(uiColor: .systemBackground)`) and fail contrast when system high contrast or dark mode toggles.

### 🔵 Low (Hygiene & Polish)
- **Redundant Trait Verbiage in Labels**: Including words like "button", "link", or "header" in `.accessibilityLabel("Close button")`, causing VoiceOver to announce "Close button, button".
- **Suboptimal Reading Sequence**: VoiceOver navigating visual elements out of logical hierarchical order due to deep view nesting without `.accessibilityElement(children: .combine)`.

---

## 2. Automated Fast-Scan (CLI Pre-Scan)

Before conducting deep AST manual inspection, run the bundled zero-dependency Python scanner to surface project-wide accessibility hazards in seconds:

```bash
# Output colored table summary of accessibility hazards
python3 skills/ios-a11y-audit/scripts/scan_a11y.py <path/to/ios/project>

# Export structured Markdown report for pull requests
python3 skills/ios-a11y-audit/scripts/scan_a11y.py <path/to/ios/project> --format markdown -o a11y_report.md

# Machine-readable JSON output
python3 skills/ios-a11y-audit/scripts/scan_a11y.py <path/to/ios/project> --format json
```

The scanner analyzes Swift files for:
- Bare `Button` or `UIButton` instances lacking accessible labels
- Rigid `.frame(height: N)` text containers causing Dynamic Type clipping
- Interactive controls with sub-44pt active hit areas
- Looping `.repeatForever()` animations missing `accessibilityReduceMotion`
- `.ultraThinMaterial` backgrounds missing `accessibilityReduceTransparency`
- Color-only status circles without symbol or `accessibilityDifferentiateWithoutColor` support
- Media and avatars missing `.accessibilityIgnoresInvertColors(true)`
- Custom tap gestures missing `.accessibilityAddTraits(.isButton)`
- Hardcoded RGB colors risking contrast failures in Dark Mode
- Redundant trait words in accessibility labels

---

## 3. Screen & Component Audit Protocol

Perform the accessibility audit methodically across the view layers:

```
[UI Screen / View Hierarchy]
  │
  ├── 1. VoiceOver Tree & Trait Inspection
  │     ├── Are all icon-only buttons labelled?
  │     ├── Are composite rows combined with .accessibilityElement(children: .combine)?
  │     └── Are custom toggles/headers decorated with correct traits?
  │
  ├── 2. Dynamic Type & Layout Adaptation (AX Sizes)
  │     ├── Do text views allow vertical expansion (no rigid .frame(height: N))?
  │     ├── Are custom icons/spacings scaled using @ScaledMetric?
  │     └── Do horizontal stacks adapt via ViewThatFits or DynamicTypeSize?
  │
  ├── 3. Touch Bounding Box & Motor Ergonomics
  │     ├── Do all interactive elements meet the 44x44pt minimum?
  │     └── Are touch hit areas expanded with .contentShape(Rectangle())?
  │
  ├── 4. Contrast & Color Independence
  │     ├── Does text meet WCAG AA (4.5:1 normal, 3:1 large) across Light & Dark?
  │     └── Are state indicators paired with shapes/symbols (Differentiate Without Color)?
  │
  └── 5. Sensory & Media Adaptations
        ├── Is vestibular motion mitigated via accessibilityReduceMotion?
        ├── Are blurred materials backed with opaque fallbacks (Reduce Transparency)?
        └── Are images/videos protected with accessibilityIgnoresInvertColors?
```

---

## 4. Surgical Remediation Patterns

### A. VoiceOver Unlabelled Icon Button & Touch Expansion
```swift
// ❌ BEFORE: Unlabelled icon, active tap area only 18x18pt
Button {
    dismiss()
} label: {
    Image(systemName: "xmark")
        .frame(width: 18, height: 18)
}

// ✅ AFTER: Semantic label, 44x44pt hit target, voice control synonyms
Button {
    dismiss()
} label: {
    Image(systemName: "xmark")
        .font(.system(size: 18, weight: .bold))
        .frame(width: 18, height: 18)
        .frame(minWidth: 44, minHeight: 44)
        .contentShape(Rectangle())
}
.accessibilityLabel("Dismiss")
.accessibilityInputLabels(["Dismiss", "Close", "Cancel"])
```

### B. Dynamic Type Text Clipping & Layout Reflow
```swift
// ❌ BEFORE: Rigid frame clips text; horizontal stack overflows at AX3
HStack {
    Image(systemName: "star.fill")
        .frame(width: 20, height: 20)
    Text("Premium Gold Membership")
        .font(.headline)
        .frame(height: 30)
}

// ✅ AFTER: @ScaledMetric geometry, flexible vertical height, ViewThatFits reflow
struct MembershipBadge: View {
    @ScaledMetric(relativeTo: .headline) private var iconSize: CGFloat = 20

    var body: some View {
        ViewThatFits(in: .horizontal) {
            HStack(spacing: 8) {
                iconView
                textView
            }
            VStack(alignment: .leading, spacing: 6) {
                iconView
                textView
            }
        }
    }

    private var iconView: some View {
        Image(systemName: "star.fill")
            .resizable()
            .scaledToFit()
            .frame(width: iconSize, height: iconSize)
            .accessibilityHidden(true)
    }

    private var textView: some View {
        Text("Premium Gold Membership")
            .font(.headline)
            .frame(minHeight: 30)
            .fixedSize(horizontal: false, vertical: true)
    }
}
```

### C. Sensory & Motion Safeguards
```swift
// ❌ BEFORE: Infinite spin causes nausea; glassy card illegible when blurred
struct RadarCard: View {
    @State private var isPulsing = false

    var body: some View {
        Text("Scanning for devices...")
            .padding()
            .background(.ultraThinMaterial)
            .scaleEffect(isPulsing ? 1.1 : 1.0)
            .animation(.easeInOut.repeatForever(), value: isPulsing)
            .onAppear { isPulsing = true }
    }
}

// ✅ AFTER: Reduce Motion and Reduce Transparency compliance
struct RadarCard: View {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @Environment(\.accessibilityReduceTransparency) private var reduceTransparency
    @State private var isPulsing = false

    var body: some View {
        Text("Scanning for devices...")
            .padding()
            .background(
                reduceTransparency
                    ? AnyShapeStyle(Color(uiColor: .secondarySystemBackground))
                    : AnyShapeStyle(.ultraThinMaterial)
            )
            .scaleEffect(!reduceMotion && isPulsing ? 1.05 : 1.0)
            .animation(
                reduceMotion ? nil : .easeInOut(duration: 1.0).repeatForever(),
                value: isPulsing
            )
            .onAppear {
                if !reduceMotion { isPulsing = true }
            }
            .accessibilityLabel("Scanning for nearby devices")
    }
}
```

---

## 5. Automated Runtime Verification & Tooling

To ensure zero regressions, execute automated assertions across three levels:

1. **Xcode 15+ Native UI Test Audits**:
   ```swift
   func testAccessibilityCompliance() throws {
       let app = XCUIApplication()
       app.launch()
       try app.performAccessibilityAudit(for: [
           .contrast,
           .hitTesting,
           .sufficientElementDescription,
           .dynamicType
       ])
   }
   ```
2. **SwiftUI Canvas Preview Matrices**: Verify views in `.accessibility2` and `.accessibility5` font scales simultaneously with Dark Mode and High Contrast.
3. **Xcode Accessibility Inspector**: Connect via **Xcode > Open Developer Tool > Accessibility Inspector**, trigger the **Audit** tab, and verify 0 warnings across all screens.

---

## 6. Detailed Reference Guides

For deep domain patterns and code implementations, consult the bundled reference documents:
- [VoiceOver Tree, Rotors & Traits](references/voiceover-tree-and-rotors.md)
- [Dynamic Type, @ScaledMetric & AX Layouts](references/dynamic-type-and-scaled-metric.md)
- [Hit Targets & Touch Handling](references/hit-targets-and-touch-handling.md)
- [WCAG Contrast & Color Independence](references/wcag-contrast-and-color.md)
- [Sensory Adaptations: Motion, Materials & Smart Invert](references/sensory-motion-and-materials.md)
- [Automated Testing & Audio Graphs](references/automated-a11y-testing-and-charts.md)
