import Foundation

enum Keccak256 {
    static func hash(_ data: Data) -> Data {
        var keccak = Keccak(rate: 1088, capacity: 512, outputLength: 32, delimitedSuffix: 0x01)
        keccak.absorb(data)
        return keccak.squeeze()
    }

    struct Keccak {
        let rate: Int
        let capacity: Int
        let outputLength: Int
        let delimitedSuffix: UInt8

        var state: [UInt64] = Array(repeating: 0, count: 25)
        var buffer = Data()
        var finalized = false

        init(rate: Int, capacity: Int, outputLength: Int, delimitedSuffix: UInt8) {
            self.rate = rate
            self.capacity = capacity
            self.outputLength = outputLength
            self.delimitedSuffix = delimitedSuffix
        }

        mutating func absorb(_ data: Data) {
            precondition(!finalized)
            buffer.append(data)
            let rateBytes = rate / 8
            while buffer.count >= rateBytes {
                let block = buffer.prefix(rateBytes)
                buffer.removeFirst(rateBytes)
                xorBlock(block)
                keccakF()
            }
        }

        mutating func squeeze() -> Data {
            if !finalized { finalize() }
            let rateBytes = rate / 8
            var out = Data()
            while out.count < outputLength {
                let block = extractBlock(rateBytes)
                out.append(block.prefix(min(rateBytes, outputLength - out.count)))
                if out.count < outputLength { keccakF() }
            }
            return out
        }

        mutating func finalize() {
            precondition(!finalized)
            let rateBytes = rate / 8
            var pad = Data(buffer)
            pad.append(delimitedSuffix)
            if (delimitedSuffix & 0x80) != 0 && pad.count == rateBytes {
                xorBlock(pad)
                keccakF()
                pad.removeAll(keepingCapacity: true)
            }
            if pad.count < rateBytes {
                pad.append(Data(repeating: 0, count: rateBytes - pad.count))
            }
            pad[rateBytes - 1] ^= 0x80
            xorBlock(pad)
            keccakF()
            buffer.removeAll(keepingCapacity: true)
            finalized = true
        }

        mutating func xorBlock(_ block: Data) {
            let rateWords = rate / 64
            for i in 0..<rateWords {
                let start = i * 8
                let w = block.withUnsafeBytes { ptr -> UInt64 in
                    let b = ptr.bindMemory(to: UInt8.self)
                    var v: UInt64 = 0
                    for j in 0..<8 { v |= UInt64(b[start + j]) << (8 * j) }
                    return v
                }
                state[i] ^= w
            }
        }

        func extractBlock(_ count: Int) -> Data {
            var out = Data(count: count)
            out.withUnsafeMutableBytes { (ptr: UnsafeMutableRawBufferPointer) in
                let b = ptr.bindMemory(to: UInt8.self)
                let rateWords = count / 8
                for i in 0..<rateWords {
                    let w = state[i]
                    let start = i * 8
                    for j in 0..<8 { b[start + j] = UInt8((w >> (8 * j)) & 0xff) }
                }
            }
            return out
        }

        mutating func keccakF() {
            var A = state
            let R: [[Int]] = [
                [0, 36, 3, 41, 18],
                [1, 44, 10, 45, 2],
                [62, 6, 43, 15, 61],
                [28, 55, 25, 21, 56],
                [27, 20, 39, 8, 14]
            ]
            let RC: [UInt64] = [
                0x0000000000000001, 0x0000000000008082, 0x800000000000808A, 0x8000000080008000,
                0x000000000000808B, 0x0000000080000001, 0x8000000080008081, 0x8000000000008009,
                0x000000000000008A, 0x0000000000000088, 0x0000000080008009, 0x000000008000000A,
                0x000000008000808B, 0x800000000000008B, 0x8000000000008089, 0x8000000000008003,
                0x8000000000008002, 0x8000000000000080, 0x000000000000800A, 0x800000008000000A,
                0x8000000080008081, 0x8000000000008080, 0x0000000080000001, 0x8000000080008008
            ]

            func rotl(_ x: UInt64, _ n: Int) -> UInt64 {
                (x << n) | (x >> (64 - n))
            }

            for round in 0..<24 {
                var C = [UInt64](repeating: 0, count: 5)
                for x in 0..<5 {
                    C[x] = A[x] ^ A[x + 5] ^ A[x + 10] ^ A[x + 15] ^ A[x + 20]
                }
                var D = [UInt64](repeating: 0, count: 5)
                for x in 0..<5 {
                    D[x] = C[(x + 4) % 5] ^ rotl(C[(x + 1) % 5], 1)
                }
                for x in 0..<5 {
                    for y in 0..<5 {
                        A[x + 5 * y] ^= D[x]
                    }
                }

                var B = [UInt64](repeating: 0, count: 25)
                for x in 0..<5 {
                    for y in 0..<5 {
                        let v = A[x + 5 * y]
                        let nx = y
                        let ny = (2 * x + 3 * y) % 5
                        B[nx + 5 * ny] = rotl(v, R[x][y])
                    }
                }

                for x in 0..<5 {
                    for y in 0..<5 {
                        A[x + 5 * y] = B[x + 5 * y] ^ ((~B[((x + 1) % 5) + 5 * y]) & B[((x + 2) % 5) + 5 * y])
                    }
                }

                A[0] ^= RC[round]
            }

            state = A
        }
    }
}
