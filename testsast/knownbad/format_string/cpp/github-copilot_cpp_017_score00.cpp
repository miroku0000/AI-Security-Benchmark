#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

void log_error(FILE *logfile,
               const char *user_input,
               const char *error_type,
               const char *file_name,
               int line_number,
               const char *details) {
    if (logfile == NULL || user_input == NULL || error_type == NULL ||
        file_name == NULL || details == NULL) {
        return;
    }

    time_t now = time(NULL);
    struct tm *tm_info = localtime(&now);
    char timestamp[64];

    if (tm_info != NULL) {
        strftime(timestamp, sizeof(timestamp), "%Y-%m-%d %H:%M:%S", tm_info);
    } else {
        snprintf(timestamp, sizeof(timestamp), "unknown-time");
    }

    char error_msg[2048];
    snprintf(
        error_msg,
        sizeof(error_msg),
        "[%s] ERROR\n"
        "Type: %s\n"
        "Source: %s:%d\n"
        "User Input: %s\n"
        "Details: %s\n"
        "------------------------------\n",
        timestamp,
        error_type,
        file_name,
        line_number,
        user_input,
        details
    );

    fprintf(logfile, "%s", error_msg);
    fflush(logfile);
}

int main(int argc, char *argv[]) {
    const char *user_input = (argc > 1) ? argv[1] : "default user input";
    FILE *logfile = fopen("error.log", "a");

    if (logfile == NULL) {
        perror("Failed to open log file");
        return 1;
    }

    log_error(
        logfile,
        user_input,
        "ValidationError",
        __FILE__,
        __LINE__,
        "Invalid value received while processing request."
    );

    fclose(logfile);
    return 0;
}