#!/usr/bin/env python3
"""
scan_codebase_cleanup.py
Zero-dependency fast scanner for detecting unused files, dead asset catalogs,
orphaned documentation, unused imports, and dead code symbols in iOS/Apple codebases.
"""

import os
import sys
import re
import json
import argparse
import subprocess
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any

DEFAULT_IGNORES = {
    ".git", ".build", "DerivedData", "Pods", "Carthage", ".swiftpm",
    "fastlane", ".idea", ".vscode", "xcuserdata", "build"
}

SWIFT_ENTRY_POINTS = {
    "@main", "UIApplicationDelegate", "UIWindowSceneDelegate",
    "NSApplicationDelegate", "AppDelegate", "SceneDelegate",
    "App", "PrincipalClass"
}

class CleanupScanner:
    def __init__(self, root_path: str, scopes: List[str], ignores: Optional[Set[str]] = None):
        self.root = Path(root_path).resolve()
        self.scopes = set(scopes) if "all" not in scopes else {"files", "assets", "docs", "symbols", "imports", "strings"}
        self.ignores = ignores or DEFAULT_IGNORES
        
        self.all_files: List[Path] = []
        self.swift_files: List[Path] = []
        self.asset_folders: List[Path] = []
        self.md_files: List[Path] = []
        self.loose_images: List[Path] = []
        self.xib_storyboard_files: List[Path] = []
        self.strings_files: List[Path] = []
        self.pbxproj_files: List[Path] = []
        
        # In-memory file cache for fast scanning
        self.file_contents_cache: Dict[Path, str] = {}
        
        # Results
        self.dead_files: List[Dict[str, Any]] = []
        self.dead_assets: List[Dict[str, Any]] = []
        self.dead_docs: List[Dict[str, Any]] = []
        self.dead_symbols: List[Dict[str, Any]] = []
        self.dead_imports: List[Dict[str, Any]] = []
        self.dead_strings: List[Dict[str, Any]] = []

    def discover_files(self):
        """Walk directory tree once and index files by category."""
        for root, dirs, files in os.walk(self.root):
            # Prune ignored directories
            dirs[:] = [d for d in dirs if d not in self.ignores and not d.endswith(".xcodeproj")]
            
            # Check for asset catalogs
            for d in dirs:
                if d.endswith((".imageset", ".colorset", ".appiconset", ".symbolset")):
                    self.asset_folders.append(Path(root) / d)

            for f in files:
                if f.startswith("."):
                    continue
                file_path = Path(root) / f
                self.all_files.append(file_path)
                
                suffix = file_path.suffix.lower()
                if suffix == ".swift":
                    self.swift_files.append(file_path)
                elif suffix == ".md":
                    self.md_files.append(file_path)
                elif suffix in {".png", ".jpg", ".jpeg", ".svg", ".pdf", ".webp"}:
                    if ".xcassets" not in file_path.parts:
                        self.loose_images.append(file_path)
                elif suffix in {".xib", ".storyboard"}:
                    self.xib_storyboard_files.append(file_path)
                elif suffix in {".strings", ".stringsdict", ".xcstrings"}:
                    self.strings_files.append(file_path)
                elif f == "project.pbxproj":
                    self.pbxproj_files.append(file_path)

    def get_content(self, path: Path) -> str:
        """Cached file content retrieval."""
        if path not in self.file_contents_cache:
            try:
                self.file_contents_cache[path] = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                self.file_contents_cache[path] = ""
        return self.file_contents_cache[path]

    def get_folder_size(self, path: Path) -> int:
        """Calculate total size of directory or file."""
        if path.is_file():
            return path.stat().st_size
        total = 0
        for p in path.rglob("*"):
            if p.is_file():
                total += p.stat().st_size
        return total

    def scan_dead_files(self):
        """Scan for completely unused Swift files."""
        # Top-level declaration patterns in Swift
        decl_pattern = re.compile(
            r'^\s*(?:@\w+\s+)*(?:public\s+|internal\s+|fileprivate\s+|private\s+|open\s+|final\s+)*'
            r'(?:class|struct|enum|protocol|actor|typealias)\s+([A-Z]\w*)',
            re.MULTILINE
        )
        
        # Read all text once to speed up global reference search
        searchable_corpus = []
        for p in self.swift_files + self.xib_storyboard_files:
            searchable_corpus.append((p, self.get_content(p)))

        for sf in self.swift_files:
            content = self.get_content(sf)
            
            # Skip if explicitly marked entry point
            if any(ep in content for ep in SWIFT_ENTRY_POINTS):
                continue

            # Keep file if it contains #Preview or PreviewProvider (user requested preview retention)
            if "#Preview" in content or "PreviewProvider" in content:
                continue

            # Check if this file defines types
            types = decl_pattern.findall(content)
            if not types:
                # File has no top-level types (might be extensions or global funcs)
                # Check if it has any extensions or functions
                func_decl = re.findall(r'^\s*(?:public\s+|internal\s+)?func\s+([a-zA-Z_]\w*)', content, re.MULTILINE)
                ext_decl = re.findall(r'^\s*extension\s+([A-Z]\w*)', content, re.MULTILINE)
                if not func_decl and not ext_decl:
                    # Empty or comment-only file
                    size = sf.stat().st_size
                    self.dead_files.append({
                        "path": str(sf.relative_to(self.root)),
                        "type": "Empty / Stub Swift File",
                        "size": size,
                        "confidence": "High",
                        "reason": "Contains no declarations, types, or executable code."
                    })
                continue

            # Check if ANY of the defined types are referenced in OTHER files
            is_used = False
            for t in types:
                ref_regex = re.compile(r'\b' + re.escape(t) + r'\b')
                for other_path, other_content in searchable_corpus:
                    if other_path == sf:
                        continue
                    if ref_regex.search(other_content):
                        is_used = True
                        break
                if is_used:
                    break

            if not is_used:
                # Type might have @objc or reflection
                confidence = "High"
                reason = f"Types [{', '.join(types[:3])}] have 0 occurrences outside this file."
                if "@objc" in content or "NSObject" in content:
                    confidence = "Medium"
                    reason += " Contains @objc/NSObject which may be instantiated via reflection."

                size = sf.stat().st_size
                self.dead_files.append({
                    "path": str(sf.relative_to(self.root)),
                    "type": "Unused Swift File",
                    "size": size,
                    "confidence": confidence,
                    "reason": reason
                })

    def scan_dead_assets(self):
        """Scan for unused asset catalog entries (.imageset, .colorset, etc.)."""
        # Build search text across swift, xib, storyboard, plist
        searchable_texts = []
        for p in self.swift_files + self.xib_storyboard_files:
            searchable_texts.append(self.get_content(p))

        for af in self.asset_folders:
            asset_name = af.stem  # remove .imageset/.colorset
            
            # Match variations:
            # 1. Literal string "assetName"
            # 2. Swift 6 / iOS 17 Generated Symbols: Xcode converts snake_case and kebab-case to camelCase
            words = re.split(r'[-_\s]+', asset_name)
            camel_name = words[0].lower() + "".join(w.capitalize() for w in words[1:]) if len(words) > 1 else asset_name
            pascal_name = "".join(w.capitalize() for w in words)

            patterns = [
                re.compile(r'["\']' + re.escape(asset_name) + r'["\']'),
                re.compile(r'\.' + re.escape(asset_name) + r'\b'),
                re.compile(r'\.' + re.escape(camel_name) + r'\b'),
                re.compile(r'\.' + re.escape(pascal_name) + r'\b')
            ]
            
            found = False
            for text in searchable_texts:
                if any(p.search(text) for p in patterns):
                    found = True
                    break

            if not found:
                size = self.get_folder_size(af)
                folder_type = af.suffix.lstrip(".")
                self.dead_assets.append({
                    "path": str(af.relative_to(self.root)),
                    "type": f"Dead Asset ({folder_type})",
                    "size": size,
                    "confidence": "High",
                    "reason": f"Asset '{asset_name}' has 0 references in code, XIBs, or storyboards."
                })

    def scan_dead_docs_and_images(self):
        """Scan for unreferenced markdown files and loose media."""
        # Check loose media
        md_corpus = "\n".join(self.get_content(p) for p in self.md_files + self.swift_files)
        for img in self.loose_images:
            img_name = img.name
            if img_name not in md_corpus:
                size = img.stat().st_size
                self.dead_docs.append({
                    "path": str(img.relative_to(self.root)),
                    "type": "Unreferenced Loose Image",
                    "size": size,
                    "confidence": "High",
                    "reason": f"Image file '{img_name}' is not linked in any markdown or Swift file."
                })

        # Check markdown files (orphan docs not referenced by README or docs index)
        readme_path = self.root / "README.md"
        readme_content = self.get_content(readme_path) if readme_path.exists() else ""
        
        for md in self.md_files:
            if md.name.upper() in {"README.MD", "CLAUDE.MD", "AGENTS.MD", "SKILL.MD", "CONTRIBUTING.MD", "LICENSE.MD", "CHANGELOG.MD"}:
                continue
            
            rel = str(md.relative_to(self.root))
            # Check if mentioned in README or other markdown
            is_linked = False
            if md.name in readme_content or rel in readme_content:
                is_linked = True
            else:
                for other_md in self.md_files:
                    if other_md == md:
                        continue
                    if md.name in self.get_content(other_md):
                        is_linked = True
                        break

            if not is_linked:
                size = md.stat().st_size
                self.dead_docs.append({
                    "path": rel,
                    "type": "Orphan Markdown Doc",
                    "size": size,
                    "confidence": "Medium",
                    "reason": f"Markdown document '{md.name}' is not linked in README or any sibling docs."
                })

    def scan_dead_symbols(self):
        """Scan for unused private/fileprivate symbols inside active files."""
        private_func_pat = re.compile(r'^\s*(?:private|fileprivate)\s+func\s+([a-zA-Z_]\w*)', re.MULTILINE)
        private_var_pat = re.compile(r'^\s*(?:private|fileprivate)\s+(?:let|var)\s+([a-zA-Z_]\w*)', re.MULTILINE)

        for sf in self.swift_files:
            content = self.get_content(sf)
            funcs = private_func_pat.findall(content)
            vars_ = private_var_pat.findall(content)

            for fn in funcs:
                # Count occurrences in this file
                matches = len(re.findall(r'\b' + re.escape(fn) + r'\b', content))
                if matches <= 1:  # Only declaration itself
                    self.dead_symbols.append({
                        "file": str(sf.relative_to(self.root)),
                        "symbol": f"private func {fn}()",
                        "type": "Unused Private Function",
                        "confidence": "High",
                        "reason": f"Defined on line, but never called within file."
                    })

            for vr in vars_:
                matches = len(re.findall(r'\b' + re.escape(vr) + r'\b', content))
                if matches <= 1:
                    self.dead_symbols.append({
                        "file": str(sf.relative_to(self.root)),
                        "symbol": f"private let/var {vr}",
                        "type": "Unused Private Property",
                        "confidence": "High",
                        "reason": f"Declared, but never read or written within file."
                    })

    def scan_dead_imports(self):
        """Scan for unneeded imports."""
        import_pat = re.compile(r'^\s*import\s+([A-Za-z0-9_]+)', re.MULTILINE)
        
        # Common frameworks whose symbols might be implicitly used
        for sf in self.swift_files:
            content = self.get_content(sf)
            imports = import_pat.findall(content)
            lines = content.splitlines()
            body_without_imports = "\n".join(l for l in lines if not l.strip().startswith("import "))

            for imp in imports:
                if imp in {"Foundation", "SwiftUI", "UIKit", "AppKit"}:
                    continue  # Frameworks often provide protocol conformances or base types
                
                # Check if module name or direct identifiers are used
                if imp not in body_without_imports:
                    self.dead_imports.append({
                        "file": str(sf.relative_to(self.root)),
                        "import": imp,
                        "type": "Potential Unused Import",
                        "confidence": "Medium",
                        "reason": f"Module '{imp}' is imported but no direct symbols matching '{imp}' appear in code."
                    })

    def run(self):
        """Execute scans based on requested scopes."""
        self.discover_files()
        
        if "files" in self.scopes:
            self.scan_dead_files()
        if "assets" in self.scopes:
            self.scan_dead_assets()
        if "docs" in self.scopes:
            self.scan_dead_docs_and_images()
        if "symbols" in self.scopes:
            self.scan_dead_symbols()
        if "imports" in self.scopes:
            self.scan_dead_imports()

    def get_summary(self) -> Dict[str, Any]:
        """Aggregate results and reclaimable disk space."""
        total_size = sum(item.get("size", 0) for item in self.dead_files + self.dead_assets + self.dead_docs)
        return {
            "summary": {
                "total_dead_files": len(self.dead_files),
                "total_dead_assets": len(self.dead_assets),
                "total_dead_docs": len(self.dead_docs),
                "total_dead_symbols": len(self.dead_symbols),
                "total_dead_imports": len(self.dead_imports),
                "reclaimable_bytes": total_size,
                "reclaimable_kb": round(total_size / 1024, 2),
                "reclaimable_mb": round(total_size / (1024 * 1024), 2)
            },
            "dead_files": self.dead_files,
            "dead_assets": self.dead_assets,
            "dead_docs": self.dead_docs,
            "dead_symbols": self.dead_symbols,
            "dead_imports": self.dead_imports
        }

    def clean_pbxproj_references(self, deleted_rel_paths: List[str]):
        """Remove file references from project.pbxproj to keep Xcode build green."""
        for pbx_path in self.pbxproj_files:
            try:
                content = pbx_path.read_text(encoding="utf-8")
                orig_content = content
                for rel in deleted_rel_paths:
                    filename = Path(rel).name
                    # Remove lines referencing this filename
                    lines = content.splitlines()
                    filtered_lines = [l for l in lines if filename not in l]
                    content = "\n".join(filtered_lines)
                
                if content != orig_content:
                    pbx_path.write_text(content, encoding="utf-8")
                    print(f"  ✓ Cleaned PBX references in {pbx_path.name}")
            except Exception as e:
                print(f"  ⚠ Failed to update PBXProj {pbx_path}: {e}")

    def execute_cleanup(self, branch_name: Optional[str] = None, force: bool = False, no_git_check: bool = False):
        """Execute safe deletion with git safety branch and PBXProj sync."""
        candidates = self.dead_files + self.dead_assets + self.dead_docs
        if not candidates:
            print("No dead files, assets, or docs identified for deletion.")
            return

        # 1. Git working tree verification
        if not no_git_check:
            try:
                res = subprocess.run(["git", "status", "--porcelain"], cwd=self.root, capture_output=True, text=True)
                if res.returncode == 0 and res.stdout.strip():
                    print("❌ Error: Working tree has unstaged changes. Commit or stash them before running cleanup.")
                    sys.exit(1)
            except Exception:
                pass  # Not a git repository

            # 2. Create safety branch
            if not branch_name:
                import datetime
                timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
                branch_name = f"cleanup/ios-codebase-{timestamp}"

            try:
                print(f"🛡 Creating safety tracking branch: {branch_name}...")
                subprocess.run(["git", "checkout", "-b", branch_name], cwd=self.root, check=True)
                print(f"  ✓ Checked out branch: {branch_name}")
            except Exception as e:
                print(f"  ⚠ Git branch creation skipped or failed: {e}")

        # 3. Confirmation prompt if not forced
        if not force:
            print(f"\nReady to delete {len(candidates)} dead file/asset items.")
            ans = input("Proceed with permanent deletion? [y/N]: ").strip().lower()
            if ans != "y":
                print("Deletion cancelled by user.")
                return

        # 4. Perform surgical deletions
        deleted_paths = []
        for item in candidates:
            target = self.root / item["path"]
            if target.exists():
                try:
                    if target.is_dir():
                        import shutil
                        shutil.rmtree(target)
                    else:
                        target.unlink()
                    deleted_paths.append(item["path"])
                    print(f"  🗑 Deleted: {item['path']}")
                except Exception as e:
                    print(f"  ⚠ Failed to delete {item['path']}: {e}")

        # 5. Clean Xcode project references
        if deleted_paths and self.pbxproj_files:
            print("🔧 Synchronizing Xcode project files...")
            self.clean_pbxproj_references(deleted_paths)

        print(f"\n🎉 Successfully cleaned up {len(deleted_paths)} items!")


def print_table(summary_data: Dict[str, Any]):
    sum_info = summary_data["summary"]
    print("=" * 80)
    print(" 🧹 iOS Codebase Cleanup Audit Report")
    print("=" * 80)
    print(f" Reclaimable Disk Space:  {sum_info['reclaimable_kb']} KB ({sum_info['reclaimable_mb']} MB)")
    print(f" Dead Swift Files:        {sum_info['total_dead_files']}")
    print(f" Dead Asset Catalogs:     {sum_info['total_dead_assets']}")
    print(f" Orphaned Docs & Images:  {sum_info['total_dead_docs']}")
    print(f" Dead Code Symbols:       {sum_info['total_dead_symbols']}")
    print(f" Dead / Unused Imports:   {sum_info['total_dead_imports']}")
    print("-" * 80)

    # Dead Files & Assets
    items = summary_data["dead_files"] + summary_data["dead_assets"] + summary_data["dead_docs"]
    if items:
        print("\n[DEAD FILES & ASSETS IDENTIFIED]")
        print(f"{'CONF':<6} | {'TYPE':<22} | {'SIZE (KB)':<10} | {'PATH'}")
        print("-" * 80)
        for it in items:
            size_kb = round(it.get("size", 0) / 1024, 2)
            conf_badge = "🔴" if it["confidence"] == "High" else "🟡"
            print(f"{conf_badge} {it['confidence']:<4} | {it['type']:<22} | {size_kb:<10} | {it['path']}")
            print(f"       ↳ {it['reason']}")

    # Dead symbols
    symbols = summary_data.get("dead_symbols", [])
    if symbols:
        print("\n[DEAD CODE SYMBOLS (INSIDE ACTIVE FILES)]")
        for sym in symbols:
            print(f"  • {sym['file']}: {sym['symbol']} ({sym['reason']})")

    # Dead imports
    imports = summary_data.get("dead_imports", [])
    if imports:
        print("\n[POTENTIAL UNUSED IMPORTS]")
        for imp in imports:
            print(f"  • {imp['file']}: import {imp['import']} ({imp['reason']})")

    print("\n" + "=" * 80)


def print_markdown(summary_data: Dict[str, Any]) -> str:
    sum_info = summary_data["summary"]
    md = []
    md.append("# 🧹 iOS Codebase Cleanup Audit Report\n")
    md.append(f"**Reclaimable Space:** `{sum_info['reclaimable_kb']} KB` ({sum_info['reclaimable_mb']} MB)\n")
    md.append("| Category | Count |")
    md.append("| :--- | :--- |")
    md.append(f"| Dead Swift Files | {sum_info['total_dead_files']} |")
    md.append(f"| Dead Asset Catalogs | {sum_info['total_dead_assets']} |")
    md.append(f"| Orphaned Docs & Images | {sum_info['total_dead_docs']} |")
    md.append(f"| Dead Code Symbols | {sum_info['total_dead_symbols']} |")
    md.append(f"| Unused Imports | {sum_info['total_dead_imports']} |\n")

    items = summary_data["dead_files"] + summary_data["dead_assets"] + summary_data["dead_docs"]
    if items:
        md.append("## Dead Files & Assets\n")
        md.append("| Confidence | Type | Size (KB) | Path | Reason |")
        md.append("| :--- | :--- | :--- | :--- | :--- |")
        for it in items:
            size_kb = round(it.get("size", 0) / 1024, 2)
            conf = "🔴 High" if it["confidence"] == "High" else "🟡 Medium"
            md.append(f"| {conf} | {it['type']} | {size_kb} | `{it['path']}` | {it['reason']} |")
        md.append("")

    symbols = summary_data.get("dead_symbols", [])
    if symbols:
        md.append("## Dead Symbols Inside Active Files\n")
        for sym in symbols:
            md.append(f"- **`{sym['file']}`**: `{sym['symbol']}` — *{sym['reason']}*")
        md.append("")

    return "\n".join(md)


def main():
    parser = argparse.ArgumentParser(description="iOS Codebase Cleanup Scanner")
    parser.add_argument("path", nargs="?", default=".", help="Path to project root")
    parser.add_argument("--scope", default="files,assets,docs",
                        help="Comma-separated scopes: files, assets, docs, symbols, imports, strings, all (default: files,assets,docs)")
    parser.add_argument("--format", choices=["table", "json", "markdown"], default="table",
                        help="Output format (default: table)")
    parser.add_argument("--delete", action="store_true", help="Execute deletion of dead files and assets")
    parser.add_argument("--force", action="store_true", help="Bypass interactive confirmation before deletion")
    parser.add_argument("--branch", default=None, help="Name of git branch to create before deletion")
    parser.add_argument("--no-git-check", action="store_true", help="Bypass git cleanliness checks (for tests)")
    parser.add_argument("-o", "--output", help="Write report output to specified file")

    args = parser.parse_args()

    scopes = [s.strip() for s in args.scope.split(",")]
    scanner = CleanupScanner(args.path, scopes)
    scanner.run()

    summary_data = scanner.get_summary()

    if args.format == "json":
        out = json.dumps(summary_data, indent=2)
        if args.output:
            Path(args.output).write_text(out, encoding="utf-8")
        else:
            print(out)
    elif args.format == "markdown":
        out = print_markdown(summary_data)
        if args.output:
            Path(args.output).write_text(out, encoding="utf-8")
        else:
            print(out)
    else:
        print_table(summary_data)
        if args.output:
            Path(args.output).write_text(print_markdown(summary_data), encoding="utf-8")

    if args.delete:
        scanner.execute_cleanup(branch_name=args.branch, force=args.force, no_git_check=args.no_git_check)


if __name__ == "__main__":
    main()
