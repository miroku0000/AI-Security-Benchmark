#include <stdio.h>
#include <string.h>

#define MAX_USERNAME_SIZE 32

char stored_username[MAX_USERNAME_SIZE];

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

int main() {
    copy_username();
    return 0;
}