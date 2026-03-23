#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct UserRecord {
    char *name;
    char *email;
} UserRecord;

typedef struct UserNode {
    UserRecord user;
    struct UserNode *next;
} UserNode;

void print_user_records(UserNode *head)
{
    UserNode *node;

    for (node = head; node != NULL; node = node->next) {
        printf("name: %s\n", node->user.name);
        printf("email: %s\n", node->user.email);
    }
}

void free_user_list(UserNode *head)
{
    UserNode *node;
    UserNode *next;

    for (node = head; node != NULL; node = next) {
        next = node->next;
        free(node->user.name);
        free(node->user.email);
        free(node);
    }
}

static UserNode *append_user(UserNode *head, const char *name, const char *email)
{
    UserNode *node;
    UserNode *tail;

    node = (UserNode *)malloc(sizeof(UserNode));
    if (node == NULL) {
        return head;
    }
    node->user.name = strdup(name);
    node->user.email = strdup(email);
    if (node->user.name == NULL || node->user.email == NULL) {
        free(node->user.name);
        free(node->user.email);
        free(node);
        return head;
    }
    node->next = NULL;
    if (head == NULL) {
        return node;
    }
    for (tail = head; tail->next != NULL; tail = tail->next) {
        /* find end */
    }
    tail->next = node;
    return head;
}

int main(void)
{
    UserNode *list = NULL;

    list = append_user(list, "Ada Lovelace", "ada@example.com");
    list = append_user(list, "Alan Turing", "alan@example.com");
    print_user_records(list);
    free_user_list(list);
    return 0;
}
