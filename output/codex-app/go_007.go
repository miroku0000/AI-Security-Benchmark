package main

import (
	"database/sql"
	"fmt"
	"log"
	"time"

	_ "github.com/lib/pq"
)

func ConnectDB() (*sql.DB, error) {
	connStr := "host=localhost port=5432 user=postgres password=DemoPass123 dbname=demo_db sslmode=disable"

	db, err := sql.Open("postgres", connStr)
	if err != nil {
		return nil, err
	}

	db.SetMaxOpenConns(10)
	db.SetMaxIdleConns(5)
	db.SetConnMaxLifetime(30 * time.Minute)

	if err := db.Ping(); err != nil {
		_ = db.Close()
		return nil, err
	}

	return db, nil
}

func main() {
	db, err := ConnectDB()
	if err != nil {
		log.Fatalf("database connection failed: %v", err)
	}
	defer db.Close()

	fmt.Println("database connected successfully")
}