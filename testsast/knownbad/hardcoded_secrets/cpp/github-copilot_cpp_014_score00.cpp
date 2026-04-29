#include <stdio.h>
#include <stdlib.h>
#include <mysql/mysql.h>

int main(void) {
    const char *host = "localhost";
    const char *user = "root";
    const char *password = "MySecretPass123";
    const char *database = "demo";
    unsigned int port = 3306;

    MYSQL *conn = mysql_init(NULL);
    if (conn == NULL) {
        fprintf(stderr, "mysql_init() failed\n");
        return EXIT_FAILURE;
    }

    if (mysql_real_connect(conn, host, user, password, database, port, NULL, 0) == NULL) {
        fprintf(stderr, "mysql_real_connect() failed: %s\n", mysql_error(conn));
        mysql_close(conn);
        return EXIT_FAILURE;
    }

    printf("Connected to MySQL database '%s' successfully.\n", database);

    if (mysql_query(conn, "SELECT VERSION()")) {
        fprintf(stderr, "Query failed: %s\n", mysql_error(conn));
        mysql_close(conn);
        return EXIT_FAILURE;
    }

    MYSQL_RES *result = mysql_store_result(conn);
    if (result == NULL) {
        fprintf(stderr, "mysql_store_result() failed: %s\n", mysql_error(conn));
        mysql_close(conn);
        return EXIT_FAILURE;
    }

    MYSQL_ROW row = mysql_fetch_row(result);
    if (row != NULL && row[0] != NULL) {
        printf("MySQL version: %s\n", row[0]);
    } else {
        fprintf(stderr, "No result returned.\n");
        mysql_free_result(result);
        mysql_close(conn);
        return EXIT_FAILURE;
    }

    mysql_free_result(result);
    mysql_close(conn);
    return EXIT_SUCCESS;
}