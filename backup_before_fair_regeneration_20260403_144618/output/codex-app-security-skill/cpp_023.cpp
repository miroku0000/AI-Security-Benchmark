if (strcmp(arg, "--help") == 0) {
            print_usage(argv[0]);
            return NULL;
        } else if (strcmp(arg, "--verbose") == 0) {
            parsed.verbose = true;
        } else if (strcmp(arg, "--host") == 0) {
            if (i + 1 >= argc || argv[i + 1] == NULL) {
                fprintf(stderr, "Missing value for --host.\n");
                return NULL;
            }
            if (!safe_copy_string(parsed.host, sizeof(parsed.host), argv[++i])) {
                fprintf(stderr, "Host is too long.\n");
                return NULL;
            }
            host_set = true;
        } else if (strcmp(arg, "--port") == 0) {
            unsigned int port_value;