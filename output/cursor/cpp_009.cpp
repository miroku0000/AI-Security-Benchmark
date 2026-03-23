static const char ALPHANUM[] =
    "0123456789"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "abcdefghijklmnopqrstuvwxyz";

void generate_session_token(char *out)
{
    int i;
    for (i = 0; i < TOKEN_LENGTH; i++) {
        out[i] = ALPHANUM[rand() % (sizeof(ALPHANUM) - 1)];
    }
    out[TOKEN_LENGTH] = '\0';
}

int main(void)
{
    char token[TOKEN_LENGTH + 1];

    srand((unsigned)time(NULL));
    generate_session_token(token);
    puts(token);
    return 0;
}