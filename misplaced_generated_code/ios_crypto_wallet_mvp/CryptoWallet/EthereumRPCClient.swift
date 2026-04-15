import Foundation

final class EthereumRPCClient {
    let url: URL
    init(rpcURL: URL) { self.url = rpcURL }

    private func rpcCall<T: Decodable>(method: String, params: [Any], result: T.Type) async throws -> T {
        let body: [String: Any] = [
            "jsonrpc": "2.0",
            "id": Int.random(in: 1...1_000_000),
            "method": method,
            "params": params
        ]
        let data = try JSONSerialization.data(withJSONObject: body)
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = data
        do {
            let (respData, resp) = try await URLSession.shared.data(for: request)
            guard let http = resp as? HTTPURLResponse, (200...299).contains(http.statusCode) else {
                throw WalletError.invalidResponse
            }
            let obj = try JSONSerialization.jsonObject(with: respData) as? [String: Any]
            guard let o = obj else { throw WalletError.invalidResponse }
            if let err = o["error"] as? [String: Any], let msg = err["message"] as? String {
                throw WalletError.server(msg)
            }
            guard let res = o["result"] else { throw WalletError.invalidResponse }
            return try decodeResult(res, as: T.self)
        } catch let e as WalletError {
            throw e
        } catch {
            throw WalletError.network(error)
        }
    }

    private func decodeResult<T: Decodable>(_ value: Any, as _: T.Type) throws -> T {
        if T.self == String.self, let s = value as? String {
            return s as! T
        }
        let data = try JSONSerialization.data(withJSONObject: value)
        return try JSONDecoder().decode(T.self, from: data)
    }

    func chainId() async throws -> String {
        try await rpcCall(method: "eth_chainId", params: [], result: String.self)
    }

    func getBalance(address: String, block: String = "latest") async throws -> String {
        try await rpcCall(method: "eth_getBalance", params: [address, block], result: String.self)
    }

    func getTransactionCount(address: String, block: String = "latest") async throws -> String {
        try await rpcCall(method: "eth_getTransactionCount", params: [address, block], result: String.self)
    }

    func gasPrice() async throws -> String {
        try await rpcCall(method: "eth_gasPrice", params: [], result: String.self)
    }

    func sendRawTransaction(_ rawTxHex: String) async throws -> String {
        try await rpcCall(method: "eth_sendRawTransaction", params: [rawTxHex], result: String.self)
    }
}
