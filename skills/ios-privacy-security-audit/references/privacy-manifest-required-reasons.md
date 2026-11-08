# Apple Privacy Manifest (`PrivacyInfo.xcprivacy`) & Required Reason APIs

## Overview
Starting in May 2024, Apple strictly enforces Privacy Manifest declarations for any app or third-party SDK submitted to App Store Connect. If an app calls an API classified under **Required Reason APIs** without declaring that API category and an approved reason code in `PrivacyInfo.xcprivacy`, App Store submissions are automatically rejected with error `ITMS-91053`.

---

## 1. The 5 Required Reason API Categories & Approved Codes

### A. User Defaults (`NSPrivacyAccessedAPICategoryUserDefaults`)
- **Covered APIs:** `UserDefaults`, `UserDefaults.standard`, `UserDefaults(suiteName:)`
- **Approved Reason Codes:**
  - `CA92.1`: Access user defaults to read or write information that is only accessible to the app itself.
  - `1C8F.1`: Access user defaults to read or write information that is shared between apps in the same App Group.

### B. System Boot Time (`NSPrivacyAccessedAPICategorySystemBootTime`)
- **Covered APIs:** `systemUptime`, `mach_absolute_time()`
- **Approved Reason Codes:**
  - `35F9.1`: Measure the amount of time that has elapsed between events that occurred within the app (e.g. benchmarking, UI responsiveness).
  - `8FFB.1`: Calculate absolute timestamps for events occurring within the app.

### C. Disk Space (`NSPrivacyAccessedAPICategoryDiskSpace`)
- **Covered APIs:** `volumeAvailableCapacityKey`, `volumeAvailableCapacityForImportantUsageKey`, `volumeTotalCapacityKey`, `statfs`, `statvfs`
- **Approved Reason Codes:**
  - `85F4.1`: Display disk space to the person using the device.
  - `E174.1`: Check whether there is sufficient disk space to write files or download content.
  - `1B2D.1`: Manage in-app files and caches to avoid disk-exhaustion crashes.

### D. File Timestamps (`NSPrivacyAccessedAPICategoryFileTimestamp`)
- **Covered APIs:** `URLContentModificationDateKey`, `URLCreationDateKey`, `fileModificationDate`, `fileCreationDate`, `stat`
- **Approved Reason Codes:**
  - `0A2A.1`: Display the date or timestamp of files to the person using the device.
  - `3B52.1`: Access timestamps of files inside the app's container, app group, or cloud documents.
  - `C617.1`: Access timestamps of files inside the app bundle.

### E. Active Keyboards (`NSPrivacyAccessedAPICategoryActiveKeyboards`)
- **Covered APIs:** `UITextInputMode.activeInputModes`
- **Approved Reason Codes:**
  - `3EC4.1`: Present custom keyboards or adjust text formatting based on active keyboard modes.
  - `54DA.1`: Customize in-app user interface elements based on keyboard layout.

---

## 2. Sample Valid `PrivacyInfo.xcprivacy`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>NSPrivacyTracking</key>
    <false/>
    <key>NSPrivacyTrackingDomains</key>
    <array/>
    <key>NSPrivacyCollectedDataTypes</key>
    <array/>
    <key>NSPrivacyAccessedAPITypes</key>
    <array>
        <dict>
            <key>NSPrivacyAccessedAPIType</key>
            <string>NSPrivacyAccessedAPICategoryUserDefaults</string>
            <key>NSPrivacyAccessedAPITypeReasons</key>
            <array>
                <string>CA92.1</string>
            </array>
        </dict>
        <dict>
            <key>NSPrivacyAccessedAPIType</key>
            <string>NSPrivacyAccessedAPICategorySystemBootTime</string>
            <key>NSPrivacyAccessedAPITypeReasons</key>
            <array>
                <string>35F9.1</string>
            </array>
        </dict>
        <dict>
            <key>NSPrivacyAccessedAPIType</key>
            <string>NSPrivacyAccessedAPICategoryDiskSpace</string>
            <key>NSPrivacyAccessedAPITypeReasons</key>
            <array>
                <string>E174.1</string>
            </array>
        </dict>
    </array>
</dict>
</plist>
```
