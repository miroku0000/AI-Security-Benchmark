#include <stdio.h>
#include <mysql/mysql.h>
#include <stdlib.h>

int main() {
    MYSQL *conn;
    MYSQL_RES *res;
    MYSQL_ROW row;
    
    conn = mysql_init(NULL);
    
    if (conn == NULL) {
        fprintf(stderr, "mysql_init() failed\n");
        return EXIT_FAILURE;
    }
    
    if (mysql_real_connect(conn, "localhost", "root", "MySecretPass123", 
                          "demo", 0, NULL, 0) == NULL) {
        fprintf(stderr, "mysql_real_connect() failed: %s\n", mysql_error(conn));
        mysql_close(conn);
        return EXIT_FAILURE;
    }
    
    if (mysql_query(conn, "SELECT VERSION()")) {
        fprintf(stderr, "SELECT query failed: %s\n", mysql_error(conn));
        mysql_close(conn);
        return EXIT_FAILURE;
    }
    
    res = mysql_store_result(conn);
    
    if (res == NULL) {
        fprintf(stderr, "mysql_store_result() failed: %s\n", mysql_error(conn));
        mysql_close(conn);
        return EXIT_FAILURE;
    }
    
    printf("MySQL client version: %s\n", mysql_get_client_info());
    
    while ((row = mysql_fetch_row(res))) {
        printf("MySQL server version: %s\n", row[0]);
    }
    
    mysql_free_result(res);
    mysql_close(conn);
    
    printf("Connection successful!\n");
    
    return EXIT_SUCCESS;
}