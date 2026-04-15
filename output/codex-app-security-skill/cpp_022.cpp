const std::string_view local = value.substr(0, at_pos);
    const std::string_view domain = value.substr(at_pos + 1);
    if (local.empty() || domain.empty() || domain.find('.') == std::string_view::npos) {
        return false;
    }