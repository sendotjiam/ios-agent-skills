---
name: ios-iphone-duo-audit
description: Audits and designs iOS/iPadOS apps for iPhone Duo (Apple's foldable dual-display iPhone, iOS 27.1+). Covers dynamic resizing across compact outer and regular inner displays, 6 device poses, ReservedRegion (.occlusion for outer/inner cameras and Dynamic Island, .division for the center hinge fold), ArrangementView / UIArrangementViewController (.split and .overlay styles), and vertical side-mounted toolbars, tab bars, and navigation bars (mandatory icon+title toolbar items, ToolbarVerticalCompressionBehavior, ToolbarItemVisibilityPriority, ToolbarOverflowMenu, toolbarVerticalEdge, and backgroundExtensionEffect). Use whenever designing, reviewing, migrating, or auditing an iOS app for iPhone Duo, foldable displays, vertical toolbars/tab bars, ArrangementView, or ReservedRegion APIs.
---

# `ios-iphone-duo-audit`

## Purpose
Guides architecture, UI/UX design, and static verification of iOS applications for **iPhone Duo** based on Apple's [Designing for iPhone Duo](https://developer.apple.com/design/human-interface-guidelines/designing-for-iphone-duo) Human Interface Guidelines and [Preparing your app for iPhone Duo](https://developer.apple.com/documentation/technologyoverviews/preparing-your-app-for-iphone-duo) (iOS 27.1+ / Xcode 27+). Ensures seamless continuity as people open, close, partially fold, and rotate the device across outer and inner displays.

---

## ⚡ Fast-Scanner CLI

Run the zero-dependency scanner before or after modifying SwiftUI/UIKit views to catch layout, fold-region, and vertical-bar regressions:

```bash
# Terminal table output
python3 skills/ios-iphone-duo-audit/scripts/scan_iphone_duo.py /path/to/project

# Or via the unified auditor CLI
./bin/ios-audit /path/to/project --skills duo

# Xcode Issue Navigator inline format
python3 skills/ios-iphone-duo-audit/scripts/scan_iphone_duo.py /path/to/project --format xcode

# Machine-readable JSON output
python3 skills/ios-iphone-duo-audit/scripts/scan_iphone_duo.py /path/to/project --format json
```

---

## 🛑 Detection Taxonomy & Severity Tiers

| Severity | Rule ID | Category | Detection Target |
| :--- | :--- | :--- | :--- |
| **Critical** | `DUO_SCREEN_BOUNDS_HARDCODED` | Dynamic Resizing | Hardcoded `UIScreen.main.bounds` or `nativeBounds` sizing that breaks across outer/inner displays, Split View multitasking, and folded poses. |
| **Critical** | `DUO_ARRANGEMENT_INVALID_NESTING` | Arrangement Views | Nesting `ArrangementView` inside `ScrollView`/`List`, or placing `NavigationSplitView`/`TabView` inside `ArrangementView`. |
| **High** | `DUO_IDIOM_OR_ORIENTATION_LAYOUT` | Pose & Size Classes | Branching layout decisions on `UIDevice.current.userInterfaceIdiom` or `UIDevice.current.orientation` / `UIInterfaceOrientation` instead of size classes. |
| **High** | `DUO_HARDCODED_SCREEN_DIMENSION` | Layout Anti-Patterns | Equality or comparison checks against fixed iPhone Duo hardware point dimensions (`466`, `951`, `475.5`). |
| **High** | `DUO_SYMMETRIC_SAFE_AREA_ASSUMPTION` | Safe Area Insets | Multiplying leading/trailing insets by 2 (`inset * 2`) assuming symmetric safe areas on an asymmetric device. |
| **High** | `DUO_TOOLBAR_TEXT_ONLY_ITEM` | Vertical Controls | `ToolbarItem` with a text-only `Button("Title")` lacking an icon. iPhone Duo omits text-only items from vertical side bars. |
| **High** | `DUO_CUSTOM_BAR_BYPASS` | Vertical Controls | Standalone `UIToolbar()`, `UINavigationBar()`, or `UITabBar()` subviews that bypass automatic vertical side-bar presentation. |
| **Medium** | `DUO_FIXED_FRAME_WIDTH` | Dynamic Resizing | Rigid `.frame(width: >= 320)` containers that clip on the compact outer display or Split View multitasking panes. |
| **Medium** | `DUO_ODD_GRID_COLUMNS_ON_FOLD` | Reserved Regions | `LazyVGrid` with an odd number of flexible columns (e.g., 3 columns) where the middle column straddles the center hinge `.division` fold. |
| **Low** | `DUO_MANUAL_TOOLBAR_SPACER` | Vertical Controls | Manual `Spacer(minLength:)` or custom `"ellipsis"` button inside `.toolbar` instead of `ToolbarItemGroup` and `ToolbarOverflowMenu`. |

---

## 📐 Core iPhone Duo Design & Engineering Rules

### 1. Dual Displays & 6 Device Poses
- **Outer Display (Closed)**: Compact width (`466 × 678 pt`, 1398 × 2034 px @ 460 ppi). Reference safe area insets in closed portrait: top `0 pt`, bottom `34 pt` (home indicator), left `0 pt`, right `84 pt` (vertical bar), safe content area `382 × 644 pt`. Asymmetric corner radii: `8 pt` (left) and `59 pt` (right). Toolbars and tab bars sit vertically on the side edge to maximize vertical space for content; outer front-facing camera is always visible in the corner aligned with side controls.
- **Inner Display (Open / Partially Folded)**: Regular width (`951 × 669 pt` in landscape, 2670 × 1878 px @ 430 ppi; `669 × 951 pt` in portrait). Symmetric corner radii: `55 pt`. Supports flat portrait, flat landscape, book pose, tent pose, laptop pose, and Split View multitasking. Reference safe area in open Landscape Left: top `0 pt`, bottom `34 pt`, left `0 pt`, right `84 pt` (safe content area `867 × 635 pt`); in portrait: top `84 pt`, bottom `95 pt`. The inner front-facing camera stays hidden behind the display until active. *(Reference values only — never hardcode insets; always query `safeAreaInsets`, `GeometryReader`, or `ReservedRegion` at runtime.)*
- **Build with iOS 27.1+ SDK (Xcode 27.1 beta `27A9269`)**: Apps built with iOS 26 SDK or earlier sit centered/letterboxed; iOS 27.0 SDK resizes to fill most of the inner display but still avoids the right-edge status bar. Target **iOS 27.1+ SDK** on **macOS Tahoe 26.6+ (Apple silicon)** to unlock full-screen mode, vertical bars, and reserved-region APIs. TestFlight accepts both `27.1 beta` and `27.2 beta 2 (27B5028f)` builds, though confirm Duo SDK/runtime support separately before switching to `27.2`.
- **Strict `.phone` Idiom**: iPhone Duo runs exclusively under the `.phone` idiom (`UIDevice.current.userInterfaceIdiom == .phone`). A regular-width inner window does not make the app an iPad target; never branch on `.pad`.
- **Never design custom layouts per pose**: Use `horizontalSizeClass` and `verticalSizeClass` (Compact for outer display, Regular for inner display) plus `NavigationSplitView` so hierarchies expand naturally (e.g., Mail shows a single list or message on the outer display, and side-by-side list + message on the inner display).

### 2. Reserved Regions vs. Safe Areas
- **Safe Areas & Layout Margins**: Describe bounds around system UI bars (status bar, home indicator, vertical navigation bar) and default content margins (`20 pt`). Always treat edges independently; never mirror insets.
- **`.occlusion`**: Hardware areas that cover content (always-present outer camera/Dynamic Island, and conditional inner camera when active).
- **`.division`**: Active when iPhone Duo is partially folded, dividing the inner display at the center hinge crease (center fold at `475.5 pt`).
- **Grid & Custom View Adaptation**: Prefer even column counts in grids so items divide cleanly across the fold. In custom canvases, read `proxy.reservedRegions(kind: .division)` (SwiftUI) or `view.reservedRegions(kind: .division)` (UIKit) and make subtle positional adjustments rather than jarring layout rearrangements.

### 3. Arrangement Views (`ArrangementView` / `UIArrangementViewController`)
- **`.split` Style**: Places `primary` and `secondary` views side-by-side when wide or stacked when tall, automatically parting around `.division` fold regions. Use where you would otherwise write conditional `HStack`/`VStack` logic.
- **`.overlay` Style**: Layers `primary` over `secondary` when the display is flat (closed or fully open), and automatically separates them onto opposite sides of the fold when partially open (ideal for video/camera surfaces with floating transport controls).
- **Boundary Constraint**: Keep navigation containers (`NavigationSplitView`, `TabView`, `NavigationStack`) *outside* of `ArrangementView`, and never embed `ArrangementView` inside a `ScrollView` or `List`.

### 4. Vertical Side Bars, Compression & Overflow
- **Side-Mounted Axis**: On the outer display and inner landscape/Split View, the system stacks Dynamic Island $\rightarrow$ Status Bar $\rightarrow$ Toolbar $\rightarrow$ Tab Bar vertically along the outer edge.
- **Always Provide Title + Icon**: Vertical bars display icons only; overflow menus display icon + title. Text-only buttons or custom view items are excluded from vertical bars. Always use `Label("Action", systemImage: "...")` or `Button("Action", systemImage: "...")`.
- **Placement Order & Grouping**:
  - Top of vertical axis: Primary navigation (`Back` / `.cancellationAction` `Close`), followed by `.topBarPinnedTrailing` / `pinnedTrailingGroup` (`Done`).
  - Group related items with `ToolbarItemGroup` / `UIBarButtonItemGroup` instead of manual fixed spacers.
  - Items overflow from **bottom to top** by default; customize retention with `.visibilityPriority(_:)` (`ToolbarItemVisibilityPriority`).
- **Bar Compression (`ToolbarVerticalCompressionBehavior` / `UIVerticalBarCompressionBehavior`)**:
  - Navigation-focused views: `.prefersTabBar` (default — collapses toolbar items into overflow first to keep tab destinations visible).
  - Task-oriented views: `.prefersToolbarItems` (collapses tab bar into a single control to keep central task actions visible).
- **Pane Proximity in Split Views**: Keep controls that affect a leading sidebar/list horizontally at the top of that leading pane; only controls for the trailing detail pane move to the trailing vertical bar.
- **System Overflow & Full-Width Backgrounds**: Place secondary actions in `ToolbarOverflowMenu` / `additionalOverflowItems` (reserve the `ellipsis` symbol exclusively for the system overflow menu). Use `.backgroundExtensionEffect()` or `UIBackgroundExtensionView` so hero backgrounds extend seamlessly beneath vertical side bars.

### 5. WKWebView, Simulator Caveats & Continuous Task Verification
- **WKWebView Boundaries**: Document whether the native container or web CSS owns safe-area padding (avoid double-padding with `env(safe-area-inset-*)`). Use `100dvh` and test Safari 27 scroll anchoring (`overflow-anchor: none`), and do not assume Safari's experimental `device-posture` / `viewport-segment-*` flags are enabled in app-hosted `WKWebView`.
- **Xcode Simulator / Device Hub**: Test open, close, fold, and Split View transitions during one continuous task rather than taking static screenshots.
- **Known Beta Limitations**: StandBy is unavailable in the Duo simulator runtime; debugging most app extensions is limited; first simulator boot may take several minutes.
- **Previews**: In SwiftUI Previews, use the *Display* group in the canvas overrides picker to verify views on the alternate display.
- **Mac Catalyst Considerations**: Guard iOS 27.1-only APIs with `#if !targetEnvironment(macCatalyst)` or set minimum Mac Catalyst deployment to 27.0.
- **20-Point Verification**: Execute the 5 verification tiers (Scope & Environment, Design & Layout, State & Interaction, WebView & Input, Accessibility & Delivery) in [20-Point Verification & WKWebView Checklist](./references/verification-checklist.md) before sign-off.

---

## 📖 Bundled References & Recipes
- [Dynamic Layouts, Reserved Regions & Arrangement Views](./references/dynamic-layouts-and-reserved-regions.md)
- [Vertical Axis Controls, Bar Compression & Overflow Menus](./references/vertical-bars-and-overflow.md)
- [20-Point Verification & WKWebView Checklist](./references/verification-checklist.md)
- [Benchmark Evaluation Report](./evals/benchmark.md)
