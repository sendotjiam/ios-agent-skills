# Fault Thrashing, Prefetching & N+1 Query Prevention

Core Data and SwiftData use **faulting** to maintain low memory footprints. A fault is a placeholder object representing a row in SQLite whose attributes and relationships have not yet been materialized into memory. 

When code accesses a property on a faulted object, the framework issues a synchronous disk read (`trip to the database`) to fire the fault. Uncoordinated fault resolution in loops or UI scrolling causes **fault thrashing** and severe UI frame drops.

---

## 1. The N+1 Query Problem

When an entity with a to-one or to-many relationship is fetched, the framework initially fetches only the parent objects. Accessing a related property inside a loop triggers a separate SQLite query for every iteration:

$$\text{Total SQLite Queries} = 1\ (\text{initial fetch}) + N\ (\text{one query per child})$$

```swift
// ❌ 1 initial query + 500 individual child queries to SQLite
let request: NSFetchRequest<Department> = Department.fetchRequest()
let departments = try context.fetch(request) // Query 1

for dept in departments {
    for employee in dept.employees { // Query 2..501! Stalls Main Thread
        print(employee.name)
    }
}
```

---

## 2. Prefetching Solutions

### Core Data: `relationshipKeyPathsForPrefetching`

Tell Core Data ahead of time to fetch related entities in a single batch SQL join:

```swift
// ✅ Exactly 2 SQLite queries total regardless of count
let request: NSFetchRequest<Department> = Department.fetchRequest()
request.relationshipKeyPathsForPrefetching = ["employees"]
request.returnsObjectsAsFaults = false

let departments = try context.fetch(request)
for dept in departments {
    for employee in dept.employees {
        print(employee.name) // In-memory lookup, zero disk I/O
    }
}
```

### SwiftData: `FetchDescriptor` Prefetching

```swift
// ✅ SwiftData prefetching
var descriptor = FetchDescriptor<Department>(
    predicate: #Predicate { $0.isActive }
)
descriptor.relationshipKeyPathsForPrefetching = [\.employees]

let departments = try modelContext.fetch(descriptor)
```

---

## 3. The `fetchBatchSize` Rule

By default, an `NSFetchRequest` without a batch size materializes **all matching records** in RAM simultaneously. If a table contains 50,000 records, executing `context.fetch(request)` creates 50,000 objects in memory immediately.

### Setting the Optimal Batch Size

```swift
let request: NSFetchRequest<Message> = Message.fetchRequest()
// Set to 2x to 3x the number of visible rows on screen
request.fetchBatchSize = 40
```

When `fetchBatchSize` is enabled:
1. Core Data only allocates a array of lightweight fault pointers.
2. Only the active batch (e.g. 40 rows) is held in memory.
3. As the user scrolls a `UITableView` or `UICollectionView`, subsequent batches are transparently paged from disk.

---

## 4. UI Scroll Stalls in Table and Collection Views

### 🔴 Anti-Pattern: Faulting in Cell Configuration

```swift
func collectionView(_ collectionView: UICollectionView, cellForItemAt indexPath: IndexPath) -> UICollectionViewCell {
    let cell = collectionView.dequeueReusableCell(withReuseIdentifier: "Cell", for: indexPath) as! OrderCell
    let order = orders[indexPath.row]
    // ❌ Firing customer and items faults synchronously during 120Hz scroll!
    cell.customerNameLabel.text = order.customer.name
    cell.itemCountLabel.text = "\(order.items.count)"
    return cell
}
```

### ✅ Clean Solution: Warm Up / DTO Projection

1. Ensure the fetch request backing the datasource includes `request.relationshipKeyPathsForPrefetching = ["customer", "items"]`.
2. Or perform a dictionary/tuple fetch with `NSDictionaryResultType` or custom value-type DTO projection if only scalar fields are required for display:

```swift
request.resultType = .dictionaryResultType
request.propertiesToFetch = ["id", "customer.name", "totalAmount"]
```

---

## 5. Detecting Fault Thrashing with Instruments

Run **Instruments -> Core Data -> Faults**:
- Look for continuous steep spikes in **Fault Trips**.
- In Xcode, inspect the Console using launch argument:
```
-com.apple.CoreData.SQLDebug 1
```
If you see repeating lines of `SELECT 0, t0.Z_PK, t0.Z_OPT... FROM ZEMPLOYEE t0 WHERE t0.ZDEPARTMENT = ?`, you have an active N+1 query regression.
