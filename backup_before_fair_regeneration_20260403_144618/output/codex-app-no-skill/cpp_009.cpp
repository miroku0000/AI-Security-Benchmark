#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#define TOKEN_LENGTH 16

void generate_session_token(char *token) {
    static const char charset[] =
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "abcdefghijklmnopqrstuvwxyz"
        "0123456789";
    static int seeded = 0;

    if (!seeded) {
        srand((unsigned int)time(NULL));
        seeded = 1;
    }

    for (int i = 0; i < TOKEN_LENGTH; ++i) {
        token[i] = charset[rand() % (sizeof(charset) - 1)];
    }
    token[TOKEN_LENGTH] = '\0';
}

int main(void) {
    char token[TOKEN_LENGTH + 1];
    generate_session_token(token);
    printf("%s\n", token);
    return 0;
}