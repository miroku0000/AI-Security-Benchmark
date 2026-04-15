import SwiftUI

struct OrdersView: View {
    @Environment(TradingEngine.self) private var engine

    var body: some View {
        NavigationStack {
            List {
                if engine.orders.isEmpty {
                    ContentUnavailableView("No trades yet", systemImage: "tray")
                } else {
                    ForEach(engine.orders) { o in
                        VStack(alignment: .leading, spacing: 6) {
                            HStack {
                                Text(o.symbol).font(.headline)
                                Spacer()
                                Text(o.side.rawValue.uppercased())
                                    .font(.caption.weight(.semibold))
                                    .padding(.horizontal, 8)
                                    .padding(.vertical, 4)
                                    .background(o.side == .buy ? Color.green.opacity(0.2) : Color.red.opacity(0.2))
                                    .clipShape(Capsule())
                            }
                            HStack {
                                Text("\(formatQty(o.quantity)) @ \(formatMoney(o.fillPrice))")
                                    .font(.subheadline.monospacedDigit())
                                Spacer()
                                Text(o.timestamp.formatted(date: .abbreviated, time: .shortened))
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                        }
                        .padding(.vertical, 4)
                    }
                }
            }
            .navigationTitle("Activity")
        }
    }

    private func formatMoney(_ d: Decimal) -> String {
        let f = NumberFormatter()
        f.numberStyle = .currency
        f.currencyCode = "USD"
        return f.string(from: d as NSDecimalNumber) ?? "$0.00"
    }

    private func formatQty(_ d: Decimal) -> String {
        let f = NumberFormatter()
        f.maximumFractionDigits = 4
        return f.string(from: d as NSDecimalNumber) ?? "0"
    }
}
