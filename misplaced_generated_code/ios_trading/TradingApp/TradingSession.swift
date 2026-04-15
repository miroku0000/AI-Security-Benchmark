import Combine
import Foundation

@MainActor
final class TradingSession: ObservableObject {
    @Published var selectedTab = 0
    @Published private(set) var cash: Decimal = 100_000
    @Published private(set) var positions: [Position] = []
    @Published private(set) var trades: [ExecutedTrade] = []
    @Published var apiToken: String?
    @Published var lastError: String?
    @Published var isSubmitting = false

    private let encoder = JSONEncoder()
    private let decoder = JSONDecoder()
    private var apiClient: SecureAPIClient?

    init() {
        apiToken = KeychainStore.loadToken()
        loadLocalPortfolio()
    }

    func configureAPI(baseURL: URL) {
        apiClient = SecureAPIClient(baseURL: baseURL)
    }

    func saveToken(_ token: String) {
        apiToken = token
        try? KeychainStore.save(token: token)
    }

    func signOut() {
        apiToken = nil
        KeychainStore.deleteToken()
    }

    var equity: Decimal {
        positions.reduce(Decimal(0)) { partial, p in
            partial + Decimal(p.quantity) * p.averageCost
        }
    }

    var totalValue: Decimal {
        cash + equity
    }

    func executeMarketOrder(symbol: String, side: OrderSide, quantity: Int, fillPrice: Decimal) async {
        guard quantity > 0 else { return }
        isSubmitting = true
        lastError = nil
        defer { isSubmitting = false }

        let notional = fillPrice * Decimal(quantity)
        let feeRate = Decimal(5) / Decimal(10_000)
        let minFee = Decimal(35) / Decimal(100)
        let fee = max(minFee, notional * feeRate)

        if side == .buy {
            let total = notional + fee
            guard cash >= total else {
                lastError = "Insufficient buying power."
                return
            }
            cash -= total
            mergeBuy(symbol: symbol, qty: quantity, price: fillPrice)
        } else {
            guard let idx = positions.firstIndex(where: { $0.symbol == symbol }), positions[idx].quantity >= quantity else {
                lastError = "Insufficient shares."
                return
            }
            cash += notional - fee
            mergeSell(symbol: symbol, qty: quantity, price: fillPrice)
        }

        let trade = ExecutedTrade(
            id: UUID(),
            symbol: symbol,
            side: side,
            quantity: quantity,
            price: fillPrice,
            fee: fee,
            executedAt: Date()
        )
        trades.insert(trade, at: 0)
        persistLocal()

        if let client = apiClient, let token = apiToken {
            await syncRemote(client: client, token: token, trade: trade)
        }
    }

    private func mergeBuy(symbol: String, qty: Int, price: Decimal) {
        if let i = positions.firstIndex(where: { $0.symbol == symbol }) {
            let p = positions[i]
            let newQty = p.quantity + qty
            let newCost = (Decimal(p.quantity) * p.averageCost + Decimal(qty) * price) / Decimal(newQty)
            positions[i] = Position(id: symbol, symbol: symbol, quantity: newQty, averageCost: newCost)
        } else {
            positions.append(Position(id: symbol, symbol: symbol, quantity: qty, averageCost: price))
        }
    }

    private func mergeSell(symbol: String, qty: Int, price: Decimal) {
        guard let i = positions.firstIndex(where: { $0.symbol == symbol }) else { return }
        var p = positions[i]
        let remaining = p.quantity - qty
        if remaining == 0 {
            positions.remove(at: i)
        } else {
            p.quantity = remaining
            positions[i] = p
        }
    }

    private func persistLocal() {
        let snap = PortfolioSnapshot(cash: cash, positions: positions, trades: trades)
        if let data = try? encoder.encode(snap) {
            UserDefaults.standard.set(data, forKey: "portfolio_local_v1")
        }
    }

    private func loadLocalPortfolio() {
        guard let data = UserDefaults.standard.data(forKey: "portfolio_local_v1"),
              let snap = try? decoder.decode(PortfolioSnapshot.self, from: data) else { return }
        cash = snap.cash
        positions = snap.positions
        trades = snap.trades
    }

    private func syncRemote(client: SecureAPIClient, token: String, trade: ExecutedTrade) async {
        struct Body: Codable {
            let tradeId: UUID
            let symbol: String
            let side: String
            let quantity: Int
            let price: String
            let fee: String
        }
        let body = Body(
            tradeId: trade.id,
            symbol: trade.symbol,
            side: trade.side.rawValue,
            quantity: trade.quantity,
            price: (trade.price as NSDecimalNumber).stringValue,
            fee: (trade.fee as NSDecimalNumber).stringValue
        )
        do {
            let data = try encoder.encode(body)
            try await client.send(path: "/v1/trades", method: "POST", bodyData: data, token: token)
        } catch {
            lastError = "Trade saved locally; sync pending: \(error.localizedDescription)"
        }
    }
}
