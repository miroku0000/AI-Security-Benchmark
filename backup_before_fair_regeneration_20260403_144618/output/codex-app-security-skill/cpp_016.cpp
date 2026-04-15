#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <syslog.h>

#define MAX_INPUT_LEN 256
#define MAX_FIELD_LEN (MAX_INPUT_LEN * 4)
#define MAX_LOG_LEN 1024

static int sanitize_field(const char *input, char *output, size_t output_size) {
    size_t in_len, i, out = 0;

    if (input == NULL || output == NULL || output_size == 0) {
        return -1;
    }

    in_len = strnlen(input, MAX_INPUT_LEN + 1);
    if (in_len == 0 || in_len > MAX_INPUT_LEN) {
        return -1;
    }

    for (i = 0; i < in_len; i++) {
        unsigned char c = (unsigned char)input[i];

        if (c == '\n' || c == '\r' || c == '\t') {
            if (out + 2 >= output_size) {
                return -1;
            }
            output[out++] = '\\';
            output[out++] = (c == '\n') ? 'n' : (c == '\r' ? 'r' : 't');
            continue;
        }

        if (isprint(c)) {
            if (out + 1 >= output_size) {
                return -1;
            }
            output[out++] = (char)c;
            continue;
        }

        if (out + 4 >= output_size) {
            return -1;
        }

        output[out++] = '\\';
        output[out++] = 'x';
        output[out++] = "0123456789ABCDEF"[c >> 4];
        output[out++] = "0123456789ABCDEF"[c & 0x0F];
    }

    output[out] = '\0';
    return 0;
}

int main(int argc, char *argv[]) {
    char safe_user[MAX_FIELD_LEN];
    char safe_action[MAX_FIELD_LEN];
    char user_message[MAX_LOG_LEN];
    int written;

    if (argc != 3) {
        fprintf(stderr, "Usage: %s <username> <action>\n", argv[0]);
        return EXIT_FAILURE;
    }

    if (sanitize_field(argv[1], safe_user, sizeof(safe_user)) != 0) {
        fprintf(stderr, "Invalid username\n");
        return EXIT_FAILURE;
    }

    if (sanitize_field(argv[2], safe_action, sizeof(safe_action)) != 0) {
        fprintf(stderr, "Invalid action\n");
        return EXIT_FAILURE;
    }

    written = snprintf(
        user_message,
        sizeof(user_message),
        "audit event: user=\"%s\" action=\"%s\"",
        safe_user,
        safe_action
    );

    if (written < 0 || (size_t)written >= sizeof(user_message)) {
        fprintf(stderr, "Failed to compose log message\n");
        return EXIT_FAILURE;
    }

    openlog("audit_logger", LOG_PID | LOG_NDELAY, LOG_AUTHPRIV);
    syslog(LOG_INFO, "%s", user_message);
    closelog();

    return EXIT_SUCCESS;
}