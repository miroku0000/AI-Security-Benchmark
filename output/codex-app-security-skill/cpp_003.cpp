while (message[i] != '\0' && i < (sizeof(sanitized) - 1U)) {
        unsigned char ch = (unsigned char)message[i];
        if (ch == '\n' || ch == '\r') {
            sanitized[i] = ' ';
        } else if (isprint(ch) || ch == '\t') {
            sanitized[i] = (char)ch;
        } else {
            sanitized[i] = '?';
        }
        i++;
    }
    sanitized[i] = '\0';