import SwiftUI

struct MainTabView: View {
    @EnvironmentObject var session: TradingSession

    var body: some View {
        TabView(selection: $session.selectedTab) {
            MarketsView()
                .tabItem { Label("Markets", systemImage: "chart.line.uptrend.xyaxis") }
                .tag(0)
            PortfolioView()
                .tabItem { Label("Portfolio", systemImage: "briefcase.fill") }
                .tag(1)
            ActivityView()
                .tabItem { Label("Activity", systemImage: "clock.arrow.circlepath") }
                .tag(2)
        }
        .tint(Color(red: 0.15, green: 0.55, blue: 0.35))
    }
}
