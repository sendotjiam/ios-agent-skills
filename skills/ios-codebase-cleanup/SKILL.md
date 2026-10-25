---
name: ios-codebase-cleanup
description: Scan iOS, macOS, and Swift codebases to detect and safely clean up unused files, dead asset catalogs (.imageset, .colorset, .appiconset), orphaned documentation (.md, loose images), dead code symbols (unused private functions/properties), and unused imports. Always trigger this skill whenever the user asks to "clean up unused files", "find dead code", "remove unused assets", "clean codebase", "audit unused images", "prune project", or mentions deleting stale Swift files, assets, or documentation.
---

# iOS Codebase Cleanup Skill (`ios-codebase-cleanup`)

A comprehensive, production-grade auditing and cleanup skill for Apple platforms (iOS, iPadOS, macOS, watchOS, visionOS). Scans the codebase for dead files, orphaned assets, unreferenced documentation, and dead internal symbols, providing a non-destructive triage table and an automated, git-safe pruning workflow with Xcode `project.pbxproj` synchronization.

---

## ⚡ Quick Start: Running the CLI Fast-Scanner

The skill bundles a zero-dependency Python 3 scanner (`scripts/scan_codebase_cleanup.py`) that indexes and audits projects in <2 seconds.

```bash
# 1. Non-destructive Dry-Run Audit (Files, Assets, Docs)
python3 skills/ios-codebase-cleanup/scripts/scan_codebase_cleanup.py /path/to/project

# 2. Deep symbol-level audit (Dead functions, properties, imports)
python3 skills/ios-codebase-cleanup/scripts/scan_codebase_cleanup.py /path/to/project --scope all

# 3. Export structured Markdown for Pull Request review
python3 skills/ios-codebase-cleanup/scripts/scan_codebase_cleanup.py /path/to/project --format markdown -o cleanup_audit.md

# 4. Execute Safe Deletion (Creates git branch + cleans PBXProj)
python3 skills/ios-codebase-cleanup/scripts/scan_codebase_cleanup.py /path/to/project --delete
```

---

## 🔍 Core Detection Taxonomy

| Category | Target Types | Detection Method | Confidence |
| :--- | :--- | :--- | :--- |
| **Dead Swift Files** | `.swift` | Extracts top-level declarations (`class`, `struct`, `enum`, `protocol`, `actor`). Checks for 0 external references across project. Excludes `@main`, App Delegate, and `#Preview` blocks. | 🔴 High (or 🟡 Medium if `@objc` present) |
| **Dead Asset Catalogs** | `.imageset`, `.colorset`, `.appiconset`, `.symbolset` | Scans `.xcassets`. Cross-checks asset names against string literals (`"icon"`), iOS 17 generated symbols (`.icon`), Storyboards, and XIBs. | 🔴 High |
| **Orphaned Docs & Images** | `.md`, `.png`, `.svg` | Checks loose images for markdown/code links; flags `.md` files unlinked in `README.md` or navigation indices. | 🟡 Medium |
| **Dead Code Symbols** | `private func`, `private var/let` | Scans inside active files for declarations with zero calls within their enclosing file. | 🔴 High |
| **Unused Imports** | `import Module` | Identifies module imports whose symbols are never invoked in the source body. | 🟡 Medium |

---

## 🛡 Safety & Verification Workflow

```
┌─────────────────────────────────┐
│  Phase 1: Fast Scan & Triage    │  python3 scan_codebase_cleanup.py . --dry-run
│  (Read-Only Audit Table)        │  Classifies findings by type, size, and confidence
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│  Phase 2: Human Sign-off Gate   │  Present findings to user; confirm files to prune
│  (Selection & Review)           │  Exclude false-positive candidates (see references/)
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│  Phase 3: Git Safety Branch     │  git checkout -b cleanup/ios-codebase-YYYYMMDD
│  (Zero-Data-Loss Checkpoint)    │  Verifies clean working tree before touching disk
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│  Phase 4: Surgical Deletion &   │  Unlinks selected files, removes dead .xcassets,
│  PBXProj Synchronization        │  and cleans PBXBuildFile / PBXFileReference entries
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│  Phase 5: Build Verification    │  Runs `swift build` or `xcodebuild` to guarantee
│  (Empirical Proof of Zero Breaks)│ clean compilation. Instant rollback if errors occur.
└─────────────────────────────────┘
```

---

## 📖 Deep References

When handling complex edge cases, consult the bundled reference guides:
- [False-Positive Avoidance Rules](references/false-positive-rules.md): Guidance on dynamic reflection, `@objc`, dependency injection containers (Factory, Swinject), and string-interpolated asset names.
- [Xcode PBXProj Safe Reference Removal](references/pbxproj-safe-removal.md): Deep dive into Xcode's project structure and manual recovery commands if a project reference is broken.

---

## ✦ Execution Protocol for the Agent

When triggered by the user:
1. **Never delete immediately**. Always run Phase 1 first (`--dry-run`) to display the audit table.
2. Calculate and highlight total **reclaimable disk space** (KB/MB).
3. Confirm with the user before deleting:
   > *"Found X dead files and Y dead asset catalogs (Z KB reclaimable). Shall I create a safety branch and delete these items?"*
4. Run `--delete` to create the tracking branch and remove files.
5. Immediately execute `swift build` or `xcodebuild` to verify that the build remains green.
