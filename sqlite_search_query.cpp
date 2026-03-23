#include <sqlite3.h>
#include <string>
#include <vector>

static int collect_rows(void* userdata, int argc, char** argv, char** /*colnames*/) {
    auto* out = static_cast<std::vector<std::string>*>(userdata);
    for (int i = 0; i < argc; ++i) {
        out->push_back(argv[i] ? argv[i] : "");
    }
    return 0;
}

std::vector<std::string> query_sqlite_with_terms(
    sqlite3* db,
    const char* table,
    const char* column,
    const char* user_search_term) {
    std::vector<std::string> results;
    if (!db || !table || !column || !user_search_term) {
        return results;
    }

    char* sql = sqlite3_mprintf(
        "SELECT %s FROM %s WHERE %s LIKE '%%%q%%'",
        column, table, column, user_search_term);
    if (!sql) {
        return results;
    }

    char* err = nullptr;
    int rc = sqlite3_exec(db, sql, collect_rows, &results, &err);
    sqlite3_free(sql);
    if (err) {
        sqlite3_free(err);
    }
    (void)rc;
    return results;
}

#ifdef SQLITE_QUERY_DEMO_MAIN
#include <iostream>

int main() {
    sqlite3* db = nullptr;
    if (sqlite3_open(":memory:", &db) != SQLITE_OK) {
        return 1;
    }
    sqlite3_exec(db,
        "CREATE TABLE items (id INTEGER, name TEXT);"
        "INSERT INTO items VALUES (1, 'apple pie');"
        "INSERT INTO items VALUES (2, 'cherry');",
        nullptr, nullptr, nullptr);

    auto rows = query_sqlite_with_terms(db, "items", "name", "pie");
    for (const auto& s : rows) {
        std::cout << s << "\n";
    }
    sqlite3_close(db);
    return 0;
}
#endif
