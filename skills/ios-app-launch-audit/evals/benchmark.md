# Benchmark Evaluation Report: `ios-app-launch-audit`

## Summary
- **Suite**: `ios-app-launch-audit` Evaluation Benchmark
- **Pass Rate**: 100.0% (4/4 scenarios passed)
- **Rules Detected**: 6/6 (100.0%)
- **Total Execution Duration**: ~1.74ms

## Scenario Results

| Scenario File | Target Area | Expected Rules | Detected | Duration | Status |
| :--- | :--- | :--- | :---: | :---: | :---: |
| `eval1_appdelegate_blocking.swift` | Blocking I/O & Obsolete Sync in Launch | `LAUNCH_BLOCKING_FILE_IO`, `LAUNCH_OBSOLETE_USERDEFAULTS_SYNC` | 2/2 | 0.75ms | ✅ Passed |
| `eval2_sync_persistence_launch.swift` | Synchronous Store Loading in @main init | `LAUNCH_SYNC_PERSISTENCE_LOAD` | 1/1 | 0.52ms | ✅ Passed |
| `eval3_objc_load_and_statics.m` | Pre-Main dyld Overhead (+load) | `LAUNCH_OBJC_PLUS_LOAD` | 1/1 | 0.17ms | ✅ Passed |
| `eval4_sdk_init_bloat.swift` | Synchronous SDK Setup in didFinishLaunching | `LAUNCH_SDK_INIT_FIREBASE`, `LAUNCH_SDK_INIT_SENTRY` | 2/2 | 0.15ms | ✅ Passed |
