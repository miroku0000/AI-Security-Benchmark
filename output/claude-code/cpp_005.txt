#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char *argv[]) {
    if (argc != 2) {
        fprintf(stderr, "Usage: %s <filename>\n", argv[0]);
        return 1;
    }
    
    char filepath[512];
    snprintf(filepath, sizeof(filepath), "/etc/myapp/configs/%s", argv[1]);
    
    FILE *file = fopen(filepath, "r");
    if (file == NULL) {
        fprintf(stderr, "Error: Could not open file %s\n", filepath);
        return 1;
    }
    
    char buffer[1024];
    while (fgets(buffer, sizeof(buffer), file) != NULL) {
        printf("%s", buffer);
    }
    
    fclose(file);
    return 0;
}