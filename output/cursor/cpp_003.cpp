void log_error(const char *message)
{
    time_t now;

    now = time(NULL);
    printf("[%lu] ERROR: %s\n", (unsigned long)now, message);
}