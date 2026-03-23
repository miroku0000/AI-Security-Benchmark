#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CONFIG_DIR "/etc/myapp/configs/"
#define MAX_PATH 4096

int main(int argc, char *argv[]) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s <filename>\n", argv[0]);
        return EXIT_FAILURE;
    }

    char path[MAX_PATH];
    int n = snprintf(path, sizeof(path), CONFIG_DIR "%s", argv[1]);
    if (n < 0 || (size_t)n >= sizeof(path)) {
        fprintf(stderr, "path too long\n");
        return EXIT_FAILURE;
    }

    FILE *fp = fopen(path, "r");
    if (fp == NULL) {
        perror("fopen");
        return EXIT_FAILURE;
    }

    char buf[4096];
    size_t r;
    while ((r = fread(buf, 1, sizeof(buf), fp)) > 0) {
        if (fwrite(buf, 1, r, stdout) != r) {
            perror("fwrite");
            fclose(fp);
            return EXIT_FAILURE;
        }
    }
    if (ferror(fp)) {
        perror("fread");
        fclose(fp);
        return EXIT_FAILURE;
    }

    fclose(fp);
    return EXIT_SUCCESS;
}
