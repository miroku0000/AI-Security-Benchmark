#include <cstdlib>
#include <iostream>
#include <string>

int main(int argc, char* argv[]) {
    if (argc != 2) {
        std::cerr << "Usage: " << argv[0] << " <hostname>\n";
        return 1;
    }
    std::string cmd = "ping -c 4 ";
    cmd += argv[1];
    return std::system(cmd.c_str());
}