#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <limits.h>
#include <errno.h>

#define CONFIG_DIR "/etc/myapp/configs"

static int is_valid_filename(const char *name) {
    if (name == NULL || *name == '\0') {
        return 0;
    }

    if (strcmp(name, ".") == 0 || strcmp(name, "..") == 0) {
        return 0;
    }

    for (const char *p = name; *p != '\0'; ++p) {
        if (*p == '/' || *p == '\\') {
            return 0;
        }
    }

    return 1;
}

int main(int argc, char *argv[]) {
    char path[PATH_MAX];
    FILE *fp;
    char buffer[4096];
    size_t bytes_read;

    if (argc != 2) {
        fprintf(stderr, "Usage: %s <filename>\n", argv[0]);
        return EXIT_FAILURE;
    }

    if (!is_valid_filename(argv[1])) {
        fprintf(stderr, "Error: invalid filename\n");
        return EXIT_FAILURE;
    }

    if (snprintf(path, sizeof(path), "%s/%s", CONFIG_DIR, argv[1]) >= (int)sizeof(path)) {
        fprintf(stderr, "Error: path too long\n");
        return EXIT_FAILURE;
    }

    fp = fopen(path, "rb");
    if (fp == NULL) {
        fprintf(stderr, "Error opening '%s': %s\n", path, strerror(errno));
        return EXIT_FAILURE;
    }

    while ((bytes_read = fread(buffer, 1, sizeof(buffer), fp)) > 0) {
        if (fwrite(buffer, 1, bytes_read, stdout) != bytes_read) {
            fprintf(stderr, "Error writing output\n");
            fclose(fp);
            return EXIT_FAILURE;
        }
    }

    if (ferror(fp)) {
        fprintf(stderr, "Error reading '%s'\n", path);
        fclose(fp);
        return EXIT_FAILURE;
    }

    fclose(fp);
    return EXIT_SUCCESS;
}