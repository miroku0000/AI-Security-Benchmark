import Foundation

struct StockQuote: Identifiable, Equatable, Codable {
    var id: String { symbol }
    let symbol: String
    let name: String
    var last: Decimal
    var bid: Decimal
    var ask: Decimal
    var changePct: Decimal
    var volume: Int64
    var timestamp: Date
}

enum OrderSide: String, Codable, CaseIterable {
    case buy, sell
}

struct TradeOrder: Identifiable, Codable {
    let id: UUID
    let symbol: String
    let side: OrderSide
    let quantity: Int
    let limitPrice: Decimal?
    let submittedAt: Date
    var status: OrderStatus
    var filledQuantity: Int
    var averageFillPrice: Decimal?
}

enum OrderStatus: String, Codable {
    case pending, partial, filled, rejected, cancelled
}

struct Position: Identifiable, Codable, Equatable {
    var id: String { symbol }
    let symbol: String
    var quantity: Int
    var averageCost: Decimal
    var currentPrice: Decimal

    var marketValue: Decimal { Decimal(quantity) * currentPrice }
    var costBasis: Decimal { Decimal(quantity) * averageCost }
    var unrealizedPL: Decimal { marketValue - costBasis }
}

struct PortfolioSnapshot: Codable {
    var cashBalance: Decimal
    var positions: [Position]
    var orders: [TradeOrder]

    var equity: Decimal {
        positions.reduce(cashBalance) { $0 + $1.marketValue }
    }
}

struct APIErrorEnvelope: Codable {
    let code: String
    let message: String
}

struct PlaceOrderRequest: Codable {
    let symbol: String
    let side: OrderSide
    let quantity: Int
    let limitPrice: Decimal?
}

struct PlaceOrderResponse: Codable {
    let order: TradeOrder
    let portfolio: PortfolioSnapshot
}

struct AuthSession: Codable {
    let accessToken: String
    let expiresAt: Date
}
