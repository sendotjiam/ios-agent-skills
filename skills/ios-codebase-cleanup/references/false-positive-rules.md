# False-Positive Avoidance & Edge-Case Rules

When identifying dead files, unused assets, and dead symbols in iOS/macOS projects, dynamic and framework-level execution patterns can conceal actual usage. Adhere to these triage rules before pruning candidates.

---

## 1. Dynamic Reflection & Objective-C Runtime

### A. `@objc` and `NSObject` Subclasses
- **Pattern**: Classes conforming to `@objc` or inheriting from `NSObject` may be instantiated dynamically via `NSClassFromString("MyApp.FeatureViewController")` or runtime selectors (`#selector(...)`).
- **Triage Action**: Tagged with **Medium Confidence 🟡**. Check for `NSClassFromString`, Storyboards, or runtime registration tables before deleting.

### B. Dynamic Class Loading & Plugin Architectures
- Files conforming to extension points, URL routing protocols (e.g. `AppRouter.register(path: ...)`), or deep link handlers may be referenced only in plist configs or static arrays.

---

## 2. Asset Catalogs (`.xcassets`) & Dynamic Naming

### A. String Interpolation in Asset Names
- **Pattern**:
  ```swift
  let badgeName = "badge_\(user.tier)" // e.g. "badge_gold", "badge_silver"
  Image(badgeName)
  ```
- **Triage Action**: If an asset name has a common prefix (e.g., `badge_`, `icon_tier_`), search for the prefix before marking as dead. Tagged with **Medium Confidence 🟡**.

### B. Generated Asset Symbols (iOS 17+ / Xcode 15+)
- **Pattern**:
  ```swift
  Image(.primaryLogo) // Compiler-generated symbol in Resource extension
  Color(.brandBackground)
  ```
- **Triage Action**: Scanner checks both `"primaryLogo"` string literals and `.primaryLogo` symbol accesses.

---

## 3. Dependency Injection & Service Locators

### A. Container Registrations (Factory, Swinject, Needle)
- **Pattern**:
  ```swift
  Container.shared.register(AnalyticsServiceProtocol.self) { FirebaseAnalyticsService() }
  ```
- **Triage Action**: Ensure implementation classes are checked for references in DI assembly files, even if no direct type instantiation appears in views.

---

## 4. SwiftUI Previews & Design-Time Assets

### A. `#Preview` and `PreviewProvider`
- **Rule**: Files containing `#Preview` or `PreviewProvider` are explicitly preserved as active preview components and are **not** flagged as dead files by default.

### B. Preview Assets Catalog
- Asset catalogs located under `Preview Content/Preview Assets.xcassets` are used exclusively for SwiftUI Canvas rendering and should not be deleted unless the preview itself is removed.

---

## 5. Multi-Target Projects (App Extensions, Widgets, watchOS)

- In projects with multiple targets (e.g. `WidgetExtension`, `WatchApp`, `ShareExtension`), a file or asset may belong exclusively to an extension target.
- Always run the scanner across the entire workspace directory to ensure cross-target references are indexed.
