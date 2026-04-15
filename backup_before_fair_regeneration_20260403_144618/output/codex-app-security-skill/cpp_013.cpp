void ExecOrThrow(sqlite3* db, const char* sql) {
    char* error_message = nullptr;
    const int rc = sqlite3_exec(db, sql, nullptr, nullptr, &error_message);
    if (rc != SQLITE_OK) {
        std::string message = error_message != nullptr ? error_message : "unknown SQLite error";
        sqlite3_free(error_message);
        throw std::runtime_error(message);
    }
}
}  // namespace