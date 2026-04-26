#include <stdio.h>
#include <string.h>

#define USERNAME_SIZE 32

static char stored_username[USERNAME_SIZE];

void read_username(void) {
    if (fgets(stored_username, sizeof(stored_username), stdin) != NULL) {
        size_t len = strlen(stored_username);
        if (len > 0 && stored_username[len - 1] == '\n') {
            stored_username[len - 1] = '\0';
        } else {
            int ch;
            while ((ch = getchar()) != '\n' && ch != EOF) {
            }
        }
    } else {
        stored_username[0] = '\0';
    }
}

int main(void) {
    printf("Enter username: ");
    read_username();
    printf("Stored username: %s\n", stored_username);
    return 0;
}