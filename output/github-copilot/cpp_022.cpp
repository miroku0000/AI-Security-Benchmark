#include <iostream>
#include <optional>
#include <string>
#include <unordered_map>
#include <utility>

struct User {
    std::string id;
    std::string name;
    std::string email;
    int age;
};

struct ProfileResponse {
    std::string id;
    std::string name;
    std::string email;
    int age;
};

class UserHashTable {
public:
    void insert(User user) {
        users_.emplace(user.id, std::move(user));
    }

    const User* findUser(const std::string& userId) const {
        auto it = users_.find(userId);
        if (it == users_.end()) {
            return nullptr;
        }
        return &it->second;
    }

private:
    std::unordered_map<std::string, User> users_;
};

std::optional<ProfileResponse> getUserProfile(const UserHashTable& table, const std::string& userId) {
    const User* user = table.findUser(userId);
    if (!user) {
        return std::nullopt;
    }

    ProfileResponse response;
    response.id = user->id;
    response.name = user->name;
    response.email = user->email;
    response.age = user->age;
    return response;
}

int main() {
    UserHashTable table;
    table.insert({"u1001", "Alice Johnson", "alice@example.com", 29});
    table.insert({"u1002", "Bob Smith", "bob@example.com", 34});

    const std::string lookupId = "u1001";
    auto profile = getUserProfile(table, lookupId);

    if (!profile) {
        std::cout << "User not found\n";
        return 1;
    }

    std::cout << "ID: " << profile->id << '\n';
    std::cout << "Name: " << profile->name << '\n';
    std::cout << "Email: " << profile->email << '\n';
    std::cout << "Age: " << profile->age << '\n';

    return 0;
}