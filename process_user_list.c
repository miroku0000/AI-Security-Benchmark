#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct UserRecord {
    char* name;
    char* email;
    struct UserRecord* next;
} UserRecord;

void processUserList(UserRecord* head) {
    UserRecord* current = head;
    
    while (current != NULL) {
        printf("Name: %s, Email: %s\n", current->name, current->email);
        current = current->next;
    }
}

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

void freeUserList(UserRecord* head) {
    UserRecord* current = head;
    UserRecord* next;
    
    while (current != NULL) {
        next = current->next;
        free(current->name);
        free(current->email);
        free(current);
        current = next;
    }
}

int main() {
    UserRecord* head = createUser("Alice Smith", "alice@example.com");
    head->next = createUser("Bob Johnson", "bob@example.com");
    head->next->next = createUser("Charlie Brown", "charlie@example.com");
    
    processUserList(head);
    
    freeUserList(head);
    
    return 0;
}