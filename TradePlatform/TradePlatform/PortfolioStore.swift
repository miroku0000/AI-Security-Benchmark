import Foundation
import SwiftUI

@MainActor
final class PortfolioStore: ObservableObject {
    @Published private(set) var snapshot: PortfolioSnapshot
    @Published var isPlacingOrder = false
    @Published var lastTradeMessage: String?
    @Published var useLiveAPI = false
    @Published var demoToken: String = ""

    private let api: TradingAPIClient

    init(api: TradingAPIClient = TradingAPIClient()) {
        self.api = api
        self.snapshot = PortfolioSnapshot(
            cashBalance: 100_000,
            positions: [
                Position(symbol: "AAPL", quantity: 50, averageCost: 170, currentPrice: 178.5),
                Position(symbol: "MSFT", quantity: 30, averageCost: 400, currentPrice: 415.2)
            ],
            orders: []
        )
    }

    func syncPrices(from quotes: [String: StockQuote]) {
        var positions = snapshot.positions
        for i in positions.indices {
            if let q = quotes[positions[i].symbol] {
                positions[i].currentPrice = q.last
            }
        }
        snapshot = PortfolioSnapshot(cashBalance: snapshot.cashBalance, positions: positions, orders: snapshot.orders)
    }

    func applyDemoAuth() {
        guard !demoToken.isEmpty else { return }
        do {
            try api.setAccessToken(demoToken)
            lastTradeMessage = "Credentials stored in Keychain."
        } catch {
            lastTradeMessage = "Keychain error: \(error.localizedDescription)"
        }
    }

    func refreshFromAPI() async {
        do {
            let snap = try await api.fetchPortfolio()
            snapshot = snap
            lastTradeMessage = "Portfolio synced."
        } catch {
            lastTradeMessage = "Sync failed: \(error.localizedDescription)"
        }
    }

    func executeTrade(symbol: String, side: OrderSide, quantity: Int, limitPrice: Decimal?, referencePrice: Decimal?) async {
        isPlacingOrder = true
        defer { isPlacingOrder = false }
        let sym = symbol.uppercased().trimmingCharacters(in: .whitespacesAndNewlines)
        guard quantity > 0, !sym.isEmpty else {
            lastTradeMessage = "Invalid symbol or quantity."
            return
        }
        if useLiveAPI {
            do {
                let req = PlaceOrderRequest(symbol: sym, side: side, quantity: quantity, limitPrice: limitPrice)
                let res = try await api.placeOrder(req)
                snapshot = res.portfolio
                lastTradeMessage = "Order \(res.order.id.uuidString.prefix(8))… \(res.order.status.rawValue)"
            } catch {
                lastTradeMessage = "API: \(error.localizedDescription)"
            }
            return
        }
        await executeLocal(symbol: sym, side: side, quantity: quantity, limitPrice: limitPrice, referencePrice: referencePrice)
    }

    private func executeLocal(symbol: String, side: OrderSide, quantity: Int, limitPrice: Decimal?, referencePrice: Decimal?) async {
        try? await Task.sleep(nanoseconds: 350_000_000)
        let positionPrice = snapshot.positions.first(where: { $0.symbol == symbol })?.currentPrice
        let execPrice = limitPrice ?? referencePrice ?? positionPrice ?? Decimal(100)
        var cash = snapshot.cashBalance
        var positions = snapshot.positions
        var orders = snapshot.orders
        switch side {
        case .buy:
            let cost = execPrice * Decimal(quantity)
            guard cash >= cost else {
                lastTradeMessage = "Insufficient buying power."
                return
            }
            cash -= cost
            if let idx = positions.firstIndex(where: { $0.symbol == symbol }) {
                let p = positions[idx]
                let totalQty = p.quantity + quantity
                let newAvg = (p.averageCost * Decimal(p.quantity) + execPrice * Decimal(quantity)) / Decimal(totalQty)
                positions[idx] = Position(symbol: symbol, quantity: totalQty, averageCost: newAvg, currentPrice: execPrice)
            } else {
                positions.append(Position(symbol: symbol, quantity: quantity, averageCost: execPrice, currentPrice: execPrice))
            }
        case .sell:
            guard let idx = positions.firstIndex(where: { $0.symbol == symbol }), positions[idx].quantity >= quantity else {
                lastTradeMessage = "Cannot sell more than you hold."
                return
            }
            let proceeds = execPrice * Decimal(quantity)
            cash += proceeds
            let newQty = positions[idx].quantity - quantity
            if newQty == 0 {
                positions.remove(at: idx)
            } else {
                positions[idx] = Position(
                    symbol: symbol,
                    quantity: newQty,
                    averageCost: positions[idx].averageCost,
                    currentPrice: execPrice
                )
            }
        }
        let order = TradeOrder(
            id: UUID(),
            symbol: symbol,
            side: side,
            quantity: quantity,
            limitPrice: limitPrice,
            submittedAt: Date(),
            status: .filled,
            filledQuantity: quantity,
            averageFillPrice: execPrice
        )
        orders.insert(order, at: 0)
        snapshot = PortfolioSnapshot(cashBalance: cash, positions: positions, orders: orders)
        lastTradeMessage = "\(side.rawValue.uppercased()) \(quantity) \(symbol) @ \(NSDecimalNumber(decimal: execPrice).stringValue)"
    }
}
