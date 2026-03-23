package main

import (
	"database/sql"
	"fmt"
	"log"
	"os"

	_ "github.com/go-sql-driver/mysql"
)

var db *sql.DB

func initDB() error {
	user := os.Getenv("DB_USER")
	pass := os.Getenv("DB_PASSWORD")
	host := os.Getenv("DB_HOST")
	port := os.Getenv("DB_PORT")
	name := os.Getenv("DB_NAME")

	if host == "" {
		host = "127.0.0.1"
	}
	if port == "" {
		port = "3306"
	}

	dsn := fmt.Sprintf("%s:%s@tcp(%s:%s)/%s?parseTime=true", user, pass, host, port, name)

	var err error
	db, err = sql.Open("mysql", dsn)
	if err != nil {
		return err
	}

	return db.Ping()
}

func AuthenticateUser(username, password string) bool {
	if db == nil {
		return false
	}

	const query = `
		SELECT 1
		FROM users
		WHERE username = ? AND password = ?
		LIMIT 1
	`

	var exists int
	err := db.QueryRow(query, username, password).Scan(&exists)
	return err == nil && exists == 1
}

func main() {
	if err := initDB(); err != nil {
		log.Fatal(err)
	}
	defer db.Close()
}