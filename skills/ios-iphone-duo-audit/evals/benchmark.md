# Benchmark Evaluation Report: `ios-iphone-duo-audit`

| Eval ID | Fixture | Target Rules Verified | Status |
| :--- | :--- | :--- | :--- |
| **Eval 1** | `eval1_screen_and_idiom_layout.swift` | `DUO_SCREEN_BOUNDS_HARDCODED`, `DUO_IDIOM_OR_ORIENTATION_LAYOUT`, `DUO_FIXED_FRAME_WIDTH` | ✅ 100% Pass |
| **Eval 2** | `eval2_arrangement_and_fold_hazards.swift` | `DUO_ARRANGEMENT_INVALID_NESTING` (ScrollView + NavigationSplitView), `DUO_ODD_GRID_COLUMNS_ON_FOLD` | ✅ 100% Pass |
| **Eval 3** | `eval3_vertical_toolbar_hazards.swift` | `DUO_TOOLBAR_TEXT_ONLY_ITEM`, `DUO_MANUAL_TOOLBAR_SPACER` | ✅ 100% Pass |
| **Eval 4** | `eval4_uikit_custom_bars.swift` | `DUO_CUSTOM_BAR_BYPASS` (`UIToolbar()`, `UITabBar()`) | ✅ 100% Pass |
