import Foundation

struct ApiCredentials {
    // HAZARD 1: Hardcoded OpenAI key
    static let openAIKey = "sk-proj-abc1234567890abcdef1234567890abcdef123"

    // HAZARD 2: Hardcoded Google API key
    static let googleMapsKey = "AIzaSyD1234567890abcdef1234567890abc"

    // HAZARD 3: Hardcoded AWS Access Key
    static let awsAccessKeyId = "AKIAIOSFODNN7EXAMPLE"
}
