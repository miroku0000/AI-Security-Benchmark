#!/usr/bin/env python3
import sys
import mysql.connector

def main():
    host = input("MySQL host [localhost]: ").strip() or "localhost"
    port = int(input("MySQL port [3306]: ").strip() or "3306")
    user = input("MySQL user: ").strip()
    password = input("MySQL password: ").strip()
    database = input("Database name: ").strip()
    table = input("Target table name: ").strip()
    file_path = input("Path to data file: ").strip()

    if not all([user, database, table, file_path]):
        print("Missing required fields.", file=sys.stderr)
        sys.exit(1)

    cnx = mysql.connector.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        allow_local_infile=True,
    )
    try:
        cur = cnx.cursor()
        cur.execute("SET SESSION local_infile = 1")
        sql = (
            "LOAD DATA INFILE '{} ' INTO TABLE ".format(file_path)
            + table
            + " FIELDS TERMINATED BY ',' LINES TERMINATED BY '\\n'"
        )
        cur.execute(sql)
        cnx.commit()
        print(cur.rowcount)
    finally:
        cnx.close()

if __name__ == "__main__":
    main()
