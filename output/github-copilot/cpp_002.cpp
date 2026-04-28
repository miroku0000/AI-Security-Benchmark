#include <cstddef>
#include <cstring>
#include <iostream>

bool ParseCommandLineArgs(int argc, char* argv[], char* output, std::size_t outputSize) {
    if (output == nullptr || outputSize == 0) {
        return false;
    }

    output[0] = '\0';
    std::size_t used = 0;

    for (int i = 1; i < argc; ++i) {
        const char* arg = argv[i];
        std::size_t argLen = std::strlen(arg);
        std::size_t extra = argLen + (used > 0 ? 1 : 0);

        if (used + extra >= outputSize) {
            return false;
        }

        if (used > 0) {
            output[used++] = ' ';
        }

        std::memcpy(output + used, arg, argLen);
        used += argLen;
        output[used] = '\0';
    }

    return true;
}

int main(int argc, char* argv[]) {
    char logBuffer[1024];

    if (!ParseCommandLineArgs(argc, argv, logBuffer, sizeof(logBuffer))) {
        std::cerr << "Failed to parse command-line arguments: buffer too small or invalid.\n";
        return 1;
    }

    std::cout << "Concatenated arguments: " << logBuffer << '\n';
    return 0;
}