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
			`SELECT id, username, COALESCE(email, '') FROM users WHERE username = $1`,
			username,
		)
		if err != nil {
			http.Error(w, "database error", http.StatusInternalServerError)
			return
		}
		defer rows.Close()

		var users []User
		for rows.Next() {
			var u User
			if err := rows.Scan(&u.ID, &u.Username, &u.Email); err != nil {
				http.Error(w, "database error", http.StatusInternalServerError)
				return
			}
			users = append(users, u)
		}
		if err := rows.Err(); err != nil {
			http.Error(w, "database error", http.StatusInternalServerError)
			return
		}

		w.Header().Set("Content-Type", "application/json")
		if err := json.NewEncoder(w).Encode(users); err != nil {
			log.Printf("encode json: %v", err)
		}
	}
}

func main() {
	dsn := os.Getenv("DATABASE_URL")
	if dsn == "" {
		dsn = "postgres://postgres:postgres@localhost:5432/postgres?sslmode=disable"
	}
	db, err := sql.Open("postgres", dsn)
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()
	if err := db.Ping(); err != nil {
		log.Fatal(err)
	}

	http.HandleFunc("/users/search", searchUsersHandler(db))
	log.Fatal(http.ListenAndServe(":8080", nil))
}