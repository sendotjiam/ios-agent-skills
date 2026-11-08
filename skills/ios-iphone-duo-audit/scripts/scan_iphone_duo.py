#!/usr/bin/env python3
"""
scan_iphone_duo.py - iPhone Duo Dual-Display, Fold & Vertical Bar Fast-Scanner

Audits iOS/iPadOS projects against Apple's "Designing for iPhone Duo" HIG and iOS 27.1+ APIs:
  1. Hardcoded screen bounds (`UIScreen.main.bounds` / `nativeBounds`) breaking across dual displays & poses
  2. Invalid `ArrangementView` nesting (inside `ScrollView`/`List`, or wrapping `NavigationSplitView`/`TabView`)
  3. Layout branching on `UIDevice.current.userInterfaceIdiom` or `UIInterfaceOrientation` instead of size classes
  4. Text-only `ToolbarItem` buttons that cannot render on iPhone Duo's vertical side bar
  5. Standalone `UIToolbar()`, `UINavigationBar()`, or `UITabBar()` subviews bypassing system vertical bar adaptation
  6. Hardcoded wide `.frame(width: >= 320)` overflowing compact outer displays and Split View panes
  7. Odd-column `LazyVGrid` (e.g., 3 flexible columns) straddling the center hinge `.division` reserved region
  8. Manual toolbar spacers (`Spacer(minLength:)`) or custom `"ellipsis"` buttons instead of `ToolbarItemGroup` / `ToolbarOverflowMenu`
"""

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Optional

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


class IPhoneDuoScanner:
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
        base_ignores = [
            "Pods",
            "DerivedData",
            ".build",
            ".swiftpm",
            "Carthage",
            ".git",
            "golden_fixes",
        ]
        if not include_tests:
            base_ignores.extend(
                [
                    "Tests",
                    "UITests",
                    "UnitTests",
                    "IntegrationTests",
                    "Mocks",
                    "Fixtures",
                    "TestHelpers",
                ]
            )
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
            if (
                name.endswith("Tests.swift")
                or name.endswith("Test.swift")
                or name.endswith("Mock.swift")
                or name.endswith("Fixture.swift")
            ):
                return True
        return False

    def is_rule_suppressed(
        self, line: str, prev_line: Optional[str], rule_id: str
    ) -> bool:
        if "//" in line:
            same_line_pat = re.compile(
                r"//\s*(?:ios-audit|swift-audit)\s*:\s*ignore\s+([\w\-, ]+)",
                re.IGNORECASE,
            )
            m = same_line_pat.search(line)
            if m:
                ignored = [r.strip().upper() for r in m.group(1).split(",")]
                if "ALL" in ignored or rule_id.upper() in ignored:
                    return True
            if re.search(
                r"//\s*(?:ios-audit|swift-audit)\s*:\s*ignore-all\b",
                line,
                re.IGNORECASE,
            ):
                return True

        if prev_line and "//" in prev_line:
            next_line_pat = re.compile(
                r"//\s*(?:ios-audit|swift-audit)\s*:\s*(?:ignore-next-line|disable-next-line)\s+([\w\-, ]+)",
                re.IGNORECASE,
            )
            m_next = next_line_pat.search(prev_line)
            if m_next:
                ignored = [r.strip().upper() for r in m_next.group(1).split(",")]
                if "ALL" in ignored or rule_id.upper() in ignored:
                    return True
            if re.search(
                r"//\s*(?:ios-audit|swift-audit)\s*:\s*(?:ignore-next-line-all|disable-next-line-all)\b",
                prev_line,
                re.IGNORECASE,
            ):
                return True

        return False

    def scan(self) -> List[Finding]:
        swift_files: List[Path] = []

        if self.target_path.is_file():
            if self.target_path.suffix == ".swift":
                swift_files.append(self.target_path)
        else:
            for root, dirs, files in os.walk(self.target_path):
                dirs[:] = [
                    d
                    for d in dirs
                    if not any(ign in d for ign in self.ignore_patterns)
                ]
                for file in files:
                    full_p = Path(root) / file
                    if self.should_ignore(full_p):
                        continue
                    if file.endswith(".swift"):
                        swift_files.append(full_p)

        self.files_scanned = len(swift_files)

        for s_file in swift_files:
            self._scan_swift_file(s_file)

        min_rank = self.severity_order.get(self.min_severity, 1)
        self.findings = [
            f
            for f in self.findings
            if self.severity_order.get(f.severity.lower(), 1) >= min_rank
        ]
        self.findings.sort(
            key=lambda x: (
                -self.severity_order.get(x.severity.lower(), 1),
                x.file_path,
                x.line_number,
            )
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

        in_scroll_or_list = False
        scroll_depth = 0

        in_arrangement = False
        arrangement_depth = 0

        in_toolbar = False
        toolbar_depth = 0

        in_toolbar_item = False
        toolbar_item_depth = 0
        toolbar_item_start_line = 0
        toolbar_item_has_icon = False
        toolbar_item_text_btn_line = 0
        toolbar_item_text_btn_snippet = ""

        # Track odd-column GridItem definitions in file
        odd_grid_vars = set()
        for idx, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("//"):
                continue
            grid_items = re.findall(r"GridItem\s*\(\s*\.flexible", line)
            if len(grid_items) >= 3 and len(grid_items) % 2 == 1:
                m_var = re.search(r"(?:let|var)\s+([a-zA-Z0-9_]+)\s*=", line)
                if m_var:
                    odd_grid_vars.add(m_var.group(1))

        for idx, line in enumerate(lines):
            stripped = line.strip()
            if (
                stripped.startswith("//")
                or stripped.startswith("/*")
                or stripped.startswith("*")
            ):
                continue

            prev_line = lines[idx - 1] if idx > 0 else ""
            brace_delta = line.count("{") - line.count("}")

            # Scope 1: ScrollView or List container tracking
            if re.search(r"\b(?:ScrollView|List)\b[^{]*\{", line) and not in_scroll_or_list:
                in_scroll_or_list = True
                scroll_depth = brace_delta
            elif in_scroll_or_list:
                scroll_depth += brace_delta
                if scroll_depth <= 0:
                    in_scroll_or_list = False

            # Scope 2: ArrangementView tracking & invalid nesting check
            if re.search(r"\bArrangementView\b[^{]*\{", line):
                if in_scroll_or_list:
                    rule_id = "DUO_ARRANGEMENT_INVALID_NESTING"
                    if not self.is_rule_suppressed(line, prev_line, rule_id):
                        self.findings.append(
                            Finding(
                                severity="Critical",
                                category="Invalid ArrangementView Container Nesting",
                                rule_id=rule_id,
                                file_path=file_str,
                                line_number=idx + 1,
                                matched_snippet=stripped,
                                description="ArrangementView is nested inside a ScrollView or List, breaking iPhone Duo fold division geometry.",
                                remediation="Place ArrangementView at the root content level outside ScrollView/List, and make individual primary/secondary views scrollable if needed.",
                            )
                        )
                if not in_arrangement:
                    in_arrangement = True
                    arrangement_depth = brace_delta
            elif in_arrangement:
                if re.search(r"\b(?:NavigationSplitView|TabView)\b[^{]*\{", line):
                    rule_id = "DUO_ARRANGEMENT_INVALID_NESTING"
                    if not self.is_rule_suppressed(line, prev_line, rule_id):
                        self.findings.append(
                            Finding(
                                severity="Critical",
                                category="Navigation Container Inside ArrangementView",
                                rule_id=rule_id,
                                file_path=file_str,
                                line_number=idx + 1,
                                matched_snippet=stripped,
                                description="NavigationSplitView or TabView is nested inside an ArrangementView. ArrangementView lays out content but does not manage navigation.",
                                remediation="Move NavigationSplitView or TabView outside of the ArrangementView hierarchy.",
                            )
                        )
                arrangement_depth += brace_delta
                if arrangement_depth <= 0:
                    in_arrangement = False

            # Scope 3: .toolbar { ... } and ToolbarItem { ... } tracking
            if re.search(r"\.toolbar\s*\{", line) and not in_toolbar:
                in_toolbar = True
                toolbar_depth = brace_delta
            elif in_toolbar:
                toolbar_depth += brace_delta
                if toolbar_depth <= 0:
                    in_toolbar = False

            if in_toolbar and re.search(r"\bToolbarItem(?:Group)?\b[^{]*\{", line) and not in_toolbar_item:
                in_toolbar_item = True
                toolbar_item_depth = brace_delta
                toolbar_item_start_line = idx + 1
                toolbar_item_has_icon = bool(
                    re.search(r"\b(?:Label|Image|systemImage|systemName)\b", line)
                )
                toolbar_item_text_btn_line = 0
                toolbar_item_text_btn_snippet = ""
            elif in_toolbar_item:
                if re.search(r"\b(?:Label|Image|systemImage|systemName)\b", line):
                    toolbar_item_has_icon = True
                if re.search(r'\bButton\s*\(\s*"[^"]+"\s*\)', line) and not re.search(
                    r"systemImage\s*:", line
                ):
                    toolbar_item_text_btn_line = idx + 1
                    toolbar_item_text_btn_snippet = stripped

                toolbar_item_depth += brace_delta
                if toolbar_item_depth <= 0:
                    if toolbar_item_text_btn_line > 0 and not toolbar_item_has_icon:
                        rule_id = "DUO_TOOLBAR_TEXT_ONLY_ITEM"
                        btn_line_str = lines[toolbar_item_text_btn_line - 1]
                        btn_prev_str = (
                            lines[toolbar_item_text_btn_line - 2]
                            if toolbar_item_text_btn_line >= 2
                            else ""
                        )
                        if not self.is_rule_suppressed(
                            btn_line_str, btn_prev_str, rule_id
                        ):
                            self.findings.append(
                                Finding(
                                    severity="High",
                                    category="Text-Only Toolbar Item on Vertical Bar",
                                    rule_id=rule_id,
                                    file_path=file_str,
                                    line_number=toolbar_item_text_btn_line,
                                    matched_snippet=toolbar_item_text_btn_snippet,
                                    description="ToolbarItem uses a text-only Button without an icon. On iPhone Duo, items without an icon cannot be presented on the vertical side bar.",
                                    remediation='Provide both a title and a symbol using Button("Title", systemImage: "...") or Label("Title", systemImage: "...").',
                                )
                            )
                    in_toolbar_item = False

            # Rule 1: Hardcoded UIScreen.main.bounds / nativeBounds
            if re.search(r"\bUIScreen\.main\.(?:bounds|nativeBounds)\b", line):
                rule_id = "DUO_SCREEN_BOUNDS_HARDCODED"
                if not self.is_rule_suppressed(line, prev_line, rule_id):
                    self.findings.append(
                        Finding(
                            severity="Critical",
                            category="Hardcoded UIScreen Bounds",
                            rule_id=rule_id,
                            file_path=file_str,
                            line_number=idx + 1,
                            matched_snippet=stripped,
                            description="UIScreen.main.bounds assumes a static single screen and breaks when iPhone Duo transitions between outer/inner displays, Split View, or folded poses.",
                            remediation="Size views relative to their container or scene bounds using GeometryReader, containerRelativeFrame, or view.bounds/safeAreaLayoutGuide.",
                        )
                    )

            # Rule 3: Idiom or device orientation layout branching
            if re.search(
                r"\b(?:UIDevice\.current\.(?:userInterfaceIdiom|orientation)|UIInterfaceOrientation(?:IsLandscape|IsPortrait)?)\b",
                line,
            ):
                rule_id = "DUO_IDIOM_OR_ORIENTATION_LAYOUT"
                if not self.is_rule_suppressed(line, prev_line, rule_id):
                    self.findings.append(
                        Finding(
                            severity="High",
                            category="Idiom or Orientation Layout Branching",
                            rule_id=rule_id,
                            file_path=file_str,
                            line_number=idx + 1,
                            matched_snippet=stripped,
                            description="Using UIDevice.userInterfaceIdiom or device orientation for layout decisions fails on iPhone Duo where a `.phone` idiom spans both compact outer and regular inner displays across 6 poses.",
                            remediation="Adapt layouts using horizontalSizeClass / verticalSizeClass, ArrangementView, and GeometryProxy.reservedRegions(kind:).",
                        )
                    )

            # Rule 5: Standalone UIToolbar, UINavigationBar, or UITabBar instantiation
            if re.search(
                r"=\s*(?:UIToolbar|UINavigationBar|UITabBar)\s*\(", line
            ):
                rule_id = "DUO_CUSTOM_BAR_BYPASS"
                if not self.is_rule_suppressed(line, prev_line, rule_id):
                    self.findings.append(
                        Finding(
                            severity="High",
                            category="Standalone UIKit Bar Bypassing Vertical Axis",
                            rule_id=rule_id,
                            file_path=file_str,
                            line_number=idx + 1,
                            matched_snippet=stripped,
                            description="Manually instantiating a standalone UIToolbar, UINavigationBar, or UITabBar prevents iOS from automatically presenting bars vertically on the side of iPhone Duo.",
                            remediation="Configure navigationItem / toolbarItems on view controllers inside a UINavigationController or UITabBarController.",
                        )
                    )

            # Rule 6: Hardcoded wide .frame(width: >= 320)
            m_width = re.search(r"\.frame\s*\(\s*width\s*:\s*([0-9]+(?:\.[0-9]+)?)", line)
            if m_width:
                width_val = float(m_width.group(1))
                if width_val >= 320:
                    rule_id = "DUO_FIXED_FRAME_WIDTH"
                    if not self.is_rule_suppressed(line, prev_line, rule_id):
                        self.findings.append(
                            Finding(
                                severity="Medium",
                                category="Fixed Wide Frame Width",
                                rule_id=rule_id,
                                file_path=file_str,
                                line_number=idx + 1,
                                matched_snippet=stripped,
                                description=f"Fixed .frame(width: {m_width.group(1)}) prevents dynamic resizing across iPhone Duo outer display, Split View multitasking, and vertical side-bar insets.",
                                remediation="Use flexible `.frame(maxWidth: .infinity)`, layout margins, or `containerRelativeFrame` instead of fixed pixel widths.",
                            )
                        )

            # Rule 7: Odd-column LazyVGrid across fold division
            if "LazyVGrid" in line:
                inline_items = re.findall(r"GridItem\s*\(\s*\.flexible", line)
                uses_odd_var = any(
                    re.search(rf"columns\s*:\s*{re.escape(v)}\b", line)
                    for v in odd_grid_vars
                )
                if (len(inline_items) >= 3 and len(inline_items) % 2 == 1) or uses_odd_var:
                    rule_id = "DUO_ODD_GRID_COLUMNS_ON_FOLD"
                    if not self.is_rule_suppressed(line, prev_line, rule_id):
                        self.findings.append(
                            Finding(
                                severity="Medium",
                                category="Odd Grid Columns Straddling Hinge Fold",
                                rule_id=rule_id,
                                file_path=file_str,
                                line_number=idx + 1,
                                matched_snippet=stripped,
                                description="LazyVGrid uses an odd number of flexible columns (e.g., 3), causing the center column to straddle the iPhone Duo hinge `.division` reserved region when partially folded.",
                                remediation="Prefer an even number of columns on the inner display or adjust column counts around `proxy.reservedRegions(kind: .division)`.",
                            )
                        )

            # Rule 8: Manual toolbar spacer or custom ellipsis button in toolbar
            if in_toolbar:
                if re.search(r"\bSpacer\s*\(\s*minLength\s*:", line):
                    rule_id = "DUO_MANUAL_TOOLBAR_SPACER"
                    if not self.is_rule_suppressed(line, prev_line, rule_id):
                        self.findings.append(
                            Finding(
                                severity="Low",
                                category="Manual Fixed Spacing in Toolbar",
                                rule_id=rule_id,
                                file_path=file_str,
                                line_number=idx + 1,
                                matched_snippet=stripped,
                                description="Manual fixed Spacer(minLength:) in a toolbar disrupts automatic vertical bar grouping and overflow compression on iPhone Duo.",
                                remediation="Group related items using ToolbarItemGroup (SwiftUI) or UIBarButtonItemGroup (UIKit) so the system spaces groups automatically on both horizontal and vertical axes.",
                            )
                        )
                elif re.search(
                    r'(?:systemName|systemImage)\s*:\s*"ellipsis(?:\.circle)?"', line
                ):
                    rule_id = "DUO_MANUAL_TOOLBAR_SPACER"
                    if not self.is_rule_suppressed(line, prev_line, rule_id):
                        self.findings.append(
                            Finding(
                                severity="Low",
                                category="Custom Ellipsis Overflow Button in Toolbar",
                                rule_id=rule_id,
                                file_path=file_str,
                                line_number=idx + 1,
                                matched_snippet=stripped,
                                description="Custom ellipsis toolbar button competes with the system overflow menu on iPhone Duo vertical bars.",
                                remediation="Move overflow actions into the system overflow menu using `ToolbarOverflowMenu` (SwiftUI) or `navigationItem.additionalOverflowItems` (UIKit).",
                            )
                        )


def format_table(scanner: IPhoneDuoScanner) -> str:
    lines = []
    lines.append(
        f"\n{BOLD}{CYAN}=== iPhone Duo Dual-Display, Fold & Vertical Bar Audit ==={RESET}"
    )
    lines.append(
        f"Scanned {scanner.files_scanned} files ({scanner.lines_scanned} lines)\n"
    )

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
        lines.append(
            f"{GREEN}✅ No iPhone Duo layout, reserved-region, or vertical-bar hazards detected.{RESET}\n"
        )
        return "\n".join(lines)

    lines.append(f"{'SEV':<10} {'RULE ID':<34} {'LOCATION':<36} {'CATEGORY'}")
    lines.append("-" * 100)

    for f in scanner.findings:
        color = (
            RED
            if f.severity == "Critical"
            else YELLOW
            if f.severity == "High"
            else CYAN
            if f.severity == "Medium"
            else DIM
        )
        loc = f"{Path(f.file_path).name}:{f.line_number}"
        lines.append(
            f"{color}{f.severity:<10}{RESET} {f.rule_id:<34} {loc:<36} {f.category}"
        )
        lines.append(f"  {DIM}Snippet:{RESET} {f.matched_snippet}")
        lines.append(f"  {DIM}Fix:{RESET} {f.remediation}\n")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="iPhone Duo Dual-Display, Fold & Vertical Bar Fast-Scanner"
    )
    parser.add_argument(
        "path", nargs="?", default=".", help="Target Xcode project or Swift file"
    )
    parser.add_argument(
        "--format",
        choices=["table", "json", "markdown", "xcode"],
        default="table",
    )
    parser.add_argument(
        "--min-severity",
        choices=["critical", "high", "medium", "low"],
        default="low",
    )
    parser.add_argument(
        "--include-tests", action="store_true", help="Include test files in audit"
    )
    parser.add_argument("-o", "--output", help="Write report to file")

    args = parser.parse_args()
    scanner = IPhoneDuoScanner(
        args.path,
        min_severity=args.min_severity,
        include_tests=args.include_tests,
    )
    findings = scanner.scan()

    if args.format == "table":
        out = format_table(scanner)
    elif args.format == "xcode":
        out = "\n".join(
            [
                f"{f.file_path}:{f.line_number}:1: {'error' if f.severity in ['Critical', 'High'] else 'warning'}: [ios-iphone-duo-audit] [{f.rule_id}] {f.description}"
                for f in findings
            ]
        )
    elif args.format == "markdown":
        out = f"# iPhone Duo Adaptability Audit Report\n\nTotal findings: {len(findings)}\n"
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
