#include <errno.h>
#include <inttypes.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

static int parse_size_arg(const char *input, size_t *out_value) {
    char *end = NULL;
    uintmax_t value;

    if (input == NULL || out_value == NULL || input[0] == '\0') {
        return 0;
    }

    errno = 0;
    value = strtoumax(input, &end, 10);

    if (errno != 0 || end == input || *end != '\0') {
        return 0;
    }

    if (value == 0 || value > SIZE_MAX) {
        return 0;
    }

    *out_value = (size_t)value;
    return 1;
}

static int *allocate_image_buffer(size_t width, size_t height) {
    size_t pixel_count;

    if (width == 0 || height == 0) {
        return NULL;
    }

    if (width > SIZE_MAX / height) {
        return NULL;
    }
    pixel_count = width * height;

    if (pixel_count > SIZE_MAX / sizeof(int)) {
        return NULL;
    }

    return (int *)calloc(pixel_count, sizeof(int));
}

int main(int argc, char *argv[]) {
    size_t width, height;
    int *image = NULL;

    if (argc != 3) {
        fprintf(stderr, "Usage: %s <width> <height>\n", argv[0]);
        return EXIT_FAILURE;
    }

    if (!parse_size_arg(argv[1], &width) || !parse_size_arg(argv[2], &height)) {
        fprintf(stderr, "Invalid dimensions. Width and height must be positive integers within range.\n");
        return EXIT_FAILURE;
    }

    image = allocate_image_buffer(width, height);
    if (image == NULL) {
        fprintf(stderr, "Allocation failed. Dimensions may be too large.\n");
        return EXIT_FAILURE;
    }

    printf("Allocated buffer for %zu x %zu image (%zu bytes)\n",
           width, height, width * height * sizeof(int));

    free(image);
    return EXIT_SUCCESS;
}