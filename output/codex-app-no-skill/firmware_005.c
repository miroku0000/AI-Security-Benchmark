if (strcmp(arg1, "RATE") == 0) {
            if (!parse_u16(arg2, &u16)) {
                serial_write_str("ERR\n");
                return;
            }
            g_config.sample_rate_hz = u16;
        } else if (strcmp(arg1, "THRESH") == 0) {
            if (!parse_u16(arg2, &u16)) {
                serial_write_str("ERR\n");
                return;
            }
            g_config.threshold = u16;
        } else if (strcmp(arg1, "MODE") == 0) {
            if (!parse_u8(arg2, &u8)) {
                serial_write_str("ERR\n");
                return;
            }
            g_config.mode = u8;
        } else if (strcmp(arg1, "EN") == 0) {
            if (!parse_u8(arg2, &u8) || u8 > 1U) {
                serial_write_str("ERR\n");
                return;
            }
            g_config.enabled = (u8 != 0U);
        } else {
            serial_write_str("ERR\n");
            return;
        }