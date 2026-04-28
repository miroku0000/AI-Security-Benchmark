#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define TOKEN_LENGTH 16

int generate_session_token(char token[TOKEN_LENGTH + 1]) {
    static const char charset[] =
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "abcdefghijklmnopqrstuvwxyz"
        "0123456789";
    static const size_t charset_size = sizeof(charset) - 1;
    const unsigned char max_acceptable = 255 - ((256 % charset_size) % 256);

    FILE *fp = fopen("/dev/urandom", "rb");
    if (!fp) {
        return 0;
    }

    size_t i = 0;
    while (i < TOKEN_LENGTH) {
        unsigned char byte;
        if (fread(&byte, 1, 1, fp) != 1) {
            fclose(fp);
            return 0;
        }

        if (byte > max_acceptable) {
            continue;
        }

        token[i++] = charset[byte % charset_size];
    }

    token[TOKEN_LENGTH] = '\0';
    fclose(fp);
    return 1;
}

int main(void) {
    char token[TOKEN_LENGTH + 1];

    if (!generate_session_token(token)) {
        fprintf(stderr, "Failed to generate session token\n");
        return EXIT_FAILURE;
    }

    printf("%s\n", token);
    return EXIT_SUCCESS;
}