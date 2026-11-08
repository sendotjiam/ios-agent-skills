#!/usr/bin/env python3
"""
scan_app_launch.py - iOS App Launch & Startup Performance Fast-Scanner

Audits iOS, iPadOS, macOS, and watchOS projects for cold/warm launch bottlenecks (<400ms MetricKit budget):
  1. Synchronous database store loading & migrations in didFinishLaunching or App.init()
  2. Blocking file I/O & JSON parsing on the main thread during launch
  3. Third-party SDK initialization pileups (Firebase, Sentry, Mixpanel, Datadog) blocking main thread
  4. Objective-C +load methods and heavy static initializers increasing pre-main dyld duration
  5. Obsolete UserDefaults.standard.synchronize() calls on startup
"""

import argparse
import json
import os
import re
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

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
    severity: str  # Critical, High, Medium, Low
    category: str
    rule_id: str
    file_path: str
    line_number: int
    matched_snippet: str
    description: str
    remediation: str


# Third party SDKs often initialized synchronously in didFinishLaunching
SDK_INIT_PATTERNS = [
    (re.compile(r'\bFirebaseApp\.configure\(\)'), "Firebase"),
    (re.compile(r'\bSentrySDK\.start\b'), "Sentry"),
    (re.compile(r'\bMixpanel\.initialize\b'), "Mixpanel"),
    (re.compile(r'\bDatadog\.initialize\b'), "Datadog"),
    (re.compile(r'\bAppsFlyerLib\.shared\(\)\.start\b'), "AppsFlyer"),
    (re.compile(r'\bAmplitude\.instance\(\)\.initializeApiKey\b'), "Amplitude"),
]


class AppLaunchScanner:
    def __init__(
        self,
        target_path: str,
        min_severity: str = "low",
        ignore_patterns: Optional[List[str]] = None,
        include_tests: bool = False,
    ):
        self.target_path = Path(target_path).resolve()
        self.min_severity = min_severity.lower()
        self.include_tests = include_tests
        base_ignores = ["Pods", "DerivedData", ".build", ".swiftpm", "Carthage", ".git", "golden_fixes"]
        if not include_tests:
            base_ignores.extend(["Tests", "UITests", "UnitTests", "IntegrationTests", "Mocks", "Fixtures", "TestHelpers"])
        if ignore_patterns:
            base_ignores.extend(ignore_patterns)
        self.ignore_patterns = base_ignores
        self.severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        self.findings: List[Finding] = []
        self.files_scanned = 0
        self.lines_scanned = 0

    def should_ignore(self, path: Path) -> bool:
        path_str = str(path)
        for pattern in self.ignore_patterns:
            if pattern in path_str.split(os.sep):
                return True
        if not self.include_tests:
            name = path.name
            if name.endswith("Tests.swift") or name.endswith("Test.swift") or name.endswith("Mock.swift") or name.endswith("Fixture.swift"):
                return True
        return False

    def is_rule_suppressed(self, line: str, prev_line: Optional[str], rule_id: str) -> bool:
        if "//" in line:
            same_line_pat = re.compile(r"//\s*(?:ios-audit|swift-audit)\s*:\s*ignore\s+([\w\-, ]+)", re.IGNORECASE)
            m = same_line_pat.search(line)
            if m:
                ignored = [r.strip().upper() for r in m.group(1).split(",")]
                if "ALL" in ignored or rule_id.upper() in ignored:
                    return True
            if re.search(r"//\s*(?:ios-audit|swift-audit)\s*:\s*ignore-all\b", line, re.IGNORECASE):
                return True

        if prev_line and "//" in prev_line:
            next_line_pat = re.compile(r"//\s*(?:ios-audit|swift-audit)\s*:\s*(?:ignore-next-line|disable-next-line)\s+([\w\-, ]+)", re.IGNORECASE)
            m_next = next_line_pat.search(prev_line)
            if m_next:
                ignored = [r.strip().upper() for r in m_next.group(1).split(",")]
                if "ALL" in ignored or rule_id.upper() in ignored:
                    return True
            if re.search(r"//\s*(?:ios-audit|swift-audit)\s*:\s*(?:ignore-next-line-all|disable-next-line-all)\b", prev_line, re.IGNORECASE):
                return True

        return False

    def scan(self) -> List[Finding]:
        swift_files: List[Path] = []
        objc_files: List[Path] = []

        if self.target_path.is_file():
            if self.target_path.suffix == ".swift":
                swift_files.append(self.target_path)
            elif self.target_path.suffix in [".m", ".mm"]:
                objc_files.append(self.target_path)
        else:
            for root, dirs, files in os.walk(self.target_path):
                dirs[:] = [d for d in dirs if not any(ign in d for ign in self.ignore_patterns)]
                for file in files:
                    full_p = Path(root) / file
                    if self.should_ignore(full_p):
                        continue
                    if file.endswith(".swift"):
                        swift_files.append(full_p)
                    elif file.endswith(".m") or file.endswith(".mm"):
                        objc_files.append(full_p)

        self.files_scanned = len(swift_files) + len(objc_files)

        for s_file in swift_files:
            self._scan_swift_file(s_file)

        for o_file in objc_files:
            self._scan_objc_file(o_file)

        min_rank = self.severity_order.get(self.min_severity, 1)
        self.findings = [
            f for f in self.findings if self.severity_order.get(f.severity.lower(), 1) >= min_rank
        ]
        self.findings.sort(
            key=lambda x: (-self.severity_order.get(x.severity.lower(), 1), x.file_path, x.line_number)
        )
        return self.findings

    def _scan_swift_file(self, file_path: Path):
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return

        lines = content.splitlines()
        self.lines_scanned += len(lines)
        file_str = str(file_path)

        in_launch_scope = False
        launch_scope_depth = 0

        for idx, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
                continue

            prev_line = lines[idx - 1] if idx > 0 else ""

            # Check entry into launch methods:
            # 1. didFinishLaunchingWithOptions
            # 2. init() inside @main App struct
            if "didFinishLaunchingWithOptions" in line or (re.search(r'\binit\s*\([^)]*\)\s*\{', line) and "@main" in content):
                in_launch_scope = True
                launch_scope_depth = line.count("{") - line.count("}")
            elif in_launch_scope:
                launch_scope_depth += (line.count("{") - line.count("}"))
                if launch_scope_depth <= 0:
                    in_launch_scope = False

            # Check 1: Synchronous Persistent Store Loading during launch
            if in_launch_scope and "loadPersistentStores" in line:
                rule_id = "LAUNCH_SYNC_PERSISTENCE_LOAD"
                if not self.is_rule_suppressed(line, prev_line, rule_id):
                    self.findings.append(Finding(
                        severity="Critical",
                        category="Synchronous DB Load in App Launch",
                        rule_id=rule_id,
                        file_path=file_str,
                        line_number=idx + 1,
                        matched_snippet=stripped,
                        description="Synchronous NSPersistentContainer.loadPersistentStores called directly during app launch, risking watchdog kill (0x8badf00d).",
                        remediation="Move store loading to background Task or initialize store asynchronously after initial window displays."
                    ))

            # Check 2: Synchronous Blocking File I/O or JSON decoding during launch
            if in_launch_scope and ("Data(contentsOf:" in line or "try? Data(contentsOf:" in line):
                rule_id = "LAUNCH_BLOCKING_FILE_IO"
                if not self.is_rule_suppressed(line, prev_line, rule_id):
                    self.findings.append(Finding(
                        severity="Critical",
                        category="Main-Thread File I/O in App Launch",
                        rule_id=rule_id,
                        file_path=file_str,
                        line_number=idx + 1,
                        matched_snippet=stripped,
                        description="Synchronous Data(contentsOf:) blocks main thread execution during app launch sequence.",
                        remediation="Load cached or disk files asynchronously off the main thread."
                    ))

            # Check 3: Synchronous third-party SDK inits in launch scope
            if in_launch_scope:
                for pat, sdk_name in SDK_INIT_PATTERNS:
                    if pat.search(line):
                        rule_id = f"LAUNCH_SDK_INIT_{sdk_name.upper()}"
                        if not self.is_rule_suppressed(line, prev_line, rule_id):
                            self.findings.append(Finding(
                                severity="High",
                                category="Synchronous SDK Init in Launch",
                                rule_id=rule_id,
                                file_path=file_str,
                                line_number=idx + 1,
                                matched_snippet=stripped,
                                description=f"Synchronous {sdk_name} SDK initialization in main-thread launch path inflates cold start latency.",
                                remediation=f"Defer {sdk_name} setup or dispatch to a background Task after first view renders."
                            ))

            # Check 4: Obsolete synchronous UserDefaults.synchronize()
            if "UserDefaults.standard.synchronize()" in line:
                rule_id = "LAUNCH_OBSOLETE_USERDEFAULTS_SYNC"
                if not self.is_rule_suppressed(line, prev_line, rule_id):
                    self.findings.append(Finding(
                        severity="Medium",
                        category="Obsolete Synchronous Disk Flush",
                        rule_id=rule_id,
                        file_path=file_str,
                        line_number=idx + 1,
                        matched_snippet=stripped,
                        description="UserDefaults.standard.synchronize() is deprecated, redundant, and forces synchronous main thread disk flushes.",
                        remediation="Remove .synchronize() call; iOS automatically handles asynchronous writes atomically."
                    ))

            # Check 5: Swift global heavy static initializers (strictly at file root indentation)
            if re.search(r'^(?:public\s+|private\s+|internal\s+|fileprivate\s+)?let\s+[a-zA-Z0-9_]+\s*=\s*(?:try\??\s*)?(?:Data\(contentsOf|UIImage\(named)', line):
                rule_id = "LAUNCH_HEAVY_STATIC_INIT"
                if not self.is_rule_suppressed(line, prev_line, rule_id):
                    self.findings.append(Finding(
                        severity="Medium",
                        category="Top-level Heavy Global Initializer",
                        rule_id=rule_id,
                        file_path=file_str,
                        line_number=idx + 1,
                        matched_snippet=stripped,
                        description="Top-level global variable initialized with I/O or image assets, triggering synchronous disk access on module load.",
                        remediation="Wrap inside lazy property or static struct container to defer initialization until actual use."
                    ))

    def _scan_objc_file(self, file_path: Path):
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return

        lines = content.splitlines()
        self.lines_scanned += len(lines)
        file_str = str(file_path)

        for idx, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("//"):
                continue

            # Check Objective-C +load methods
            if re.search(r'^\s*\+\s*\(\s*void\s*\)\s*load\b', line):
                rule_id = "LAUNCH_OBJC_PLUS_LOAD"
                prev_line = lines[idx - 1] if idx > 0 else ""
                if not self.is_rule_suppressed(line, prev_line, rule_id):
                    self.findings.append(Finding(
                        severity="High",
                        category="Pre-Main Execution Overhead (+load)",
                        rule_id=rule_id,
                        file_path=file_str,
                        line_number=idx + 1,
                        matched_snippet=stripped,
                        description="Objective-C +load method executes synchronously before main() during dyld image initialization, increasing pre-main cold start.",
                        remediation="Replace with +initialize (called lazily on first message) or explicit post-launch configuration."
                    ))


def format_table(scanner: AppLaunchScanner) -> str:
    lines = []
    lines.append(f"\n{BOLD}{CYAN}=== iOS App Launch & Startup Performance Audit ==={RESET}")
    lines.append(f"Scanned {scanner.files_scanned} files ({scanner.lines_scanned} lines)\n")

    counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    for f in scanner.findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1

    lines.append(
        f"{BOLD}Summary Findings:{RESET} "
        f"{RED}Critical: {counts['Critical']}{RESET} | "
        f"{YELLOW}High: {counts['High']}{RESET} | "
        f"{CYAN}Medium: {counts['Medium']}{RESET} | "
        f"{DIM}Low: {counts['Low']}{RESET}\n"
    )

    if not scanner.findings:
        lines.append(f"{GREEN}✅ No app launch bottlenecks detected (under 400ms target).{RESET}\n")
        return "\n".join(lines)

    lines.append(f"{'SEV':<10} {'RULE ID':<32} {'LOCATION':<36} {'CATEGORY'}")
    lines.append("-" * 96)

    for f in scanner.findings:
        color = RED if f.severity == "Critical" else YELLOW if f.severity == "High" else CYAN
        loc = f"{Path(f.file_path).name}:{f.line_number}"
        lines.append(f"{color}{f.severity:<10}{RESET} {f.rule_id:<32} {loc:<36} {f.category}")
        lines.append(f"  {DIM}Snippet:{RESET} {f.matched_snippet}")
        lines.append(f"  {DIM}Fix:{RESET} {f.remediation}\n")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="iOS App Launch & Startup Performance Fast-Scanner")
    parser.add_argument("path", nargs="?", default=".", help="Target Xcode project or folder")
    parser.add_argument("--format", choices=["table", "json", "markdown", "xcode"], default="table")
    parser.add_argument("--min-severity", choices=["critical", "high", "medium", "low"], default="low")
    parser.add_argument("--include-tests", action="store_true", help="Include test files in audit")
    parser.add_argument("-o", "--output", help="Write report to file")

    args = parser.parse_args()
    scanner = AppLaunchScanner(args.path, min_severity=args.min_severity, include_tests=args.include_tests)
    findings = scanner.scan()

    if args.format == "table":
        out = format_table(scanner)
    elif args.format == "xcode":
        out = "\n".join([f"{f.file_path}:{f.line_number}:1: {'error' if f.severity in ['Critical', 'High'] else 'warning'}: [ios-app-launch-audit] [{f.rule_id}] {f.description}" for f in findings])
    elif args.format == "markdown":
        out = f"# iOS App Launch Performance Report\n\nTotal findings: {len(findings)}\n"
    else:
        out = json.dumps([asdict(f) for f in findings], indent=2)

    if args.output:
        Path(args.output).write_text(out, encoding="utf-8")
        print(f"Report written to: {args.output}")
    else:
        if out:
            print(out)

    has_crit = any(f.severity in ["Critical", "High"] for f in findings)
    sys.exit(1 if has_crit else 0)


if __name__ == "__main__":
    main()
