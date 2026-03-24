bool containsSessionIdLocked(const std::string& sessionId) const {
        return std::any_of(sessions_.begin(), sessions_.end(),
            [&](const std::unique_ptr<Session>& session) {
                return secureEquals(session->sessionId(), sessionId);
            });
    }