import Foundation

enum RLP {
    enum Item {
        case bytes(Data)
        case list([Item])
    }

    static func encode(_ item: Item) -> Data {
        switch item {
        case .bytes(let b):
            return encodeBytes(b)
        case .list(let items):
            let payload = items.map { encode($0) }.reduce(Data(), +)
            if payload.count < 56 {
                return Data([0xc0 + UInt8(payload.count)]) + payload
            }
            let lenB = bigEndianLength(payload.count)
            return Data([0xf7 + UInt8(lenB.count)]) + lenB + payload
        }
    }

    private static func encodeBytes(_ bytes: Data) -> Data {
        if bytes.count == 1 && bytes[0] < 0x80 {
            return bytes
        }
        if bytes.count < 56 {
            return Data([0x80 + UInt8(bytes.count)]) + bytes
        }
        let lenB = bigEndianLength(bytes.count)
        return Data([0xb7 + UInt8(lenB.count)]) + lenB + bytes
    }

    private static func bigEndianLength(_ n: Int) -> Data {
        precondition(n > 0)
        var v = n
        var out = [UInt8]()
        while v > 0 {
            out.insert(UInt8(v & 0xff), at: 0)
            v >>= 8
        }
        return Data(out)
    }

    static func uint256Bytes(_ value: BigInt) -> Data {
        if value.isZero { return Data() }
        return value.toData(paddedTo: nil)
    }
}
