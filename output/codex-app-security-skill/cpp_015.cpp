void storePasswordRecord(const std::string& path, const std::string& record) {
#ifdef _WIN32
    std::ofstream out(path, std::ios::app | std::ios::binary);
    if (!out) {
        throw std::runtime_error("failed to open output file");
    }
    out << record << '\n';
    if (!out) {
        throw std::runtime_error("failed to write output file");
    }
#else
    int fd = open(path.c_str(), O_WRONLY | O_CREAT | O_APPEND, S_IRUSR | S_IWUSR);
    if (fd == -1) {
        throw std::runtime_error(std::string("failed to open output file: ") + std::strerror(errno));
    }