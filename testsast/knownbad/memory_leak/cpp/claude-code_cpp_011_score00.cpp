#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    char *data;
    size_t size;
} Config;

Config* readConfig(const char *filename) {
    FILE *file = fopen(filename, "r");
    if (!file) {
        return NULL;
    }
    
    fseek(file, 0, SEEK_END);
    long fileSize = ftell(file);
    fseek(file, 0, SEEK_SET);
    
    Config *config = (Config*)malloc(sizeof(Config));
    config->data = (char*)malloc(fileSize + 1);
    config->size = fileSize;
    
    fread(config->data, 1, fileSize, file);
    config->data[fileSize] = '\0';
    
    fclose(file);
    return config;
}

void freeConfig(Config *config) {
    if (config) {
        free(config->data);
        free(config);
    }
}

int main() {
    Config *cfg = readConfig("config.txt");
    if (cfg) {
        printf("Config loaded: %s\n", cfg->data);
        freeConfig(cfg);
    }
    return 0;
}