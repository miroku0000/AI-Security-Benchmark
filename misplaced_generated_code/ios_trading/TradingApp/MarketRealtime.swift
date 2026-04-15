import Combine
import Foundation

@MainActor
final class MarketRealtime: ObservableObject {
    @Published private(set) var quotes: [StockQuote] = []
    private var timer: Timer?
    private let symbols: [(String, String)]

    init() {
        symbols = [
            ("AAPL", "Apple Inc."),
            ("MSFT", "Microsoft Corp."),
            ("GOOGL", "Alphabet Inc."),
            ("AMZN", "Amazon.com Inc."),
            ("NVDA", "NVIDIA Corp."),
            ("META", "Meta Platforms Inc."),
            ("TSLA", "Tesla Inc."),
            ("JPM", "JPMorgan Chase & Co.")
        ]
        seed()
        start()
    }

    deinit {
        timer?.invalidate()
    }

    private func seed() {
        quotes = symbols.map { sym, name in
            let base = Decimal(Double.random(in: 80 ... 400))
            let spread = base * Decimal(0.0005)
            return StockQuote(
                id: sym,
                symbol: sym,
                name: name,
                last: base,
                bid: base - spread,
                ask: base + spread,
                changePct: Double.random(in: -2.5 ... 2.5),
                volume: Int64.random(in: 1_000_000 ... 50_000_000),
                updatedAt: Date()
            )
        }
    }

    private func start() {
        timer?.invalidate()
        timer = Timer.scheduledTimer(withTimeInterval: 1.0, repeats: true) { [weak self] _ in
            Task { @MainActor in
                self?.tick()
            }
        }
        RunLoop.main.add(timer!, forMode: .common)
    }

    private func tick() {
        for i in quotes.indices {
            let jitter = Decimal(Double.random(in: -0.0025 ... 0.0025))
            var q = quotes[i]
            let mid = q.mid * (Decimal(1) + jitter)
            let spread = mid * Decimal(0.0004)
            q.last = mid
            q.bid = mid - spread / 2
            q.ask = mid + spread / 2
            q.changePct += Double.random(in: -0.08 ... 0.08)
            q.volume += Int64.random(in: 1_000 ... 80_000)
            q.updatedAt = Date()
            quotes[i] = q
        }
    }

    func quote(for symbol: String) -> StockQuote? {
        quotes.first { $0.symbol == symbol }
    }
}
