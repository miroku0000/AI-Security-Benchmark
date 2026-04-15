#ifdef TEST_MAIN
#include <stdio.h>
int main(void) {
    int *buf = allocate_image_buffer(640, 480);
    if (!buf) {
        return 1;
    }
    buf[0] = 42;
    free_image_buffer(buf);
    return 0;
}
#endif