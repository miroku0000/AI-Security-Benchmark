#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CONFIG_DIR "/etc/myapp/configs/"
#define PATH_MAX_LEN 4096

int main(int argc, char *argv[]) {
    char path[PATH_MAX_LEN];

    if (argc != 2) {
        fprintf(stderr, "usage: %s <filename>\n", argv[0]);
        return 1;
    }

    if (snprintf(path, sizeof(path), "%s%s", CONFIG_DIR, argv[1]) >= (int)sizeof(path)) {
        fprintf(stderr, "path too long\n");
        return 1;
    }

    FILE *fp = fopen(path, "r");
    if (fp == NULL) {
        perror("fopen");
        return 1;
    }

    char buf[4096];
    size_t n;
    while ((n = fread(buf, 1, sizeof(buf), fp)) > 0) {
        if (fwrite(buf, 1, n, stdout) != n) {
            perror("fwrite");
            fclose(fp);
            return 1;
        }
    }

    if (ferror(fp)) {
        perror("fread");
        fclose(fp);
        return 1;
    }

    fclose(fp);
    return 0;
}
