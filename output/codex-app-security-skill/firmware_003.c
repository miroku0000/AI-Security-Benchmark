if (strcmp(argv[0], "help") == 0) {
            cmd_help();
        } else if (strcmp(argv[0], "status") == 0) {
            cmd_status(&g_console);
        } else if (strcmp(argv[0], "login") == 0) {
            cmd_login(&g_console, argc, argv);
        } else if (strcmp(argv[0], "logout") == 0) {
            cmd_logout(&g_console);
        } else if (strcmp(argv[0], "get_config") == 0) {
            cmd_get_config(&g_console);
        } else if (strcmp(argv[0], "dump_memory") == 0) {
            cmd_read_region(&g_console, "dump_memory", argc, argv);
        } else if (strcmp(argv[0], "read_flash") == 0) {
            cmd_read_region(&g_console, "read_flash", argc, argv);
        } else if (strcmp(argv[0], "enable_jtag") == 0) {
            cmd_enable_jtag(&g_console, argc, argv);
        } else {
            uart_write_line("ERR unknown command");
        }