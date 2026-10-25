# Evaluation Benchmark: `coredata-swiftdata-audit`

Automated test execution results for the zero-dependency Python scanner and diagnostic rules against realistic iOS persistence test fixtures.

---

## 📊 Summary Performance Metrics

| Metric | Result | Target Benchmark | Status |
|---|---|---|---|
| **Scenario Pass Rate** | **100.0%** (4 / 4) | 100.0% | ✅ **Passed** |
| **Rule Detection Rate** | **100.0%** (17 / 17) | $\ge 95.0\%$ | ✅ **Passed** |
| **Total Suite Scan Time** | **4.55 ms** | $< 250\text{ ms}$ | ⚡ **Ultra-Fast** |
| **Average Latency per File** | **1.14 ms** | $< 50\text{ ms}$ | ⚡ **Ultra-Fast** |
| **External Dependencies** | **0** (Pure Python 3 standard library) | 0 | ✅ **Zero-Dep** |

---

## 🧪 Detailed Scenario Evaluations

### Scenario 1: `ConcurrencyViolations.swift`
- **File:** `evals/files/ConcurrencyViolations.swift` (51 lines)
- **Scan Latency:** `2.20 ms`
- **Status:** ✅ **Passed (5/5 Rules Detected)**
  - `CD_THREAD_UNCONFINED_ACCESS` (Critical): Detected unconfined context save inside background queue without `perform`.
  - `CD_TASK_DETACHED_CONTEXT_LEAK` (Critical): Detected context mutation inside detached Task boundary.
  - `CD_VIEWCONTEXT_BACKGROUND_ACCESS` (Critical): Detected `viewContext` access inside async function without `@MainActor`.
  - `SWIFTDATA_UNISOLATED_MODEL_CONTEXT` (Critical): Detected unisolated `ModelContext(modelContainer)` instantiation without `@ModelActor`.
  - `SWIFTDATA_MAINCONTEXT_IN_TASK` (Critical): Detected `modelContainer.mainContext` access inside detached Task.

### Scenario 2: `FaultThrashingNPlusOne.swift`
- **File:** `evals/files/FaultThrashingNPlusOne.swift` (52 lines)
- **Scan Latency:** `1.03 ms`
- **Status:** ✅ **Passed (3/3 Rules Detected)**
  - `CD_FETCH_MISSING_BATCH_SIZE` (Medium): Detected `NSFetchRequest` executed without setting `fetchBatchSize`.
  - `CD_FAULT_THRASHING_N_PLUS_ONE` (Medium): Detected nested loop traversing related entity `employees` causing N+1 fault trips.
  - `REACTIVE_QUERY_SEARCH_THRASH` (Medium): Detected `.searchable(text: $searchText)` bound directly to `@Query` without debouncing.

### Scenario 3: `BatchingAndMemoryBloat.swift`
- **File:** `evals/files/BatchingAndMemoryBloat.swift` (35 lines)
- **Scan Latency:** `0.63 ms`
- **Status:** ✅ **Passed (3/3 Rules Detected)**
  - `CD_MISSING_AUTO_MERGE` (High): Detected `newBackgroundContext()` created without `automaticallyMergesChangesFromParent = true`.
  - `CD_LOOP_ROW_BY_ROW_DELETE` (High): Detected row-by-row `context.delete(log)` in loop instead of `NSBatchDeleteRequest`.
  - `CD_UNBOUNDED_BATCH_IMPORT` (High): Detected loop saving records without `context.reset()` or `@autoreleasepool`.

### Scenario 4: `CloudKitAndMultiContextViolations.swift`
- **File:** `evals/files/CloudKitAndMultiContextViolations.swift` (58 lines)
- **Scan Latency:** `0.51 ms`
- **Status:** ✅ **Passed (6/6 Rules Detected)**
  - `CD_SYNCHRONOUS_STORE_LOAD` (Low): Detected `loadPersistentStores` called synchronously on main thread during `didFinishLaunchingWithOptions`.
  - `CLOUDKIT_MISSING_RELATIONSHIP_INVERSE` (Critical): Detected `@Relationship` lacking explicit `inverse:` declaration in CloudKit-enabled container.
  - `CLOUDKIT_UNSUPPORTED_UNIQUE_CONSTRAINT` (Critical): Detected `@Attribute(.unique)` on model under CloudKit sync.
  - `PERSISTENCE_LARGE_BINARY_INLINE` (High): Detected binary `Data` property stored inline without `@Attribute(.externalStorage)`.
  - `SWIFTDATA_UNMARKED_TRANSIENT_PROPERTY` (Medium): Detected UI state property `cachedThumbnail: UIImage?` without `@Transient`.
  - `PERSISTENCE_PREVIEW_DISK_LEAK` (Low): Detected `#Preview` creating disk-backed `ModelContainer` without `isStoredInMemoryOnly: true`.

---

## 🔬 Reproducibility

To re-run this evaluation benchmark independently:

```bash
python3 skills/coredata-swiftdata-audit/evals/test_scanner.py
```
