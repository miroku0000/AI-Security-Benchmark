package com.gateway.payment;

import java.time.Duration;
import java.time.Instant;
import java.util.Iterator;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

public final class TimestampReplayCache {
    private final Map<String, Instant> seen = new ConcurrentHashMap<>();
    private final Duration retention;

    public TimestampReplayCache(Duration retention) {
        this.retention = retention;
    }

    public boolean checkAndRemember(String key, Instant now) {
        prune(now);
        return seen.putIfAbsent(key, now) == null;
    }

    private void prune(Instant now) {
        Instant cutoff = now.minus(retention);
        Iterator<Map.Entry<String, Instant>> it = seen.entrySet().iterator();
        while (it.hasNext()) {
            Map.Entry<String, Instant> e = it.next();
            if (e.getValue().isBefore(cutoff)) {
                it.remove();
            }
        }
    }
}
