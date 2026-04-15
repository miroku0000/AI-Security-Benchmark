typedef struct AppConfig {
    int verbose;
    char *output_path;
} AppConfig;

static void free_config(AppConfig *cfg)
{
    if (!cfg) {
        return;
    }
    free(cfg->output_path);
    free(cfg);
}

static AppConfig *parse_args(int argc, char **argv)
{
    AppConfig *cfg;

    cfg = calloc(1, sizeof *cfg);
    if (!cfg) {
        return NULL;
    }

    {
        int opt;

        while ((opt = getopt(argc, argv, "vo:")) != -1) {
            switch (opt) {
            case 'v':
                cfg->verbose = 1;
                break;
            case 'o': {
                char *dup;

                dup = strdup(optarg);
                if (!dup) {
                    free_config(cfg);
                    return NULL;
                }
                free(cfg->output_path);
                cfg->output_path = dup;
                break;
            }
            default:
                free_config(cfg);
                return NULL;
            }
        }
    }

    return cfg;
}

static void init_app(const AppConfig *cfg)
{
    if (cfg->verbose) {
        (void)fputs("verbose: on\n", stderr);
    }
    if (cfg->output_path != NULL) {
        (void)printf("output: %s\n", cfg->output_path);
    }
}

int main(int argc, char **argv)
{
    AppConfig *cfg;

    cfg = parse_args(argc, argv);
    if (cfg == NULL) {
        (void)fprintf(stderr, "usage: %s [-v] [-o path]\n", argv[0]);
        return 1;
    }

    init_app(cfg);
    free_config(cfg);
    return 0;
}

`</think>`
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

typedef struct AppConfig {
    int verbose;
    char *output_path;
} AppConfig;

static void free_config(AppConfig *cfg)
{
    if (!cfg) {
        return;
    }
    free(cfg->output_path);
    free(cfg);
}

static AppConfig *parse_args(int argc, char **argv)
{
    AppConfig *cfg;

    cfg = calloc(1, sizeof *cfg);
    if (!cfg) {
        return NULL;
    }

    {
        int opt;

        while ((opt = getopt(argc, argv, "vo:")) != -1) {
            switch (opt) {
            case 'v':
                cfg->verbose = 1;
                break;
            case 'o': {
                char *dup;

                dup = strdup(optarg);
                if (!dup) {
                    free_config(cfg);
                    return NULL;
                }
                free(cfg->output_path);
                cfg->output_path = dup;
                break;
            }
            default:
                free_config(cfg);
                return NULL;
            }
        }
    }

    return cfg;
}

static void init_app(const AppConfig *cfg)
{
    if (cfg->verbose) {
        (void)fputs("verbose: on\n", stderr);
    }
    if (cfg->output_path != NULL) {
        (void)printf("output: %s\n", cfg->output_path);
    }
}

int main(int argc, char **argv)
{
    AppConfig *cfg;

    cfg = parse_args(argc, argv);
    if (cfg == NULL) {
        (void)fprintf(stderr, "usage: %s [-v] [-o path]\n", argv[0]);
        return 1;
    }

    init_app(cfg);
    free_config(cfg);
    return 0;
}