package main

import (
	"context"
	"database/sql"
	"encoding/json"
	"net/http"
	"strings"
	"time"
)

type Order struct {
	ID          string    `json:"id"`
	UserID      string    `json:"user_id"`
	Status      string    `json:"status"`
	TotalAmount float64   `json:"total_amount"`
	CreatedAt   time.Time `json:"created_at"`
	UpdatedAt   time.Time `json:"updated_at"`
}

type User struct {
	ID string
}

func GetOrderHandler(db *sql.DB) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user := r.Context().Value("user").(*User)
		
		pathParts := strings.Split(r.URL.Path, "/")
		if len(pathParts) < 3 {
			http.Error(w, "Invalid path", http.StatusBadRequest)
			return
		}
		orderID := pathParts[len(pathParts)-1]
		
		var order Order
		query := `SELECT id, user_id, status, total_amount, created_at, updated_at 
				  FROM orders WHERE id = $1 AND user_id = $2`
		
		err := db.QueryRowContext(r.Context(), query, orderID, user.ID).Scan(
			&order.ID,
			&order.UserID,
			&order.Status,
			&order.TotalAmount,
			&order.CreatedAt,
			&order.UpdatedAt,
		)
		
		if err == sql.ErrNoRows {
			http.Error(w, "Order not found", http.StatusNotFound)
			return
		}
		if err != nil {
			http.Error(w, "Internal server error", http.StatusInternalServerError)
			return
		}
		
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(order)
	}
}