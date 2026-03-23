for (int i = 1; i < argc; ++i) {
        const char* arg = argv[i] ? argv[i] : "";
        std::size_t currentLen = std::strlen(outBuffer);
        std::size_t argLen = std::strlen(arg);
        std::size_t needed = currentLen + (currentLen > 0 ? 1 : 0) + argLen + 1;