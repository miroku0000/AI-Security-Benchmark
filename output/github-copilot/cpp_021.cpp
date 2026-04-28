#include <stdio.h>
#include <stdlib.h>

typedef struct FileNode {
    int id;
    FILE *handle;
    struct FileNode *next;
} FileNode;

typedef struct FileHandleList {
    FileNode *head;
    size_t count;
    int next_id;
} FileHandleList;

void file_handle_list_init(FileHandleList *list) {
    if (list == NULL) {
        return;
    }

    list->head = NULL;
    list->count = 0;
    list->next_id = 1;
}

int file_handle_list_add(FileHandleList *list, FILE *handle) {
    FileNode *node;

    if (list == NULL || handle == NULL) {
        return -1;
    }

    node = (FileNode *)malloc(sizeof(*node));
    if (node == NULL) {
        return -1;
    }

    node->id = list->next_id++;
    node->handle = handle;
    node->next = list->head;
    list->head = node;
    list->count++;

    return node->id;
}

int file_handle_list_remove(FileHandleList *list, int id) {
    FileNode *prev = NULL;
    FileNode *curr;

    if (list == NULL) {
        return -1;
    }

    curr = list->head;
    while (curr != NULL) {
        if (curr->id == id) {
            if (prev == NULL) {
                list->head = curr->next;
            } else {
                prev->next = curr->next;
            }

            if (curr->handle != NULL) {
                fclose(curr->handle);
                curr->handle = NULL;
            }

            free(curr);
            list->count--;
            return 0;
        }

        prev = curr;
        curr = curr->next;
    }

    return -1;
}

void file_handle_list_cleanup(FileHandleList *list) {
    FileNode *curr;
    FileNode *next;

    if (list == NULL) {
        return;
    }

    curr = list->head;
    while (curr != NULL) {
        next = curr->next;

        if (curr->handle != NULL) {
            fclose(curr->handle);
            curr->handle = NULL;
        }

        free(curr);
        curr = next;
    }

    list->head = NULL;
    list->count = 0;
}

static void print_list(const FileHandleList *list) {
    const FileNode *curr;

    if (list == NULL) {
        return;
    }

    printf("Tracked handles: %zu\n", list->count);
    curr = list->head;
    while (curr != NULL) {
        printf("  id=%d handle=%p\n", curr->id, (void *)curr->handle);
        curr = curr->next;
    }
}

int main(void) {
    FileHandleList pool;
    FILE *a;
    FILE *b;
    FILE *c;
    int id_a;
    int id_b;
    int id_c;

    file_handle_list_init(&pool);

    a = tmpfile();
    b = tmpfile();
    c = tmpfile();

    if (a == NULL || b == NULL || c == NULL) {
        perror("tmpfile");
        if (a != NULL) fclose(a);
        if (b != NULL) fclose(b);
        if (c != NULL) fclose(c);
        return 1;
    }

    id_a = file_handle_list_add(&pool, a);
    id_b = file_handle_list_add(&pool, b);
    id_c = file_handle_list_add(&pool, c);

    if (id_a < 0 || id_b < 0 || id_c < 0) {
        fprintf(stderr, "Failed to add file handles to pool\n");
        file_handle_list_cleanup(&pool);
        return 1;
    }

    fputs("alpha\n", a);
    fputs("beta\n", b);
    fputs("gamma\n", c);

    print_list(&pool);

    if (file_handle_list_remove(&pool, id_b) != 0) {
        fprintf(stderr, "Failed to remove handle %d\n", id_b);
        file_handle_list_cleanup(&pool);
        return 1;
    }

    printf("After removing id=%d:\n", id_b);
    print_list(&pool);

    file_handle_list_cleanup(&pool);
    file_handle_list_cleanup(&pool);

    printf("After cleanup called twice:\n");
    print_list(&pool);

    return 0;
}