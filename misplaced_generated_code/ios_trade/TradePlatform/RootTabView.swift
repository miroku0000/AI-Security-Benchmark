import SwiftUI

struct RootTabView: View {
    @Environment(TradingEngine.self) private var engine

    var body: some View {
        TabView {
            MarketsView()
                .tabItem { Label("Markets", systemImage: "chart.line.uptrend.xyaxis") }
            PortfolioView()
                .tabItem { Label("Portfolio", systemImage: "briefcase.fill") }
            OrdersView()
                .tabItem { Label("Activity", systemImage: "clock.arrow.circlepath") }
            SettingsView()
                .tabItem { Label("Account", systemImage: "person.crop.circle") }
        }
        .tint(.cyan)
    }
}
