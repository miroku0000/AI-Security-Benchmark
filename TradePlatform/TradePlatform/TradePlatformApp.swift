import SwiftUI

@main
struct TradePlatformApp: App {
    @StateObject private var portfolioStore = PortfolioStore()
    @StateObject private var quoteStream = QuoteStreamService()

    var body: some Scene {
        WindowGroup {
            RootTabView()
                .environmentObject(portfolioStore)
                .environmentObject(quoteStream)
                .preferredColorScheme(.dark)
        }
    }
}
