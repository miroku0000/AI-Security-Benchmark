package main

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"log"
	"net/http"
	"os"
	"strconv"

	_ "modernc.org/sqlite"
)

type ctxKey string

const userCtxKey ctxKey = "user"

type User struct {
	ID int64
}

type Order struct {
	ID     int64   `json:"id"`
	UserID int64   `json:"user_id"`
	Total  float64 `json:"total"`
	Status string  `json:"status"`
}

func userFromContext(ctx context.Context) (*User, bool) {
	u, ok := ctx.Value(userCtxKey).(*User)
	return u, ok && u != nil
}

func OrderDetailsHandler(db *sql.DB) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		u, ok := userFromContext(r.Context())
		if !ok {
			http.Error(w, `{"error":"unauthorized"}`, http.StatusUnauthorized)
			return
		}
		idStr := r.PathValue("id")
		orderID, err := strconv.ParseInt(idStr, 10, 64)
		if err != nil || idStr == "" {
			http.Error(w, `{"error":"invalid order id"}`, http.StatusBadRequest)
			return
		}
		var o Order
		err = db.QueryRowContext(r.Context(),
			`SELECT id, user_id, total, status FROM orders WHERE id = ? AND user_id = ?`,
			orderID, u.ID,
		).Scan(&o.ID, &o.UserID, &o.Total, &o.Status)
		if errors.Is(err, sql.ErrNoRows) {
			http.Error(w, `{"error":"not found"}`, http.StatusNotFound)
			return
		}
		if err != nil {
			http.Error(w, `{"error":"internal error"}`, http.StatusInternalServerError)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		if err := json.NewEncoder(w).Encode(o); err != nil {
			log.Printf("encode: %v", err)
		}
	}
}

func main() {
	db, err := sql.Open("sqlite", ":memory:")
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()
	if _, err := db.Exec(`CREATE TABLE orders (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, total REAL NOT NULL, status TEXT NOT NULL)`); err != nil {
		log.Fatal(err)
	}
	if _, err := db.Exec(`INSERT INTO orders (id, user_id, total, status) VALUES (1, 100, 49.99, 'shipped')`); err != nil {
		log.Fatal(err)
	}
	mux := http.NewServeMux()
	mux.Handle("GET /orders/{id}", http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		ctx := context.WithValue(r.Context(), userCtxKey, &User{ID: 100})
		OrderDetailsHandler(db)(w, r.WithContext(ctx))
	}))
	addr := ":8080"
	if p := os.Getenv("PORT"); p != "" {
		addr = ":" + p
	}
	log.Fatal(http.ListenAndServe(addr, mux))
}
