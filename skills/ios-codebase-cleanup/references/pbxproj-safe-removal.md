# Xcode Project (`project.pbxproj`) Safe Reference Pruning

When deleting source files (`.swift`, `.m`, `.h`, `.xib`, `.storyboard`) from an Xcode project, simply unlinking them from disk causes compilation failures:

```
error: /path/to/OldViewController.swift: No such file or directory
Build Failed: Missing file reference in PBXBuildFile / PBXSourcesBuildPhase
```

---

## 1. Anatomy of an Xcode File Reference

Inside `project.pbxproj`, every tracked file has two main entries:

1. **`PBXFileReference`**: Points from Xcode's file navigator hierarchy to the relative path on disk:
   ```text
   21A0F4912B1001A000A00123 /* OldService.swift */ = {isa = PBXFileReference; fileEncoding = 4; lastKnownFileType = sourcecode.swift; path = OldService.swift; sourceTree = "<group>"; };
   ```

2. **`PBXBuildFile`**: Links the file reference to a build phase (e.g. `PBXSourcesBuildPhase` for compilation, or `PBXResourcesBuildPhase` for bundle assets):
   ```text
   21A0F4922B1001A000A00123 /* OldService.swift in Sources */ = {isa = PBXBuildFile; fileRef = 21A0F4912B1001A000A00123 /* OldService.swift */; };
   ```

3. **`PBXGroup` / `PBXSourcesBuildPhase`**: Contains the UUIDs of the build file and file reference:
   ```text
   files = (
       21A0F4922B1001A000A00123 /* OldService.swift in Sources */,
   );
   ```

---

## 2. Safe Deletion Workflow

1. **Git Working Tree Safety**:
   Ensure `git status --porcelain` is empty. Always create a branch before deletion:
   ```bash
   git checkout -b cleanup/ios-codebase-YYYYMMDD
   ```

2. **Automated Line-Level Pruning**:
   `scan_codebase_cleanup.py` automatically strips lines containing the deleted filename from `project.pbxproj`:
   ```bash
   python3 scripts/scan_codebase_cleanup.py . --delete
   ```

3. **Xcode Build Graph Validation**:
   Immediately test the project build after deletion:
   ```bash
   # For Swift Package projects:
   swift build

   # For Xcode projects / workspaces:
   xcodebuild -scheme <AppScheme> -destination 'generic/platform=iOS Simulator' clean build CODE_SIGNING_ALLOWED=NO
   ```

4. **Rollback Command**:
   If any compilation errors or broken references emerge:
   ```bash
   git reset --hard HEAD
   git checkout main
   ```
