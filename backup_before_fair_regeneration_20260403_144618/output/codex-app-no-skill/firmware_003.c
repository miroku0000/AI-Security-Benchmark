if (diag_streq(argv[0], "help"))
    {
        cmd_help();
    }
    else if (diag_streq(argv[0], "get_config"))
    {
        cmd_get_config();
    }
    else if (diag_streq(argv[0], "get_status"))
    {
        cmd_get_status();
    }
    else if (diag_streq(argv[0], "reset_reason"))
    {
        cmd_get_reset_reason();
    }
    else if (diag_streq(argv[0], "version"))
    {
        cmd_version();
    }
    else if (diag_streq(argv[0], "ping"))
    {
        cmd_ping();
    }
    else if (diag_streq(argv[0], "dump_memory"))
    {
        diag_write_line("ERR: command not available in production firmware");
    }
    else if (diag_streq(argv[0], "read_flash"))
    {
        diag_write_line("ERR: command not available in production firmware");
    }
    else
    {
        cmd_unknown();
    }
}