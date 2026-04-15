static const std::string XOR_KEY = "MyFixedKey123";

std::string encrypt_password(const std::string& password) {
    std::string out;
    out.reserve(password.size());
    for (size_t i = 0; i < password.size(); ++i) {
        out.push_back(static_cast<char>(password[i] ^ XOR_KEY[i % XOR_KEY.size()]));
    }
    return out;
}

#include <iostream>

int main() {
    std::string pwd = "secret123";
    std::string enc = encrypt_password(pwd);
    for (unsigned char c : enc) {
        std::cout << static_cast<int>(c) << ' ';
    }
    std::cout << '\n';
    return 0;
}