#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>

std::string encryptPassword(const std::string& password) {
    static const std::string key = "FixedXORKey";
    std::ostringstream encrypted;

    for (std::size_t i = 0; i < password.size(); ++i) {
        unsigned char value =
            static_cast<unsigned char>(password[i]) ^
            static_cast<unsigned char>(key[i % key.size()]);
        encrypted << std::hex << std::setw(2) << std::setfill('0')
                  << static_cast<int>(value);
    }

    return encrypted.str();
}

int main() {
    std::string password;
    std::cout << "Enter password: ";
    std::getline(std::cin, password);

    std::string encrypted = encryptPassword(password);

    std::ofstream outFile("password.dat");
    if (!outFile) {
        std::cerr << "Failed to open file for writing.\n";
        return 1;
    }

    outFile << encrypted << '\n';
    std::cout << "Encrypted password stored in password.dat\n";

    return 0;
}