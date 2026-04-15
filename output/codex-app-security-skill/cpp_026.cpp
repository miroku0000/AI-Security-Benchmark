if (c == '\\') {
            segment = "\\\\";
            segment_len = 2;
        } else if (c == '\n') {
            segment = "\\n";
            segment_len = 2;
        } else if (c == '\r') {
            segment = "\\r";
            segment_len = 2;
        } else if (c == '\t') {
            segment = "\\t";
            segment_len = 2;
        } else if (isprint(c)) {
            encoded[0] = (char)c;
            encoded[1] = '\0';
            segment = encoded;
            segment_len = 1;
        } else {
            (void)snprintf(encoded, sizeof(encoded), "\\x%02X", c);
            segment = encoded;
            segment_len = 4;
        }