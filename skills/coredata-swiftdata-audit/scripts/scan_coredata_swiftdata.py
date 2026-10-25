#!/usr/bin/env python3
"""
scan_coredata_swiftdata.py - Zero-dependency Core Data & SwiftData Persistence Auditor

Scans Swift source files for high-risk persistence hazards:
- Context concurrency violations (missing perform/performAndWait, cross-actor raw model leaks)
- SwiftData unisolated ModelContext and mainContext misuse
- CloudKit mirroring traps (missing relationship inverses, unique constraint incompatibility)
- Fault thrashing & N+1 queries (loop relationship traversal, missing fetchBatchSize)
- Batching & memory bloat (row-by-row deletions/updates, missing context.reset())
- Multi-context merge omissions & synchronous main thread store initialization
"""

import os
import sys
import re
import json
import argparse
import time
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple

# ANSI Colors
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

@dataclass
class Finding:
    severity: str
    category: str
    rule_id: str
    file_path: str
    line_number: int
    matched_snippet: str
    description: str
    remediation: str

class CoreDataSwiftDataScanner:
    def __init__(self, target_path: str, min_severity: str = "low", ignore_patterns: Optional[List[str]] = None):
        self.target_path = Path(target_path).resolve()
        self.min_severity = min_severity.lower()
        self.ignore_patterns = ignore_patterns or [
            "Pods", "DerivedData", ".build", ".swiftpm", "Carthage", ".git"
        ]
        self.severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        self.findings: List[Finding] = []
        self.files_scanned = 0
        self.lines_scanned = 0

    def should_ignore(self, path: Path) -> bool:
        path_str = str(path)
        for pattern in self.ignore_patterns:
            if pattern in path_str.split(os.sep):
                return True
        return False

    def scan(self) -> List[Finding]:
        swift_files = []

        if self.target_path.is_file():
            if self.target_path.suffix == ".swift":
                swift_files.append(self.target_path)
        else:
            for root, dirs, files in os.walk(self.target_path):
                dirs[:] = [d for d in dirs if not any(ign in d for ign in self.ignore_patterns)]
                for file in files:
                    if file.endswith(".swift"):
                        full_p = Path(root) / file
                        if not self.should_ignore(full_p):
                            swift_files.append(full_p)

        self.files_scanned = len(swift_files)
        for file_p in swift_files:
            self._scan_file(file_p)

        min_val = self.severity_order.get(self.min_severity, 1)
        self.findings = [f for f in self.findings if self.severity_order.get(f.severity.lower(), 1) >= min_val]
        # Sort findings: severity descending, then file, then line
        self.findings.sort(key=lambda f: (-self.severity_order.get(f.severity.lower(), 1), f.file_path, f.line_number))
        return self.findings

    def _strip_comments(self, text: str) -> str:
        """Replaces comment characters with spaces to preserve line numbers and character offsets."""
        def repl_single(match):
            return " " * len(match.group(0))
        def repl_multi(match):
            return "".join("\n" if c == "\n" else " " for c in match.group(0))

        text = re.sub(r'//.*$', repl_single, text, flags=re.MULTILINE)
        text = re.sub(r'/\*.*?\*/', repl_multi, text, flags=re.DOTALL)
        return text

    def _scan_file(self, file_path: Path):
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception:
            return

        lines = content.splitlines()
        self.lines_scanned += len(lines)
        file_str = str(file_path)

        # Generate clean content with comments stripped to avoid false negatives on keywords in comments
        clean_content = self._strip_comments(content)

        # Detect CloudKit involvement in the file or project context
        has_cloudkit = bool(re.search(r'\b(NSPersistentCloudKitContainer|CloudKit|CKRecord|CKContainer)\b', clean_content))

        self._check_context_concurrency(clean_content, lines, file_str)
        self._check_swiftdata_isolation(clean_content, lines, file_str)
        self._check_cloudkit_rules(clean_content, lines, file_str, has_cloudkit)
        self._check_batching_and_memory(clean_content, lines, file_str)
        self._check_fault_thrashing(clean_content, lines, file_str)
        self._check_migration_and_store_hygiene(clean_content, lines, file_str)

    def _get_line_number(self, match_start: int, content: str) -> int:
        return content[:match_start].count("\n") + 1

    def _extract_snippet(self, lines: List[str], line_no: int, context: int = 1) -> str:
        idx = line_no - 1
        start = max(0, idx - context)
        end = min(len(lines), idx + context + 1)
        snippet_lines = lines[start:end]
        return "\n".join(snippet_lines).strip()

    def _check_context_concurrency(self, content: str, lines: List[str], file_str: str):
        # 1. Unconfined context save/fetch/delete on background queue without perform/performAndWait
        # Look for DispatchQueue.global(...).async or DispatchQueue.XXX.async { ... }
        bg_queue_matches = re.finditer(
            r'DispatchQueue\.(?:global\([^)]*\)\.async|[a-zA-Z0-9_.]+\.async)\s*\{',
            content
        )
        for m in bg_queue_matches:
            # Find the balanced or approximate closing of this block
            start_pos = m.end()
            # Look forward up to 800 chars
            sub = content[start_pos:min(len(content), start_pos + 800)]
            if re.search(r'\b(?:context|managedObjectContext|moc)\.(?:save|fetch|delete|insert)\b', sub):
                if not re.search(r'\b(?:context|managedObjectContext|moc)\.(?:perform|performAndWait)\b', sub):
                    line_no = self._get_line_number(m.start(), content)
                    self.findings.append(Finding(
                        severity="Critical",
                        category="Concurrency & Thread Safety",
                        rule_id="CD_THREAD_UNCONFINED_ACCESS",
                        file_path=file_str,
                        line_number=line_no,
                        matched_snippet=self._extract_snippet(lines, line_no),
                        description="Direct NSManagedObjectContext operation inside background queue without perform/performAndWait.",
                        remediation="Enclose all background context operations in `context.perform { ... }` or `context.performAndWait { ... }` to guarantee thread confinement."
                    ))

        # 2. Passing raw NSManagedObject or @Model across Task.detached or Task boundaries
        task_matches = re.finditer(r'Task(?:\.detached)?\s*(?:\([^\)]*\))?\s*\{', content)
        for m in task_matches:
            start_pos = m.end()
            sub = content[start_pos:min(len(content), start_pos + 600)]
            if re.search(r'\b(?:self\.)?(?:context|modelContext)\.(?:save|delete|insert)\b', sub) and "Task.detached" in content[max(0, m.start() - 20):m.end()]:
                line_no = self._get_line_number(m.start(), content)
                self.findings.append(Finding(
                    severity="Critical",
                    category="Concurrency & Thread Safety",
                    rule_id="CD_TASK_DETACHED_CONTEXT_LEAK",
                    file_path=file_str,
                    line_number=line_no,
                    matched_snippet=self._extract_snippet(lines, line_no),
                    description="Accessing unconfined managed context or model objects across detached Task boundary.",
                    remediation="Pass only `NSManagedObjectID` or `PersistentIdentifier` across Tasks. Re-fetch the object inside the Task using an isolated background context or @ModelActor."
                ))

        # 3. Accessing viewContext from non-main actor / background functions
        viewcontext_matches = re.finditer(r'\b(?:[a-zA-Z0-9_]+\.)?viewContext\.(?:save|fetch|delete|insert)\b', content)
        for m in viewcontext_matches:
            line_no = self._get_line_number(m.start(), content)
            prefix = content[:m.start()]
            last_func = prefix.rfind("func ")
            if last_func != -1:
                # Find signature up to {
                brace_pos = prefix.find("{", last_func)
                func_decl = prefix[last_func:brace_pos if brace_pos != -1 else m.start()]
                prev_lines = prefix[max(0, last_func - 200):last_func]
                if "@MainActor" not in prev_lines and "@MainActor" not in func_decl and "DispatchQueue.main" not in prefix[max(0, m.start() - 300):m.start()]:
                    if "async" in func_decl or "DispatchQueue.global" in prefix[max(0, m.start() - 400):m.start()]:
                        self.findings.append(Finding(
                            severity="Critical",
                            category="Concurrency & Thread Safety",
                            rule_id="CD_VIEWCONTEXT_BACKGROUND_ACCESS",
                            file_path=file_str,
                            line_number=line_no,
                            matched_snippet=self._extract_snippet(lines, line_no),
                            description="Accessing viewContext outside MainActor in an asynchronous or background context.",
                            remediation="viewContext is strictly bound to the Main Thread. Annotate the calling scope with `@MainActor` or use `persistentContainer.newBackgroundContext()`."
                        ))

    def _check_swiftdata_isolation(self, content: str, lines: List[str], file_str: str):
        # 1. Direct ModelContext instantiation without @ModelActor in async/concurrent code
        unisolated_context = re.finditer(r'\bModelContext\s*\(\s*([a-zA-Z0-9_.]+)\s*\)', content)
        for m in unisolated_context:
            line_no = self._get_line_number(m.start(), content)
            prefix = content[:m.start()]
            last_actor = prefix.rfind("actor ")
            is_model_actor = "@ModelActor" in prefix[max(0, last_actor - 150):last_actor + 30] if last_actor != -1 else False
            if not is_model_actor and ("Task" in prefix[max(0, m.start() - 300):m.start()] or "DispatchQueue" in prefix[max(0, m.start() - 300):m.start()]):
                self.findings.append(Finding(
                    severity="Critical",
                    category="SwiftData Concurrency",
                    rule_id="SWIFTDATA_UNISOLATED_MODEL_CONTEXT",
                    file_path=file_str,
                    line_number=line_no,
                    matched_snippet=self._extract_snippet(lines, line_no),
                    description="Manual ModelContext instantiation in concurrent scope without @ModelActor isolation.",
                    remediation="Wrap background SwiftData execution in a `@ModelActor` actor type: `actor BackgroundWorker: ModelActor { let modelContainer: ModelContainer ... }`."
                ))

        # 2. Accessing container.mainContext from background tasks
        bg_maincontext = re.finditer(r'Task(?:\.detached)?\s*\{[^}]*\b(?:[a-zA-Z0-9_]+\.)?mainContext\b', content)
        for m in bg_maincontext:
            line_no = self._get_line_number(m.start(), content)
            self.findings.append(Finding(
                severity="Critical",
                category="SwiftData Concurrency",
                rule_id="SWIFTDATA_MAINCONTEXT_IN_TASK",
                file_path=file_str,
                line_number=line_no,
                matched_snippet=self._extract_snippet(lines, line_no),
                description="Invoking ModelContainer.mainContext inside a concurrent Task or detached Task.",
                remediation="`mainContext` is MainActor-isolated. Use a `@ModelActor` or detached `ModelContext` initialized on the actor for background operations."
            ))

        # 3. Non-transient property in @Model causing observation churn
        model_classes = re.finditer(r'@Model\s+(?:final\s+)?class\s+([a-zA-Z0-9_]+)[^{]*\{([^}]+)\}', content, re.MULTILINE)
        for mc in model_classes:
            body = mc.group(2)
            for prop in re.finditer(r'(?:var|let)\s+([a-zA-Z0-9_]+)\s*:\s*(UIImage\??|NSImage\??|UIColor\??|NSColor\??|Any\?|\[String:\s*Any\])', body):
                prop_decl = prop.group(0)
                prop_pos = mc.start() + mc.group(0).find(prop_decl)
                line_no = self._get_line_number(prop_pos, content)
                pre_prop = content[max(0, prop_pos - 80):prop_pos]
                if "@Transient" not in pre_prop:
                    self.findings.append(Finding(
                        severity="Medium",
                        category="SwiftData Model Architecture",
                        rule_id="SWIFTDATA_UNMARKED_TRANSIENT_PROPERTY",
                        file_path=file_str,
                        line_number=line_no,
                        matched_snippet=self._extract_snippet(lines, line_no),
                        description=f"UI or non-persisted property `{prop.group(1)}` in @Model class without @Transient annotation.",
                        remediation="Mark non-persisted runtime, cached, or platform UI properties with `@Transient` to prevent SwiftData persistence errors and view churn."
                    ))

    def _check_cloudkit_rules(self, content: str, lines: List[str], file_str: str, has_cloudkit: bool):
        # 1. Missing inverse on @Relationship when CloudKit is active or generic best practice
        # @Relationship(...) var items: [Item]? without inverse:
        rel_matches = re.finditer(r'@Relationship\s*(\(([^)]*)\))?\s*(?:var|let)\s+([a-zA-Z0-9_]+)\s*:\s*([^=\n]+)', content)
        for m in rel_matches:
            args = m.group(2) or ""
            line_no = self._get_line_number(m.start(), content)
            if "inverse:" not in args and (has_cloudkit or "deleteRule" in args):
                severity = "Critical" if has_cloudkit else "Medium"
                self.findings.append(Finding(
                    severity=severity,
                    category="CloudKit & Schema Integrity",
                    rule_id="CLOUDKIT_MISSING_RELATIONSHIP_INVERSE",
                    file_path=file_str,
                    line_number=line_no,
                    matched_snippet=self._extract_snippet(lines, line_no),
                    description=f"Relationship `{m.group(3)}` lacks an explicit inverse relationship declaration.",
                    remediation="CloudKit requires all entity relationships to have an explicit reciprocal inverse: `@Relationship(inverse: \\OtherModel.property)`."
                ))

        # 2. @Attribute(.unique) combined with CloudKit container
        if has_cloudkit:
            unique_attrs = re.finditer(r'@Attribute\s*\(\s*\.unique\s*\)', content)
            for m in unique_attrs:
                line_no = self._get_line_number(m.start(), content)
                self.findings.append(Finding(
                    severity="Critical",
                    category="CloudKit & Schema Integrity",
                    rule_id="CLOUDKIT_UNSUPPORTED_UNIQUE_CONSTRAINT",
                    file_path=file_str,
                    line_number=line_no,
                    matched_snippet=self._extract_snippet(lines, line_no),
                    description="`@Attribute(.unique)` detected in a CloudKit-backed persistence model.",
                    remediation="CloudKit does not support unique constraints. Remove `@Attribute(.unique)` or handle client-side deduplication during record ingest."
                ))

        # 3. Large binary data inline without external storage
        # var photo: Data without @Attribute(.externalStorage) or allowsExternalBinaryDataStorage
        binary_props = re.finditer(r'(?:var|let)\s+([a-zA-Z0-9_]+)\s*:\s*(Data|Data\?|\[UInt8\])', content)
        for m in binary_props:
            prop_pos = m.start()
            line_no = self._get_line_number(prop_pos, content)
            pre_text = content[max(0, prop_pos - 120):prop_pos]
            if "@Attribute(.externalStorage)" not in pre_text and "allowsExternalBinaryDataStorage" not in content:
                # Only flag if in @Model or NSManagedObject
                enclosing = content[max(0, prop_pos - 500):prop_pos]
                if "@Model" in enclosing or "NSManagedObject" in enclosing or "class " in enclosing:
                    self.findings.append(Finding(
                        severity="High",
                        category="Storage & CloudKit Bloat",
                        rule_id="PERSISTENCE_LARGE_BINARY_INLINE",
                        file_path=file_str,
                        line_number=line_no,
                        matched_snippet=self._extract_snippet(lines, line_no),
                        description=f"Binary property `{m.group(1)}: {m.group(2)}` stored inline without external storage annotation.",
                        remediation="Add `@Attribute(.externalStorage)` (SwiftData) or enable 'Allows External Binary Data Storage' in .xcdatamodeld to prevent SQLite/CloudKit payload bloat."
                    ))

    def _check_batching_and_memory(self, content: str, lines: List[str], file_str: str):
        # 1. Row-by-row deletions inside loops instead of NSBatchDeleteRequest or SwiftData batch delete
        delete_loop = re.finditer(
            r'for\s+([a-zA-Z0-9_]+)\s+in\s+([a-zA-Z0-9_.]+)\s*\{',
            content
        )
        for m in delete_loop:
            start_pos = m.end()
            sub = content[start_pos:min(len(content), start_pos + 600)]
            var_name = m.group(1)
            # Match context.delete(var_name)
            if re.search(r'\b(?:context|moc|modelContext)\.delete\s*\(\s*' + re.escape(var_name) + r'\s*\)', sub):
                line_no = self._get_line_number(m.start(), content)
                self.findings.append(Finding(
                    severity="High",
                    category="Batch Operations & Memory Bloat",
                    rule_id="CD_LOOP_ROW_BY_ROW_DELETE",
                    file_path=file_str,
                    line_number=line_no,
                    matched_snippet=self._extract_snippet(lines, line_no),
                    description="Row-by-row deletion in loop thrashes SQLite I/O and retains individual objects in memory.",
                    remediation="Execute `NSBatchDeleteRequest(fetchRequest:)` (Core Data) or `modelContext.delete(model:where:)` (SwiftData iOS 18) for atomic, memory-free batch deletion."
                ))

            # 2. Row-by-row property mutation or insertion in loop without batch or periodic reset
            elif re.search(r'\b(?:context|moc|modelContext)\.save\(\)', sub) or re.search(r'try\s+(?:context|modelContext)\.save\(\)', sub):
                if "context.reset()" not in sub and "modelContext.reset()" not in sub and "autoreleasepool" not in sub:
                    line_no = self._get_line_number(m.start(), content)
                    self.findings.append(Finding(
                        severity="High",
                        category="Batch Operations & Memory Bloat",
                        rule_id="CD_UNBOUNDED_BATCH_IMPORT",
                        file_path=file_str,
                        line_number=line_no,
                        matched_snippet=self._extract_snippet(lines, line_no),
                        description="Loop mutation/saving without `context.reset()` or `@autoreleasepool` causes unbounded memory accumulation.",
                        remediation="Batch mutations into chunks (e.g., 500-1000 items), wrap inside `@autoreleasepool { ... }`, save, and invoke `context.reset()` to release managed object graphs."
                    ))

        # 3. Missing automaticallyMergesChangesFromParent on container setup
        if "newBackgroundContext()" in content:
            if "automaticallyMergesChangesFromParent" not in content and "NSManagedObjectContextDidSave" not in content:
                for m in re.finditer(r'\bnewBackgroundContext\(\)', content):
                    line_no = self._get_line_number(m.start(), content)
                    self.findings.append(Finding(
                        severity="High",
                        category="Multi-Context Sync & Merging",
                        rule_id="CD_MISSING_AUTO_MERGE",
                        file_path=file_str,
                        line_number=line_no,
                        matched_snippet=self._extract_snippet(lines, line_no),
                        description="`newBackgroundContext()` created without configuring `automaticallyMergesChangesFromParent` on viewContext.",
                        remediation="Set `container.viewContext.automaticallyMergesChangesFromParent = true` so background context saves automatically reflect in UI contexts."
                    ))

    def _check_fault_thrashing(self, content: str, lines: List[str], file_str: str):
        # 1. NSFetchRequest missing fetchBatchSize
        fetch_requests = re.finditer(r'\bNSFetchRequest(?:<[^>]+>)?\s*\(\s*(?:entityName:[^)]+|[a-zA-Z0-9_.]+\.fetchRequest\(\))|\b[a-zA-Z0-9_]+\.fetchRequest\(\)', content)
        for m in fetch_requests:
            req_pos = m.start()
            line_no = self._get_line_number(req_pos, content)
            subsequent = content[req_pos:min(len(content), req_pos + 600)]
            if "fetchBatchSize" not in subsequent and ("executeFetchRequest" in subsequent or "context.fetch" in subsequent or "return try context.fetch" in subsequent):
                self.findings.append(Finding(
                    severity="Medium",
                    category="Fault Thrashing & Query Performance",
                    rule_id="CD_FETCH_MISSING_BATCH_SIZE",
                    file_path=file_str,
                    line_number=line_no,
                    matched_snippet=self._extract_snippet(lines, line_no),
                    description="NSFetchRequest executed without setting `fetchBatchSize`.",
                    remediation="Configure `request.fetchBatchSize = 20` (or 2x visible UI items) to avoid pulling all row data into memory simultaneously."
                ))

        # 2. Nested relationship traversal in loops without prefetching
        for m in re.finditer(r'for\s+([a-zA-Z0-9_]+)\s+in\s+([a-zA-Z0-9_.]+)\s*\{', content):
            var_name = m.group(1)
            start_pos = m.end()
            sub = content[start_pos:min(len(content), start_pos + 800)]
            rel_loop = re.search(r'for\s+([a-zA-Z0-9_]+)\s+in\s+' + re.escape(var_name) + r'\.([a-zA-Z0-9_]+)', sub)
            if rel_loop and "relationshipKeyPathsForPrefetching" not in content:
                rel_name = rel_loop.group(2)
                line_no = self._get_line_number(m.start(), content)
                self.findings.append(Finding(
                    severity="Medium",
                    category="Fault Thrashing & Query Performance",
                    rule_id="CD_FAULT_THRASHING_N_PLUS_ONE",
                    file_path=file_str,
                    line_number=line_no,
                    matched_snippet=self._extract_snippet(lines, line_no),
                    description=f"Iterating over related entity `{rel_name}` in loop causes N+1 SQLite fault trips.",
                    remediation=f"Configure `request.relationshipKeyPathsForPrefetching = [\"{rel_name}\"]` (Core Data) or `FetchDescriptor(prefetch: [\\.{rel_name}])` (SwiftData) to batch fault resolution."
                ))

        # 3. Reactive @Query / @FetchRequest text search without debouncing
        if re.search(r'@(?:Query|FetchRequest)\b', content):
            search_match = re.search(r'\.searchable\s*\(text:\s*\$([a-zA-Z0-9_]+)\)', content)
            if search_match and "debounce" not in content:
                line_no = self._get_line_number(search_match.start(), content)
                self.findings.append(Finding(
                    severity="Medium",
                    category="Reactive Query Churn",
                    rule_id="REACTIVE_QUERY_SEARCH_THRASH",
                    file_path=file_str,
                    line_number=line_no,
                    matched_snippet=self._extract_snippet(lines, line_no),
                    description="Binding dynamic @Query / @FetchRequest directly to real-time search text without debouncing.",
                    remediation="Debounce search queries (e.g. 250-300ms Task delay or Combine debounce) before mutating the query predicate to prevent keystroke SQLite thrashing."
                ))

    def _check_migration_and_store_hygiene(self, content: str, lines: List[str], file_str: str):
        # 1. Preview disk container leak
        preview_match = re.search(r'#(?:Preview|PREVIEW)\s*\{([^}]+)\}', content, re.MULTILINE)
        if preview_match:
            body = preview_match.group(1)
            if re.search(r'ModelContainer\s*\(\s*for:', body) and "isStoredInMemoryOnly:\s*true" not in body and "inMemory:\s*true" not in body:
                line_no = self._get_line_number(preview_match.start(), content)
                self.findings.append(Finding(
                    severity="Low",
                    category="Store Hygiene & Previews",
                    rule_id="PERSISTENCE_PREVIEW_DISK_LEAK",
                    file_path=file_str,
                    line_number=line_no,
                    matched_snippet=self._extract_snippet(lines, line_no),
                    description="SwiftUI #Preview initializes a disk-backed ModelContainer instead of an in-memory store.",
                    remediation="Configure `ModelConfiguration(isStoredInMemoryOnly: true)` inside previews to prevent disk pollution and sandbox lockups."
                ))

        # 2. Synchronous loadPersistentStores in main thread setup
        if "loadPersistentStores" in content:
            # Check if called directly inside init / didFinishLaunchingWithOptions
            main_sync_load = re.search(r'loadPersistentStores\s*\(\s*completionHandler:\s*\{[^}]*\}\s*\)', content)
            if main_sync_load and "DispatchQueue.global" not in content[max(0, main_sync_load.start() - 250):main_sync_load.start()]:
                if "application(_:didFinishLaunchingWithOptions:)" in content or "init()" in content:
                    line_no = self._get_line_number(main_sync_load.start(), content)
                    self.findings.append(Finding(
                        severity="Low",
                        category="Migration Safety & Store Hygiene",
                        rule_id="CD_SYNCHRONOUS_STORE_LOAD",
                        file_path=file_str,
                        line_number=line_no,
                        matched_snippet=self._extract_snippet(lines, line_no),
                        description="`loadPersistentStores` called synchronously on main thread during app initialization.",
                        remediation="Heavyweight migrations will block the main thread and trigger watchdog 0x8badf00d kills. Load stores asynchronously or display a progress UI."
                    ))

def format_table(findings: List[Finding], files_count: int, lines_count: int) -> str:
    color_map = {
        "Critical": f"{RED}{BOLD}CRITICAL{RESET}",
        "High": f"{YELLOW}{BOLD}HIGH{RESET}",
        "Medium": f"{CYAN}MEDIUM{RESET}",
        "Low": f"{DIM}LOW{RESET}"
    }

    counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1

    lines = []
    lines.append(f"\n{BOLD}{CYAN}=== Core Data & SwiftData Persistence Audit Report ==={RESET}")
    lines.append(f"Scanned {files_count} Swift file(s) ({lines_count} lines). Found {len(findings)} issue(s):\n")
    lines.append(f"  {RED}{BOLD}Critical:{RESET} {counts['Critical']}   {YELLOW}{BOLD}High:{RESET} {counts['High']}   {CYAN}Medium:{RESET} {counts['Medium']}   {DIM}Low:{RESET} {counts['Low']}\n")

    if not findings:
        lines.append(f"{GREEN}✓ No persistence hazards detected! Clean codebase.{RESET}\n")
        return "\n".join(lines)

    lines.append(f"{BOLD}{'SEVERITY':<10} {'RULE ID':<36} {'LOCATION':<45} {'DESCRIPTION'}{RESET}")
    lines.append("-" * 120)

    for f in findings:
        loc = f"{Path(f.file_path).name}:{f.line_number}"
        sev_colored = color_map.get(f.severity, f.severity)
        lines.append(f"{sev_colored:<19} {f.rule_id:<36} {loc:<45} {f.description[:50]}")

    lines.append("\n" + "=" * 120 + "\n")
    lines.append(f"{BOLD}Detailed Breakdown & Remediation:{RESET}\n")

    for i, f in enumerate(findings, 1):
        sev_colored = color_map.get(f.severity, f.severity)
        lines.append(f"{BOLD}[{i}] {sev_colored} - {f.rule_id} ({f.category}){RESET}")
        lines.append(f"    File: {f.file_path}:{f.line_number}")
        lines.append(f"    Issue: {f.description}")
        lines.append(f"    Fix:   {GREEN}{f.remediation}{RESET}")
        if f.matched_snippet:
            lines.append("    Snippet:")
            for s_line in f.matched_snippet.splitlines():
                lines.append(f"      {DIM}| {s_line}{RESET}")
        lines.append("")

    return "\n".join(lines)

def format_markdown(findings: List[Finding], files_count: int, lines_count: int) -> str:
    counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1

    md = []
    md.append("# 💾 Core Data & SwiftData Persistence Audit Report")
    md.append("")
    md.append(f"**Files Scanned:** {files_count}  ")
    md.append(f"**Lines Scanned:** {lines_count}  ")
    md.append(f"**Total Findings:** {len(findings)} (🔴 {counts['Critical']} Critical, 🟠 {counts['High']} High, 🟡 {counts['Medium']} Medium, 🔵 {counts['Low']} Low)")
    md.append("")

    if not findings:
        md.append("> ✨ **Clean Audit**: No persistence hazards or concurrency violations detected.")
        return "\n".join(md)

    md.append("## Summary Table")
    md.append("")
    md.append("| Severity | Rule ID | Category | Location | Description |")
    md.append("|---|---|---|---|---|")
    for f in findings:
        loc = f"`{Path(f.file_path).name}:{f.line_number}`"
        md.append(f"| **{f.severity}** | `{f.rule_id}` | {f.category} | {loc} | {f.description} |")

    md.append("")
    md.append("## Detailed Findings & Actionable Remediations")
    md.append("")

    for i, f in enumerate(findings, 1):
        md.append(f"### {i}. [{f.severity}] `{f.rule_id}`: {f.category}")
        md.append(f"- **Location**: `{f.file_path}:{f.line_number}`")
        md.append(f"- **Problem**: {f.description}")
        md.append(f"- **Remediation**: {f.remediation}")
        if f.matched_snippet:
            md.append("```swift")
            md.append(f.matched_snippet)
            md.append("```")
        md.append("")

    return "\n".join(md)

def main():
    parser = argparse.ArgumentParser(description="Zero-dependency Core Data & SwiftData Persistence Auditor")
    parser.add_argument("target", help="Swift file or project directory to scan")
    parser.add_argument("--format", choices=["table", "markdown", "json"], default="table", help="Output format")
    parser.add_argument("--min-severity", choices=["critical", "high", "medium", "low"], default="low", help="Minimum severity threshold")
    parser.add_argument("-o", "--output", help="Optional output file path")
    parser.add_argument("--no-exit-code", action="store_true", help="Do not exit with code 1 if critical/high issues are found")

    args = parser.parse_args()

    scanner = CoreDataSwiftDataScanner(args.target, min_severity=args.min_severity)
    findings = scanner.scan()

    if args.format == "json":
        output = json.dumps({
            "files_scanned": scanner.files_scanned,
            "lines_scanned": scanner.lines_scanned,
            "findings_count": len(findings),
            "findings": [asdict(f) for f in findings]
        }, indent=2)
    elif args.format == "markdown":
        output = format_markdown(findings, scanner.files_scanned, scanner.lines_scanned)
    else:
        output = format_table(findings, scanner.files_scanned, scanner.lines_scanned)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Report written to {args.output}")
    else:
        print(output)

    if not args.no_exit_code:
        has_blockers = any(f.severity in ["Critical", "High"] for f in findings)
        if has_blockers:
            sys.exit(1)

    sys.exit(0)

if __name__ == "__main__":
    main()
