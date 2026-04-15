import CryptoKit
import Foundation

struct Secp256k1 {
    static let p = BigInt(hex: "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F")
    static let n = BigInt(hex: "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141")
    static let Gx = BigInt(hex: "79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798")
    static let Gy = BigInt(hex: "483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8")

    struct Point {
        var x: BigInt
        var y: BigInt
        var infinity: Bool = false
    }

    static func isOnCurve(_ P: Point) -> Bool {
        if P.infinity { return true }
        let y2 = BigInt.modMul(P.y, P.y, p)
        let x2 = BigInt.modMul(P.x, P.x, p)
        let x3 = BigInt.modMul(x2, P.x, p)
        let rhs = BigInt.modAdd(x3, BigInt(7), p)
        return y2 == rhs
    }

    static func pointAdd(_ P: Point, _ Q: Point) -> Point {
        if P.infinity { return Q }
        if Q.infinity { return P }
        if P.x == Q.x {
            if BigInt.modAdd(P.y, Q.y, p).isZero { return Point(x: BigInt(0), y: BigInt(0), infinity: true) }
            return pointDouble(P)
        }
        let num = BigInt.modSub(Q.y, P.y, p)
        let den = BigInt.modSub(Q.x, P.x, p)
        let invDen = BigInt.modInvPrime(den, p)
        let lambda = BigInt.modMul(num, invDen, p)
        let xr = BigInt.modSub(BigInt.modSub(BigInt.modMul(lambda, lambda, p), P.x, p), Q.x, p)
        let yr = BigInt.modSub(BigInt.modMul(lambda, BigInt.modSub(P.x, xr, p), p), P.y, p)
        return Point(x: xr, y: yr, infinity: false)
    }

    static func pointDouble(_ P: Point) -> Point {
        if P.infinity { return P }
        if P.y.isZero { return Point(x: BigInt(0), y: BigInt(0), infinity: true) }
        let num = BigInt.modMul(BigInt(3), BigInt.modMul(P.x, P.x, p), p)
        let den = BigInt.modMul(BigInt(2), P.y, p)
        let invDen = BigInt.modInvPrime(den, p)
        let lambda = BigInt.modMul(num, invDen, p)
        let xr = BigInt.modSub(BigInt.modMul(lambda, lambda, p), BigInt.modMul(BigInt(2), P.x, p), p)
        let yr = BigInt.modSub(BigInt.modMul(lambda, BigInt.modSub(P.x, xr, p), p), P.y, p)
        return Point(x: xr, y: yr, infinity: false)
    }

    static func scalarMult(_ k: BigInt, _ P: Point) -> Point {
        var N = P
        var Q = Point(x: BigInt(0), y: BigInt(0), infinity: true)
        var i = 0
        while i < k.bitLength {
            if k.bit(at: i) == 1 { Q = pointAdd(Q, N) }
            N = pointDouble(N)
            i += 1
        }
        return Q
    }

    static func publicKey(fromPrivateKey32 priv: Data, compressed: Bool) throws -> Data {
        guard priv.count == 32 else { throw WalletError.invalidPrivateKey }
        let d = BigInt(priv)
        if d.isZero || d >= n { throw WalletError.invalidPrivateKey }
        let G = Point(x: Gx, y: Gy, infinity: false)
        let Q = scalarMult(d, G)
        precondition(isOnCurve(Q))
        let x = Q.x.toData(paddedTo: 32)
        let y = Q.y.toData(paddedTo: 32)
        if !compressed {
            return Data([0x04]) + x + y
        } else {
            let prefix: UInt8 = (Q.y.toData(paddedTo: 32).last! & 1) == 0 ? 0x02 : 0x03
            return Data([prefix]) + x
        }
    }

    static func deterministicK(priv: Data, msg32: Data) -> BigInt {
        let x = priv
        let h1 = msg32
        var V = Data(repeating: 0x01, count: 32)
        var K = Data(repeating: 0x00, count: 32)

        func hmac(_ key: Data, _ data: Data) -> Data {
            let sk = SymmetricKey(data: key)
            let mac = HMAC<SHA256>.authenticationCode(for: data, using: sk)
            return Data(mac)
        }

        K = hmac(K, V + Data([0x00]) + x + h1)
        V = hmac(K, V)
        K = hmac(K, V + Data([0x01]) + x + h1)
        V = hmac(K, V)

        while true {
            V = hmac(K, V)
            let T = V
            var k = BigInt(T)
            k = k.mod(n)
            if !k.isZero { return k }
            K = hmac(K, V + Data([0x00]))
            V = hmac(K, V)
        }
    }

    static func sign(priv: Data, msg32: Data) throws -> (r: Data, s: Data, yParity: UInt8) {
        guard priv.count == 32, msg32.count == 32 else { throw WalletError.invalidPrivateKey }
        let d = BigInt(priv)
        if d.isZero || d >= n { throw WalletError.invalidPrivateKey }

        let z = BigInt(msg32)
        let G = Point(x: Gx, y: Gy, infinity: false)

        let k = deterministicK(priv: priv, msg32: msg32)
        let R = scalarMult(k, G)
        let rBI = R.x.mod(n)
        if rBI.isZero { throw WalletError.keyGenerationFailed }
        let kInv = BigInt.modInvPrime(k, n)
        var sBI = BigInt.modMul(kInv, BigInt.modAdd(z, BigInt.modMul(rBI, d, n), n), n)
        if sBI.isZero { throw WalletError.keyGenerationFailed }

        let nMinusS = n - sBI
        if sBI > nMinusS { sBI = nMinusS }

        let r = rBI.toData(paddedTo: 32)
        let s = sBI.toData(paddedTo: 32)

        let yIsOdd = (R.y.toData(paddedTo: 32).last! & 1) == 1
        let parity: UInt8 = yIsOdd ? 1 : 0
        return (r, s, parity)
    }
}
