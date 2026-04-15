#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <syslog.h>

int main(int argc, char *argv[]) {
    if (argc != 3) {
        fprintf(stderr, "Usage: %s <username> <action>\n", argv[0]);
        return 1;
    }

    const char *username = argv[1];
    const char *action = argv[2];

    size_t needed = snprintf(NULL, 0, "audit user=%s action=%s", username, action) + 1;
    char *user_message = malloc(needed);
    if (user_message == NULL) {
        fprintf(stderr, "Memory allocation failed\n");
        return 1;
    }

    snprintf(user_message, needed, "audit user=%s action=%s", username, action);

    openlog("audit_logger", LOG_PID | LOG_NDELAY, LOG_USER);
    syslog(LOG_INFO, "%s", user_message);
    closelog();

    free(user_message);
    return 0;
}