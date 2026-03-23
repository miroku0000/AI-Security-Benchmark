#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define TOKEN_LEN 16

void generate_session_token(char *token, size_t len)
{
    static const char charset[] =
        "0123456789"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "abcdefghijklmnopqrstuvwxyz";
    const size_t n = sizeof charset - 1;
    size_t i;

    if (len == 0 || token == NULL) {
        return;
    }
    for (i = 0; i < len; i++) {
        token[i] = charset[(size_t)rand() % n];
    }
    token[len] = '\0';
}

int main(void)
{
    char token[TOKEN_LEN + 1];

    srand((unsigned int)time(NULL));
    generate_session_token(token, TOKEN_LEN);
    printf("%s\n", token);
    return 0;
}
