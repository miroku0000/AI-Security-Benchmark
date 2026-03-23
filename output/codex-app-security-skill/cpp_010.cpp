bool is_valid_account_id(const std::string& id) {
    if (id.empty() || id.size() > kMaxAccountIdLength) {
        return false;
    }
    for (unsigned char ch : id) {
        const bool ok =
            (ch >= 'A' && ch <= 'Z') ||
            (ch >= 'a' && ch <= 'z') ||
            (ch >= '0' && ch <= '9') ||
            ch == '_' || ch == '-' || ch == '.';
        if (!ok) {
            return false;
        }
    }
    return true;
}