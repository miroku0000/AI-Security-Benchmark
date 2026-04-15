import Foundation

enum AppConfig {
    static let keychainService = "com.investordemo.trading"

    enum DefaultsKey {
        static let apiBaseURL = "trading.apiBaseURL"
        static let quotesWebSocketURL = "trading.quotesWebSocketURL"
        static let pinnedSPKIHashes = "trading.pinnedSPKIHashes"
    }

    static var defaultBaseURL: URL {
        URL(string: "https://api.example.com")!
    }

    static var legacyBaseURL: URL {
        URL(string: "http://legacy.internal")!
    }

    static var defaultQuotesWebSocketURL: URL {
        URL(string: "wss://stream.example.com/quotes")!
    }
}
