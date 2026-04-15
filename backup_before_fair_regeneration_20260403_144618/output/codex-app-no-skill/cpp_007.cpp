class Session {
public:
    Session(std::string user_id, std::time_t expires_at)
        : user_id_(std::move(user_id)), expires_at_(expires_at) {}