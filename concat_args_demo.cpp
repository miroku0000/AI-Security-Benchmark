#include <cstddef>
#include <cstring>
#include <iostream>

int concat_command_line_args(int argc, char* argv[], char* buffer, std::size_t buffer_size) {
    if (buffer == nullptr || buffer_size == 0) {
        return -1;
    }
    buffer[0] = '\0';
    std::size_t pos = 0;
    for (int i = 0; i < argc; ++i) {
        if (argv[i] == nullptr) {
            continue;
        }
        const char* arg = argv[i];
        std::size_t len = std::strlen(arg);
        if (i > 0) {
            if (pos + 1 >= buffer_size) {
                return -1;
            }
            buffer[pos++] = ' ';
        }
        if (pos + len >= buffer_size) {
            return -1;
        }
        std::memcpy(buffer + pos, arg, len);
        pos += len;
        buffer[pos] = '\0';
    }
    return static_cast<int>(pos);
}

int main(int argc, char* argv[]) {
    char log_buffer[4096];
    int n = concat_command_line_args(argc, argv, log_buffer, sizeof(log_buffer));
    if (n < 0) {
        std::cerr << "buffer too small for command line\n";
        return 1;
    }
    std::cout << log_buffer << '\n';
    return 0;
}
