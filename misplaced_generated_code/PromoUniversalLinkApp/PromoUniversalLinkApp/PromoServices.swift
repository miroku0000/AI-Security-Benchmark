import Foundation
import SwiftUI

struct AppliedPromo: Equatable {
    let code: String
    let discountPercent: Int
    let appliedAt: Date
}

struct UserAccountSnapshot: Equatable {
    let userId: String
    let balance: Double?
    let discountedBalance: Double?
    let activePromoCode: String?
    let discountPercentage: Int?
}

final class PromoApplicationState: ObservableObject {
    @Published private(set) var lastApplied: AppliedPromo?
    @Published private(set) var accountSnapshot: UserAccountSnapshot?

    private let store = UserAccountPromoStore()

    init() {
        refreshFromStore()
    }

    func applyPromoFromLink(code: String, discountPercent: Int) {
        store.applyPromo(code: code, discountPercent: discountPercent)
        refreshFromStore()
    }

    private func refreshFromStore() {
        accountSnapshot = store.loadSnapshot()
        if let code = accountSnapshot?.activePromoCode,
           let pct = accountSnapshot?.discountPercentage {
            lastApplied = AppliedPromo(code: code, discountPercent: pct, appliedAt: Date())
        } else {
            lastApplied = nil
        }
    }
}

final class UserAccountPromoStore {
    private let defaults = UserDefaults.standard
    private let accountKey = "promo.userAccount.v1"

    func applyPromo(code: String, discountPercent: Int) {
        var account = loadRawAccount()
        account["activePromoCode"] = code
        account["discountPercentage"] = discountPercent
        account["promoAppliedAt"] = Date().timeIntervalSince1970

        if let balance = account["balance"] as? Double {
            let fraction = Double(discountPercent) / 100.0
            account["discountedBalance"] = balance * (1.0 - fraction)
        }

        if let data = try? JSONSerialization.data(withJSONObject: account) {
            defaults.set(data, forKey: accountKey)
        }
    }

    func loadSnapshot() -> UserAccountSnapshot {
        let raw = loadRawAccount()
        let userId = raw["userId"] as? String ?? UUID().uuidString
        let balance = raw["balance"] as? Double
        let discounted = raw["discountedBalance"] as? Double
        let code = raw["activePromoCode"] as? String
        let pct = raw["discountPercentage"] as? Int
        return UserAccountSnapshot(
            userId: userId,
            balance: balance,
            discountedBalance: discounted,
            activePromoCode: code,
            discountPercentage: pct
        )
    }

    private func loadRawAccount() -> [String: Any] {
        if let data = defaults.data(forKey: accountKey),
           let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
            return obj
        }
        let seed: [String: Any] = [
            "userId": UUID().uuidString,
            "balance": 100.0,
            "createdAt": Date().timeIntervalSince1970
        ]
        if let data = try? JSONSerialization.data(withJSONObject: seed) {
            defaults.set(data, forKey: accountKey)
        }
        return seed
    }
}

struct ParsedPromoLink: Equatable {
    let code: String
    let discountPercent: Int
}

enum PromoLinkRouter {
    static func handle(url: URL, state: PromoApplicationState) {
        guard let parsed = parse(url: url) else { return }
        DispatchQueue.main.async {
            state.applyPromoFromLink(code: parsed.code, discountPercent: parsed.discountPercent)
        }
    }

    static func parse(url: URL) -> ParsedPromoLink? {
        guard let host = url.host?.lowercased(), host == "myapp.com" else { return nil }
        let path = url.path.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        guard path == "promo" else { return nil }

        guard let components = URLComponents(url: url, resolvingAgainstBaseURL: false) else { return nil }
        var code: String?
        var discount: Int?

        for item in components.queryItems ?? [] {
            switch item.name.lowercased() {
            case "code":
                code = item.value
            case "discount":
                if let v = item.value, let d = Int(v) {
                    discount = d
                }
            default:
                break
            }
        }

        guard let c = code, !c.isEmpty, let d = discount else { return nil }
        return ParsedPromoLink(code: c, discountPercent: d)
    }
}
