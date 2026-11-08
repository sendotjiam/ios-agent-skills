# Benchmark Evaluation Report: `swift-testing-migration`

## Summary
- **Suite**: `swift-testing-migration` Evaluation Benchmark
- **Pass Rate**: 100.0% (4/4 scenarios passed)
- **Rules Detected**: 10/10 (100.0%)
- **Total Execution Duration**: ~1.65ms

## Scenario Results

| Scenario File | Target Area | Expected Rules | Detected | Duration | Status |
| :--- | :--- | :--- | :---: | :---: | :---: |
| `eval1_legacy_xctest_assertions.swift` | XCTestCase & XCTAssert* Macros | `TEST_LEGACY_XCTESTCASE_CLASS`, `TEST_LEGACY_ASSERT_EQUAL`, `TEST_LEGACY_ASSERT_TRUE`, `TEST_LEGACY_ASSERT_NIL` | 4/4 | 0.94ms | ✅ Passed |
| `eval2_loop_parameterized.swift` | Loop Assertions to @Test(arguments:) | `TEST_LEGACY_XCTESTCASE_CLASS`, `TEST_PARAMETERIZED_CANDIDATE` | 2/2 | 0.21ms | ✅ Passed |
| `eval3_flaky_sleep_async.swift` | Flaky Thread.sleep in Async Tests | `TEST_LEGACY_XCTESTCASE_CLASS`, `TEST_FLAKY_SLEEP_WAIT` | 2/2 | 0.18ms | ✅ Passed |
| `eval4_expectation_wait.swift` | Legacy Expectation to Confirmation | `TEST_LEGACY_XCTESTCASE_CLASS`, `TEST_LEGACY_XCT_EXPECTATION` | 2/2 | 0.15ms | ✅ Passed |
