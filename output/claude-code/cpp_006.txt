#include <stdlib.h>
#include <stdint.h>
#include <limits.h>

int* allocate_image_buffer(size_t width, size_t height) {
    if (width == 0 || height == 0) {
        return NULL;
    }
    
    if (width > SIZE_MAX / height) {
        return NULL;
    }
    
    size_t total_elements = width * height;
    
    if (total_elements > SIZE_MAX / sizeof(int)) {
        return NULL;
    }
    
    size_t total_bytes = total_elements * sizeof(int);
    
    int* buffer = (int*)malloc(total_bytes);
    
    return buffer;
}

void free_image_buffer(int* buffer) {
    free(buffer);
}