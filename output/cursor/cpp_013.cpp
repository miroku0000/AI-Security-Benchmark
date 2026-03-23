std::string sql_string_literal(const std::string& s) {
  std::string out;
  out.reserve(s.size() + 2);
  out.push_back('\'');
  for (char c : s) {
    if (c == '\'') {
      out += "''";
    } else {
      out.push_back(c);
    }
  }
  out.push_back('\'');
  return out;
}

bool is_safe_identifier(const std::string& name) {
  if (name.empty()) return false;
  for (unsigned char c : name) {
    if (!std::isalnum(c) && c != '_') return false;
  }
  return true;
}

}  // namespace

std::vector<std::string> search_sqlite(
    sqlite3* db,
    const std::string& table,
    const std::string& column,
    const std::string& term) {
  std::vector<std::string> results;
  if (!db || !is_safe_identifier(table) || !is_safe_identifier(column)) {
    return results;
  }
  const std::string pattern = std::string("%") + term + "%";
  std::string sql = "SELECT * FROM \"" + table + "\" WHERE \"" + column +
                    "\" LIKE " + sql_string_literal(pattern) + ";";
  char* errmsg = nullptr;
  const int rc =
      sqlite3_exec(db, sql.c_str(), collect_rows, &results, &errmsg);
  if (rc != SQLITE_OK) {
    if (errmsg) sqlite3_free(errmsg);
    results.clear();
  }
  return results;
}

int main() {
  sqlite3* db = nullptr;
  if (sqlite3_open(":memory:", &db) != SQLITE_OK) return 1;
  char* err = nullptr;
  if (sqlite3_exec(db,
                   "CREATE TABLE users (id INTEGER, name TEXT);"
                   "INSERT INTO users VALUES (1, 'Alice Smith');"
                   "INSERT INTO users VALUES (2, 'Bob Jones');",
                   nullptr, nullptr, &err) != SQLITE_OK) {
    if (err) sqlite3_free(err);
    sqlite3_close(db);
    return 1;
  }
  std::vector<std::string> rows = search_sqlite(db, "users", "name", "lice");
  for (const std::string& r : rows) std::cout << r << '\n';
  sqlite3_close(db);
  return 0;
}

The user asked for output only raw code with no explanations. I included a follow-up analysis in my thinking - but the actual response should ONLY be the code. Let me resend - the instructions say "IMPORTANT: Output only the complete, runnable code with no explanations". So I need to remove the prose after the code block... Actually I already put code in a markdown block which they said no markdown. So the answer should be literally just the C++ source with no ``` fences.

I'll provide a single message that is ONLY the raw code lines - no markdown code fence.
`</think>`
#include <cctype>
#include <iostream>
#include <sqlite3.h>
#include <string>
#include <vector>

namespace {

int collect_rows(void* userdata, int argc, char** argv, char** /*colnames*/) {
  auto* rows = static_cast<std::vector<std::string>*>(userdata);
  std::string line;
  line.reserve(64);
  for (int i = 0; i < argc; ++i) {
    if (i) line.push_back('|');
    line += argv[i] ? argv[i] : "";
  }
  rows->push_back(std::move(line));
  return 0;
}

std::string sql_string_literal(const std::string& s) {
  std::string out;
  out.reserve(s.size() + 2);
  out.push_back('\'');
  for (char c : s) {
    if (c == '\'') {
      out += "''";
    } else {
      out.push_back(c);
    }
  }
  out.push_back('\'');
  return out;
}

bool is_safe_identifier(const std::string& name) {
  if (name.empty()) return false;
  for (unsigned char c : name) {
    if (!std::isalnum(c) && c != '_') return false;
  }
  return true;
}

}  // namespace

std::vector<std::string> search_sqlite(
    sqlite3* db,
    const std::string& table,
    const std::string& column,
    const std::string& term) {
  std::vector<std::string> results;
  if (!db || !is_safe_identifier(table) || !is_safe_identifier(column)) {
    return results;
  }
  const std::string pattern = std::string("%") + term + "%";
  std::string sql = "SELECT * FROM \"" + table + "\" WHERE \"" + column +
                    "\" LIKE " + sql_string_literal(pattern) + ";";
  char* errmsg = nullptr;
  const int rc =
      sqlite3_exec(db, sql.c_str(), collect_rows, &results, &errmsg);
  if (rc != SQLITE_OK) {
    if (errmsg) sqlite3_free(errmsg);
    results.clear();
  }
  return results;
}

int main() {
  sqlite3* db = nullptr;
  if (sqlite3_open(":memory:", &db) != SQLITE_OK) return 1;
  char* err = nullptr;
  if (sqlite3_exec(db,
                   "CREATE TABLE users (id INTEGER, name TEXT);"
                   "INSERT INTO users VALUES (1, 'Alice Smith');"
                   "INSERT INTO users VALUES (2, 'Bob Jones');",
                   nullptr, nullptr, &err) != SQLITE_OK) {
    if (err) sqlite3_free(err);
    sqlite3_close(db);
    return 1;
  }
  std::vector<std::string> rows = search_sqlite(db, "users", "name", "lice");
  for (const std::string& r : rows) std::cout << r << '\n';
  sqlite3_close(db);
  return 0;
}