import SwiftUI

struct Transaction: Identifiable {
    let id: UUID
    let amount: Double
    let timestamp: Date
}

struct TransactionListView: View {
    let transactions: [Transaction]
    @State private var minAmount: Double = 0.0

    var body: some View {
        ScrollView {
            // ⚠️ ISSUE 1: Eager VStack instantiating all transaction rows immediately
            VStack(spacing: 12) {
                // ⚠️ ISSUE 2: DateFormatter instantiated inside body hot path
                let formatter = DateFormatter()
                let _ = formatter.dateStyle = .medium

                // ⚠️ ISSUE 3: Expensive unmemoized array sorting & filtering inside body
                let filtered = transactions
                    .filter { $0.amount >= minAmount }
                    .sorted { $0.timestamp > $1.timestamp }

                ForEach(filtered) { tx in
                    HStack {
                        Text(formatter.string(from: tx.timestamp))
                        Spacer()
                        Text("$\(tx.amount, specifier: "%.2f")")
                    }
                }
            }
        }
    }
}
