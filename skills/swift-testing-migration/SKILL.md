---
name: swift-testing-migration
description: Audits iOS, iPadOS, macOS, and watchOS test suites for modernization to the WWDC24 Swift Testing framework (@Suite, @Test, #expect, #require), parameterized arguments, eliminating flaky Thread.sleep in async tests, and migrating XCTest expectations to confirmations.
---

# `swift-testing-migration`

## Purpose
A modernization and code health auditor for Apple platforms focused on migrating legacy `XCTestCase` suites to Apple's modern **Swift Testing** framework (introduced in Xcode 16 / Swift 6). Identifies parameterized testing candidates, eliminates flaky sleep delays, and migrates legacy assertion macros.

---

## ⚡ Fast-Scanner CLI

```bash
# Terminal table output
python3 skills/swift-testing-migration/scripts/scan_test_migration.py /path/to/tests

# Xcode Issue Navigator inline format
python3 skills/swift-testing-migration/scripts/scan_test_migration.py /path/to/tests --format xcode

# Machine-readable JSON output
python3 skills/swift-testing-migration/scripts/scan_test_migration.py /path/to/tests --format json
```

---

## 🧪 Detection Taxonomy & Severity Tiers

| Severity | Rule ID | Category | Detection Target |
| :--- | :--- | :--- | :--- |
| **High** | `TEST_LEGACY_XCTESTCASE_CLASS` | Suite Architecture | `class FooTests: XCTestCase` candidate for `@Suite struct FooTests`. |
| **High** | `TEST_FLAKY_SLEEP_WAIT` | Test Reliability | `Thread.sleep` or `Task.sleep` used for async synchronization. |
| **Medium** | `TEST_PARAMETERIZED_CANDIDATE` | Parameterization | For-in loops running assertions candidate for `@Test(arguments: [...])`. |
| **Medium** | `TEST_LEGACY_XCT_EXPECTATION` | Async Testing | `expectation(description:)` candidate for `await confirmation(...)`. |
| **Low** | `TEST_LEGACY_ASSERT_*` | Assertion Macros | `XCTAssertEqual`, `XCTAssertTrue`, `XCTAssertNil` $\rightarrow$ `#expect(...)`. |

---

## 📖 Bundled References & Recipes
- [Swift Testing Migration Guide](./references/swift-testing-migration-guide.md)
- [Parameterized Testing with @Test(arguments:)](./references/parameterized-testing-and-arguments.md)
- [Benchmark Evaluation Report](./evals/benchmark.md)
