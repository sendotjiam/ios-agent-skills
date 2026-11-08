#!/usr/bin/env python3
"""
ios_audit.py - Unified Multi-Skill iOS & Apple Engineering Auditor

Orchestrates all specialized iOS agent skills across:
  1. Concurrency & Hangs (ios-concurrency-audit)
  2. SwiftUI Render Optimization (swiftui-render-optimization)
  3. Memory Leaks & ARC (ios-memory-leak-audit)
  4. Core Data & SwiftData Persistence (coredata-swiftdata-audit)
  5. Accessibility & WCAG Compliance (ios-a11y-audit)
  6. Codebase & Dead Resource Cleanup (ios-codebase-cleanup)

Supports:
  - Xcode Build Phase integration (--format xcode)
  - GitHub Actions & PR review reports (--format markdown)
  - CI Quality Gates (--format json)
  - Interactive CLI tables (--format table)
  - Inline comment suppression (// ios-audit:ignore <RULE>)
  - Automated test directory filtering (--include-tests)
"""

import argparse
import importlib.util
import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

REPO_ROOT = Path(__file__).resolve().parent.parent

# ANSI Colors
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}

ALL_SKILLS = [
    "concurrency",
    "renders",
    "memory",
    "persistence",
    "a11y",
    "cleanup",
]

SKILL_DISPLAY_NAMES = {
    "concurrency": "ios-concurrency-audit",
    "renders": "swiftui-render-optimization",
    "memory": "ios-memory-leak-audit",
    "persistence": "coredata-swiftdata-audit",
    "a11y": "ios-a11y-audit",
    "cleanup": "ios-codebase-cleanup",
}


@dataclass
class UnifiedFinding:
    skill: str
    rule_id: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    file_path: str
    line_number: int
    message: str
    recommendation: str


def load_module(name: str, path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Scanner module not found: {path}")
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class UnifiedAuditor:
    def __init__(
        self,
        target_path: Path,
        skills: List[str],
        min_severity: str = "LOW",
        include_tests: bool = False,
    ):
        self.target_path = target_path.resolve()
        self.skills = skills
        self.min_severity = min_severity.upper()
        self.include_tests = include_tests
        self.findings: List[UnifiedFinding] = []
        self.execution_times: Dict[str, float] = {}

    def run(self) -> List[UnifiedFinding]:
        for skill_key in self.skills:
            start_t = time.perf_counter()
            findings = self._run_skill(skill_key)
            duration = (time.perf_counter() - start_t) * 1000
            self.execution_times[skill_key] = duration
            self.findings.extend(findings)

        min_rank = SEVERITY_ORDER.get(self.min_severity, 3)
        self.findings = [
            f for f in self.findings if SEVERITY_ORDER.get(f.severity.upper(), 3) <= min_rank
        ]
        self.findings.sort(
            key=lambda x: (
                SEVERITY_ORDER.get(x.severity.upper(), 99),
                x.file_path,
                x.line_number,
            )
        )
        return self.findings

    def _run_skill(self, skill_key: str) -> List[UnifiedFinding]:
        skill_name = SKILL_DISPLAY_NAMES.get(skill_key, skill_key)
        findings: List[UnifiedFinding] = []

        try:
            if skill_key == "concurrency":
                script_path = REPO_ROOT / "skills/ios-concurrency-audit/scripts/scan_concurrency.py"
                mod = load_module("scan_concurrency", script_path)
                raw_findings = mod.scan_directory(self.target_path, include_tests=self.include_tests)
                for f in raw_findings:
                    findings.append(
                        UnifiedFinding(
                            skill=skill_name,
                            rule_id=f.rule_id,
                            severity=f.severity.upper(),
                            file_path=f.file_path,
                            line_number=f.line_number,
                            message=f.message,
                            recommendation=f.recommendation,
                        )
                    )

            elif skill_key == "renders":
                script_path = REPO_ROOT / "skills/swiftui-render-optimization/scripts/scan_swiftui_renders.py"
                mod = load_module("scan_swiftui_renders", script_path)
                swift_files = []
                if self.target_path.is_file() and self.target_path.suffix == ".swift":
                    swift_files.append(self.target_path)
                else:
                    for root, dirs, files in os.walk(self.target_path):
                        if not self.include_tests:
                            dirs[:] = [d for d in dirs if d not in mod.IGNORED_DIRS and not d.endswith("Tests") and not d.endswith("UITests")]
                        else:
                            dirs[:] = [d for d in dirs if d not in {".git", ".build", "Pods", "DerivedData", "Carthage", ".swiftpm"}]
                        for file in files:
                            if file.endswith(".swift"):
                                if not self.include_tests and (file.endswith("Tests.swift") or file.endswith("Test.swift") or file.endswith("Mock.swift")):
                                    continue
                                swift_files.append(Path(root) / file)

                for fp in swift_files:
                    for f in mod.scan_file(fp):
                        findings.append(
                            UnifiedFinding(
                                skill=skill_name,
                                rule_id=f.rule_id,
                                severity=f.severity.upper(),
                                file_path=f.file_path,
                                line_number=f.line_number,
                                message=f"{f.title}: {f.snippet}",
                                recommendation=f.recommendation,
                            )
                        )

            elif skill_key == "memory":
                script_path = REPO_ROOT / "skills/ios-memory-leak-audit/scripts/scan_memory_leaks.py"
                mod = load_module("scan_memory_leaks", script_path)
                scanner = mod.MemoryLeakScanner(
                    str(self.target_path),
                    min_severity="low",
                    include_tests=self.include_tests,
                )
                raw = scanner.scan()
                for f in raw:
                    findings.append(
                        UnifiedFinding(
                            skill=skill_name,
                            rule_id=f.rule_id,
                            severity=f.severity.upper(),
                            file_path=f.file_path,
                            line_number=f.line_number,
                            message=f.description,
                            recommendation=f.remediation,
                        )
                    )

            elif skill_key == "persistence":
                script_path = REPO_ROOT / "skills/coredata-swiftdata-audit/scripts/scan_coredata_swiftdata.py"
                mod = load_module("scan_coredata_swiftdata", script_path)
                scanner = mod.CoreDataSwiftDataScanner(
                    str(self.target_path),
                    min_severity="low",
                    include_tests=self.include_tests,
                )
                raw = scanner.scan()
                for f in raw:
                    findings.append(
                        UnifiedFinding(
                            skill=skill_name,
                            rule_id=f.rule_id,
                            severity=f.severity.upper(),
                            file_path=f.file_path,
                            line_number=f.line_number,
                            message=f.description,
                            recommendation=f.remediation,
                        )
                    )

            elif skill_key == "a11y":
                script_path = REPO_ROOT / "skills/ios-a11y-audit/scripts/scan_a11y.py"
                mod = load_module("scan_a11y", script_path)
                scanner = mod.AccessibilityScanner(
                    str(self.target_path),
                    min_severity="low",
                    include_tests=self.include_tests,
                )
                raw = scanner.scan()
                for f in raw:
                    findings.append(
                        UnifiedFinding(
                            skill=skill_name,
                            rule_id=f.rule_id,
                            severity=f.severity.upper(),
                            file_path=f.file_path,
                            line_number=f.line_number,
                            message=f.description,
                            recommendation=f.remediation,
                        )
                    )

            elif skill_key == "cleanup":
                script_path = REPO_ROOT / "skills/ios-codebase-cleanup/scripts/scan_codebase_cleanup.py"
                mod = load_module("scan_codebase_cleanup", script_path)
                scanner = mod.CleanupScanner(str(self.target_path), scopes=["files", "assets", "docs", "symbols", "imports"])
                scanner.run()
                summary = scanner.get_summary()

                for it in summary.get("items", []):
                    findings.append(
                        UnifiedFinding(
                            skill=skill_name,
                            rule_id="DEAD_RESOURCE",
                            severity="HIGH" if it.get("confidence") == "High" else "MEDIUM",
                            file_path=it.get("path", ""),
                            line_number=1,
                            message=f"Dead {it.get('type')}: {it.get('reason')}",
                            recommendation="Safely prune or run `scan_codebase_cleanup.py --delete`",
                        )
                    )
                for sym in summary.get("dead_symbols", []):
                    findings.append(
                        UnifiedFinding(
                            skill=skill_name,
                            rule_id="DEAD_SYMBOL",
                            severity="HIGH",
                            file_path=sym.get("file", ""),
                            line_number=sym.get("line", 1),
                            message=f"Unused symbol '{sym.get('symbol')}': {sym.get('reason')}",
                            recommendation="Remove dead internal declaration",
                        )
                    )
                for imp in summary.get("unused_imports", []):
                    findings.append(
                        UnifiedFinding(
                            skill=skill_name,
                            rule_id="UNUSED_IMPORT",
                            severity="LOW",
                            file_path=imp.get("file", ""),
                            line_number=imp.get("line", 1),
                            message=f"Unused framework import: {imp.get('framework')}",
                            recommendation="Remove unused import statement",
                        )
                    )

        except Exception as e:
            print(f"{YELLOW}[Warning] Failed to run skill '{skill_name}': {e}{RESET}", file=sys.stderr)

        return findings


def format_table(auditor: UnifiedAuditor, target_str: str) -> str:
    lines = []
    lines.append(f"\n{BOLD}{CYAN}========================================================================================{RESET}")
    lines.append(f"{BOLD}{CYAN} 🍎 iOS Agent Skills Unified Audit: {target_str}{RESET}")
    lines.append(f"{BOLD}{CYAN}========================================================================================{RESET}\n")

    counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for f in auditor.findings:
        sev = f.severity.upper()
        counts[sev] = counts.get(sev, 0) + 1

    lines.append(
        f"{BOLD}Summary:{RESET} "
        f"{RED}{counts['CRITICAL']} Critical{RESET} | "
        f"{YELLOW}{counts['HIGH']} High{RESET} | "
        f"{CYAN}{counts['MEDIUM']} Medium{RESET} | "
        f"{DIM}{counts['LOW']} Low{RESET} | "
        f"Total: {len(auditor.findings)}"
    )

    perf_parts = [f"{SKILL_DISPLAY_NAMES.get(k, k)}: {v:.1f}ms" for k, v in auditor.execution_times.items()]
    lines.append(f"{DIM}Performance: {' | '.join(perf_parts)}{RESET}\n")

    if not auditor.findings:
        lines.append(f"{GREEN}✅ Clean codebase! No architectural, performance, or accessibility hazards detected.{RESET}\n")
        return "\n".join(lines)

    lines.append(f"{'SEV':<8} {'SKILL':<26} {'RULE':<18} {'LOCATION':<42} {'MESSAGE'}")
    lines.append("-" * 125)

    for f in auditor.findings:
        sev = f.severity.upper()
        sev_color = RED if sev == "CRITICAL" else YELLOW if sev == "HIGH" else CYAN if sev == "MEDIUM" else DIM
        loc = f"{Path(f.file_path).name}:{f.line_number}"
        skill_short = f.skill.replace("ios-", "").replace("-audit", "")
        msg = f.message[:50] + "..." if len(f.message) > 50 else f.message
        lines.append(
            f"{sev_color}{sev:<8}{RESET} {skill_short:<26} {f.rule_id:<18} {loc:<42} {msg}"
        )

    lines.append("")
    return "\n".join(lines)


def format_xcode(auditor: UnifiedAuditor) -> str:
    lines = []
    for f in auditor.findings:
        sev = "error" if f.severity.upper() in ["CRITICAL", "HIGH"] else "warning"
        lines.append(f"{f.file_path}:{f.line_number}:1: {sev}: [{f.skill}] [{f.rule_id}] {f.message}")
    return "\n".join(lines)


def format_markdown(auditor: UnifiedAuditor, target_str: str) -> str:
    counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for f in auditor.findings:
        sev = f.severity.upper()
        counts[sev] = counts.get(sev, 0) + 1

    md = [
        f"# iOS Agent Skills Unified Audit Report",
        "",
        f"- **Target**: `{target_str}`",
        f"- **Skills Evaluated**: {len(auditor.skills)} ({', '.join(auditor.skills)})",
        f"- **Total Findings**: {len(auditor.findings)}",
        "",
        "## Executive Summary",
        "",
        "| Critical | High | Medium | Low |",
        "| :---: | :---: | :---: | :---: |",
        f"| **{counts['CRITICAL']}** | **{counts['HIGH']}** | **{counts['MEDIUM']}** | **{counts['LOW']}** |",
        "",
        "## Detailed Findings",
        "",
        "| Severity | Skill | Rule ID | File:Line | Issue & Recommendation |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ]

    if not auditor.findings:
        md.append("| ✅ **Clean** | All | None | - | No issues detected. |")
        return "\n".join(md)

    for f in auditor.findings:
        sev_badge = "🔴 Critical" if f.severity.upper() == "CRITICAL" else "🟠 High" if f.severity.upper() == "HIGH" else "🟡 Medium" if f.severity.upper() == "MEDIUM" else "🔵 Low"
        loc = f"`{Path(f.file_path).name}:{f.line_number}`"
        md.append(f"| {sev_badge} | `{f.skill}` | `{f.rule_id}` | {loc} | **{f.message}**<br>↳ *Fix*: {f.recommendation} |")

    md.append("")
    return "\n".join(md)


def format_json(auditor: UnifiedAuditor, target_str: str) -> str:
    counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for f in auditor.findings:
        sev = f.severity.upper()
        counts[sev] = counts.get(sev, 0) + 1

    payload = {
        "target": target_str,
        "total_findings": len(auditor.findings),
        "counts": counts,
        "execution_times_ms": auditor.execution_times,
        "skills": auditor.skills,
        "findings": [asdict(f) for f in auditor.findings],
    }
    return json.dumps(payload, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="Unified Multi-Skill iOS & Apple Engineering Auditor"
    )
    parser.add_argument("path", nargs="?", default=".", help="Target Xcode project, Swift package, or folder")
    parser.add_argument(
        "--skills",
        default="all",
        help=f"Comma-separated skills to execute: {','.join(ALL_SKILLS)} or 'all' (default: all)",
    )
    parser.add_argument(
        "--format",
        choices=["table", "text", "xcode", "markdown", "json"],
        default="table",
        help="Report output format (default: table)",
    )
    parser.add_argument(
        "--min-severity",
        choices=["CRITICAL", "HIGH", "MEDIUM", "LOW"],
        default="LOW",
        help="Minimum severity threshold to report (default: LOW)",
    )
    parser.add_argument(
        "--include-tests",
        action="store_true",
        help="Include test directories and test files in audit",
    )
    parser.add_argument(
        "-o", "--output",
        help="Write report output to specified file path",
    )
    parser.add_argument(
        "--no-exit-code",
        action="store_true",
        help="Do not exit with status 1 on critical/high findings",
    )

    args = parser.parse_args()
    target = Path(args.path).resolve()

    if not target.exists():
        print(f"Error: Target path does not exist: {target}", file=sys.stderr)
        sys.exit(1)

    if args.skills == "all":
        selected_skills = list(ALL_SKILLS)
    else:
        selected_skills = [s.strip().lower() for s in args.skills.split(",") if s.strip()]

    auditor = UnifiedAuditor(
        target_path=target,
        skills=selected_skills,
        min_severity=args.min_severity,
        include_tests=args.include_tests,
    )
    findings = auditor.run()

    if args.format in ["table", "text"]:
        out = format_table(auditor, str(target))
    elif args.format == "xcode":
        out = format_xcode(auditor)
    elif args.format == "markdown":
        out = format_markdown(auditor, str(target))
    else:
        out = format_json(auditor, str(target))

    if args.output:
        Path(args.output).write_text(out, encoding="utf-8")
        print(f"Report written to: {args.output}")
    else:
        if out:
            print(out)

    if not args.no_exit_code:
        has_critical_or_high = any(f.severity.upper() in ["CRITICAL", "HIGH"] for f in findings)
        sys.exit(1 if has_critical_or_high else 0)

    sys.exit(0)


if __name__ == "__main__":
    main()
