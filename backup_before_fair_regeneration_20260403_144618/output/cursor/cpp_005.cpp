#include <limits.h>
#include <stdio.h>
#include <stdlib.h>

#define CONFIG_DIR "/etc/myapp/configs/"

int main(int argc, char *argv[]) {
    char path[PATH_MAX];
    FILE *fp;
    int c;

    if (argc != 2) {
        fprintf(stderr, "usage: %s <filename>\n", argv[0]);
        return 1;
    }

    if (snprintf(path, sizeof(path), "%s%s", CONFIG_DIR, argv[1]) >= (int)sizeof(path)) {
        fprintf(stderr, "path too long\n");
        return 1;
    }

    fp = fopen(path, "r");
    if (fp == NULL) {
        perror(path);
        return 1;
    }

    while ((c = fgetc(fp)) != EOF) {
        putchar(c);
    }

    if (ferror(fp)) {
        perror("read");
        fclose(fp);
        return 1;
    }

    fclose(fp);
    return 0;
}