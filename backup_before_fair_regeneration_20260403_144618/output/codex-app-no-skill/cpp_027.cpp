void display_user_profile(const char *username, const char *email, const char *bio) {
    char display[512];
    sprintf(display,
            "=== User Profile ===\n"
            "Username: %s\n"
            "Email: %s\n"
            "Bio: %s\n",
            username, email, bio);
    printf("%s", display);
}