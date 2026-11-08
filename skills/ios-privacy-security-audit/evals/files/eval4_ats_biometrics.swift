import Foundation
import LocalAuthentication

final class NetworkAndBiometricService {
    func executeLogin() {
        // HAZARD 1: Insecure plaintext HTTP URL
        let url = URL(string: "http://api.internal-enterprise.com/v1/auth")!
        let request = URLRequest(url: url)
        print("Sending to \(request)")
    }

    func authenticateWithFaceID() {
        let context = LAContext()
        // HAZARD 2: Biometric evaluatePolicy without canEvaluatePolicy check
        context.evaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, localizedReason: "Unlock wallet") { success, error in
            if success {
                print("Authenticated successfully")
            }
        }
    }
}
