#!/usr/bin/env python3
"""
test_scanner.py
Automated evaluation test runner for ios-codebase-cleanup scanner.
"""

import unittest
import tempfile
import shutil
from pathlib import Path
import sys

# Add scripts directory to path
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from scan_codebase_cleanup import CleanupScanner

class TestCleanupScanner(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.root = Path(self.test_dir)
        
        # 1. Used swift file
        (self.root / "UsedService.swift").write_text("class UsedService { func call() {} }")
        
        # 2. Main app file using UsedService
        (self.root / "App.swift").write_text("import SwiftUI\n@main\nstruct MyApp: App {\n    let service = UsedService()\n}")
        
        # 3. Completely unused dead file
        (self.root / "DeadModel.swift").write_text("struct DeadModel { let id: Int }")
        
        # 4. Preview-only file (should NOT be flagged as dead per user requirement)
        (self.root / "PreviewOnlyView.swift").write_text("import SwiftUI\nstruct PreviewOnlyView: View {\n    var body: some View { Text(\"Hi\") }\n}\n#Preview {\n    PreviewOnlyView()\n}")
        
        # 5. Asset catalog: 1 used, 1 dead
        assets_dir = self.root / "Assets.xcassets"
        used_icon = assets_dir / "used_logo.imageset"
        used_icon.mkdir(parents=True)
        (used_icon / "Contents.json").write_text("{}")
        (used_icon / "logo.png").write_text("dummy image data")
        
        dead_icon = assets_dir / "dead_icon.imageset"
        dead_icon.mkdir(parents=True)
        (dead_icon / "Contents.json").write_text("{}")
        (dead_icon / "icon.png").write_text("dummy dead image data")
        
        # Reference used_logo in App.swift
        (self.root / "App.swift").write_text((self.root / "App.swift").read_text() + '\nlet img = Image("used_logo")')
        
        # 6. Dead markdown file
        (self.root / "README.md").write_text("# My App\nWelcome.")
        (self.root / "forgotten_notes.md").write_text("# Old Notes")

        # 7. Unused symbols and imports inside an active file
        (self.root / "ActiveWithDeadCode.swift").write_text("""
import Foundation
import CoreLocation

class ActiveWithDeadCode {
    private func unusedHelper() {}
    private let unusedVar = 42
    func run() { print("ok") }
}
""")
        # Reference ActiveWithDeadCode in App.swift
        (self.root / "App.swift").write_text((self.root / "App.swift").read_text() + '\nlet act = ActiveWithDeadCode()')
        
    def tearDown(self):
        shutil.rmtree(self.test_dir)
        
    def test_dead_files_and_assets(self):
        scanner = CleanupScanner(self.test_dir, scopes=["files", "assets", "docs"])
        scanner.run()
        summary = scanner.get_summary()
        
        dead_files = [f["path"] for f in summary["dead_files"]]
        self.assertIn("DeadModel.swift", dead_files)
        self.assertNotIn("UsedService.swift", dead_files)
        self.assertNotIn("App.swift", dead_files)
        self.assertNotIn("PreviewOnlyView.swift", dead_files)
        
        dead_assets = [a["path"] for a in summary["dead_assets"]]
        self.assertTrue(any("dead_icon.imageset" in a for a in dead_assets))
        self.assertFalse(any("used_logo.imageset" in a for a in dead_assets))
        
        dead_docs = [d["path"] for d in summary["dead_docs"]]
        self.assertIn("forgotten_notes.md", dead_docs)
        self.assertNotIn("README.md", dead_docs)

    def test_symbols_and_imports(self):
        scanner = CleanupScanner(self.test_dir, scopes=["symbols", "imports"])
        scanner.run()
        summary = scanner.get_summary()
        
        sym_names = [s["symbol"] for s in summary["dead_symbols"]]
        self.assertIn("private func unusedHelper()", sym_names)
        self.assertIn("private let/var unusedVar", sym_names)
        
        imp_names = [i["import"] for i in summary["dead_imports"]]
        self.assertIn("CoreLocation", imp_names)
        self.assertNotIn("Foundation", imp_names)

if __name__ == "__main__":
    unittest.main()
