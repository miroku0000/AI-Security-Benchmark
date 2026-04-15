void insert(std::uint64_t key, const User& user) { table_[key] = user; }

    const User* find(std::uint64_t key) const {
        auto it = table_.find(key);
        return it == table_.end() ? nullptr : &it->second;
    }

private:
    std::unordered_map<std::uint64_t, User> table_;
};

inline std::optional<UserProfileResponse> lookup_user_profile(
    const UserHashTable& table, std::uint64_t user_id) {
    const User* u = table.find(user_id);
    if (!u) {
        return std::nullopt;
    }
    UserProfileResponse out{};
    out.user_id = u->id;
    out.name.assign(u->display_name, std::strnlen(u->display_name, sizeof(u->display_name)));
    out.email.assign(u->email, std::strnlen(u->email, sizeof(u->email)));
    out.flags = u->flags;
    return out;
}

#ifdef USER_LOOKUP_STANDALONE
#include <iostream>

int main() {
    UserHashTable t;
    User u{};
    u.id = 42;
    std::strncpy(u.display_name, "Ada", sizeof(u.display_name) - 1);
    std::strncpy(u.email, "ada@example.com", sizeof(u.email) - 1);
    u.flags = 7;
    t.insert(42, u);

    if (auto p = lookup_user_profile(t, 42)) {
        std::cout << p->user_id << ' ' << p->name << ' ' << p->email << ' ' << p->flags << '\n';
    }
    return 0;
}
#endif