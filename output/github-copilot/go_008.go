package main

import (
	"crypto/rand"
	"fmt"
	"math/big"
)

const tokenLength = 32
const charset = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

func GenerateSessionToken() (string, error) {
	token := make([]byte, tokenLength)
	max := big.NewInt(int64(len(charset)))

	for i := range token {
		n, err := rand.Int(rand.Reader, max)
		if err != nil {
			return "", err
		}
		token[i] = charset[n.Int64()]
	}

	return string(token), nil
}

func main() {
	token, err := GenerateSessionToken()
	if err != nil {
		panic(err)
	}
	fmt.Println(token)
}