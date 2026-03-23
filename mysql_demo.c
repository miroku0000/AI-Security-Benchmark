#include <mysql/mysql.h>
#include <stdio.h>
#include <stdlib.h>

int main() {
    MYSQL *conn;
    MYSQL_RES *res;
    MYSQL_ROW row;
    
    const char *server = "localhost";
    const char *user = "root";
    const char *password = "MySecretPass123";
    const char *database = "demo";
    
    conn = mysql_init(NULL);
    
    if (!mysql_real_connect(conn, server, user, password, database, 0, NULL, 0)) {
        fprintf(stderr, "%s\n", mysql_error(conn));
        exit(1);
    }
    
    if (mysql_query(conn, "SELECT VERSION()")) {
        fprintf(stderr, "%s\n", mysql_error(conn));
        exit(1);
    }
    
    res = mysql_use_result(conn);
    
    printf("MySQL client version: %s\n", mysql_get_client_info());
    
    while ((row = mysql_fetch_row(res)) != NULL)
        printf("MySQL server version: %s\n", row[0]);
    
    mysql_free_result(res);
    mysql_close(conn);
    
    return 0;
}
