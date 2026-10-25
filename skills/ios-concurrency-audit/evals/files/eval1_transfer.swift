import UIKit

actor AccountManager {
    private var balance: Decimal = 1000
    private let paymentService: PaymentGateway

    init(paymentService: PaymentGateway) {
        self.paymentService = paymentService
    }

    func transfer(amount: Decimal, to recipient: String) async throws -> Bool {
        guard balance >= amount else { return false }
        // SUSPENSION HAZARD: Reentrancy vulnerability
        let success = try await paymentService.charge(amount, recipient: recipient)
        if success {
            balance -= amount
            return true
        }
        return false
    }
}

class TransferViewController: UIViewController {
    let accountManager: AccountManager

    init(accountManager: AccountManager) {
        self.accountManager = accountManager
        super.init(nibName: nil, bundle: nil)
    }
    
    required init?(coder: NSCoder) { fatalError() }

    override func viewDidLoad() {
        super.viewDidLoad()
        // MAIN THREAD BLOCK: Synchronous disk read on main thread
        let localConfigURL = Bundle.main.bundleURL.appendingPathComponent("config.json")
        let configData = try! Data(contentsOf: localConfigURL)
        let config = try! JSONDecoder().decode([String: String].self, from: configData)
        print("Loaded config: \(config)")
    }

    @objc func onTransferTapped() {
        Task {
            _ = try await accountManager.transfer(amount: 50, to: "user_456")
        }
    }
}

protocol PaymentGateway {
    func charge(_ amount: Decimal, recipient: String) async throws -> Bool
}
