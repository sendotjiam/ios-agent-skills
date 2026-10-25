# Automated Accessibility Testing & Swift Charts Audio Graphs

Empirical accessibility testing prevents regressions before code lands in production. This guide details Xcode 15+ automated accessibility audits, Swift Charts audio graph sonification (`AXChartDescriptor`), and SwiftUI preview matrices.

---

## 1. Xcode 15+ Automated Accessibility Audits (`XCTest`)

Starting with iOS 17 and Xcode 15, `XCUIApplication` provides native accessibility auditing that automatically traverses view hierarchies to detect contrast issues, insufficient touch target sizes, missing descriptions, and Dynamic Type clipping.

```swift
import XCTest

final class AccessibilityAuditUITests: XCTestCase {
    func testMainScreensAccessibility() throws {
        let app = XCUIApplication()
        app.launch()

        // 1. Audit HomeScreen
        try app.performAccessibilityAudit(for: [
            .contrast,
            .hitTesting,
            .sufficientElementDescription,
            .dynamicType
        ]) { issue in
            // Filter out known vendor false positives if necessary
            if issue.element.identifier == "ThirdPartyBannerAd" {
                return true // Ignore specific issue
            }
            return false // Fail test on issue
        }

        // 2. Navigate to Settings and audit
        app.buttons["Settings"].tap()
        try app.performAccessibilityAudit(for: [
            .contrast,
            .hitTesting,
            .sufficientElementDescription
        ])
    }
}
```

### Supported Audit Issue Types

| Issue Type (`XCUIAccessibilityAuditType`) | What Xcode Detects |
| :--- | :--- |
| `.contrast` | Text or non-text contrast failing WCAG AA (4.5:1 or 3:1) |
| `.hitTesting` | Interactive elements with active tap area $< 44\times 44\text{pt}$ |
| `.sufficientElementDescription` | Interactive controls missing labels or accessibility elements |
| `.dynamicType` | Text clipped or truncated when font scale changes |
| `.elementDetection` | Untagged visual elements that should be accessibility elements |

---

## 2. Swift Charts & Audio Graph Sonification (`AXChartDescriptor`)

Blind and low-vision users cannot view graphical charts. Apple provides **Audio Graphs**, allowing VoiceOver users to listen to data trends via musical pitch (higher pitch = higher value) and read summary statistics.

### Conforming Custom or Swift Charts to `AXChartDescriptorRepresentable`
```swift
import SwiftUI
import Charts
import Accessibility

struct RevenueDataPoint: Identifiable {
    let id = UUID()
    let month: String
    let value: Double
}

struct AccessibleRevenueChart: View {
    let data: [RevenueDataPoint]

    var body: some View {
        Chart(data) { point in
            BarMark(
                x: .value("Month", point.month),
                y: .value("Revenue ($K)", point.value)
            )
            .foregroundStyle(.blue)
        }
        .frame(height: 250)
        .accessibilityChartDescriptor(self)
    }
}

extension AccessibleRevenueChart: AXChartDescriptorRepresentable {
    func makeChartDescriptor() -> AXChartDescriptor {
        let xAxis = AXCategoricalDataAxisDescriptor(
            title: "Month",
            categoryOrder: data.map { $0.month }
        )

        let minVal = data.map(\.value).min() ?? 0
        let maxVal = data.map(\.value).max() ?? 100

        let yAxis = AXNumericDataAxisDescriptor(
            title: "Revenue in Thousands",
            range: minVal...maxVal,
            gridlinePositions: []
        ) { value in "$\(Int(value))K" }

        let series = AXDataSeriesDescriptor(
            name: "Monthly Revenue",
            isContinuous: false,
            dataPoints: data.map { point in
                AXDataPoint(
                    x: .category(point.month),
                    y: .number(point.value)
                )
            }
        )

        return AXChartDescriptor(
            title: "2026 Monthly Revenue",
            summary: "Bar chart displaying revenue across months, peaking in December at $\(Int(maxVal))K.",
            xAxis: xAxis,
            yAxis: yAxis,
            additionalAxes: [],
            series: [series]
        )
    }
}
```

---

## 3. SwiftUI Preview Accessibility Matrix

Audit views rapidly in Xcode Canvas across multiple Dynamic Type sizes, dark mode, and high contrast without launching simulators:

```swift
#Preview("Dynamic Type Matrix") {
    ScrollView {
        VStack(spacing: 24) {
            Text("Default Size (Large)").font(.caption).foregroundColor(.secondary)
            UserProfileCard()
                .environment(\.dynamicTypeSize, .large)

            Divider()

            Text("Accessibility XXL (AX2)").font(.caption).foregroundColor(.secondary)
            UserProfileCard()
                .environment(\.dynamicTypeSize, .accessibility2)

            Divider()

            Text("Accessibility XXXL (AX5)").font(.caption).foregroundColor(.secondary)
            UserProfileCard()
                .environment(\.dynamicTypeSize, .accessibility5)
        }
        .padding()
    }
}

#Preview("High Contrast & Dark Mode") {
    UserProfileCard()
        .preferredColorScheme(.dark)
        .environment(\.colorSchemeContrast, .increased)
}
```

---

## 4. CI/CD Integration: GitHub Actions

Automate static scanning on every pull request using the zero-dependency Python scanner:

```yaml
name: Accessibility Audit

on:
  pull_request:
    paths:
      - '**/*.swift'

jobs:
  a11y-audit:
    runs-on: macos-14
    steps:
      - uses: actions/checkout@v4

      - name: Run Fast Accessibility Scanner
        run: |
          python3 skills/ios-a11y-audit/scripts/scan_a11y.py . --min-severity high --format markdown -o a11y_summary.md

      - name: Post Summary to PR
        if: failure() || success()
        run: |
          cat a11y_summary.md >> $GITHUB_STEP_SUMMARY
```
