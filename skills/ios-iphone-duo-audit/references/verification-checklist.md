# iPhone Duo 20-Point Verification & WKWebView Checklist

Derived from Plurigent's *App Testing Checklist*, *WKWebView Guide*, and *20-Point Adaptation Checklist* (Oct 2026). Execute against one continuous user task across transitions rather than isolated screenshots.

---

## WKWebView & Hybrid Container Rules

- **Native–Web Space Ownership**: Establish whether the native `WKWebView` container already respects safe-area insets. If the native container is inset, applying `env(safe-area-inset-*)` in CSS causes **double padding**. Only use CSS safe-area insets with `viewport-fit=cover` on an edge-to-edge web container.
- **No Experimental Fold Flags in WKWebView**: `navigator.devicePosture`, `device-posture` media queries, and `env(viewport-segment-*)` sit behind experimental Safari Feature Flags and are **not** exposed in app-hosted `WKWebView` by default. Always keep a responsive CSS fallback.
- **Dynamic Viewport & Scroll Anchoring**: Use `100dvh` (`svh`, `lvh`) for full-height containers, and watch for interactions between Safari 27 default scroll anchoring (`overflow-anchor: none` to opt out) and SPA/virtualized list scroll restoration.

---

## 20-Point Adaptation Audit Checklist

### 1. Scope & Environment
1. **Record environment baseline**: Document macOS version, full Xcode build, SDK, app build/commit, and evidence category (`Physical Device`, `Xcode Simulator / Device Hub`, `Online Preview`, or `Code Inspection`).
2. **Define adaptation scope**: Identify the core user task and explicit exclusions for the pass.
3. **Keep an original baseline build**: Compare against pre-iOS 27.1 behavior to distinguish new regressions from existing issues.

### 2. Design & Layout
4. **Content priority across sizes**: Essential content and actions remain reachable in compact outer and roomy inner layouts.
5. **Asymmetric safe areas**: Verify each edge independently; never assume opposite edges have equal insets.
6. **Controls near folding regions**: Verify interactive elements clear `.division` fold regions (`475.5 pt` center) on the actual target.
7. **Long copy and empty states**: Test multiline headings, errors, empty lists, and overflow in narrow panes.

### 3. State & Interaction
8. **Preserve form drafts**: Resize and fold while typing; confirm input values, validation state, and focus survive.
9. **Selection & navigation coherence**: Confirm list selection and back navigation remain consistent when expanding/collapsing panes.
10. **Prevent duplicate requests on resize**: Check network/business logs to confirm layout callbacks do not re-trigger fetches.
11. **Operable dialogs & overlays**: Resize/fold with sheets, popovers, or alerts open; verify fold avoidance, focus, and dismissibility.
12. **Background/scene restoration**: Define and verify restoration for unfinished drafts, media, and in-flight operations.

### 4. WebView & Input
13. **Agree native/web space ownership**: Document which layer owns safe areas, scrolling, and keyboard inset adjustments.
14. **Prevent unintentional reloads on resize**: Verify components, routes, and `WKWebView` instances survive size transitions without reloading.
15. **Reachable inputs with keyboard**: Verify text inputs, errors, and submit actions stay usable when the software keyboard is active (do not rely solely on `dvh`).
16. **Long-list scroll positioning**: Verify scroll position remains sensible after narrowing and restoring container width.

### 5. Accessibility, Testing & Delivery
17. **Larger text & assistive tech**: Test with Accessibility Dynamic Type sizes, VoiceOver, and display accommodations.
18. **Verify third-party SDKs separately**: Exercise camera, maps, payments, and media components independently.
19. **Segregate evidence labels**: Keep `Pass`, `Issue`, `Not checked`, and `Not applicable` distinct; never substitute Simulator results for physical-device verification.
20. **Assign owners & recheck before release**: Re-run affected matrix rows after fixes and verify App Store submission/asset requirements separately from TestFlight beta acceptance.
