#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct User {
    char *name;
    char *email;
    struct User *next;
} User;

static User *create_user(const char *name, const char *email) {
    User *user = (User *)malloc(sizeof(User));
    if (user == NULL) {
        fprintf(stderr, "Failed to allocate memory for user.\n");
        exit(EXIT_FAILURE);
    }

    user->name = (char *)malloc(strlen(name) + 1);
    user->email = (char *)malloc(strlen(email) + 1);

    if (user->name == NULL || user->email == NULL) {
        fprintf(stderr, "Failed to allocate memory for user fields.\n");
        free(user->name);
        free(user->email);
        free(user);
        exit(EXIT_FAILURE);
    }

    strcpy(user->name, name);
    strcpy(user->email, email);
    user->next = NULL;

    return user;
}

static void append_user(User **head, const char *name, const char *email) {
    User *new_user = create_user(name, email);

    if (*head == NULL) {
        *head = new_user;
        return;
    }

    User *current = *head;
    while (current->next != NULL) {
        current = current->next;
    }
    current->next = new_user;
}

void print_user_list(const User *head) {
    const User *current = head;

    while (current != NULL) {
        printf("Name: %s, Email: %s\n", current->name, current->email);
        current = current->next;
    }
}

static void free_user_list(User *head) {
    while (head != NULL) {
        User *next = head->next;
        free(head->name);
        free(head->email);
        free(head);
        head = next;
    }
}

int main(void) {
    User *users = NULL;

    append_user(&users, "Alice Johnson", "alice@example.com");
    append_user(&users, "Bob Smith", "bob@example.com");
    append_user(&users, "Carol Davis", "carol@example.com");

    print_user_list(users);
    free_user_list(users);

    return 0;
}