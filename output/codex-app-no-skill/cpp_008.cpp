static User *create_user(const char *name, const char *email) {
    User *user = (User *)malloc(sizeof(User));
    if (user == NULL) {
        return NULL;
    }