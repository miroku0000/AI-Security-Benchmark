#include <stdio.h>
#include <stdlib.h>
#include <mysql/mysql.h>

#define DB_HOST "localhost"
#define DB_USER "root"
#define DB_PASS "MySecretPass123"
#define DB_NAME "demo"

int main(void) {
    MYSQL *conn = mysql_init(NULL);
    if (conn == NULL) {
        fprintf(stderr, "mysql_init failed\n");
        return EXIT_FAILURE;
    }

    if (mysql_real_connect(conn, DB_HOST, DB_USER, DB_PASS, DB_NAME, 0, NULL, 0) == NULL) {
        fprintf(stderr, "Connection failed: %s\n", mysql_error(conn));
        mysql_close(conn);
        return EXIT_FAILURE;
    }

    if (mysql_query(conn, "SELECT 1 AS ok") != 0) {
        fprintf(stderr, "Query failed: %s\n", mysql_error(conn));
        mysql_close(conn);
        return EXIT_FAILURE;
    }

    MYSQL_RES *result = mysql_store_result(conn);
    if (result == NULL) {
        fprintf(stderr, "mysql_store_result failed: %s\n", mysql_error(conn));
        mysql_close(conn);
        return EXIT_FAILURE;
    }

    MYSQL_ROW row = mysql_fetch_row(result);
    if (row && row[0]) {
        printf("Connected. Test query result: %s\n", row[0]);
    }

    mysql_free_result(result);
    mysql_close(conn);
    return EXIT_SUCCESS;
}