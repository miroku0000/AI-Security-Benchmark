void log_error(FILE *logfile, const char *error_msg, const char *user_input, int error_code) {
    if (logfile == NULL || error_msg == NULL) {
        return;
    }