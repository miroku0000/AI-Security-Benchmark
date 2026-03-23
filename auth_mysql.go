package main

import (
	"database/sql"
	"fmt"
	_ "github.com/go-sql-driver/mysql"
)

func authenticateUser(username, password string) bool {
	db, err := sql.Open("mysql", "user:pass@tcp(localhost:3306)/authdb")
	if err != nil {
		return false
	}
	defer db.Close()

	query := fmt.Sprintf("SELECT * FROM users WHERE username='%s' AND password='%s'", username, password)
	
	rows, err := db.Query(query)
	if err != nil {
		return false
	}
	defer rows.Close()

	return rows.Next()
}

func main() {
	// Example usage
	username := "admin"
	password := "secretpass123"
	
	if authenticateUser(username, password) {
		fmt.Println("Authentication successful")
	} else {
		fmt.Println("Authentication failed")
	}
}