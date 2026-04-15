import Foundation
import Observation

@Observable
@MainActor
final class TradingStore {
    var quotes: [Quote] = []
    var portfolio: PortfolioSnapshot = .init(cashBalance: 0, holdings: [], recentExecutions: [])
    var isLiveAPI: Bool { CredentialStore.baseURLString().flatMap(URL.init(string:)) != nil }
    var lastError: String?
    var isBusy: Bool = false

    private var apiClient: TradingAPIClient = TradingStore.makeAPIClient()
    private var quoteTask: Task<Void, Never>?
    private let watchSymbols = ["AAPL", "MSFT", "NVDA", "GOOGL"]

    init() {
        reloadFromMock()
        startRealtimeLoop()
    }

    deinit {
        quoteTask?.cancel()
    }

    func refreshCredentials() {
        replaceAPIClient(Self.makeAPIClient())
    }

    func replaceAPIClient(_ client: TradingAPIClient) {
        apiClient = client
    }

    private static func makeAPIClient() -> TradingAPIClient {
        let url = CredentialStore.baseURLString().flatMap(URL.init(string:))
        let raw = UserDefaults.standard.string(forKey: "trading_spki_pins") ?? ""
        let pins: Set<String> = Set(
            raw.split(separator: ",").map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }.filter { $0.isEmpty == false }
        )
        return TradingAPIClient(baseURL: url, pinnedSPKIHashes: pins)
    }

    func reloadFromMock() {
        portfolio = MockTradingBackend.snapshot()
        quotes = MockTradingBackend.quotes(for: watchSymbols)
    }

    func refreshAll() async {
        isBusy = true
        lastError = nil
        defer { isBusy = false }
        if isLiveAPI {
            do {
                let token = CredentialStore.bearerToken()
                async let p = try await apiClient.fetchPortfolio(token: token)
                async let q = try await apiClient.fetchQuotes(symbols: watchSymbols, token: token)
                portfolio = try await p
                quotes = try await q
            } catch {
                lastError = error.localizedDescription
                reloadFromMock()
            }
        } else {
            reloadFromMock()
        }
    }

    func placeOrder(symbol: String, side: OrderSide, quantity: Decimal) async -> Execution? {
        isBusy = true
        lastError = nil
        defer { isBusy = false }
        let req = OrderRequest(symbol: symbol, side: side, quantity: quantity, orderType: "market")
        if isLiveAPI {
            do {
                let exec = try await apiClient.placeOrder(req, token: CredentialStore.bearerToken())
                await refreshAll()
                return exec
            } catch {
                lastError = error.localizedDescription
                return nil
            }
        } else {
            do {
                let exec = try MockTradingBackend.execute(req)
                reloadFromMock()
                return exec
            } catch {
                lastError = error.localizedDescription
                return nil
            }
        }
    }

    private func startRealtimeLoop() {
        quoteTask?.cancel()
        quoteTask = Task { [weak self] in
            while !Task.isCancelled {
                try? await Task.sleep(nanoseconds: 1_200_000_000)
                await MainActor.run {
                    guard let self else { return }
                    if self.isLiveAPI {
                        Task { await self.refreshQuotesOnly() }
                    } else {
                        MockTradingBackend.tickPrices()
                        self.reloadFromMock()
                    }
                }
            }
        }
    }

    private func refreshQuotesOnly() async {
        guard isLiveAPI else { return }
        do {
            quotes = try await apiClient.fetchQuotes(symbols: watchSymbols, token: CredentialStore.bearerToken())
        } catch {
            lastError = error.localizedDescription
        }
    }
}
