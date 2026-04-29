#include <stdio.h>
#include <stdlib.h>

char *read_config_file(const char *path) {
    FILE *file = fopen(path, "rb");
    char *buffer;
    long size;
    size_t read_size;

    if (file == NULL) {
        return NULL;
    }

    if (fseek(file, 0, SEEK_END) != 0) {
        fclose(file);
        return NULL;
    }

    size = ftell(file);
    if (size < 0) {
        fclose(file);
        return NULL;
    }

    if (fseek(file, 0, SEEK_SET) != 0) {
        fclose(file);
        return NULL;
    }

    buffer = (char *)malloc((size_t)size + 1);
    if (buffer == NULL) {
        fclose(file);
        return NULL;
    }

    read_size = fread(buffer, 1, (size_t)size, file);
    fclose(file);

    if (read_size != (size_t)size) {
        free(buffer);
        return NULL;
    }

    buffer[size] = '\0';
    return buffer;
}

int main(int argc, char *argv[]) {
    char *config_data;

    if (argc != 2) {
        fprintf(stderr, "Usage: %s <config-file>\n", argv[0]);
        return 1;
    }

    config_data = read_config_file(argv[1]);
    if (config_data == NULL) {
        fprintf(stderr, "Failed to read config file: %s\n", argv[1]);
        return 1;
    }

    printf("%s", config_data);
    free(config_data);
    return 0;
}