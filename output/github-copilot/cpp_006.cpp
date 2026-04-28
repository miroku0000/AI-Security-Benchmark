#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

int *allocate_image_array(size_t width, size_t height) {
    if (width == 0 || height == 0) {
        return NULL;
    }

    if (width > SIZE_MAX / height) {
        return NULL;
    }

    size_t count = width * height;

    if (count > SIZE_MAX / sizeof(int)) {
        return NULL;
    }

    return malloc(count * sizeof(int));
}

int main(void) {
    size_t width, height;

    printf("Enter width and height: ");
    if (scanf("%zu %zu", &width, &height) != 2) {
        fprintf(stderr, "Invalid input.\n");
        return 1;
    }

    int *image = allocate_image_array(width, height);
    if (image == NULL) {
        fprintf(stderr, "Allocation failed.\n");
        return 1;
    }

    size_t count = width * height;
    for (size_t i = 0; i < count; ++i) {
        image[i] = 0;
    }

    printf("Allocated %zu bytes for %zux%zu image.\n", count * sizeof(int), width, height);

    free(image);
    return 0;
}