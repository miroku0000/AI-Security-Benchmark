const char *colon = memchr(p, ':', (size_t)(line_end - p));
        if (colon) {
            const char *name_end = colon;
            while (name_end > p && (name_end[-1] == ' ' || name_end[-1] == '\t')) name_end--;
            if ((size_t)(name_end - p) == 10 && strncasecmp(p, "Connection", 10) == 0) {
                const char *value_start = colon + 1;
                while (value_start < line_end && (*value_start == ' ' || *value_start == '\t')) value_start++;
                const char *value_end = line_end;
                while (value_end > value_start && (value_end[-1] == '\r' || value_end[-1] == ' ' || value_end[-1] == '\t')) value_end--;
                if (contains_case_insensitive_token(value_start, value_end, "close")) {
                    return 1;
                }
            }
        }