std::size_t start = 0;
    while (start < host.size()) {
        const std::size_t dot = host.find('.', start);
        const std::size_t end = (dot == std::string::npos) ? host.size() : dot;
        const std::string label = host.substr(start, end - start);