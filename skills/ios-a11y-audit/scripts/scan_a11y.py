#!/usr/bin/env python3
"""
scan_a11y.py - Zero-dependency iOS & macOS Accessibility Auditor

Scans Swift source files for high-risk accessibility hazards:
- Unlabelled interactive elements and VoiceOver traps
- Dynamic Type fixed-frame text clipping and missing @ScaledMetric
- Sub-44pt tap targets and missing contentShape hit expansion
- Vestibular motion hazards ignoring accessibilityReduceMotion
- Translucent material illegibility without accessibilityReduceTransparency
- Color-only state indicators violating Differentiate Without Color
- Smart Invert media distortion missing accessibilityIgnoresInvertColors
- Missing assistive traits (.isButton, .isHeader, .isSelected)
- Hardcoded non-semantic colors with contrast risk
- Redundant trait verbiage in accessibility labels ("button", "link")
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
MAGENTA = "\033[95m"
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

class AccessibilityScanner:
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

        min_rank = self.severity_order.get(self.min_severity, 1)
        self.findings = [
            f for f in self.findings if self.severity_order.get(f.severity.lower(), 1) >= min_rank
        ]

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

        # Context lookahead and file-level scans
        self._check_unlabelled_icon_buttons(lines, content, file_str)
        self._check_dynamic_type_clipping(lines, content, file_str)
        self._check_sub_44pt_tap_targets(lines, content, file_str)
        self._check_vestibular_motion(lines, content, file_str)
        self._check_translucent_materials(lines, content, file_str)
        self._check_color_only_state(lines, content, file_str)
        self._check_smart_invert_media(lines, content, file_str)
        self._check_missing_traits(lines, content, file_str)
        self._check_hardcoded_colors(lines, content, file_str)
        self._check_redundant_trait_verbiage(lines, content, file_str)
        self._check_unscaled_metrics(lines, content, file_str)

    def _check_unlabelled_icon_buttons(self, lines: List[str], full_text: str, file_str: str):
        """Rule 1: Unlabelled interactive buttons or icons"""
        # SwiftUI: Button with Image(systemName: "...") without .accessibilityLabel
        button_pattern = re.compile(r'Button\s*(?:\([^)]*\))?\s*\{', re.MULTILINE)
        for m in button_pattern.finditer(full_text):
            start_pos = m.start()
            line_no = full_text[:start_pos].count('\n') + 1
            if lines[line_no-1].strip().startswith("//"):
                continue
            window_lines = lines[line_no-1 : min(len(lines), line_no + 12)]
            window_text = "\n".join(window_lines)

            # Check if this button contains an image / symbol
            has_image = bool(re.search(r'Image\s*\(\s*(?:systemName:|"|uiImage:)', window_text))
            has_text_label = bool(re.search(r'\bText\s*\(', window_text))
            has_a11y_label = bool(re.search(r'\.accessibilityLabel\s*\(', window_text))
            has_a11y_element = bool(re.search(r'\.accessibilityElement\s*\(', window_text))

            if has_image and not has_text_label and not has_a11y_label and not has_a11y_element:
                self.findings.append(Finding(
                    severity="Critical",
                    category="VoiceOver & Tree Integrity",
                    rule_id="A11Y-001",
                    file_path=file_str,
                    line_number=line_no,
                    matched_snippet=lines[line_no-1].strip(),
                    description="Interactive Button renders an icon without a visible Text label or an .accessibilityLabel.",
                    remediation="Add .accessibilityLabel(\"Action Name\") to the Button or image to allow VoiceOver navigation."
                ))

        # UIKit: UIButton() created without setTitle or accessibilityLabel
        for i, line in enumerate(lines, 1):
            if line.strip().startswith("//"):
                continue
            if "UIButton" in line and ("UIButton(" in line or "UIButton.init" in line):
                window = "\n".join(lines[i-1:min(len(lines), i+8)])
                if not re.search(r'(\.setTitle|\.accessibilityLabel|\.configuration)', window):
                    self.findings.append(Finding(
                        severity="Critical",
                        category="VoiceOver & Tree Integrity",
                        rule_id="A11Y-002",
                        file_path=file_str,
                        line_number=i,
                        matched_snippet=line.strip(),
                        description="UIButton instantiated without an initial title or accessibilityLabel.",
                        remediation="Configure button.accessibilityLabel = \"Description\" or set a title via UIButton.Configuration."
                    ))

    def _check_dynamic_type_clipping(self, lines: List[str], full_text: str, file_str: str):
        """Rule 2: Fixed-height frames on Text causing Dynamic Type truncation"""
        for i, line in enumerate(lines, 1):
            if line.strip().startswith("//"):
                continue
            # Look for Text("...") followed immediately or next line by .frame(height: 30) or .frame(width: X, height: Y)
            if "Text(" in line:
                window = "\n".join(lines[i-1:min(len(lines), i+4)])
                frame_match = re.search(r'\.frame\s*\([^)]*height:\s*(\d+)[^)]*\)', window)
                if frame_match:
                    height_val = int(frame_match.group(1))
                    if height_val < 80 and not ("minHeight" in window or "idealHeight" in window or "fixedSize" in window):
                        self.findings.append(Finding(
                            severity="Critical",
                            category="Dynamic Type & Scaling",
                            rule_id="A11Y-003",
                            file_path=file_str,
                            line_number=i,
                            matched_snippet=line.strip(),
                            description=f"Fixed height ({height_val}pt) on Text container causes text clipping and truncation under Dynamic Type accessibility sizes.",
                            remediation="Replace rigid .frame(height: N) with .frame(minHeight: N) or allow natural vertical expansion with .fixedSize(horizontal: false, vertical: true)."
                        ))

            # Unbounded body text with strict lineLimit(1) without truncationMode or expansion
            if ".lineLimit(1)" in line:
                prev_line = lines[i-2] if i >= 2 else ""
                if "Text(" in prev_line or "Text(" in line:
                    if not any(k in prev_line + line for k in [".font(.title", ".font(.headline", "caption"]):
                        self.findings.append(Finding(
                            severity="High",
                            category="Dynamic Type & Scaling",
                            rule_id="A11Y-004",
                            file_path=file_str,
                            line_number=i,
                            matched_snippet=line.strip(),
                            description="Strict .lineLimit(1) applied to body text without dynamic adaptation, leading to information loss at AX font sizes.",
                            remediation="Use ViewThatFits, .lineLimit(nil), or adapt line limits dynamically using @Environment(\\.dynamicTypeSize)."
                        ))

    def _check_sub_44pt_tap_targets(self, lines: List[str], full_text: str, file_str: str):
        """Rule 3: Tap target minimums (44x44pt Apple HIG & WCAG 2.5.5)"""
        for i, line in enumerate(lines, 1):
            if line.strip().startswith("//"):
                continue
            if "Button" in line or ".onTapGesture" in line:
                window = "\n".join(lines[i-1:min(len(lines), i+6)])
                dim_match = re.search(r'\.frame\s*\(\s*(?:width:\s*(\d+)\s*,\s*height:\s*(\d+)|height:\s*(\d+)\s*,\s*width:\s*(\d+))\s*\)', window)
                if dim_match:
                    dims = [int(g) for g in dim_match.groups() if g is not None]
                    if len(dims) >= 2:
                        w, h = dims[0], dims[1]
                        if w < 44 or h < 44:
                            has_content_shape = bool(re.search(r'\.contentShape\s*\(', window))
                            has_min_bounds = bool(re.search(r'minWidth:\s*44|minHeight:\s*44', window))
                            if not has_content_shape and not has_min_bounds:
                                severity = "Critical" if (w < 30 or h < 30) else "High"
                                self.findings.append(Finding(
                                    severity=severity,
                                    category="Touch Target & Geometry",
                                    rule_id="A11Y-005",
                                    file_path=file_str,
                                    line_number=i,
                                    matched_snippet=line.strip(),
                                    description=f"Interactive tap target is {w}x{h}pt, violating Apple HIG 44x44pt minimum touch boundary.",
                                    remediation="Expand touch bounding box using .frame(minWidth: 44, minHeight: 44).contentShape(Rectangle()) without altering visual icon frame."
                                ))

    def _check_vestibular_motion(self, lines: List[str], full_text: str, file_str: str):
        """Rule 4: Vestibular motion hazards (animations without accessibilityReduceMotion)"""
        has_reduce_motion_check = "accessibilityReduceMotion" in full_text or "isReduceMotionEnabled" in full_text

        for i, line in enumerate(lines, 1):
            if line.strip().startswith("//"):
                continue
            if ".repeatForever(" in line or ".repeatForever)" in line:
                if not has_reduce_motion_check:
                    self.findings.append(Finding(
                        severity="High",
                        category="Sensory & Motion Adaptations",
                        rule_id="A11Y-006",
                        file_path=file_str,
                        line_number=i,
                        matched_snippet=line.strip(),
                        description="Continuous looping animation (.repeatForever) declared without honoring accessibilityReduceMotion.",
                        remediation="Check @Environment(\\.accessibilityReduceMotion) and disable continuous motion or replace with a static/cross-fade state."
                    ))

    def _check_translucent_materials(self, lines: List[str], full_text: str, file_str: str):
        """Rule 5: Translucent materials without accessibilityReduceTransparency fallback"""
        has_transparency_check = "accessibilityReduceTransparency" in full_text or "isReduceTransparencyEnabled" in full_text

        for i, line in enumerate(lines, 1):
            if line.strip().startswith("//"):
                continue
            if any(mat in line for mat in [".ultraThinMaterial", ".thinMaterial", "UIBlurEffect"]):
                if not has_transparency_check:
                    self.findings.append(Finding(
                        severity="High",
                        category="Sensory & Motion Adaptations",
                        rule_id="A11Y-007",
                        file_path=file_str,
                        line_number=i,
                        matched_snippet=line.strip(),
                        description="Translucent material used as background without fallback for users who enable Reduce Transparency.",
                        remediation="Provide an opaque background fallback when @Environment(\\.accessibilityReduceTransparency) is true."
                    ))

    def _check_color_only_state(self, lines: List[str], full_text: str, file_str: str):
        """Rule 6: State communicated solely through color"""
        has_diff_color_check = "accessibilityDifferentiateWithoutColor" in full_text or "shouldDifferentiateWithoutColor" in full_text

        for i, line in enumerate(lines, 1):
            if line.strip().startswith("//"):
                continue
            # Check status indicators: Circle().fill(.green / .red) without accompanying icon or label
            if "Circle()" in line or "Capsule()" in line:
                window = "\n".join(lines[i-1:min(len(lines), i+6)])
                if any(c in window for c in [".green", ".red", ".orange", "Color.green", "Color.red"]):
                    has_symbol = bool(re.search(r'Image\s*\(\s*systemName:', window))
                    has_label = bool(re.search(r'Text\s*\(|\.accessibilityLabel', window))
                    if not has_symbol and not has_label and not has_diff_color_check:
                        self.findings.append(Finding(
                            severity="High",
                            category="WCAG Color & Contrast",
                            rule_id="A11Y-008",
                            file_path=file_str,
                            line_number=i,
                            matched_snippet=line.strip(),
                            description="Status indicator relies exclusively on color (red/green) without shape differentiation or text label.",
                            remediation="Support Differentiate Without Color by pairing colored circles with distinct icons (e.g., checkmark, xmark) or an explicit status text."
                        ))

    def _check_smart_invert_media(self, lines: List[str], full_text: str, file_str: str):
        """Rule 7: Photo/video content missing accessibilityIgnoresInvertColors"""
        for i, line in enumerate(lines, 1):
            if line.strip().startswith("//"):
                continue
            if "AsyncImage" in line or ("Image(uiImage:" in line and "avatar" in line.lower()):
                window = "\n".join(lines[i-1:min(len(lines), i+18)])
                if not re.search(r'\.accessibilityIgnoresInvertColors\s*\(', window):
                    self.findings.append(Finding(
                        severity="Medium",
                        category="Media & Smart Invert",
                        rule_id="A11Y-009",
                        file_path=file_str,
                        line_number=i,
                        matched_snippet=line.strip(),
                        description="Photo or media component missing .accessibilityIgnoresInvertColors(true), causing photo reversal under Smart Invert.",
                        remediation="Add .accessibilityIgnoresInvertColors(true) to ensure media renders naturally when Smart Invert is active."
                    ))

    def _check_missing_traits(self, lines: List[str], full_text: str, file_str: str):
        """Rule 8: Interactive custom components missing assistive traits"""
        for i, line in enumerate(lines, 1):
            if line.strip().startswith("//"):
                continue
            if ".onTapGesture" in line:
                window = "\n".join(lines[max(0, i-4):min(len(lines), i+6)])
                has_traits = bool(re.search(r'\.accessibilityAddTraits\s*\(|\.accessibilityTraits', window))
                has_button_role = bool(re.search(r'role:\s*\.button|\.isButton', window))
                if not has_traits and not has_button_role:
                    self.findings.append(Finding(
                        severity="High",
                        category="Assistive Traits & Roles",
                        rule_id="A11Y-010",
                        file_path=file_str,
                        line_number=i,
                        matched_snippet=line.strip(),
                        description="Custom view uses .onTapGesture but does not register .accessibilityAddTraits(.isButton).",
                        remediation="Attach .accessibilityAddTraits(.isButton) so VoiceOver identifies the element as an interactive control."
                    ))

    def _check_hardcoded_colors(self, lines: List[str], full_text: str, file_str: str):
        """Rule 9: Hardcoded RGB/Hex colors skipping semantic tokens"""
        for i, line in enumerate(lines, 1):
            if line.strip().startswith("//"):
                continue
            if any(kw in line for kw in ["Color(red:", "UIColor(red:", "Color(hex:", "UIColor(hex:"]):
                if not any(f in file_str.lower() for f in ["color+", "palette", "assets", "theme"]):
                    self.findings.append(Finding(
                        severity="Medium",
                        category="WCAG Color & Contrast",
                        rule_id="A11Y-011",
                        file_path=file_str,
                        line_number=i,
                        matched_snippet=line.strip(),
                        description="Hardcoded RGB/Hex color used inline; may fail WCAG contrast ratios in Dark Mode or High Contrast mode.",
                        remediation="Use semantic dynamic colors (Color(uiColor: .label), .secondary) or named asset catalog colors with Light/Dark contrast variants."
                    ))

    def _check_redundant_trait_verbiage(self, lines: List[str], full_text: str, file_str: str):
        """Rule 10: Redundant words in accessibility labels"""
        for i, line in enumerate(lines, 1):
            if line.strip().startswith("//"):
                continue
            match = re.search(r'\.accessibilityLabel\s*\(\s*"([^"]+)"\s*\)', line)
            if match:
                label_val = match.group(1).lower()
                for bad_word in [" button", " link", " image", " heading"]:
                    if label_val.endswith(bad_word) or label_val == bad_word.strip():
                        self.findings.append(Finding(
                            severity="Low",
                            category="VoiceOver & Tree Integrity",
                            rule_id="A11Y-012",
                            file_path=file_str,
                            line_number=i,
                            matched_snippet=line.strip(),
                            description=f"Accessibility label contains redundant trait word '{bad_word.strip()}'; VoiceOver will announce this trait automatically.",
                            remediation=f"Remove '{bad_word.strip()}' from the label text (e.g., change \"Close button\" to \"Close\")."
                        ))

    def _check_unscaled_metrics(self, lines: List[str], full_text: str, file_str: str):
        """Rule 11: Custom geometry or icon sizes in Views missing @ScaledMetric"""
        in_view_struct = False

        for i, line in enumerate(lines, 1):
            if line.strip().startswith("//"):
                continue
            if re.search(r'struct\s+\w+\s*:\s*View\b', line):
                in_view_struct = True
            elif line.startswith("}") and in_view_struct:
                pass

            # Detect: private let iconSize: CGFloat = 24 without @ScaledMetric on current or preceding line
            if in_view_struct and re.search(r'(?:(?:private|fileprivate|public|internal)\s+)?(?:let|var)\s+(?:iconSize|avatarSize|spacing|margin|padding|badgeSize)\s*:\s*CGFloat\s*=\s*\d+', line):
                prev_line = lines[i-2] if i >= 2 else ""
                has_metric_on_prop = "@ScaledMetric" in prev_line or "@ScaledMetric" in line
                if not has_metric_on_prop:
                    self.findings.append(Finding(
                        severity="Medium",
                        category="Dynamic Type & Scaling",
                        rule_id="A11Y-013",
                        file_path=file_str,
                        line_number=i,
                        matched_snippet=line.strip(),
                        description="Custom icon or layout dimension declared as fixed CGFloat without @ScaledMetric.",
                        remediation="Annotate custom dimensional properties with @ScaledMetric to allow proportional scaling under Dynamic Type."
                    ))

# Output Formatters
def format_text(scanner: AccessibilityScanner, findings: List[Finding], duration: float) -> str:
    lines = []
    lines.append(f"{BOLD}{CYAN}╔══════════════════════════════════════════════════════════════════════════════════╗{RESET}")
    lines.append(f"{BOLD}{CYAN}║                     iOS Accessibility Audit (scan_a11y.py)                       ║{RESET}")
    lines.append(f"{BOLD}{CYAN}╚══════════════════════════════════════════════════════════════════════════════════╝{RESET}")
    lines.append("")
    lines.append(f"  {BOLD}Files Scanned:{RESET} {scanner.files_scanned}  |  {BOLD}Lines:{RESET} {scanner.lines_scanned}  |  {BOLD}Duration:{RESET} {duration:.2f}s")
    lines.append("")

    counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1

    lines.append(f"  {RED}● Critical: {counts['Critical']}{RESET}   "
                 f"{YELLOW}▲ High: {counts['High']}{RESET}   "
                 f"{CYAN}■ Medium: {counts['Medium']}{RESET}   "
                 f"{DIM}○ Low: {counts['Low']}{RESET}")
    lines.append("")

    if not findings:
        lines.append(f"  {GREEN}{BOLD}✓ No accessibility violations detected! Codebase meets baseline criteria.{RESET}\n")
        return "\n".join(lines)

    for idx, f in enumerate(findings, 1):
        color = RED if f.severity == "Critical" else YELLOW if f.severity == "High" else CYAN if f.severity == "Medium" else DIM
        icon = "●" if f.severity == "Critical" else "▲" if f.severity == "High" else "■" if f.severity == "Medium" else "○"
        
        lines.append(f"  {color}{BOLD}{icon} [{f.severity.upper()}] {f.rule_id}: {f.category}{RESET}")
        lines.append(f"     {BOLD}File:{RESET} {f.file_path}:{f.line_number}")
        lines.append(f"     {BOLD}Problem:{RESET} {f.description}")
        lines.append(f"     {DIM}Snippet: {f.matched_snippet}{RESET}")
        lines.append(f"     {GREEN}Fix:{RESET} {f.remediation}")
        lines.append("")

    return "\n".join(lines)

def format_markdown(scanner: AccessibilityScanner, findings: List[Finding], duration: float) -> str:
    md = []
    md.append("# iOS Accessibility Audit Report\n")
    md.append(f"- **Files Scanned:** `{scanner.files_scanned}`")
    md.append(f"- **Total Lines:** `{scanner.lines_scanned}`")
    md.append(f"- **Execution Time:** `{duration:.2f}s`\n")

    counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1

    md.append("## Summary\n")
    md.append("| Severity | Count | Impact |")
    md.append("| :--- | :--- | :--- |")
    md.append(f"| 🔴 Critical | {counts['Critical']} | Screen reader blocker or text clipping at AX font sizes |")
    md.append(f"| 🟠 High | {counts['High']} | Missing assistive traits, sub-44pt targets, vestibular motion |")
    md.append(f"| 🟡 Medium | {counts['Medium']} | Missing @ScaledMetric, Smart Invert distortion, hardcoded colors |")
    md.append(f"| 🔵 Low | {counts['Low']} | Label verbiage hygiene and minor reading order polish |")
    md.append("\n---\n")

    md.append("## Detailed Findings\n")
    if not findings:
        md.append("✓ *No accessibility violations found.*")
        return "\n".join(md)

    for f in findings:
        badge = "🔴" if f.severity == "Critical" else "🟠" if f.severity == "High" else "🟡" if f.severity == "Medium" else "🔵"
        md.append(f"### {badge} [{f.rule_id}] {f.description}\n")
        md.append(f"- **Category:** {f.category}")
        md.append(f"- **Location:** `{f.file_path}:{f.line_number}`")
        md.append(f"- **Snippet:** `{f.matched_snippet}`")
        md.append(f"- **Remediation:** {f.remediation}\n")

    return "\n".join(md)

def format_json(scanner: AccessibilityScanner, findings: List[Finding], duration: float) -> str:
    data = {
        "metadata": {
            "files_scanned": scanner.files_scanned,
            "lines_scanned": scanner.lines_scanned,
            "duration_seconds": round(duration, 3),
            "findings_count": len(findings)
        },
        "findings": [asdict(f) for f in findings]
    }
    return json.dumps(data, indent=2)

def main():
    parser = argparse.ArgumentParser(description="Zero-dependency iOS & macOS Accessibility Auditor")
    parser.add_argument("target", help="Target Swift file or Xcode project directory")
    parser.add_argument("--min-severity", choices=["critical", "high", "medium", "low"], default="low",
                        help="Filter minimum reported severity tier")
    parser.add_argument("--format", choices=["text", "markdown", "json"], default="text",
                        help="Output format (text, markdown, json)")
    parser.add_argument("-o", "--output", help="Write report to output file")

    args = parser.parse_args()

    scanner = AccessibilityScanner(args.target, min_severity=args.min_severity)
    start_time = time.time()
    findings = scanner.scan()
    duration = time.time() - start_time

    if args.format == "text":
        result = format_text(scanner, findings, duration)
    elif args.format == "markdown":
        result = format_markdown(scanner, findings, duration)
    else:
        result = format_json(scanner, findings, duration)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"Report saved to {args.output}")
    else:
        print(result)

    # Return non-zero if critical findings exist
    has_critical = any(f.severity == "Critical" for f in findings)
    sys.exit(1 if has_critical else 0)

if __name__ == "__main__":
    main()
