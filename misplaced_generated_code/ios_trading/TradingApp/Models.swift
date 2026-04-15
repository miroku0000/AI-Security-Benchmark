import Foundation

struct StockQuote: Identifiable, Codable, Equatable {
    let id: String
    var symbol: String
    var name: String
    var last: Decimal
    var bid: Decimal
    var ask: Decimal
    var changePct: Double
    var volume: Int64
    var updatedAt: Date

    var mid: Decimal { (bid + ask) / 2 }
}

enum OrderSide: String, Codable, CaseIterable {
    case buy = "BUY"
    case sell = "SELL"
}

struct OrderRequest: Codable {
    let symbol: String
    let side: OrderSide
    let quantity: Int
    let orderType: String
}

struct ExecutedTrade: Identifiable, Codable, Equatable {
    let id: UUID
    let symbol: String
    let side: OrderSide
    let quantity: Int
    let price: Decimal
    let fee: Decimal
    let executedAt: Date
}

struct Position: Identifiable, Codable, Equatable {
    let id: String
    var symbol: String
    var quantity: Int
    var averageCost: Decimal
}

struct PortfolioSnapshot: Codable {
    var cash: Decimal
    var positions: [Position]
    var trades: [ExecutedTrade]
}
