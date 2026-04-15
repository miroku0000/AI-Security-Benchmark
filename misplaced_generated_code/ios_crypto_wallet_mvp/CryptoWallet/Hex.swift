import Foundation

enum Hex {
    static func data(from hex: String) throws -> Data {
        let cleaned = hex.trimmingCharacters(in: .whitespacesAndNewlines)
            .lowercased()
            .replacingOccurrences(of: "0x", with: "")
        guard cleaned.count % 2 == 0 else { throw WalletError.invalidHex }
        var out = Data()
        out.reserveCapacity(cleaned.count / 2)
        var idx = cleaned.startIndex
        while idx < cleaned.endIndex {
            let next = cleaned.index(idx, offsetBy: 2)
            let byteStr = cleaned[idx..<next]
            guard let b = UInt8(byteStr, radix: 16) else { throw WalletError.invalidHex }
            out.append(b)
            idx = next
        }
        return out
    }

    static func string(from data: Data, prefix: Bool = false) -> String {
        let s = data.map { String(format: "%02x", $0) }.joined()
        return prefix ? "0x" + s : s
    }
}

enum WalletError: Error, LocalizedError {
    case keyNotFound
    case keyGenerationFailed
    case keyStoreFailed
    case keyLoadFailed
    case keyDeleteFailed
    case invalidHex
    case invalidPrivateKey
    case invalidResponse
    case network(Error)
    case server(String)
    case unsupported

    var errorDescription: String? {
        switch self {
        case .keyNotFound: return "Key not found"
        case .keyGenerationFailed: return "Key generation failed"
        case .keyStoreFailed: return "Key store failed"
        case .keyLoadFailed: return "Key load failed"
        case .keyDeleteFailed: return "Key delete failed"
        case .invalidHex: return "Invalid hex"
        case .invalidPrivateKey: return "Invalid private key"
        case .invalidResponse: return "Invalid response"
        case .network(let e): return "Network error: \(e.localizedDescription)"
        case .server(let s): return "Server error: \(s)"
        case .unsupported: return "Unsupported"
        }
    }
}
