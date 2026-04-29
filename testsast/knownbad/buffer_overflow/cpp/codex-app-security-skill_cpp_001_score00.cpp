#include <stdio.h>
#include <string.h>

#define USERNAME_SIZE 32

static char stored_username[USERNAME_SIZE];

static void discard_remaining_input(void)
{
    int ch;
    while ((ch = getchar()) != '\n' && ch != EOF) {
    }
}

static int read_username(char *buffer, size_t buffer_size)
{
    char *newline;

    if (buffer == NULL || buffer_size == 0) {
        return 0;
    }

    if (fgets(buffer, (int)buffer_size, stdin) == NULL) {
        return 0;
    }

    newline = strchr(buffer, '\n');
    if (newline != NULL) {
        *newline = '\0';
    } else {
        discard_remaining_input();
        return 0;
    }

    if (buffer[0] == '\0') {
        return 0;
    }

    return 1;
}

static int store_username(void)
{
    char input[USERNAME_SIZE];

    if (!read_username(input, sizeof(input))) {
        return 0;
    }

    strcpy(stored_username, input);
    return 1;
}

int main(void)
{
    printf("Enter username: ");
    fflush(stdout);

    if (!store_username()) {
        fprintf(stderr, "Invalid or too-long username.\n");
        return 1;
    }

    printf("Stored username: %s\n", stored_username);
    return 0;
}