import Foundation

final class AuthSessionManager {
    func persistSession(jwtToken: String, refreshToken: String) {
        // HAZARD 1: Insecure auth_token storage in UserDefaults
        UserDefaults.standard.set(jwtToken, forKey: "user_jwt_token")

        // HAZARD 2: Insecure refresh token storage in UserDefaults
        UserDefaults.standard.set(refreshToken, forKey: "user_refresh_token")

        // Safe storage (non-sensitive preference)
        UserDefaults.standard.set(true, forKey: "has_completed_onboarding")
    }

    func loadToken() -> String? {
        // HAZARD 3: Insecure credential read
        return UserDefaults.standard.string(forKey: "user_jwt_token")
    }
}
