import Foundation
import Observation

@Observable
@MainActor
final class TradingEngine {
    var instruments: [Instrument] = []
    var cash: Decimal = 100_000
    var positions: [Position] = []
    var orders: [ExecutedOrder] = []
    var isSubmitting = false
    var lastError: String?
    var sessionTokenSet = false

    private let quotes = RealtimeQuoteService()
    private let api = SecureAPIClient()
    private let watchlist = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]

    init() {
        Task { await bootstrap() }
    }

    private func bootstrap() async {
        if (try? KeychainService.read(account: AppConfiguration.keychainTokenAccount)) != nil {
            sessionTokenSet = true
        }
        if let base = AppConfiguration.apiBaseURL {
            do {
                let snap = try await api.fetchPortfolio(base: base)
                applyRemote(snap)
            } catch {
                seedLocal()
            }
        } else {
            seedLocal()
        }
        quotes.start(symbols: watchlist) { [weak self] list in
            Task { @MainActor in
                self?.mergeQuotes(list)
            }
        }
    }

    private func seedLocal() {
        instruments = watchlist.map { sym in
            let p = Decimal(Double.random(in: 80...400))
            return Instrument(id: sym, symbol: sym, name: sym, last: p, changePct: 0, bid: p - 0.02, ask: p + 0.02)
        }
    }

    private func applyRemote(_ snap: PortfolioSnapshot) {
        cash = snap.cash
        positions = snap.positions
        recalcEquity()
    }

    private func mergeQuotes(_ list: [Instrument]) {
        instruments = list
        positions = positions.map { pos in
            let px = list.first { $0.symbol == pos.symbol }?.last ?? pos.lastPrice
            return Position(symbol: pos.symbol, quantity: pos.quantity, averageCost: pos.averageCost, lastPrice: px)
        }
    }

    private func recalcEquity() {
        _ = positions.reduce(cash) { $0 + $1.marketValue }
    }

    func setSessionToken(_ token: String) throws {
        guard let d = token.data(using: .utf8) else { return }
        try KeychainService.save(d, account: AppConfiguration.keychainTokenAccount)
        sessionTokenSet = true
    }

    func signOut() {
        KeychainService.delete(account: AppConfiguration.keychainTokenAccount)
        sessionTokenSet = false
    }

    func execute(symbol: String, side: OrderSide, quantity: Decimal, limit: Decimal?) async {
        guard quantity > 0 else {
            lastError = "Invalid quantity"
            return
        }
        isSubmitting = true
        lastError = nil
        defer { isSubmitting = false }

        guard let inst = instruments.first(where: { $0.symbol == symbol }) else {
            lastError = "Unknown symbol"
            return
        }

        let fill = limit ?? inst.last

        if let base = AppConfiguration.apiBaseURL {
            do {
                let ticket = OrderTicket(symbol: symbol, side: side, quantity: quantity, orderType: limit == nil ? "market" : "limit", limitPrice: limit)
                let ex = try await api.submitOrder(base: base, ticket: ticket)
                orders.insert(ex, at: 0)
                await refreshFromRemote(base: base)
            } catch {
                lastError = "Order failed"
            }
            return
        }

        switch side {
        case .buy:
            let cost = fill * quantity
            guard cash >= cost else {
                lastError = "Insufficient buying power"
                return
            }
            cash -= cost
            upsertPosition(symbol: symbol, deltaQty: quantity, tradePrice: fill)
        case .sell:
            guard let pos = positions.first(where: { $0.symbol == symbol }), pos.quantity >= quantity else {
                lastError = "Insufficient shares"
                return
            }
            cash += fill * quantity
            upsertPosition(symbol: symbol, deltaQty: -quantity, tradePrice: fill)
        }

        let ex = ExecutedOrder(id: UUID(), symbol: symbol, side: side, quantity: quantity, fillPrice: fill, timestamp: Date())
        orders.insert(ex, at: 0)
        recalcEquity()
    }

    private func upsertPosition(symbol: String, deltaQty: Decimal, tradePrice: Decimal) {
        if let idx = positions.firstIndex(where: { $0.symbol == symbol }) {
            var p = positions[idx]
            let newQ = p.quantity + deltaQty
            if newQ <= 0 {
                positions.remove(at: idx)
            } else if deltaQty > 0 {
                let totalCost = p.averageCost * p.quantity + tradePrice * deltaQty
                p.quantity = newQ
                p.averageCost = totalCost / newQ
                p.lastPrice = instruments.first { $0.symbol == symbol }?.last ?? tradePrice
                positions[idx] = p
            } else {
                p.quantity = newQ
                p.lastPrice = instruments.first { $0.symbol == symbol }?.last ?? tradePrice
                positions[idx] = p
            }
        } else if deltaQty > 0 {
            let lp = instruments.first { $0.symbol == symbol }?.last ?? tradePrice
            positions.append(Position(symbol: symbol, quantity: deltaQty, averageCost: tradePrice, lastPrice: lp))
        }
    }

    private func refreshFromRemote(base: URL) async {
        if let snap = try? await api.fetchPortfolio(base: base) {
            applyRemote(snap)
        }
    }

    var equity: Decimal {
        positions.reduce(cash) { $0 + $1.marketValue }
    }
}
