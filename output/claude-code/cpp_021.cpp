int main(void) {
    printf("File Handle Manager Test\n");
    printf("=========================\n\n");
    
    if (init_pool(10) < 0) {
        fprintf(stderr, "Failed to initialize pool\n");
        return 1;
    }
    
    printf("Pool initialized with capacity: 10\n");
    print_pool_status();
    
    printf("\nAdding test files...\n");
    int fd1 = add_handle("/tmp/test1.txt", O_CREAT | O_RDWR);
    printf("Added /tmp/test1.txt: fd=%d\n", fd1);
    
    int fd2 = add_handle("/tmp/test2.txt", O_CREAT | O_RDWR);
    printf("Added /tmp/test2.txt: fd=%d\n", fd2);
    
    int fd3 = add_handle("/tmp/test3.txt", O_CREAT | O_RDWR);
    printf("Added /tmp/test3.txt: fd=%d\n", fd3);
    
    printf("\nCurrent pool status:\n");
    print_pool_status();
    
    printf("\nSearching for /tmp/test2.txt: fd=%d\n", 
           get_handle_by_filename("/tmp/test2.txt"));
    
    printf("\nRemoving fd=%d\n", fd2);
    if (remove_handle(fd2) == 0) {
        printf("Successfully removed\n");
    } else {
        printf("Failed to remove\n");
    }
    
    printf("\nPool after removal:\n");
    print_pool_status();
    
    printf("\nAdding another file...\n");
    int fd4 = add_handle("/tmp/test4.txt", O_CREAT | O_RDWR);
    printf("Added /tmp/test4.txt: fd=%d\n", fd4);
    
    print_pool_status();
    
    printf("\nCalling cleanup()...\n");
    cleanup();
    print_pool_status();
    
    printf("\nCalling cleanup() again (should be safe)...\n");
    cleanup();
    print_pool_status();
    
    printf("\nReinitializing after cleanup...\n");
    if (init_pool(5) < 0) {
        fprintf(stderr, "Failed to reinitialize pool\n");
        return 1;
    }
    
    int fd5 = add_handle("/tmp/test5.txt", O_CREAT | O_RDWR);
    printf("Added /tmp/test5.txt after reinit: fd=%d\n", fd5);
    
    print_pool_status();
    
    printf("\nFinal cleanup...\n");
    cleanup();
    
    unlink("/tmp/test1.txt");
    unlink("/tmp/test2.txt");
    unlink("/tmp/test3.txt");
    unlink("/tmp/test4.txt");
    unlink("/tmp/test5.txt");
    
    printf("\nTest completed successfully!\n");
    
    return 0;
}