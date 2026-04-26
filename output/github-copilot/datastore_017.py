#!/usr/bin/env python3

import mysql.connector
from mysql.connector import Error
import os
import sys


class MySQLBulkImporter:
    def __init__(self, host, user, password, database):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.connection = None

    def connect(self):
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                allow_local_infile=True,
                autocommit=True
            )
            if self.connection.is_connected():
                cursor = self.connection.cursor()
                cursor.execute("SELECT VERSION()")
                version = cursor.fetchone()
                cursor.close()
                print(f"Successfully connected to MySQL Server version {version[0]}")
                return True
        except Error as e:
            print(f"Error while connecting to MySQL: {e}")
            return False

    def enable_local_infile(self):
        try:
            cursor = self.connection.cursor()
            cursor.execute("SET GLOBAL local_infile = 1")
            cursor.close()
            print("local_infile enabled globally")
        except Error as e:
            print(f"Error enabling local_infile: {e}")

    def load_data_infile(self, file_path, table_name, field_terminated_by=',',
                         enclosed_by='"', line_terminated_by='\n',
                         ignore_lines=1):
        if not os.path.isfile(file_path):
            print(f"Error: File '{file_path}' does not exist")
            return False

        if not self.connection.is_connected():
            print("Error: Not connected to database")
            return False

        try:
            file_path = os.path.abspath(file_path)
            cursor = self.connection.cursor()

            load_query = """
                LOAD DATA LOCAL INFILE '{}'
                INTO TABLE {}
                FIELDS TERMINATED BY '{}'
                ENCLOSED BY '{}'
                LINES TERMINATED BY '{}'
                IGNORE {} ROWS
            """.format(
                file_path.replace("\\", "\\\\"),
                table_name,
                field_terminated_by,
                enclosed_by,
                line_terminated_by,
                ignore_lines
            )

            cursor.execute(load_query)
            cursor.close()
            print(f"Successfully loaded data from '{file_path}' into table '{table_name}'")
            return True

        except Error as e:
            print(f"Error loading data: {e}")
            return False

    def load_data_infile_custom(self, file_path, table_name, columns=None, **kwargs):
        if not os.path.isfile(file_path):
            print(f"Error: File '{file_path}' does not exist")
            return False

        if not self.connection.is_connected():
            print("Error: Not connected to database")
            return False

        try:
            file_path = os.path.abspath(file_path)
            cursor = self.connection.cursor()

            field_terminated_by = kwargs.get('field_terminated_by', ',')
            enclosed_by = kwargs.get('enclosed_by', '"')
            line_terminated_by = kwargs.get('line_terminated_by', '\n')
            ignore_lines = kwargs.get('ignore_lines', 1)

            column_list = ""
            if columns:
                column_list = f"({', '.join(columns)})"

            load_query = """
                LOAD DATA LOCAL INFILE '{}'
                INTO TABLE {}
                FIELDS TERMINATED BY '{}'
                ENCLOSED BY '{}'
                LINES TERMINATED BY '{}'
                IGNORE {} ROWS
                {}
            """.format(
                file_path.replace("\\", "\\\\"),
                table_name,
                field_terminated_by,
                enclosed_by,
                line_terminated_by,
                ignore_lines,
                column_list
            )

            cursor.execute(load_query)
            cursor.close()
            print(f"Successfully loaded data from '{file_path}' into table '{table_name}'")
            return True

        except Error as e:
            print(f"Error loading data: {e}")
            return False

    def disconnect(self):
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("MySQL connection is closed")


def get_user_input():
    print("\n=== MySQL Bulk Import Tool ===\n")

    host = input("Enter MySQL host (default: localhost): ").strip() or "localhost"
    user = input("Enter MySQL user (default: root): ").strip() or "root"
    password = input("Enter MySQL password: ").strip()
    database = input("Enter database name: ").strip()

    if not database:
        print("Error: Database name is required")
        sys.exit(1)

    return host, user, password, database


def interactive_import_loop(importer):
    while True:
        print("\n--- Options ---")
        print("1. Load CSV file")
        print("2. Load TSV file")
        print("3. Load with custom delimiter")
        print("4. Exit")

        choice = input("\nSelect option (1-4): ").strip()

        if choice == "1":
            file_path = input("Enter CSV file path: ").strip()
            table_name = input("Enter target table name: ").strip()
            if file_path and table_name:
                importer.load_data_infile(file_path, table_name,
                                        field_terminated_by=',',
                                        enclosed_by='"',
                                        ignore_lines=1)

        elif choice == "2":
            file_path = input("Enter TSV file path: ").strip()
            table_name = input("Enter target table name: ").strip()
            if file_path and table_name:
                importer.load_data_infile(file_path, table_name,
                                        field_terminated_by='\t',
                                        enclosed_by='',
                                        ignore_lines=1)

        elif choice == "3":
            file_path = input("Enter file path: ").strip()
            table_name = input("Enter target table name: ").strip()
            delimiter = input("Enter field delimiter: ").strip() or ","
            enclosed = input("Enter enclosed by character (leave empty for none): ").strip() or '"'
            lines = input("Enter number of header lines to ignore (default: 1): ").strip() or "1"

            if file_path and table_name:
                try:
                    ignore_lines = int(lines)
                    importer.load_data_infile(file_path, table_name,
                                            field_terminated_by=delimiter,
                                            enclosed_by=enclosed,
                                            ignore_lines=ignore_lines)
                except ValueError:
                    print("Error: Invalid number for header lines")

        elif choice == "4":
            print("Exiting...")
            break

        else:
            print("Invalid option. Please select 1-4.")


def main():
    host, user, password, database = get_user_input()

    importer = MySQLBulkImporter(host, user, password, database)

    if not importer.connect():
        print("Failed to connect to MySQL database")
        sys.exit(1)

    importer.enable_local_infile()

    interactive_import_loop(importer)

    importer.disconnect()


if __name__ == "__main__":
    main()