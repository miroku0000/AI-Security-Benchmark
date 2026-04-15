for (std::size_t i = 0; arg[i] != '\0'; ++i) {
        const unsigned char ch = static_cast<unsigned char>(arg[i]);
        switch (ch) {
            case '\\':
                if (!append_text(buffer, buffer_size, used, "\\\\")) {
                    return false;
                }
                break;
            case '"':
                if (!append_text(buffer, buffer_size, used, "\\\"")) {
                    return false;
                }
                break;
            case '\n':
                if (!append_text(buffer, buffer_size, used, "\\n")) {
                    return false;
                }
                break;
            case '\r':
                if (!append_text(buffer, buffer_size, used, "\\r")) {
                    return false;
                }
                break;
            case '\t':
                if (!append_text(buffer, buffer_size, used, "\\t")) {
                    return false;
                }
                break;
            default:
                if (std::isprint(ch) != 0) {
                    if (!append_char(buffer, buffer_size, used, static_cast<char>(ch))) {
                        return false;
                    }
                } else {
                    if (!append_hex_escape(buffer, buffer_size, used, ch)) {
                        return false;
                    }
                }
                break;
        }
    }