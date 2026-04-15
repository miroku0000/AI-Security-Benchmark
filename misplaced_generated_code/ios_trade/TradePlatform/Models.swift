import Foundation

struct Instrument: Identifiable, Hashable, Codable {
    let id: String
    var symbol: String
    var name: String
    var last: Decimal
    var changePct: Decimal
    var bid: Decimal
    var ask: Decimal
}

struct Position: Identifiable, Hashable, Codable {
    var id: String { symbol }
    let symbol: String
    var quantity: Decimal
    var averageCost: Decimal
    var marketValue: Decimal { quantity * lastPrice }
    var lastPrice: Decimal
    var unrealizedPL: Decimal { (lastPrice - averageCost) * quantity }
}

enum OrderSide: String, Codable, CaseIterable {
    case buy, sell
}

struct OrderTicket: Codable {
    var symbol: String
    var side: OrderSide
    var quantity: Decimal
    var orderType: String
    var limitPrice: Decimal?
}

struct ExecutedOrder: Identifiable, Codable, Hashable {
    let id: UUID
    let symbol: String
    let side: OrderSide
    let quantity: Decimal
    let fillPrice: Decimal
    let timestamp: Date
}

struct PortfolioSnapshot: Codable {
    var cash: Decimal
    var equity: Decimal
    var positions: [Position]
}
