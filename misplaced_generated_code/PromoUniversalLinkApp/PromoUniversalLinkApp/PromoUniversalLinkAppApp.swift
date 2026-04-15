import SwiftUI

@main
struct PromoUniversalLinkAppApp: App {
    @StateObject private var promoState = PromoApplicationState()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(promoState)
                .onOpenURL { url in
                    PromoLinkRouter.handle(url: url, state: promoState)
                }
                .onContinueUserActivity(NSUserActivityTypeBrowsingWeb) { userActivity in
                    guard let url = userActivity.webpageURL else { return }
                    PromoLinkRouter.handle(url: url, state: promoState)
                }
        }
    }
}
