import Foundation

enum MockTradingBackend {
    private static var quotes: [String: Quote] = [
        "AAPL": Quote(symbol: "AAPL", name: "Apple Inc.", price: 198.50, changePct: 0.012, volume: 52_000_000, timestamp: Date()),
        "MSFT": Quote(symbol: "MSFT", name: "Microsoft", price: 415.20, changePct: -0.004, volume: 21_000_000, timestamp: Date()),
        "NVDA": Quote(symbol: "NVDA", name: "NVIDIA", price: 892.10, changePct: 0.028, volume: 48_000_000, timestamp: Date()),
        "GOOGL": Quote(symbol: "GOOGL", name: "Alphabet", price: 168.40, changePct: 0.001, volume: 18_000_000, timestamp: Date())
    ]

    private static var cash: Decimal = 100_000
    private static var holdings: [String: Holding] = [
        "AAPL": Holding(symbol: "AAPL", quantity: 10, averageCost: 185, lastPrice: quotes["AAPL"]!.price)
    ]
    private static var executions: [Execution] = []
    private static let lock = NSLock()

    static func snapshot() -> PortfolioSnapshot {
        lock.lock()
        defer { lock.unlock() }
        refreshHoldingPrices()
        return PortfolioSnapshot(cashBalance: cash, holdings: Array(holdings.values).sorted { $0.symbol < $1.symbol }, recentExecutions: Array(executions.suffix(50).reversed()))
    }

    static func quotes(for symbols: [String]) -> [Quote] {
        lock.lock()
        defer { lock.unlock() }
        symbols.map { s in
            var q = quotes[s.uppercased()] ?? Quote(symbol: s.uppercased(), name: s.uppercased(), price: 100, changePct: 0, volume: 1_000_000, timestamp: Date())
            q.timestamp = Date()
            quotes[s.uppercased()] = q
            return q
        }
    }

    static func tickPrices() {
        lock.lock()
        defer { lock.unlock() }
        for (sym, var q) in quotes {
            let jitter = Decimal(Double.random(in: -0.002 ... 0.002))
            q.price = max(1, q.price * (1 + jitter))
            q.changePct += Decimal(Double.random(in: -0.0005 ... 0.0005))
            q.timestamp = Date()
            quotes[sym] = q
        }
        refreshHoldingPrices()
    }

    private static func refreshHoldingPrices() {
        for (sym, var h) in holdings {
            if let q = quotes[sym] {
                h.lastPrice = q.price
                holdings[sym] = h
            }
        }
    }

    static func execute(_ order: OrderRequest) throws -> Execution {
        lock.lock()
        defer { lock.unlock() }
        let sym = order.symbol.uppercased()
        guard let q = quotes[sym] else {
            throw NSError(domain: "MockTrading", code: 1, userInfo: [NSLocalizedDescriptionKey: "Unknown symbol"])
        }
        let px = q.price
        let qty = order.quantity
        let notional = qty * px

        switch order.side {
        case .buy:
            guard cash >= notional else {
                throw NSError(domain: "MockTrading", code: 2, userInfo: [NSLocalizedDescriptionKey: "Insufficient cash"])
            }
            cash -= notional
            if var h = holdings[sym] {
                let totalQty = h.quantity + qty
                let newAvg = (h.averageCost * h.quantity + px * qty) / totalQty
                h.quantity = totalQty
                h.averageCost = newAvg
                h.lastPrice = px
                holdings[sym] = h
            } else {
                holdings[sym] = Holding(symbol: sym, quantity: qty, averageCost: px, lastPrice: px)
            }
        case .sell:
            guard var h = holdings[sym], h.quantity >= qty else {
                throw NSError(domain: "MockTrading", code: 3, userInfo: [NSLocalizedDescriptionKey: "Insufficient shares"])
            }
            cash += notional
            h.quantity -= qty
            h.lastPrice = px
            if h.quantity == 0 {
                holdings.removeValue(forKey: sym)
            } else {
                holdings[sym] = h
            }
        }

        let exec = Execution(id: UUID().uuidString, symbol: sym, side: order.side, quantity: qty, price: px, executedAt: Date())
        executions.append(exec)
        return exec
    }
}
