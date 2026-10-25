#!/usr/bin/env python3
"""
SwiftUI Render & Performance Fast-Scanner
Zero-dependency static analysis tool to detect SwiftUI render bottlenecks,
identity churn, over-invalidation, heavy body computations, and lifecycle hazards.
"""

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

@dataclass
class Finding:
    rule_id: str
    severity: str
    title: str
    file_path: str
    line_number: int
    snippet: str
    recommendation: str

RULES = [
    {
        "id": "CRIT_VM_INIT",
        "severity": "critical",
        "title": "@ObservedObject initialized inline",
        "description": "Initializing @ObservedObject directly (= ViewModel()) recreates the instance on every parent body evaluation.",
        "recommendation": "Use @StateObject for ownership in iOS 14-16, or @State with @Observable in iOS 17+.",
    },
    {
        "id": "CRIT_STATE_INIT",
        "severity": "critical",
        "title": "@State initialized in init() from parameters",
        "description": "Setting _state = State(initialValue:) in init() only runs once; subsequent parent updates pass stale values.",
        "recommendation": "Use @Binding, derived computed state, or .onChange(of:) synchronization.",
    },
    {
        "id": "CRIT_TRANSIENT_ID",
        "severity": "critical",
        "title": "Transient or volatile ID in view identity",
        "description": "Using UUID() or random values in .id() or ForEach destroys view state and forces full re-render every frame.",
        "recommendation": "Use persistent model identifiers conforming to Identifiable with stable IDs.",
    },
    {
        "id": "HIGH_ANYVIEW",
        "severity": "high",
        "title": "AnyView type erasure",
        "description": "AnyView destroys compile-time structural type hierarchy, bypassing SwiftUI view diffing optimizations.",
        "recommendation": "Replace with @ViewBuilder, Group, or native enum/conditional branching.",
    },
    {
        "id": "HIGH_BODY_COMPUTE",
        "severity": "high",
        "title": "Heavy computation / allocation in body",
        "description": "Instantiating formatters, decoders, or sorting/filtering arrays inside body stalls main-thread rendering.",
        "recommendation": "Precompute in ViewModel or use memoized/cached properties outside body.",
    },
    {
        "id": "HIGH_SHEET_IN_LOOP",
        "severity": "high",
        "title": "Presentation modifier inside ForEach loop",
        "description": "Placing .sheet, .fullScreenCover, or .popover inside ForEach creates N presentation coordinator bindings.",
        "recommendation": "Hoist presentation modifiers to the parent collection view with a single binding or item.",
    },
    {
        "id": "HIGH_ONAPPEAR_TASK",
        "severity": "high",
        "title": "Unstructured Task in .onAppear",
        "description": "Spawning Task { ... } inside .onAppear does not automatically cancel when view disappears.",
        "recommendation": "Use the native .task modifier or .task(id:) for lifecycle-bound cooperative cancellation.",
    },
    {
        "id": "MED_EAGER_SCROLL",
        "severity": "medium",
        "title": "Eager stack inside ScrollView",
        "description": "Using VStack/HStack inside ScrollView with dynamic collections instantiates all child views immediately.",
        "recommendation": "Replace with LazyVStack, LazyHStack, or List for cell recycling.",
    },
    {
        "id": "MED_UNSCOPED_ANIMATION",
        "severity": "medium",
        "title": "Unscoped implicit .animation() modifier",
        "description": "Calling .animation(...) without a 'value:' parameter animates all state changes across the subtree.",
        "recommendation": "Use .animation(.spring, value: targetState) or withAnimation block.",
    },
    {
        "id": "MED_GEOMETRY_READER",
        "severity": "medium",
        "title": "GeometryReader inside list or lazy collection",
        "description": "GeometryReader inside scrollable cells triggers multi-pass layout renegotiation during scrolling.",
        "recommendation": "Use preference keys, containerRelativeFrame, or .onGeometryChange (iOS 16+) instead.",
    },
    {
        "id": "HIGH_INIT_SIDE_EFFECT",
        "severity": "high",
        "title": "Side effect / logging in view init()",
        "description": "View init() executes on every parent body evaluation; placing analytics or side effects in init() causes repeated execution.",
        "recommendation": "Move analytics and side effects to .task or .onAppear.",
    },
    {
        "id": "MED_OBSERVATION_IGNORED",
        "severity": "medium",
        "title": "Non-UI property in @Observable missing @ObservationIgnored",
        "description": "Timers, tasks, or network tokens in @Observable classes trigger view body invalidations unless ignored.",
        "recommendation": "Add @ObservationIgnored to non-UI coordination properties.",
    },
    {
        "id": "LOW_PRINT_CHANGES",
        "severity": "low",
        "title": "Diagnostic _printChanges() call in production code",
        "description": "Self._printChanges() generates console logging overhead and should be removed before release.",
        "recommendation": "Strip _printChanges() calls or wrap inside #if DEBUG.",
    },
]

RULE_LOOKUP = {r["id"]: r for r in RULES}

IGNORED_DIRS = {
    ".git", ".build", "Pods", "DerivedData", "Carthage", ".swiftpm",
    ".idea", ".vscode", "xcuserdata", "Tests", "UITests"
}

def is_ignored(path: Path) -> bool:
    for part in path.parts:
        if part in IGNORED_DIRS:
            return True
    return False

def extract_balanced_block(content: str, open_brace_idx: int) -> Optional[Tuple[int, str]]:
    """Returns (end_index, inner_content) for a block starting with '{' at open_brace_idx."""
    if open_brace_idx >= len(content) or content[open_brace_idx] != '{':
        return None
    brace_count = 0
    start = open_brace_idx + 1
    for i in range(open_brace_idx, len(content)):
        char = content[i]
        if char == '{':
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0:
                return (i + 1, content[start:i])
    return None

def find_body_blocks(content: str) -> List[Tuple[int, int, str]]:
    """Extract (start_line, end_line, body_content) for var body: some View."""
    body_blocks = []
    body_pattern = re.compile(r'\bvar\s+body\s*:\s*some\s+View\b[^{]*\{')
    for m in body_pattern.finditer(content):
        brace_pos = m.end() - 1
        res = extract_balanced_block(content, brace_pos)
        if res:
            end_pos, inner = res
            start_line = content[:m.start()].count('\n') + 1
            end_line = content[:end_pos].count('\n') + 1
            body_blocks.append((start_line, end_line, inner))
    return body_blocks

def scan_file(file_path: Path) -> List[Finding]:
    findings: List[Finding] = []
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return findings

    lines = content.splitlines()
    rel_path = str(file_path)

    lines = content.splitlines()
    rel_path = str(file_path)

    # 1. Line-by-line single regex checks
    for idx, line in enumerate(lines):
        line_num = idx + 1
        stripped = line.strip()

        # Skip comment lines
        if stripped.startswith("//") or stripped.startswith("/*"):
            continue

        # CRIT_VM_INIT: @ObservedObject var vm = ViewModel()
        if re.search(r'@ObservedObject\s+(?:private\s+)?var\s+\w+\s*=\s*[A-Z]\w*\(', stripped):
            findings.append(Finding(
                rule_id="CRIT_VM_INIT",
                severity="critical",
                title=RULE_LOOKUP["CRIT_VM_INIT"]["title"],
                file_path=rel_path,
                line_number=line_num,
                snippet=stripped,
                recommendation=RULE_LOOKUP["CRIT_VM_INIT"]["recommendation"]
            ))

        # CRIT_STATE_INIT: _state = State(initialValue:
        if re.search(r'_\w+\s*=\s*State\s*\(\s*initialValue\s*:', stripped):
            findings.append(Finding(
                rule_id="CRIT_STATE_INIT",
                severity="critical",
                title=RULE_LOOKUP["CRIT_STATE_INIT"]["title"],
                file_path=rel_path,
                line_number=line_num,
                snippet=stripped,
                recommendation=RULE_LOOKUP["CRIT_STATE_INIT"]["recommendation"]
            ))

        # CRIT_TRANSIENT_ID: .id(UUID()) or ForEach(..., id: \.self) with UUID()
        if re.search(r'\.id\s*\(\s*UUID\s*\(\s*\)\s*\)', stripped) or re.search(r'ForEach\b[^,]+,\s*id:\s*\\\.self\b[^)]*UUID\(', stripped):
            findings.append(Finding(
                rule_id="CRIT_TRANSIENT_ID",
                severity="critical",
                title=RULE_LOOKUP["CRIT_TRANSIENT_ID"]["title"],
                file_path=rel_path,
                line_number=line_num,
                snippet=stripped,
                recommendation=RULE_LOOKUP["CRIT_TRANSIENT_ID"]["recommendation"]
            ))

        # HIGH_ANYVIEW: AnyView(
        if re.search(r'\bAnyView\s*\(', stripped):
            findings.append(Finding(
                rule_id="HIGH_ANYVIEW",
                severity="high",
                title=RULE_LOOKUP["HIGH_ANYVIEW"]["title"],
                file_path=rel_path,
                line_number=line_num,
                snippet=stripped,
                recommendation=RULE_LOOKUP["HIGH_ANYVIEW"]["recommendation"]
            ))

        # LOW_PRINT_CHANGES: Self._printChanges()
        if re.search(r'\b(?:Self\.)?_printChanges\s*\(\s*\)', stripped):
            findings.append(Finding(
                rule_id="LOW_PRINT_CHANGES",
                severity="low",
                title=RULE_LOOKUP["LOW_PRINT_CHANGES"]["title"],
                file_path=rel_path,
                line_number=line_num,
                snippet=stripped,
                recommendation=RULE_LOOKUP["LOW_PRINT_CHANGES"]["recommendation"]
            ))

        # MED_UNSCOPED_ANIMATION: .animation(.easeIn) without value:
        anim_match = re.search(r'\.animation\s*\(\s*(\.[a-zA-Z]+(?:\([^)]*\))?)\s*\)', stripped)
        if anim_match and "value:" not in stripped:
            findings.append(Finding(
                rule_id="MED_UNSCOPED_ANIMATION",
                severity="medium",
                title=RULE_LOOKUP["MED_UNSCOPED_ANIMATION"]["title"],
                file_path=rel_path,
                line_number=line_num,
                snippet=stripped,
                recommendation=RULE_LOOKUP["MED_UNSCOPED_ANIMATION"]["recommendation"]
            ))

    # 2. Block-level inspections: Heavy compute in `body`
    body_blocks = find_body_blocks(content)
    for start_line, end_line, body_str in body_blocks:
        body_lines = body_str.splitlines()
        for idx, b_line in enumerate(body_lines):
            b_stripped = b_line.strip()
            cur_line_num = start_line + idx

            if b_stripped.startswith("//"):
                continue

            # Heavy allocation/compute: DateFormatter(), NumberFormatter(), JSONDecoder(), .sorted(
            compute_patterns = [
                (r'\bDateFormatter\s*\(\s*\)', "DateFormatter instantiation in body"),
                (r'\bISO8601DateFormatter\s*\(\s*\)', "ISO8601DateFormatter instantiation in body"),
                (r'\bNumberFormatter\s*\(\s*\)', "NumberFormatter instantiation in body"),
                (r'\bJSONDecoder\s*\(\s*\)', "JSONDecoder instantiation in body"),
                (r'\.sorted\s*[\(\{]', "Array .sorted() called in body"),
                (r'\.filter\s*[\(\{]', "Array .filter() called in body"),
            ]
            for pattern, desc in compute_patterns:
                if re.search(pattern, b_stripped):
                    findings.append(Finding(
                        rule_id="HIGH_BODY_COMPUTE",
                        severity="high",
                        title=f"{RULE_LOOKUP['HIGH_BODY_COMPUTE']['title']} ({desc})",
                        file_path=rel_path,
                        line_number=cur_line_num,
                        snippet=b_stripped,
                        recommendation=RULE_LOOKUP["HIGH_BODY_COMPUTE"]["recommendation"]
                    ))

    # 3. Contextual scans across file content
    # HIGH_SHEET_IN_LOOP: .sheet / .fullScreenCover inside ForEach
    foreach_pattern = re.compile(r'\bForEach\b[^{]*\{')
    for match in foreach_pattern.finditer(content):
        res = extract_balanced_block(content, match.end() - 1)
        if res:
            _, inner_content = res
            if re.search(r'\.(?:sheet|fullScreenCover|popover)\s*\(', inner_content):
                offset = match.start()
                line_num = content[:offset].count('\n') + 1
                snippet = inner_content.strip().splitlines()[0] if inner_content.strip() else "ForEach block"
                findings.append(Finding(
                    rule_id="HIGH_SHEET_IN_LOOP",
                    severity="high",
                    title=RULE_LOOKUP["HIGH_SHEET_IN_LOOP"]["title"],
                    file_path=rel_path,
                    line_number=line_num,
                    snippet=f"ForEach {snippet[:60]}...",
                    recommendation=RULE_LOOKUP["HIGH_SHEET_IN_LOOP"]["recommendation"]
                ))

    # HIGH_ONAPPEAR_TASK: Task inside onAppear
    onappear_pattern = re.compile(r'\.onAppear\s*(?:\([^)]*\))?\s*\{')
    for match in onappear_pattern.finditer(content):
        res = extract_balanced_block(content, match.end() - 1)
        if res:
            _, inner_content = res
            if re.search(r'\bTask\s*\{', inner_content):
                offset = match.start()
                line_num = content[:offset].count('\n') + 1
                findings.append(Finding(
                    rule_id="HIGH_ONAPPEAR_TASK",
                    severity="high",
                    title=RULE_LOOKUP["HIGH_ONAPPEAR_TASK"]["title"],
                    file_path=rel_path,
                    line_number=line_num,
                    snippet=".onAppear { Task { ... } }",
                    recommendation=RULE_LOOKUP["HIGH_ONAPPEAR_TASK"]["recommendation"]
                ))

    # MED_EAGER_SCROLL: ScrollView containing eager VStack/HStack with ForEach
    scroll_pattern = re.compile(r'\bScrollView\b[^{]*\{')
    for match in scroll_pattern.finditer(content):
        res = extract_balanced_block(content, match.end() - 1)
        if res:
            _, scroll_inner = res
            eager_stack_match = re.search(r'\b([HV]Stack)\b[^{]*\{', scroll_inner)
            if eager_stack_match:
                stack_type = eager_stack_match.group(1)
                stack_open_pos = eager_stack_match.end() - 1
                stack_res = extract_balanced_block(scroll_inner, stack_open_pos)
                if stack_res:
                    _, stack_inner = stack_res
                    if "ForEach" in stack_inner:
                        offset = match.start()
                        line_num = content[:offset].count('\n') + 1
                        findings.append(Finding(
                            rule_id="MED_EAGER_SCROLL",
                            severity="medium",
                            title=f"{RULE_LOOKUP['MED_EAGER_SCROLL']['title']} ({stack_type})",
                            file_path=rel_path,
                            line_number=line_num,
                            snippet=f"ScrollView {{ {stack_type} {{ ForEach(...) }} }}",
                            recommendation=RULE_LOOKUP["MED_EAGER_SCROLL"]["recommendation"]
                        ))

    # MED_GEOMETRY_READER inside List or Lazy collection
    geom_pattern = re.compile(r'\b(List|LazyVStack|LazyHStack)\b[^{]*\{')
    for match in geom_pattern.finditer(content):
        container_type = match.group(1)
        res = extract_balanced_block(content, match.end() - 1)
        if res:
            _, container_inner = res
            if "GeometryReader" in container_inner:
                offset = match.start()
                line_num = content[:offset].count('\n') + 1
                findings.append(Finding(
                    rule_id="MED_GEOMETRY_READER",
                    severity="medium",
                    title=f"{RULE_LOOKUP['MED_GEOMETRY_READER']['title']} in {container_type}",
                    file_path=rel_path,
                    line_number=line_num,
                    snippet=f"{container_type} {{ GeometryReader {{ ... }} }}",
                    recommendation=RULE_LOOKUP["MED_GEOMETRY_READER"]["recommendation"]
                ))

    # 4. Init blocks: side effects and logging
    init_pattern = re.compile(r'\binit\s*\([^)]*\)\s*\{')
    for match in init_pattern.finditer(content):
        res = extract_balanced_block(content, match.end() - 1)
        if res:
            _, inner_content = res
            init_lines = inner_content.splitlines()
            for idx, i_line in enumerate(init_lines):
                i_strip = i_line.strip()
                if i_strip.startswith("//"):
                    continue
                if re.search(r'\b(?:print|Analytics\.\w+|Logger\.\w+|os_log)\s*\(', i_strip):
                    offset = match.start()
                    line_num = content[:offset].count('\n') + idx + 1
                    findings.append(Finding(
                        rule_id="HIGH_INIT_SIDE_EFFECT",
                        severity="high",
                        title=RULE_LOOKUP["HIGH_INIT_SIDE_EFFECT"]["title"],
                        file_path=rel_path,
                        line_number=line_num,
                        snippet=i_strip,
                        recommendation=RULE_LOOKUP["HIGH_INIT_SIDE_EFFECT"]["recommendation"]
                    ))

    # 5. @Observable classes: missing @ObservationIgnored on timers/tokens
    observable_pattern = re.compile(r'@Observable\s+(?:final\s+)?class\s+\w+[^{]*\{')
    for match in observable_pattern.finditer(content):
        res = extract_balanced_block(content, match.end() - 1)
        if res:
            _, class_inner = res
            class_lines = class_inner.splitlines()
            for idx, c_line in enumerate(class_lines):
                c_strip = c_line.strip()
                if c_strip.startswith("//"):
                    continue
                # If declares Timer, AnyCancellable, Task without @ObservationIgnored
                if re.search(r'\bvar\s+\w+\s*:\s*(?:Timer\??|AnyCancellable|Set<AnyCancellable>|Task<[^>]+>\??)', c_strip):
                    # Check if preceding line or same line has @ObservationIgnored
                    prev_line = class_lines[idx - 1].strip() if idx > 0 else ""
                    has_annotation = prev_line.startswith("@ObservationIgnored") or "@ObservationIgnored" in c_strip
                    if not has_annotation:
                        offset = match.start()
                        line_num = content[:offset].count('\n') + idx + 1
                        findings.append(Finding(
                            rule_id="MED_OBSERVATION_IGNORED",
                            severity="medium",
                            title=RULE_LOOKUP["MED_OBSERVATION_IGNORED"]["title"],
                            file_path=rel_path,
                            line_number=line_num,
                            snippet=c_strip,
                            recommendation=RULE_LOOKUP["MED_OBSERVATION_IGNORED"]["recommendation"]
                        ))

    return findings

def render_text(findings: List[Finding], target_path: str, min_severity: str) -> str:
    min_rank = SEVERITY_ORDER[min_severity]
    filtered = [f for f in findings if SEVERITY_ORDER[f.severity] <= min_rank]

    lines = []
    lines.append("=" * 80)
    lines.append(f"  SwiftUI Render Performance Scan: {target_path}")
    lines.append("=" * 80)

    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for f in filtered:
        counts[f.severity] += 1

    lines.append(f"Summary: {counts['critical']} Critical | {counts['high']} High | {counts['medium']} Medium | {counts['low']} Low")
    lines.append("-" * 80)

    if not filtered:
        lines.append("✅ No SwiftUI render anti-patterns detected!")
        return "\n".join(lines)

    # Sort findings by severity then path
    filtered.sort(key=lambda x: (SEVERITY_ORDER[x.severity], x.file_path, x.line_number))

    for f in filtered:
        sev_tag = f"[{f.severity.upper():<8}]"
        lines.append(f"{sev_tag} {f.title}")
        lines.append(f"  Location: {f.file_path}:{f.line_number}")
        lines.append(f"  Code:     {f.snippet}")
        lines.append(f"  Fix:      {f.recommendation}")
        lines.append("")

    return "\n".join(lines)

def render_markdown(findings: List[Finding], target_path: str, min_severity: str) -> str:
    min_rank = SEVERITY_ORDER[min_severity]
    filtered = [f for f in findings if SEVERITY_ORDER[f.severity] <= min_rank]

    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for f in filtered:
        counts[f.severity] += 1

    md = []
    md.append(f"# SwiftUI Render Performance Audit: `{target_path}`\n")
    md.append("## Executive Summary\n")
    md.append("| Critical | High | Medium | Low | Total Findings |")
    md.append("| :---: | :---: | :---: | :---: | :---: |")
    md.append(f"| **{counts['critical']}** | **{counts['high']}** | **{counts['medium']}** | **{counts['low']}** | **{len(filtered)}** |\n")

    if not filtered:
        md.append("✅ **No SwiftUI render bottlenecks or anti-patterns detected.**\n")
        return "\n".join(md)

    filtered.sort(key=lambda x: (SEVERITY_ORDER[x.severity], x.file_path, x.line_number))

    md.append("## Detailed Findings\n")
    for f in filtered:
        badge = {
            "critical": "🔴 **CRITICAL**",
            "high": "🟠 **HIGH**",
            "medium": "🟡 **MEDIUM**",
            "low": "🔵 **LOW**"
        }.get(f.severity, f.severity.upper())

        md.append(f"### {badge}: {f.title}")
        md.append(f"- **File**: `{f.file_path}:{f.line_number}`")
        md.append(f"- **Recommendation**: {f.recommendation}")
        md.append("```swift")
        md.append(f"// Line {f.line_number}")
        md.append(f"{f.snippet}")
        md.append("```\n")

    return "\n".join(md)

def render_json(findings: List[Finding], target_path: str, min_severity: str) -> str:
    min_rank = SEVERITY_ORDER[min_severity]
    filtered = [f for f in findings if SEVERITY_ORDER[f.severity] <= min_rank]

    payload = {
        "target": target_path,
        "total_findings": len(filtered),
        "counts": {
            "critical": sum(1 for f in filtered if f.severity == "critical"),
            "high": sum(1 for f in filtered if f.severity == "high"),
            "medium": sum(1 for f in filtered if f.severity == "medium"),
            "low": sum(1 for f in filtered if f.severity == "low"),
        },
        "findings": [asdict(f) for f in filtered]
    }
    return json.dumps(payload, indent=2)

def main():
    parser = argparse.ArgumentParser(description="SwiftUI Render Performance Static Scanner")
    parser.add_argument("path", help="Path to Xcode project, package, or directory to scan")
    parser.add_argument("--format", choices=["text", "markdown", "json"], default="text", help="Output format")
    parser.add_argument("--min-severity", choices=["critical", "high", "medium", "low"], default="low", help="Minimum severity threshold")
    parser.add_argument("-o", "--output", help="Optional file path to write results")

    args = parser.parse_args()
    target_path = Path(args.path).resolve()

    if not target_path.exists():
        print(f"Error: Target path '{target_path}' does not exist.", file=sys.stderr)
        sys.exit(1)

    swift_files = []
    if target_path.is_file() and target_path.suffix == ".swift":
        swift_files.append(target_path)
    else:
        for root, dirs, files in os.walk(target_path):
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
            for file in files:
                if file.endswith(".swift"):
                    swift_files.append(Path(root) / file)

    all_findings: List[Finding] = []
    for file_p in swift_files:
        all_findings.extend(scan_file(file_p))

    if args.format == "markdown":
        output = render_markdown(all_findings, str(target_path), args.min_severity)
    elif args.format == "json":
        output = render_json(all_findings, str(target_path), args.min_severity)
    else:
        output = render_text(all_findings, str(target_path), args.min_severity)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Audit results written to {args.output}")
    else:
        print(output)

    # Return exit code 1 if critical issues found
    if any(f.severity == "critical" for f in all_findings):
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()
