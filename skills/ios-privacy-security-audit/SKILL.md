---
name: ios-privacy-security-audit
description: Audits iOS, iPadOS, macOS, and watchOS projects for Apple Privacy Manifest (PrivacyInfo.xcprivacy) required reason APIs, insecure credential storage in UserDefaults vs Keychain, hardcoded API secrets, App Transport Security (ATS) HTTP exceptions, and biometric auth bypasses.
---

# `ios-privacy-security-audit`

## Purpose
A production-grade privacy, security, and App Store submission readiness auditor for Apple platforms. Detects compliance blockers (Apple Required Reason APIs under May 2024 enforcement), unencrypted token storage in `UserDefaults`, hardcoded API credentials, and ATS vulnerabilities before submitting to App Store Connect.

---

## ⚡ Fast-Scanner CLI

Run the zero-dependency Python scanner across your repository:

```bash
# Output formatted colored terminal table
python3 skills/ios-privacy-security-audit/scripts/scan_privacy_security.py /path/to/project

# Format for Xcode Issue Navigator inline warnings
python3 skills/ios-privacy-security-audit/scripts/scan_privacy_security.py /path/to/project --format xcode

# Machine-readable JSON output
python3 skills/ios-privacy-security-audit/scripts/scan_privacy_security.py /path/to/project --format json
```

---

## 🛡️ Detection Taxonomy & Severity Tiers

| Severity | Rule ID | Category | Detection Target |
| :--- | :--- | :--- | :--- |
| **Critical** | `INSECURE_USERDEFAULTS_STORAGE` | Credential Security | Storing auth tokens, JWTs, bearer headers, or passwords in plain-text `UserDefaults`. |
| **Critical** | `SEC_OPENAI_KEY` / `SEC_GOOGLE_KEY` / `SEC_AWS_KEY` | Secret Management | Hardcoded LLM API keys (`sk-...`), Google (`AIza...`), AWS (`AKIA...`), or private keys. |
| **Critical** | `ATS_ALLOWS_ARBITRARY_LOADS` | Network Transport | `<key>NSAllowsArbitraryLoads</key><true/>` in `Info.plist` disabling ATS globally. |
| **High** | `PRIV_REQ_USERDEFAULTS` | Apple Privacy Manifest | `UserDefaults` accessed without declared reason code (`CA92.1` / `1C8F.1`) in `PrivacyInfo.xcprivacy`. |
| **High** | `PRIV_REQ_BOOTTIME` | Apple Privacy Manifest | `systemUptime` or `mach_absolute_time` accessed without declared reason (`35F9.1`). |
| **High** | `PRIV_REQ_DISKSPACE` | Apple Privacy Manifest | `volumeAvailableCapacityKey` or `statfs` accessed without declared reason (`85F4.1` / `E174.1`). |
| **High** | `PRIV_REQ_FILETIME` | Apple Privacy Manifest | `URLContentModificationDateKey` accessed without declared reason (`0A2A.1` / `3B52.1`). |
| **High** | `PRIV_REQ_KEYBOARD` | Apple Privacy Manifest | `activeInputModes` accessed without declared reason (`3EC4.1`). |
| **High** | `INSECURE_HTTP_TRANSPORT` | Network Transport | Unencrypted `http://` URLs used in API clients. |
| **Medium** | `BIOMETRIC_CHECK_WITHOUT_CAN_EVALUATE` | LocalAuthentication | `LAContext.evaluatePolicy` invoked without checking `canEvaluatePolicy` first. |

---

## 📖 Bundled References & Recipes
- [Apple Privacy Manifest Required Reasons Guide](./references/privacy-manifest-required-reasons.md)
- [Keychain Services & Secure Token Storage](./references/keychain-and-secure-storage.md)
- [ATS & Network Transport Hardening](./references/ats-and-network-security.md)
- [Benchmark Evaluation Report](./evals/benchmark.md)
