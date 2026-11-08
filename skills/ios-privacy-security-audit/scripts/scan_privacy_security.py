#!/usr/bin/env python3
"""
scan_privacy_security.py - iOS Privacy Manifest & Security Fast-Scanner

Audits iOS, iPadOS, macOS, and watchOS codebases for:
  1. Apple Required Reason APIs without Privacy Manifest declarations (PrivacyInfo.xcprivacy)
  2. Insecure Credential Storage (Tokens/Passwords in UserDefaults vs Keychain)
  3. Hardcoded Secrets (API keys, AWS tokens, private keys)
  4. Insecure Network Transport (plain http://, ATS NSAllowsArbitraryLoads bypasses)
  5. Biometric Authentication & LocalAuthentication vulnerabilities
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


# Apple Required Reason API Categories and their signature symbols
REQUIRED_REASON_APIS = {
    "NSPrivacyAccessedAPICategoryUserDefaults": {
        "rule_id": "PRIV_REQ_USERDEFAULTS",
        "category": "Apple Privacy Manifest: UserDefaults Required Reason",
        "severity": "High",
        "pattern": re.compile(r'\bUserDefaults(?:\.standard|\([a-zA-Z0-9_:]+\))\b'),
        "reason_hint": "Declare 'NSPrivacyAccessedAPICategoryUserDefaults' with reason code CA92.1 (app data storage) in PrivacyInfo.xcprivacy.",
    },
    "NSPrivacyAccessedAPICategorySystemBootTime": {
        "rule_id": "PRIV_REQ_BOOTTIME",
        "category": "Apple Privacy Manifest: System Boot Time Required Reason",
        "severity": "High",
        "pattern": re.compile(r'\b(?:ProcessInfo\.processInfo\.systemUptime|mach_absolute_time\(\))\b'),
        "reason_hint": "Declare 'NSPrivacyAccessedAPICategorySystemBootTime' with reason code 35F9.1 (timing inside app) in PrivacyInfo.xcprivacy.",
    },
    "NSPrivacyAccessedAPICategoryDiskSpace": {
        "rule_id": "PRIV_REQ_DISKSPACE",
        "category": "Apple Privacy Manifest: Disk Space Required Reason",
        "severity": "High",
        "pattern": re.compile(r'\b(?:volumeAvailableCapacityForImportantUsageKey|volumeAvailableCapacityKey|volumeTotalCapacityKey|statfs|statvfs)\b'),
        "reason_hint": "Declare 'NSPrivacyAccessedAPICategoryDiskSpace' with reason code 85F4.1 (displaying space) or E174.1 (checking space before download).",
    },
    "NSPrivacyAccessedAPICategoryFileTimestamp": {
        "rule_id": "PRIV_REQ_FILETIME",
        "category": "Apple Privacy Manifest: File Timestamp Required Reason",
        "severity": "High",
        "pattern": re.compile(r'\b(?:URLContentModificationDateKey|URLCreationDateKey|fileModificationDate|fileCreationDate)\b'),
        "reason_hint": "Declare 'NSPrivacyAccessedAPICategoryFileTimestamp' with reason code 0A2A.1 (displaying timestamps) or 3B52.1 (in-app file access).",
    },
    "NSPrivacyAccessedAPICategoryActiveKeyboards": {
        "rule_id": "PRIV_REQ_KEYBOARD",
        "category": "Apple Privacy Manifest: Active Keyboard Required Reason",
        "severity": "High",
        "pattern": re.compile(r'\bactiveInputModes\b'),
        "reason_hint": "Declare 'NSPrivacyAccessedAPICategoryActiveKeyboards' with reason code 3EC4.1 in PrivacyInfo.xcprivacy.",
    },
}

# Sensitive keys stored insecurely in UserDefaults
SENSITIVE_KEY_PATTERN = re.compile(
    r'\bUserDefaults\.standard\.(?:set|setValue|string|object)\s*\([^,]+,\s*(?:forKey|for)\s*:\s*["\']([^"\']*(?:token|jwt|auth|secret|password|bearer|apikey|api_key|credential|private_key)[^"\']*)["\']',
    re.IGNORECASE,
)

# Hardcoded secret credentials
SECRET_PATTERNS = [
    (re.compile(r'["\']sk-(?:proj-)?[a-zA-Z0-9_\-]{32,}["\']'), "SEC_OPENAI_KEY", "Critical", "Hardcoded OpenAI / LLM API Key detected in source code."),
    (re.compile(r'["\']AIza[0-9A-Za-z_\-]{30,40}["\']'), "SEC_GOOGLE_KEY", "Critical", "Hardcoded Google API Key detected in source code."),
    (re.compile(r'["\']AKIA[0-9A-Z]{16}["\']'), "SEC_AWS_KEY", "Critical", "Hardcoded AWS Access Key ID detected in source code."),
    (re.compile(r'-----BEGIN (?:RSA |EC )?PRIVATE KEY-----'), "SEC_PRIVATE_KEY", "Critical", "Unencrypted private cryptographic key block embedded in source code."),
    (re.compile(r'\b(?:let|var)\s+[a-zA-Z0-9_]*(?:secret|apiKey|api_key|auth_token)\s*=\s*["\'][a-zA-Z0-9_\-]{16,}["\']', re.IGNORECASE), "SEC_HARDCODED_CREDENTIAL", "High", "High-entropy secret or API token hardcoded in Swift variable declaration."),
]


class PrivacySecurityScanner:
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
        self.privacy_manifest_categories: Set[str] = set()
        self.has_privacy_manifest = False

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
        self._index_privacy_manifests()

        swift_files: List[Path] = []
        plist_files: List[Path] = []

        if self.target_path.is_file():
            if self.target_path.suffix == ".swift":
                swift_files.append(self.target_path)
            elif self.target_path.name == "Info.plist":
                plist_files.append(self.target_path)
        else:
            for root, dirs, files in os.walk(self.target_path):
                dirs[:] = [d for d in dirs if not any(ign in d for ign in self.ignore_patterns)]
                for file in files:
                    full_p = Path(root) / file
                    if self.should_ignore(full_p):
                        continue
                    if file.endswith(".swift"):
                        swift_files.append(full_p)
                    elif file.endswith(".plist") and "Info" in file:
                        plist_files.append(full_p)

        self.files_scanned = len(swift_files) + len(plist_files)

        for p_file in plist_files:
            self._scan_info_plist(p_file)

        for s_file in swift_files:
            self._scan_swift_file(s_file)

        min_rank = self.severity_order.get(self.min_severity, 1)
        self.findings = [
            f for f in self.findings if self.severity_order.get(f.severity.lower(), 1) >= min_rank
        ]
        self.findings.sort(
            key=lambda x: (-self.severity_order.get(x.severity.lower(), 1), x.file_path, x.line_number)
        )
        return self.findings

    def _index_privacy_manifests(self):
        manifest_files: List[Path] = []
        if self.target_path.is_file() and self.target_path.name == "PrivacyInfo.xcprivacy":
            manifest_files.append(self.target_path)
        elif self.target_path.is_dir():
            for root, _, files in os.walk(self.target_path):
                for f in files:
                    if f == "PrivacyInfo.xcprivacy":
                        manifest_files.append(Path(root) / f)

        if manifest_files:
            self.has_privacy_manifest = True
            for m_path in manifest_files:
                try:
                    content = m_path.read_text(encoding="utf-8", errors="replace")
                    for cat in REQUIRED_REASON_APIS.keys():
                        if cat in content:
                            self.privacy_manifest_categories.add(cat)
                except Exception:
                    pass

    def _scan_info_plist(self, file_path: Path):
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return

        lines = content.splitlines()
        file_str = str(file_path)
        for idx, line in enumerate(lines):
            if "<key>NSAllowsArbitraryLoads</key>" in line:
                window = "\n".join(lines[idx:min(idx + 3, len(lines))])
                if "<true/>" in window:
                    self.findings.append(Finding(
                        severity="Critical",
                        category="App Transport Security (ATS) Insecure HTTP",
                        rule_id="ATS_ALLOWS_ARBITRARY_LOADS",
                        file_path=file_str,
                        line_number=idx + 1,
                        matched_snippet=line.strip(),
                        description="NSAllowsArbitraryLoads is enabled in Info.plist, completely disabling ATS and allowing insecure unencrypted HTTP connections.",
                        remediation="Remove NSAllowsArbitraryLoads and use HTTPS exclusively or configure scoped NSExceptionDomains."
                    ))

    def _scan_swift_file(self, file_path: Path):
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return

        lines = content.splitlines()
        self.lines_scanned += len(lines)
        file_str = str(file_path)

        for idx, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
                continue

            prev_line = lines[idx - 1] if idx > 0 else ""

            # 1. Apple Required Reason APIs
            for cat_key, cat_data in REQUIRED_REASON_APIS.items():
                if cat_data["pattern"].search(line):
                    # If manifest is present and already declares this category, skip
                    if self.has_privacy_manifest and cat_key in self.privacy_manifest_categories:
                        continue

                    rule_id = cat_data["rule_id"]
                    if not self.is_rule_suppressed(line, prev_line, rule_id):
                        manifest_status = "Missing PrivacyInfo.xcprivacy" if not self.has_privacy_manifest else f"Missing '{cat_key}' in PrivacyInfo.xcprivacy"
                        self.findings.append(Finding(
                            severity=cat_data["severity"],
                            category=cat_data["category"],
                            rule_id=rule_id,
                            file_path=file_str,
                            line_number=idx + 1,
                            matched_snippet=stripped,
                            description=f"Accessed Apple Required Reason API ({cat_key}) without declared manifest entry. {manifest_status}.",
                            remediation=cat_data["reason_hint"]
                        ))

            # 2. Insecure Storage in UserDefaults
            sens_match = SENSITIVE_KEY_PATTERN.search(line)
            if sens_match:
                rule_id = "INSECURE_USERDEFAULTS_STORAGE"
                if not self.is_rule_suppressed(line, prev_line, rule_id):
                    key_name = sens_match.group(1)
                    self.findings.append(Finding(
                        severity="Critical",
                        category="Insecure Credential Storage",
                        rule_id=rule_id,
                        file_path=file_str,
                        line_number=idx + 1,
                        matched_snippet=stripped,
                        description=f"Sensitive authentication key '{key_name}' stored in unencrypted UserDefaults plist.",
                        remediation="Store credentials in iOS Keychain Services (kSecClassGenericPassword) or a secure enclave wrapper."
                    ))

            # 3. Hardcoded Secrets
            for pat, rule_id, sev, desc in SECRET_PATTERNS:
                if pat.search(line):
                    if not self.is_rule_suppressed(line, prev_line, rule_id):
                        self.findings.append(Finding(
                            severity=sev,
                            category="Hardcoded Secret Credential",
                            rule_id=rule_id,
                            file_path=file_str,
                            line_number=idx + 1,
                            matched_snippet=stripped[:80] + "...",
                            description=desc,
                            remediation="Extract credentials to Xcode .xcconfig / environment variables and inject at build time."
                        ))

            # 4. Insecure HTTP URLs
            if "http://" in line and not any(safe in line for safe in ["http://localhost", "http://127.0.0.1", "http://schemas.xmlsoap.org"]):
                rule_id = "INSECURE_HTTP_TRANSPORT"
                if not self.is_rule_suppressed(line, prev_line, rule_id):
                    self.findings.append(Finding(
                        severity="High",
                        category="Insecure Network Transport",
                        rule_id=rule_id,
                        file_path=file_str,
                        line_number=idx + 1,
                        matched_snippet=stripped,
                        description="Insecure plaintext HTTP URL used instead of encrypted HTTPS, violating App Transport Security (ATS).",
                        remediation="Upgrade URL protocol scheme to 'https://' to ensure transport-layer encryption."
                    ))

            # 5. Biometric Authentication LocalAuthentication Bypasses
            if "evaluatePolicy" in line:
                window_lines = [l for l in lines[max(0, idx - 8):min(idx + 15, len(lines))] if not l.strip().startswith("//")]
                window = "\n".join(window_lines)
                if "LAContext" in window or "LocalAuthentication" in content:
                    if "canEvaluatePolicy" not in window:
                        rule_id = "BIOMETRIC_CHECK_WITHOUT_CAN_EVALUATE"
                        if not self.is_rule_suppressed(line, prev_line, rule_id):
                            self.findings.append(Finding(
                                severity="Medium",
                                category="LocalAuthentication Biometric Bypass",
                                rule_id=rule_id,
                                file_path=file_str,
                                line_number=idx + 1,
                                matched_snippet=stripped,
                                description="LAContext.evaluatePolicy called without pre-flight 'canEvaluatePolicy', risking crash or silent auth bypass.",
                                remediation="Guard with 'context.canEvaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, error: &error)'."
                            ))


def format_table(scanner: PrivacySecurityScanner) -> str:
    lines = []
    lines.append(f"\n{BOLD}{CYAN}=== iOS Privacy & Security Audit Scan ==={RESET}")
    lines.append(f"Scanned {scanner.files_scanned} files ({scanner.lines_scanned} lines)")
    manifest_tag = f"{GREEN}Present ({len(scanner.privacy_manifest_categories)} categories declared){RESET}" if scanner.has_privacy_manifest else f"{RED}Missing{RESET}"
    lines.append(f"PrivacyInfo.xcprivacy: {manifest_tag}\n")

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
        lines.append(f"{GREEN}✅ No privacy or security vulnerabilities detected.{RESET}\n")
        return "\n".join(lines)

    lines.append(f"{'SEV':<10} {'RULE ID':<26} {'LOCATION':<36} {'CATEGORY'}")
    lines.append("-" * 90)

    for f in scanner.findings:
        color = RED if f.severity == "Critical" else YELLOW if f.severity == "High" else CYAN
        loc = f"{Path(f.file_path).name}:{f.line_number}"
        lines.append(f"{color}{f.severity:<10}{RESET} {f.rule_id:<26} {loc:<36} {f.category}")
        lines.append(f"  {DIM}Snippet:{RESET} {f.matched_snippet}")
        lines.append(f"  {DIM}Fix:{RESET} {f.remediation}\n")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="iOS Privacy Manifest & Security Fast-Scanner")
    parser.add_argument("path", nargs="?", default=".", help="Target Xcode project or folder")
    parser.add_argument("--format", choices=["table", "json", "markdown", "xcode"], default="table")
    parser.add_argument("--min-severity", choices=["critical", "high", "medium", "low"], default="low")
    parser.add_argument("--include-tests", action="store_true", help="Include test files in audit")
    parser.add_argument("-o", "--output", help="Write report to file")

    args = parser.parse_args()
    scanner = PrivacySecurityScanner(args.path, min_severity=args.min_severity, include_tests=args.include_tests)
    findings = scanner.scan()

    if args.format == "table":
        out = format_table(scanner)
    elif args.format == "xcode":
        out = "\n".join([f"{f.file_path}:{f.line_number}:1: {'error' if f.severity in ['Critical', 'High'] else 'warning'}: [ios-privacy-security-audit] [{f.rule_id}] {f.description}" for f in findings])
    elif args.format == "markdown":
        out = f"# iOS Privacy & Security Audit Report\n\nTotal findings: {len(findings)}\n"
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
