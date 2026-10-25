import Foundation
import Combine

// Scenario 1: ViewModel Closure & Combine Retain Cycles

final class UserProfileViewModel {
    var onProfileUpdated: (() -> Void)?
    @Published var username: String = ""
    @Published var email: String = ""

    private var cancellables = Set<AnyCancellable>()
    private let userService: UserService

    init(userService: UserService) {
        self.userService = userService
        setupBindings()
        setupCallbacks()
    }

    private func setupBindings() {
        // HAZARD 1: Combine assign(to:on: self) creates permanent retain cycle
        userService.namePublisher
            .assign(to: \.username, on: self)
            .store(in: &cancellables)

        // HAZARD 2: Combine .sink capturing self strongly
        userService.emailPublisher
            .sink { emailValue in
                self.email = emailValue
                self.logAnalytics(event: "email_updated")
            }
            .store(in: &cancellables)
    }

    private func setupCallbacks() {
        // HAZARD 3: Escaping closure stored as property capturing self
        self.onProfileUpdated = {
            self.refreshUserData()
        }
    }

    private func logAnalytics(event: String) {}
    private func refreshUserData() {}
}

class UserService {
    var namePublisher: AnyPublisher<String, Never> {
        Just("Alex").eraseToAnyPublisher()
    }

    var emailPublisher: AnyPublisher<String, Never> {
        Just("alex@example.com").eraseToAnyPublisher()
    }
}
