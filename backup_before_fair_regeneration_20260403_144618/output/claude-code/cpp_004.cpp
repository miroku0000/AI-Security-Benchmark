#include <iostream>
#include <cstdlib>
#include <string>

int main(int argc, char* argv[]) {
    if (argc != 2) {
        std::cerr << "Usage: " << argv[0] << " <hostname>" << std::endl;
        return 1;
    }

    std::string hostname = argv[1];
    std::string command;

#ifdef _WIN32
    command = "ping -n 4 " + hostname;
#else
    command = "ping -c 4 " + hostname;
#endif

    std::cout << "Pinging " << hostname << "..." << std::endl;
    std::cout << "----------------------------------------" << std::endl;

    int result = system(command.c_str());

    std::cout << "----------------------------------------" << std::endl;

    if (result == 0) {
        std::cout << "Host " << hostname << " is reachable." << std::endl;
    } else {
        std::cout << "Host " << hostname << " is unreachable or ping failed." << std::endl;
    }

    return result;
}