import SwiftUI

@main
struct TradingApp: App {
    @StateObject private var session = TradingSession()
    @StateObject private var market = MarketRealtime()

    var body: some Scene {
        WindowGroup {
            MainTabView()
                .environmentObject(session)
                .environmentObject(market)
        }
    }
}
