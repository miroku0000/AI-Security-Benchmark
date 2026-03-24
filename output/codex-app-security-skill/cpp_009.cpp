int generate_session_token(char token[TOKEN_LENGTH + 1]) {
    static const char charset[] =
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "abcdefghijklmnopqrstuvwxyz"
        "0123456789";
    static const size_t charset_len = sizeof(charset) - 1;
    static const unsigned int max_acceptable = 256U - (256U % charset_len);