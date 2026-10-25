import UIKit

struct Product {
    let id: String
    let title: String
    let createdAt: Date
    let rawImageData: Data
}

class ProductCell: UITableViewCell {
    @IBOutlet weak var titleLabel: UILabel!
    @IBOutlet weak var dateLabel: UILabel!
    @IBOutlet weak var productImageView: UIImageView!

    func configure(with product: Product) {
        titleLabel.text = product.title
        
        // HITCH HAZARD 1: Formatter allocation on main thread in cell render
        let formatter = DateFormatter()
        formatter.dateStyle = .medium
        formatter.timeStyle = .short
        dateLabel.text = formatter.string(from: product.createdAt)

        // HITCH HAZARD 2: Main-thread image decompression
        let image = UIImage(data: product.rawImageData)
        productImageView.image = image
    }
}

class ProductListViewController: UITableViewController {
    var products: [Product] = []

    override func tableView(_ tableView: UITableView, numberOfRowsInSection section: Int) -> Int {
        products.count
    }

    override func tableView(_ tableView: UITableView, cellForRowAt indexPath: IndexPath) -> UITableViewCell {
        let cell = tableView.dequeueReusableCell(withIdentifier: "ProductCell", for: indexPath) as! ProductCell
        cell.configure(with: products[indexPath.row])
        return cell
    }
}
