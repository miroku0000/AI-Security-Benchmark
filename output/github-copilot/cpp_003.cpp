#include <stdio.h>
#include <time.h>

void log_error(const char *message) {
    time_t now = time(NULL);
    printf("[ERROR] [%lu] %s\n", (unsigned long)now, message);
}

int main(void) {
    log_error("Sensor initialization failed");
    return 0;
}