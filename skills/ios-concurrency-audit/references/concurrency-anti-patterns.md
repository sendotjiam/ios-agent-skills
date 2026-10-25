# iOS Concurrency Anti-Patterns & Solutions

This reference catalog details common concurrency mistakes, root causes, failure modes, and idiomatic Swift solutions.

---

## 1. Actor Reentrancy Pitfalls

### Pattern 1.1: Double-Fetch / Stampede in Caching Actors
**Symptom**: Redundant network requests triggered simultaneously for the same resource, wasting bandwidth and corrupting cache state.

**Anti-Pattern**:
```swift
actor ImageCache {
    private var cache: [URL: UIImage] = [:]

    func image(for url: URL) async throws -> UIImage {
        if let cached = cache[url] {
            return cached
        }
        // SUSPENSION: Multiple callers reach this point while the download is in-flight!
        let (data, _) = try await URLSession.shared.data(from: url)
        guard let image = UIImage(data: data) else { throw CacheError.invalidData }
        cache[url] = image
        return image
    }
}
```

**Safe Solution (In-Flight Task Deduplication)**:
```swift
actor ImageCache {
    private enum CacheEntry {
        case inProgress(Task<UIImage, Error>)
        case ready(UIImage)
    }
    private var cache: [URL: CacheEntry] = [:]

    func image(for url: URL) async throws -> UIImage {
        if let entry = cache[url] {
            switch entry {
            case .ready(let image):
                return image
            case .inProgress(let task):
                return try await task.value
            }
        }

        let downloadTask = Task { () -> UIImage in
            let (data, _) = try await URLSession.shared.data(from: url)
            guard let image = UIImage(data: data)?.preparingForDisplay() else {
                throw CacheError.invalidData
            }
            return image
        }

        cache[url] = .inProgress(downloadTask)
        do {
            let image = try await downloadTask.value
            cache[url] = .ready(image)
            return image
        } catch {
            cache.removeValue(forKey: url)
            throw error
        }
    }
}
```

---

## 2. Main-Thread Blocking & Mini-Hangs

### Pattern 2.1: Heavy JSON Parsing or Cryptography on `@MainActor`
**Symptom**: UI drops frames (100–300ms freeze) when opening a screen with a large API response.

**Anti-Pattern**:
```swift
@MainActor
class FeedViewModel: ObservableObject {
    @Published var items: [FeedItem] = []

    func loadFeed() async {
        let (data, _) = try! await URLSession.shared.data(from: feedURL)
        // RUNS ON MAIN THREAD: Blocks rendering while decoding 5MB of JSON
        let decoded = try! JSONDecoder().decode([FeedItem].self, from: data)
        self.items = decoded
    }
}
```

**Safe Solution (Non-Isolated Worker Function)**:
```swift
@MainActor
class FeedViewModel: ObservableObject {
    @Published var items: [FeedItem] = []

    func loadFeed() async {
        let (data, _) = try! await URLSession.shared.data(from: feedURL)
        // Offload decoding to the cooperative background pool
        let decoded = await Task.detached(priority: .userInitiated) {
            try? JSONDecoder().decode([FeedItem].self, from: data)
        }.value ?? []
        self.items = decoded
    }
}
```

### Pattern 2.2: Expensive Formatters in Cell Lifecycle
**Symptom**: Scroll hitching (mini-hangs of 20–50ms) in `UICollectionView` or SwiftUI `List`.

**Anti-Pattern**:
```swift
func collectionView(_ collectionView: UICollectionView, cellForItemAt indexPath: IndexPath) -> UICollectionViewCell {
    let cell = collectionView.dequeueReusableCell(withReuseIdentifier: "Cell", for: indexPath) as! FeedCell
    let item = items[indexPath.row]
    // AVOID: Initializing DateFormatter on every cell render is extremely costly!
    let formatter = DateFormatter()
    formatter.dateStyle = .medium
    cell.dateLabel.text = formatter.string(from: item.timestamp)
    return cell
}
```

**Safe Solution (Static Cached Formatter / Modern FormatStyle)**:
```swift
// Swift 5.5+ FormatStyle (Fast & lightweight)
cell.dateLabel.text = item.timestamp.formatted(date: .abbreviated, time: .omitted)

// Or static cached instance
private enum Formatters {
    static let mediumDate: DateFormatter = {
        let f = DateFormatter()
        f.dateStyle = .medium
        return f
    }()
}
```

---

## 3. Deadlocks & Cooperative Pool Starvation

### Pattern 3.1: Bridging Async Code to Synchronous with `DispatchSemaphore`
**Symptom**: Sudden, inexplicable freeze of the entire app or random network timeouts under load.

**Anti-Pattern**:
```swift
// Synchronous wrapper called from legacy code or background task
func getUserSync(id: String) -> User? {
    let semaphore = DispatchSemaphore(value: 0)
    var user: User?
    Task {
        user = await repository.fetchUser(id: id)
        semaphore.signal()
    }
    // DANGER: If called from a thread in the cooperative pool, wait() starves the pool thread.
    // If all pool threads block on semaphores, no Task can ever run -> COMPLETE DEADLOCK.
    semaphore.wait()
    return user
}
```

**Safe Solution**:
Do not block threads in Swift Concurrency. Migrate the caller to `async`, or if bridging from Objective-C/legacy sync APIs, use completion handlers on a dedicated dispatch queue rather than blocking a cooperative pool thread.

---

## 4. UI Lifecycle & Task Cancellation

### Pattern 4.1: Stray Unstructured Tasks in Table/Collection Cells
**Symptom**: Memory leaks, flickers, and mismatched data when scrolling rapidly as recycled cells receive results from prior rows.

**Anti-Pattern**:
```swift
class PostCell: UICollectionViewCell {
    @IBOutlet weak var avatarImageView: UIImageView!

    func configure(with post: Post) {
        // AVOID: Cell recycling does not cancel this Task!
        Task {
            let image = await ImageService.shared.fetchAvatar(for: post.authorId)
            self.avatarImageView.image = image // May display author A on cell reused for author B!
        }
    }
}
```

**Safe Solution (Cancellation on Reuse)**:
```swift
class PostCell: UICollectionViewCell {
    @IBOutlet weak var avatarImageView: UIImageView!
    private var loadTask: Task<Void, Never>?

    override func prepareForReuse() {
        super.prepareForReuse()
        loadTask?.cancel()
        loadTask = nil
        avatarImageView.image = nil
    }

    func configure(with post: Post) {
        loadTask?.cancel()
        loadTask = Task { [weak self] in
            let image = await ImageService.shared.fetchAvatar(for: post.authorId)
            guard !Task.isCancelled else { return }
            self?.avatarImageView.image = image
        }
    }
}
```
In SwiftUI, prefer `.task(id: post.id) { ... }` which automatically cancels and restarts when identity changes or when the view leaves the hierarchy.
