import Foundation

struct Quote: Codable, Hashable {
    let symbol: String
    let price: Decimal
    let change: Decimal
    let changePct: Decimal
    let asOf: Date
}

enum TradeSide: String, Codable, CaseIterable, Identifiable {
    case buy
    case sell
    var id: String { rawValue }
}

enum OrderType: String, Codable, CaseIterable, Identifiable {
    case market
    case limit
    var id: String { rawValue }
}

struct TradeRequest: Codable {
    let symbol: String
    let side: TradeSide
    let quantity: Int
    let orderType: OrderType
    let limitPrice: Decimal?
    let clientOrderId: String
    let timestamp: Date
}

struct TradeFill: Codable, Hashable, Identifiable {
    let id: String
    let symbol: String
    let side: TradeSide
    let quantity: Int
    let price: Decimal
    let executedAt: Date
}

struct Position: Codable, Hashable, Identifiable {
    var id: String { symbol }
    let symbol: String
    var quantity: Int
    var avgCost: Decimal
    var marketPrice: Decimal

    var marketValue: Decimal { Decimal(quantity) * marketPrice }
    var costBasis: Decimal { Decimal(quantity) * avgCost }
    var unrealizedPnL: Decimal { marketValue - costBasis }
}

struct Portfolio: Codable {
    var cash: Decimal
    var positions: [Position]
    var fills: [TradeFill]

    var equity: Decimal {
        positions.reduce(cash) { $0 + $1.marketValue }
    }
}

enum TradingError: Error, LocalizedError {
    case invalidQuantity
    case insufficientFunds
    case insufficientShares
    case invalidLimitPrice
    case network(String)
    case rejected(String)

    var errorDescription: String? {
        switch self {
        case .invalidQuantity:
            return "Quantity must be at least 1."
        case .insufficientFunds:
            return "Insufficient buying power."
        case .insufficientShares:
            return "Insufficient shares to sell."
        case .invalidLimitPrice:
            return "Limit price must be greater than 0."
        case .network(let msg):
            return msg
        case .rejected(let msg):
            return msg
        }
    }
}

extension Decimal {
    func rounded(scale: Int, mode: NSDecimalNumber.RoundingMode = .bankers) -> Decimal {
        var v = self
        var r = Decimal()
        NSDecimalRound(&r, &v, scale, mode)
        return r
    }
}

extension NumberFormatter {
    static let currency2: NumberFormatter = {
        let f = NumberFormatter()
        f.numberStyle = .currency
        f.currencyCode = "USD"
        f.maximumFractionDigits = 2
        f.minimumFractionDigits = 2
        return f
    }()

    static let percent2: NumberFormatter = {
        let f = NumberFormatter()
        f.numberStyle = .percent
        f.maximumFractionDigits = 2
        f.minimumFractionDigits = 2
        return f
    }()

    static let decimal2: NumberFormatter = {
        let f = NumberFormatter()
        f.numberStyle = .decimal
        f.maximumFractionDigits = 2
        f.minimumFractionDigits = 2
        return f
    }()
}

func formatCurrency(_ d: Decimal) -> String {
    NumberFormatter.currency2.string(from: d as NSDecimalNumber) ?? "$0.00"
}

func formatDecimal2(_ d: Decimal) -> String {
    NumberFormatter.decimal2.string(from: d as NSDecimalNumber) ?? "0.00"
}

func formatPct(_ d: Decimal) -> String {
    let n = (d as NSDecimalNumber).doubleValue
    return NumberFormatter.percent2.string(from: NSNumber(value: n)) ?? "0.00%"
}
