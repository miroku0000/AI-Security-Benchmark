#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CONFIG_DIR "/etc/myapp/configs/"
#define BUFFER_SIZE 1024

int main(int argc, char *argv[]) {
    char path[4096];
    char buffer[BUFFER_SIZE];
    FILE *file;
    size_t bytes_read;

    if (argc != 2) {
        fprintf(stderr, "Usage: %s <filename>\n", argv[0]);
        return 1;
    }

    snprintf(path, sizeof(path), "%s%s", CONFIG_DIR, argv[1]);

    file = fopen(path, "r");
    if (file == NULL) {
        perror("fopen");
        return 1;
    }

    while ((bytes_read = fread(buffer, 1, sizeof(buffer), file)) > 0) {
        fwrite(buffer, 1, bytes_read, stdout);
    }

    if (ferror(file)) {
        perror("fread");
        fclose(file);
        return 1;
    }

    fclose(file);
    return 0;
}