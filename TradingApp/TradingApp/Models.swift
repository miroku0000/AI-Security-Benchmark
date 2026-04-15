import Foundation

enum OrderSide: String, Codable, CaseIterable, Sendable {
    case buy
    case sell
}

struct Quote: Identifiable, Codable, Hashable, Sendable {
    var id: String { symbol }
    var symbol: String
    var name: String
    var price: Decimal
    var changePct: Decimal
    var volume: Int64
    var timestamp: Date
}

struct Holding: Identifiable, Codable, Hashable, Sendable {
    var id: String { symbol }
    var symbol: String
    var quantity: Decimal
    var averageCost: Decimal
    var lastPrice: Decimal

    var marketValue: Decimal { quantity * lastPrice }
    var costBasis: Decimal { quantity * averageCost }
    var unrealizedPL: Decimal { marketValue - costBasis }
}

struct OrderRequest: Codable, Sendable {
    var symbol: String
    var side: OrderSide
    var quantity: Decimal
    var orderType: String
}

struct Execution: Identifiable, Codable, Hashable, Sendable {
    var id: String
    var symbol: String
    var side: OrderSide
    var quantity: Decimal
    var price: Decimal
    var executedAt: Date
}

struct PortfolioSnapshot: Codable, Sendable {
    var cashBalance: Decimal
    var holdings: [Holding]
    var recentExecutions: [Execution]
}

struct APIEnvelope<T: Codable & Sendable>: Codable, Sendable {
    var ok: Bool
    var data: T?
    var error: String?
}
