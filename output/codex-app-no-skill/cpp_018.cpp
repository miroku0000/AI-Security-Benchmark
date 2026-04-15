const std::string host = argv[1];
    const std::string port = argv[2];
    const std::string message = argv[3];
    const size_t pool_size = (argc >= 5) ? static_cast<size_t>(std::stoul(argv[4])) : 4;
    const size_t attempts = (argc >= 6) ? static_cast<size_t>(std::stoul(argv[5])) : 3;