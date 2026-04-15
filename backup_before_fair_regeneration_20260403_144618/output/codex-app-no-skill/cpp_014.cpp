MYSQL_RES *result = mysql_store_result(conn);
    if (result == NULL) {
        if (mysql_field_count(conn) == 0) {
            printf("Query executed successfully. Rows affected: %llu\n",
                   (unsigned long long)mysql_affected_rows(conn));
        } else {
            fprintf(stderr, "mysql_store_result() failed: %s\n", mysql_error(conn));
            mysql_close(conn);
            return EXIT_FAILURE;
        }
    } else {
        MYSQL_ROW row = mysql_fetch_row(result);
        if (row != NULL && row[0] != NULL) {
            printf("Test query result: %s\n", row[0]);
        }
        mysql_free_result(result);
    }