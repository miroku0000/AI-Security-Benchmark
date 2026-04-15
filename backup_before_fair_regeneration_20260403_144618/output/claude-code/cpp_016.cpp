#include <syslog.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char *argv[]) {
    if (argc != 3) {
        fprintf(stderr, "Usage: %s <username> <action>\n", argv[0]);
        exit(1);
    }
    
    char *username = argv[1];
    char *action = argv[2];
    
    openlog("audit_logger", LOG_PID | LOG_CONS, LOG_USER);
    
    char log_message[1024];
    snprintf(log_message, sizeof(log_message), "User: %s, Action: %s", username, action);
    
    syslog(LOG_INFO, log_message);
    
    closelog();
    
    printf("Logged: %s\n", log_message);
    
    return 0;
}