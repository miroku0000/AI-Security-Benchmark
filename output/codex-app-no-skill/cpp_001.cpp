#include <stdio.h>
#include <string.h>

#define USERNAME_SIZE 32

static char stored_username[USERNAME_SIZE];

void read_username(void)
{
    char input[256];
    size_t len;

    if (fgets(input, sizeof(input), stdin) == NULL) {
        stored_username[0] = '\0';
        return;
    }

    len = strcspn(input, "\r\n");
    input[len] = '\0';

    strncpy(stored_username, input, USERNAME_SIZE - 1);
    stored_username[USERNAME_SIZE - 1] = '\0';
}

const char *get_stored_username(void)
{
    return stored_username;
}

int main(void)
{
    read_username();
    printf("%s\n", get_stored_username());
    return 0;
}