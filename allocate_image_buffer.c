#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>

int *allocate_image_buffer(int width, int height)
{
    size_t n;

    if (width <= 0 || height <= 0) {
        return NULL;
    }
    n = (size_t)width * (size_t)height;
    if (n / (size_t)width != (size_t)height) {
        return NULL;
    }
    return (int *)malloc(n * sizeof(int));
}

int main(void)
{
    int *buf = allocate_image_buffer(640, 480);

    if (buf == NULL) {
        return 1;
    }
    free(buf);
    return 0;
}
