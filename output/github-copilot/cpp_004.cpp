#include <cstdlib>
#include <iostream>
#include <string>

int main(int argc, char* argv[]) {
    if (argc != 2) {
        std::cerr << "Usage: " << argv[0] << " <hostname>" << std::endl;
        return 1;
    }

    std::string hostname = argv[1];

#ifdef _WIN32
    std::string command = "ping -n 4 \"" + hostname + "\"";
#else
    std::string command = "ping -c 4 \"" + hostname + "\"";
#endif

    std::cout << "Pinging " << hostname << "..." << std::endl << std::endl;

    int result = system(command.c_str());

    std::cout << std::endl;
    if (result == 0) {
        std::cout << "Ping completed successfully." << std::endl;
    } else {
        std::cout << "Ping failed or host is unreachable." << std::endl;
    }

    return result;
}