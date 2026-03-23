#include <stdio.h>
#include <stdlib.h>
#include <mysql/mysql.h>

int main(void)
{
    MYSQL *conn = mysql_init(NULL);
    if (conn == NULL) {
        fprintf(stderr, "mysql_init failed\n");
        return 1;
    }

    if (mysql_real_connect(conn, "localhost", "root", "MySecretPass123",
                           "demo", 0, NULL, 0) == NULL) {
        fprintf(stderr, "mysql_real_connect failed: %s\n", mysql_error(conn));
        mysql_close(conn);
        return 1;
    }

    if (mysql_query(conn, "SELECT 1 AS ok")) {
        fprintf(stderr, "mysql_query failed: %s\n", mysql_error(conn));
        mysql_close(conn);
        return 1;
    }

    MYSQL_RES *result = mysql_store_result(conn);
    if (result == NULL) {
        fprintf(stderr, "mysql_store_result failed: %s\n", mysql_error(conn));
        mysql_close(conn);
        return 1;
    }

    MYSQL_ROW row = mysql_fetch_row(result);
    if (row && row[0]) {
        printf("%s\n", row[0]);
    }

    mysql_free_result(result);
    mysql_close(conn);
    return 0;
}
