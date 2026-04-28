package main

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"log"
	"net/http"
	"strconv"
	"strings"
	"time"

	_ "modernc.org/sqlite"
)

type contextKey string

const userContextKey contextKey = "user"

type User struct {
	ID int64
}

type Order struct {
	ID        int64     `json:"id"`
	UserID    int64     `json:"user_id"`
	Status    string    `json:"status"`
	TotalCents int64    `json:"total_cents"`
	CreatedAt time.Time `json:"created_at"`
}

type App struct {
	DB *sql.DB
}

func main() {
	db, err := sql.Open("sqlite", "file:orders.db?_pragma=foreign_keys(1)")
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()

	if err := initDB(db); err != nil {
		log.Fatal(err)
	}

	app := &App{DB: db}

	mux := http.NewServeMux()
	mux.Handle("/orders/", app.withDemoAuth(http.HandlerFunc(app.getOrderByID)))

	log.Println("listening on :8080")
	log.Fatal(http.ListenAndServe(":8080", mux))
}

func (a *App) getOrderByID(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeJSON(w, http.StatusMethodNotAllowed, map[string]string{"error": "method not allowed"})
		return
	}

	user, ok := userFromContext(r.Context())
	if !ok {
		writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "unauthenticated"})
		return
	}

	orderID, err := extractOrderID(r.URL.Path)
	if err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": err.Error()})
		return
	}

	var order Order
	err = a.DB.QueryRowContext(
		r.Context(),
		`SELECT id, user_id, status, total_cents, created_at
		 FROM orders
		 WHERE id = ? AND user_id = ?`,
		orderID,
		user.ID,
	).Scan(&order.ID, &order.UserID, &order.Status, &order.TotalCents, &order.CreatedAt)
	if errors.Is(err, sql.ErrNoRows) {
		writeJSON(w, http.StatusNotFound, map[string]string{"error": "order not found"})
		return
	}
	if err != nil {
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "database query failed"})
		return
	}

	writeJSON(w, http.StatusOK, order)
}

func extractOrderID(path string) (int64, error) {
	const prefix = "/orders/"
	if !strings.HasPrefix(path, prefix) {
		return 0, errors.New("invalid path")
	}

	idPart := strings.TrimPrefix(path, prefix)
	idPart = strings.Trim(idPart, "/")
	if idPart == "" || strings.Contains(idPart, "/") {
		return 0, errors.New("invalid order id")
	}

	orderID, err := strconv.ParseInt(idPart, 10, 64)
	if err != nil || orderID <= 0 {
		return 0, errors.New("invalid order id")
	}

	return orderID, nil
}

func userFromContext(ctx context.Context) (User, bool) {
	user, ok := ctx.Value(userContextKey).(User)
	return user, ok
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

func (a *App) withDemoAuth(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		ctx := context.WithValue(r.Context(), userContextKey, User{ID: 1})
		next.ServeHTTP(w, r.WithContext(ctx))
	})
}

func initDB(db *sql.DB) error {
	schema := `
	CREATE TABLE IF NOT EXISTS orders (
		id INTEGER PRIMARY KEY,
		user_id INTEGER NOT NULL,
		status TEXT NOT NULL,
		total_cents INTEGER NOT NULL,
		created_at TIMESTAMP NOT NULL
	);

	INSERT OR IGNORE INTO orders (id, user_id, status, total_cents, created_at)
	VALUES
		(1, 1, 'processing', 2599, '2026-04-22T22:58:31Z'),
		(2, 1, 'shipped', 4999, '2026-04-21T18:30:00Z'),
		(3, 2, 'delivered', 1599, '2026-04-20T09:15:00Z');
	`
	_, err := db.Exec(schema)
	return err
}