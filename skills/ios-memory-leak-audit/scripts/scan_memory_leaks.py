#!/usr/bin/env python3
"""
scan_memory_leaks.py - Zero-dependency iOS Memory Leak & Retain Cycle Auditor

Scans Swift source files for high-risk ARC retain cycles, closure capture hazards,
memory bloat (missing @autoreleasepool, raw image decoding, Core Data context bloat),
WebKit/AVFoundation observer leaks, GCD delayed retain traps, and CoreFoundation leaks.
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

class MemoryLeakScanner:
    def __init__(self, target_path: str, min_severity: str = "low", ignore_patterns: Optional[List[str]] = None):
        self.target_path = Path(target_path).resolve()
        self.min_severity = min_severity.lower()
        self.ignore_patterns = ignore_patterns or [
            "Pods", "DerivedData", ".build", ".swiftpm", "Carthage", ".git", "golden_fixes"
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
        start_time = time.time()
        swift_files = []

        if self.target_path.is_file():
            if self.target_path.suffix == ".swift":
                swift_files.append(self.target_path)
        else:
            for root, dirs, files in os.walk(self.target_path):
                # Filter out ignored directories
                dirs[:] = [d for d in dirs if not any(ign in d for ign in self.ignore_patterns)]
                for file in files:
                    if file.endswith(".swift"):
                        full_p = Path(root) / file
                        if not self.should_ignore(full_p):
                            swift_files.append(full_p)

        self.files_scanned = len(swift_files)
        for file_p in swift_files:
            self._scan_file(file_p)

        # Filter by minimum severity
        min_rank = self.severity_order.get(self.min_severity, 1)
        self.findings = [
            f for f in self.findings if self.severity_order.get(f.severity.lower(), 1) >= min_rank
        ]

        # Sort by severity descending, then file and line
        self.findings.sort(
            key=lambda x: (-self.severity_order.get(x.severity.lower(), 1), x.file_path, x.line_number)
        )
        return self.findings

    def _scan_file(self, file_path: Path):
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception:
            return

        lines = content.splitlines()
        self.lines_scanned += len(lines)
        file_str = str(file_path)

        # Run line-by-line and multiline checks
        self._check_strong_delegates(lines, file_str)
        self._check_combine_cycles(lines, file_str)
        self._check_timer_and_gcd_traps(lines, file_str)
        self._check_system_observers(lines, file_str)
        self._check_memory_bloat_loops(lines, file_str)
        self._check_caches_and_core_data(lines, file_str)
        self._check_corefoundation_unmanaged(lines, file_str)

    def _check_strong_delegates(self, lines: List[str], file_path: str):
        in_protocol = False
        for idx, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("protocol ") and "{" in stripped:
                in_protocol = True
            elif in_protocol and stripped.startswith("}"):
                in_protocol = False

            if in_protocol:
                continue

            delegate_match = re.search(r'\b(?:public|private|internal|fileprivate)?\s*var\s+([a-zA-Z0-9_]*delegate[a-zA-Z0-9_]*)\s*:\s*([A-Za-z0-9_]+)', line, re.IGNORECASE)
            if delegate_match and not re.search(r'\bweak\b', line):
                if not re.search(r'\{\s*(?:get|return)\b', line) and not stripped.startswith("//"):
                    self.findings.append(Finding(
                        severity="Critical",
                        category="Strong Delegate Retain Cycle",
                        rule_id="STRONG_DELEGATE",
                        file_path=file_path,
                        line_number=idx + 1,
                        matched_snippet=stripped,
                        description=f"Delegate property '{delegate_match.group(1)}' declared without 'weak', causing bidirectional retain cycles.",
                        remediation="Declare delegate as 'weak var delegate: SomeDelegate?' and constrain protocol to 'AnyObject'."
                    ))

    def _check_combine_cycles(self, lines: List[str], file_path: str):
        for idx, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("//"):
                continue

            # Check assign(to:on: self)
            if ".assign(" in line and "on: self" in "\n".join(lines[idx:min(idx + 3, len(lines))]):
                self.findings.append(Finding(
                    severity="Critical",
                    category="Combine assign(to:on:) Retain Cycle",
                    rule_id="COMBINE_ASSIGN_CYCLE",
                    file_path=file_path,
                    line_number=idx + 1,
                    matched_snippet=stripped,
                    description="Combine's 'assign(to:on: self)' creates an immediate strong retain cycle to self.",
                    remediation="Use 'assign(to: &$publishedProperty)' or rewrite as '.sink { [weak self] in self?.prop = $0 }'."
                ))

            # Check .sink without weak/unowned self
            if re.search(r'\.sink\s*\{', line) and not re.search(r'\[\s*(?:weak|unowned)\s+self\s*\]', line):
                lookahead_window = "\n".join(lines[idx:min(idx + 5, len(lines))])
                if "self." in lookahead_window and not re.search(r'\[\s*(?:weak|unowned)\s+self\s*\]', lookahead_window):
                    self.findings.append(Finding(
                        severity="Critical",
                        category="Combine .sink Closure Retain Cycle",
                        rule_id="COMBINE_SINK_CYCLE",
                        file_path=file_path,
                        line_number=idx + 1,
                        matched_snippet=stripped,
                        description="Combine '.sink' closure captures 'self' strongly, keeping subscription and owner alive permanently.",
                        remediation="Add '[weak self]' to the capture list: '.sink { [weak self] value in self?.handle(value) }'."
                    ))

    def _check_timer_and_gcd_traps(self, lines: List[str], file_path: str):
        for idx, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("//"):
                continue

            # Multiline Timer.scheduledTimer check
            if "Timer.scheduledTimer" in line:
                window = "\n".join(lines[idx:min(idx + 10, len(lines))])
                if re.search(r'target\s*:\s*self\b', window):
                    self.findings.append(Finding(
                        severity="Critical",
                        category="Timer Target-Action RunLoop Cycle",
                        rule_id="TIMER_TARGET_SELF",
                        file_path=file_path,
                        line_number=idx + 1,
                        matched_snippet=stripped,
                        description="Timer strongly retains target 'self' in the RunLoop until explicitly invalidated.",
                        remediation="Use block-based 'Timer.scheduledTimer(withTimeInterval:repeats:) { [weak self] _ in }' or WeakProxy."
                    ))

            # DispatchSourceTimer event handler capturing self
            if "DispatchSource.makeTimerSource" in line:
                lookahead = "\n".join(lines[idx:min(idx + 12, len(lines))])
                if re.search(r'setEventHandler\s*\{(?!\s*\[\s*weak)', lookahead) and "self." in lookahead:
                    self.findings.append(Finding(
                        severity="High",
                        category="DispatchSourceTimer Retain Cycle",
                        rule_id="GCD_TIMER_CYCLE",
                        file_path=file_path,
                        line_number=idx + 1,
                        matched_snippet=stripped,
                        description="DispatchSourceTimer setEventHandler strongly captures self, forming a retain cycle with the stored timer.",
                        remediation="Add '[weak self]' to setEventHandler: 'timer.setEventHandler { [weak self] in self?.tick() }'."
                    ))

            # DispatchQueue asyncAfter with self
            if ".asyncAfter" in line:
                lookahead = "\n".join(lines[idx:min(idx + 6, len(lines))])
                if ("self." in lookahead or "self?" in lookahead) and not re.search(r'\[\s*(?:weak|unowned)\s+self\s*\]', lookahead):
                    self.findings.append(Finding(
                        severity="Medium",
                        category="GCD asyncAfter Delayed Retention",
                        rule_id="GCD_DELAYED_RETENTION",
                        file_path=file_path,
                        line_number=idx + 1,
                        matched_snippet=stripped,
                        description="Delayed asyncAfter block strongly captures 'self', keeping the instance alive in memory until the delay completes.",
                        remediation="Add '[weak self]' to allow immediate deallocation on screen dismissal."
                    ))

    def _check_system_observers(self, lines: List[str], file_path: str):
        for idx, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("//"):
                continue

            # Multiline NotificationCenter block observer check
            if "NotificationCenter.default.addObserver(" in line or "NotificationCenter.default.addObserver" in line:
                window = "\n".join(lines[idx:min(idx + 10, len(lines))])
                if "forName:" in window:
                    # Check if assigned to token
                    has_assignment = bool(re.search(r'(?:let|var)\s+[a-zA-Z0-9_]+\s*=\s*NotificationCenter', line)) or \
                                     bool(re.search(r'(?:let|var)\s+[a-zA-Z0-9_]+\s*=\s*NotificationCenter', "\n".join(lines[max(0, idx-1):idx+1])))
                    if not has_assignment or ("self." in window and not re.search(r'\[\s*weak\s+self\s*\]', window)):
                        self.findings.append(Finding(
                            severity="Medium",
                            category="NotificationCenter Observer Token Discard",
                            rule_id="NOTIFICATION_TOKEN_DISCARD",
                            file_path=file_path,
                            line_number=idx + 1,
                            matched_snippet=stripped,
                            description="NotificationCenter block observer created without retaining token or without weak self capture.",
                            remediation="Store returned NSObjectProtocol token and call NotificationCenter.default.removeObserver(token) in deinit."
                        ))

            # WKUserContentController.add(self, name:)
            if re.search(r'userContentController\.add\s*\(\s*self\s*,', line):
                self.findings.append(Finding(
                    severity="Critical",
                    category="WebKit Script Message Handler Leak",
                    rule_id="WEBKIT_HANDLER_CYCLE",
                    file_path=file_path,
                    line_number=idx + 1,
                    matched_snippet=stripped,
                    description="WKUserContentController retains script message handler 'self' strongly, permanently leaking the UIViewController.",
                    remediation="Wrap self in a WeakProxy: 'userContentController.add(WeakProxy(self), name: \"...\")'."
                ))

            # AVPlayer addPeriodicTimeObserver without token capture
            if "addPeriodicTimeObserver" in line:
                window = "\n".join(lines[idx:min(idx + 6, len(lines))])
                has_token = bool(re.search(r'(?:let|var)\s+[a-zA-Z0-9_]+\s*=\s*.*addPeriodicTimeObserver', window)) or \
                            bool(re.search(r'[a-zA-Z0-9_.]+\s*=\s*.*addPeriodicTimeObserver', line))
                if not has_token:
                    self.findings.append(Finding(
                        severity="Medium",
                        category="AVPlayer Periodic Time Observer Leak",
                        rule_id="AVFOUNDATION_OBSERVER_LEAK",
                        file_path=file_path,
                        line_number=idx + 1,
                        matched_snippet=stripped,
                        description="addPeriodicTimeObserver called without capturing observer token for later removal.",
                        remediation="Store token and call 'player.removeTimeObserver(token)' when tearing down player."
                    ))

    def _check_memory_bloat_loops(self, lines: List[str], file_path: str):
        loop_pattern = re.compile(r'for\s+[a-zA-Z0-9_()]+\s+in\s+([a-zA-Z0-9_.]+)\s*\{')
        for idx, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("//"):
                continue

            match = loop_pattern.search(line)
            if match:
                loop_body = "\n".join(lines[idx:min(idx + 25, len(lines))])
                if "@autoreleasepool" not in loop_body:
                    if re.search(r'\b(?:UIImage|CIImage|CGImageSource|Data\(contentsOf|CVPixelBuffer)\b', loop_body):
                        self.findings.append(Finding(
                            severity="High",
                            category="Loop Memory Bloat (Missing @autoreleasepool)",
                            rule_id="LOOP_WITHOUT_AUTORELEASE",
                            file_path=file_path,
                            line_number=idx + 1,
                            matched_snippet=stripped,
                            description="Batch loop allocating high-memory objects (UIImage/Data) without @autoreleasepool, risking JetSam OOM crash.",
                            remediation="Wrap loop iteration body in '@autoreleasepool { ... }' to flush allocations immediately."
                        ))

    def _check_caches_and_core_data(self, lines: List[str], file_path: str):
        for idx, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("//"):
                continue

            # Unbounded dictionary cache
            if re.search(r'(?:private|public|internal)?\s*(?:var|let)\s+[a-zA-Z0-9_]*cache[a-zA-Z0-9_]*\s*=\s*\[\s*[A-Za-z0-9_]+\s*:\s*[A-Za-z0-9_]+\s*\]\(\)', line, re.IGNORECASE):
                self.findings.append(Finding(
                    severity="High",
                    category="Unbounded Dictionary Memory Cache",
                    rule_id="UNBOUNDED_CACHE",
                    file_path=file_path,
                    line_number=idx + 1,
                    matched_snippet=stripped,
                    description="Standard Swift Dictionary used as cache without eviction policy or memory-pressure purge.",
                    remediation="Replace with 'NSCache<Key, Value>' to allow automatic system eviction during memory pressure."
                ))

            # Core Data batch fetch loop without context reset
            if ".fetch(" in line:
                window_lines = [l for l in lines[max(0, idx - 10):min(idx + 15, len(lines))] if not l.strip().startswith("//")]
                window = "\n".join(window_lines)
                if "for " in window and not re.search(r'\b(?:context\.)?reset\(\)', window) and "refreshAllObjects" not in window:
                    self.findings.append(Finding(
                        severity="High",
                        category="Core Data Batch Fault Bloat",
                        rule_id="CORE_DATA_BATCH_BLOAT",
                        file_path=file_path,
                        line_number=idx + 1,
                        matched_snippet=stripped,
                        description="Batch processing Core Data records without 'context.reset()' causes persistent memory retention.",
                        remediation="Call 'context.reset()' or 'context.refreshAllObjects()' periodically in batch loops."
                    ))

    def _check_corefoundation_unmanaged(self, lines: List[str], file_path: str):
        for idx, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("//"):
                continue

            if "Unmanaged.passRetained" in line:
                lookahead = "\n".join(lines[idx:min(idx + 15, len(lines))])
                if "release()" not in lookahead and "takeRetainedValue()" not in lookahead:
                    self.findings.append(Finding(
                        severity="Critical",
                        category="Unmanaged Retained Pointer Leak",
                        rule_id="UNMANAGED_CF_LEAK",
                        file_path=file_path,
                        line_number=idx + 1,
                        matched_snippet=stripped,
                        description="Unmanaged.passRetained transfers ownership without corresponding release or takeRetainedValue.",
                        remediation="Ensure Unmanaged instance is balanced with .release() or consumed via .takeRetainedValue()."
                    ))

    def format_table(self) -> str:
        out = []
        out.append(f"\n{BOLD}{CYAN}=== iOS Memory Leak & Retain Cycle Audit Scan ==={RESET}")
        out.append(f"{DIM}Scanned {self.files_scanned} Swift files ({self.lines_scanned} lines){RESET}\n")

        if not self.findings:
            out.append(f"{GREEN}✓ No memory leak hazards detected! Clean codebase.{RESET}\n")
            return "\n".join(out)

        counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
        for f in self.findings:
            counts[f.severity] = counts.get(f.severity, 0) + 1

        out.append(f"{BOLD}Summary Findings:{RESET}")
        out.append(f"  {RED}Critical: {counts['Critical']}{RESET} | {YELLOW}High: {counts['High']}{RESET} | "
                   f"{CYAN}Medium: {counts['Medium']}{RESET} | {DIM}Low: {counts['Low']}{RESET}\n")

        out.append(f"{'-'*90}")
        out.append(f"{BOLD}{'SEV':<10} {'RULE ID':<26} {'LOCATION':<36} {'CATEGORY'}{RESET}")
        out.append(f"{'-'*90}")

        for f in self.findings:
            sev_color = RED if f.severity == "Critical" else (YELLOW if f.severity == "High" else CYAN)
            rel_path = os.path.relpath(f.file_path, self.target_path if self.target_path.is_dir() else self.target_path.parent)
            loc = f"{rel_path}:{f.line_number}"
            if len(loc) > 34:
                loc = "..." + loc[-31:]

            out.append(f"{sev_color}{f.severity:<10}{RESET} {f.rule_id:<26} {loc:<36} {f.category}")
            out.append(f"  {DIM}Snippet:{RESET} {f.matched_snippet[:80]}")
            out.append(f"  {GREEN}Fix:{RESET} {f.remediation}\n")

        return "\n".join(out)

    def format_markdown(self) -> str:
        out = []
        out.append("# iOS Memory Leak & Retain Cycle Audit Report\n")
        out.append(f"**Target:** `{self.target_path}`  ")
        out.append(f"**Files Scanned:** {self.files_scanned}  ")
        out.append(f"**Lines Scanned:** {self.lines_scanned}  ")
        out.append(f"**Total Findings:** {len(self.findings)}\n")

        counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
        for f in self.findings:
            counts[f.severity] = counts.get(f.severity, 0) + 1

        out.append(f"| Critical (Permanent Cycle) | High (OOM Bloat) | Medium (Zombie Subscriptions) | Low (Hygiene) |")
        out.append(f"| :---: | :---: | :---: | :---: |")
        out.append(f"| **{counts['Critical']}** | **{counts['High']}** | **{counts['Medium']}** | **{counts['Low']}** |\n")

        if not self.findings:
            out.append("> ✅ **Clean Scan:** No memory leak or ARC retain cycle hazards detected.\n")
            return "\n".join(out)

        out.append("## Detailed Findings\n")
        out.append("| Severity | Rule ID | File:Line | Description | Actionable Remediation |")
        out.append("| :--- | :--- | :--- | :--- | :--- |")

        for f in self.findings:
            rel_path = os.path.relpath(f.file_path, self.target_path if self.target_path.is_dir() else self.target_path.parent)
            out.append(f"| **{f.severity}** | `{f.rule_id}` | `{rel_path}:{f.line_number}` | {f.description} | {f.remediation} |")

        return "\n".join(out)

    def format_json(self) -> str:
        data = {
            "target": str(self.target_path),
            "files_scanned": self.files_scanned,
            "lines_scanned": self.lines_scanned,
            "total_findings": len(self.findings),
            "findings": [asdict(f) for f in self.findings]
        }
        return json.dumps(data, indent=2)

def main():
    parser = argparse.ArgumentParser(
        description="Zero-dependency iOS Memory Leak & Retain Cycle Auditor"
    )
    parser.add_argument("path", help="Path to iOS project directory or Swift file")
    parser.add_argument(
        "--format",
        choices=["table", "markdown", "json"],
        default="table",
        help="Report output format (default: table)"
    )
    parser.add_argument(
        "-o", "--output",
        help="Write report output to specified file"
    )
    parser.add_argument(
        "--severity",
        choices=["critical", "high", "medium", "low"],
        default="low",
        help="Minimum severity threshold to report (default: low)"
    )
    parser.add_argument(
        "--ignore",
        help="Comma-separated folder names to ignore"
    )

    args = parser.parse_args()
    ignore_list = [p.strip() for p in args.ignore.split(",")] if args.ignore else None

    scanner = MemoryLeakScanner(
        target_path=args.path,
        min_severity=args.severity,
        ignore_patterns=ignore_list
    )
    findings = scanner.scan()

    if args.format == "table":
        output = scanner.format_table()
    elif args.format == "markdown":
        output = scanner.format_markdown()
    else:
        output = scanner.format_json()

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Report saved to {args.output}")
    else:
        print(output)

    has_blocking = any(f.severity in ["Critical", "High"] for f in findings)
    sys.exit(1 if has_blocking else 0)

if __name__ == "__main__":
    main()
