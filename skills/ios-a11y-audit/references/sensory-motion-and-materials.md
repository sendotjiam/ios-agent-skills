# Sensory Adaptations: Motion, Materials & Smart Invert

Users with vestibular disorders, motion sensitivity, migraine triggers, or severe low vision rely on system accessibility toggles to eliminate disorientation, eye fatigue, and illegible text.

---

## 1. Vestibular Protection & Reduce Motion

Rapid translations, 3D rotations, looping spinning animations, and parallax shifts can trigger acute vertigo, nausea, and migraines for users with vestibular system disorders.

### In SwiftUI: `@Environment(\.accessibilityReduceMotion)`
```swift
// ❌ ANTI-PATTERN: Unmitigated infinite rotation causing motion sickness
struct LoadingSpinner: View {
    @State private var isSpinning = false

    var body: some View {
        Image(systemName: "arrow.triangle.2.circlepath")
            .rotationEffect(.degrees(isSpinning ? 360 : 0))
            .animation(.linear(duration: 1).repeatForever(autoreverses: false), value: isSpinning)
            .onAppear { isSpinning = true }
    }
}

// ✅ MODERN SWIFTUI: Vestibular-safe loading animation
struct SafeLoadingSpinner: View {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var isSpinning = false
    @State private var pulseOpacity = 0.5

    var body: some View {
        Group {
            if reduceMotion {
                // Static or gentle pulse cross-fade instead of spinning
                Image(systemName: "arrow.triangle.2.circlepath")
                    .opacity(pulseOpacity)
                    .onAppear {
                        withAnimation(.easeInOut(duration: 0.8).repeatForever()) {
                            pulseOpacity = 1.0
                        }
                    }
            } else {
                Image(systemName: "arrow.triangle.2.circlepath")
                    .rotationEffect(.degrees(isSpinning ? 360 : 0))
                    .animation(.linear(duration: 1).repeatForever(autoreverses: false), value: isSpinning)
                    .onAppear { isSpinning = true }
            }
        }
        .accessibilityLabel("Loading content")
    }
}
```

### In UIKit: `UIAccessibility.isReduceMotionEnabled`
```swift
if UIAccessibility.isReduceMotionEnabled {
    // Perform gentle alpha cross-fade
    UIView.transition(with: containerView, duration: 0.25, options: .transitionCrossDissolve) {
        self.activeView.isHidden = true
        self.nextView.isHidden = false
    }
} else {
    // Perform full spatial slide-in transition
    animateSlideTransition()
}
```

---

## 2. Reduce Transparency & Glassmorphic Fallbacks

Glassmorphic materials (`.ultraThinMaterial`, `UIBlurEffect`) blur background images or text. Low-vision users and users prone to eye strain enable **Reduce Transparency** (`Settings > Accessibility > Display & Text Size > Reduce Transparency`). Apps must supply solid, high-contrast surface fallbacks:

```swift
// ❌ ANTI-PATTERN: Text floating over translucent blur without fallback
struct FloatingActionCard: View {
    var body: some View {
        VStack {
            Text("Complete Profile").font(.headline)
            Text("Add photo to finish").font(.subheadline)
        }
        .padding()
        .background(.ultraThinMaterial) // Ineligible when complex content scrolls beneath
        .cornerRadius(16)
    }
}

// ✅ MODERN SWIFTUI: Solid fallback when Reduce Transparency is active
struct FloatingActionCard: View {
    @Environment(\.accessibilityReduceTransparency) private var reduceTransparency

    var body: some View {
        VStack {
            Text("Complete Profile").font(.headline)
            Text("Add photo to finish").font(.subheadline)
        }
        .padding()
        .background(
            reduceTransparency
                ? AnyShapeStyle(Color(uiColor: .secondarySystemBackground))
                : AnyShapeStyle(.ultraThinMaterial)
        )
        .cornerRadius(16)
    }
}
```

---

## 3. Smart Invert Protection (`accessibilityIgnoresInvertColors`)

When users enable **Smart Invert** (`Settings > Accessibility > Display & Text Size > Smart Invert`), iOS inverts user interface colors (turning light surfaces dark) while attempting to preserve media. However, custom image renderers, photo previews, video players, and avatar stacks often get inverted into photographic negatives unless explicitly protected:

```swift
// ❌ ANTI-PATTERN: Avatar turns into an inverted photographic negative
AsyncImage(url: user.avatarURL) { image in
    image.resizable().scaledToFill()
} placeholder: {
    ProgressView()
}
.frame(width: 60, height: 60)
.clipShape(Circle())

// ✅ MODERN SWIFTUI: Preserved true colors under Smart Invert
AsyncImage(url: user.avatarURL) { image in
    image.resizable().scaledToFill()
} placeholder: {
    ProgressView()
}
.frame(width: 60, height: 60)
.clipShape(Circle())
.accessibilityIgnoresInvertColors(true) // Protects from photo color inversion
```

### In UIKit:
```swift
let imageView = UIImageView(image: photo)
imageView.accessibilityIgnoresInvertColors = true
```

---

## 4. Media & Closed Captioning Verification

For apps delivering video or audio payloads:
1. Ensure `AVPlayerViewController` has closed caption and subtitle tracks exposed (`player.currentItem?.tracks`).
2. Verify audio cues (e.g. notification chime or error buzz) are paired with visual toast notifications or haptic feedback.
