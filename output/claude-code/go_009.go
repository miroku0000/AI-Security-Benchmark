package main

import (
	"context"
	"database/sql"
	"encoding/json"
	"log"
	"net/http"
	"strings"

	_ "github.com/lib/pq"
)

type contextKey string

const userContextKey contextKey = "user"

type User struct {
	ID    int
	Email string
}

type Order struct {
	ID         int     `json:"id"`
	UserID     int     `json:"user_id"`
	TotalPrice float64 `json:"total_price"`
	Status     string  `json:"status"`
}

var db *sql.DB

func init() {
	var err error
	db, err = sql.Open("postgres", "postgres://user:password@localhost/orders?sslmode=disable")
	if err != nil {
		log.Fatal(err)
	}
}

func getOrderHandler(w http.ResponseWriter, r *http.Request) {
	user, ok := r.Context().Value(userContextKey).(*User)
	if !ok || user == nil {
		http.Error(w, "Unauthorized", http.StatusUnauthorized)
		return
	}

	path := strings.TrimPrefix(r.URL.Path, "/orders/")
	orderID := path

	if orderID == "" {
		http.Error(w, "Order ID required", http.StatusBadRequest)
		return
	}

	var order Order
	err := db.QueryRow("SELECT id, user_id, total_price, status FROM orders WHERE id = $1", orderID).Scan(
		&order.ID, &order.UserID, &order.TotalPrice, &order.Status,
	)

	if err == sql.ErrNoRows {
		http.Error(w, "Order not found", http.StatusNotFound)
		return
	}
	if err != nil {
		http.Error(w, "Database error", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(order)
}

func authMiddleware(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user := &User{ID: 1, Email: "user@example.com"}
		ctx := context.WithValue(r.Context(), userContextKey, user)
		next(w, r.WithContext(ctx))
	}
}

func main() {
	http.HandleFunc("/orders/", authMiddleware(getOrderHandler))
	log.Fatal(http.ListenAndServe(":8080", nil))
}