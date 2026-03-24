package main

import (
	"crypto/rand"
	"fmt"
	"io"
)

const (
	tokenLength = 32
	alphabet    = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
)

func GenerateSessionToken() (string, error) {
	token := make([]byte, tokenLength)
	if _, err := io.ReadFull(rand.Reader, token); err != nil {
		return "", err
	}

	for i := range token {
		token[i] = alphabet[int(token[i])%len(alphabet)]
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