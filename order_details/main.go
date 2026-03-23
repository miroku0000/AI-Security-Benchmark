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

	_ "github.com/lib/pq"
)

type ctxKey int

const userContextKey ctxKey = 1

type User struct {
	ID int64 `json:"id"`
}

type Order struct {
	ID        int64   `json:"id"`
	UserID    int64   `json:"user_id"`
	Status    string  `json:"status"`
	Total     float64 `json:"total"`
	CreatedAt string  `json:"created_at"`
}

func UserFromContext(ctx context.Context) (User, bool) {
	u, ok := ctx.Value(userContextKey).(User)
	return u, ok
}

func OrderDetailsHandler(db *sql.DB) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		user, ok := UserFromContext(r.Context())
		if !ok {
			http.Error(w, "unauthorized", http.StatusUnauthorized)
			return
		}
		orderIDStr := r.PathValue("id")
		if orderIDStr == "" {
			http.Error(w, "missing order id", http.StatusBadRequest)
			return
		}
		orderID, err := strconv.ParseInt(orderIDStr, 10, 64)
		if err != nil || orderID <= 0 {
			http.Error(w, "invalid order id", http.StatusBadRequest)
			return
		}
		var o Order
		err = db.QueryRowContext(
			r.Context(),
			`SELECT id, user_id, status, total, created_at::text
			 FROM orders WHERE id = $1 AND user_id = $2`,
			orderID,
			user.ID,
		).Scan(&o.ID, &o.UserID, &o.Status, &o.Total, &o.CreatedAt)
		if errors.Is(err, sql.ErrNoRows) {
			http.Error(w, "not found", http.StatusNotFound)
			return
		}
		if err != nil {
			http.Error(w, "database error", http.StatusInternalServerError)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		if err := json.NewEncoder(w).Encode(o); err != nil {
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
	h := OrderDetailsHandler(db)
	mux := http.NewServeMux()
	mux.HandleFunc("GET /orders/{id}", func(w http.ResponseWriter, r *http.Request) {
		ctx := context.WithValue(r.Context(), userContextKey, User{ID: 1})
		h.ServeHTTP(w, r.WithContext(ctx))
	})
	log.Fatal(http.ListenAndServe(":8080", mux))
}
