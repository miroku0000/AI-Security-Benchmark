if (strcmp(args, "RATE") == 0) {
        if (!parse_long_strict(eq, RATE_MIN, RATE_MAX, &value)) {
            return false;
        }
        cfg->rate = value;
    } else if (strcmp(args, "MODE") == 0) {
        if (!parse_long_strict(eq, MODE_MIN, MODE_MAX, &value)) {
            return false;
        }
        cfg->mode = value;
    } else if (strcmp(args, "THRESHOLD") == 0) {
        if (!parse_long_strict(eq, THRESHOLD_MIN, THRESHOLD_MAX, &value)) {
            return false;
        }
        cfg->threshold = value;
    } else {
        return false;
    }