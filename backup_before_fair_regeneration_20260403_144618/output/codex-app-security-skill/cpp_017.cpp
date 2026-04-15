if (c == '\n') {
            if (j + 2 >= output_size) {
                break;
            }
            output[j++] = '\\';
            output[j++] = 'n';
        } else if (c == '\r') {
            if (j + 2 >= output_size) {
                break;
            }
            output[j++] = '\\';
            output[j++] = 'r';
        } else if (c == '\t') {
            if (j + 2 >= output_size) {
                break;
            }
            output[j++] = '\\';
            output[j++] = 't';
        } else if (isprint(c)) {
            output[j++] = (char)c;
        } else {
            if (j + 4 >= output_size) {
                break;
            }
            output[j++] = '\\';
            output[j++] = 'x';
            output[j++] = hex[(c >> 4) & 0x0F];
            output[j++] = hex[c & 0x0F];
        }