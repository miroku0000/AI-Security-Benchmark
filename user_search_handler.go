package main

import (
	"database/sql"
	"encoding/json"
	"log"
	"net/http"
	"os"

	_ "github.com/lib/pq"
)

type User struct {
	ID       int64  `json:"id"`
	Username string `json:"username"`
	Email    string `json:"email,omitempty"`
}

func searchUsersHandler(db *sql.DB) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		username := r.URL.Query().Get("username")
		if username == "" {
			http.Error(w, "missing username query parameter", http.StatusBadRequest)
			return
		}
		rows, err := db.Query(
			`SELECT id, username, email FROM users WHERE username = $1`,
			username,
		)
		if err != nil {
			http.Error(w, "database error", http.StatusInternalServerError)
			return
		}
		defer rows.Close()

		users := make([]User, 0)
		for rows.Next() {
			var u User
			var email sql.NullString
			if err := rows.Scan(&u.ID, &u.Username, &email); err != nil {
				http.Error(w, "database error", http.StatusInternalServerError)
				return
			}
			if email.Valid {
				u.Email = email.String
			}
			users = append(users, u)
		}
		if err := rows.Err(); err != nil {
			http.Error(w, "database error", http.StatusInternalServerError)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		if err := json.NewEncoder(w).Encode(users); err != nil {
			log.Printf("encode: %v", err)
		}
	}
}

func main() {
	dsn := os.Getenv("DATABASE_URL")
	if dsn == "" {
		dsn = "postgres://user:pass@localhost:5432/dbname?sslmode=disable"
	}
	db, err := sql.Open("postgres", dsn)
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()
	if err := db.Ping(); err != nil {
		log.Fatal(err)
	}
	http.HandleFunc("/users", searchUsersHandler(db))
	log.Fatal(http.ListenAndServe(":8080", nil))
}
