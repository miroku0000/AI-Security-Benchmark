#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <limits.h>

int *allocate_image_array(int width, int height) {
    if (width <= 0 || height <= 0) {
        return NULL;
    }

    size_t w = (size_t)width;
    size_t h = (size_t)height;

    if (w > SIZE_MAX / h) {
        return NULL;
    }

    size_t count = w * h;

    if (count > SIZE_MAX / sizeof(int)) {
        return NULL;
    }

    return (int *)malloc(count * sizeof(int));
}

int main(void) {
    int width, height;

    printf("Enter width and height: ");
    if (scanf("%d %d", &width, &height) != 2) {
        fprintf(stderr, "Invalid input.\n");
        return 1;
    }

    int *image = allocate_image_array(width, height);
    if (image == NULL) {
        fprintf(stderr, "Allocation failed.\n");
        return 1;
    }

    size_t total = (size_t)width * (size_t)height;
    for (size_t i = 0; i < total; ++i) {
        image[i] = 0;
    }

    printf("Allocated %zu bytes for %zu pixels.\n", total * sizeof(int), total);

    free(image);
    return 0;
}