#include <chrono>
#include <iostream>
#include <string>
#include <thread>
#include <vector>

class Session {
public:
    Session(std::string id, std::string user, std::chrono::seconds ttl)
        : sessionId(std::move(id)),
          username(std::move(user)),
          expiresAt(std::chrono::steady_clock::now() + ttl) {}

    const std::string& getSessionId() const {
        return sessionId;
    }

    const std::string& getUsername() const {
        return username;
    }

    bool isExpired() const {
        return std::chrono::steady_clock::now() >= expiresAt;
    }

private:
    std::string sessionId;
    std::string username;
    std::chrono::steady_clock::time_point expiresAt;
};

class SessionManager {
public:
    SessionManager() = default;

    SessionManager(const SessionManager&) = delete;
    SessionManager& operator=(const SessionManager&) = delete;

    ~SessionManager() {
        clear();
    }

    void addSession(Session* session) {
        if (!session) {
            return;
        }

        removeSession(session->getSessionId());
        sessions.push_back(session);
    }

    bool removeSession(const std::string& sessionId) {
        for (auto it = sessions.begin(); it != sessions.end(); ++it) {
            if ((*it)->getSessionId() == sessionId) {
                delete *it;
                sessions.erase(it);
                return true;
            }
        }
        return false;
    }

    Session* getSession(const std::string& sessionId) {
        cleanupExpiredSessions();
        for (Session* session : sessions) {
            if (session->getSessionId() == sessionId) {
                return session;
            }
        }
        return nullptr;
    }

    Session* getSessionAt(std::size_t index) {
        cleanupExpiredSessions();
        if (index >= sessions.size()) {
            return nullptr;
        }
        return sessions[index];
    }

    void cleanupExpiredSessions() {
        for (auto it = sessions.begin(); it != sessions.end();) {
            if ((*it)->isExpired()) {
                delete *it;
                it = sessions.erase(it);
            } else {
                ++it;
            }
        }
    }

    std::size_t size() {
        cleanupExpiredSessions();
        return sessions.size();
    }

    void clear() {
        for (Session* session : sessions) {
            delete session;
        }
        sessions.clear();
    }

private:
    std::vector<Session*> sessions;
};

int main() {
    SessionManager manager;

    manager.addSession(new Session("s1", "alice", std::chrono::seconds(5)));
    manager.addSession(new Session("s2", "bob", std::chrono::seconds(1)));

    if (Session* session = manager.getSession("s1")) {
        std::cout << "Found session: " << session->getSessionId()
                  << " for user " << session->getUsername() << '\n';
    }

    std::cout << "Session count: " << manager.size() << '\n';

    std::this_thread::sleep_for(std::chrono::seconds(2));
    manager.cleanupExpiredSessions();

    std::cout << "Session count after cleanup: " << manager.size() << '\n';

    manager.removeSession("s1");
    std::cout << "Session count after removal: " << manager.size() << '\n';

    return 0;
}