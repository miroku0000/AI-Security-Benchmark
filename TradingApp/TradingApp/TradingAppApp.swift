import SwiftUI

@main
struct TradingAppApp: App {
    @State private var tradingStore = TradingStore()

    var body: some Scene {
        WindowGroup {
            MainTabView()
                .environment(tradingStore)
        }
    }
}
