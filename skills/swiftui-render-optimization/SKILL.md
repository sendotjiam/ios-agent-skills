---
name: swiftui-render-optimization
description: Audits and optimizes SwiftUI view hierarchies for render performance, 120fps/60fps smoothness, and minimal CPU/GPU overhead. Detects view graph invalidation cascades, identity churn (structural vs explicit, AnyView), observation over-invalidation (@Observable vs ObservableObject), main-thread body computation, layout thrashing, lifecycle anti-patterns, and offscreen GPU rendering bottlenecks. Use whenever debugging SwiftUI frame drops, scroll hitches, unexpected re-renders, high CPU during view updates, or optimizing view lifecycle and Observation state tracking.
---

# SwiftUI Render & Performance Optimization Guide

This skill provides an empirical, systematic framework for diagnosing, auditing, and resolving SwiftUI render bottlenecks, view graph thrashing, unnecessary `body` re-evaluations, and frame hitches.

---

## 1. Audit Taxonomy & Severity Tiers

When inspecting code or profiling with Instruments, classify all findings into four severity tiers:

### Critical (Infinite Render Loops / View Graph Destruction / Process Hangs)
- **Inline `@ObservedObject` Initialization**: Defining `@ObservedObject var vm = ViewModel()` without `@StateObject`. Causes the object to be deallocated and re-instantiated on every parent body evaluation, dropping state and resetting view graphs.
- **Mutating State During View Update**: Mutating `@State`, `@Binding`, or `@Published` directly inside `body` or a computed property called during render, triggering runtime warning `Modifying state during view update, this will cause undefined behavior` and 100% CPU lockups.
- **Transient Collection Identity**: Using dynamic transient identifiers in collections (`ForEach(items, id: \.self)` where `id` returns `UUID()`), destroying and recreating all child view nodes, state, and animations on every frame.
- **`@State` in `init()` Desynchronization Trap**: Setting `_state = State(initialValue: param)` in `init`. State storage is created once; subsequent parent updates pass new values that are silently ignored, prompting anti-pattern `.id(UUID())` hacks to force view tree reconstruction.

### High (Over-Invalidation / Frame Drops 16.6ms–100ms / Main-Thread Heavy Work)
- **Heavy Computations in `body`**: Executing synchronous `.sorted()`, `.filter()`, `DateFormatter()`, `NumberFormatter()`, `JSONDecoder()`, or regex compilation inside `var body: some View`.
- **`AnyView` Overuse**: Wrapping dynamic branches in `AnyView`. Erases compile-time structural type identity, forcing SwiftUI to destroy and recreate the underlying RenderNode tree instead of diffing.
- **Coarse Observable Graph Coupling**: Passing an entire `@Observable` model or `ObservableObject` down to small leaf views that only consume one primitive property, triggering wide subtree re-renders whenever any unrelated model property mutates.
- **`ObservableObject` Publishing Storms**: Emitting repeated `objectWillChange` events in tight loops without debouncing, or publishing updates from background queues causing main-thread hop thrashing.
- **Row-Level Modal Sheet Modifiers**: Placing `.sheet(item:)` or `.fullScreenCover` inside `ForEach` rows instead of hoisting to the parent collection container, creating $N$ presentation coordinator bindings.

### Medium (Scroll Hitches / Layout Thrashing / Unbounded Memory)
- **Eager Stacks in `ScrollView`**: Using `VStack` or `HStack` inside a `ScrollView` for large dynamic collections instead of `LazyVStack`, `LazyHStack`, or `List`, forcing immediate instantiation of all row views and images.
- **Nested `GeometryReader` Layout Thrashing**: Nesting `GeometryReader` inside tight `List` or `Lazy` cells, causing multi-pass parent-child layout measurements on every scroll tick.
- **Unscoped Implicit `.animation()`**: Using legacy `.animation(.default)` without the `value:` parameter, causing all unrelated view updates across the entire hierarchy to trigger animations.
- **Uncontrolled `updateUIView` Passes**: Recreating UIKit subviews, delegate bindings, or text in `UIViewRepresentable.updateUIView` without diffing existing values.
- **Offscreen GPU Rasterization Overload**: Stacking heavy `.shadow()`, `.blur()`, `.clipShape()`, and transparency overlays in scrolling lists without `.drawingGroup()` or pre-rendered assets.

### Low (Diagnostic Leftovers / Anti-Patterns / Modernization Opportunities)
- **Forgotten `Self._printChanges()`**: Debug diagnostic calls left in production release builds.
- **Missing `@ObservationIgnored`**: Background timers, cancellables, or cache dictionaries in `@Observable` classes lacking `@ObservationIgnored`.
- **Arbitrary `.id(UUID())` Invalidation**: Forcing full view destruction to solve state sync issues instead of fixing state ownership.
- **Legacy `ObservableObject` in iOS 17+**: Retaining Combine-based `@Published` models where Swift 5.9/6 `@Observable` would provide surgical, property-level observation.

---

## 2. Automated Fast-Scan (CLI Pre-Scan)

Before conducting deep manual AST inspection, run the bundled zero-dependency Python scanner to surface project-wide red flags:

```bash
# Terminal summary of SwiftUI render anti-patterns
python3 scripts/scan_swiftui_renders.py <path/to/ios/project>

# Generate a structured Markdown audit report
python3 scripts/scan_swiftui_renders.py <path/to/ios/project> --format markdown -o swiftui_render_scan.md

# Output JSON for CI/CD gates
python3 scripts/scan_swiftui_renders.py <path/to/ios/project> --format json
```

The scanner analyzes:
- Critical model and state initialization issues (`@ObservedObject = ViewModel()`, `_state = State(initialValue:)`)
- Identity hazards (`AnyView`, volatile `UUID()` in `.id()` or `ForEach`)
- Heavy `body` execution (`.sorted()`, `filter()`, `DateFormatter()`, `JSONDecoder()`)
- Lifecycle issues (`Task {` inside `.onAppear`, side-effects in `init()`)
- Layout & presentation leaks (eager `VStack` in `ScrollView`, `.sheet` inside `ForEach`, unscoped `.animation(`)
- Diagnostic leftovers (`Self._printChanges()`)

---

## 3. Systematic 5-Step Audit Protocol

When evaluating a SwiftUI screen or component, step through these five layers:

```
[1. View Identity & Diffing] -> [2. Observation & State Slicing] -> [3. Body Purity & Computation]
                                              |
[5. GPU Compositing & Offscreen] <- [4. Layout Containers & Lifecycle]
```

### Step 1: Audit View Identity & Hierarchy
1. Check every `ForEach`:
   - Is `id:` stable and immutable (e.g., `\.id` on an `Identifiable` model)?
   - Are elements uniquely keyed, or is `id: \.self` used on mutated structs?
2. Search for `AnyView`:
   - Replace with `@ViewBuilder`, `@ToolbarContentBuilder`, or `Group`.
   - Prefer type-stable control flow (`if / else` or enum matching).
3. Check `.id(...)` modifiers:
   - Is `.id()` used to reset state because `init()` didn't update? Fix state ownership instead of destroying identity.

### Step 2: Audit State Ownership & Observation
1. **Modern SwiftUI (iOS 17+)**:
   - Ensure `@Observable` classes only trigger invalidations on accessed properties.
   - Annotate non-UI state (timers, analytics, background tasks) with `@ObservationIgnored`.
   - Slice large models: pass primitive types (`title: String`) to leaf subviews rather than passing the entire observable class.
2. **Classic SwiftUI (iOS 14-16)**:
   - Audit `@StateObject` vs `@ObservedObject`. If the view owns the lifecycle, it MUST be `@StateObject`.
   - Audit `@Published` emissions. Avoid firing multiple property updates back-to-back; debounce or batch updates.

### Step 3: Enforce `body` Purity & Computation Offloading
1. `var body: some View` must be a **pure function of state**:
   - Zero object allocations (`DateFormatter()`, `NumberFormatter()`, `JSONDecoder()`).
   - Zero array filtering, sorting, or complex mapping. Pre-compute in ViewModel or use cached computed properties.
   - Zero state mutations during evaluation.

### Step 4: Audit Containers, Navigation & Lifecycle
1. Collections:
   - For lists larger than 20 items, replace `ScrollView { VStack { ... } }` with `LazyVStack` or `List`.
2. Lifecycle & Tasks:
   - Replace `.onAppear { Task { ... } }` with `.task { ... }` or `.task(id: trigger) { ... }` for automatic cancellation.
   - Remove analytics or heavy side-effects from struct `init()`.
3. Presentation:
   - Hoist `.sheet(item:)` and `.navigationDestination` outside `ForEach` rows to the parent view.

### Step 5: Audit Layout & GPU Compositing
1. Measure layout passes: Avoid `GeometryReader` inside cell rows. Use preference keys or `.onGeometryChange` (iOS 16+).
2. Animations: Ensure every `.animation()` has an explicit `value:` parameter.
3. GPU Fill-Rate:
   - Minimize complex shadows and overlapping blurs in scrolling rows.
   - Apply `.drawingGroup()` for complex vector graphics or Canvas for high-frequency charts.

---

## 4. Invalidation Debugging Recipes

### 1. Pinpointing Re-Renders with `Self._printChanges()`
Insert `let _ = Self._printChanges()` directly inside the view's `body`:

```swift
var body: some View {
    let _ = Self._printChanges()
    VStack {
        Text(title)
        CustomButton(action: performAction)
    }
}
```
Console output indicates the exact dependency triggering the invalidation:
- `@self changed`: View struct values or captured parameters changed.
- `@identity changed`: Structural or explicit identity reset.
- `_viewModel changed`: Observable state notification fired.

### 2. Xcode Instruments: SwiftUI View Body Track
1. Profile the app using the **Time Profiler** or **SwiftUI** template in Instruments (`Cmd + I`).
2. Add the **SwiftUI View Body** instrument.
3. Filter by View Name:
   - Inspect **Evaluation Count**: Views with hundreds of evaluations during a single scroll event indicate parent over-invalidation.
   - Inspect **Average Duration**: Views with average duration $> 1\text{ms}$ have expensive computations inside `body`.
4. Add the **Core Animation Commits** instrument:
   - Look for **Commit Cost** $> 4\text{ms}$ or recurring hitches ($> 16.6\text{ms}$ at 60fps / $> 8.3\text{ms}$ at 120fps ProMotion).

---

## 5. Structured Audit Report Format

When delivering audit results, use this standardized structure:

````markdown
# SwiftUI Render & Performance Audit Report: [Screen / Feature Name]

## Executive Summary
- **Primary Issue**: [e.g., Severe scroll stutter in FeedView caused by unmemoized array sorting and AnyView identity churn]
- **Frame Budget Impact**: [e.g., 45-60ms body evaluation times, dropping frame rate to ~20fps]
- **Key Bottlenecks**: [Count of Critical / High / Medium / Low findings]

---

## Detailed Findings

### [Finding Title]
- **File & Line**: `[Path/To/File.swift#L45-L60]`
- **Severity**: Critical | High | Medium | Low
- **Category**: Identity | Observation | Body Computation | Lifecycle | Layout/GPU
- **Root Cause**: [Explain why SwiftUI re-evaluates or drops frames]
- **Evidence / Profiling**: [Instruments duration, `Self._printChanges()` output, or AST scanner hit]

#### Anti-Pattern Code:
```swift
// ⚠️ Problematic implementation
```

#### Optimized Fix:
```swift
// ✅ Optimized implementation
```

#### Why it Works:
[Explain view graph diffing, memory stability, or cooperative task cancellation benefit]

---

## Verification & Profiling Plan
- Step-by-step instructions to verify via `Self._printChanges()` and Xcode Instruments.
````

---

## 6. Reference Links
- [`identity-and-viewgraph.md`](references/identity-and-viewgraph.md): Deep dive into structural vs explicit identity, diffing, and `AnyView`.
- [`observation-and-invalidation.md`](references/observation-and-invalidation.md): iOS 17 `@Observable` macro vs Combine `ObservableObject`, fine-grained slicing.
- [`lifecycle-and-state-flow.md`](references/lifecycle-and-state-flow.md): View `init` vs view lifetime, `.task` vs `.onAppear`, `@State` traps.
- [`instruments-profiling-recipes.md`](references/instruments-profiling-recipes.md): Practical recipes for Xcode Instruments SwiftUI and Core Animation tracks.
