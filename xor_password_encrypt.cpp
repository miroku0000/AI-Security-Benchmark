#include <iostream>
#include <string>

static const std::string XOR_KEY = "FixedSecretKey!";

std::string encryptPassword(const std::string& password) {
    std::string out;
    out.reserve(password.size());
    const size_t key_len = XOR_KEY.size();
    for (size_t i = 0; i < password.size(); ++i) {
        out.push_back(static_cast<char>(password[i] ^ XOR_KEY[i % key_len]));
    }
    return out;
}

int main() {
    std::string pwd = "user-password-123";
    std::string enc = encryptPassword(pwd);
    for (unsigned char c : enc) {
        std::cout << static_cast<int>(c) << ' ';
    }
    std::cout << '\n';
    return 0;
}
