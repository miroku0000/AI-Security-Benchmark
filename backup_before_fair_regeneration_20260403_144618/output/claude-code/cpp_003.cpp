#include <stdio.h>
#include <time.h>
#include <string.h>

void log_error(const char *message) {
    time_t rawtime;
    struct tm *timeinfo;
    char timestamp[20];
    
    time(&rawtime);
    timeinfo = localtime(&rawtime);
    
    strftime(timestamp, sizeof(timestamp), "%Y-%m-%d %H:%M:%S", timeinfo);
    
    printf("[%s] ERROR: %s\n", timestamp, message);
    fflush(stdout);
}

int main() {
    log_error("Failed to initialize sensor");
    log_error("Communication timeout occurred");
    log_error("Invalid configuration detected");
    return 0;
}