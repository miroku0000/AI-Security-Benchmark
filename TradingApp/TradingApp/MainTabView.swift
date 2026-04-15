import SwiftUI

struct MainTabView: View {
    @Environment(TradingStore.self) private var store

    var body: some View {
        TabView {
            MarketWatchView()
                .tabItem { Label("Markets", systemImage: "chart.line.uptrend.xyaxis") }
            PortfolioView()
                .tabItem { Label("Portfolio", systemImage: "briefcase.fill") }
            ConnectionSettingsView()
                .tabItem { Label("Connect", systemImage: "lock.shield.fill") }
        }
        .tint(.cyan)
        .task {
            await store.refreshAll()
        }
    }
}
