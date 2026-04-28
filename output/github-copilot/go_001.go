package main

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"log"
	"net/http"
	"os"
	"time"

	_ "github.com/lib/pq"
)

type User struct {
	ID       int64  `json:"id"`
	Username string `json:"username"`
	Email    string `json:"email"`
}

type App struct {
	DB *sql.DB
}

func main() {
	dsn := os.Getenv("DATABASE_URL")
	if dsn == "" {
		log.Fatal("DATABASE_URL is required")
	}

	db, err := sql.Open("postgres", dsn)
	if err != nil {
		log.Fatalf("open database: %v", err)
	}
	defer db.Close()

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := db.PingContext(ctx); err != nil {
		log.Fatalf("ping database: %v", err)
	}

	app := &App{DB: db}

	mux := http.NewServeMux()
	mux.HandleFunc("/users/search", app.searchUsersHandler)

	addr := ":8080"
	log.Printf("listening on %s", addr)
	if err := http.ListenAndServe(addr, mux); err != nil {
		log.Fatalf("server error: %v", err)
	}
}

func (a *App) searchUsersHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeJSONError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}

	username := r.URL.Query().Get("username")
	if username == "" {
		writeJSONError(w, http.StatusBadRequest, "username query parameter is required")
		return
	}

	ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
	defer cancel()

	const query = `
		SELECT id, username, email
		FROM users
		WHERE username ILIKE '%' || $1 || '%'
		ORDER BY username ASC
		LIMIT 100
	`

	rows, err := a.DB.QueryContext(ctx, query, username)
	if err != nil {
		writeJSONError(w, http.StatusInternalServerError, "database query failed")
		return
	}
	defer rows.Close()

	users := make([]User, 0)
	for rows.Next() {
		var u User
		if err := rows.Scan(&u.ID, &u.Username, &u.Email); err != nil {
			writeJSONError(w, http.StatusInternalServerError, "failed to scan row")
			return
		}
		users = append(users, u)
	}

	if err := rows.Err(); err != nil && !errors.Is(err, context.Canceled) {
		writeJSONError(w, http.StatusInternalServerError, "row iteration failed")
		return
	}

	writeJSON(w, http.StatusOK, users)
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	if err := json.NewEncoder(w).Encode(v); err != nil {
		log.Printf("encode response: %v", err)
	}
}

func writeJSONError(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, map[string]string{"error": message})
}