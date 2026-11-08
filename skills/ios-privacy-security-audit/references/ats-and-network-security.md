# App Transport Security (ATS) & Network Transport Hardening

## 1. App Transport Security (ATS) Rules
By default on iOS and macOS, Apple enforces App Transport Security (ATS) on all network requests initiated by `URLSession` or `WKWebView`.
- Requests must use **HTTPS** with **TLS 1.2 or TLS 1.3**.
- Symmetric ciphers must support Forward Secrecy (ECDHE).
- Certificates must use SHA-256 or better with 2048-bit+ RSA or 256-bit+ ECC keys.

---

## 2. Insecure ATS Anti-Patterns

### Anti-Pattern 1: `NSAllowsArbitraryLoads = true`
```xml
<!-- Info.plist: HIGH RISK - REJECTION RISK -->
<key>NSAppTransportSecurity</key>
<dict>
    <key>NSAllowsArbitraryLoads</key>
    <true/>
</dict>
```
**Why it fails App Store review:**
Apple requires explicit justification for `NSAllowsArbitraryLoads` during App Store review. Apps without a documented requirement for unrestricted HTTP access will be rejected.

### Remediation: Per-Domain Exceptions
If communicating with an internal or legacy domain that cannot support HTTPS:
```xml
<key>NSAppTransportSecurity</key>
<dict>
    <key>NSExceptionDomains</key>
    <dict>
        <key>legacy-api.internal.company.com</key>
        <dict>
            <key>NSIncludesSubdomains</key>
            <true/>
            <key>NSTemporaryExceptionAllowsInsecureHTTPLoads</key>
            <true/>
        </dict>
    </dict>
</dict>
```

---

## 3. Biometric Authentication Guards (`LocalAuthentication`)

### Vulnerable Pattern:
```swift
let context = LAContext()
// RISKY: If device lacks Face ID hardware or passcode, evaluatePolicy fails silently or crashes
context.evaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, localizedReason: "Unlock") { success, _ in
    if success { grantAccess() }
}
```

### Secure Pattern:
```swift
let context = LAContext()
var authError: NSError?

if context.canEvaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, error: &authError) {
    context.evaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, localizedReason: "Unlock App") { success, error in
        DispatchQueue.main.async {
            if success {
                grantAccess()
            } else {
                presentPasscodeFallback()
            }
        }
    }
} else {
    // Hardware or biometric enrollment unavailable -> fallback to app passcode
    presentPasscodeFallback()
}
```
