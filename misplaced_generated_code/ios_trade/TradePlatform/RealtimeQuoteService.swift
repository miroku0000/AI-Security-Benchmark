import Foundation

@MainActor
final class RealtimeQuoteService: NSObject {
    private var webSocket: URLSessionWebSocketTask?
    private var session: URLSession!
    private var tickTimer: Timer?
    private var onTick: (([String: Decimal]) -> Void)?

    func start(symbols: [String], onUpdate: @escaping ([Instrument]) -> Void) {
        stop()
        var map: [String: Instrument] = Dictionary(uniqueKeysWithValues: symbols.map { sym in
            let base = Decimal(Double.random(in: 50...500))
            (sym, Instrument(id: sym, symbol: sym, name: sym, last: base, changePct: 0, bid: base - 0.01, ask: base + 0.01))
        })

        onTick = { deltas in
            for (k, v) in deltas {
                guard var i = map[k] else { continue }
                let nl = max(Decimal(0.01), i.last + v)
                let ch = (nl - i.last) / max(i.last, 0.01) * 100
                i.last = nl
                i.changePct = ch
                i.bid = nl - Decimal(0.01)
                i.ask = nl + Decimal(0.01)
                map[k] = i
            }
            onUpdate(Array(map.values).sorted { $0.symbol < $1.symbol })
        }

        if let wsURL = AppConfiguration.websocketURL {
            let cfg = URLSessionConfiguration.default
            session = URLSession(configuration: cfg, delegate: self, delegateQueue: .main)
            webSocket = session.webSocketTask(with: wsURL)
            webSocket?.resume()
            receiveLoop()
        }

        tickTimer = Timer.scheduledTimer(withTimeInterval: 0.35, repeats: true) { [weak self] _ in
            guard let self else { return }
            var d: [String: Decimal] = [:]
            for sym in symbols {
                let jitter = Decimal(Double.random(in: -0.35...0.35))
                d[sym] = jitter
            }
            Task { @MainActor in
                self.onTick?(d)
            }
        }
        RunLoop.main.add(tickTimer!, forMode: .common)
        onUpdate(Array(map.values).sorted { $0.symbol < $1.symbol })
    }

    func stop() {
        tickTimer?.invalidate()
        tickTimer = nil
        webSocket?.cancel(with: .goingAway, reason: nil)
        webSocket = nil
        onTick = nil
    }

    private func receiveLoop() {
        webSocket?.receive { [weak self] result in
            guard let self else { return }
            switch result {
            case .success(let message):
                if case .string(let text) = message, let data = text.data(using: .utf8),
                   let arr = try? JSONDecoder().decode([Instrument].self, from: data) {
                    Task { @MainActor in
                        // Remote snapshot replaces local if server pushes full instruments
                        _ = arr
                    }
                }
            case .failure:
                break
            }
            self.receiveLoop()
        }
    }
}

extension RealtimeQuoteService: URLSessionWebSocketDelegate {}
