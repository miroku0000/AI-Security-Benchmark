import Foundation

enum AppConfiguration {
    static var apiBaseURL: URL? {
        guard let s = Bundle.main.object(forInfoDictionaryKey: "TRADE_API_BASE_URL") as? String,
              !s.isEmpty,
              let u = URL(string: s) else { return nil }
        return u
    }

    static var websocketURL: URL? {
        guard let s = Bundle.main.object(forInfoDictionaryKey: "TRADE_WS_URL") as? String,
              !s.isEmpty,
              let u = URL(string: s) else { return nil }
        return u
    }

    static let keychainTokenAccount = "access_token"
}
