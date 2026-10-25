# Memory Bloat, Autorelease Pools & JetSam OOM Prevention

A memory leak is not the only cause of Out-Of-Memory (OOM) crashes in iOS apps. Transient **memory bloat**—where memory consumption temporarily spikes beyond the physical device's threshold—triggers Apple's low-memory killer daemon (**JetSam**) to terminate the application with `EXC_RESOURCE RESOURCE_TYPE_MEMORY`.

---

## 1. RunLoop Mechanics & Autorelease Pool Exhaustion

In Objective-C and Swift, objects returned as `autoreleased` (e.g., Core Graphics representations, `Data(contentsOf:)`, `UIImage` decodes, formatters) are placed into the thread's active `NSAutoreleasePool`.

### The Problem: Monotonic Accumulation in Tight Loops
By default, the thread's autorelease pool is only drained at the **end of each RunLoop turn**. If your code runs a tight synchronous loop that processes 500 images or 10,000 JSON payloads on a single RunLoop turn, none of the intermediate autoreleased objects are deallocated until the entire loop finishes:

```swift
// ❌ HIGH BLOAT: 500 images kept in RAM simultaneously until loop finishes
func processPhotoBatch(urls: [URL]) {
    for url in urls {
        // Each raw UIImage consumes 20-50MB uncompressed bitmap in RAM
        if let image = UIImage(contentsOfFile: url.path) {
            let processed = applyFilters(image)
            saveToDisk(processed)
        }
    } // Memory reaches 1.5 GB -> Kernel terminates app via JetSam!
}
```

### The Solution: `@autoreleasepool { ... }`
Wrapping each iteration in `@autoreleasepool` forces ARC to drain the autorelease pool immediately at the end of each iteration:

```swift
// ✅ CLEAN: Memory strictly capped at ~30MB throughout the entire batch
func processPhotoBatch(urls: [URL]) {
    for url in urls {
        @autoreleasepool {
            if let image = UIImage(contentsOfFile: url.path) {
                let processed = applyFilters(image)
                saveToDisk(processed)
            }
        }
    }
}
```

---

## 2. Image Decoding: Downsampling vs Full-Resolution Bitmaps

A compressed JPEG/PNG file might only be 2MB on disk, but when iOS renders it in a `UIImageView`, it must decompress it into an uncompressed bitmap buffer:

$$\text{RAM Consumption} = \text{Width} \times \text{Height} \times 4 \text{ bytes (RGBA8888)}$$

A 48MP camera photo ($8000 \times 6000$ pixels) consumes:
$$8000 \times 6000 \times 4 = 192,000,000 \text{ bytes} \approx 192\text{ MB of RAM!}$$

Loading 10 such images into a scrolling `UICollectionView` or SwiftUI `LazyVGrid` consumes nearly 2GB of RAM, guaranteeing an immediate crash.

### Production Downsampling Recipe (`ImageIO`)
Instead of decoding the full 192MB bitmap, decode only the exact pixel size required by the display container using `CGImageSourceCreateThumbnailAtIndex`:

```swift
import ImageIO
import UIKit

func downsample(imageAt imageURL: URL, to pointSize: CGSize, scale: CGFloat = UIScreen.main.scale) -> UIImage? {
    // 1. Create CGImageSource without immediately caching bitmap
    let sourceOptions = [kCGImageSourceShouldCache: false] as CFDictionary
    guard let imageSource = CGImageSourceCreateWithURL(imageURL as CFURL, sourceOptions) else {
        return nil
    }

    // 2. Calculate target pixel dimension
    let maxDimensionInPixels = max(pointSize.width, pointSize.height) * scale

    // 3. Request thumbnail decoding directly at destination resolution
    let downsampleOptions = [
        kCGImageSourceCreateThumbnailFromImageAlways: true,
        kCGImageSourceShouldCacheImmediately: true,
        kCGImageSourceCreateThumbnailWithTransform: true,
        kCGImageSourceThumbnailMaxPixelSize: maxDimensionInPixels
    ] as [CFString: Any] as CFDictionary

    guard let downsampledImage = CGImageSourceCreateThumbnailAtIndex(imageSource, 0, downsampleOptions) else {
        return nil
    }

    return UIImage(cgImage: downsampledImage)
}
```

> **Memory Saving:** Reduces RAM footprint from 192 MB down to **~1.2 MB** per image with zero visible loss in screen sharpness.

---

## 3. Unbounded In-Memory Caches: `Dictionary` vs `NSCache`

Standard Swift collections (`[Key: Value]`) never purge entries unless explicitly modified. In contrast, `NSCache` is integrated directly into the iOS kernel's memory pressure notification subsystem.

```swift
// ❌ HIGH RISK: Unbounded Dictionary Cache
final class ImageStore {
    // Grows indefinitely until device runs out of memory
    private var cache = [String: UIImage]()

    func store(_ image: UIImage, for key: String) {
        cache[key] = image
    }
}

// ✅ CLEAN: Memory-Aware NSCache
final class ImageStore {
    private let cache = NSCache<NSString, UIImage>()

    init() {
        // Automatically limits max objects and total cost (e.g. 100MB)
        cache.countLimit = 100
        cache.totalCostLimit = 100 * 1024 * 1024
    }

    func store(_ image: UIImage, for key: String) {
        let cost = Int(image.size.width * image.size.height * 4)
        cache.setObject(image, forKey: key as NSString, cost: cost)
    }

    func image(for key: String) -> UIImage? {
        return cache.object(forKey: key as NSString)
    }
}
```

---

## 4. Core Data Batch Fault Retention & Context Bloat

When Core Data fetches or modifies records, it registers each `NSManagedObject` inside the `NSManagedObjectContext`. During bulk migrations or batch imports, these objects accumulate in memory as live faults:

```swift
// ❌ HIGH BLOAT: 50,000 managed objects held in context memory
func importRecords(payloads: [[String: Any]], context: NSManagedObjectContext) {
    for payload in payloads {
        let record = UserEntity(context: context)
        record.update(from: payload)
    }
    try? context.save()
}
```

### The Fix: Periodic Slicing with `reset()`
Drain intermediate objects by saving and calling `context.reset()` or `context.refreshAllObjects()` in chunks:

```swift
// ✅ CLEAN: Context stays small, resident memory remains constant
func importRecords(payloads: [[String: Any]], context: NSManagedObjectContext) {
    let batchSize = 500
    for (index, payload) in payloads.enumerated() {
        @autoreleasepool {
            let record = UserEntity(context: context)
            record.update(from: payload)

            if (index + 1) % batchSize == 0 {
                try? context.save()
                context.reset() // Clears all fault references from RAM
            }
        }
    }
    try? context.save()
    context.reset()
}
```
