typedef struct User {
    char *name;
    char *email;
    struct User *next;
} User;

void print_user_list(User *head)
{
    User *node;

    for (node = head; node != NULL; node = node->next) {
        printf("%s\t%s\n", node->name, node->email);
    }
}

int main(void)
{
    User a = { "Alice", "alice@example.com", NULL };
    User b = { "Bob", "bob@example.com", NULL };
    User c = { "Carol", "carol@example.com", NULL };

    a.next = &b;
    b.next = &c;

    print_user_list(&a);
    return 0;
}