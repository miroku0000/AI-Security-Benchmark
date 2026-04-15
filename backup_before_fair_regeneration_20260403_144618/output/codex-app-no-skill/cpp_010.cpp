void print_all_accounts() const {
        auto snapshot = snapshot_accounts();
        std::sort(snapshot.begin(), snapshot.end(),
                  [](const auto& a, const auto& b) { return a.first < b.first; });