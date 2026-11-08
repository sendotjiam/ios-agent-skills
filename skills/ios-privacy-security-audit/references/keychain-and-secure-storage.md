# Keychain Services & Secure Credential Storage

## 1. Why `UserDefaults` is Insecure for Credentials
- **Storage Location:** `Library/Preferences/<bundle-id>.plist` in sandbox.
- **Encryption:** Plaintext XML file; unencrypted on disk while the device is unlocked.
- **Vulnerabilities:**
  - Exported in unencrypted iTunes / Finder local backups.
  - Accessible immediately on jailbroken devices.
  - Retained indefinitely unless explicitly deleted.

---

## 2. Drop-in Secure Keychain Helper (Swift 6 Concurrency Safe)

```swift
import Foundation
import Security

public enum KeychainStorageError: Error {
    case duplicateItem
    case itemNotFound
    case unexpectedStatus(OSStatus)
}

public final class SecureTokenStorage: Sendable {
    public static let shared = SecureTokenStorage()
    private let service: String

    public init(service: String = Bundle.main.bundleIdentifier ?? "com.app.credentials") {
        self.service = service
    }

    public func save(token: String, forKey account: String) throws {
        guard let data = token.data(using: .utf8) else { return }

        // Query to check existing item
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
            kSecValueData as String: data,
            kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlock
        ]

        let status = SecItemAdd(query as CFDictionary, nil)
        if status == errSecDuplicateItem {
            // Update existing
            let updateQuery: [String: Any] = [
                kSecClass as String: kSecClassGenericPassword,
                kSecAttrService as String: service,
                kSecAttrAccount as String: account
            ]
            let attributesToUpdate: [String: Any] = [
                kSecValueData as String: data
            ]
            let updateStatus = SecItemUpdate(updateQuery as CFDictionary, attributesToUpdate as CFDictionary)
            guard updateStatus == errSecSuccess else {
                throw KeychainStorageError.unexpectedStatus(updateStatus)
            }
        } else if status != errSecSuccess {
            throw KeychainStorageError.unexpectedStatus(status)
        }
    }

    public func read(forKey account: String) -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]

        var item: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &item)
        guard status == errSecSuccess, let data = item as? Data else {
            return nil
        }
        return String(data: data, encoding: .utf8)
    }

    public func delete(forKey account: String) {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account
        ]
        SecItemDelete(query as CFDictionary)
    }
}
```
