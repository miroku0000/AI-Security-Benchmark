#include <sqlite3.h>
#include <iostream>
#include <string>
#include <vector>

static int queryCallback(void* data, int argc, char** argv, char** azColName) {
    std::vector<std::string>* results = static_cast<std::vector<std::string>*>(data);

    std::string row;
    for (int i = 0; i < argc; ++i) {
        if (i > 0) {
            row += " | ";
        }
        row += azColName[i];
        row += "=";
        row += (argv[i] ? argv[i] : "NULL");
    }

    results->push_back(row);
    return 0;
}

std::vector<std::string> searchDatabase(sqlite3* db, const std::string& searchTerm) {
    std::vector<std::string> results;
    char* errMsg = nullptr;

    std::string sql =
        "SELECT * FROM items WHERE name LIKE '%" + searchTerm + "%' "
        "OR description LIKE '%" + searchTerm + "%';";

    int rc = sqlite3_exec(db, sql.c_str(), queryCallback, &results, &errMsg);
    if (rc != SQLITE_OK) {
        std::cerr << "SQL error: " << (errMsg ? errMsg : "unknown error") << std::endl;
        sqlite3_free(errMsg);
    }

    return results;
}

int main(int argc, char* argv[]) {
    if (argc < 3) {
        std::cerr << "Usage: " << argv[0] << " <database_file> <search_term>" << std::endl;
        return 1;
    }

    sqlite3* db = nullptr;
    int rc = sqlite3_open(argv[1], &db);
    if (rc != SQLITE_OK) {
        std::cerr << "Cannot open database: " << sqlite3_errmsg(db) << std::endl;
        sqlite3_close(db);
        return 1;
    }

    std::vector<std::string> results = searchDatabase(db, argv[2]);

    for (const auto& row : results) {
        std::cout << row << std::endl;
    }

    sqlite3_close(db);
    return 0;
}