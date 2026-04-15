import SwiftUI

struct ContentView: View {
    @EnvironmentObject private var promoState: PromoApplicationState

    var body: some View {
        NavigationStack {
            VStack(spacing: 20) {
                Text("Marketing promo")
                    .font(.title2.weight(.semibold))
                if let applied = promoState.lastApplied {
                    VStack(spacing: 8) {
                        Text("Active promo")
                            .foregroundStyle(.green)
                        Text("Code: \(applied.code)")
                        Text("Discount: \(applied.discountPercent)%")
                    }
                    .padding()
                } else {
                    Text("Open a promo link to apply a code.")
                        .foregroundStyle(.secondary)
                        .multilineTextAlignment(.center)
                }
                if let account = promoState.accountSnapshot {
                    Divider()
                    Text("Account")
                        .font(.headline)
                    Text("User ID: \(account.userId)")
                    if let balance = account.balance {
                        Text(String(format: "Balance: %.2f", balance))
                    }
                    if let discounted = account.discountedBalance {
                        Text(String(format: "After discount: %.2f", discounted))
                            .foregroundStyle(.green)
                    }
                }
                Spacer(minLength: 0)
            }
            .padding()
            .navigationTitle("Promo")
        }
    }
}

#Preview {
    ContentView()
        .environmentObject(PromoApplicationState())
}
