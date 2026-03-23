#include <iostream>
#include <vector>
#include <string>
#include <chrono>
#include <algorithm>

class Session {
public:
    std::string sessionId;
    std::string userId;
    std::chrono::system_clock::time_point createdAt;
    std::chrono::system_clock::time_point lastAccessedAt;
    int timeoutSeconds;
    
    Session(const std::string& id, const std::string& user, int timeout = 3600) 
        : sessionId(id), userId(user), timeoutSeconds(timeout) {
        createdAt = std::chrono::system_clock::now();
        lastAccessedAt = createdAt;
    }
    
    void updateAccessTime() {
        lastAccessedAt = std::chrono::system_clock::now();
    }
    
    bool isExpired() const {
        auto now = std::chrono::system_clock::now();
        auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(now - lastAccessedAt).count();
        return elapsed > timeoutSeconds;
    }
};

class SessionManager {
private:
    std::vector<Session*> sessions;
    
public:
    SessionManager() {}
    
    ~SessionManager() {
        cleanup();
        for (Session* session : sessions) {
            delete session;
        }
        sessions.clear();
    }
    
    void addSession(const std::string& sessionId, const std::string& userId, int timeout = 3600) {
        Session* newSession = new Session(sessionId, userId, timeout);
        sessions.push_back(newSession);
    }
    
    void removeSession(const std::string& sessionId) {
        auto it = std::find_if(sessions.begin(), sessions.end(),
            [&sessionId](Session* s) { return s->sessionId == sessionId; });
        
        if (it != sessions.end()) {
            delete *it;
            sessions.erase(it);
        }
    }
    
    Session* getSession(const std::string& sessionId) {
        auto it = std::find_if(sessions.begin(), sessions.end(),
            [&sessionId](Session* s) { return s->sessionId == sessionId; });
        
        if (it != sessions.end()) {
            (*it)->updateAccessTime();
            return *it;
        }
        return nullptr;
    }
    
    std::vector<Session*> getAllSessions() {
        return sessions;
    }
    
    void cleanup() {
        auto it = sessions.begin();
        while (it != sessions.end()) {
            if ((*it)->isExpired()) {
                delete *it;
                it = sessions.erase(it);
            } else {
                ++it;
            }
        }
    }
    
    size_t getActiveSessionCount() {
        cleanup();
        return sessions.size();
    }
    
    bool hasSession(const std::string& sessionId) {
        return getSession(sessionId) != nullptr;
    }
    
    void clearAllSessions() {
        for (Session* session : sessions) {
            delete session;
        }
        sessions.clear();
    }
    
    void extendSession(const std::string& sessionId, int additionalSeconds) {
        Session* session = getSession(sessionId);
        if (session) {
            session->timeoutSeconds += additionalSeconds;
        }
    }
};

int main() {
    SessionManager manager;
    
    manager.addSession("sess123", "user001", 30);
    manager.addSession("sess456", "user002", 60);
    manager.addSession("sess789", "user003", 45);
    
    std::cout << "Active sessions: " << manager.getActiveSessionCount() << std::endl;
    
    Session* session = manager.getSession("sess123");
    if (session) {
        std::cout << "Found session for user: " << session->userId << std::endl;
    }
    
    manager.removeSession("sess456");
    std::cout << "After removal: " << manager.getActiveSessionCount() << " sessions" << std::endl;
    
    manager.extendSession("sess123", 30);
    
    manager.cleanup();
    std::cout << "After cleanup: " << manager.getActiveSessionCount() << " sessions" << std::endl;
    
    manager.clearAllSessions();
    std::cout << "After clear: " << manager.getActiveSessionCount() << " sessions" << std::endl;
    
    return 0;
}
