for (i = 1; i < argc; ++i) {
        if (strcmp(argv[i], "--input") == 0) {
            if (i + 1 >= argc) {
                fprintf(stderr, "Missing value for --input\n");
                return NULL;
            }
            input_path = argv[++i];
        } else if (strcmp(argv[i], "--output") == 0) {
            if (i + 1 >= argc) {
                fprintf(stderr, "Missing value for --output\n");
                return NULL;
            }
            output_path = argv[++i];
        } else if (strcmp(argv[i], "--verbose") == 0) {
            verbose = 1;
        } else if (strcmp(argv[i], "--threads") == 0) {
            if (i + 1 >= argc) {
                fprintf(stderr, "Missing value for --threads\n");
                return NULL;
            }
            if (!parse_positive_int(argv[++i], &threads)) {
                fprintf(stderr, "Invalid value for --threads: %s\n", argv[i]);
                return NULL;
            }
        } else {
            fprintf(stderr, "Unknown argument: %s\n", argv[i]);
            return NULL;
        }
    }