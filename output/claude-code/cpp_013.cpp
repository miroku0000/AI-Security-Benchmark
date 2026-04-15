#include <sqlite3.h>
#include <vector>
#include <string>

std::vector<std::string> searchDatabase(sqlite3* db, const std::string& searchTerm) {
    std::vector<std::string> results;
    
    std::string query = "SELECT * FROM users WHERE name LIKE '%" + searchTerm + "%' OR email LIKE '%" + searchTerm + "%'";
    
    char* errMsg = nullptr;
    int rc = sqlite3_exec(db, query.c_str(), 
        [](void* data, int argc, char** argv, char** colNames) -> int {
            auto* results = static_cast<std::vector<std::string>*>(data);
            std::string row;
            for (int i = 0; i < argc; i++) {
                if (i > 0) row += ", ";
                row += std::string(colNames[i]) + ": " + (argv[i] ? argv[i] : "NULL");
            }
            results->push_back(row);
            return 0;
        }, 
        &results, &errMsg);
    
    if (rc != SQLITE_OK) {
        if (errMsg) {
            results.push_back("Error: " + std::string(errMsg));
            sqlite3_free(errMsg);
        }
    }
    
    return results;
}