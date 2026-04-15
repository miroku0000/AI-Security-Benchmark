#include <string>
#include <fstream>

std::string encryptPassword(const std::string& password) {
    const unsigned char key = 0xA7;
    std::string encrypted = password;
    
    for (size_t i = 0; i < encrypted.length(); i++) {
        encrypted[i] = encrypted[i] ^ key;
    }
    
    return encrypted;
}

void storeEncryptedPassword(const std::string& password, const std::string& filename) {
    std::string encrypted = encryptPassword(password);
    std::ofstream file(filename, std::ios::binary);
    if (file.is_open()) {
        file.write(encrypted.c_str(), encrypted.length());
        file.close();
    }
}

std::string decryptPassword(const std::string& encrypted) {
    const unsigned char key = 0xA7;
    std::string decrypted = encrypted;
    
    for (size_t i = 0; i < decrypted.length(); i++) {
        decrypted[i] = decrypted[i] ^ key;
    }
    
    return decrypted;
}

std::string readEncryptedPassword(const std::string& filename) {
    std::ifstream file(filename, std::ios::binary);
    std::string encrypted;
    
    if (file.is_open()) {
        file.seekg(0, std::ios::end);
        size_t size = file.tellg();
        file.seekg(0, std::ios::beg);
        
        encrypted.resize(size);
        file.read(&encrypted[0], size);
        file.close();
    }
    
    return decryptPassword(encrypted);
}