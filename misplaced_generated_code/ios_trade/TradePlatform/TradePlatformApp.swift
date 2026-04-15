import SwiftUI

@main
struct TradePlatformApp: App {
    @State private var engine = TradingEngine()

    var body: some Scene {
        WindowGroup {
            RootTabView()
                .environment(engine)
        }
    }
}
