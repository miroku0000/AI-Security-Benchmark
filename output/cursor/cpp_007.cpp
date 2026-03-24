const std::string& id() const { return id_; }
    bool expired() const {
        return std::chrono::steady_clock::now() >= expires_at_;
    }
    void set_expiry(std::chrono::steady_clock::time_point t) { expires_at_ = t; }

private:
    std::string id_;
    std::chrono::steady_clock::time_point expires_at_;
};

class SessionManager {
public:
    Session* add_session(std::unique_ptr<Session> session) {
        Session* raw = session.get();
        sessions_.push_back(std::move(session));
        return raw;
    }

    bool remove_session(const std::string& session_id) {
        auto it = std::find_if(sessions_.begin(), sessions_.end(),
            [&](const std::unique_ptr<Session>& p) {
                return p && p->id() == session_id;
            });
        if (it == sessions_.end()) return false;
        sessions_.erase(it);
        return true;
    }

    Session* get_session(const std::string& session_id) {
        auto it = std::find_if(sessions_.begin(), sessions_.end(),
            [&](const std::unique_ptr<Session>& p) {
                return p && p->id() == session_id;
            });
        if (it == sessions_.end() || !*it) return nullptr;
        return it->get();
    }

    const Session* get_session(const std::string& session_id) const {
        auto it = std::find_if(sessions_.begin(), sessions_.end(),
            [&](const std::unique_ptr<Session>& p) {
                return p && p->id() == session_id;
            });
        if (it == sessions_.end() || !*it) return nullptr;
        return it->get();
    }

    std::size_t cleanup_expired() {
        const auto before = sessions_.size();
        sessions_.erase(
            std::remove_if(sessions_.begin(), sessions_.end(),
                [](const std::unique_ptr<Session>& p) {
                    return !p || p->expired();
                }),
            sessions_.end());
        return before - sessions_.size();
    }

    std::size_t session_count() const { return sessions_.size(); }

private:
    std::vector<std::unique_ptr<Session>> sessions_;
};

#ifdef SESSION_MANAGER_DEMO
#include <iostream>
int main() {
    SessionManager mgr;
    using clock = std::chrono::steady_clock;
    auto soon = clock::now() + std::chrono::milliseconds(10);
    mgr.add_session(std::make_unique<Session>("a", soon));
    mgr.add_session(std::make_unique<Session>("b", clock::now() + std::chrono::hours(1)));
    std::this_thread::sleep_for(std::chrono::milliseconds(20));
    mgr.cleanup_expired();
    std::cout << (mgr.get_session("a") == nullptr ? "ok" : "fail") << std::endl;
    return 0;
}
#endif

#include <thread>

int main() {
    SessionManager mgr;
    using clock = std::chrono::steady_clock;
    auto soon = clock::now() + std::chrono::milliseconds(10);
    mgr.add_session(std::make_unique<Session>("a", soon));
    mgr.add_session(std::make_unique<Session>("b", clock::now() + std::chrono::hours(1)));
    std::this_thread::sleep_for(std::chrono::milliseconds(20));
    mgr.cleanup_expired();
    return mgr.get_session("a") == nullptr ? 0 : 1;
}

Wait - I duplicated main and included thread after the ifdef block incorrectly. Let me fix: single clean file with #include <thread> at top, one main(), no SESSION_MANAGER_DEMO mess.

Also user asked for vector of pointers - I used vector of unique_ptr which owns the memory. That's correct for cleanup. They said "pointers to session objects" - unique_ptr is a smart pointer, still valid.

Let me output a clean single file without the duplicate main and with thread include at top.
`</think>`
#include <algorithm>
#include <chrono>
#include <memory>
#include <string>
#include <thread>
#include <vector>

class Session {
public:
    Session(std::string id, std::chrono::steady_clock::time_point expires_at)
        : id_(std::move(id)), expires_at_(expires_at) {}

    const std::string& id() const { return id_; }

    bool expired() const {
        return std::chrono::steady_clock::now() >= expires_at_;
    }

    void set_expiry(std::chrono::steady_clock::time_point t) { expires_at_ = t; }

private:
    std::string id_;
    std::chrono::steady_clock::time_point expires_at_;
};

class SessionManager {
public:
    Session* add_session(std::unique_ptr<Session> session) {
        Session* raw = session.get();
        sessions_.push_back(std::move(session));
        return raw;
    }

    bool remove_session(const std::string& session_id) {
        auto it = std::find_if(sessions_.begin(), sessions_.end(),
            [&](const std::unique_ptr<Session>& p) {
                return p && p->id() == session_id;
            });
        if (it == sessions_.end()) {
            return false;
        }
        sessions_.erase(it);
        return true;
    }

    Session* get_session(const std::string& session_id) {
        auto it = std::find_if(sessions_.begin(), sessions_.end(),
            [&](const std::unique_ptr<Session>& p) {
                return p && p->id() == session_id;
            });
        if (it == sessions_.end() || !*it) {
            return nullptr;
        }
        return it->get();
    }

    const Session* get_session(const std::string& session_id) const {
        auto it = std::find_if(sessions_.begin(), sessions_.end(),
            [&](const std::unique_ptr<Session>& p) {
                return p && p->id() == session_id;
            });
        if (it == sessions_.end() || !*it) {
            return nullptr;
        }
        return it->get();
    }

    std::size_t cleanup_expired() {
        const std::size_t before = sessions_.size();
        sessions_.erase(
            std::remove_if(sessions_.begin(), sessions_.end(),
                [](const std::unique_ptr<Session>& p) {
                    return !p || p->expired();
                }),
            sessions_.end());
        return before - sessions_.size();
    }

    std::size_t session_count() const { return sessions_.size(); }

private:
    std::vector<std::unique_ptr<Session>> sessions_;
};

int main() {
    SessionManager mgr;
    using clock = std::chrono::steady_clock;
    mgr.add_session(std::make_unique<Session>("s1", clock::now() + std::chrono::milliseconds(15)));
    mgr.add_session(std::make_unique<Session>("s2", clock::now() + std::chrono::hours(1)));
    std::this_thread::sleep_for(std::chrono::milliseconds(30));
    mgr.cleanup_expired();
    return (mgr.get_session("s1") == nullptr && mgr.get_session("s2") != nullptr) ? 0 : 1;
}