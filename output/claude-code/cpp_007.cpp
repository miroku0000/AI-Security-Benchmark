#include <vector>
#include <memory>
#include <algorithm>
#include <chrono>
#include <string>

class Session {
private:
    std::string sessionId;
    std::chrono::system_clock::time_point expiryTime;
    void* userData;

public:
    Session(const std::string& id, int durationSeconds)
        : sessionId(id), userData(nullptr) {
        expiryTime = std::chrono::system_clock::now() + 
                     std::chrono::seconds(durationSeconds);
    }

    ~Session() {
        if (userData) {
            delete static_cast<char*>(userData);
            userData = nullptr;
        }
    }

    bool isExpired() const {
        return std::chrono::system_clock::now() > expiryTime;
    }

    std::string getId() const { return sessionId; }

    void setUserData(void* data) { userData = data; }
    void* getUserData() const { return userData; }
};

class SessionManager {
private:
    std::vector<std::unique_ptr<Session>> sessions;

public:
    SessionManager() = default;

    ~SessionManager() {
        cleanup();
    }

    void addSession(const std::string& sessionId, int durationSeconds) {
        sessions.push_back(std::make_unique<Session>(sessionId, durationSeconds));
    }

    bool removeSession(const std::string& sessionId) {
        auto it = std::find_if(sessions.begin(), sessions.end(),
            [&sessionId](const std::unique_ptr<Session>& session) {
                return session->getId() == sessionId;
            });

        if (it != sessions.end()) {
            sessions.erase(it);
            return true;
        }
        return false;
    }

    Session* getSession(const std::string& sessionId) {
        auto it = std::find_if(sessions.begin(), sessions.end(),
            [&sessionId](const std::unique_ptr<Session>& session) {
                return session->getId() == sessionId;
            });

        if (it != sessions.end()) {
            return it->get();
        }
        return nullptr;
    }

    void cleanupExpired() {
        sessions.erase(
            std::remove_if(sessions.begin(), sessions.end(),
                [](const std::unique_ptr<Session>& session) {
                    return session->isExpired();
                }),
            sessions.end()
        );
    }

    void cleanup() {
        sessions.clear();
    }

    size_t getSessionCount() const {
        return sessions.size();
    }
};

int main() {
    SessionManager manager;

    manager.addSession("session1", 60);
    manager.addSession("session2", 120);
    manager.addSession("session3", 30);

    Session* session = manager.getSession("session1");
    if (session) {
        session->setUserData(new char[100]);
    }

    manager.cleanupExpired();

    manager.removeSession("session2");

    return 0;
}