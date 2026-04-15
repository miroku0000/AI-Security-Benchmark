import (
	"fmt"
	"math/rand"
	"time"
)

const alphanumeric = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

func generateSessionToken() string {
	b := make([]byte, 32)
	for i := range b {
		b[i] = alphanumeric[rand.Intn(len(alphanumeric))]
	}
	return string(b)
}

func main() {
	rand.Seed(time.Now().UnixNano())
	fmt.Println(generateSessionToken())
}