import CryptoKit
import Foundation
import Security

final class WalletCore {
    static func parseHexBigInt(_ s: String) throws -> BigInt {
        let t = s.trimmingCharacters(in: .whitespacesAndNewlines)
        if t.isEmpty { return BigInt(0) }
        return BigInt(try Hex.data(from: t))
    }

    static func addressBytes20(_ hexAddress: String) throws -> Data {
        let d = try Hex.data(from: hexAddress)
        guard d.count == 20 else { throw WalletError.invalidHex }
        return d
    }

    static func generatePrivateKey() throws -> Data {
        var bytes = [UInt8](repeating: 0, count: 32)
        let status = SecRandomCopyBytes(kSecRandomDefault, bytes.count, &bytes)
        guard status == errSecSuccess else { throw WalletError.keyGenerationFailed }
        let d = Data(bytes)
        let bi = BigInt(d)
        if bi.isZero || bi >= Secp256k1.n { return try generatePrivateKey() }
        return d
    }

    static func ethereumAddress(fromPrivateKey priv: Data) throws -> String {
        let pubUncompressed = try Secp256k1.publicKey(fromPrivateKey32: priv, compressed: false)
        let pub = pubUncompressed.dropFirst()
        let hash = Keccak256.hash(Data(pub))
        let addr = hash.suffix(20)
        return "0x" + Hex.string(from: addr)
    }

    static func personalSign(message: Data, priv: Data) throws -> String {
        let prefix = "\u{19}Ethereum Signed Message:\n\(message.count)"
        let payload = Data(prefix.utf8) + message
        let digest = Keccak256.hash(payload)
        return try signDigest(digest32: digest, priv: priv)
    }

    static func signDigest(digest32: Data, priv: Data) throws -> String {
        guard digest32.count == 32 else { throw WalletError.invalidResponse }
        let (r, s, yParity) = try Secp256k1.sign(priv: priv, msg32: digest32)
        let v = Data([UInt8(27 + yParity)])
        let sig = r + s + v
        return "0x" + Hex.string(from: sig)
    }

    static func signLegacyEIP155Raw(
        nonce: BigInt,
        gasPrice: BigInt,
        gasLimit: BigInt,
        toAddress20: Data,
        value: BigInt,
        data: Data,
        chainId: BigInt,
        priv: Data
    ) throws -> Data {
        guard toAddress20.count == 20 else { throw WalletError.invalidPrivateKey }
        let unsigned: [RLP.Item] = [
            .bytes(RLP.uint256Bytes(nonce)),
            .bytes(RLP.uint256Bytes(gasPrice)),
            .bytes(RLP.uint256Bytes(gasLimit)),
            .bytes(toAddress20),
            .bytes(RLP.uint256Bytes(value)),
            .bytes(data),
            .bytes(RLP.uint256Bytes(chainId)),
            .bytes(Data()),
            .bytes(Data())
        ]
        let unsignedRLP = RLP.encode(.list(unsigned))
        let hash = Keccak256.hash(unsignedRLP)
        let (r, s, yParity) = try Secp256k1.sign(priv: priv, msg32: hash)
        let vNum = chainId * BigInt(2) + BigInt(35) + BigInt(UInt64(yParity))
        let signed: [RLP.Item] = [
            .bytes(RLP.uint256Bytes(nonce)),
            .bytes(RLP.uint256Bytes(gasPrice)),
            .bytes(RLP.uint256Bytes(gasLimit)),
            .bytes(toAddress20),
            .bytes(RLP.uint256Bytes(value)),
            .bytes(data),
            .bytes(RLP.uint256Bytes(vNum)),
            .bytes(RLP.uint256Bytes(BigInt(r))),
            .bytes(RLP.uint256Bytes(BigInt(s)))
        ]
        return RLP.encode(.list(signed))
    }
}
