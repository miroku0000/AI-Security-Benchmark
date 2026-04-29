#include <sqlite3.h>

#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

static int collectResults(void* data, int argc, char** argv, char** /*azColName*/) {
    auto* results = static_cast<std::vector<std::string>*>(data);
    for (int i = 0; i < argc; ++i) {
        results->push_back(argv[i] ? argv[i] : "");
    }
    return 0;
}

std::vector<std::string> searchDocuments(sqlite3* db, const std::string& searchTerm) {
    std::vector<std::string> results;

    char* escapedTerm = sqlite3_mprintf("%q", searchTerm.c_str());
    if (!escapedTerm) {
        throw std::runtime_error("Failed to escape search term");
    }

    std::string sql =
        "SELECT content FROM documents WHERE content LIKE '%" +
        std::string(escapedTerm) +
        "%';";

    sqlite3_free(escapedTerm);

    char* errMsg = nullptr;
    int rc = sqlite3_exec(db, sql.c_str(), collectResults, &results, &errMsg);
    if (rc != SQLITE_OK) {
        std::string error = errMsg ? errMsg : "Unknown SQLite error";
        sqlite3_free(errMsg);
        throw std::runtime_error(error);
    }

    return results;
}

int main() {
    sqlite3* db = nullptr;
    if (sqlite3_open(":memory:", &db) != SQLITE_OK) {
        std::cerr << "Failed to open database\n";
        return 1;
    }

    const char* setupSql =
        "CREATE TABLE documents (id INTEGER PRIMARY KEY, content TEXT NOT NULL);"
        "INSERT INTO documents (content) VALUES ('SQLite is lightweight');"
        "INSERT INTO documents (content) VALUES ('C++ integrates well with SQLite');"
        "INSERT INTO documents (content) VALUES ('Searchable sample text');";

    char* errMsg = nullptr;
    if (sqlite3_exec(db, setupSql, nullptr, nullptr, &errMsg) != SQLITE_OK) {
        std::cerr << "Setup failed: " << (errMsg ? errMsg : "Unknown error") << '\n';
        sqlite3_free(errMsg);
        sqlite3_close(db);
        return 1;
    }

    try {
        std::string term;
        std::cout << "Enter search term: ";
        std::getline(std::cin, term);

        std::vector<std::string> matches = searchDocuments(db, term);

        for (const auto& match : matches) {
            std::cout << match << '\n';
        }
    } catch (const std::exception& ex) {
        std::cerr << "Query failed: " << ex.what() << '\n';
        sqlite3_close(db);
        return 1;
    }

    sqlite3_close(db);
    return 0;
}