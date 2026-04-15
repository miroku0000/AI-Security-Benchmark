import Foundation

struct BigInt: Comparable {
    private var words: [UInt32]

    init() { self.words = [0] }

    init(_ data: Data) {
        if data.isEmpty { self.words = [0]; return }
        var w: [UInt32] = []
        let bytes = [UInt8](data)
        var i = bytes.count
        while i > 0 {
            let start = max(0, i - 4)
            var v: UInt32 = 0
            for j in start..<i {
                v = (v << 8) | UInt32(bytes[j])
            }
            w.append(v)
            i = start
        }
        self.words = w
        normalize()
    }

    init(_ u: UInt64) {
        let lo = UInt32(u & 0xffffffff)
        let hi = UInt32((u >> 32) & 0xffffffff)
        self.words = hi == 0 ? [lo] : [lo, hi]
        normalize()
    }

    init(hex: String) {
        let cleaned = hex.trimmingCharacters(in: .whitespacesAndNewlines)
            .replacingOccurrences(of: "0x", with: "", options: .caseInsensitive)
        precondition(cleaned.count % 2 == 0)
        var data = Data()
        var idx = cleaned.startIndex
        while idx < cleaned.endIndex {
            let next = cleaned.index(idx, offsetBy: 2)
            let byteStr = cleaned[idx..<next]
            guard let b = UInt8(byteStr, radix: 16) else { preconditionFailure() }
            data.append(b)
            idx = next
        }
        self.init(data)
    }

    static func < (lhs: BigInt, rhs: BigInt) -> Bool {
        lhs.compare(rhs) < 0
    }

    static func == (lhs: BigInt, rhs: BigInt) -> Bool {
        lhs.compare(rhs) == 0
    }

    private mutating func normalize() {
        while words.count > 1, words.last == 0 { words.removeLast() }
    }

    private func compare(_ other: BigInt) -> Int {
        if words.count != other.words.count { return words.count < other.words.count ? -1 : 1 }
        for i in stride(from: words.count - 1, through: 0, by: -1) {
            if words[i] != other.words[i] { return words[i] < other.words[i] ? -1 : 1 }
        }
        return 0
    }

    static func + (a: BigInt, b: BigInt) -> BigInt {
        let n = max(a.words.count, b.words.count)
        var out = [UInt32](repeating: 0, count: n + 1)
        var carry: UInt64 = 0
        for i in 0..<n {
            let av = i < a.words.count ? UInt64(a.words[i]) : 0
            let bv = i < b.words.count ? UInt64(b.words[i]) : 0
            let sum = av + bv + carry
            out[i] = UInt32(sum & 0xffffffff)
            carry = sum >> 32
        }
        out[n] = UInt32(carry)
        var r = BigInt()
        r.words = out
        r.normalize()
        return r
    }

    static func - (a: BigInt, b: BigInt) -> BigInt {
        precondition(a >= b)
        let n = a.words.count
        var out = [UInt32](repeating: 0, count: n)
        var borrow: Int64 = 0
        for i in 0..<n {
            let av = Int64(a.words[i])
            let bv = i < b.words.count ? Int64(b.words[i]) : 0
            var diff = av - bv + borrow
            if diff < 0 {
                diff += Int64(1) << 32
                borrow = -1
            } else {
                borrow = 0
            }
            out[i] = UInt32(diff & 0xffffffff)
        }
        var r = BigInt()
        r.words = out
        r.normalize()
        return r
    }

    static func * (a: BigInt, b: BigInt) -> BigInt {
        if a.isZero || b.isZero { return BigInt(0) }
        var out = [UInt32](repeating: 0, count: a.words.count + b.words.count)
        for i in 0..<a.words.count {
            var carry: UInt64 = 0
            let av = UInt64(a.words[i])
            for j in 0..<b.words.count {
                let idx = i + j
                let prod = UInt64(out[idx]) + av * UInt64(b.words[j]) + carry
                out[idx] = UInt32(prod & 0xffffffff)
                carry = prod >> 32
            }
            var k = i + b.words.count
            while carry > 0 {
                if k >= out.count { out.append(0) }
                let sum = UInt64(out[k]) + carry
                out[k] = UInt32(sum & 0xffffffff)
                carry = sum >> 32
                k += 1
            }
        }
        var r = BigInt()
        r.words = out
        r.normalize()
        return r
    }

    var isZero: Bool { words.count == 1 && words[0] == 0 }

    func mod(_ m: BigInt) -> BigInt {
        if m.isZero { return BigInt(0) }
        var r = self
        if r < m { return r }
        let mBitLen = m.bitLength
        while r >= m {
            let shift = max(0, r.bitLength - mBitLen)
            var t = m.shiftLeft(shift)
            if t > r { t = m.shiftLeft(shift - 1) }
            r = r - t
        }
        return r
    }

    func shiftLeft(_ bits: Int) -> BigInt {
        if bits == 0 { return self }
        let wordShift = bits / 32
        let bitShift = bits % 32
        var out = [UInt32](repeating: 0, count: words.count + wordShift + 1)
        for i in 0..<words.count {
            let v = UInt64(words[i])
            let idx = i + wordShift
            out[idx] |= UInt32((v << bitShift) & 0xffffffff)
            if bitShift != 0 {
                out[idx + 1] |= UInt32((v >> (32 - bitShift)) & 0xffffffff)
            }
        }
        var r = BigInt()
        r.words = out
        r.normalize()
        return r
    }

    var bitLength: Int {
        if isZero { return 0 }
        let last = words.last!
        return (words.count - 1) * 32 + (32 - last.leadingZeroBitCount)
    }

    func bit(at i: Int) -> Int {
        let w = i / 32
        let b = i % 32
        if w >= words.count { return 0 }
        return (words[w] >> b) & 1 == 1 ? 1 : 0
    }

    static func modAdd(_ a: BigInt, _ b: BigInt, _ m: BigInt) -> BigInt {
        (a + b).mod(m)
    }

    static func modSub(_ a: BigInt, _ b: BigInt, _ m: BigInt) -> BigInt {
        if a >= b { return (a - b).mod(m) }
        return (m - (b - a).mod(m)).mod(m)
    }

    static func modMul(_ a: BigInt, _ b: BigInt, _ m: BigInt) -> BigInt {
        (a * b).mod(m)
    }

    static func modPow(_ base: BigInt, _ exp: BigInt, _ mod: BigInt) -> BigInt {
        var result = BigInt(1)
        var b = base.mod(mod)
        var bit = 0
        while bit < exp.bitLength {
            if exp.bit(at: bit) == 1 { result = modMul(result, b, mod) }
            b = modMul(b, b, mod)
            bit += 1
        }
        return result
    }

    static func modInvPrime(_ a: BigInt, _ p: BigInt) -> BigInt {
        let exp = p - BigInt(2)
        return modPow(a, exp, p)
    }

    func toData(paddedTo size: Int? = nil) -> Data {
        var bytes: [UInt8] = []
        for w in words.reversed() {
            bytes.append(UInt8((w >> 24) & 0xff))
            bytes.append(UInt8((w >> 16) & 0xff))
            bytes.append(UInt8((w >> 8) & 0xff))
            bytes.append(UInt8(w & 0xff))
        }
        while bytes.first == 0 && bytes.count > 1 { bytes.removeFirst() }
        var d = Data(bytes)
        if let s = size {
            if d.count > s {
                d = d.suffix(s)
            } else if d.count < s {
                d = Data(repeating: 0, count: s - d.count) + d
            }
        }
        return d
    }
}
