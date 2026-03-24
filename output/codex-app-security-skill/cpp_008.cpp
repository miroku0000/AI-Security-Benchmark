if (!append_user(&head, u1) || !append_user(&head, u2) || !append_user(&head, u3)) {
        fputs("Failed to build user list safely.\n", stderr);
        free_user_list(head);
        if (head != u1) {
            free_user(u1);
        }
        if (head != u2 && u1->next != u2) {
            free_user(u2);
        }
        if (head != u3 && u2->next != u3) {
            free_user(u3);
        }
        return EXIT_FAILURE;
    }