Config* parse_arguments(int argc, char* argv[]) {
    Config* config = (Config*)malloc(sizeof(Config));
    
    config->input_file = NULL;
    config->output_file = NULL;
    config->verbose_level = 0;
    config->debug_mode = false;
    config->max_threads = 4;
    config->log_file = NULL;
    
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "-i") == 0 || strcmp(argv[i], "--input") == 0) {
            if (i + 1 < argc) {
                config->input_file = (char*)malloc(strlen(argv[++i]) + 1);
                strcpy(config->input_file, argv[i]);
            }
        }
        else if (strcmp(argv[i], "-o") == 0 || strcmp(argv[i], "--output") == 0) {
            if (i + 1 < argc) {
                config->output_file = (char*)malloc(strlen(argv[++i]) + 1);
                strcpy(config->output_file, argv[i]);
            }
        }
        else if (strcmp(argv[i], "-v") == 0 || strcmp(argv[i], "--verbose") == 0) {
            config->verbose_level++;
        }
        else if (strcmp(argv[i], "-d") == 0 || strcmp(argv[i], "--debug") == 0) {
            config->debug_mode = true;
        }
        else if (strcmp(argv[i], "-t") == 0 || strcmp(argv[i], "--threads") == 0) {
            if (i + 1 < argc) {
                config->max_threads = atoi(argv[++i]);
            }
        }
        else if (strcmp(argv[i], "-l") == 0 || strcmp(argv[i], "--log") == 0) {
            if (i + 1 < argc) {
                config->log_file = (char*)malloc(strlen(argv[++i]) + 1);
                strcpy(config->log_file, argv[i]);
            }
        }
        else if (strcmp(argv[i], "-h") == 0 || strcmp(argv[i], "--help") == 0) {
            free(config);
            return NULL;
        }
    }
    
    return config;
}