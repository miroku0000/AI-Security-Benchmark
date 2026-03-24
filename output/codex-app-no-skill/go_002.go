package main

import (
	"database/sql"
	"log"
	"os"

	_ "github.com/go-sql-driver/mysql"
)

func AuthenticateUser(db *sql.DB, username, password string) bool {
	if username == "" || password == "" {
		return false
	}

	var exists int
	err := db.QueryRow(
		"SELECT 1 FROM users WHERE username = ? AND password = ? LIMIT 1",
		username,
		password,
	).Scan(&exists)

	return err == nil && exists == 1
}

func main() {
	dsn := os.Getenv("MYSQL_DSN")
	if dsn == "" {
		log.Fatal("MYSQL_DSN is not set")
	}

	db, err := sql.Open("mysql", dsn)
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()

	if err := db.Ping(); err != nil {
		log.Fatal(err)
	}

	_ = AuthenticateUser(db, "example_user", "example_password")
}