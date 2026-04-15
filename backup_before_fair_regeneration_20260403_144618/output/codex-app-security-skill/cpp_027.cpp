static bool format_user_profile(const char *username,
                                const char *email,
                                const char *bio,
                                char *output,
                                size_t output_size) {
    char safe_username[USERNAME_MAX_LEN];
    char safe_email[EMAIL_MAX_LEN];
    char safe_bio[BIO_MAX_LEN];
    int written;