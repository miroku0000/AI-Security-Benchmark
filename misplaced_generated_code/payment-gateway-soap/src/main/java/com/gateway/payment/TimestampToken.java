package com.gateway.payment;

import java.io.Serializable;
import java.time.Instant;
import java.util.Objects;

public final class TimestampToken implements Serializable {
    private static final long serialVersionUID = 1L;

    private final String wsuId;
    private final Instant created;
    private final Instant expires;

    public TimestampToken(String wsuId, Instant created, Instant expires) {
        this.wsuId = wsuId;
        this.created = Objects.requireNonNull(created, "created");
        this.expires = Objects.requireNonNull(expires, "expires");
    }

    public String getWsuId() {
        return wsuId;
    }

    public Instant getCreated() {
        return created;
    }

    public Instant getExpires() {
        return expires;
    }

    public String replayKey() {
        return (wsuId != null ? wsuId : "") + "|" + created.toString() + "|" + expires.toString();
    }
}
