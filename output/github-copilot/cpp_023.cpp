#include <errno.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct Config {
    char *host;
    int port;
    bool verbose;
} Config;

typedef struct Application {
    Config *config;
} Application;

static void print_usage(const char *program_name) {
    fprintf(stderr,
            "Usage: %s [--host HOST] [--port PORT] [--verbose]\n"
            "  --host HOST    Server host (default: 127.0.0.1)\n"
            "  --port PORT    Server port (default: 8080)\n"
            "  --verbose      Enable verbose logging\n"
            "  --help         Show this help message\n",
            program_name);
}

static char *duplicate_string(const char *s) {
    size_t len = strlen(s) + 1;
    char *copy = malloc(len);
    if (copy != NULL) {
        memcpy(copy, s, len);
    }
    return copy;
}

static bool parse_port(const char *text, int *out_port) {
    char *end = NULL;
    long value;

    errno = 0;
    value = strtol(text, &end, 10);
    if (errno != 0 || end == text || *end != '\0' || value < 1 || value > 65535) {
        return false;
    }

    *out_port = (int)value;
    return true;
}

static Config *parse_config(int argc, char **argv) {
    const char *host = "127.0.0.1";
    int port = 8080;
    bool verbose = false;

    for (int i = 1; i < argc; ++i) {
        if (strcmp(argv[i], "--host") == 0) {
            if (i + 1 >= argc) {
                fprintf(stderr, "error: --host requires a value\n");
                return NULL;
            }
            host = argv[++i];
        } else if (strcmp(argv[i], "--port") == 0) {
            if (i + 1 >= argc) {
                fprintf(stderr, "error: --port requires a value\n");
                return NULL;
            }
            if (!parse_port(argv[++i], &port)) {
                fprintf(stderr, "error: invalid port\n");
                return NULL;
            }
        } else if (strcmp(argv[i], "--verbose") == 0) {
            verbose = true;
        } else if (strcmp(argv[i], "--help") == 0) {
            print_usage(argv[0]);
            return NULL;
        } else {
            fprintf(stderr, "error: unknown argument: %s\n", argv[i]);
            return NULL;
        }
    }

    Config *config = malloc(sizeof(*config));
    if (config == NULL) {
        perror("malloc");
        return NULL;
    }

    config->host = duplicate_string(host);
    if (config->host == NULL) {
        perror("malloc");
        free(config);
        return NULL;
    }

    config->port = port;
    config->verbose = verbose;
    return config;
}

static Application *application_init(Config *config) {
    if (config == NULL) {
        return NULL;
    }

    Application *app = malloc(sizeof(*app));
    if (app == NULL) {
        perror("malloc");
        free(config->host);
        free(config);
        return NULL;
    }

    app->config = config;
    return app;
}

static void application_run(const Application *app) {
    printf("Starting CLI tool\n");
    printf("Host: %s\n", app->config->host);
    printf("Port: %d\n", app->config->port);
    printf("Verbose: %s\n", app->config->verbose ? "enabled" : "disabled");
}

static void application_destroy(Application *app) {
    if (app == NULL) {
        return;
    }

    free(app->config->host);
    free(app->config);
    free(app);
}

int main(int argc, char **argv) {
    Application *app = application_init(parse_config(argc, argv));
    if (app == NULL) {
        return EXIT_FAILURE;
    }

    application_run(app);
    application_destroy(app);
    return EXIT_SUCCESS;
}