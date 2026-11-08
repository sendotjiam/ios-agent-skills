#!/usr/bin/env python3
"""iOS Concurrency & Performance Fast Scanner.

Scans Swift and Objective-C files for concurrency hazards, main-thread blocking,
actor reentrancy bugs, deadlocks, Swift 6 unsafety, and scroll hitch triggers.
"""

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Optional

SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}

DEFAULT_EXCLUDES = {
    ".build",
    ".git",
    "DerivedData",
    "Pods",
    "Carthage",
    "fastlane",
    ".swiftpm",
}

DEFAULT_TEST_EXCLUDES = {
    "Tests",
    "UITests",
    "UnitTests",
    "IntegrationTests",
    "Mocks",
    "Fixtures",
    "TestHelpers",
}


@dataclass
class Finding:
    rule_id: str
    severity: str
    category: str
    file_path: str
    line_number: int
    line_content: str
    message: str
    recommendation: str


RULES = [
    # Critical Hangs & Deadlocks
    {
        "id": "HANG-001",
        "severity": "CRITICAL",
        "category": "Main Thread Hang",
        "pattern": re.compile(r"Data\s*\(\s*contentsOf\s*:"),
        "message": "Synchronous Data(contentsOf:) blocks the calling thread during disk or network I/O.",
        "recommendation": "Offload to Task.detached or URLSession.shared.data(from:).",
    },
    {
        "id": "HANG-002",
        "severity": "CRITICAL",
        "category": "Main Thread Hang",
        "pattern": re.compile(r"DispatchQueue\.main\.sync\b"),
        "message": "DispatchQueue.main.sync causes immediate deadlock if invoked from the main thread.",
        "recommendation": "Use DispatchQueue.main.async or @MainActor isolated async methods.",
    },
    {
        "id": "DEADLOCK-001",
        "severity": "CRITICAL",
        "category": "Deadlock / Starvation",
        "pattern": re.compile(r"\b(DispatchSemaphore|semaphore)\b.*\.wait\s*\("),
        "message": "Synchronous semaphore wait inside async code can starve the cooperative thread pool.",
        "recommendation": "Migrate to async/await or withCheckedContinuation.",
    },
    {
        "id": "DEADLOCK-002",
        "severity": "CRITICAL",
        "category": "Deadlock / Starvation",
        "pattern": re.compile(r"Thread\.sleep\s*\("),
        "message": "Thread.sleep blocks the physical OS thread, breaking cooperative concurrency.",
        "recommendation": "Use Task.sleep(nanoseconds:) or Task.sleep(for:).",
    },
    # High Severity: Swift 6 Unsafe & Data Persistence
    {
        "id": "SWIFT6-001",
        "severity": "HIGH",
        "category": "Swift 6 Unsafe Escape",
        "pattern": re.compile(r"@unchecked\s+Sendable\b"),
        "message": "@unchecked Sendable disables compiler race checking and may conceal data races.",
        "recommendation": "Use actor isolation, immutable value types, or OSAllocatedUnfairLock / Mutex.",
    },
    {
        "id": "SWIFT6-002",
        "severity": "HIGH",
        "category": "Swift 6 Unsafe Escape",
        "pattern": re.compile(r"MainActor\.assumeIsolated\b"),
        "message": "MainActor.assumeIsolated crashes at runtime if invoked off the main thread.",
        "recommendation": "Explicitly mark caller with @MainActor or await MainActor.run.",
    },
    {
        "id": "SWIFT6-003",
        "severity": "HIGH",
        "category": "Swift 6 Global State",
        "pattern": re.compile(r"nonisolated\(unsafe\)\s+(var|let)\b"),
        "message": "nonisolated(unsafe) opts out of data race protection for global or shared state.",
        "recommendation": "Protect with a global actor (@MainActor) or thread-safe synchronization primitive.",
    },
    {
        "id": "PERSIST-001",
        "severity": "HIGH",
        "category": "Data Persistence Threading",
        "pattern": re.compile(r"\.viewContext\b.*\.(performAndWait|save\(\)|fetch\()"),
        "message": "Heavy Core Data operations on viewContext directly block the main thread.",
        "recommendation": "Use persistentContainer.newBackgroundContext() or performBackgroundTask.",
    },
    {
        "id": "PERSIST-002",
        "severity": "HIGH",
        "category": "Data Persistence Threading",
        "pattern": re.compile(r"func\s+\w+\s*\(.*:\s*NSManagedObject\b"),
        "message": "Passing NSManagedObject across isolation or async boundaries causes thread conflicts.",
        "recommendation": "Pass NSManagedObjectID or PersistentIdentifier and fetch on destination context.",
    },
    # Medium: Scroll Hitches & Allocation Churn
    {
        "id": "HITCH-001",
        "severity": "MEDIUM",
        "category": "Scroll Hitch / Allocation",
        "pattern": re.compile(r"(DateFormatter|ISO8601DateFormatter|NumberFormatter)\s*\(\s*\)"),
        "message": "Instantiating formatters is costly (~1-5ms); in cell rendering this causes dropped frames.",
        "recommendation": "Cache in a static property or use Swift 5.5+ Date.formatted(...) Style.",
    },
    {
        "id": "HITCH-002",
        "severity": "MEDIUM",
        "category": "Scroll Hitch / Image Decode",
        "pattern": re.compile(r"UIImage\s*\(\s*(data|contentsOfFile)\s*:"),
        "message": "Synchronously decoding images into views inside cell render loops causes frame hitches.",
        "recommendation": "Decode off-main with preparingForDisplay() or ImageIO thumbnail downsampling.",
    },
    {
        "id": "HITCH-003",
        "severity": "MEDIUM",
        "category": "Scroll Hitch / Allocation",
        "pattern": re.compile(r"NSRegularExpression\s*\(\s*pattern\s*:"),
        "message": "Compiling regex on main thread in hot loops causes layout stalls.",
        "recommendation": "Cache compiled NSRegularExpression statically or use Regex literals (Swift 5.7+).",
    },
    # Low / Moderate: Task Lifecycle & Combine Bridges
    {
        "id": "TASK-001",
        "severity": "MEDIUM",
        "category": "Task Retain Cycle / Leak",
        "pattern": re.compile(r"Task\s*\{\s*\[\s*self\s*\]"),
        "message": "Strong self capture in Task without lifecycle management risks leaking ViewControllers.",
        "recommendation": "Use [weak self] or bind task cancellation to view lifecycle (SwiftUI .task).",
    },
    {
        "id": "COMBINE-001",
        "severity": "LOW",
        "category": "Combine Thrashing",
        "pattern": re.compile(r"\.receive\s*\(\s*on\s*:\s*DispatchQueue\.main\s*\)"),
        "message": "Redundant main queue dispatches inside @MainActor isolated classes causes extra runloop hops.",
        "recommendation": "Rely on @MainActor isolation contract rather than manual Combine thread hops.",
    },
]


def strip_inline_comment(line: str) -> str:
    """Strips trailing // comments while preserving string literals."""
    in_string = False
    escape = False
    out = []
    i = 0
    while i < len(line):
        ch = line[i]
        if escape:
            out.append(ch)
            escape = False
            i += 1
            continue
        if ch == '\\' and in_string:
            out.append(ch)
            escape = True
            i += 1
            continue
        if ch == '"':
            in_string = not in_string
            out.append(ch)
            i += 1
            continue
        if not in_string and i + 1 < len(line) and line[i:i+2] == '//':
            break
        out.append(ch)
        i += 1
    return "".join(out)


def is_rule_suppressed(line: str, prev_line: Optional[str], rule_id: str) -> bool:
    """Checks for same-line // ios-audit:ignore <RULE> or previous-line // ios-audit:ignore-next-line <RULE>."""
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


def should_skip(path: Path, include_tests: bool = False) -> bool:
    for part in path.parts:
        if part in DEFAULT_EXCLUDES or part.endswith(".xcodeproj") or part.endswith(".xcworkspace"):
            return True
        if not include_tests:
            if part in DEFAULT_TEST_EXCLUDES or part.endswith("Tests") or part.endswith("UITests"):
                return True
    if not include_tests:
        name = path.name
        if name.endswith("Tests.swift") or name.endswith("Test.swift") or name.endswith("Mock.swift") or name.endswith("Fixture.swift"):
            return True
    return False


def scan_file(file_path: Path) -> List[Finding]:
    findings: List[Finding] = []
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except Exception:
        return findings

    prev_line = ""
    for idx, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()
        if stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
            prev_line = raw_line
            continue

        code_only = strip_inline_comment(raw_line)

        for rule in RULES:
            rule_id = rule["id"]
            if is_rule_suppressed(raw_line, prev_line, rule_id):
                continue

            # Avoid false positive on static or lazy cached formatters
            if rule_id == "HITCH-001" and re.search(r"\b(static\s+let|static\s+var|lazy\s+var)\b", code_only):
                continue

            if rule["pattern"].search(code_only):
                findings.append(
                    Finding(
                        rule_id=rule_id,
                        severity=rule["severity"],
                        category=rule["category"],
                        file_path=str(file_path),
                        line_number=idx,
                        line_content=stripped[:120],
                        message=rule["message"],
                        recommendation=rule["recommendation"],
                    )
                )

        prev_line = raw_line

    return findings


def scan_directory(root_path: Path, include_tests: bool = False) -> List[Finding]:
    all_findings: List[Finding] = []
    if root_path.is_file():
        return scan_file(root_path)

    for ext in ("*.swift", "*.m", "*.h"):
        for path in root_path.rglob(ext):
            if not should_skip(path, include_tests=include_tests):
                all_findings.extend(scan_file(path))

    all_findings.sort(key=lambda x: (SEVERITY_ORDER.get(x.severity, 99), x.file_path, x.line_number))
    return all_findings


def format_table(findings: List[Finding]) -> str:
    if not findings:
        return "✅ No concurrency hazards or hang risks detected."

    lines = [
        f"{'SEVERITY':<10} {'ID':<12} {'LOCATION':<50} {'MESSAGE'}",
        "=" * 110,
    ]
    for f in findings:
        loc = f"{Path(f.file_path).name}:{f.line_number}"
        lines.append(f"{f.severity:<10} {f.rule_id:<12} {loc:<50} {f.message}")
    return "\n".join(lines)


def format_xcode(findings: List[Finding]) -> str:
    if not findings:
        return ""
    lines = []
    for f in findings:
        sev = "error" if f.severity.upper() in ["CRITICAL", "HIGH"] else "warning"
        lines.append(f"{f.file_path}:{f.line_number}:1: {sev}: [{f.rule_id}] {f.message}")
    return "\n".join(lines)


def format_markdown(findings: List[Finding], target: str) -> str:
    if not findings:
        return "## iOS Concurrency Fast Scan\n\n✅ **Clean**: No concurrency hazards or hang risks detected."

    counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1

    md = [
        f"# iOS Concurrency Fast Scan: `{target}`",
        "",
        "## Summary",
        f"- **Critical**: {counts['CRITICAL']}",
        f"- **High**: {counts['HIGH']}",
        f"- **Medium**: {counts['MEDIUM']}",
        f"- **Low**: {counts['LOW']}",
        "",
        "## Findings",
        "",
        "| Severity | Rule ID | Category | File:Line | Recommendation |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ]

    for f in findings:
        file_ref = f"`{Path(f.file_path).name}:{f.line_number}`"
        md.append(f"| **{f.severity}** | `{f.rule_id}` | {f.category} | {file_ref} | {f.recommendation} |")

    return "\n".join(md)


def main():
    parser = argparse.ArgumentParser(description="Scan iOS codebase for concurrency and main-thread performance risks.")
    parser.add_argument("path", nargs="?", default=".", help="Path to project or file to scan (default: current directory)")
    parser.add_argument("--format", choices=["table", "text", "markdown", "json", "xcode"], default="table", help="Output format")
    parser.add_argument("--min-severity", choices=["CRITICAL", "HIGH", "MEDIUM", "LOW"], default="LOW", help="Minimum severity to report")
    parser.add_argument("--include-tests", action="store_true", help="Include test directories and test files in scan")
    parser.add_argument("--output", "-o", help="Write output to file instead of stdout")

    args = parser.parse_args()
    target_path = Path(args.path).resolve()

    if not target_path.exists():
        print(f"Error: Path does not exist: {target_path}", file=sys.stderr)
        sys.exit(1)

    findings = scan_directory(target_path, include_tests=args.include_tests)
    min_rank = SEVERITY_ORDER.get(args.min_severity, 3)
    filtered = [f for f in findings if SEVERITY_ORDER.get(f.severity, 3) <= min_rank]

    if args.format == "json":
        output = json.dumps([asdict(f) for f in filtered], indent=2)
    elif args.format == "markdown":
        output = format_markdown(filtered, str(target_path))
    elif args.format == "xcode":
        output = format_xcode(filtered)
    else:
        output = format_table(filtered)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output + "\n")
        print(f"Report written to: {args.output}")
    else:
        if output:
            print(output)

    has_critical = any(f.severity == "CRITICAL" for f in filtered)
    sys.exit(1 if has_critical else 0)


if __name__ == "__main__":
    main()
