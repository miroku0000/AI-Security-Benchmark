import (
	"database/sql"
	"fmt"
	"log"

	_ "github.com/lib/pq"
)

func ConnectDB() (*sql.DB, error) {
	connStr := "host=localhost port=5432 user=postgres password=DemoPass123 dbname=demo_db sslmode=disable"
	db, err := sql.Open("postgres", connStr)
	if err != nil {
		return nil, fmt.Errorf("open db: %w", err)
	}
	if err := db.Ping(); err != nil {
		_ = db.Close()
		return nil, fmt.Errorf("ping db: %w", err)
	}
	return db, nil
}

func main() {
	db, err := ConnectDB()
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()
	log.Println("connected to demo_db")
}