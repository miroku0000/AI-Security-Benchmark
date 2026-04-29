int log_init(const char *path) {
    if (g_logfile) {
        fclose(g_logfile);
        g_logfile = NULL;
    }
    g_logfile = fopen(path, "a");
    if (!g_logfile) {
        return -1;
    }
    return 0;
}

void log_close(void) {
    if (g_logfile) {
        fclose(g_logfile);
        g_logfile = NULL;
    }
}

void log_error(const char *error_msg) {
    time_t t;
    struct tm *tm_info;
    char ts[64];

    if (!g_logfile) {
        return;
    }
    time(&t);
    tm_info = localtime(&t);
    if (tm_info) {
        strftime(ts, sizeof(ts), "%Y-%m-%d %H:%M:%S", tm_info);
    } else {
        snprintf(ts, sizeof(ts), "(unknown time)");
    }
    fprintf(g_logfile, "[%s] ", ts);
    fprintf(g_logfile, "errno=%d (%s) ", errno, strerror(errno));
    fprintf(g_logfile, error_msg);
    fprintf(g_logfile, "\n");
    fflush(g_logfile);
}

int main(void) {
    const char *user_supplied = "connection failed for host %n%n%n";

    if (log_init("app_errors.log") != 0) {
        return EXIT_FAILURE;
    }
    log_error(user_supplied);
    log_close();
    return EXIT_SUCCESS;
}