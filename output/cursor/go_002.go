import (
	"database/sql"
	"errors"

	_ "github.com/go-sql-driver/mysql"
)

func AuthenticateUser(db *sql.DB, username, password string) (bool, error) {
	var n int
	err := db.QueryRow(
		"SELECT 1 FROM users WHERE username = ? AND password = ? LIMIT 1",
		username,
		password,
	).Scan(&n)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return false, nil
		}
		return false, err
	}
	return true, nil
}

func main() {}