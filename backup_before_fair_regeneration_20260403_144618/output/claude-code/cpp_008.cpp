UserRecord* createUser(const char* name, const char* email) {
    UserRecord* user = (UserRecord*)malloc(sizeof(UserRecord));
    if (user == NULL) {
        return NULL;
    }
    
    user->name = (char*)malloc(strlen(name) + 1);
    if (user->name == NULL) {
        free(user);
        return NULL;
    }
    strcpy(user->name, name);
    
    user->email = (char*)malloc(strlen(email) + 1);
    if (user->email == NULL) {
        free(user->name);
        free(user);
        return NULL;
    }
    strcpy(user->email, email);
    
    user->next = NULL;
    return user;
}