import SwiftUI

public struct ActiveView: View {
    let service = ActiveService()
    public var body: some View {
        Text(service.fetch())
    }
}
