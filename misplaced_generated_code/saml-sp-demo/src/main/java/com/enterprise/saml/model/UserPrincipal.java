package com.enterprise.saml.model;

import java.io.Serializable;
import java.time.Instant;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;

public final class UserPrincipal implements Serializable {
    private static final long serialVersionUID = 1L;

    private final String nameId;
    private final String nameIdFormat;
    private final Map<String, List<String>> attributes;
    private final Instant assertionIssueInstant;
    private final Instant sessionNotOnOrAfter;

    public UserPrincipal(
            String nameId,
            String nameIdFormat,
            Map<String, List<String>> attributes,
            Instant assertionIssueInstant,
            Instant sessionNotOnOrAfter) {
        this.nameId = Objects.requireNonNull(nameId, "nameId");
        this.nameIdFormat = nameIdFormat;
        this.attributes = Collections.unmodifiableMap(new LinkedHashMap<>(attributes));
        this.assertionIssueInstant = assertionIssueInstant;
        this.sessionNotOnOrAfter = sessionNotOnOrAfter;
    }

    public String getNameId() {
        return nameId;
    }

    public String getNameIdFormat() {
        return nameIdFormat;
    }

    public Map<String, List<String>> getAttributes() {
        return attributes;
    }

    public Instant getAssertionIssueInstant() {
        return assertionIssueInstant;
    }

    public Instant getSessionNotOnOrAfter() {
        return sessionNotOnOrAfter;
    }
}
