const char* arg = argv[i];
        std::size_t arg_len = std::strlen(arg);
        std::size_t need = arg_len;
        if (i > 0) {
            need += 1;
        }
        if (written + need >= buffer_size) {
            break;
        }
        if (i > 0) {
            buffer[written++] = ' ';
        }
        std::memcpy(buffer + written, arg, arg_len);
        written += arg_len;
        buffer[written] = '\0';
    }
    return written;
}

#include <iostream>

int main(int argc, char* argv[]) {
    char log_buffer[4096];
    std::size_t n = concat_args_to_buffer(argc, argv, log_buffer, sizeof(log_buffer));
    std::cout << n << " bytes: " << log_buffer << std::endl;
    return 0;
}