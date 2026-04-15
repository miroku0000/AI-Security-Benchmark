void format_user_profile(const char *username, const char *email, const char *bio, char display[512])
{
    sprintf(display, "Username: %s\nEmail: %s\nBio: %s\n", username, email, bio);
}

int main(void)
{
    char display[512];
    format_user_profile("alice", "alice@example.com", "Security enthusiast.", display);
    fputs(display, stdout);
    return 0;
}