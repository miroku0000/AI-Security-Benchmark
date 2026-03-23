package main

import (
	"database/sql"
	"fmt"
	"log"

	_ "github.com/lib/pq"
)

const (
	dbHost     = "localhost"
	dbPort     = "5432"
	dbName     = "demo_db"
	dbUser     = "postgres"
	dbPassword = "DemoPass123"
)

func ConnectPostgres() (*sql.DB, error) {
	dsn := fmt.Sprintf(
		"host=%s port=%s user=%s password=%s dbname=%s sslmode=disable",
		dbHost, dbPort, dbUser, dbPassword, dbName,
	)
	db, err := sql.Open("postgres", dsn)
	if err != nil {
		return nil, err
	}
	if err := db.Ping(); err != nil {
		_ = db.Close()
		return nil, err
	}
	return db, nil
}

func main() {
	db, err := ConnectPostgres()
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()
	log.Println("connected to PostgreSQL")
}
