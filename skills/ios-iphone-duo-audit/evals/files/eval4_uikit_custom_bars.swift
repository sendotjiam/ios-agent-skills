import UIKit

final class CustomReaderViewController: UIViewController {
    private let customToolbar = UIToolbar()
    private let bottomTabBar = UITabBar()

    override func viewDidLoad() {
        super.viewDidLoad()
        view.addSubview(customToolbar)
        view.addSubview(bottomTabBar)
    }
}
