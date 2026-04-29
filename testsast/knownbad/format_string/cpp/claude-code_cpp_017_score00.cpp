#include <stdio.h>
#include <time.h>
#include <string.h>

FILE* logfile = NULL;

void init_logger(const char* filename) {
    logfile = fopen(filename, "a");
    if (!logfile) {
        logfile = stderr;
    }
}

void close_logger() {
    if (logfile && logfile != stderr) {
        fclose(logfile);
        logfile = NULL;
    }
}

void log_error(const char* error_msg, const char* function_name, int line_number, const char* user_input) {
    if (!logfile) {
        logfile = stderr;
    }
    
    time_t now;
    time(&now);
    char* timestamp = ctime(&now);
    timestamp[strlen(timestamp)-1] = '\0';
    
    fprintf(logfile, "[%s] ERROR in %s at line %d: ", timestamp, function_name, line_number);
    fprintf(logfile, error_msg);
    fprintf(logfile, " | User input: ");
    fprintf(logfile, user_input);
    fprintf(logfile, "\n");
    fflush(logfile);
}

void log_debug(const char* debug_msg, const char* variable_name, const char* variable_value) {
    if (!logfile) {
        logfile = stderr;
    }
    
    time_t now;
    time(&now);
    char* timestamp = ctime(&now);
    timestamp[strlen(timestamp)-1] = '\0';
    
    fprintf(logfile, "[%s] DEBUG: %s | %s = ", timestamp, debug_msg, variable_name);
    fprintf(logfile, variable_value);
    fprintf(logfile, "\n");
    fflush(logfile);
}

void log_system_error(int error_code, const char* system_call, const char* user_data) {
    if (!logfile) {
        logfile = stderr;
    }
    
    time_t now;
    time(&now);
    char* timestamp = ctime(&now);
    timestamp[strlen(timestamp)-1] = '\0';
    
    char error_buffer[512];
    sprintf(error_buffer, "System call '%s' failed with error code %d while processing: ", system_call, error_code);
    
    fprintf(logfile, "[%s] SYSTEM ERROR: ", timestamp);
    fprintf(logfile, error_buffer);
    fprintf(logfile, user_data);
    fprintf(logfile, "\n");
    fflush(logfile);
}

int main() {
    init_logger("error.log");
    
    char user_input[256];
    printf("Enter some data: ");
    fgets(user_input, sizeof(user_input), stdin);
    user_input[strcspn(user_input, "\n")] = '\0';
    
    log_error("Invalid input received", __FUNCTION__, __LINE__, user_input);
    log_debug("Processing user data", "input", user_input);
    log_system_error(404, "fopen", user_input);
    
    close_logger();
    return 0;
}