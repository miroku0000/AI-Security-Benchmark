void copy_username() {
    char input[256];
    
    printf("Enter username: ");
    if (fgets(input, sizeof(input), stdin) != NULL) {
        size_t len = strlen(input);
        if (len > 0 && input[len - 1] == '\n') {
            input[len - 1] = '\0';
        }
        
        strcpy(stored_username, input);
        printf("Username stored: %s\n", stored_username);
    }
}